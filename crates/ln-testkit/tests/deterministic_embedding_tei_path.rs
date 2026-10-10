//! Deterministic TEI-path integration for the M215 S03 test port.
//!
//! This suite drives the deterministic test transport through the *same* TEI
//! adapter seam that the S02 live path uses
//! ([`TeiEmbeddingAdapter`]), but without a socket, network or loopback server.
//! It documents that the deterministic transport replaces S02's loopback
//! fixture for CI determinism: the adapter boundary, the closed error mapping
//! and the provenance composition are exercised end to end.
//!
//! Coverage:
//! - happy path: adapter + provenance composition satisfies the shared artifact
//!   contract and two embeds of one request are byte-identical;
//! - fail-closed: a hostile (NUL) text is rejected as
//!   [`ln_storage::StorageError::TransportBadResponse`] with no artifact and no
//!   panic (the payload is dropped at the S02 D703/D704 boundary);
//! - adapter semantics: model drift and expected-dimension mismatch are
//!   rejected before any transport call.
//!
//! Non-claim: this is a deterministic CI fixture, not a live TEI model
//! validation. No weights, no network, no new dependencies.

use ln_storage::adapters::tei::TeiEmbeddingAdapter;
use ln_storage::{
    EmbeddingArtifactPort, EmbeddingArtifactRequest, ModelProvenance, ProvenancedEmbedding,
    StorageError,
};
use ln_testkit::{
    DeterministicEmbeddingTransport, MAX_DETERMINISTIC_DIMENSIONS,
    assert_embedding_artifact_port_contract,
};

const MODEL_ID: &str = "det-model";
const DIMENSIONS: usize = 16;

/// Raw bit patterns so equality is exact and a `NaN` would surface.
fn bits(vector: &[f32]) -> Vec<u32> {
    vector.iter().map(|value| value.to_bits()).collect()
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

/// Build the deterministic TEI adapter + provenance port over no socket.
fn deterministic_port() -> ProvenancedEmbedding<TeiEmbeddingAdapter<DeterministicEmbeddingTransport>>
{
    let transport =
        DeterministicEmbeddingTransport::new(DIMENSIONS).expect("valid deterministic transport");
    let adapter =
        TeiEmbeddingAdapter::try_new(transport, MODEL_ID, DIMENSIONS).expect("valid TEI adapter");
    ProvenancedEmbedding::try_new(adapter, MODEL_ID, provenance(DIMENSIONS))
        .expect("valid provenance composition")
}

fn artifact_request(text: &str) -> EmbeddingArtifactRequest {
    EmbeddingArtifactRequest::try_new("det-tei-doc-1", text).expect("valid artifact request")
}

#[test]
fn deterministic_transport_constructs_on_the_tei_seam() {
    // The transport itself is fail-closed at the same dimension bounds as the port.
    assert_eq!(
        DeterministicEmbeddingTransport::new(0).err(),
        Some(StorageError::EmptyInput)
    );
    assert_eq!(
        DeterministicEmbeddingTransport::new(MAX_DETERMINISTIC_DIMENSIONS + 1).err(),
        Some(StorageError::InvalidInput("dimensions-too-large"))
    );
    let port = deterministic_port();
    assert_eq!(port.model_id(), MODEL_ID);
}

#[test]
fn happy_path_satisfies_artifact_contract_without_socket() {
    let port = deterministic_port();
    assert_embedding_artifact_port_contract(&port, MODEL_ID, DIMENSIONS);
}

#[test]
fn two_embeds_of_one_request_are_byte_identical() {
    let port = deterministic_port();
    let request = artifact_request("deterministic tei path text");
    let first = port
        .embed_artifact(&request)
        .expect("honest deterministic port must yield an artifact");
    let second = port
        .embed_artifact(&request)
        .expect("honest deterministic port must yield an artifact");
    assert_eq!(first.subject_ref(), request.subject_ref());
    assert_eq!(first.dimensions(), DIMENSIONS);
    assert_eq!(
        bits(first.vector()),
        bits(second.vector()),
        "two embeds of the same request must be byte-identical"
    );
    // A second, independently constructed stack must agree byte-for-byte too.
    let other = deterministic_port()
        .embed_artifact(&request)
        .expect("honest deterministic port must yield an artifact");
    assert_eq!(bits(first.vector()), bits(other.vector()));
}

#[test]
fn hostile_text_is_rejected_as_transport_bad_response() {
    let port = deterministic_port();
    let request = artifact_request("hostile\u{0}text");
    // `EmbeddingArtifactRequest` accepts NUL (not blank); the closed rejection
    // happens at the S02 adapter boundary, which maps the transport
    // `BadResponse` to `StorageError::TransportBadResponse` and drops the
    // payload. No artifact is produced and nothing panics.
    assert_eq!(
        port.embed_artifact(&request),
        Err(StorageError::TransportBadResponse)
    );
}

#[test]
fn model_drift_is_rejected_before_transport() {
    let transport =
        DeterministicEmbeddingTransport::new(DIMENSIONS).expect("valid deterministic transport");
    let adapter =
        TeiEmbeddingAdapter::try_new(transport, MODEL_ID, DIMENSIONS).expect("valid TEI adapter");
    // Provenance composition carries a different declared model identity, so the
    // request it builds drifts from the adapter identity.
    let port = ProvenancedEmbedding::try_new(adapter, "other-model", provenance(DIMENSIONS))
        .expect("valid provenance composition");
    assert!(matches!(
        port.embed_artifact(&artifact_request("contract text")),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}

#[test]
fn expected_dimension_mismatch_is_rejected_before_transport() {
    let transport =
        DeterministicEmbeddingTransport::new(DIMENSIONS).expect("valid deterministic transport");
    let adapter =
        TeiEmbeddingAdapter::try_new(transport, MODEL_ID, DIMENSIONS).expect("valid TEI adapter");
    // Provenance declares smaller dimensions than the adapter, so the request
    // built by the composition mismatches the adapter's expected dimensions.
    let port = ProvenancedEmbedding::try_new(adapter, MODEL_ID, provenance(DIMENSIONS / 2))
        .expect("valid provenance composition");
    assert_eq!(
        port.embed_artifact(&artifact_request("contract text")),
        Err(StorageError::DimensionMismatch {
            expected: DIMENSIONS,
            actual: DIMENSIONS / 2,
        })
    );
}
