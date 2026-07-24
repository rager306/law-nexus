const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}
impl std::fmt::Display for IdError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "invalid {}: {}", self.kind, self.reason)
    }
}
impl std::error::Error for IdError {}

fn parse_id(kind: &'static str, value: &str) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > MAX_ID_LEN {
        return Err(IdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.'))
    {
        return Err(IdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! id_type {
    ($name:ident, $kind:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);
        impl $name {
            pub fn parse(value: &str) -> Result<Self, IdError> {
                parse_id($kind, value).map(Self)
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(SinkId, "sink id");
id_type!(DiagnosticId, "diagnostic id");

pub const DIAGNOSTIC_POLICY_VERSION: &str = "hc19:safe-diagnostics:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiagnosticOutcome {
    Emitted,
    Redacted,
    Blocked,
    Failed,
}

impl DiagnosticOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Emitted => "emitted",
            Self::Redacted => "redacted",
            Self::Blocked => "blocked",
            Self::Failed => "failed",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiagnosticEntry {
    pub diagnostic_id: DiagnosticId,
    pub sink: SinkId,
    pub content: String,
    pub contains_secret: bool,
    pub contains_raw_legal_text: bool,
    pub contains_injection: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiagnosticResult {
    pub outcome: DiagnosticOutcome,
    pub diagnostic_id: DiagnosticId,
    pub emitted_content: Option<String>,
    pub policy_version: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn outcomes() {
        assert_eq!(DiagnosticOutcome::Emitted.as_str(), "emitted");
        assert_eq!(DiagnosticOutcome::Blocked.as_str(), "blocked");
    }
}
