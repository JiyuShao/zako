use serde::{Deserialize, Serialize};
use std::env;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub general: General,
    pub interaction: Interaction,
    pub persona: Persona,
    pub prompt: Prompt,
    pub correction: Correction,
    pub privacy: Privacy,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct General {
    pub enabled: bool,
    pub language: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Interaction {
    pub profile: String,
    pub success_probability: f32,
    pub cooldown_seconds: u64,
    pub startup_greeting: bool,
    pub consecutive_failure_tip: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Persona {
    pub style: String,
    pub nickname: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Prompt {
    pub mode: String,
    pub ascii_fallback: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Correction {
    pub enabled: bool,
    pub max_suggestions: usize,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Privacy {
    pub persist_command_history: bool,
    pub telemetry: bool,
    pub capture_command_output: bool,
}

impl Default for General {
    fn default() -> Self {
        Self {
            enabled: true,
            language: "zh-CN".to_string(),
        }
    }
}

impl Default for Interaction {
    fn default() -> Self {
        Self {
            profile: "active".to_string(),
            success_probability: 0.35,
            cooldown_seconds: 20,
            startup_greeting: true,
            consecutive_failure_tip: true,
        }
    }
}

impl Default for Persona {
    fn default() -> Self {
        Self {
            style: "normal".to_string(),
            nickname: "杂鱼".to_string(),
        }
    }
}

impl Default for Prompt {
    fn default() -> Self {
        Self {
            mode: "auto".to_string(),
            ascii_fallback: true,
        }
    }
}

impl Default for Correction {
    fn default() -> Self {
        Self {
            enabled: true,
            max_suggestions: 3,
        }
    }
}

#[derive(Debug)]
pub enum ConfigError {
    Read {
        path: PathBuf,
        source: std::io::Error,
    },
    Parse {
        path: PathBuf,
        source: toml::de::Error,
    },
    Invalid(String),
}

impl Display for ConfigError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Read { path, source } => {
                write!(formatter, "无法读取配置 {}: {source}", path.display())
            }
            Self::Parse { path, source } => {
                write!(formatter, "配置 {} 无法解析: {source}", path.display())
            }
            Self::Invalid(message) => formatter.write_str(message),
        }
    }
}

impl std::error::Error for ConfigError {}

impl Config {
    pub fn path() -> PathBuf {
        if let Ok(directory) = env::var("ZAKO_CONFIG_DIR") {
            return PathBuf::from(directory).join("config.toml");
        }
        if let Ok(directory) = env::var("XDG_CONFIG_HOME") {
            return PathBuf::from(directory).join("zako/config.toml");
        }
        if let Ok(home) = env::var("HOME") {
            return PathBuf::from(home).join(".config/zako/config.toml");
        }
        PathBuf::from("config.toml")
    }

    pub fn load() -> Result<Self, ConfigError> {
        let path = Self::path();
        let source = match fs::read_to_string(&path) {
            Ok(source) => source,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                return Ok(Self::default())
            }
            Err(source) => {
                return Err(ConfigError::Read {
                    path: path.clone(),
                    source,
                })
            }
        };
        let config: Self =
            toml::from_str(&source).map_err(|source| ConfigError::Parse { path, source })?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.general.language != "zh-CN" {
            return Err(ConfigError::Invalid(
                "M1 只支持 general.language = zh-CN".to_string(),
            ));
        }
        if self.persona.nickname.chars().count() > 64
            || self.persona.nickname.chars().any(char::is_control)
        {
            return Err(ConfigError::Invalid(
                "persona.nickname 必须不超过 64 字且不包含控制字符".to_string(),
            ));
        }
        if self.interaction.cooldown_seconds > 86_400 {
            return Err(ConfigError::Invalid(
                "cooldown_seconds 必须不超过 86400".to_string(),
            ));
        }
        if !(0.0..=1.0).contains(&self.interaction.success_probability) {
            return Err(ConfigError::Invalid(
                "interaction.success_probability 必须在 0 到 1 之间".to_string(),
            ));
        }
        if self.correction.max_suggestions == 0 || self.correction.max_suggestions > 3 {
            return Err(ConfigError::Invalid(
                "correction.max_suggestions 必须在 1 到 3 之间".to_string(),
            ));
        }
        if !["quiet", "active", "chatty"].contains(&self.interaction.profile.as_str()) {
            return Err(ConfigError::Invalid(
                "interaction.profile 必须是 quiet、active 或 chatty".to_string(),
            ));
        }
        if !["gentle", "normal", "spicy"].contains(&self.persona.style.as_str()) {
            return Err(ConfigError::Invalid(
                "persona.style 必须是 gentle、normal 或 spicy".to_string(),
            ));
        }
        if !["auto", "off"].contains(&self.prompt.mode.as_str()) {
            return Err(ConfigError::Invalid(
                "prompt.mode 必须是 auto 或 off".to_string(),
            ));
        }
        if self.privacy.persist_command_history
            || self.privacy.telemetry
            || self.privacy.capture_command_output
        {
            return Err(ConfigError::Invalid(
                "M1 必须关闭命令历史持久化、遥测和命令输出捕获".to_string(),
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::Config;

    #[test]
    fn defaults_are_offline_and_conservative() {
        let config = Config::default();
        assert!(config.general.enabled);
        assert!(!config.privacy.telemetry);
        assert!(!config.privacy.persist_command_history);
        assert_eq!(config.correction.max_suggestions, 3);
    }
}
