use crate::config::Config;
use crate::context::{EventRequest, EventResponse, Mood};
use crate::{correction, persona};

pub fn event(request: EventRequest, config: &Config) -> EventResponse {
    let successful = request.exit_code == 0;
    let interrupted = matches!(request.exit_code, 130 | 148);
    let neutral = is_neutral_result(&request.command, request.exit_code);
    // Only command-not-found justifies replacing an executable name. Git's known
    // misspelled subcommands have a separate conservative rule.
    let suggestions = if config.general.enabled
        && config.correction.enabled
        && !successful
        && !interrupted
        && !neutral
    {
        correction::suggest_for_exit(
            &request.command,
            config.correction.max_suggestions,
            request.exit_code,
        )
    } else {
        Vec::new()
    };
    let failure_class = if !config.general.enabled {
        "disabled"
    } else if successful {
        "success"
    } else if interrupted {
        "interrupted"
    } else if neutral {
        "neutral"
    } else if !suggestions.is_empty() {
        "correctable"
    } else {
        "unknown"
    };
    let failures = if successful || interrupted || neutral || !config.general.enabled {
        0
    } else {
        request.consecutive_failures.saturating_add(1)
    };
    let mood = if !config.general.enabled || interrupted || neutral {
        Mood::Idle
    } else if successful {
        if is_milestone(&request.command) {
            Mood::Proud
        } else {
            Mood::Happy
        }
    } else if failures >= 3 {
        Mood::Concerned
    } else {
        Mood::Annoyed
    };
    let help = failures == 3 && config.interaction.consecutive_failure_tip;
    let candidate = persona::event_message(
        config,
        mood,
        if help { "help" } else { failure_class },
        failures,
    );
    let after_cooldown = request.last_interaction_ms == 0
        || request.now_ms.saturating_sub(request.last_interaction_ms)
            >= config.interaction.cooldown_seconds.saturating_mul(1000);
    let correction_priority = failure_class == "correctable";
    let sampled = !successful
        || config.interaction.profile == "chatty"
        || request.sample < f64::from(config.interaction.success_probability);
    let message = if config.general.enabled
        && config.interaction.profile != "quiet"
        && (correction_priority || help || after_cooldown)
        && sampled
    {
        candidate
    } else {
        String::new()
    };
    EventResponse {
        protocol_version: 1,
        mood: mood.as_str().to_string(),
        consecutive_failures: failures,
        failure_class: failure_class.to_string(),
        message,
        suggestions,
        prompt_marker: persona::marker(mood, config.prompt.ascii_fallback),
    }
}

fn is_neutral_result(command: &str, exit_code: i32) -> bool {
    if exit_code != 1 {
        return false;
    }
    // Deliberately avoid guessing the exit semantics of compound/quoted input.
    if !correction::is_simple_command(command) {
        return false;
    }
    matches!(
        command.split_whitespace().next(),
        Some("grep" | "rg" | "diff" | "test" | "[")
    )
}

fn is_milestone(command: &str) -> bool {
    let words: Vec<_> = command.split_whitespace().collect();
    matches!(
        words.as_slice(),
        ["cargo", "test" | "check" | "clippy", ..] | ["git", "commit", ..]
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(command: &str, code: i32, failures: u32) -> EventRequest {
        EventRequest {
            command: command.into(),
            exit_code: code,
            consecutive_failures: failures,
            now_ms: 100_000,
            last_interaction_ms: 0,
            sample: 0.0,
        }
    }
    #[test]
    fn distinguishes_expected_nonzero_from_errors() {
        assert_eq!(
            event(request("grep missing file", 1, 2), &Config::default()).failure_class,
            "neutral"
        );
        assert_eq!(
            event(request("grep missing file", 2, 2), &Config::default()).failure_class,
            "unknown"
        );
        assert_eq!(
            event(request("grep x file | cat", 1, 0), &Config::default()).failure_class,
            "unknown"
        );
    }
    #[test]
    fn feedback_recovers_after_cooldown() {
        let config = Config::default();
        let mut req = request("false", 1, 2);
        req.last_interaction_ms = 99_000;
        assert!(event(req.clone(), &config).message.contains("连续失败 3"));
        req.consecutive_failures = 3;
        assert!(event(req.clone(), &config).message.is_empty());
        req.now_ms = 120_000;
        assert!(!event(req, &config).message.is_empty());
    }
    #[test]
    fn interrupt_resets_counter() {
        assert_eq!(
            event(request("sleep 1", 130, 7), &Config::default()).consecutive_failures,
            0
        );
    }
}
