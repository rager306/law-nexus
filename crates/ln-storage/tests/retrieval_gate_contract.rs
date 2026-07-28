use ln_storage::{
    adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore},
    adapters::tei::{EmbeddingTransport, TeiEmbeddingAdapter, TransportError},
    retrieval::{Citation, CitationTamperCheck, RetrievalGate},
    GraphStorePort, VectorStorePort,
};

struct StubTransport {
    vector: Vec<f32>,
}

impl EmbeddingTransport for StubTransport {
    fn embed_text(&self, _text: &str) -> Result<Vec<f32>, TransportError> {
        Ok(self.vector.clone())
    }
}

fn build_gate(
) -> RetrievalGate<TeiEmbeddingAdapter<StubTransport>, InMemoryVectorStore, InMemoryGraphStore> {
    let transport = StubTransport {
        vector: vec![0.5; 4],
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "stub-model", 4).unwrap();
    let mut vector_store = InMemoryVectorStore::new();
    let mut graph_store = InMemoryGraphStore::new();

    // Index a document
    let record = ln_storage::VectorRecord::try_new(
        "doc-1",
        vec![0.5; 4],
        vec![("label".to_owned(), "Statya".to_owned())],
    )
    .unwrap();
    vector_store.store(&record).unwrap();

    let node = ln_storage::GraphNode::try_new("doc-1", "Statya", Vec::new()).unwrap();
    graph_store.upsert_node(&node).unwrap();

    RetrievalGate::new(adapter, vector_store, graph_store, 4).unwrap()
}

#[test]
fn retrieval_returns_traceable_result() {
    let gate = build_gate();
    let results = gate.retrieve("query text", "stub-model", 1).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].id(), "doc-1");
    assert!(results[0].score() >= 0.0);
    assert!(!results[0].citation().source_span().is_empty());
}

#[test]
fn retrieval_rejects_model_drift() {
    let gate = build_gate();
    assert!(gate.retrieve("query text", "wrong-model", 1).is_err());
}

#[test]
fn retrieval_rejects_empty_index() {
    let transport = StubTransport {
        vector: vec![0.5; 4],
    };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "stub-model", 4).unwrap();
    let gate = RetrievalGate::new(
        adapter,
        InMemoryVectorStore::new(),
        InMemoryGraphStore::new(),
        4,
    )
    .unwrap();
    let results = gate.retrieve("query text", "stub-model", 1).unwrap();
    assert!(results.is_empty());
}

#[test]
fn citation_tamper_check_detects_modified_span() {
    let citation = Citation::try_new("doc-1", "original span", 0.95).unwrap();
    let check = CitationTamperCheck::new(&citation);
    assert!(check.verify().is_ok());

    let tampered = Citation::try_new("doc-1", "tampered span", 0.95).unwrap();
    let check2 = CitationTamperCheck::against(&citation, &tampered);
    assert!(check2.verify().is_err());
}

#[test]
fn retrieval_is_deterministic_on_repeat() {
    let gate = build_gate();
    let first = gate.retrieve("query text", "stub-model", 1).unwrap();
    let second = gate.retrieve("query text", "stub-model", 1).unwrap();
    assert_eq!(first.len(), second.len());
    assert_eq!(first[0].id(), second[0].id());
    assert_eq!(first[0].score(), second[0].score());
}

#[test]
fn citation_rejects_empty_id_or_span() {
    assert!(Citation::try_new("", "span", 0.5).is_err());
    assert!(Citation::try_new("id", "", 0.5).is_err());
    assert!(Citation::try_new("id", "span", -0.1).is_err());
    assert!(Citation::try_new("id", "span", 1.5).is_err());
}
