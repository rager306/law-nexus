//! Model provenance contract for embedding artifacts.
//!
//! An embedding artifact must carry verifiable provenance for the model that
//! produced it: source, license, weights digest, vector dimension and model
//! parameters. Without complete provenance an artifact cannot be admitted.
//!
//! This module is dependency-free and serde-free. It defines only the
//! provenance value object and its fail-closed validation; it does not select,
//! download or embed a concrete model.
//!
//! Lifecycle: `[bounded]` contract preparation (ADR-0015).

use crate::StorageError;

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
}
