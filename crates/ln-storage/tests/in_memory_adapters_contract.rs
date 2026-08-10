use ln_storage::{
    adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore, OperationEvent},
    GraphEdge, GraphNode, GraphStorePort, VectorQuery, VectorRecord, VectorStorePort,
};

fn record(id: &str) -> VectorRecord {
    VectorRecord::try_new(id, vec![0.5, 0.3, 0.2], Vec::new()).unwrap()
}

fn query() -> VectorQuery {
    VectorQuery::try_new(vec![0.5, 0.3, 0.2], 3).unwrap()
}

fn node(id: &str, label: &str) -> GraphNode {
    GraphNode::try_new(id, label, Vec::new()).unwrap()
}

fn edge(src: &str, tgt: &str) -> GraphEdge {
    GraphEdge::try_new(src, tgt, "REFERENCES").unwrap()
}

#[test]
fn vector_store_round_trips_store_and_query() {
    let mut store = InMemoryVectorStore::new();
    store.store(&record("v1")).unwrap();
    store.store(&record("v2")).unwrap();

    let results = store.query(&query()).unwrap();
    assert_eq!(results.len(), 2);
}

#[test]
fn vector_store_upsert_is_idempotent() {
    let mut store = InMemoryVectorStore::new();
    store.store(&record("v1")).unwrap();
    store.store(&record("v1")).unwrap();

    let results = store.query(&query()).unwrap();
    assert_eq!(results.len(), 1);
}

#[test]
fn graph_store_round_trips_upsert_and_query() {
    let mut store = InMemoryGraphStore::new();
    store.upsert_node(&node("n1", "Statya")).unwrap();
    store.upsert_node(&node("n2", "Punkt")).unwrap();
    store.upsert_edge(&edge("n1", "n2")).unwrap();

    let statya_nodes = store.query_nodes("Statya").unwrap();
    assert_eq!(statya_nodes.len(), 1);
    assert_eq!(statya_nodes[0].id(), "n1");

    let punkt_nodes = store.query_nodes("Punkt").unwrap();
    assert_eq!(punkt_nodes.len(), 1);
}

#[test]
fn graph_store_upsert_node_is_idempotent() {
    let mut store = InMemoryGraphStore::new();
    store.upsert_node(&node("n1", "Statya")).unwrap();
    store.upsert_node(&node("n1", "Statya")).unwrap();

    let nodes = store.query_nodes("Statya").unwrap();
    assert_eq!(nodes.len(), 1);
}

#[test]
fn journal_records_all_operations() {
    let mut store = InMemoryVectorStore::new();
    store.store(&record("v1")).unwrap();
    store.query(&query()).unwrap();

    let journal = store.journal();
    assert_eq!(journal.events().len(), 2);
    assert!(
        matches!(journal.events()[0], OperationEvent::VectorStored { ref record } if record.id() == "v1")
    );
    assert!(matches!(
        journal.events()[1],
        OperationEvent::VectorQueried { top_k: 3 }
    ));
}

#[test]
fn journal_replay_restores_state_after_simulated_crash() {
    let mut store = InMemoryVectorStore::new();
    store.store(&record("v1")).unwrap();
    store.store(&record("v2")).unwrap();
    let journal = store.journal().clone();

    // Simulate crash: create a fresh store and replay journal
    let mut recovered = InMemoryVectorStore::new();
    recovered.replay(&journal).unwrap();

    let results = recovered.query(&query()).unwrap();
    assert_eq!(results.len(), 2);
}

#[test]
fn graph_store_journal_records_upserts() {
    let mut store = InMemoryGraphStore::new();
    store.upsert_node(&node("n1", "Statya")).unwrap();
    store.upsert_edge(&edge("n1", "n2")).unwrap();
    store.query_nodes("Statya").unwrap();

    let journal = store.journal();
    assert_eq!(journal.events().len(), 3);
}

// --- M161: real cosine-similarity ranking contracts ---

/// Three documents at known cosine distances from a query vector.
/// q=[1,0], close=[1,0.01] (~1.0), mid=[1,1] (~0.707), far=[0,1] (0.0).
fn ranked_record(id: &str, vector: Vec<f32>) -> VectorRecord {
    VectorRecord::try_new(id, vector, Vec::new()).unwrap()
}

#[test]
fn vector_query_ranks_by_cosine_similarity_descending() {
    let mut store = InMemoryVectorStore::new();
    // Insert in an order unrelated to similarity to defeat any key-order shortcut.
    store.store(&ranked_record("far", vec![0.0, 1.0])).unwrap();
    store
        .store(&ranked_record("close", vec![1.0, 0.01]))
        .unwrap();
    store.store(&ranked_record("mid", vec![1.0, 1.0])).unwrap();

    let q = VectorQuery::try_new(vec![1.0, 0.0], 10).unwrap();
    let results = store.query(&q).unwrap();
    let ids: Vec<&str> = results.iter().map(VectorRecord::id).collect();
    assert_eq!(
        ids,
        vec!["close", "mid", "far"],
        "query must rank by descending cosine similarity"
    );
}

#[test]
fn vector_query_top_k_returns_most_similar_not_arbitrary() {
    let mut store = InMemoryVectorStore::new();
    store.store(&ranked_record("far", vec![0.0, 1.0])).unwrap();
    store
        .store(&ranked_record("close", vec![1.0, 0.0]))
        .unwrap();
    store.store(&ranked_record("mid", vec![1.0, 1.0])).unwrap();

    let q = VectorQuery::try_new(vec![1.0, 0.0], 1).unwrap();
    let results = store.query(&q).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(
        results[0].id(),
        "close",
        "top_k=1 must return the most similar record"
    );
}

#[test]
fn vector_query_rejects_dimension_mismatch_with_stored_record() {
    let mut store = InMemoryVectorStore::new();
    // A stored record with a different dimensionality than the query.
    store
        .store(&ranked_record("dim3", vec![1.0, 0.0, 0.0]))
        .unwrap();
    let q = VectorQuery::try_new(vec![1.0, 0.0], 10).unwrap();
    // The adapter must fail closed rather than silently truncating.
    assert!(store.query(&q).is_err());
}
