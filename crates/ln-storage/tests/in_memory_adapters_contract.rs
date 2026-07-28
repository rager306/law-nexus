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
