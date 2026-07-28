use ln_query::knowql::{execute, KnowQLOp, KnowQLResult, ValidatedOp};
use ln_storage::{
    EmbeddingPort, EmbeddingRequest, EmbeddingResponse, GraphEdge, GraphNode, GraphStorePort,
    StorageError, VectorQuery, VectorRecord, VectorStorePort,
};

struct StubEmbedding;
impl EmbeddingPort for StubEmbedding {
    fn embed(&self, request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        Ok(
            EmbeddingResponse::try_new(
                request.model_id(),
                vec![0.5; request.expected_dimensions()],
            )
            .unwrap(),
        )
    }
}

struct StubVectorStore;
impl VectorStorePort for StubVectorStore {
    fn store(&mut self, _record: &VectorRecord) -> Result<(), StorageError> {
        Ok(())
    }
    fn query(&self, q: &VectorQuery) -> Result<Vec<VectorRecord>, StorageError> {
        Ok(vec![VectorRecord::try_new(
            "doc-1",
            q.vector().to_vec(),
            Vec::new(),
        )
        .unwrap()])
    }
}

struct StubGraphStore;
impl GraphStorePort for StubGraphStore {
    fn upsert_node(&mut self, _node: &GraphNode) -> Result<(), StorageError> {
        Ok(())
    }
    fn upsert_edge(&mut self, _edge: &GraphEdge) -> Result<(), StorageError> {
        Ok(())
    }
    fn query_nodes(&self, label: &str) -> Result<Vec<GraphNode>, StorageError> {
        Ok(vec![GraphNode::try_new("n1", label, Vec::new()).unwrap()])
    }
}

#[test]
fn embed_op_executes_through_embedding_port() {
    let op = ValidatedOp::try_new(KnowQLOp::Embed {
        text: "legal text".to_owned(),
        model_id: "stub-model".to_owned(),
        dimensions: 4,
    })
    .unwrap();

    let result = execute(&op, &StubEmbedding, &StubVectorStore, &StubGraphStore).unwrap();
    match result {
        KnowQLResult::Embedding {
            model_id,
            dimensions,
            vector,
        } => {
            assert_eq!(model_id, "stub-model");
            assert_eq!(dimensions, 4);
            assert_eq!(vector.len(), 4);
        }
        _ => panic!("expected Embedding result"),
    }
}

#[test]
fn find_similar_op_executes_through_vector_store() {
    let op = ValidatedOp::try_new(KnowQLOp::FindSimilar {
        vector: vec![0.5; 4],
        top_k: 3,
    })
    .unwrap();

    let result = execute(&op, &StubEmbedding, &StubVectorStore, &StubGraphStore).unwrap();
    match result {
        KnowQLResult::SimilarRecords { ids } => {
            assert_eq!(ids, vec!["doc-1"]);
        }
        _ => panic!("expected SimilarRecords result"),
    }
}

#[test]
fn find_by_label_op_executes_through_graph_store() {
    let op = ValidatedOp::try_new(KnowQLOp::FindByLabel {
        label: "Statya".to_owned(),
    })
    .unwrap();

    let result = execute(&op, &StubEmbedding, &StubVectorStore, &StubGraphStore).unwrap();
    match result {
        KnowQLResult::GraphNodes { labels } => {
            assert_eq!(labels, vec!["Statya"]);
        }
        _ => panic!("expected GraphNodes result"),
    }
}

#[test]
fn validation_rejects_empty_embed_text() {
    assert!(ValidatedOp::try_new(KnowQLOp::Embed {
        text: "".to_owned(),
        model_id: "model".to_owned(),
        dimensions: 4,
    })
    .is_err());
}

#[test]
fn validation_rejects_zero_dimensions() {
    assert!(ValidatedOp::try_new(KnowQLOp::Embed {
        text: "text".to_owned(),
        model_id: "model".to_owned(),
        dimensions: 0,
    })
    .is_err());
}

#[test]
fn validation_rejects_empty_find_similar_vector() {
    assert!(ValidatedOp::try_new(KnowQLOp::FindSimilar {
        vector: vec![],
        top_k: 3,
    })
    .is_err());
}

#[test]
fn validation_rejects_nan_vector() {
    assert!(ValidatedOp::try_new(KnowQLOp::FindSimilar {
        vector: vec![f32::NAN],
        top_k: 3,
    })
    .is_err());
}

#[test]
fn validation_rejects_empty_label() {
    assert!(ValidatedOp::try_new(KnowQLOp::FindByLabel {
        label: "".to_owned(),
    })
    .is_err());
}
