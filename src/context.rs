use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Mood {
    Idle,
    Happy,
    Annoyed,
    Concerned,
    Proud,
}

impl Mood {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Happy => "happy",
            Self::Annoyed => "annoyed",
            Self::Concerned => "concerned",
            Self::Proud => "proud",
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Suggestion {
    pub command: String,
    pub reason: String,
    pub confidence: f32,
    pub risk: String,
}

#[derive(Debug, Clone)]
pub struct EventRequest {
    pub command: String,
    pub exit_code: i32,
    pub consecutive_failures: u32,
    pub now_ms: u64,
    pub last_interaction_ms: u64,
    pub sample: f64,
    pub stats: crate::session::State,
}

#[derive(Debug, Clone, Serialize)]
pub struct EventResponse {
    pub protocol_version: u32,
    pub mood: String,
    pub consecutive_failures: u32,
    pub failure_class: String,
    pub message: String,
    pub suggestions: Vec<Suggestion>,
    pub prompt_marker: String,
    pub stats_json: String,
}
