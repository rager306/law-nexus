//! Contract tests for the pure cosine similarity helper.
//!
//! These tests define the retrieval ranking semantics: the score between a
//! query vector and a stored vector. The helper is a pure function with no
//! adapter state. Lifecycle: [bounded] — exact arithmetic on f32 slices; no
//! live embedding or corpus claim.

use ln_storage::{cosine_similarity, StorageError};

#[test]
fn identical_vectors_score_one() {
    let v = [0.5_f32, 0.3, 0.2];
    assert!((cosine_similarity(&v, &v).unwrap() - 1.0).abs() < 1e-9);
}

#[test]
fn scaled_identical_vectors_score_one() {
    // Same direction, different magnitude: cosine is scale-invariant.
    let a = [0.5_f32, 0.3, 0.2];
    let b = [1.0_f32, 0.6, 0.4]; // a * 2
    assert!((cosine_similarity(&a, &b).unwrap() - 1.0).abs() < 1e-6);
}

#[test]
fn orthogonal_vectors_score_zero() {
    let a = [1.0_f32, 0.0];
    let b = [0.0_f32, 1.0];
    assert!((cosine_similarity(&a, &b).unwrap() - 0.0).abs() < 1e-9);
}

#[test]
fn opposite_vectors_score_zero_for_retrieval() {
    // Opposite direction maps to 0.0 relevance: an anti-correlated document is
    // not a relevant retrieval result. Negative cosine is clamped to [0,1].
    let a = [1.0_f32, 0.0];
    let b = [-1.0_f32, 0.0];
    assert!((cosine_similarity(&a, &b).unwrap() - 0.0).abs() < 1e-9);
}

#[test]
fn forty_five_degrees_scores_half() {
    // cos(45deg) ~= 0.7071; relevance clamp leaves it intact.
    let a = [1.0_f32, 0.0];
    let b = [1.0_f32, 1.0]; // 45 degrees from a
    assert!((cosine_similarity(&a, &b).unwrap() - std::f64::consts::FRAC_1_SQRT_2).abs() < 1e-6);
}

#[test]
fn zero_norm_vector_scores_zero() {
    // A zero vector has no direction; defined convention is 0.0 similarity.
    let a = [0.0_f32, 0.0];
    let b = [1.0_f32, 0.0];
    assert!((cosine_similarity(&a, &b).unwrap() - 0.0).abs() < 1e-9);
    // Symmetric in the other direction.
    assert!((cosine_similarity(&b, &a).unwrap() - 0.0).abs() < 1e-9);
}

#[test]
fn dimension_mismatch_is_rejected() {
    let a = [1.0_f32, 0.0];
    let b = [1.0_f32, 0.0, 0.0];
    assert_eq!(
        cosine_similarity(&a, &b),
        Err(StorageError::DimensionMismatch {
            expected: 2,
            actual: 3
        })
    );
}

#[test]
fn empty_slices_are_rejected() {
    let a: [f32; 0] = [];
    let b: [f32; 0] = [];
    assert_eq!(cosine_similarity(&a, &b), Err(StorageError::EmptyInput));
}
