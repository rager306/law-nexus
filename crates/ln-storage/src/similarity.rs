//! Pure cosine similarity helper for retrieval ranking.
//!
//! Bounded exact arithmetic over `f32` slices. No adapter state, no live
//! embedding claim. Used by the in-memory vector store (top-k selection) and
//! the retrieval gate (per-result score) so the end-to-end retrieval process
//! ranks by real directional similarity instead of a constant score.
//!
//! Lifecycle: [bounded].

use crate::StorageError;

/// Minimum norm below which a vector is treated as directionless (zero vector).
const ZERO_NORM_EPSILON: f64 = 1e-12;

/// Compute cosine directional similarity between two equal-length vectors,
/// clamped to the `[0.0, 1.0]` retrieval-relevance range.
///
/// Semantics:
/// - identical or scaled-identical directions -> `1.0`
/// - orthogonal directions -> `0.0`
/// - opposite (anti-correlated) directions -> `0.0` (not relevant, clamped)
/// - a zero-norm vector on either side -> `0.0` (no direction)
/// - dimension mismatch -> [`StorageError::DimensionMismatch`]
/// - empty slices -> [`StorageError::EmptyInput`]
///
/// Non-finite values are rejected upstream by `VectorRecord`/`VectorQuery`
/// construction, so this helper assumes finite inputs.
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> Result<f64, StorageError> {
    if a.is_empty() || b.is_empty() {
        return Err(StorageError::EmptyInput);
    }
    if a.len() != b.len() {
        return Err(StorageError::DimensionMismatch {
            expected: a.len(),
            actual: b.len(),
        });
    }

    let mut dot: f64 = 0.0;
    let mut norm_a: f64 = 0.0;
    let mut norm_b: f64 = 0.0;
    for (x, y) in a.iter().zip(b.iter()) {
        let x = f64::from(*x);
        let y = f64::from(*y);
        dot += x * y;
        norm_a += x * x;
        norm_b += y * y;
    }
    norm_a = norm_a.sqrt();
    norm_b = norm_b.sqrt();

    if norm_a < ZERO_NORM_EPSILON || norm_b < ZERO_NORM_EPSILON {
        return Ok(0.0);
    }

    let cosine = dot / (norm_a * norm_b);
    // Clamp to [0.0, 1.0]: negative cosine (anti-correlated) is not relevant for
    // retrieval; tiny float overshoot above 1.0 from rounding is pinned to 1.0.
    // Inputs are finite (upstream VectorRecord/VectorQuery reject non-finite)
    // and norms are non-zero (guarded above), so `cosine` is finite here.
    Ok(cosine.clamp(0.0, 1.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_input_branch() {
        let a: [f32; 0] = [];
        assert_eq!(cosine_similarity(&a, &a), Err(StorageError::EmptyInput));
    }
}
