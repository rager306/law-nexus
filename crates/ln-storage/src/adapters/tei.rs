use crate::{EmbeddingPort, EmbeddingRequest, EmbeddingResponse, StorageError};

/// Transport abstraction for embedding service calls.
///
/// This trait abstracts the HTTP + JSON layer so that adapter tests can
/// inject controlled responses without an external service.
pub trait EmbeddingTransport {
    fn embed_text(&self, text: &str) -> Result<Vec<f32>, TransportError>;
}

/// Bounded transport error categories.
#[derive(Debug, Clone, PartialEq)]
pub enum TransportError {
    Unavailable,
    Timeout,
    BadResponse(String),
}

impl std::fmt::Display for TransportError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Unavailable => write!(formatter, "service unavailable"),
            Self::Timeout => write!(formatter, "request timeout"),
            Self::BadResponse(msg) => write!(formatter, "bad response: {msg}"),
        }
    }
}

impl std::error::Error for TransportError {}

/// TEI HTTP embedding adapter behind `EmbeddingPort`.
///
/// Uses an injectable `EmbeddingTransport` to abstract the real HTTP call.
/// Validates model identity, expected dimensions, response dimensions and
/// finite values before returning.
pub struct TeiEmbeddingAdapter<T: EmbeddingTransport> {
    transport: T,
    model_id: String,
    dimensions: usize,
}

impl<T: EmbeddingTransport> TeiEmbeddingAdapter<T> {
    pub fn try_new(transport: T, model_id: &str, dimensions: usize) -> Result<Self, StorageError> {
        if model_id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if dimensions == 0 {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            transport,
            model_id: model_id.to_owned(),
            dimensions,
        })
    }
}

impl<T: EmbeddingTransport> EmbeddingPort for TeiEmbeddingAdapter<T> {
    fn embed(&self, request: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        if request.model_id() != self.model_id {
            return Err(StorageError::ModelIdentityDrift {
                expected: self.model_id.clone(),
                actual: request.model_id().to_owned(),
            });
        }
        if request.expected_dimensions() != self.dimensions {
            return Err(StorageError::DimensionMismatch {
                expected: self.dimensions,
                actual: request.expected_dimensions(),
            });
        }

        let vector = self
            .transport
            .embed_text(request.text())
            .map_err(|error| StorageError::Internal(error.to_string()))?;

        if vector.len() != self.dimensions {
            return Err(StorageError::DimensionMismatch {
                expected: self.dimensions,
                actual: vector.len(),
            });
        }

        EmbeddingResponse::try_new(&self.model_id, vector)
    }
}
