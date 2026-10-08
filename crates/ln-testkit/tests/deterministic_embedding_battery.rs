//! Determinism and hostile-input battery for the M215 S03 test port.
//!
//! This suite pins the byte-for-byte reproducibility contract of
//! [`ln_testkit::deterministic_vector`] and [`ln_testkit::DeterministicEmbedding`]
//! and the closed input-error vocabulary at the port boundary:
//!
//! - the same `(text, dimensions)` input yields byte-identical `Vec<f32>` on
//!   repeated calls, across independently constructed embedders, and across
//!   separate CI processes (the printed `DETERMINISTIC_VECTOR_DIGEST` line must
//!   match);
//! - distinct inputs yield distinct digests;
//! - every component is finite and lies in `[-1.0, 1.0)`;
//! - malformed and hostile input (`NUL`/control characters, oversized text,
//!   zero or oversized dimensions, model drift, dimension mismatch) fails
//!   closed through the closed `StorageError` vocabulary;
//! - the port composes with S01 provenance and satisfies the shared artifact
//!   contract.
//!
//! Non-claim: the golden pin is a drift detector for the output stream, not a
//! proof that the vector is semantically correct or retrieval-useful. No
//! network, no weights, no randomness, no new dependencies.
//!
//! Lifecycle: `[bounded]` deterministic test-support battery.

use std::collections::HashSet;

use ln_storage::{
    EmbeddingArtifactPort, EmbeddingArtifactRequest, EmbeddingPort, EmbeddingRequest,
    ModelProvenance, ProvenancedEmbedding, StorageError,
};
use ln_testkit::{
    assert_embedding_artifact_port_contract, deterministic_vector, DeterministicEmbedding,
    MAX_DETERMINISTIC_DIMENSIONS, MAX_DETERMINISTIC_INPUT_BYTES,
};

/// Known input for the golden pin.
const GOLDEN_TEXT: &str = "m215-s03 golden embedding fixture";
/// Dimensions for the golden pin.
const GOLDEN_DIMENSIONS: usize = 16;
/// FNV-1a 64 over the little-endian `f32::to_bits()` bytes of the golden vector.
///
/// Drift detector only: if the deterministic stream changes, this constant
/// trips and CI must consciously re-pin. It does not assert vector quality.
const GOLDEN_VECTOR_DIGEST: u64 = 0x4b86_fa6d_ed99_5e38;

/// Raw bit patterns, so equality is exact and `NaN` would be caught.
fn bits(vector: &[f32]) -> Vec<u32> {
    vector.iter().map(|value| value.to_bits()).collect()
}

/// FNV-1a (64-bit) over little-endian `value.to_bits()` bytes of a vector.
fn vector_digest(vector: &[f32]) -> u64 {
    const BASIS: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;
    let mut hash = BASIS;
    for value in vector {
        for byte in value.to_bits().to_le_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(PRIME);
        }
    }
    hash
}

fn request(model_id: &str, dimensions: usize, text: &str) -> EmbeddingRequest {
    EmbeddingRequest::try_new(text, model_id, dimensions).expect("valid request fixture")
}

fn provenance(dimensions: usize) -> ModelProvenance {
    ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &format!("sha256:{}", "a".repeat(64)),
        dimensions,
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ],
    )
    .expect("valid provenance")
}

#[test]
fn deterministic_vector_is_byte_identical_across_calls() {
    let first = deterministic_vector("deterministic fixture text", 32);
    let second = deterministic_vector("deterministic fixture text", 32);
    assert_eq!(
        bits(&first),
        bits(&second),
        "repeated deterministic_vector calls must agree byte-for-byte"
    );
}

#[test]
fn independently_constructed_embedders_agree_byte_for_byte() {
    let left = DeterministicEmbedding::try_new("det-model", 32).expect("valid embedder");
    let right = DeterministicEmbedding::try_new("det-model", 32).expect("valid embedder");
    let left_vector = left
        .embed(&request("det-model", 32, "deterministic fixture text"))
        .expect("valid embed")
        .vector()
        .to_vec();
    let right_vector = right
        .embed(&request("det-model", 32, "deterministic fixture text"))
        .expect("valid embed")
        .vector()
        .to_vec();
    assert_eq!(
        bits(&left_vector),
        bits(&right_vector),
        "independently constructed embedders must agree byte-for-byte"
    );
    assert_eq!(
        bits(&left_vector),
        bits(&deterministic_vector("deterministic fixture text", 32)),
        "embedder output must match the raw deterministic stream"
    );
}

#[test]
fn golden_vector_digest_is_pinned() {
    let vector = deterministic_vector(GOLDEN_TEXT, GOLDEN_DIMENSIONS);
    assert_eq!(vector.len(), GOLDEN_DIMENSIONS);
    let digest = vector_digest(&vector);
    // Printed for the cross-process check: two separate `cargo test ...
    // -- --nocapture` runs must emit the same line.
    println!("DETERMINISTIC_VECTOR_DIGEST={digest:016x}");
    assert_eq!(
        digest, GOLDEN_VECTOR_DIGEST,
        "deterministic output drifted; re-pin GOLDEN_VECTOR_DIGEST consciously"
    );
}

#[test]
fn distinct_inputs_yield_distinct_digests() {
    let inputs = [
        "alpha",
        "beta",
        "gamma",
        "alpha ",
        "ALPHA",
        "кириллица",
        "alpha.beta,gamma!",
    ];
    let mut digests = HashSet::new();
    for input in inputs {
        let digest = vector_digest(&deterministic_vector(input, 16));
        assert!(
            digests.insert(digest),
            "input {input:?} collided with an earlier input digest {digest:016x}"
        );
    }
    // Dimensions participate in the digest too.
    let same_text_small = vector_digest(&deterministic_vector("alpha", 8));
    let same_text_large = vector_digest(&deterministic_vector("alpha", 64));
    assert_ne!(same_text_small, same_text_large);
}

#[test]
fn vectors_are_finite_and_in_range_across_input_matrix() {
    let long_ascii = "a".repeat(4096);
    let inputs: [&str; 5] = [
        "plain ascii input",
        "русский текст для проверки",
        long_ascii.as_str(),
        "line one\nline two\nline three",
        "punctuation: !@#$%^&*()[]{};:',.<>/?|`~",
    ];
    for input in inputs {
        for dimensions in [1_usize, 8, 16, 1024] {
            let vector = deterministic_vector(input, dimensions);
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
}

#[test]
fn control_character_is_rejected_with_label() {
    let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
    assert_eq!(
        embedder.embed(&request("det-model", 8, "hostile\u{0}text")),
        Err(StorageError::InvalidInput("control-character"))
    );
    // A second control character class (ESC, U+001B) is rejected the same way.
    assert_eq!(
        embedder.embed(&request("det-model", 8, "escape\u{1b}sequence")),
        Err(StorageError::InvalidInput("control-character"))
    );
    // Tab, newline and carriage return are permitted (not control-rejected).
    assert!(embedder
        .embed(&request("det-model", 8, "line one\nline two\ttabbed\r"))
        .is_ok());
}

#[test]
fn oversized_input_is_rejected_with_label() {
    let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
    let oversized = "a".repeat(MAX_DETERMINISTIC_INPUT_BYTES + 1);
    assert_eq!(
        embedder.embed(&request("det-model", 8, &oversized)),
        Err(StorageError::InvalidInput("input-too-large"))
    );
    // Exactly at the boundary is accepted.
    let at_bound = "a".repeat(MAX_DETERMINISTIC_INPUT_BYTES);
    assert!(embedder.embed(&request("det-model", 8, &at_bound)).is_ok());
}

#[test]
fn zero_and_oversized_dimensions_are_rejected() {
    assert_eq!(
        DeterministicEmbedding::try_new("det-model", 0).err(),
        Some(StorageError::EmptyInput)
    );
    assert_eq!(
        DeterministicEmbedding::try_new("det-model", MAX_DETERMINISTIC_DIMENSIONS + 1).err(),
        Some(StorageError::InvalidInput("dimensions-too-large"))
    );
    // The exact upper bound is allowed.
    assert!(DeterministicEmbedding::try_new("det-model", MAX_DETERMINISTIC_DIMENSIONS).is_ok());
}

#[test]
fn model_identity_drift_is_rejected() {
    let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
    assert!(matches!(
        embedder.embed(&request("other-model", 8, "contract text")),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}

#[test]
fn request_dimension_mismatch_is_rejected() {
    let embedder = DeterministicEmbedding::try_new("det-model", 8).expect("valid embedder");
    assert_eq!(
        embedder.embed(&request("det-model", 4, "contract text")),
        Err(StorageError::DimensionMismatch {
            expected: 8,
            actual: 4,
        })
    );
}

#[test]
fn provenanced_composition_satisfies_artifact_contract() {
    let embedder = DeterministicEmbedding::try_new("det-model", 16).expect("valid embedder");
    let port = ProvenancedEmbedding::try_new(embedder, "det-model", provenance(16))
        .expect("valid composition");
    assert_embedding_artifact_port_contract(&port, "det-model", 16);
}

#[test]
fn provenanced_composition_is_deterministic() {
    let embedder = DeterministicEmbedding::try_new("det-model", 16).expect("valid embedder");
    let port = ProvenancedEmbedding::try_new(embedder, "det-model", provenance(16))
        .expect("valid composition");
    let request = EmbeddingArtifactRequest::try_new("doc-1", "deterministic artifact text")
        .expect("valid artifact request");
    let first = port
        .embed_artifact(&request)
        .expect("honest port must yield an artifact");
    let second = port
        .embed_artifact(&request)
        .expect("honest port must yield an artifact");
    assert_eq!(
        bits(first.vector()),
        bits(second.vector()),
        "two embeds of the same request must be byte-identical"
    );
    assert_eq!(
        first.vector(),
        deterministic_vector("deterministic artifact text", 16)
    );
}
