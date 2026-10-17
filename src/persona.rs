use crate::config::Config;
use crate::context::Mood;

pub fn startup(config: &Config) -> String {
    if !config.interaction.startup_greeting || !config.general.enabled {
        return String::new();
    }
    "♡ 哼，今天也要本小姐陪你写代码？".to_string()
}

pub fn marker(mood: Mood, ascii_fallback: bool) -> String {
    let value = match mood {
        Mood::Happy => "(＾▽＾)",
        Mood::Annoyed => "(ಠ_ಠ)",
        Mood::Concerned => "(・_・;)",
        Mood::Proud => "(≧▽≦)",
        Mood::Idle => "(¬_¬)",
    };
    if ascii_fallback {
        match mood {
            Mood::Happy => ":)".to_string(),
            Mood::Annoyed => ":/".to_string(),
            Mood::Concerned => ":|".to_string(),
            Mood::Proud => ":D".to_string(),
            Mood::Idle => ":3".to_string(),
        }
    } else {
        format!("♡ {value}")
    }
}

pub fn event_message(config: &Config, mood: Mood, failure_class: &str, failures: u32) -> String {
    if failure_class == "correctable" {
        return match config.persona.style.as_str() {
            "gentle" => "这条命令好像有个小拼写问题，我找到一个可能的写法。".to_string(),
            "spicy" => "哼，连命令都能打错？我给你找了个可能的写法。".to_string(),
            _ => "命令拼写好像不对，我给你找了个可能的写法。".to_string(),
        };
    }
    if failure_class == "unknown" {
        return match config.persona.style.as_str() {
            "gentle" => "命令没有成功，可以检查一下参数或环境。".to_string(),
            "spicy" => "命令没有成功。要不要让本小姐替你看看？".to_string(),
            _ => "命令没有成功。要不要检查一下？".to_string(),
        };
    }
    if failure_class == "help" && config.interaction.consecutive_failure_tip {
        return format!(
            "已经连续失败 {failures} 次了，要不要让{}帮你看看？",
            config.persona.nickname
        );
    }
    if mood == Mood::Proud {
        return "居然成功了？勉强夸你一下吧。".to_string();
    }
    if mood == Mood::Happy && config.interaction.profile != "quiet" {
        return match config.persona.style.as_str() {
            "gentle" => "做得不错，继续吧。".to_string(),
            "spicy" => "哼，勉强算你做对了。".to_string(),
            _ => "完成得不错。".to_string(),
        };
    }
    String::new()
}
