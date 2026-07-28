pub mod adapters;

/// Storage error type for port operations.
#[derive(Debug, Clone, PartialEq)]
pub enum StorageError {
    EmptyInput,
    DimensionMismatch { expected: usize, actual: usize },
    ModelIdentityDrift { expected: String, actual: String },
    NonFiniteValue,
    Unsupported,
    Internal(String),
}

impl std::fmt::Display for StorageError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyInput => write!(formatter, "empty input"),
            Self::DimensionMismatch { expected, actual } => {
                write!(
                    formatter,
                    "dimension mismatch: expected {expected}, got {actual}"
                )
            }
            Self::ModelIdentityDrift { expected, actual } => {
                write!(
                    formatter,
                    "model identity drift: expected {expected}, got {actual}"
                )
            }
            Self::NonFiniteValue => write!(formatter, "non-finite vector value"),
            Self::Unsupported => write!(formatter, "unsupported operation"),
            Self::Internal(msg) => write!(formatter, "internal: {msg}"),
        }
    }
}

impl std::error::Error for StorageError {}

// --- Embedding port ---

pub struct EmbeddingRequest {
    text: String,
    model_id: String,
    expected_dimensions: usize,
}

impl EmbeddingRequest {
    pub fn try_new(
        text: &str,
        model_id: &str,
        expected_dimensions: usize,
    ) -> Result<Self, StorageError> {
        if text.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if model_id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if expected_dimensions == 0 {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            text: text.to_owned(),
            model_id: model_id.to_owned(),
            expected_dimensions,
        })
    }
    pub fn text(&self) -> &str {
        &self.text
    }
    pub fn model_id(&self) -> &str {
        &self.model_id
    }
    pub fn expected_dimensions(&self) -> usize {
        self.expected_dimensions
    }
}

pub struct EmbeddingResponse {
    model_id: String,
    vector: Vec<f32>,
}

impl EmbeddingResponse {
    pub fn try_new(model_id: &str, vector: Vec<f32>) -> Result<Self, StorageError> {
        if model_id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.iter().any(|v| !v.is_finite()) {
            return Err(StorageError::NonFiniteValue);
        }
        Ok(Self {
            model_id: model_id.to_owned(),
            vector,
        })
    }
    pub fn model_id(&self) -> &str {
        &self.model_id
    }
    pub fn dimensions(&self) -> usize {
        self.vector.len()
    }
    pub fn vector(&self) -> &[f32] {
        &self.vector
    }
}

pub trait EmbeddingPort {
    fn embed(&self, request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError>;
}

// --- Vector store port ---

pub struct VectorRecord {
    id: String,
    vector: Vec<f32>,
    metadata: Vec<(String, String)>,
}

impl VectorRecord {
    pub fn try_new(
        id: &str,
        vector: Vec<f32>,
        metadata: Vec<(String, String)>,
    ) -> Result<Self, StorageError> {
        if id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.iter().any(|v| !v.is_finite()) {
            return Err(StorageError::NonFiniteValue);
        }
        Ok(Self {
            id: id.to_owned(),
            vector,
            metadata,
        })
    }
    pub fn id(&self) -> &str {
        &self.id
    }
    pub fn vector(&self) -> &[f32] {
        &self.vector
    }
    pub fn metadata(&self) -> &[(String, String)] {
        &self.metadata
    }
}

pub struct VectorQuery {
    vector: Vec<f32>,
    top_k: usize,
}

impl VectorQuery {
    pub fn try_new(vector: Vec<f32>, top_k: usize) -> Result<Self, StorageError> {
        if vector.is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.iter().any(|v| !v.is_finite()) {
            return Err(StorageError::NonFiniteValue);
        }
        if top_k == 0 {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self { vector, top_k })
    }
    pub fn vector(&self) -> &[f32] {
        &self.vector
    }
    pub fn top_k(&self) -> usize {
        self.top_k
    }
}

pub trait VectorStorePort {
    fn store(&mut self, record: &VectorRecord) -> Result<(), StorageError>;
    fn query(&self, query: &VectorQuery) -> Result<Vec<VectorRecord>, StorageError>;
}

// --- Graph store port ---

pub struct GraphNode {
    id: String,
    label: String,
    properties: Vec<(String, String)>,
}

impl GraphNode {
    pub fn try_new(
        id: &str,
        label: &str,
        properties: Vec<(String, String)>,
    ) -> Result<Self, StorageError> {
        if id.trim().is_empty() || label.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            id: id.to_owned(),
            label: label.to_owned(),
            properties,
        })
    }
    pub fn id(&self) -> &str {
        &self.id
    }
    pub fn label(&self) -> &str {
        &self.label
    }
    pub fn properties(&self) -> &[(String, String)] {
        &self.properties
    }
}

pub struct GraphEdge {
    source: String,
    target: String,
    label: String,
}

impl GraphEdge {
    pub fn try_new(source: &str, target: &str, label: &str) -> Result<Self, StorageError> {
        if source.trim().is_empty() || target.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            source: source.to_owned(),
            target: target.to_owned(),
            label: label.to_owned(),
        })
    }
    pub fn source(&self) -> &str {
        &self.source
    }
    pub fn target(&self) -> &str {
        &self.target
    }
    pub fn label(&self) -> &str {
        &self.label
    }
}

pub trait GraphStorePort {
    fn upsert_node(&mut self, node: &GraphNode) -> Result<(), StorageError>;
    fn upsert_edge(&mut self, edge: &GraphEdge) -> Result<(), StorageError>;
    fn query_nodes(&self, label: &str) -> Result<Vec<GraphNode>, StorageError>;
}
