use ln_storage::{
    adapters::tei::{EmbeddingTransport, TeiEmbeddingAdapter, TransportError},
    EmbeddingPort, EmbeddingRequest, StorageError,
};

struct StubTransport {
    vector: Result<Vec<f32>, TransportError>,
}

impl EmbeddingTransport for StubTransport {
    fn embed_text(&self, _text: &str) -> Result<Vec<f32>, TransportError> {
        self.vector.clone()
    }
}

fn request(model: &str, dims: usize) -> EmbeddingRequest {
    EmbeddingRequest::try_new("legal text", model, dims).unwrap()
}

#[test]
fn adapter_returns_validated_response_on_match() {
    let transport = StubTransport {
        vector: Ok(vec![0.5; 1024]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    let resp = adapter.embed(&request("tei-bge-m3", 1024)).unwrap();
    assert_eq!(resp.model_id(), "tei-bge-m3");
    assert_eq!(resp.dimensions(), 1024);
}

#[test]
fn adapter_rejects_model_identity_drift() {
    let transport = StubTransport {
        vector: Ok(vec![0.5; 1024]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    assert!(matches!(
        adapter.embed(&request("wrong-model", 1024)),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}

#[test]
fn adapter_rejects_expected_dimension_mismatch() {
    let transport = StubTransport {
        vector: Ok(vec![0.5; 1024]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    assert!(matches!(
        adapter.embed(&request("tei-bge-m3", 512)),
        Err(StorageError::DimensionMismatch { .. })
    ));
}

#[test]
fn adapter_rejects_response_dimension_mismatch() {
    let transport = StubTransport {
        vector: Ok(vec![0.5; 512]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    assert!(matches!(
        adapter.embed(&request("tei-bge-m3", 1024)),
        Err(StorageError::DimensionMismatch { .. })
    ));
}

#[test]
fn adapter_rejects_non_finite_response() {
    let transport = StubTransport {
        vector: Ok(vec![f32::NAN; 1024]),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    assert!(matches!(
        adapter.embed(&request("tei-bge-m3", 1024)),
        Err(StorageError::NonFiniteValue)
    ));
}

#[test]
fn adapter_maps_transport_unavailable_to_internal() {
    let transport = StubTransport {
        vector: Err(TransportError::Unavailable),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    assert!(matches!(
        adapter.embed(&request("tei-bge-m3", 1024)),
        Err(StorageError::Internal(_))
    ));
}

#[test]
fn adapter_maps_transport_bad_response_to_internal() {
    let transport = StubTransport {
        vector: Err(TransportError::BadResponse("HTTP 500".to_owned())),
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "tei-bge-m3", 1024).unwrap();
    let err = adapter.embed(&request("tei-bge-m3", 1024));
    assert!(matches!(err, Err(StorageError::Internal(msg)) if msg.contains("HTTP 500")));
}

#[test]
fn adapter_construction_rejects_empty_model_or_zero_dimensions() {
    let transport = StubTransport {
        vector: Ok(vec![0.5; 1024]),
    };
    assert!(TeiEmbeddingAdapter::try_new(transport, "", 1024).is_err());
}
