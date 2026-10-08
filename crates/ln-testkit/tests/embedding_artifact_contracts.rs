//! Shared embedding-artifact contract suite for provenance-bearing ports
//! (ADR-0015 / M215 S01).
//!
//! Proves that an honest `EmbeddingArtifactPort` built on top of a
//! deterministic in-test `EmbeddingPort` satisfies the shared suite, and that
//! provenance cannot be lost: a record without provenance is rejected, and
//! dimension desynchronisation and model identity drift fail closed.
//! No network, no weights, no concrete model.
//! Lifecycle: `[bounded]` contract preparation.

use ln_storage::{
    EmbeddingArtifactPort, EmbeddingArtifactRecord, EmbeddingArtifactRequest, EmbeddingPort,
    EmbeddingRequest, EmbeddingResponse, ModelProvenance, ProvenancedEmbedding, StorageError,
};
use ln_testkit::assert_embedding_artifact_port_contract;

/// Deterministic in-test embedder: returns a fixed model identity and a fixed
/// finite vector. Ignores the request text on purpose so the contract suite is
/// exercised against a known-good response shape.
struct DeterministicEmbedder {
    model_id: String,
    dimensions: usize,
}

impl EmbeddingPort for DeterministicEmbedder {
    fn embed(&self, _request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        EmbeddingResponse::try_new(&self.model_id, vec![0.125; self.dimensions])
    }
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

fn request() -> EmbeddingArtifactRequest {
    EmbeddingArtifactRequest::try_new("doc-1", "contract legal text")
        .expect("valid artifact request")
}

#[test]
fn honest_provenanced_embedding_satisfies_shared_artifact_contract() {
    let embedder = DeterministicEmbedder {
        model_id: "contract-model".to_owned(),
        dimensions: 16,
    };
    let port = ProvenancedEmbedding::try_new(embedder, "contract-model", provenance(16))
        .expect("valid composition");

    assert_embedding_artifact_port_contract(&port, "contract-model", 16);
}

#[test]
fn honest_provenanced_embedding_yields_populated_provenance() {
    let embedder = DeterministicEmbedder {
        model_id: "contract-model".to_owned(),
        dimensions: 16,
    };
    let port = ProvenancedEmbedding::try_new(embedder, "contract-model", provenance(16))
        .expect("valid composition");

    let artifact = port
        .embed_artifact(&request())
        .expect("honest port must yield an artifact");
    assert_eq!(artifact.subject_ref(), "doc-1");
    assert_eq!(artifact.dimensions(), 16);
    assert_eq!(artifact.provenance().license(), "Apache-2.0");
    assert_eq!(artifact.provenance().parameters().len(), 2);
    assert!(artifact
        .provenance()
        .weights_sha256()
        .starts_with("sha256:"));
}

#[test]
fn artifact_record_without_provenance_is_rejected() {
    let record = EmbeddingArtifactRecord::new("doc-1", vec![0.5; 16], None);
    assert!(record.provenance().is_none());
    assert_eq!(record.admit(), Err(StorageError::MissingProvenance));
}

#[test]
fn provenance_bearing_record_is_admitted() {
    let record = EmbeddingArtifactRecord::new("doc-1", vec![0.5; 16], Some(provenance(16)));
    let artifact = record.admit().expect("record with provenance must admit");
    assert_eq!(artifact.subject_ref(), "doc-1");
    assert_eq!(artifact.dimensions(), 16);
}

#[test]
fn dimension_desync_is_rejected() {
    let embedder = DeterministicEmbedder {
        model_id: "contract-model".to_owned(),
        dimensions: 8,
    };
    let port = ProvenancedEmbedding::try_new(embedder, "contract-model", provenance(16))
        .expect("valid composition");

    assert!(matches!(
        port.embed_artifact(&request()),
        Err(StorageError::DimensionMismatch { .. })
    ));
}

#[test]
fn model_identity_drift_is_rejected() {
    let embedder = DeterministicEmbedder {
        model_id: "other-model".to_owned(),
        dimensions: 16,
    };
    let port = ProvenancedEmbedding::try_new(embedder, "contract-model", provenance(16))
        .expect("valid composition");

    assert!(matches!(
        port.embed_artifact(&request()),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}
