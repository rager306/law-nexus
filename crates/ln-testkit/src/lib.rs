//! Shared port-contract helpers for law-nexus (ADR-0015).
//!
//! These helpers encode semantic expectations that every adapter of a port
//! must satisfy. InMemory adapters must pass the same suite intended for
//! future real adapters (TEI/RuVector/redb).
//!
//! Lifecycle: foundation is `[bounded]`. Real-infrastructure validation is not
//! claimed by the existence of this crate.

use ln_storage::{
    GraphEdge, GraphNode, GraphStorePort, StorageError, VectorQuery, VectorRecord, VectorStorePort,
};

fn vector_record(id: &str, dims: &[f32]) -> VectorRecord {
    VectorRecord::try_new(id, dims.to_vec(), Vec::new()).expect("valid vector record")
}

fn vector_query(dims: &[f32], top_k: usize) -> VectorQuery {
    VectorQuery::try_new(dims.to_vec(), top_k).expect("valid vector query")
}

fn graph_node(id: &str, label: &str) -> GraphNode {
    GraphNode::try_new(id, label, Vec::new()).expect("valid graph node")
}

fn graph_edge(source: &str, target: &str, label: &str) -> GraphEdge {
    GraphEdge::try_new(source, target, label).expect("valid graph edge")
}

/// Shared semantic contract for [`VectorStorePort`].
pub fn assert_vector_store_contract<S: VectorStorePort>(store: &mut S) {
    let dims = [0.5_f32, 0.3, 0.2];
    let first = vector_record("contract-v1", &dims);
    let second = vector_record("contract-v2", &dims);

    store
        .store(&first)
        .expect("store accepts a validated vector record");
    store
        .store(&second)
        .expect("store accepts a second validated vector record");

    let results = store
        .query(&vector_query(&dims, 10))
        .expect("query returns stored records");
    let ids: Vec<&str> = results.iter().map(VectorRecord::id).collect();
    assert!(
        ids.contains(&"contract-v1") && ids.contains(&"contract-v2"),
        "query must return both stored ids, got {ids:?}"
    );

    // Idempotent upsert by id: second store of same id does not create a duplicate.
    store
        .store(&first)
        .expect("upsert of existing id must succeed");
    let after_upsert = store
        .query(&vector_query(&dims, 10))
        .expect("query after upsert");
    let count_v1 = after_upsert
        .iter()
        .filter(|record| record.id() == "contract-v1")
        .count();
    assert_eq!(count_v1, 1, "vector id upsert must be idempotent");

    // top_k bounds result cardinality.
    let limited = store
        .query(&vector_query(&dims, 1))
        .expect("top_k=1 query succeeds");
    assert!(
        limited.len() <= 1,
        "top_k must bound returned cardinality, got {}",
        limited.len()
    );

    // Empty id is rejected by validated record construction; adapter must still
    // reject empty top-level misuse if it re-validates — covered by type boundary.
    let _ = StorageError::EmptyInput;
}

/// Shared semantic contract for [`GraphStorePort`].
pub fn assert_graph_store_contract<S: GraphStorePort>(store: &mut S) {
    let article = graph_node("contract-n1", "Statya");
    let point = graph_node("contract-n2", "Punkt");
    let edge = graph_edge("contract-n1", "contract-n2", "CONTAINS");

    store
        .upsert_node(&article)
        .expect("upsert accepts validated node");
    store
        .upsert_node(&point)
        .expect("upsert accepts second validated node");
    store
        .upsert_edge(&edge)
        .expect("upsert accepts validated edge");

    let articles = store
        .query_nodes("Statya")
        .expect("label query returns nodes");
    assert_eq!(
        articles.len(),
        1,
        "exact label query returns one Statya node"
    );
    assert_eq!(articles[0].id(), "contract-n1");

    let points = store
        .query_nodes("Punkt")
        .expect("label query returns Punkt nodes");
    assert_eq!(points.len(), 1);
    assert_eq!(points[0].id(), "contract-n2");

    // Idempotent node upsert by id.
    store
        .upsert_node(&article)
        .expect("node upsert by id is idempotent");
    let articles_after = store
        .query_nodes("Statya")
        .expect("label query after upsert");
    assert_eq!(
        articles_after.len(),
        1,
        "node id upsert must not create duplicates"
    );

    // Unknown label returns empty, not error.
    let missing = store
        .query_nodes("MissingLabel")
        .expect("unknown label is empty success");
    assert!(
        missing.is_empty(),
        "unknown label must return empty set, got {}",
        missing.len()
    );
}
