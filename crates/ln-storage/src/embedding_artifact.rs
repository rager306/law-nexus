//! Model provenance contract for embedding artifacts.
//!
//! An embedding artifact must carry verifiable provenance for the model that
//! produced it: source, license, weights digest, vector dimension and model
//! parameters. Without complete provenance an artifact cannot be admitted.
//!
//! This module is dependency-free and serde-free. It defines the provenance
//! value object, the fail-closed artifact contract, the raw artifact record and
//! its `admit` gate, and a reference composition (`ProvenancedEmbedding`) that
//! attaches provenance to an existing [`crate::EmbeddingPort`]. It does not
//! select, download or embed a concrete model.
//!
//! Lifecycle: `[bounded]` contract preparation (ADR-0015).

use crate::{EmbeddingPort, EmbeddingRequest, StorageError};

/// Verifiable provenance for the embedding model that produced an artifact.
///
/// The value is constructed only through [`ModelProvenance::try_new`], which
/// rejects incomplete or malformed provenance. Every field is required, so a
/// present `ModelProvenance` is itself the proof that provenance exists.
#[derive(Debug, Clone, PartialEq)]
pub struct ModelProvenance {
    source: String,
    license: String,
    weights_sha256: String,
    dimensions: usize,
    parameters: Vec<(String, String)>,
}

impl ModelProvenance {
    /// Build provenance, rejecting incomplete or malformed fields.
    ///
    /// Fail-closed rules:
    /// - `source` and `license` must be non-empty (trimmed);
    /// - `weights_sha256` must be exactly `sha256:` + 64 lower-case hex digits;
    /// - `dimensions` must be greater than zero;
    /// - `parameters` must be non-empty with unique, non-empty keys.
    pub fn try_new(
        source: &str,
        license: &str,
        weights_sha256: &str,
        dimensions: usize,
        parameters: Vec<(String, String)>,
    ) -> Result<Self, StorageError> {
        if source.trim().is_empty() {
            return Err(StorageError::InvalidProvenanceField("source"));
        }
        if license.trim().is_empty() {
            return Err(StorageError::InvalidProvenanceField("license"));
        }
        if !is_sha256_digest(weights_sha256) {
            return Err(StorageError::InvalidProvenanceField("weights_sha256"));
        }
        if dimensions == 0 {
            return Err(StorageError::InvalidProvenanceField("dimensions"));
        }
        if parameters.is_empty() {
            return Err(StorageError::InvalidProvenanceField("parameters"));
        }
        let mut seen_keys: Vec<&str> = Vec::with_capacity(parameters.len());
        for (key, _value) in &parameters {
            if key.trim().is_empty() {
                return Err(StorageError::InvalidProvenanceField("parameters"));
            }
            if seen_keys.contains(&key.as_str()) {
                return Err(StorageError::InvalidProvenanceField("parameters"));
            }
            seen_keys.push(key.as_str());
        }
        Ok(Self {
            source: source.to_owned(),
            license: license.to_owned(),
            weights_sha256: weights_sha256.to_owned(),
            dimensions,
            parameters,
        })
    }

    /// Model source identifier (for example a repository or registry URL).
    pub fn source(&self) -> &str {
        &self.source
    }

    /// License identifier under which the model weights are distributed.
    pub fn license(&self) -> &str {
        &self.license
    }

    /// Canonical weights digest in `sha256:<64 lower-hex>` form.
    pub fn weights_sha256(&self) -> &str {
        &self.weights_sha256
    }

    /// Vector dimensionality the model produces.
    pub fn dimensions(&self) -> usize {
        self.dimensions
    }

    /// Model configuration parameters as unique key/value pairs.
    pub fn parameters(&self) -> &[(String, String)] {
        &self.parameters
    }

    /// Deterministic, serde-free canonical rendering of the provenance.
    ///
    /// Parameters are sorted by key, so two provenances that differ only in
    /// parameter order render identically. The result is stable input for
    /// later pinning or digesting and carries no legal text.
    pub fn canonical_string(&self) -> String {
        let mut params: Vec<&(String, String)> = self.parameters.iter().collect();
        params.sort_by(|a, b| a.0.cmp(&b.0));
        let rendered = params
            .iter()
            .map(|(key, value)| format!("{key}={value}"))
            .collect::<Vec<_>>()
            .join(",");
        format!(
            "source={};license={};weights_sha256={};dimensions={};parameters=[{rendered}]",
            self.source, self.license, self.weights_sha256, self.dimensions
        )
    }
}

/// Strict `sha256:` + 64 lower-case hex digest check.
fn is_sha256_digest(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("sha256:") else {
        return false;
    };
    hex.len() == 64
        && hex
            .bytes()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
}

/// A validated embedding artifact: a subject reference, its vector and the
/// provenance of the model that produced it.
///
/// The only way to build one is [`EmbeddingArtifact::try_new`], which fails
/// closed when the subject is empty, the vector is empty or non-finite, or the
/// vector length disagrees with the provenance dimensions. Because a
/// `ModelProvenance` can only be built through validation, a present artifact
/// is itself the proof that provenance exists.
#[derive(Debug, Clone, PartialEq)]
pub struct EmbeddingArtifact {
    subject_ref: String,
    vector: Vec<f32>,
    provenance: ModelProvenance,
}

impl EmbeddingArtifact {
    /// Build an artifact, rejecting incomplete or inconsistent input.
    ///
    /// Fail-closed rules:
    /// - `subject_ref` must be non-empty (trimmed) - otherwise [`StorageError::EmptyInput`];
    /// - `vector` must be non-empty - otherwise [`StorageError::EmptyInput`];
    /// - every vector value must be finite - otherwise [`StorageError::NonFiniteValue`];
    /// - `vector.len()` must equal [`ModelProvenance::dimensions`] - otherwise
    ///   [`StorageError::DimensionMismatch`].
    pub fn try_new(
        subject_ref: &str,
        vector: Vec<f32>,
        provenance: ModelProvenance,
    ) -> Result<Self, StorageError> {
        if subject_ref.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.is_empty() {
            return Err(StorageError::EmptyInput);
        }
        if vector.iter().any(|value| !value.is_finite()) {
            return Err(StorageError::NonFiniteValue);
        }
        if vector.len() != provenance.dimensions() {
            return Err(StorageError::DimensionMismatch {
                expected: provenance.dimensions(),
                actual: vector.len(),
            });
        }
        Ok(Self {
            subject_ref: subject_ref.to_owned(),
            vector,
            provenance,
        })
    }

    /// Subject reference the vector was embedded for.
    pub fn subject_ref(&self) -> &str {
        &self.subject_ref
    }

    /// The embedding vector.
    pub fn vector(&self) -> &[f32] {
        &self.vector
    }

    /// Provenance of the model that produced the vector.
    pub fn provenance(&self) -> &ModelProvenance {
        &self.provenance
    }

    /// Vector dimensionality (equal to [`ModelProvenance::dimensions`]).
    pub fn dimensions(&self) -> usize {
        self.vector.len()
    }
}

/// A raw embedding artifact record that may or may not carry provenance.
///
/// The record is an unvalidated carrier: `admit` is the fail-closed gate that
/// turns it into an [`EmbeddingArtifact`]. A record without provenance is never
/// admitted - `admit` returns [`StorageError::MissingProvenance`] instead of
/// panicking or inventing a vector.
#[derive(Debug, Clone, PartialEq)]
pub struct EmbeddingArtifactRecord {
    subject_ref: String,
    vector: Vec<f32>,
    provenance: Option<ModelProvenance>,
}

impl EmbeddingArtifactRecord {
    /// Build a raw record. No validation happens here; call [`Self::admit`] to
    /// obtain a validated artifact.
    pub fn new(subject_ref: &str, vector: Vec<f32>, provenance: Option<ModelProvenance>) -> Self {
        Self {
            subject_ref: subject_ref.to_owned(),
            vector,
            provenance,
        }
    }

    /// Subject reference the vector was embedded for.
    pub fn subject_ref(&self) -> &str {
        &self.subject_ref
    }

    /// The raw embedding vector.
    pub fn vector(&self) -> &[f32] {
        &self.vector
    }

    /// Provenance, if the record carried any.
    pub fn provenance(&self) -> Option<&ModelProvenance> {
        self.provenance.as_ref()
    }

    /// Admit the record as a validated artifact.
    ///
    /// Returns [`StorageError::MissingProvenance`] when the record carries no
    /// provenance; otherwise delegates to [`EmbeddingArtifact::try_new`], so
    /// empty subjects, empty/non-finite vectors and dimension mismatches are
    /// rejected there.
    pub fn admit(self) -> Result<EmbeddingArtifact, StorageError> {
        match self.provenance {
            None => Err(StorageError::MissingProvenance),
            Some(provenance) => {
                EmbeddingArtifact::try_new(&self.subject_ref, self.vector, provenance)
            }
        }
    }
}

/// A request to embed a subject through a provenance-bearing port.
#[derive(Debug, Clone, PartialEq)]
pub struct EmbeddingArtifactRequest {
    subject_ref: String,
    text: String,
}

impl EmbeddingArtifactRequest {
    /// Build a request, rejecting empty (trimmed) fields.
    pub fn try_new(subject_ref: &str, text: &str) -> Result<Self, StorageError> {
        if subject_ref.trim().is_empty() || text.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            subject_ref: subject_ref.to_owned(),
            text: text.to_owned(),
        })
    }

    /// Subject reference the embedding is requested for.
    pub fn subject_ref(&self) -> &str {
        &self.subject_ref
    }

    /// Source text to embed.
    pub fn text(&self) -> &str {
        &self.text
    }
}

/// Port for producing provenance-bearing embedding artifacts.
pub trait EmbeddingArtifactPort {
    /// Embed the request and return a validated artifact carrying provenance.
    fn embed_artifact(
        &self,
        request: &EmbeddingArtifactRequest,
    ) -> Result<EmbeddingArtifact, StorageError>;
}

/// Reference composition that binds a [`ModelProvenance`] to an existing
/// [`EmbeddingPort`].
///
/// `ProvenancedEmbedding` holds the expected `model_id` and the provenance to
/// attach. It delegates to `E::embed`, then rejects model identity drift and
/// dimension desynchronisation before attaching provenance. The wrapped
/// `EmbeddingPort` is not modified.
pub struct ProvenancedEmbedding<E: EmbeddingPort> {
    embedder: E,
    model_id: String,
    provenance: ModelProvenance,
}

impl<E: EmbeddingPort> ProvenancedEmbedding<E> {
    /// Bind an embedder to a model identity and its provenance.
    ///
    /// Rejects an empty (trimmed) `model_id`. Expected dimensions are taken
    /// from [`ModelProvenance::dimensions`].
    pub fn try_new(
        embedder: E,
        model_id: &str,
        provenance: ModelProvenance,
    ) -> Result<Self, StorageError> {
        if model_id.trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        Ok(Self {
            embedder,
            model_id: model_id.to_owned(),
            provenance,
        })
    }

    /// Expected model identity.
    pub fn model_id(&self) -> &str {
        &self.model_id
    }

    /// Provenance attached to produced artifacts.
    pub fn provenance(&self) -> &ModelProvenance {
        &self.provenance
    }
}

impl<E: EmbeddingPort> EmbeddingArtifactPort for ProvenancedEmbedding<E> {
    fn embed_artifact(
        &self,
        request: &EmbeddingArtifactRequest,
    ) -> Result<EmbeddingArtifact, StorageError> {
        let embed_request = EmbeddingRequest::try_new(
            request.text(),
            &self.model_id,
            self.provenance.dimensions(),
        )?;
        let response = self.embedder.embed(&embed_request)?;
        if response.model_id() != self.model_id {
            return Err(StorageError::ModelIdentityDrift {
                expected: self.model_id.clone(),
                actual: response.model_id().to_owned(),
            });
        }
        if response.dimensions() != self.provenance.dimensions() {
            return Err(StorageError::DimensionMismatch {
                expected: self.provenance.dimensions(),
                actual: response.dimensions(),
            });
        }
        EmbeddingArtifact::try_new(
            request.subject_ref(),
            response.vector().to_vec(),
            self.provenance.clone(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_parameters() -> Vec<(String, String)> {
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ]
    }

    fn valid_hash() -> String {
        format!("sha256:{}", "a".repeat(64))
    }

    fn valid_provenance() -> ModelProvenance {
        ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            valid_parameters(),
        )
        .expect("valid provenance must be accepted")
    }

    #[test]
    fn accepts_valid_provenance() {
        let provenance = valid_provenance();
        assert_eq!(provenance.source(), "https://example.invalid/model");
        assert_eq!(provenance.license(), "Apache-2.0");
        assert_eq!(provenance.weights_sha256(), valid_hash());
        assert_eq!(provenance.dimensions(), 768);
        assert_eq!(provenance.parameters().len(), 2);
    }

    #[test]
    fn rejects_empty_source() {
        let result =
            ModelProvenance::try_new("   ", "Apache-2.0", &valid_hash(), 768, valid_parameters());
        assert_eq!(result, Err(StorageError::InvalidProvenanceField("source")));
    }

    #[test]
    fn rejects_empty_license() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "",
            &valid_hash(),
            768,
            valid_parameters(),
        );
        assert_eq!(result, Err(StorageError::InvalidProvenanceField("license")));
    }

    #[test]
    fn rejects_hash_without_prefix() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &"a".repeat(64),
            768,
            valid_parameters(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("weights_sha256"))
        );
    }

    #[test]
    fn rejects_short_hash() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            "sha256:abcd",
            768,
            valid_parameters(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("weights_sha256"))
        );
    }

    #[test]
    fn rejects_uppercase_hash() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &format!("sha256:{}", "A".repeat(64)),
            768,
            valid_parameters(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("weights_sha256"))
        );
    }

    #[test]
    fn rejects_non_hex_hash() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &format!("sha256:{}", "g".repeat(64)),
            768,
            valid_parameters(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("weights_sha256"))
        );
    }

    #[test]
    fn rejects_zero_dimensions() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            0,
            valid_parameters(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("dimensions"))
        );
    }

    #[test]
    fn rejects_empty_parameters() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            Vec::new(),
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("parameters"))
        );
    }

    #[test]
    fn rejects_empty_parameter_key() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            vec![("  ".to_owned(), "value".to_owned())],
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("parameters"))
        );
    }

    #[test]
    fn rejects_duplicate_parameter_keys() {
        let result = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            vec![
                ("pooling".to_owned(), "mean".to_owned()),
                ("pooling".to_owned(), "cls".to_owned()),
            ],
        );
        assert_eq!(
            result,
            Err(StorageError::InvalidProvenanceField("parameters"))
        );
    }

    #[test]
    fn canonical_string_is_deterministic_across_parameter_order() {
        let forward = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            vec![
                ("normalize".to_owned(), "true".to_owned()),
                ("pooling".to_owned(), "mean".to_owned()),
            ],
        )
        .expect("valid provenance");
        let reversed = ModelProvenance::try_new(
            "https://example.invalid/model",
            "Apache-2.0",
            &valid_hash(),
            768,
            vec![
                ("pooling".to_owned(), "mean".to_owned()),
                ("normalize".to_owned(), "true".to_owned()),
            ],
        )
        .expect("valid provenance");

        assert_eq!(forward.canonical_string(), reversed.canonical_string());
        assert!(forward
            .canonical_string()
            .contains("parameters=[normalize=true,pooling=mean]"));
    }

    // --- Embedding artifact contract ---

    fn valid_artifact() -> EmbeddingArtifact {
        EmbeddingArtifact::try_new("doc-1", vec![0.5; 768], valid_provenance())
            .expect("valid artifact must be accepted")
    }

    #[test]
    fn artifact_accepts_valid_input() {
        let artifact = valid_artifact();
        assert_eq!(artifact.subject_ref(), "doc-1");
        assert_eq!(artifact.vector().len(), 768);
        assert_eq!(artifact.dimensions(), 768);
        assert_eq!(artifact.provenance().weights_sha256(), valid_hash());
    }

    #[test]
    fn artifact_rejects_empty_subject() {
        assert_eq!(
            EmbeddingArtifact::try_new("   ", vec![0.5; 768], valid_provenance()),
            Err(StorageError::EmptyInput)
        );
    }

    #[test]
    fn artifact_rejects_empty_vector() {
        assert_eq!(
            EmbeddingArtifact::try_new("doc-1", Vec::new(), valid_provenance()),
            Err(StorageError::EmptyInput)
        );
    }

    #[test]
    fn artifact_rejects_non_finite_vector() {
        let mut vector = vec![0.5_f32; 768];
        vector[0] = f32::NAN;
        assert_eq!(
            EmbeddingArtifact::try_new("doc-1", vector, valid_provenance()),
            Err(StorageError::NonFiniteValue)
        );
    }

    #[test]
    fn artifact_rejects_dimension_mismatch() {
        assert_eq!(
            EmbeddingArtifact::try_new("doc-1", vec![0.5; 4], valid_provenance()),
            Err(StorageError::DimensionMismatch {
                expected: 768,
                actual: 4,
            })
        );
    }

    #[test]
    fn record_without_provenance_is_rejected() {
        let record = EmbeddingArtifactRecord::new("doc-1", vec![0.5; 768], None);
        assert!(record.provenance().is_none());
        assert_eq!(record.admit(), Err(StorageError::MissingProvenance));
    }

    #[test]
    fn record_with_provenance_is_admitted() {
        let record =
            EmbeddingArtifactRecord::new("doc-1", vec![0.5; 768], Some(valid_provenance()));
        let artifact = record.admit().expect("record with provenance admits");
        assert_eq!(artifact.subject_ref(), "doc-1");
        assert_eq!(artifact.dimensions(), 768);
    }

    #[test]
    fn request_rejects_empty_fields() {
        assert_eq!(
            EmbeddingArtifactRequest::try_new("", "text"),
            Err(StorageError::EmptyInput)
        );
        assert_eq!(
            EmbeddingArtifactRequest::try_new("doc-1", "  "),
            Err(StorageError::EmptyInput)
        );
    }

    struct StubEmbedding {
        response_model_id: String,
        dimensions: usize,
    }

    impl EmbeddingPort for StubEmbedding {
        fn embed(
            &self,
            _request: &EmbeddingRequest,
        ) -> Result<crate::EmbeddingResponse, StorageError> {
            crate::EmbeddingResponse::try_new(&self.response_model_id, vec![0.25; self.dimensions])
        }
    }

    fn request() -> EmbeddingArtifactRequest {
        EmbeddingArtifactRequest::try_new("doc-1", "contract legal text")
            .expect("valid artifact request")
    }

    #[test]
    fn provenanced_embedding_attaches_provenance() {
        let embedder = StubEmbedding {
            response_model_id: "stub-model".to_owned(),
            dimensions: 768,
        };
        let port = ProvenancedEmbedding::try_new(embedder, "stub-model", valid_provenance())
            .expect("valid composition");
        let artifact = port
            .embed_artifact(&request())
            .expect("honest embedder must yield an artifact");
        assert_eq!(artifact.subject_ref(), "doc-1");
        assert_eq!(artifact.dimensions(), 768);
        assert_eq!(
            artifact.provenance().source(),
            "https://example.invalid/model"
        );
    }

    #[test]
    fn provenanced_embedding_rejects_model_drift() {
        let embedder = StubEmbedding {
            response_model_id: "other-model".to_owned(),
            dimensions: 768,
        };
        let port = ProvenancedEmbedding::try_new(embedder, "stub-model", valid_provenance())
            .expect("valid composition");
        assert!(matches!(
            port.embed_artifact(&request()),
            Err(StorageError::ModelIdentityDrift { .. })
        ));
    }

    #[test]
    fn provenanced_embedding_rejects_dimension_desync() {
        let embedder = StubEmbedding {
            response_model_id: "stub-model".to_owned(),
            dimensions: 4,
        };
        let port = ProvenancedEmbedding::try_new(embedder, "stub-model", valid_provenance())
            .expect("valid composition");
        assert!(matches!(
            port.embed_artifact(&request()),
            Err(StorageError::DimensionMismatch { .. })
        ));
    }

    #[test]
    fn provenanced_embedding_rejects_empty_model_id() {
        let embedder = StubEmbedding {
            response_model_id: "stub-model".to_owned(),
            dimensions: 768,
        };
        assert!(matches!(
            ProvenancedEmbedding::try_new(embedder, "   ", valid_provenance()),
            Err(StorageError::EmptyInput)
        ));
    }
}
