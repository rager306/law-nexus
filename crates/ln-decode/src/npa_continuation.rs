//! RC28-F07 continuation eligibility (M211 S03, ADR-0029).
//!
//! Single source of truth for one question: *may this frame stand as the head
//! of a series that an open coordination continues?* The predicate is a
//! conjunction of proof obligations — never a proximity or multiplicity vote.
//! The D385 `document_context` overlay and the derived `npa_link` pipeline
//! both delegate here, so the rule cannot drift into a second, weaker copy
//! (D612).
//!
//! No external (de)serialization crate, filesystem, or environment access
//! (D602); the predicate is allocation-free and has no I/O.

/// The boolean clauses of RC28-F07 continuation-head eligibility.
///
/// Callers map their own private frame fields onto these clauses; the
/// predicate has no dependency on any frame representation, so the
/// block/scope/order vocabulary of each consumer stays local.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ContinuationEligibility {
    /// The candidate head frame is fully proven (`Proposed`: no unresolved,
    /// ambiguous, or incomplete member).
    pub head_status_proposed: bool,
    /// The tail is not `Rejected`; a rejected frame never continues.
    pub tail_status_not_rejected: bool,
    /// Head and tail are different frames (never self-continuation).
    pub distinct_frames: bool,
    /// Head and tail live in different source blocks (never intra-block).
    pub distinct_blocks: bool,
    /// The grammar admitted an act type inside the head's own block. A frame
    /// whose act type was never admitted locally can only ever be a tail.
    pub head_admits_act_type: bool,
    /// Head precedes tail in source-block *document order* — never a
    /// comparison of fragment-local offsets (RC28-F07).
    pub head_order_before_tail: bool,
    /// Head and tail share the nearest structural scope/boundary.
    pub same_scope: bool,
    /// The head retains a real source-local derivation span.
    pub head_retains_derivation: bool,
    /// The tail retains a real source-local derivation span.
    pub tail_retains_derivation: bool,
}

/// RC28-F07: a head is eligible for a tail only when every clause holds.
pub fn eligible_continuation_head_for(eligibility: &ContinuationEligibility) -> bool {
    eligibility.head_status_proposed
        && eligibility.tail_status_not_rejected
        && eligibility.distinct_frames
        && eligibility.distinct_blocks
        && eligibility.head_admits_act_type
        && eligibility.head_order_before_tail
        && eligibility.same_scope
        && eligibility.head_retains_derivation
        && eligibility.tail_retains_derivation
}

#[cfg(test)]
mod tests {
    use super::*;

    fn all_true() -> ContinuationEligibility {
        ContinuationEligibility {
            head_status_proposed: true,
            tail_status_not_rejected: true,
            distinct_frames: true,
            distinct_blocks: true,
            head_admits_act_type: true,
            head_order_before_tail: true,
            same_scope: true,
            head_retains_derivation: true,
            tail_retains_derivation: true,
        }
    }

    #[test]
    fn every_clause_is_load_bearing() {
        assert!(eligible_continuation_head_for(&all_true()));
        for clause in 0..9 {
            let mut e = all_true();
            match clause {
                0 => e.head_status_proposed = false,
                1 => e.tail_status_not_rejected = false,
                2 => e.distinct_frames = false,
                3 => e.distinct_blocks = false,
                4 => e.head_admits_act_type = false,
                5 => e.head_order_before_tail = false,
                6 => e.same_scope = false,
                7 => e.head_retains_derivation = false,
                _ => e.tail_retains_derivation = false,
            }
            assert!(
                !eligible_continuation_head_for(&e),
                "clause {clause} must be load-bearing"
            );
        }
    }

    #[test]
    fn default_is_ineligible() {
        assert!(!eligible_continuation_head_for(
            &ContinuationEligibility::default()
        ));
    }
}
