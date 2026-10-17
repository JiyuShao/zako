use crate::{config::Config, correction};
use serde::{Deserialize, Serialize};

const FAMILIES: [&str; 6] = ["git", "cargo", "docker", "rm", "sudo", "other"];

/// Bounded aggregate state only: no command text, paths or command output.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct State {
    pub commands: u32,
    pub successes: u32,
    pub failures: u32,
    pub corrections: u32,
    pub neutral: u32,
    pub interrupted: u32,
    pub streak: u32,
    pub best_streak: u32,
    pub ranks: [u32; 6],
    pub success_badge: bool,
    pub failure_badge: bool,
    pub recent_failures: Vec<u64>,
    pub last_budget_ms: Option<u64>,
}

pub struct Feedback {
    pub achievement: Option<&'static str>,
    pub budget: bool,
}

pub fn family(command: &str) -> usize {
    if !correction::is_simple_command(command) {
        return 5;
    }
    FAMILIES
        .iter()
        .position(|s| Some(*s) == command.split_whitespace().next())
        .unwrap_or(5)
}

impl State {
    pub fn parse(raw: &str) -> Result<Self, String> {
        if raw.len() > 4096 {
            return Err("会话状态过长".into());
        }
        let state: Self = serde_json::from_str(raw).map_err(|e| e.to_string())?;
        if state.recent_failures.len() > 100
            || state.recent_failures.windows(2).any(|w| w[0] > w[1])
        {
            return Err("会话失败窗口无效".into());
        }
        Ok(state)
    }

    pub fn record(
        &mut self,
        class: &str,
        command: &str,
        now: u64,
        config: &Config,
        can_speak: bool,
    ) -> Feedback {
        let mut feedback = Feedback {
            achievement: None,
            budget: false,
        };
        if class == "disabled" {
            return feedback;
        }
        let failed = matches!(class, "unknown" | "correctable");
        if config.interaction.failure_budget {
            let window = config.interaction.failure_window_seconds * 1000;
            // Wall-clock adjustments cannot retain future timestamps indefinitely.
            self.recent_failures
                .retain(|t| *t <= now && now.saturating_sub(*t) < window);
            if failed {
                self.recent_failures.push(now);
                if self.recent_failures.len() > 100 {
                    self.recent_failures.remove(0);
                }
                if self.recent_failures.len() >= config.interaction.failure_budget_count
                    && self
                        .last_budget_ms
                        .is_none_or(|t| t > now || now.saturating_sub(t) >= window)
                    && can_speak
                {
                    feedback.budget = true;
                    self.last_budget_ms = Some(now);
                }
            }
        } else {
            self.recent_failures.clear();
            self.last_budget_ms = None;
        }
        if !config.session.enabled {
            return feedback;
        }
        self.commands = self.commands.saturating_add(1);
        if class == "success" {
            self.successes = self.successes.saturating_add(1);
            self.streak = self.streak.saturating_add(1);
            self.best_streak = self.best_streak.max(self.streak);
            if config.session.achievements
                && !self.success_badge
                && self.streak >= config.session.success_streak_goal
            {
                self.success_badge = true;
                feedback.achievement = Some("success_streak");
            }
        } else {
            self.streak = 0;
            if failed {
                self.failures = self.failures.saturating_add(1);
                self.ranks[family(command)] = self.ranks[family(command)].saturating_add(1);
                if class == "correctable" {
                    self.corrections = self.corrections.saturating_add(1);
                }
                if config.session.achievements
                    && !self.failure_badge
                    && self.failures >= config.session.failure_milestone
                {
                    self.failure_badge = true;
                    feedback.achievement = Some("persistent");
                }
            } else if class == "neutral" {
                self.neutral = self.neutral.saturating_add(1);
            } else if class == "interrupted" {
                self.interrupted = self.interrupted.saturating_add(1);
            }
        }
        feedback
    }

    pub fn summary(&self, config: &Config) -> String {
        if !config.session.enabled {
            return "会话统计已关闭（session.enabled = false）。".into();
        }
        let mut ranking: Vec<_> = FAMILIES
            .iter()
            .zip(self.ranks)
            .filter(|(_, n)| *n > 0)
            .collect();
        ranking.sort_by_key(|a| std::cmp::Reverse(a.1));
        let ranking = ranking
            .iter()
            .map(|(name, n)| format!("{name}:{n}"))
            .collect::<Vec<_>>()
            .join(" ");
        let mut badges = Vec::new();
        if self.success_badge {
            badges.push("连胜小天才");
        }
        if self.failure_badge {
            badges.push("不服输的杂鱼");
        }
        format!("commands={} successes={} failures={} corrections={}\nneutral={} interrupted={} streak={} best_streak={}\n失败排行：{}\n会话成就：{}\n统计仅保存在当前 Shell；运行 zako stats reset 清零。", self.commands, self.successes, self.failures, self.corrections, self.neutral, self.interrupted, self.streak, self.best_streak, if ranking.is_empty() { "暂无" } else { &ranking }, if badges.is_empty() { "暂无".into() } else { badges.join("、") })
    }
}
