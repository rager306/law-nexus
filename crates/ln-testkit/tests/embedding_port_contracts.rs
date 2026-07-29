//! EmbeddingPort shared suite for real-adapter preparation (ADR-0015 / M152).
//!
//! Uses TeiEmbeddingAdapter with injectable stub transport only.
//! Lifecycle: `[bounded]` preparation. Not live TEI validation.

use ln_storage::{
    adapters::tei::{EmbeddingTransport, TeiEmbeddingAdapter, TransportError},
    EmbeddingPort, EmbeddingRequest, StorageError,
};
use ln_testkit::assert_embedding_port_contract;

struct StubTransport {
    vector: Result<Vec<f32>, TransportError>,
}

impl EmbeddingTransport for StubTransport {
    fn embed_text(&self, _text: &str) -> Result<Vec<f32>, TransportError> {
        self.vector.clone()
    }
}

fn request(model: &str, dims: usize) -> EmbeddingRequest {
    EmbeddingRequest::try_new("contract legal text", model, dims).expect("valid request")
}

#[test]
fn tei_stub_transport_satisfies_shared_embedding_port_contract() {
    let transport = StubTransport {
        vector: Ok(vec![0.25; 8]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert_embedding_port_contract(&adapter, "tei-contract-model", 8);
}

#[test]
fn tei_stub_transport_rejects_model_identity_drift() {
    let transport = StubTransport {
        vector: Ok(vec![0.25; 8]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert!(matches!(
        adapter.embed(&request("wrong-model", 8)),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}

#[test]
fn tei_stub_transport_rejects_expected_dimension_mismatch() {
    let transport = StubTransport {
        vector: Ok(vec![0.25; 8]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert!(matches!(
        adapter.embed(&request("tei-contract-model", 4)),
        Err(StorageError::DimensionMismatch { .. })
    ));
}

#[test]
fn tei_stub_transport_rejects_response_dimension_mismatch() {
    let transport = StubTransport {
        vector: Ok(vec![0.25; 4]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert!(matches!(
        adapter.embed(&request("tei-contract-model", 8)),
        Err(StorageError::DimensionMismatch { .. })
    ));
}

#[test]
fn tei_stub_transport_rejects_non_finite_values() {
    let transport = StubTransport {
        vector: Ok(vec![0.25, f32::NAN, 0.5, 0.1, 0.2, 0.3, 0.4, 0.5]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert!(matches!(
        adapter.embed(&request("tei-contract-model", 8)),
        Err(StorageError::NonFiniteValue)
    ));
}

#[test]
fn tei_stub_transport_maps_transport_failure() {
    let transport = StubTransport {
        vector: Err(TransportError::Unavailable),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-contract-model", 8)
        .expect("valid tei adapter");
    assert!(matches!(
        adapter.embed(&request("tei-contract-model", 8)),
        Err(StorageError::Internal(_))
    ));
}
