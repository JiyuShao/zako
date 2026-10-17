use crate::config::Config;
use crate::context::{EventRequest, EventResponse, Mood};
use crate::{interaction, persona};
use serde_json::json;
use std::{collections::BTreeMap, io::Read, str::FromStr};

const INTEGRATION: &str = include_str!("../integrations/zako.zsh");
const SEP: &str = "\u{1f}";

pub fn run(arguments: Vec<String>) -> Result<(), String> {
    let Some(command) = arguments.first().map(String::as_str) else {
        print_help();
        return Ok(());
    };
    let rest = &arguments[1..];
    match command {
        "init" if rest == ["zsh"] => {
            print!("{INTEGRATION}");
            Ok(())
        }
        "init" => Err("用法：zako init zsh；M1 只支持 Zsh".into()),
        "event" => event(rest),
        "suggest" => suggest(rest),
        "session" => session(rest),
        "startup" => {
            let opts = Options::parse(rest, &[], &["--json"])?;
            let message = persona::startup(&load_config(&opts)?);
            if opts.has("--json") {
                println!("{}", json!({"protocol_version":1,"message":message}));
            } else if !message.is_empty() {
                println!("{message}");
            }
            Ok(())
        }
        "prompt" => {
            let config = Config::load().map_err(|e| e.to_string())?;
            println!(
                "{}",
                if config.general.enabled {
                    &config.prompt.mode
                } else {
                    "off"
                }
            );
            Ok(())
        }
        "doctor" => {
            let opts = Options::parse(rest, &["--config-json"], &[])?;
            let config = load_config(&opts)?;
            println!(
                "config: ok ({})\nshell: Zsh 5.9+\nlanguage: {}\noffline: true\nprompt: {}",
                Config::path().display(),
                config.general.language,
                config.prompt.mode
            );
            println!("manual prompt: add ${{_ZAKO_PROMPT_MARKER}} to your theme with prompt substitution enabled");
            Ok(())
        }
        "fix" | "on" | "off" | "status" => {
            Err("请先在交互式 Zsh 中加载：eval \"$(zako init zsh)\"".into())
        }
        "--help" | "-h" | "help" => {
            print_help();
            Ok(())
        }
        "--version" | "-V" => {
            println!("zako {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        _ => Err(format!("未知命令 `{command}`，使用 zako --help 查看帮助")),
    }
}

fn session(args: &[String]) -> Result<(), String> {
    let opts = Options::parse(args, &[], &["--json"])?;
    let mut config = Config::load().map_err(|e| e.to_string())?;
    let enabled = config.general.enabled;
    let greeting = persona::startup(&config);
    let marker = persona::marker(Mood::Idle, config.prompt.ascii_fallback);
    // The Shell owns the runtime switch. Preserve the initial flag separately,
    // allowing `zako on` to override an initially disabled session.
    config.general.enabled = true;
    let snapshot = serde_json::to_string(&config).map_err(|e| e.to_string())?;
    if opts.has("--json") {
        println!(
            "{}",
            json!({"protocol_version":1,"enabled":enabled,"prompt_mode":config.prompt.mode,"prompt_marker":marker,"message":greeting,"config_json":snapshot})
        );
    } else {
        print_fields(&[
            "1".into(),
            u8::from(enabled).to_string(),
            config.prompt.mode,
            marker,
            greeting,
            snapshot,
        ]);
    }
    Ok(())
}

fn load_config(opts: &Options<'_>) -> Result<Config, String> {
    if let Some(snapshot) = opts.get("--config-json") {
        if snapshot.len() > 8192 {
            return Err("配置快照过长".into());
        }
        let config: Config = serde_json::from_str(snapshot).map_err(|e| e.to_string())?;
        config.validate().map_err(|e| e.to_string())?;
        Ok(config)
    } else {
        Config::load().map_err(|e| e.to_string())
    }
}
fn suggest(args: &[String]) -> Result<(), String> {
    let opts = Options::parse(args, &["--command"], &[])?;
    let config = load_config(&opts)?;
    let raw = opts.required("--command")?;
    let suggestions = if config.general.enabled && config.correction.enabled {
        crate::correction::suggest(raw, config.correction.max_suggestions)
    } else {
        Vec::new()
    };
    println!(
        "{}",
        serde_json::to_string(&suggestions).map_err(|e| e.to_string())?
    );
    Ok(())
}
fn event(args: &[String]) -> Result<(), String> {
    let opts = Options::parse(
        args,
        &[
            "--command",
            "--exit-code",
            "--failures",
            "--now-ms",
            "--last-interaction-ms",
            "--sample",
            "--config-json",
            "--protocol-version",
            "--event",
            "--elapsed-ms",
            "--mood",
            "--cwd",
            "--shell",
        ],
        &["--json"],
    )?;
    if opts.number::<u32>("--protocol-version", "1")? != 1 {
        return Err("不支持的协议版本".into());
    }
    if opts.get("--event").is_some_and(|s| s != "command_finished") {
        return Err("不支持的事件类型".into());
    }
    let sample = match opts.get("--sample") {
        Some(value) => value
            .parse::<f64>()
            .map_err(|_| "sample 无效".to_string())?,
        None => random_sample()?,
    };
    if !(0.0..1.0).contains(&sample) {
        return Err("sample 必须在 [0, 1) 内".into());
    }
    let request = EventRequest {
        command: opts.get("--command").unwrap_or("").to_string(),
        exit_code: opts.number("--exit-code", "0")?,
        consecutive_failures: opts.number("--failures", "0")?,
        now_ms: opts.number("--now-ms", "0")?,
        last_interaction_ms: opts.number("--last-interaction-ms", "0")?,
        sample,
    };
    let response = interaction::event(request, &load_config(&opts)?);
    if opts.has("--json") {
        println!(
            "{}",
            serde_json::to_string(&response).map_err(|e| e.to_string())?
        );
    } else {
        print_shell_response(&response);
    }
    Ok(())
}
fn random_sample() -> Result<f64, String> {
    let mut bytes = [0u8; 4];
    std::fs::File::open("/dev/urandom")
        .and_then(|mut file| file.read_exact(&mut bytes))
        .map_err(|e| e.to_string())?;
    Ok(f64::from(u32::from_ne_bytes(bytes)) / (f64::from(u32::MAX) + 1.0))
}
fn print_shell_response(response: &EventResponse) {
    let mut fields = vec![
        "1".into(),
        response.mood.clone(),
        response.consecutive_failures.to_string(),
        response.failure_class.clone(),
        response.message.clone(),
        response.prompt_marker.clone(),
        response.suggestions.len().to_string(),
    ];
    for index in 0..3 {
        let value = response.suggestions.get(index);
        fields.push(value.map(|s| s.command.clone()).unwrap_or_default());
        fields.push(value.map(|s| s.reason.clone()).unwrap_or_default());
    }
    print_fields(&fields);
}
fn print_fields(fields: &[String]) {
    let fields: Vec<String> = fields
        .iter()
        .map(|value| {
            value
                .chars()
                .map(|c| if c.is_control() { ' ' } else { c })
                .collect()
        })
        .collect();
    println!("{}", fields.join(SEP));
}
struct Options<'a> {
    values: BTreeMap<&'a str, &'a str>,
}
impl<'a> Options<'a> {
    fn parse(args: &'a [String], values: &[&str], flags: &[&str]) -> Result<Self, String> {
        let mut parsed = BTreeMap::new();
        let mut index = 0;
        while let Some(key) = args.get(index) {
            if parsed.contains_key(key.as_str()) {
                return Err(format!("重复参数 {key}"));
            }
            let value = if flags.contains(&key.as_str()) {
                ""
            } else if values.contains(&key.as_str()) {
                index += 1;
                args.get(index)
                    .ok_or_else(|| format!("缺少参数值 {key}"))?
                    .as_str()
            } else {
                return Err(format!("未知参数 {key}"));
            };
            parsed.insert(key.as_str(), value);
            index += 1;
        }
        Ok(Self { values: parsed })
    }
    fn get(&self, key: &str) -> Option<&'a str> {
        self.values.get(key).copied()
    }
    fn has(&self, key: &str) -> bool {
        self.values.contains_key(key)
    }
    fn required(&self, key: &str) -> Result<&'a str, String> {
        self.get(key).ok_or_else(|| format!("缺少参数 {key}"))
    }
    fn number<T: FromStr>(&self, key: &str, default: &str) -> Result<T, String> {
        self.get(key)
            .unwrap_or(default)
            .parse()
            .map_err(|_| format!("参数 {key} 无效"))
    }
}
fn print_help() {
    println!("zako - Zsh Shell Companion\n\n  zako init zsh   输出初始化脚本\n  zako doctor     配置与当前会话排障\n  zako on/off     当前会话开关\n  zako status     当前会话状态\n  zako fix        查看建议；需要手动输入与执行\n\n离线运行，不接管 Tab，不自动执行，不保存命令历史。");
}
