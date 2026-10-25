//! Deterministic, dependency-free test port for embeddings (M215 S03).
//!
//! This module is shared test support (`publish = false`), not a product
//! provider. It gives CI a byte-identical vector for a fixed (text,
//! dimensions) input on any platform and toolchain, without network, weights
//! or a random source, and it rejects malformed or hostile input through the
//! closed [`StorageError::InvalidInput`] vocabulary.
//!
//! Determinism contract:
//! - the same `text` and `dimensions` always produce byte-identical `Vec<f32>`
//!   (compared via [`f32::to_bits`]);
//! - every component is finite and lies in `[-1.0, 1.0)`;
//! - the vector is not normalised (retrieval quality is explicitly a
//!   non-claim; this is a determinism fixture, not a semantic model).
//!
//! Lifecycle: `[bounded]` test-support preparation. Not live model validation.

use ln_storage::adapters::tei::{EmbeddingTransport, TransportError};
use ln_storage::{EmbeddingPort, EmbeddingRequest, EmbeddingResponse, StorageError};

/// Upper bound on accepted UTF-8 input length in bytes.
pub const MAX_DETERMINISTIC_INPUT_BYTES: usize = 64 * 1024;

/// Upper bound on accepted vector dimensionality.
pub const MAX_DETERMINISTIC_DIMENSIONS: usize = 65_536;

/// FNV-1a (64-bit) over raw bytes. Used to seed the component stream.
fn fnv1a64(bytes: &[u8]) -> u64 {
    const BASIS: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;
    let mut hash = BASIS;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(PRIME);
    }
    hash
}

/// SplitMix64 step: advances `state` and returns the mixed output.
fn splitmix64(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

/// Closed input-validation vocabulary shared by the port and transport seams.
///
/// Labels are static strings: no caller text, server text or secret ever enters
/// an error value (redaction by construction).
fn validate_text(text: &str) -> Result<(), &'static str> {
    if text.trim().is_empty() {
        return Err("empty");
    }
    if text.len() > MAX_DETERMINISTIC_INPUT_BYTES {
        return Err("input-too-large");
    }
    if text
        .chars()
        .any(|character| character.is_control() && !matches!(character, '\t' | '\n' | '\r'))
    {
        return Err("control-character");
    }
    Ok(())
}

/// Deterministic vector for `text` with `dimensions` components.
///
/// The stream is seeded from [`fnv1a64`] over the input bytes and then drawn
/// with [`splitmix64`]. Each component uses the top 24 bits of a draw, so the
/// mapping `(hi / 2^23) - 1.0` is exact in `f32` and lands in `[-1.0, 1.0)`.
/// The same `text` and `dimensions` yield byte-identical output on any
/// platform or toolchain; values are never `NaN` or `Inf`; the vector is not
/// normalised (quality is a non-claim).
pub fn deterministic_vector(text: &str, dimensions: usize) -> Vec<f32> {
    let mut state = fnv1a64(text.as_bytes());
    let mut vector = Vec::with_capacity(dimensions);
    for _ in 0..dimensions {
        let draw = splitmix64(&mut state);
        let high = (draw >> 40) as u32;
        vector.push((high as f32) / 8_388_608.0 - 1.0);
    }
    vector
}

/// Deterministic `EmbeddingPort` implementation for CI and contract suites.
///
/// Constructed only through [`DeterministicEmbedding::try_new`], which rejects
/// an empty model id, zero dimensions and dimensions above
/// [`MAX_DETERMINISTIC_DIMENSIONS`].
pub struct DeterministicEmbedding {
    model_id: String,
    dimensions: usize,
}

impl DeterministicEmbedding {
    /// Build a deterministic embedder, fail-closed on invalid bounds.
    pub fn try_new(model_id: &str, dimensions: usize) -> Result<Self, StorageError> {
        if model_id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if dimensions == 0 {
            return Err(StorageError::EmptyInput);
        }
        if dimensions > MAX_DETERMINISTIC_DIMENSIONS {
            return Err(StorageError::InvalidInput("dimensions-too-large"));
        }
        Ok(Self {
            model_id: model_id.to_owned(),
            dimensions,
        })
    }

    /// Declared model identity.
    pub fn model_id(&self) -> &str {
        &self.model_id
    }

    /// Declared vector dimensionality.
    pub fn dimensions(&self) -> usize {
        self.dimensions
    }
}

impl EmbeddingPort for DeterministicEmbedding {
    fn embed(&self, request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        if request.model_id() != self.model_id {
            return Err(StorageError::ModelIdentityDrift {
                expected: self.model_id.clone(),
                actual: request.model_id().to_owned(),
            });
        }
        if request.expected_dimensions() != self.dimensions {
            return Err(StorageError::DimensionMismatch {
                expected: self.dimensions,
                actual: request.expected_dimensions(),
            });
        }
        if let Err(reason) = validate_text(request.text()) {
            return Err(StorageError::InvalidInput(reason));
        }
        EmbeddingResponse::try_new(
            &self.model_id,
            deterministic_vector(request.text(), self.dimensions),
        )
    }
}

/// Deterministic [`EmbeddingTransport`] so the TEI adapter seam can be driven
/// in CI without a socket.
///
/// Hostile input is rejected on the transport boundary as
/// [`TransportError::BadResponse`] with a static label; the adapter maps that to
/// the closed [`StorageError::TransportBadResponse`], so the payload is dropped
/// at the boundary and never reaches an artifact.
pub struct DeterministicEmbeddingTransport {
    dimensions: usize,
}

impl DeterministicEmbeddingTransport {
    /// Build a deterministic transport, fail-closed on invalid bounds.
    pub fn new(dimensions: usize) -> Result<Self, StorageError> {
        if dimensions == 0 {
            return Err(StorageError::EmptyInput);
        }
        if dimensions > MAX_DETERMINISTIC_DIMENSIONS {
            return Err(StorageError::InvalidInput("dimensions-too-large"));
        }
        Ok(Self { dimensions })
    }

    /// Declared vector dimensionality.
    pub fn dimensions(&self) -> usize {
        self.dimensions
    }
}

impl EmbeddingTransport for DeterministicEmbeddingTransport {
    fn embed_text(&self, text: &str) -> Result<Vec<f32>, TransportError> {
        if let Err(reason) = validate_text(text) {
            return Err(TransportError::BadResponse(reason.to_owned()));
        }
        Ok(deterministic_vector(text, self.dimensions))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bits(vector: &[f32]) -> Vec<u32> {
        vector.iter().map(|value| value.to_bits()).collect()
    }

    fn request(model_id: &str, dimensions: usize, text: &str) -> EmbeddingRequest {
        EmbeddingRequest::try_new(text, model_id, dimensions).expect("valid request fixture")
    }

    #[test]
    fn vector_is_byte_identical_across_calls_and_instances() {
        let first = deterministic_vector("deterministic fixture text", 32);
        let second = deterministic_vector("deterministic fixture text", 32);
        assert_eq!(bits(&first), bits(&second));

        let left = DeterministicEmbedding::try_new("det-model", 32).expect("valid embedder");
        let right = DeterministicEmbedding::try_new("det-model", 32).expect("valid embedder");
        let left_response = left
            .embed(&request("det-model", 32, "deterministic fixture text"))
            .expect("valid embed");
        let right_response = right
            .embed(&request("det-model", 32, "deterministic fixture text"))
            .expect("valid embed");
        assert_eq!(
            bits(left_response.vector()),
            bits(right_response.vector()),
            "independently constructed embedders must agree byte-for-byte"
        );
        assert_eq!(bits(left_response.vector()), bits(&first));
    }

    #[test]
    fn vector_is_finite_and_in_range() {
        for dimensions in [1_usize, 8, 16, 1024] {
            let vector = deterministic_vector("range fixture", dimensions);
            assert_eq!(vector.len(), dimensions);
            for value in &vector {
                assert!(value.is_finite(), "component must be finite");
                assert!(
                    (-1.0..1.0).contains(value),
                    "component {value} must lie in [-1.0, 1.0)"
                );
            }
        }
    }

    #[test]
    fn distinct_inputs_yield_distinct_vectors() {
        let a = bits(&deterministic_vector("alpha", 16));
        let b = bits(&deterministic_vector("beta", 16));
        let c = bits(&deterministic_vector("alpha", 17));
        assert_ne!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn empty_and_whitespace_text_are_rejected() {
        let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
        // EmbeddingRequest::try_new itself rejects blank text first.
        assert_eq!(
            EmbeddingRequest::try_new("   ", "det-model", 8),
            Err(StorageError::EmptyInput)
        );
        assert_eq!(
            DeterministicEmbedding::try_new("   ", 8).err(),
            Some(StorageError::EmptyInput)
        );
        let _ = embedder;
        assert_eq!(
            validate_text(""),
            Err("empty"),
            "blank text must map to the empty label"
        );
        assert_eq!(validate_text(" \t\n "), Err("empty"));
    }

    #[test]
    fn control_character_is_rejected_with_label() {
        let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
        assert_eq!(
            embedder.embed(&request("det-model", 8, "hostile\u{0}text")),
            Err(StorageError::InvalidInput("control-character"))
        );
        let transport = DeterministicEmbeddingTransport::new(8).expect("valid transport");
        assert_eq!(
            transport.embed_text("hostile\u{0}text"),
            Err(TransportError::BadResponse("control-character".to_owned()))
        );
        // Tab, newline and carriage return are permitted.
        assert!(validate_text("line one\nline two\ttabbed\r").is_ok());
    }

    #[test]
    fn oversized_input_is_rejected_with_label() {
        let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
        let oversized = "a".repeat(MAX_DETERMINISTIC_INPUT_BYTES + 1);
        assert_eq!(
            embedder.embed(&request("det-model", 8, &oversized)),
            Err(StorageError::InvalidInput("input-too-large"))
        );
        assert_eq!(validate_text(&oversized), Err("input-too-large"));
    }

    #[test]
    fn dimension_bounds_are_enforced() {
        assert_eq!(
            DeterministicEmbedding::try_new("det-model", 0).err(),
            Some(StorageError::EmptyInput)
        );
        assert_eq!(
            DeterministicEmbedding::try_new("det-model", MAX_DETERMINISTIC_DIMENSIONS + 1).err(),
            Some(StorageError::InvalidInput("dimensions-too-large"))
        );
        assert_eq!(
            DeterministicEmbeddingTransport::new(0).err(),
            Some(StorageError::EmptyInput)
        );
        assert_eq!(
            DeterministicEmbeddingTransport::new(MAX_DETERMINISTIC_DIMENSIONS + 1).err(),
            Some(StorageError::InvalidInput("dimensions-too-large"))
        );
        assert!(DeterministicEmbedding::try_new("det-model", MAX_DETERMINISTIC_DIMENSIONS).is_ok());
    }

    #[test]
    fn invalid_input_display_carries_static_label_only() {
        assert_eq!(
            StorageError::InvalidInput("control-character").to_string(),
            "invalid input: control-character"
        );
        assert_eq!(
            StorageError::InvalidInput("input-too-large").to_string(),
            "invalid input: input-too-large"
        );
    }

    #[test]
    fn model_drift_and_dimension_mismatch_are_rejected() {
        let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
        assert!(matches!(
            embedder.embed(&request("other-model", 8, "text")),
            Err(StorageError::ModelIdentityDrift { .. })
        ));
        assert!(matches!(
            embedder.embed(&request("det-model", 4, "text")),
            Err(StorageError::DimensionMismatch { .. })
        ));
    }
}
