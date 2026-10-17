use crate::context::Suggestion;
use std::{collections::BTreeSet, env, fs, path::Path};

// M1 intentionally limits fuzzy executable matches to familiar low-risk tools.
const CANDIDATES: &[&str] = &[
    "git", "cargo", "ls", "pwd", "echo", "cat", "cut", "cal", "grep", "rg", "find", "head", "tail",
    "wc", "sort", "uniq", "which", "whoami", "date", "diff",
];

pub fn suggest(raw: &str, max: usize) -> Vec<Suggestion> {
    suggest_for_exit(raw, max, 127)
}

pub fn suggest_for_exit(raw: &str, max: usize, exit_code: i32) -> Vec<Suggestion> {
    if max == 0 || !is_simple_command(raw) {
        return Vec::new();
    }
    let tokens: Vec<_> = raw.split_whitespace().collect();
    if is_high_risk(&tokens) {
        return Vec::new();
    }
    if tokens.len() >= 2 && tokens[0] == "git" {
        let replacement = match tokens[1] {
            "comit" => Some("commit"),
            "chekout" => Some("checkout"),
            "sttaus" | "stauts" => Some("status"),
            "brnach" => Some("branch"),
            _ => None,
        };
        if let Some(value) = replacement {
            let mut fixed = tokens.clone();
            fixed[1] = value;
            if !is_high_risk(&fixed) {
                return vec![suggestion(
                    fixed.join(" "),
                    format!("git 子命令可能是 {value}"),
                    0.98,
                )];
            }
        }
        return Vec::new();
    }
    if exit_code != 127
        || command_exists(tokens[0])
        || tokens[0].len() < 3
        || tokens[0].contains('/')
    {
        return Vec::new();
    }
    if tokens[0] == "gti" && command_exists("git") {
        let mut fixed = tokens.clone();
        fixed[0] = "git";
        return if is_high_risk(&fixed) {
            Vec::new()
        } else {
            vec![suggestion(fixed.join(" "), "命令名可能是 git".into(), 0.98)]
        };
    }
    let available = executable_names();
    let mut ranked: Vec<_> = CANDIDATES
        .iter()
        .filter(|name| available.contains(**name))
        .filter_map(|name| {
            let distance = edit_distance(tokens[0], name);
            (distance == 1).then_some((distance, *name))
        })
        .collect();
    ranked.sort();
    ranked
        .into_iter()
        .filter_map(|(_, name)| {
            let mut fixed = tokens.clone();
            fixed[0] = name;
            (!is_high_risk(&fixed))
                .then(|| suggestion(fixed.join(" "), format!("命令名可能是 {name}"), 0.96))
        })
        .take(max.min(3))
        .collect()
}

fn suggestion(command: String, reason: String, confidence: f32) -> Suggestion {
    Suggestion {
        command,
        reason,
        confidence,
        risk: "low".into(),
    }
}

pub fn is_simple_command(raw: &str) -> bool {
    let bracket_test = raw.starts_with("[ ") && raw.ends_with(" ]");
    (bracket_test || !raw.contains(['[', ']']))
        && !raw.is_empty()
        && raw.len() <= 4096
        && raw == raw.trim()
        && raw.split(' ').filter(|s| !s.is_empty()).count() <= 8
        && raw.chars().all(|c| {
            !c.is_control()
                && !matches!(
                    c,
                    '|' | '&'
                        | ';'
                        | '<'
                        | '>'
                        | '('
                        | ')'
                        | '$'
                        | '`'
                        | '\\'
                        | '\''
                        | '"'
                        | '*'
                        | '?'
                        | '~'
                        | '{'
                        | '}'
                        | '!'
                )
        })
}

fn is_high_risk(tokens: &[&str]) -> bool {
    tokens.iter().any(|token| {
        matches!(
            Path::new(token).file_name().and_then(|s| s.to_str()),
            Some("sudo" | "su" | "doas" | "rm" | "rmdir" | "chmod" | "chown" | "dd" | "mkfs")
        )
    }) || tokens.iter().any(|t| {
        matches!(
            *t,
            "push"
                | "reset"
                | "clean"
                | "--force"
                | "--force-with-lease"
                | "--hard"
                | "--amend"
                | "--delete"
        ) || (t.starts_with('-')
            && !t.starts_with("--")
            && t.chars().skip(1).any(|c| matches!(c, 'f' | 'D' | 'd')))
    })
}

fn command_exists(command: &str) -> bool {
    env::var_os("PATH")
        .is_some_and(|path| env::split_paths(&path).any(|dir| is_executable(&dir.join(command))))
}
fn executable_names() -> BTreeSet<String> {
    let mut names = BTreeSet::new();
    if let Some(path) = env::var_os("PATH") {
        // Check the small allowlist directly instead of scanning every PATH entry.
        for dir in env::split_paths(&path) {
            for name in CANDIDATES {
                if is_executable(&dir.join(name)) {
                    names.insert((*name).to_string());
                }
            }
        }
    }
    names
}
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    fs::metadata(path)
        .is_ok_and(|metadata| metadata.is_file() && metadata.permissions().mode() & 0o111 != 0)
}
fn edit_distance(left: &str, right: &str) -> usize {
    let mut previous: Vec<usize> = (0..=right.chars().count()).collect();
    for (i, left_char) in left.chars().enumerate() {
        let mut current = vec![i + 1];
        for (j, right_char) in right.chars().enumerate() {
            current.push(
                (current[j] + 1)
                    .min(previous[j + 1] + 1)
                    .min(previous[j] + usize::from(left_char != right_char)),
            );
        }
        previous = current;
    }
    previous.last().copied().unwrap_or_default()
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn syntax_and_risk_boundaries() {
        for command in [
            "gti *",
            "gti $(id)",
            "gti\tstatus",
            "gti 'status'",
            "gti x\n",
        ] {
            assert!(!is_simple_command(command));
        }
        assert!(is_simple_command("gti status"));
        assert!(is_high_risk(&["git", "push", "-uf"]));
        assert!(is_high_risk(&["git", "branch", "-D", "x"]));
    }
}
