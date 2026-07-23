use std::error::Error;
use std::fmt;

const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}

impl fmt::Display for IdError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid {}: {}", self.kind, self.reason)
    }
}

impl Error for IdError {}

fn parse_id(kind: &'static str, value: &str, max_len: usize) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > max_len {
        return Err(IdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b':' | b'.'))
    {
        return Err(IdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! id_type {
    ($name:ident, $kind:literal, $max_len:expr) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);

        impl $name {
            pub fn parse(value: &str) -> Result<Self, IdError> {
                parse_id($kind, value, $max_len).map(Self)
            }

            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(SourceChannelId, "source channel id", MAX_ID_LEN);
id_type!(ObservationRequestId, "observation request id", MAX_ID_LEN);
id_type!(ObservationId, "observation id", 80);
id_type!(DiagnosticId, "diagnostic id", 80);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObservationRequest {
    pub request_id: ObservationRequestId,
    pub source_channel_id: SourceChannelId,
}

impl ObservationRequest {
    pub fn new(request_id: ObservationRequestId, source_channel_id: SourceChannelId) -> Self {
        Self {
            request_id,
            source_channel_id,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TransportOutcome {
    Unavailable,
    Timeout,
    Cancelled,
    TransportOrTlsFailure,
    AccessRestricted,
    Completed,
}

impl TransportOutcome {
    pub fn diagnostic_category(self) -> &'static str {
        match self {
            Self::Unavailable => "unavailable",
            Self::Timeout => "timeout",
            Self::Cancelled => "cancelled",
            Self::TransportOrTlsFailure => "transport-or-tls-failure",
            Self::AccessRestricted => "access-restricted",
            Self::Completed => "completed",
        }
    }

    pub fn retryable(self) -> bool {
        matches!(
            self,
            Self::Unavailable | Self::Timeout | Self::TransportOrTlsFailure
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialObservationSummary {
    byte_count: usize,
    fingerprint: String,
}

impl PartialObservationSummary {
    pub fn none() -> Self {
        Self {
            byte_count: 0,
            fingerprint: String::new(),
        }
    }

    pub fn byte_count(&self) -> usize {
        self.byte_count
    }

    pub fn fingerprint(&self) -> &str {
        &self.fingerprint
    }

    pub fn from_bytes(bytes: &[u8]) -> Self {
        // FNV-1a is used only as a deterministic diagnostic fingerprint. It is
        // not an integrity, identity, authority, or cryptographic digest.
        let mut hash = 0xcbf29ce484222325_u64;
        for byte in bytes {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(0x100000001b3);
        }
        Self {
            byte_count: bytes.len(),
            fingerprint: format!("fnv1a64:{hash:016x}"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransportObservation {
    pub outcome: TransportOutcome,
    pub partial: PartialObservationSummary,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkPhase {
    Started,
    ObservationFailed,
    ObservationCompleted,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkTransition {
    pub request_id: ObservationRequestId,
    pub phase: WorkPhase,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiagnosticCode(&'static str);

impl DiagnosticCode {
    pub(crate) fn new(value: &'static str) -> Self {
        Self(value)
    }

    pub fn as_str(&self) -> &str {
        self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiagnosticEvent {
    pub diagnostic_id: DiagnosticId,
    pub observation_id: ObservationId,
    pub source_channel_id: SourceChannelId,
    pub phase: DiagnosticCode,
    pub category: DiagnosticCode,
    pub retryable: bool,
    pub partial_byte_count: usize,
    pub partial_fingerprint: String,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct AuthorityAbsence {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegalClockAnchor {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicationIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObserveSourceResult {
    pub observation_id: ObservationId,
    pub transport_outcome: TransportOutcome,
    pub work_trace: Vec<WorkTransition>,
    pub diagnostics: Vec<DiagnosticEvent>,
    pub authority: AuthorityAbsence,
    pub legal_clock_anchor: Option<LegalClockAnchor>,
    pub promotion_id: Option<PromotionIdentity>,
    pub publication_id: Option<PublicationIdentity>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identifiers_reject_empty_long_or_unsafe_values() {
        assert!(SourceChannelId::parse("").is_err());
        assert!(ObservationRequestId::parse(&"x".repeat(MAX_ID_LEN + 1)).is_err());
        assert!(ObservationId::parse("contains space").is_err());
        assert!(DiagnosticId::parse("contains/slash").is_err());
    }

    #[test]
    fn partial_summary_is_deterministic_and_payload_free() {
        let payload = b"PARTIAL-SECRET-LEGAL-TEXT";
        let first = PartialObservationSummary::from_bytes(payload);
        let second = PartialObservationSummary::from_bytes(payload);

        assert_eq!(first, second);
        assert_eq!(first.byte_count(), payload.len());
        assert_eq!(first.fingerprint(), "fnv1a64:4506db77c0be12b7");
        assert!(!format!("{first:?}").contains("PARTIAL-SECRET-LEGAL-TEXT"));
    }
}
