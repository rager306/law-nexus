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

// --- M161: real cosine-similarity retrieval ranking contracts ---
//
// These tests reject the prior fake cascade where RetrievalGate::retrieve
// assigned a constant score=1.0 to every result and never sorted. They prove
// the end-to-end retrieval process now ranks by real directional similarity.

/// Build a gate whose query embeds to `query_vec` over a 3-doc index where the
/// documents sit at distinct cosine similarities to the query.
fn build_ranked_gate(
    query_vec: Vec<f32>,
) -> RetrievalGate<TeiEmbeddingAdapter<StubTransport>, InMemoryVectorStore, InMemoryGraphStore> {
    let dims = query_vec.len();
    let transport = StubTransport { vector: query_vec };
    let adapter = TeiEmbeddingAdapter::try_new(transport, "stub-model", dims).unwrap();
    let mut vector_store = InMemoryVectorStore::new();

    // Three docs at distinct similarity to any [1, 0, ...]-aligned query:
    // close ~ 1.0, mid ~ 0.707, far ~ 0.0 (orthogonal).
    for (id, vec) in [
        ("close", vec![1.0_f32, 0.01]),
        ("mid", vec![1.0_f32, 1.0]),
        ("far", vec![0.0_f32, 1.0]),
    ] {
        let record = ln_storage::VectorRecord::try_new(id, vec, Vec::new()).unwrap();
        vector_store.store(&record).unwrap();
    }

    RetrievalGate::new(adapter, vector_store, InMemoryGraphStore::new(), dims).unwrap()
}

#[test]
fn retrieval_scores_differ_across_dissimilar_documents() {
    // Hostile to the constant-score regression: if every result got score 1.0
    // this assertion would fail because scores would all be equal.
    let gate = build_ranked_gate(vec![1.0, 0.0]);
    let results = gate.retrieve("query text", "stub-model", 3).unwrap();
    assert_eq!(results.len(), 3);

    let scores: Vec<f64> = results.iter().map(|r| r.score()).collect();
    // Scores must be strictly decreasing (distinct similarities, sorted desc).
    assert_eq!(scores.len(), 3);
    assert!(scores[0] > scores[1], "scores must differ: {scores:?}");
    assert!(scores[1] > scores[2], "scores must differ: {scores:?}");
    // Most similar doc must be ~1.0, least similar ~0.0.
    assert!((scores[0] - 1.0).abs() < 1e-3, "top score ~1.0: {scores:?}");
    assert!(scores[2] < 1e-3, "bottom score ~0.0: {scores:?}");
}

#[test]
fn retrieval_results_are_sorted_by_score_descending() {
    let gate = build_ranked_gate(vec![1.0, 0.0]);
    let results = gate.retrieve("query text", "stub-model", 3).unwrap();
    let ids: Vec<&str> = results.iter().map(|r| r.id()).collect();
    assert_eq!(
        ids,
        vec!["close", "mid", "far"],
        "results must be ranked close->mid->far"
    );
}

#[test]
fn retrieval_top_k_returns_most_similar() {
    let gate = build_ranked_gate(vec![1.0, 0.0]);
    let results = gate.retrieve("query text", "stub-model", 1).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(
        results[0].id(),
        "close",
        "top_k=1 must return the most similar doc"
    );
}

#[test]
fn retrieval_citation_score_matches_result_score() {
    let gate = build_ranked_gate(vec![1.0, 0.0]);
    let results = gate.retrieve("query text", "stub-model", 3).unwrap();
    for result in &results {
        assert_eq!(
            result.score(),
            result.citation().score(),
            "citation score must mirror result score"
        );
    }
}
