use ln_storage::{
    EmbeddingPort, EmbeddingRequest, EmbeddingResponse, GraphEdge, GraphNode, GraphStorePort,
    StorageError, VectorQuery, VectorRecord, VectorStorePort,
};

// --- Stub adapter for testing port traits ---

struct StubEmbedding;
impl EmbeddingPort for StubEmbedding {
    fn embed(&self, request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        if request.model_id() != "stub-model" {
            return Err(StorageError::ModelIdentityDrift {
                expected: "stub-model".to_owned(),
                actual: request.model_id().to_owned(),
            });
        }
        Ok(
            EmbeddingResponse::try_new("stub-model", vec![0.0; request.expected_dimensions()])
                .unwrap(),
        )
    }
}

struct StubVectorStore;
impl VectorStorePort for StubVectorStore {
    fn store(&mut self, record: &VectorRecord) -> Result<(), StorageError> {
        if record.vector().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(())
    }
    fn query(&self, query: &VectorQuery) -> Result<Vec<VectorRecord>, StorageError> {
        if query.top_k() == 0 {
            return Err(StorageError::EmptyInput);
        }
        Ok(Vec::new())
    }
}

struct StubGraphStore;
impl GraphStorePort for StubGraphStore {
    fn upsert_node(&mut self, node: &GraphNode) -> Result<(), StorageError> {
        if node.id().is_empty() || node.label().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(())
    }
    fn upsert_edge(&mut self, edge: &GraphEdge) -> Result<(), StorageError> {
        if edge.source().is_empty() || edge.target().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(())
    }
    fn query_nodes(&self, label: &str) -> Result<Vec<GraphNode>, StorageError> {
        if label.is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(Vec::new())
    }
}

// --- Tests ---

#[test]
fn embedding_request_rejects_empty_text_or_model() {
    assert!(EmbeddingRequest::try_new("", "model", 1024).is_err());
    assert!(EmbeddingRequest::try_new("text", "", 1024).is_err());
    assert!(EmbeddingRequest::try_new("text", "model", 0).is_err());
}

#[test]
fn embedding_response_rejects_non_finite_or_dimension_mismatch() {
    assert!(EmbeddingResponse::try_new("model", vec![0.0; 1024]).is_ok());
    assert!(EmbeddingResponse::try_new("model", vec![f32::NAN; 1024]).is_err());
    assert!(EmbeddingResponse::try_new("model", vec![f32::INFINITY; 1024]).is_err());
    assert!(EmbeddingResponse::try_new("model", vec![]).is_err());
}

#[test]
fn embedding_port_returns_validated_response() {
    let port = StubEmbedding;
    let req = EmbeddingRequest::try_new("legal text", "stub-model", 4).unwrap();
    let resp = port.embed(&req).unwrap();
    assert_eq!(resp.model_id(), "stub-model");
    assert_eq!(resp.dimensions(), 4);
    assert_eq!(resp.vector().len(), 4);
}

#[test]
fn embedding_port_rejects_model_drift() {
    let port = StubEmbedding;
    let req = EmbeddingRequest::try_new("text", "wrong-model", 4).unwrap();
    assert!(matches!(
        port.embed(&req),
        Err(StorageError::ModelIdentityDrift { .. })
    ));
}

#[test]
fn vector_record_rejects_empty_vector() {
    assert!(VectorRecord::try_new("id", vec![], Vec::new()).is_err());
    assert!(VectorRecord::try_new("id", vec![0.0], Vec::new()).is_ok());
    assert!(VectorRecord::try_new("", vec![0.0], Vec::new()).is_err());
}

#[test]
fn vector_query_rejects_empty_vector_or_zero_top_k() {
    assert!(VectorQuery::try_new(vec![], 5).is_err());
    assert!(VectorQuery::try_new(vec![0.0], 0).is_err());
    assert!(VectorQuery::try_new(vec![0.0], 5).is_ok());
}

#[test]
fn graph_node_rejects_empty_id_or_label() {
    assert!(GraphNode::try_new("", "label", Vec::new()).is_err());
    assert!(GraphNode::try_new("id", "", Vec::new()).is_err());
    assert!(GraphNode::try_new("id", "label", Vec::new()).is_ok());
}

#[test]
fn graph_edge_rejects_empty_endpoints() {
    assert!(GraphEdge::try_new("", "target", "label").is_err());
    assert!(GraphEdge::try_new("source", "", "label").is_err());
    assert!(GraphEdge::try_new("source", "target", "").is_ok());
}

#[test]
fn vector_store_port_round_trips_through_stub() {
    let mut store = StubVectorStore;
    let record = VectorRecord::try_new("id-1", vec![0.5], Vec::new()).unwrap();
    assert!(store.store(&record).is_ok());
    let query = VectorQuery::try_new(vec![0.5], 3).unwrap();
    let results = store.query(&query).unwrap();
    assert!(results.is_empty());
}

#[test]
fn graph_store_port_round_trips_through_stub() {
    let mut store = StubGraphStore;
    let node = GraphNode::try_new("node-1", "Statya", Vec::new()).unwrap();
    assert!(store.upsert_node(&node).is_ok());
    let edge = GraphEdge::try_new("node-1", "node-2", "REFERENCES").unwrap();
    assert!(store.upsert_edge(&edge).is_ok());
    let nodes = store.query_nodes("Statya").unwrap();
    assert!(nodes.is_empty());
}
