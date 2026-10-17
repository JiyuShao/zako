use crate::config::Config;
use crate::context::Mood;

pub fn startup(config: &Config) -> String {
    if !config.interaction.startup_greeting || !config.general.enabled {
        return String::new();
    }
    format!(
        "♡ {}",
        line(
            config,
            [
                "嘿，{name}，今天也一起写点代码吧。",
                "哼，{name}，今天也要本小姐陪你？",
                "嘿，{name}，今天也别把代码写坏了哦？",
                "哟，{name}，又来让本小姐看你手忙脚乱啦？",
                "来了呀，{name}？键盘都准备好了，就等你贡献笑话了。",
            ]
        )
    )
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

pub fn event_message(
    config: &Config,
    mood: Mood,
    failure_class: &str,
    failures: u32,
    command: &str,
) -> String {
    if failure_class == "correctable" {
        return line(
            config,
            [
                "{name}，好像有个拼写问题，运行 `zako fix` 看看候选吧。",
                "哼，拼写差一点。运行 `zako fix`，本小姐找到候选了。",
                "连命令都能打错？{name}，运行 `zako fix`，自己确认候选再输入。",
                "{name}，键盘是烫手吗？这拼写也敢回车？运行 `zako fix` 看候选。",
                "噗，{name}，命令还没开工就被你的拼写逗倒了。运行 `zako fix`，确认候选后自己输。",
            ],
        );
    }
    if failure_class == "help" && config.interaction.consecutive_failure_tip {
        return line(
            config,
            [
                "{name}，连续失败 {count} 次了，先读一下刚才的错误输出吧。",
                "连续失败 {count} 次了。哼，{name}，先检查错误输出再试。",
                "连续失败 {count} 次了。{name}，承认需要本小姐提醒了吧？先看错误输出。",
                "连续失败 {count} 次了。{name}，回车键都比你先学会反省了，看看错误输出。",
                "连续失败 {count} 次了，{name}！还想靠气势把命令吓成功？停手，先读错误输出。",
            ],
        )
        .replace("{count}", &failures.to_string());
    }
    if failure_class == "unknown" {
        let stage = if config.interaction.failure_escalation {
            failures.min(3)
        } else {
            1
        };
        let mut message = match stage {
            3 => line(
                config,
                [
                    "又失败了，{name}，换个排查方向吧。",
                    "又失败了？{name}，同样的尝试先放一放吧。",
                    "又失败了？{name}，你打算把这条命令念到它自己投降吗？",
                    "又失败了？{name}，重复按回车可解锁不了隐藏结局，换个排查方向。",
                    "又失败了？{name}，报错都快背下你的手速了，你还没读懂它？先换个排查方向。",
                ],
            ),
            2 => line(
                config,
                [
                    "又一次没成功，{name}，检查一下输入吧。",
                    "第二次了，{name}，这次看清参数了吗？",
                    "又来？{name}，回车按得再快也不会替你检查参数。",
                    "第二次还没成功？{name}，你是在拿报错练习打字吗？",
                    "第二次了，{name}，把碰运气当调试，真有你的。先核对输入。",
                ],
            ),
            _ => line(
                config,
                [
                    "{name}，这次没成功，看看错误输出吧。",
                    "哼，{name}，命令没有成功，检查一下输入。",
                    "这都能失败？{name}，先别乱按，看看错误输出。",
                    "{name}，这就翻车了？手速挺快，检查输入的速度跟上了吗？",
                    "噗，{name}，回车的气势倒是满分，结果就这？先把错误输出读明白。",
                ],
            ),
        };
        if config.interaction.command_commentary {
            if let Some(comment) = command_flavor(command) {
                message.push(' ');
                message.push_str(comment);
            }
        }
        return message;
    }
    if mood == Mood::Proud {
        return line(
            config,
            [
                "{name}，这一步做成了，值得开心一下。",
                "居然成功了？勉强夸你一下吧，{name}。",
                "居然成功了？{name}，别得意，本小姐只是刚好在看。",
                "哟，{name}，总算有点像样的成果了。才、才没替你高兴呢。",
                "{name}，居然真做成了？本小姐都准备好笑你了……算你这次厉害，只有这次！",
            ],
        );
    }
    if mood == Mood::Happy && config.interaction.profile != "quiet" {
        return line(
            config,
            [
                "{name}，做得不错，继续吧。",
                "哼，{name}，这次做对了。",
                "哼，{name}，勉强算你做对了，别以为本小姐会一直夸你。",
                "{name}，居然没翻车？这点小事就别等着本小姐鼓掌了。",
                "噫，{name}，这就得意了？勉强算你做对了，本小姐的夸奖可没这么好骗。",
            ],
        );
    }
    String::new()
}

pub fn special(config: &Config, kind: &str) -> String {
    match kind {
        "budget" => format!(
            "{} 秒内已有 {} 次失败。{}",
            config.interaction.failure_window_seconds,
            config.interaction.failure_budget_count,
            line(
                config,
                [
                    "{name}，休息一下，整理错误信息再继续吧。",
                    "{name}，失败预算用完了，先整理错误信息。",
                    "{name}，失败预算都刷光了，还想抽成功保底？先停下来排查。",
                    "{name}，报错都快被你刷出会员了。先整理错误信息，别继续乱试。",
                    "{name}，你把终端当失败批发市场啦？暂停营业，读完错误信息再回来。",
                ]
            )
        ),
        "success_streak" => format!(
            "成就解锁：连胜小天才（连续成功 {} 次）。{}",
            config.session.success_streak_goal,
            line(
                config,
                [
                    "{name}，保持这个节奏。",
                    "{name}，还算稳定嘛。",
                    "{name}，别误会，本小姐只是替你记着，才没有偷偷鼓掌。",
                    "{name}，居然一路没翻车？本小姐的笑话素材都断供了。",
                    "{name}，这样显得本小姐刚才小看你了……不许笑，下一条继续！"
                ]
            )
        ),
        _ => format!(
            "成就解锁：不服输的杂鱼（累计失败 {} 次）。{}",
            config.session.failure_milestone,
            line(
                config,
                [
                    "{name}，坚持不错，也记得换个方法。",
                    "{name}，毅力有了，方法也得跟上。",
                    "{name}，不服输是好事，别把同一个坑住成家。",
                    "{name}，失败成就都拿到了，下一次争取换个奖杯吧。",
                    "{name}，报错收藏家都没你勤快。换个方法，别再给失败冲业绩了。"
                ]
            )
        ),
    }
}

fn line(config: &Config, choices: [&str; 5]) -> String {
    let index = match config.persona.style.as_str() {
        "gentle" => 0,
        "normal" => 1,
        _ => usize::from(config.persona.intensity.saturating_sub(1)).min(4),
    };
    let name = if config.persona.nickname.is_empty() {
        "你"
    } else {
        &config.persona.nickname
    };
    choices[index].replace("{name}", name)
}

fn command_flavor(command: &str) -> Option<&'static str> {
    match crate::session::family(command) {
        0 => Some("Git 这次没成功，先核对仓库状态和错误输出。"),
        1 => Some("Cargo 已经给出结果了，先看报错位置和运行环境。"),
        2 => Some("Docker 这次没成功，先按错误输出检查参数、服务或环境。"),
        3 => Some("rm 这次没成功，确认目标路径和备份后再决定下一步。"),
        4 => Some("sudo 这次没成功，先确认命令意图和权限要求。"),
        _ => None,
    }
}
