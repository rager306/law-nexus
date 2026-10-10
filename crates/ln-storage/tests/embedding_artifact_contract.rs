//! Contract tests for the embedding artifact and model provenance (M215 S01).
//!
//! The demo contract: an embedding artifact without provenance is rejected.
//! Also covers the determinism of `canonical_string()` and the boundary
//! rejections (empty subject, empty/non-finite vector, malformed weights hash,
//! zero dimensions). Pure value-object checks: no network, no weights, no
//! concrete model. Lifecycle: `[bounded]` contract preparation.

use ln_storage::{EmbeddingArtifact, EmbeddingArtifactRecord, ModelProvenance, StorageError};

fn valid_hash() -> String {
    format!("sha256:{}", "a".repeat(64))
}

fn provenance(dimensions: usize) -> ModelProvenance {
    ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &valid_hash(),
        dimensions,
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ],
    )
    .expect("valid provenance")
}

// --- Demo contract ---

#[test]
fn artifact_without_provenance_is_rejected() {
    let record = EmbeddingArtifactRecord::new("doc-1", vec![0.5; 4], None);
    assert!(record.provenance().is_none());
    assert_eq!(record.admit(), Err(StorageError::MissingProvenance));
}

// --- canonical_string determinism ---

#[test]
fn canonical_string_is_stable_across_parameter_order() {
    let forward = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &valid_hash(),
        4,
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ],
    )
    .expect("valid provenance");
    let reversed = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &valid_hash(),
        4,
        vec![
            ("normalize".to_owned(), "true".to_owned()),
            ("pooling".to_owned(), "mean".to_owned()),
        ],
    )
    .expect("valid provenance");

    assert_eq!(forward.canonical_string(), reversed.canonical_string());
    assert!(
        forward
            .canonical_string()
            .contains("parameters=[normalize=true,pooling=mean]")
    );
    // Deterministic for repeat calls on the same value.
    assert_eq!(forward.canonical_string(), forward.canonical_string());
}

// --- Boundary rejections ---

#[test]
fn artifact_rejects_empty_subject() {
    assert_eq!(
        EmbeddingArtifact::try_new("   ", vec![0.5; 4], provenance(4)),
        Err(StorageError::EmptyInput)
    );
}

#[test]
fn artifact_rejects_empty_vector() {
    assert_eq!(
        EmbeddingArtifact::try_new("doc-1", Vec::new(), provenance(4)),
        Err(StorageError::EmptyInput)
    );
}

#[test]
fn artifact_rejects_non_finite_vector() {
    let mut vector = vec![0.5_f32; 4];
    vector[0] = f32::INFINITY;
    assert_eq!(
        EmbeddingArtifact::try_new("doc-1", vector, provenance(4)),
        Err(StorageError::NonFiniteValue)
    );
}

#[test]
fn artifact_rejects_dimension_mismatch() {
    assert_eq!(
        EmbeddingArtifact::try_new("doc-1", vec![0.5; 3], provenance(4)),
        Err(StorageError::DimensionMismatch {
            expected: 4,
            actual: 3,
        })
    );
}

#[test]
fn provenance_rejects_hash_without_sha256_prefix() {
    let result = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &"a".repeat(64),
        4,
        vec![("pooling".to_owned(), "mean".to_owned())],
    );
    assert_eq!(
        result,
        Err(StorageError::InvalidProvenanceField("weights_sha256"))
    );
}

#[test]
fn provenance_rejects_short_hash() {
    let result = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        "sha256:abcd",
        4,
        vec![("pooling".to_owned(), "mean".to_owned())],
    );
    assert_eq!(
        result,
        Err(StorageError::InvalidProvenanceField("weights_sha256"))
    );
}

#[test]
fn provenance_rejects_zero_dimensions() {
    let result = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &valid_hash(),
        0,
        vec![("pooling".to_owned(), "mean".to_owned())],
    );
    assert_eq!(
        result,
        Err(StorageError::InvalidProvenanceField("dimensions"))
    );
}

#[test]
fn provenance_rejects_empty_parameters() {
    let result = ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &valid_hash(),
        4,
        Vec::new(),
    );
    assert_eq!(
        result,
        Err(StorageError::InvalidProvenanceField("parameters"))
    );
}

// --- Happy path ---

#[test]
fn provenance_bearing_record_is_admitted() {
    let record = EmbeddingArtifactRecord::new("doc-1", vec![0.5; 4], Some(provenance(4)));
    let artifact = record.admit().expect("record with provenance must admit");
    assert_eq!(artifact.subject_ref(), "doc-1");
    assert_eq!(artifact.dimensions(), 4);
    assert_eq!(
        artifact.provenance().source(),
        "https://example.invalid/embedding-model"
    );
    assert_eq!(artifact.provenance().license(), "Apache-2.0");
    assert_eq!(artifact.provenance().weights_sha256(), valid_hash());
    assert_eq!(artifact.provenance().parameters().len(), 2);
}
