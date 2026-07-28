use ln_storage::{
    EmbeddingPort, EmbeddingRequest, GraphStorePort, StorageError, VectorQuery, VectorStorePort,
};

/// Typed KnowQL operation over storage ports.
///
/// Each variant maps to exactly one storage port operation.
/// No adapter-specific types are present.
#[derive(Debug, Clone, PartialEq)]
pub enum KnowQLOp {
    /// Embed text through EmbeddingPort.
    Embed {
        text: String,
        model_id: String,
        dimensions: usize,
    },
    /// Find similar vectors through VectorStorePort.
    FindSimilar { vector: Vec<f32>, top_k: usize },
    /// Find graph nodes by label through GraphStorePort.
    FindByLabel { label: String },
}

/// Validated KnowQL operation ready for execution.
#[derive(Debug, Clone, PartialEq)]
pub struct ValidatedOp {
    op: KnowQLOp,
}

impl ValidatedOp {
    pub fn try_new(op: KnowQLOp) -> Result<Self, StorageError> {
        match &op {
            KnowQLOp::Embed {
                text,
                model_id,
                dimensions,
            } => {
                if text.trim().is_empty() || model_id.trim().is_empty() || *dimensions == 0 {
                    return Err(StorageError::EmptyInput);
                }
            }
            KnowQLOp::FindSimilar { vector, top_k } => {
                if vector.is_empty() || *top_k == 0 {
                    return Err(StorageError::EmptyInput);
                }
                if vector.iter().any(|v| !v.is_finite()) {
                    return Err(StorageError::NonFiniteValue);
                }
            }
            KnowQLOp::FindByLabel { label } => {
                if label.trim().is_empty() {
                    return Err(StorageError::EmptyInput);
                }
            }
        }
        Ok(Self { op })
    }

    pub fn op(&self) -> &KnowQLOp {
        &self.op
    }
}

/// KnowQL execution result carrying typed data from storage ports.
#[derive(Debug, Clone, PartialEq)]
pub enum KnowQLResult {
    Embedding {
        model_id: String,
        dimensions: usize,
        vector: Vec<f32>,
    },
    SimilarRecords {
        ids: Vec<String>,
    },
    GraphNodes {
        labels: Vec<String>,
    },
}

/// Execute a validated KnowQL operation against storage ports.
///
/// This executor is a thin typed dispatcher. It does not assert legal
/// correctness, retrieval quality or citation authority.
pub fn execute<E, V, G>(
    op: &ValidatedOp,
    embedding: &E,
    vector_store: &V,
    graph_store: &G,
) -> Result<KnowQLResult, StorageError>
where
    E: EmbeddingPort,
    V: VectorStorePort,
    G: GraphStorePort,
{
    match op.op() {
        KnowQLOp::Embed {
            text,
            model_id,
            dimensions,
        } => {
            let request = EmbeddingRequest::try_new(text, model_id, *dimensions)?;
            let response = embedding.embed(&request)?;
            Ok(KnowQLResult::Embedding {
                model_id: response.model_id().to_owned(),
                dimensions: response.dimensions(),
                vector: response.vector().to_vec(),
            })
        }
        KnowQLOp::FindSimilar { vector, top_k } => {
            let query = VectorQuery::try_new(vector.clone(), *top_k)?;
            let records = vector_store.query(&query)?;
            Ok(KnowQLResult::SimilarRecords {
                ids: records.iter().map(|r| r.id().to_owned()).collect(),
            })
        }
        KnowQLOp::FindByLabel { label } => {
            let nodes = graph_store.query_nodes(label)?;
            Ok(KnowQLResult::GraphNodes {
                labels: nodes.iter().map(|n| n.label().to_owned()).collect(),
            })
        }
    }
}
