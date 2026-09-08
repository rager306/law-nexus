//! Pure candidate-pair arbitration and capture-ceiling helpers.
//!
//! These helpers are kept in a neutral module so capture-path code can depend
//! on them without introducing a module cycle through `npa_bounds`.

/// Closed span relation between two half-open byte spans, counted once per
/// unordered candidate pair (ADR profile `contour_a` span-pair metrics).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpanRelation {
    /// Identical spans.
    Exact,
    /// One span strictly contains the other (either direction).
    Containment,
    /// Spans intersect without containment.
    PartialOverlap,
    /// Spans do not intersect.
    Disjoint,
}

impl SpanRelation {
    pub const fn as_str(self) -> &'static str {
        match self {
            SpanRelation::Exact => "exact",
            SpanRelation::Containment => "containment",
            SpanRelation::PartialOverlap => "partial_overlap",
            SpanRelation::Disjoint => "disjoint",
        }
    }
}

/// Pure span-pair classifier (order-independent: containment is reported
/// once regardless of which span contains which).
pub fn span_relation(a: (usize, usize), b: (usize, usize)) -> SpanRelation {
    let (a_start, a_end) = a;
    let (b_start, b_end) = b;
    if a_start == b_start && a_end == b_end {
        SpanRelation::Exact
    } else if (a_start <= b_start && b_end <= a_end) || (b_start <= a_start && a_end <= b_end) {
        SpanRelation::Containment
    } else if a_start < b_end && b_start < a_end {
        SpanRelation::PartialOverlap
    } else {
        SpanRelation::Disjoint
    }
}

/// Closed categorical diagnostic for one arbitration pair outcome. `as_str`
/// values are the `npa-capture-arbitration/v1` `diagnostics` ids verbatim
/// (D388): stable explicit text, never invented at a call site.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PairDiagnostic {
    /// Same span + identical explicit slots collapsed to one mention.
    DuplicateMatcherEvidenceMerged,
    /// Same span + non-identical slots: conflict set, no winner invented.
    ExactSpanSlotConflict,
    /// Containment with no pair policy (every policy is deferred-undefined).
    ContainmentWithoutPairPolicy,
    /// Partial overlap: conflict set, never execution-order resolution.
    PartialOverlapConflict,
}

impl PairDiagnostic {
    pub const fn as_str(self) -> &'static str {
        match self {
            PairDiagnostic::DuplicateMatcherEvidenceMerged => "duplicate_matcher_evidence_merged",
            PairDiagnostic::ExactSpanSlotConflict => "exact_span_slot_conflict",
            PairDiagnostic::ContainmentWithoutPairPolicy => "containment_without_pair_policy",
            PairDiagnostic::PartialOverlapConflict => "partial_overlap_conflict",
        }
    }
}

/// Closed categorical outcome for one candidate pair (D388
/// `npa-capture-arbitration/v1` defaults). Pair policies are
/// deferred-undefined, so every outcome either retains both candidates or
/// refuses into a conflict set — never a silently invented winner.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PairOutcome {
    /// Both candidates retained: disjoint (no diagnostic), or containment
    /// left ambiguous because no pair policy is selected.
    RetainBoth(Option<PairDiagnostic>),
    /// One mention; all pattern/origin evidence merged (same span +
    /// identical explicit slots).
    MergeEvidence(PairDiagnostic),
    /// Conflict set; arbitration is deferred downstream with this explicit
    /// diagnostic.
    ConflictSet(PairDiagnostic),
}

/// Pure categorical pair reducer over the production [`span_relation`]
/// classifier. `slots_equal`: every closed LawRefSlot holds an equal
/// explicit value (absence is not evidence). Fragment-local by construction
/// — callers pair candidates only inside one block, so no cross-block
/// arbitration exists to invent. No numeric threshold, no score, no
/// source-function-order precedence. Same span with any non-identical slot
/// fingerprint stays a conflict set: merging without a selected pair policy
/// would invent a winner.
pub fn arbitrate_pair(a: (usize, usize), b: (usize, usize), slots_equal: bool) -> PairOutcome {
    match span_relation(a, b) {
        SpanRelation::Exact if slots_equal => {
            PairOutcome::MergeEvidence(PairDiagnostic::DuplicateMatcherEvidenceMerged)
        }
        SpanRelation::Exact => PairOutcome::ConflictSet(PairDiagnostic::ExactSpanSlotConflict),
        SpanRelation::Containment => {
            // `subsumes`/`distinct_mentions` are deferred-undefined, so
            // containment stays ambiguous: both retained + explicit diagnostic.
            PairOutcome::RetainBoth(Some(PairDiagnostic::ContainmentWithoutPairPolicy))
        }
        SpanRelation::PartialOverlap => {
            PairOutcome::ConflictSet(PairDiagnostic::PartialOverlapConflict)
        }
        SpanRelation::Disjoint => PairOutcome::RetainBoth(None),
    }
}

/// Proposed contour-A candidate safety ceiling (D388 review gate
/// `contour-a-candidates-per-block-ceiling`, review
/// `m200-s03-outlier-review/v1`): a revisable `[proposed]` safety ceiling
/// with headroom over the observed per-block maximum 504 — never a claim
/// that larger legal structures do not exist, never a legal-universe
/// maximum, never the observed max or a histogram bucket edge. Raising it
/// requires a new review row. Product-path wiring is bounded defaults-only
/// admission in `capture_lawrefs`; pair policies remain deferred-undefined.
pub const PROPOSED_CANDIDATE_CEILING: u64 = 1024;

/// Pinned refusal diagnostic for the ceiling (the arbitration contract's
/// `diagnostics` id verbatim): produced when a capture candidate arrives
/// after a block already holds [`PROPOSED_CANDIDATE_CEILING`] accepted
/// candidates. Never minted ad hoc at a call site.
pub const CANDIDATE_LIMIT_REACHED: &str = "candidate_limit_reached";

/// Closed categorical result of one [`on_candidate_limit`] decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CandidateLimitOutcome {
    /// The incoming candidate is admitted; every earlier capture is
    /// untouched.
    Accepted,
    /// The incoming candidate is refused with [`CANDIDATE_LIMIT_REACHED`];
    /// refusal never truncates what the block already holds.
    LimitReached,
}

impl CandidateLimitOutcome {
    /// `true` only for [`CandidateLimitOutcome::Accepted`].
    pub const fn is_accepted(self) -> bool {
        matches!(self, CandidateLimitOutcome::Accepted)
    }

    /// Explicit diagnostic carried by the outcome: `None` while accepting,
    /// the pinned id on refusal — a refusal is never silent.
    pub const fn diagnostic(self) -> Option<&'static str> {
        match self {
            CandidateLimitOutcome::Accepted => None,
            CandidateLimitOutcome::LimitReached => Some(CANDIDATE_LIMIT_REACHED),
        }
    }
}

/// Pure `on_limit` enforcement of the `[proposed]` contour-A safety
/// ceiling. `accepted_count` is how many capture candidates the block
/// already holds; the incoming candidate is admitted exactly while
/// `accepted_count < PROPOSED_CANDIDATE_CEILING`, so the ceiling-th
/// candidate is accepted and the ceiling+1-th is refused. Stateless and
/// total: it decides, it never mutates, truncates, or silently drops
/// earlier captures — callers keep what they already accepted and surface
/// [`CandidateLimitOutcome::diagnostic`] verbatim on refusal.
pub const fn on_candidate_limit(accepted_count: u64) -> CandidateLimitOutcome {
    if accepted_count < PROPOSED_CANDIDATE_CEILING {
        CandidateLimitOutcome::Accepted
    } else {
        CandidateLimitOutcome::LimitReached
    }
}
