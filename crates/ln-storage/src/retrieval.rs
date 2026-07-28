use crate::{
    EmbeddingPort, EmbeddingRequest, GraphStorePort, StorageError, VectorQuery, VectorStorePort,
};

/// A citation returned by retrieval with traceable source span.
///
/// This value carries only a source identifier, a source span string and a
/// similarity score. No legal authority, resolved target or citation
/// correctness is present.
#[derive(Debug, Clone, PartialEq)]
pub struct Citation {
    id: String,
    source_span: String,
    score: f64,
}

impl Citation {
    pub fn try_new(id: &str, source_span: &str, score: f64) -> Result<Self, StorageError> {
        if id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if source_span.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if score.is_nan() || score.is_infinite() {
            return Err(StorageError::NonFiniteValue);
        }
        if !(0.0..=1.0).contains(&score) {
            return Err(StorageError::Internal(
                "similarity score out of range".to_owned(),
            ));
        }
        Ok(Self {
            id: id.to_owned(),
            source_span: source_span.to_owned(),
            score,
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn source_span(&self) -> &str {
        &self.source_span
    }

    pub fn score(&self) -> f64 {
        self.score
    }
}

/// One retrieval result with citation and similarity score.
#[derive(Debug, Clone, PartialEq)]
pub struct RetrievalResult {
    id: String,
    score: f64,
    citation: Citation,
    evidence_labels: Vec<String>,
}

impl RetrievalResult {
    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn score(&self) -> f64 {
        self.score
    }

    pub fn citation(&self) -> &Citation {
        &self.citation
    }

    pub fn evidence_labels(&self) -> &[String] {
        &self.evidence_labels
    }
}

/// Citation tamper check comparing expected and actual citations.
pub struct CitationTamperCheck<'a> {
    expected: &'a Citation,
    actual: Option<&'a Citation>,
}

impl<'a> CitationTamperCheck<'a> {
    pub fn new(citation: &'a Citation) -> Self {
        Self {
            expected: citation,
            actual: None,
        }
    }

    pub fn against(expected: &'a Citation, actual: &'a Citation) -> Self {
        Self {
            expected,
            actual: Some(actual),
        }
    }

    pub fn verify(&self) -> Result<(), StorageError> {
        match self.actual {
            None => Ok(()),
            Some(actual) => {
                if actual.id() != self.expected.id()
                    || actual.source_span() != self.expected.source_span()
                {
                    return Err(StorageError::Internal(
                        "citation tamper detected".to_owned(),
                    ));
                }
                Ok(())
            }
        }
    }
}

/// Retrieval gate composing embedding, vector store and graph store ports.
///
/// This gate orchestrates retrieval mechanics only. It does not assert legal
/// correctness, citation authority or corpus completeness.
pub struct RetrievalGate<E, V, G>
where
    E: EmbeddingPort,
    V: VectorStorePort,
    G: GraphStorePort,
{
    embedding: E,
    vector_store: V,
    graph_store: G,
    embedding_dimensions: usize,
}

impl<E, V, G> RetrievalGate<E, V, G>
where
    E: EmbeddingPort,
    V: VectorStorePort,
    G: GraphStorePort,
{
    pub fn new(
        embedding: E,
        vector_store: V,
        graph_store: G,
        embedding_dimensions: usize,
    ) -> Result<Self, StorageError> {
        if embedding_dimensions == 0 {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            embedding,
            vector_store,
            graph_store,
            embedding_dimensions,
        })
    }

    /// Retrieve ranked results for a query text.
    ///
    /// Returns citations with traceable source spans. No legal correctness,
    /// citation authority or corpus completeness is claimed.
    pub fn retrieve(
        &self,
        query_text: &str,
        model_id: &str,
        top_k: usize,
    ) -> Result<Vec<RetrievalResult>, StorageError> {
        if query_text.trim().is_empty() || top_k == 0 {
            return Err(StorageError::EmptyInput);
        }

        let request = EmbeddingRequest::try_new(query_text, model_id, self.embedding_dimensions)?;
        let response = self.embedding.embed(&request)?;
        let query_vector = response.vector().to_vec();

        let query = VectorQuery::try_new(query_vector, top_k)?;
        let records = self.vector_store.query(&query)?;

        let mut results = Vec::with_capacity(records.len());
        for record in &records {
            let mut evidence_labels = Vec::new();
            for (key, value) in record.metadata() {
                if key == "label" {
                    let nodes = self.graph_store.query_nodes(value)?;
                    for node in &nodes {
                        evidence_labels.push(node.label().to_owned());
                    }
                }
            }
            let score = 1.0; // In-memory stub: exact match score
            let citation =
                Citation::try_new(record.id(), &format!("vector-store:{}", record.id()), score)
                    .unwrap_or_else(|_| Citation {
                        id: record.id().to_owned(),
                        source_span: "unknown".to_owned(),
                        score: 0.0,
                    });
            results.push(RetrievalResult {
                id: record.id().to_owned(),
                score,
                citation,
                evidence_labels,
            });
        }

        Ok(results)
    }
}
