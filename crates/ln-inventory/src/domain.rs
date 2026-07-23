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

id_type!(DropReference, "drop reference", MAX_ID_LEN);
id_type!(InventoryRequestId, "inventory request id", MAX_ID_LEN);
id_type!(ObservationAttemptId, "observation attempt id", 80);
id_type!(InventoryItemId, "inventory item id", 80);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InventoryRequest {
    pub request_id: InventoryRequestId,
    pub drop_reference: DropReference,
    input_digest: String,
}

impl InventoryRequest {
    pub fn new(
        request_id: InventoryRequestId,
        drop_reference: DropReference,
        bytes: &[u8],
    ) -> Self {
        Self {
            request_id,
            drop_reference,
            input_digest: digest_bytes(bytes),
        }
    }

    pub fn input_digest(&self) -> &str {
        &self.input_digest
    }
}

pub fn digest_bytes(bytes: &[u8]) -> String {
    // FNV-1a is used only as a deterministic synthetic integrity fingerprint.
    // It is not a cryptographic or legal authority digest.
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("fnv1a64:{hash:016x}")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InventoryDisposition {
    Pending,
    ReviewRequired,
    IntegrityFailed,
    MetadataMismatch,
    AmbiguousIdentity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InventoryVisibility {
    InventoryReview,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObservationAttempt {
    pub attempt_id: ObservationAttemptId,
    pub request_id: InventoryRequestId,
    pub drop_reference: DropReference,
    pub input_digest: String,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CuratedLabel {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CurrentLabel {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PromotionIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InventoryResult {
    pub item_id: InventoryItemId,
    pub input_digest: String,
    pub disposition: InventoryDisposition,
    pub visibility: InventoryVisibility,
    pub observation_attempts: Vec<ObservationAttempt>,
    pub curated_label: Option<CuratedLabel>,
    pub current_label: Option<CurrentLabel>,
    pub promotion_id: Option<PromotionIdentity>,
    pub publication_id: Option<PublicationIdentity>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn digest_is_deterministic_and_payload_free() {
        let bytes = b"SYNTHETIC-IMMUTABLE-DROP-D1";
        let first = digest_bytes(bytes);
        let second = digest_bytes(bytes);
        assert_eq!(first, second);
        assert!(first.starts_with("fnv1a64:"));
        assert!(!format!("{first:?}").contains("SYNTHETIC-IMMUTABLE-DROP-D1"));
    }

    #[test]
    fn identifiers_reject_empty_or_unsafe_values() {
        assert!(DropReference::parse("").is_err());
        assert!(InventoryRequestId::parse("bad id").is_err());
        assert!(ObservationAttemptId::parse("contains/slash").is_err());
    }
}
