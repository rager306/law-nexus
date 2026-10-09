//! Proof-local resolution graph for offline citation-safe retrieval.
//!
//! This module binds the S01 [`OutputIdResolutionPort`] to a real source: the
//! M213 cleaned projection read back from a pinned reader fixture. It derives a
//! deterministic, proof-local resolution graph from a [`CleanedProjection`] and
//! exposes it through the validator port so an offline envelope can be checked
//! without any network call, product API, embedding, LLM, or new crate
//! dependency.
//!
//! The contract is frozen in
//! `prd/retrieval/rust_offline_citation_retrieval_contract.md`.
//!
//! Mapping (decision D719): one [`SourceDocumentId`] per projection derived from
//! `proj.source.sha256`; one [`SourceBlockId`] per view node; one
//! [`EvidenceSpanId`] per segment node with status
//! [`EvidenceSpanStatus::Active`]; and a single [`LegalUnitId`] /
//! [`ActEditionId`] pair of bounded proof-local anchors derived from the source
//! snapshot identity, with validity covering any declared scope `as_of_date`.
//!
//! Non-promotion (decision D714): these identifiers are validator-envelope
//! proof-local tokens, not production domain entities. No
//! `prd/temporal-legal-model.md` §3 row is created and the `SourceBlock` row
//! stays `deferred-undefined`.
//!
//! Fail-closed: an unknown identifier resolves to `None`/`Unresolved`, an
//! edition resolves only inside its validity window, `is_superseded` is `false`
//! for `Active` spans, and the adapter never repairs, infers, downgrades, or
//! best-effort matches an identifier. The projection is borrowed and never
//! mutated.
//!
//! On top of the resolver the module implements the deterministic offline
//! citation-safe retrieval proof: the closed query-kind / selection-reason /
//! expected-result vocabularies ([`RetrievalQueryKind`],
//! [`OfflineSelectionReason`], [`OfflineExpectedResult`]), a case model
//! ([`OfflineRetrievalCase`], [`OfflineCaseOutcome`]) and the bounded
//! [`OfflineRetrievalProofSummary`]. Candidate selection walks the cleaned
//! projection's segment nodes in deterministic order using only closed
//! view/segment/reference kind criteria; zero matches emit a safe scoped
//! no-answer, more than one rejects without arbitrary choice, and a selected
//! candidate is converted to a validator envelope and run through
//! [`validate_retrieval_output`]. An unresolvable citation always yields
//! `rejected`: an accepted answer without a resolvable citation is never
//! emitted. Nothing in the walk ranks, embeds, calls an LLM, or touches the
//! network.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::error::Error;
use std::fmt;

use ln_decode::cleaned_wire::CleanedProjection;
use ln_decode::reader_contract::{
    ReaderReferenceType, ReaderSegmentKind, ReaderSemantic, ReaderViewKind,
};
use ln_decode::reader_projection::{ProjectedSegment, ProjectedView, ReaderProjection};

use crate::domain::QueryId;
use crate::retrieval_output::{
    validate_retrieval_output, ActEditionId, ActEditionRecord, CitationBinding, CitationKey,
    CitationKeyResolution, EvidenceSpanId, EvidenceSpanRecord, EvidenceSpanStatus, FieldShape,
    LegalActId, LegalUnitId, LegalUnitRecord, OutputDiagnosticCode, OutputIdResolutionPort,
    OutputKind, OutputScope, OutputScopeId, OutputVerdict, RetrievalOutputEnvelope,
    RetrievalOutputId, RetrievalRunId, ScopeAsOfDate, ScopeShape, SourceBlockId, SourceBlockRecord,
    SourceCorpusId, SourceDocumentId, SourceDocumentRecord, ValidatorContractVersion,
    VALIDATOR_CONTRACT_VERSION,
};

/// Inclusive lower bound of the proof-local edition validity window.
///
/// The cleaned projection carries no legal temporal semantics, so the bounded
/// proof-local edition is declared valid from this floor with an open upper
/// bound. Any declared scope `as_of_date` at or above the floor is covered,
/// which is exactly the D719 "validity covering the declared scope" contract.
const EDITION_VALID_FROM: &str = "0001-01-01";

/// Fail-closed error raised while deriving the proof-local resolution graph.
///
/// It carries a bounded, closed `kind` plus the offending identifier token, so
/// it can never smuggle raw decoded text or provider payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectionGraphError {
    kind: &'static str,
    token: String,
}

impl ProjectionGraphError {
    fn new(kind: &'static str, token: impl Into<String>) -> Self {
        Self {
            kind,
            token: token.into(),
        }
    }

    /// The closed failure kind (`invalid identifier`, `duplicate view`, ...).
    pub fn kind(&self) -> &'static str {
        self.kind
    }

    /// The bounded offending identifier token.
    pub fn token(&self) -> &str {
        &self.token
    }
}

impl fmt::Display for ProjectionGraphError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "projection graph error {}: {}", self.kind, self.token)
    }
}

impl Error for ProjectionGraphError {}

/// The proof-local resolution binding for one projected segment node.
///
/// Every field is derived from the cleaned projection; none is a literal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SegmentBinding {
    /// The citation key that resolves to this segment's evidence span.
    pub citation_key: CitationKey,
    /// The single evidence span minted for this segment node.
    pub evidence_span_id: EvidenceSpanId,
    /// The source block of the segment's owning view.
    pub source_block_id: SourceBlockId,
    /// The projection's single source document.
    pub source_document_id: SourceDocumentId,
    /// The projection's single proof-local legal unit anchor.
    pub legal_unit_id: LegalUnitId,
    /// The projection's single proof-local edition anchor.
    pub act_edition_id: ActEditionId,
}

/// Proof-local resolution graph derived from a [`CleanedProjection`].
///
/// The adapter is read-only over the projection: `new` borrows it and copies
/// bounded identifiers into maps. It never mutates the projection and never
/// performs I/O.
#[derive(Debug, Clone)]
pub struct ProjectionGraphResolver {
    scope_id: OutputScopeId,
    source_document_id: SourceDocumentId,
    source_corpus_id: SourceCorpusId,
    legal_unit_id: LegalUnitId,
    legal_act_id: LegalActId,
    act_edition_id: ActEditionId,
    valid_from: String,
    valid_to: Option<String>,
    bindings: BTreeMap<String, SegmentBinding>,
    evidence_spans: HashMap<EvidenceSpanId, EvidenceSpanRecord>,
    source_blocks: HashMap<SourceBlockId, SourceBlockRecord>,
    citation_bindings: HashMap<(OutputScopeId, CitationKey), EvidenceSpanId>,
    evidence_order: Vec<EvidenceSpanId>,
    segment_ids_by_evidence: HashMap<EvidenceSpanId, String>,
}

impl ProjectionGraphResolver {
    /// Derive the proof-local resolution graph from a cleaned projection.
    ///
    /// Fails closed on an identifier that cannot be represented as a bounded
    /// token, on a duplicated view or segment node, or on a segment whose
    /// owning view is absent from the projection.
    pub fn new(projection: &CleanedProjection) -> Result<Self, ProjectionGraphError> {
        let sha256 = projection.source.sha256.as_str();

        let source_document_id = parse_id::<SourceDocumentId>(&format!("SD-{sha256}"))?;
        let source_corpus_id = parse_id::<SourceCorpusId>(&format!("CORPUS-{sha256}"))?;
        let legal_act_id = parse_id::<LegalActId>(&format!("LA-{sha256}"))?;
        let legal_unit_id = parse_id::<LegalUnitId>(&format!("LU-{sha256}"))?;
        let act_edition_id = parse_id::<ActEditionId>(&format!("ED-{sha256}"))?;
        let scope_id = parse_id::<OutputScopeId>(&format!("SCOPE-{sha256}"))?;

        // One source block per view node.
        let mut source_blocks: HashMap<SourceBlockId, SourceBlockRecord> = HashMap::new();
        let mut view_blocks: HashMap<String, SourceBlockId> = HashMap::new();
        for view in &projection.projection.views {
            let view_id = view.id.as_str();
            if view_blocks.contains_key(view_id) {
                return Err(ProjectionGraphError::new("duplicate view", view_id));
            }
            let block_id = parse_id::<SourceBlockId>(&format!("SB-{view_id}"))?;
            if source_blocks
                .insert(
                    block_id.clone(),
                    SourceBlockRecord {
                        source_document_id: source_document_id.clone(),
                    },
                )
                .is_some()
            {
                return Err(ProjectionGraphError::new("duplicate source block", view_id));
            }
            view_blocks.insert(view_id.to_owned(), block_id);
        }

        // One evidence span per segment node, active, bound to its view's block.
        let mut bindings: BTreeMap<String, SegmentBinding> = BTreeMap::new();
        let mut evidence_spans: HashMap<EvidenceSpanId, EvidenceSpanRecord> = HashMap::new();
        let mut citation_bindings: HashMap<(OutputScopeId, CitationKey), EvidenceSpanId> =
            HashMap::new();
        let mut evidence_order: Vec<EvidenceSpanId> = Vec::new();
        let mut segment_ids_by_evidence: HashMap<EvidenceSpanId, String> = HashMap::new();

        for segment in &projection.projection.segments {
            let segment_id = segment.id.as_str();
            let view_id = segment.view.as_str();
            let source_block_id = view_blocks
                .get(view_id)
                .cloned()
                .ok_or_else(|| ProjectionGraphError::new("missing owning view", segment_id))?;

            let evidence_span_id = parse_id::<EvidenceSpanId>(&format!("EV-{segment_id}"))?;
            let citation_key = parse_id::<CitationKey>(&format!("CIT-{segment_id}"))?;

            let record = EvidenceSpanRecord {
                source_block_id: source_block_id.clone(),
                source_document_id: source_document_id.clone(),
                legal_unit_id: legal_unit_id.clone(),
                act_edition_id: act_edition_id.clone(),
                status: EvidenceSpanStatus::Active,
            };
            if evidence_spans
                .insert(evidence_span_id.clone(), record)
                .is_some()
            {
                return Err(ProjectionGraphError::new(
                    "duplicate evidence span",
                    segment_id,
                ));
            }
            if citation_bindings
                .insert(
                    (scope_id.clone(), citation_key.clone()),
                    evidence_span_id.clone(),
                )
                .is_some()
            {
                return Err(ProjectionGraphError::new(
                    "duplicate citation key",
                    segment_id,
                ));
            }
            evidence_order.push(evidence_span_id.clone());
            segment_ids_by_evidence.insert(evidence_span_id.clone(), segment_id.to_owned());

            let binding = SegmentBinding {
                citation_key,
                evidence_span_id,
                source_block_id,
                source_document_id: source_document_id.clone(),
                legal_unit_id: legal_unit_id.clone(),
                act_edition_id: act_edition_id.clone(),
            };
            if bindings.insert(segment_id.to_owned(), binding).is_some() {
                return Err(ProjectionGraphError::new("duplicate segment", segment_id));
            }
        }

        Ok(Self {
            scope_id,
            source_document_id,
            source_corpus_id,
            legal_unit_id,
            legal_act_id,
            act_edition_id,
            valid_from: EDITION_VALID_FROM.to_owned(),
            valid_to: None,
            bindings,
            evidence_spans,
            source_blocks,
            citation_bindings,
            evidence_order,
            segment_ids_by_evidence,
        })
    }

    /// The single proof-local scope identifier derived from the projection.
    ///
    /// Citation bindings resolve only under this scope; a lookup under any
    /// other scope returns [`CitationKeyResolution::Unresolved`] (fail-closed).
    pub fn scope_id(&self) -> &OutputScopeId {
        &self.scope_id
    }

    /// The projection's single proof-local source document identifier.
    pub fn source_document_id(&self) -> &SourceDocumentId {
        &self.source_document_id
    }

    /// The projection's single proof-local source corpus identifier.
    pub fn source_corpus_id(&self) -> &SourceCorpusId {
        &self.source_corpus_id
    }

    /// The projection's single proof-local legal unit identifier.
    pub fn legal_unit_id(&self) -> &LegalUnitId {
        &self.legal_unit_id
    }

    /// The projection's single proof-local edition identifier.
    pub fn act_edition_id(&self) -> &ActEditionId {
        &self.act_edition_id
    }

    /// Segment node identifiers in deterministic projection order.
    pub fn segment_ids(&self) -> impl Iterator<Item = &str> {
        self.bindings.keys().map(String::as_str)
    }

    /// Evidence span identifiers in deterministic projection order.
    pub fn evidence_span_ids(&self) -> impl Iterator<Item = &EvidenceSpanId> {
        self.evidence_order.iter()
    }

    /// The full resolution binding for a segment node.
    pub fn binding_for_segment(&self, segment_id: &str) -> Option<&SegmentBinding> {
        self.bindings.get(segment_id)
    }

    /// The citation key minted for a segment node.
    pub fn citation_key_for_segment(&self, segment_id: &str) -> Option<&CitationKey> {
        self.bindings
            .get(segment_id)
            .map(|binding| &binding.citation_key)
    }

    /// The evidence span minted for a segment node.
    pub fn evidence_span_for_segment(&self, segment_id: &str) -> Option<&EvidenceSpanId> {
        self.bindings
            .get(segment_id)
            .map(|binding| &binding.evidence_span_id)
    }

    /// The segment node a proof-local evidence span was minted from.
    pub fn segment_id_for_evidence_span(&self, evidence_span_id: &EvidenceSpanId) -> Option<&str> {
        self.segment_ids_by_evidence
            .get(evidence_span_id)
            .map(String::as_str)
    }

    /// The source block of the segment's owning view.
    pub fn source_block_for_segment(&self, segment_id: &str) -> Option<&SourceBlockId> {
        self.bindings
            .get(segment_id)
            .map(|binding| &binding.source_block_id)
    }

    /// True when `as_of` falls inside the proof-local edition validity window.
    pub fn edition_covers(&self, as_of_date: &ScopeAsOfDate) -> bool {
        let as_of = as_of_date.as_str();
        as_of >= self.valid_from.as_str()
            && self
                .valid_to
                .as_deref()
                .is_none_or(|valid_to| as_of <= valid_to)
    }
}

impl OutputIdResolutionPort for ProjectionGraphResolver {
    fn resolve_citation_key(
        &self,
        scope_id: &OutputScopeId,
        citation_key: &CitationKey,
    ) -> CitationKeyResolution {
        match self
            .citation_bindings
            .get(&(scope_id.clone(), citation_key.clone()))
        {
            Some(evidence_span_id) => CitationKeyResolution::Unique(evidence_span_id.clone()),
            None => CitationKeyResolution::Unresolved,
        }
    }

    fn resolve_evidence_span(
        &self,
        evidence_span_id: &EvidenceSpanId,
    ) -> Option<EvidenceSpanRecord> {
        self.evidence_spans.get(evidence_span_id).cloned()
    }

    fn resolve_source_block(&self, source_block_id: &SourceBlockId) -> Option<SourceBlockRecord> {
        self.source_blocks.get(source_block_id).cloned()
    }

    fn resolve_source_document(
        &self,
        source_document_id: &SourceDocumentId,
    ) -> Option<SourceDocumentRecord> {
        (source_document_id == &self.source_document_id).then(|| SourceDocumentRecord {
            source_corpus_id: self.source_corpus_id.clone(),
        })
    }

    fn resolve_legal_unit(&self, legal_unit_id: &LegalUnitId) -> Option<LegalUnitRecord> {
        (legal_unit_id == &self.legal_unit_id).then(|| LegalUnitRecord {
            act_edition_id: self.act_edition_id.clone(),
            legal_act_id: self.legal_act_id.clone(),
        })
    }

    fn resolve_act_edition(&self, act_edition_id: &ActEditionId) -> Option<ActEditionRecord> {
        (act_edition_id == &self.act_edition_id).then(|| ActEditionRecord {
            legal_act_id: self.legal_act_id.clone(),
            valid_from: self.valid_from.clone(),
            valid_to: self.valid_to.clone(),
        })
    }

    fn resolve_valid_edition(
        &self,
        legal_unit_id: &LegalUnitId,
        as_of_date: &ScopeAsOfDate,
    ) -> Option<ActEditionId> {
        (legal_unit_id == &self.legal_unit_id && self.edition_covers(as_of_date))
            .then(|| self.act_edition_id.clone())
    }

    fn is_superseded(
        &self,
        evidence_span_id: &EvidenceSpanId,
        _as_of_date: &ScopeAsOfDate,
    ) -> bool {
        self.evidence_spans
            .get(evidence_span_id)
            .map(|record| record.status == EvidenceSpanStatus::Superseded)
            .unwrap_or(false)
    }
}

/// Fail-closed parse of a minted identifier, attaching the offending token to
/// the error instead of leaking the parser's internal reason.
fn parse_id<T>(token: &str) -> Result<T, ProjectionGraphError>
where
    T: IdToken,
{
    T::parse_token(token).map_err(|_| ProjectionGraphError::new("invalid identifier", token))
}

/// Minimal seam over the envelope identifier newtypes so the derivation can
/// parse a minted token without naming each concrete type at the call site.
trait IdToken: Sized {
    fn parse_token(token: &str) -> Result<Self, crate::retrieval_output::OutputIdError>;
}

macro_rules! id_token_impl {
    ($ty:ty) => {
        impl IdToken for $ty {
            fn parse_token(token: &str) -> Result<Self, crate::retrieval_output::OutputIdError> {
                <$ty>::parse(token)
            }
        }
    };
}

id_token_impl!(SourceDocumentId);
id_token_impl!(SourceCorpusId);
id_token_impl!(LegalActId);
id_token_impl!(LegalUnitId);
id_token_impl!(ActEditionId);
id_token_impl!(OutputScopeId);
id_token_impl!(SourceBlockId);
id_token_impl!(EvidenceSpanId);
id_token_impl!(CitationKey);

// --- offline citation-safe retrieval proof --------------------------------

/// Closed query kind for the offline citation-safe retrieval proof.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RetrievalQueryKind {
    /// Select by an explicit projected node address (a segment id).
    ExactNodeAddress,
    /// Deterministic walk by a closed view/segment/reference kind criterion.
    MarkerKind,
    /// No candidate exists inside the declared proof scope.
    ScopedNoCandidate,
    /// More than one candidate satisfies the closed criteria.
    AmbiguousLookup,
    /// The candidate carries a forbidden payload class.
    InvalidCandidate,
}

impl RetrievalQueryKind {
    /// Every valid query kind, in contract order.
    pub const ALL: [Self; 5] = [
        Self::ExactNodeAddress,
        Self::MarkerKind,
        Self::ScopedNoCandidate,
        Self::AmbiguousLookup,
        Self::InvalidCandidate,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ExactNodeAddress => "exact_node_address",
            Self::MarkerKind => "marker_kind",
            Self::ScopedNoCandidate => "scoped_no_candidate",
            Self::AmbiguousLookup => "ambiguous_lookup",
            Self::InvalidCandidate => "invalid_candidate",
        }
    }
}

/// Closed selection reason for an offline proof case.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OfflineSelectionReason {
    /// The explicit node address resolved to one candidate.
    ExactNodeAddressMatch,
    /// The deterministic kind walk resolved to one candidate.
    MarkerKindMatch,
    /// No candidate exists and a safe scoped no-answer is emitted.
    ScopedNoCandidate,
    /// More than one candidate; reject without arbitrary choice.
    AmbiguousCandidateSet,
    /// The candidate cannot be bound to a complete evidence path; reject.
    UnresolvedCandidateEvidence,
    /// The candidate carries a forbidden payload class; reject at proof level.
    UnsafePayloadRejected,
}

impl OfflineSelectionReason {
    /// Every selection reason, in contract order.
    pub const ALL: [Self; 6] = [
        Self::ExactNodeAddressMatch,
        Self::MarkerKindMatch,
        Self::ScopedNoCandidate,
        Self::AmbiguousCandidateSet,
        Self::UnresolvedCandidateEvidence,
        Self::UnsafePayloadRejected,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ExactNodeAddressMatch => "exact_node_address_match",
            Self::MarkerKindMatch => "marker_kind_match",
            Self::ScopedNoCandidate => "scoped_no_candidate",
            Self::AmbiguousCandidateSet => "ambiguous_candidate_set",
            Self::UnresolvedCandidateEvidence => "unresolved_candidate_evidence",
            Self::UnsafePayloadRejected => "unsafe_payload_rejected",
        }
    }

    /// The bounded proof-level diagnostic code, or `None` for a match reason.
    pub fn proof_code(self) -> Option<&'static str> {
        match self {
            Self::ScopedNoCandidate
            | Self::AmbiguousCandidateSet
            | Self::UnresolvedCandidateEvidence
            | Self::UnsafePayloadRejected => Some(self.as_str()),
            Self::ExactNodeAddressMatch | Self::MarkerKindMatch => None,
        }
    }
}

/// Closed expected result for an offline proof case.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OfflineExpectedResult {
    /// A citation-backed candidate is accepted.
    Selected,
    /// A safe scoped no-answer is accepted.
    ScopedNoAnswer,
    /// The candidate is rejected (proof-level or by the validator).
    Rejected,
}

impl OfflineExpectedResult {
    /// Every expected result, in contract order.
    pub const ALL: [Self; 3] = [Self::Selected, Self::ScopedNoAnswer, Self::Rejected];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Selected => "selected",
            Self::ScopedNoAnswer => "scoped_no_answer",
            Self::Rejected => "rejected",
        }
    }
}

/// One deterministic offline retrieval proof case.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfflineRetrievalCase {
    /// Stable case identifier used in the summary and the envelope.
    pub case_id: String,
    /// Query identifier carried by the envelope scope.
    pub query_id: String,
    /// Declared scope identifier; citations resolve only under the projection
    /// scope, so a mismatched scope fails closed.
    pub scope_id: String,
    /// Declared scope as-of date.
    pub as_of_date: String,
    /// Closed query kind.
    pub query_kind: RetrievalQueryKind,
    /// Bounded selector: a segment id for `exact_node_address`, or a marker
    /// token (`view:<kind>`, `segment:<kind>`, `semantic:<value>`,
    /// `reference:<type>`) for `marker_kind`.
    pub selector: String,
    /// Expected result class before the run.
    pub expected_result: OfflineExpectedResult,
}

/// One deterministic offline proof outcome.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfflineCaseOutcome {
    /// The case this outcome belongs to.
    pub case_id: String,
    /// The query identifier for this case.
    pub query_id: String,
    /// The closed proof selection reason.
    pub selection_reason: OfflineSelectionReason,
    /// The validator verdict, when the envelope reached the validator.
    pub validator_verdict: Option<OutputVerdict>,
    /// The validator primary code, when available.
    pub primary_code: Option<OutputDiagnosticCode>,
    /// The expected result declared by the case.
    pub expected_result: OfflineExpectedResult,
    /// True when the observed result class equals the expected result class.
    pub matched: bool,
}

/// Bounded summary of an offline citation-safe retrieval proof run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfflineRetrievalProofSummary {
    /// Number of cases run.
    pub total_cases: usize,
    /// Cases whose observed result is a selected candidate.
    pub selected_count: usize,
    /// Cases whose observed result is a scoped no-answer.
    pub scoped_no_answer_count: usize,
    /// Cases whose observed result is a rejection.
    pub rejected_count: usize,
    /// Cases the validator accepted with a citation-backed candidate.
    pub validator_accepted_count: usize,
    /// Cases the validator rejected (proof-level rejections are not counted).
    pub validator_rejected_count: usize,
    /// Cases whose observed result disagrees with the expected result.
    pub mismatch_count: usize,
    /// Sorted, de-duplicated bounded proof and validator diagnostic codes.
    pub diagnostic_code_inventory: Vec<&'static str>,
}

/// Closed marker criterion evaluated over projected segment nodes.
///
/// The criterion is a `view:` / `segment:` / `semantic:` / `reference:` token.
/// The search space is always the segment nodes, because only a segment mints
/// an evidence span; view and reference kinds are criteria over the segment's
/// owning-view ancestry and its owning view's references.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum MarkerKind {
    View(ReaderViewKind),
    Segment(ReaderSegmentKind),
    Semantic(ReaderSemantic),
    Reference(ReaderReferenceType),
}

/// Parse a bounded marker selector; an unknown token is `None` (fail-closed).
fn parse_marker(selector: &str) -> Option<MarkerKind> {
    let (prefix, value) = selector.split_once(':')?;
    match prefix {
        "view" => ReaderViewKind::from_wire(value).ok().map(MarkerKind::View),
        "segment" => ReaderSegmentKind::from_wire(value)
            .ok()
            .map(MarkerKind::Segment),
        "semantic" => ReaderSemantic::from_wire(value)
            .ok()
            .map(MarkerKind::Semantic),
        "reference" => ReaderReferenceType::from_wire(value)
            .ok()
            .map(MarkerKind::Reference),
        _ => None,
    }
}

/// True when any ancestor-or-self view of `view` has the requested kind.
fn view_ancestry_has_kind(
    projection: &ReaderProjection,
    view: &ProjectedView,
    kind: ReaderViewKind,
) -> bool {
    if view.kind == kind {
        return true;
    }
    let mut current = view.parent_view.clone();
    let mut seen = std::collections::HashSet::new();
    while let Some(parent_id) = current {
        if !seen.insert(parent_id.clone()) {
            break;
        }
        match projection.views.iter().find(|view| view.id == parent_id) {
            Some(parent) => {
                if parent.kind == kind {
                    return true;
                }
                current = parent.parent_view.clone();
            }
            None => break,
        }
    }
    false
}

/// True when `segment` satisfies the closed marker criterion.
fn marker_matches(
    projection: &ReaderProjection,
    view: &ProjectedView,
    segment: &ProjectedSegment,
    marker: &MarkerKind,
) -> bool {
    match marker {
        MarkerKind::Segment(kind) => segment.segment_kind == *kind,
        MarkerKind::Semantic(semantic) => segment.semantic == *semantic,
        MarkerKind::View(kind) => view_ancestry_has_kind(projection, view, *kind),
        MarkerKind::Reference(reference_type) => projection.references.iter().any(|reference| {
            reference.view == view.id && reference.reference_type == *reference_type
        }),
    }
}

/// Collect the segment ids matching `marker`, in deterministic projection order
/// (views in record order, each view's segments in ordinal order), mirroring
/// `NavIndex::nodes_in_source_order` for the segment nodes.
fn matching_segments(projection: &CleanedProjection, marker: &MarkerKind) -> Vec<String> {
    let proj = &projection.projection;
    let mut matches = Vec::new();
    for view in &proj.views {
        for segment_id in &view.segment_refs {
            if let Some(segment) = proj
                .segments
                .iter()
                .find(|segment| &segment.id == segment_id)
            {
                if marker_matches(proj, view, segment, marker) {
                    matches.push(segment_id.as_str().to_owned());
                }
            }
        }
    }
    matches
}

/// The deterministic anchor binding used to complete a non-evidence envelope
/// for an unresolved candidate: the first projected segment's binding.
fn anchor_binding(resolver: &ProjectionGraphResolver) -> Option<&SegmentBinding> {
    let span = resolver.evidence_span_ids().next()?;
    let segment_id = resolver.segment_id_for_evidence_span(span)?;
    resolver.binding_for_segment(segment_id)
}

/// Build the envelope scope from all six required fields.
fn build_scope(
    case: &OfflineRetrievalCase,
    resolver: &ProjectionGraphResolver,
) -> Option<OutputScope> {
    Some(OutputScope::new(
        OutputScopeId::parse(&case.scope_id).ok()?,
        QueryId::parse(&case.query_id).ok()?,
        RetrievalRunId::parse(&format!("RUN-{}", case.case_id)).ok()?,
        ScopeAsOfDate::parse(&case.as_of_date).ok()?,
        resolver.source_corpus_id().clone(),
        ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION).ok()?,
    ))
}

/// The per-case retrieval output identifier, derived from the case id.
fn retrieval_output_id(case: &OfflineRetrievalCase) -> Option<RetrievalOutputId> {
    RetrievalOutputId::parse(&format!("RET-{}", case.case_id)).ok()
}

/// A citation binding for a fully resolved segment.
fn binding_citation(
    retrieval_output_id: &RetrievalOutputId,
    binding: &SegmentBinding,
) -> CitationBinding {
    CitationBinding {
        retrieval_output_id: FieldShape::Value(retrieval_output_id.clone()),
        citation_key: FieldShape::Value(binding.citation_key.clone()),
        evidence_span_id: FieldShape::Value(binding.evidence_span_id.clone()),
        source_block_id: FieldShape::Value(binding.source_block_id.clone()),
        source_document_id: FieldShape::Value(binding.source_document_id.clone()),
        legal_unit_id: FieldShape::Value(binding.legal_unit_id.clone()),
        act_edition_id: FieldShape::Value(binding.act_edition_id.clone()),
        answer_claim_id: FieldShape::Missing,
    }
}

/// A citation binding whose evidence span is not resolvable by the graph.
fn unresolved_citation(
    retrieval_output_id: &RetrievalOutputId,
    anchor: &SegmentBinding,
    selector: &str,
) -> Option<CitationBinding> {
    let evidence_span_id = EvidenceSpanId::parse(&format!("EV-{selector}")).ok()?;
    Some(CitationBinding {
        retrieval_output_id: FieldShape::Value(retrieval_output_id.clone()),
        citation_key: FieldShape::Value(anchor.citation_key.clone()),
        evidence_span_id: FieldShape::Value(evidence_span_id),
        source_block_id: FieldShape::Value(anchor.source_block_id.clone()),
        source_document_id: FieldShape::Value(anchor.source_document_id.clone()),
        legal_unit_id: FieldShape::Value(anchor.legal_unit_id.clone()),
        act_edition_id: FieldShape::Value(anchor.act_edition_id.clone()),
        answer_claim_id: FieldShape::Missing,
    })
}

/// A citation-backed candidate envelope.
fn candidate_envelope(
    scope: OutputScope,
    retrieval_output_id: RetrievalOutputId,
    citation: CitationBinding,
) -> RetrievalOutputEnvelope {
    RetrievalOutputEnvelope {
        retrieval_output_id: FieldShape::Value(retrieval_output_id),
        output_kind: FieldShape::Value(OutputKind::RetrievalCandidate),
        scope: ScopeShape::Complete(scope),
        citations: FieldShape::Value(vec![citation]),
        answer_claims: FieldShape::Value(Vec::new()),
        extra_field_names: Vec::new(),
    }
}

/// A safe scoped no-answer envelope.
fn scoped_no_answer_envelope(
    scope: OutputScope,
    retrieval_output_id: RetrievalOutputId,
) -> RetrievalOutputEnvelope {
    RetrievalOutputEnvelope {
        retrieval_output_id: FieldShape::Value(retrieval_output_id),
        output_kind: FieldShape::Value(OutputKind::ScopedNoAnswer),
        scope: ScopeShape::Complete(scope),
        citations: FieldShape::Value(Vec::new()),
        answer_claims: FieldShape::Value(Vec::new()),
        extra_field_names: Vec::new(),
    }
}

/// A citation-backed candidate envelope for a resolved segment.
fn candidate_envelope_for(
    case: &OfflineRetrievalCase,
    resolver: &ProjectionGraphResolver,
    binding: &SegmentBinding,
) -> Option<RetrievalOutputEnvelope> {
    let scope = build_scope(case, resolver)?;
    let output_id = retrieval_output_id(case)?;
    let citation = binding_citation(&output_id, binding);
    Some(candidate_envelope(scope, output_id, citation))
}

/// Internal evaluation of a single case before it is shaped into an outcome.
struct CaseEvaluation {
    reason: OfflineSelectionReason,
    validator_verdict: Option<OutputVerdict>,
    primary_code: Option<OutputDiagnosticCode>,
    actual: OfflineExpectedResult,
}

/// Run an envelope through the validator and derive its result class.
fn validate_handoff(
    reason: OfflineSelectionReason,
    envelope: &RetrievalOutputEnvelope,
    resolver: &ProjectionGraphResolver,
) -> CaseEvaluation {
    let outcome = validate_retrieval_output(envelope, resolver);
    let verdict = outcome.verdict();
    let actual = match verdict {
        OutputVerdict::Accepted => OfflineExpectedResult::Selected,
        OutputVerdict::AcceptedScopedNoAnswer => OfflineExpectedResult::ScopedNoAnswer,
        OutputVerdict::Rejected => OfflineExpectedResult::Rejected,
    };
    CaseEvaluation {
        reason,
        validator_verdict: Some(verdict),
        primary_code: outcome.primary_code(),
        actual,
    }
}

/// A proof-level rejection that never reaches the validator.
fn proof_rejected(reason: OfflineSelectionReason) -> CaseEvaluation {
    CaseEvaluation {
        reason,
        validator_verdict: None,
        primary_code: None,
        actual: OfflineExpectedResult::Rejected,
    }
}

/// A safe scoped no-answer outcome.
fn scoped_outcome(
    case: &OfflineRetrievalCase,
    resolver: &ProjectionGraphResolver,
) -> CaseEvaluation {
    match (build_scope(case, resolver), retrieval_output_id(case)) {
        (Some(scope), Some(output_id)) => {
            let envelope = scoped_no_answer_envelope(scope, output_id);
            validate_handoff(
                OfflineSelectionReason::ScopedNoCandidate,
                &envelope,
                resolver,
            )
        }
        _ => proof_rejected(OfflineSelectionReason::UnsafePayloadRejected),
    }
}

/// An unresolved-candidate outcome: a well-formed envelope whose evidence span
/// the graph does not resolve, so the validator fails closed.
fn unresolved_outcome(
    case: &OfflineRetrievalCase,
    resolver: &ProjectionGraphResolver,
) -> CaseEvaluation {
    let envelope = build_scope(case, resolver).and_then(|scope| {
        let output_id = retrieval_output_id(case)?;
        let anchor = anchor_binding(resolver)?;
        let citation = unresolved_citation(&output_id, anchor, &case.selector)?;
        Some(candidate_envelope(scope, output_id, citation))
    });
    match envelope {
        Some(envelope) => validate_handoff(
            OfflineSelectionReason::UnresolvedCandidateEvidence,
            &envelope,
            resolver,
        ),
        None => proof_rejected(OfflineSelectionReason::UnresolvedCandidateEvidence),
    }
}

/// Evaluate one proof case against the projection and resolver.
fn evaluate_case(
    case: &OfflineRetrievalCase,
    projection: &CleanedProjection,
    resolver: &ProjectionGraphResolver,
) -> CaseEvaluation {
    match case.query_kind {
        RetrievalQueryKind::InvalidCandidate => {
            proof_rejected(OfflineSelectionReason::UnsafePayloadRejected)
        }
        RetrievalQueryKind::AmbiguousLookup => {
            proof_rejected(OfflineSelectionReason::AmbiguousCandidateSet)
        }
        RetrievalQueryKind::ScopedNoCandidate => scoped_outcome(case, resolver),
        RetrievalQueryKind::ExactNodeAddress => {
            match resolver.binding_for_segment(&case.selector) {
                Some(binding) => match candidate_envelope_for(case, resolver, binding) {
                    Some(envelope) => validate_handoff(
                        OfflineSelectionReason::ExactNodeAddressMatch,
                        &envelope,
                        resolver,
                    ),
                    None => proof_rejected(OfflineSelectionReason::UnsafePayloadRejected),
                },
                None => unresolved_outcome(case, resolver),
            }
        }
        RetrievalQueryKind::MarkerKind => match parse_marker(&case.selector) {
            Some(marker) => {
                let matches = matching_segments(projection, &marker);
                match matches.len() {
                    0 => scoped_outcome(case, resolver),
                    1 => match resolver.binding_for_segment(&matches[0]) {
                        Some(binding) => match candidate_envelope_for(case, resolver, binding) {
                            Some(envelope) => validate_handoff(
                                OfflineSelectionReason::MarkerKindMatch,
                                &envelope,
                                resolver,
                            ),
                            None => proof_rejected(OfflineSelectionReason::UnsafePayloadRejected),
                        },
                        None => unresolved_outcome(case, resolver),
                    },
                    _ => proof_rejected(OfflineSelectionReason::AmbiguousCandidateSet),
                }
            }
            // An unknown marker criterion cannot bind a candidate; fail closed.
            None => unresolved_outcome(case, resolver),
        },
    }
}

/// Run every case and return its outcome in input order.
pub fn run_offline_citation_retrieval_cases(
    cases: &[OfflineRetrievalCase],
    projection: &CleanedProjection,
    resolver: &ProjectionGraphResolver,
) -> Vec<OfflineCaseOutcome> {
    cases
        .iter()
        .map(|case| {
            let evaluation = evaluate_case(case, projection, resolver);
            OfflineCaseOutcome {
                case_id: case.case_id.clone(),
                query_id: case.query_id.clone(),
                selection_reason: evaluation.reason,
                validator_verdict: evaluation.validator_verdict,
                primary_code: evaluation.primary_code,
                expected_result: case.expected_result,
                matched: evaluation.actual == case.expected_result,
            }
        })
        .collect()
}

/// Run the deterministic offline citation-safe retrieval proof.
///
/// For every case the runner selects a candidate with the closed criteria,
/// builds a validator envelope, runs it through [`validate_retrieval_output`],
/// and compares the observed result class with the expected result. The demo
/// invariant is that an unresolvable citation always yields `rejected`: an
/// accepted answer without a resolvable citation is never emitted.
pub fn run_offline_citation_retrieval_proof(
    cases: &[OfflineRetrievalCase],
    projection: &CleanedProjection,
    resolver: &ProjectionGraphResolver,
) -> OfflineRetrievalProofSummary {
    let outcomes = run_offline_citation_retrieval_cases(cases, projection, resolver);
    let mut summary = OfflineRetrievalProofSummary {
        total_cases: outcomes.len(),
        selected_count: 0,
        scoped_no_answer_count: 0,
        rejected_count: 0,
        validator_accepted_count: 0,
        validator_rejected_count: 0,
        mismatch_count: 0,
        diagnostic_code_inventory: Vec::new(),
    };
    let mut codes: BTreeSet<&'static str> = BTreeSet::new();
    for outcome in &outcomes {
        match outcome.validator_verdict {
            Some(OutputVerdict::Accepted) => {
                summary.selected_count += 1;
                summary.validator_accepted_count += 1;
            }
            Some(OutputVerdict::AcceptedScopedNoAnswer) => {
                summary.scoped_no_answer_count += 1;
            }
            Some(OutputVerdict::Rejected) => {
                summary.rejected_count += 1;
                summary.validator_rejected_count += 1;
            }
            None => {
                summary.rejected_count += 1;
            }
        }
        if !outcome.matched {
            summary.mismatch_count += 1;
        }
        if let Some(code) = outcome.selection_reason.proof_code() {
            codes.insert(code);
        }
        if let Some(code) = outcome.primary_code {
            codes.insert(code.as_str());
        }
    }
    summary.diagnostic_code_inventory = codes.into_iter().collect();
    summary
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    use crate::retrieval_output::BoundedToken;

    use ln_decode::cleaned_nav::{build_nav_index, NavIndex, NodeAddress};
    use ln_decode::cleaned_wire::{
        export_cleaned_projection, read_cleaned_wire, WireCompletion, WireLimits,
    };
    use ln_decode::reader_gate::{gate_reader, ReaderSourceClass};
    use ln_decode::reader_projection::build_projection;
    use ln_decode::source_package::{capture, Limits};

    /// The pinned synthetic, non-legal reader fixture. A content drift fails the
    /// `pinned` assertion below instead of being silently re-pinned.
    const MIXED_XML: &str = include_str!("../../ln-decode/tests/fixtures/reader/mixed-wordml.xml");
    const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

    /// The frozen substrate, its cleaned-projection read-back and its nav index,
    /// all produced by the real enabled pipeline. No field is a literal.
    struct Pinned {
        projection: CleanedProjection,
        nav: NavIndex,
    }

    /// Drive
    /// `capture -> gate_reader -> build_projection -> export -> read_back ->
    /// build_nav_index` over the pinned fixture.
    fn pinned() -> Pinned {
        let package = capture(MIXED_XML.as_bytes(), &Limits::default())
            .expect("the fixture bytes must capture as a source package");
        assert_eq!(
            package.manifest().source.sha256,
            MIXED_SHA256,
            "fixture content drift; re-pin the sha256 oracle instead of silently accepting it"
        );
        let class = gate_reader(package.records())
            .expect("the fixture must gate as a supported reader source");
        assert_eq!(class, ReaderSourceClass::SupportedWordml);
        let reader_projection =
            build_projection(package.records()).expect("the fixture must project");
        let artifact = export_cleaned_projection(
            &package,
            &reader_projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("a gated, projected fixture must export a complete artifact");
        let projection = read_cleaned_wire(&artifact).expect("the artifact must read back");
        let nav = build_nav_index(&projection, &package).expect("the nav index must build");
        Pinned { projection, nav }
    }

    fn resolver() -> (Pinned, ProjectionGraphResolver) {
        let pinned = pinned();
        let resolver =
            ProjectionGraphResolver::new(&pinned.projection).expect("the graph must derive");
        (pinned, resolver)
    }

    fn nav_segment_ids(nav: &NavIndex) -> BTreeSet<String> {
        nav.nodes_in_source_order()
            .iter()
            .filter_map(|address| match address {
                NodeAddress::Segment(segment_id) => Some(segment_id.as_str().to_owned()),
                NodeAddress::View(_) | NodeAddress::Reference(_) => None,
            })
            .collect()
    }

    #[test]
    fn every_segment_node_has_exactly_one_evidence_span() {
        let (pinned, resolver) = resolver();
        let resolver_segments: BTreeSet<String> = resolver
            .evidence_span_ids()
            .filter_map(|id| resolver.segment_id_for_evidence_span(id).map(str::to_owned))
            .collect();
        assert_eq!(
            resolver_segments,
            nav_segment_ids(&pinned.nav),
            "the evidence-span set must equal the nav segment-address set"
        );
        assert_eq!(
            resolver.evidence_span_ids().count(),
            resolver.segment_ids().count(),
            "one evidence span per segment node"
        );
        assert!(
            !resolver_segments.is_empty(),
            "the pinned fixture must project at least one segment"
        );
        for span in resolver.evidence_span_ids() {
            let record = resolver
                .resolve_evidence_span(span)
                .expect("every minted span must resolve");
            assert_eq!(record.status, EvidenceSpanStatus::Active);
            assert_eq!(record.source_document_id, *resolver.source_document_id());
            assert_eq!(record.legal_unit_id, *resolver.legal_unit_id());
            assert_eq!(record.act_edition_id, *resolver.act_edition_id());
        }
    }

    #[test]
    fn citation_key_over_a_segment_resolves_to_exactly_one_span() {
        let (pinned, resolver) = resolver();
        for segment_id in resolver.segment_ids() {
            let citation_key = resolver
                .citation_key_for_segment(segment_id)
                .expect("every segment must mint a citation key")
                .clone();
            match resolver.resolve_citation_key(resolver.scope_id(), &citation_key) {
                CitationKeyResolution::Unique(span) => {
                    assert_eq!(
                        Some(&span),
                        resolver.evidence_span_for_segment(segment_id),
                        "the resolved span must be the segment's own span"
                    );
                    let record = resolver
                        .resolve_evidence_span(&span)
                        .expect("the resolved span must resolve");
                    assert_eq!(
                        Some(&record.source_block_id),
                        resolver.source_block_for_segment(segment_id),
                        "the span must point at its owning view's source block"
                    );
                    let block = resolver
                        .resolve_source_block(&record.source_block_id)
                        .expect("the reached block must resolve");
                    assert_eq!(block.source_document_id, record.source_document_id);
                }
                other => panic!("segment {segment_id} must resolve uniquely, got {other:?}"),
            }
        }
        assert!(
            resolver.segment_ids().count() > 0,
            "the pinned fixture must project at least one segment"
        );
        // Origin: the binding is projection-derived, so every binding's block is
        // a real view of the pinned projection.
        let view_blocks: BTreeSet<String> = pinned
            .projection
            .projection
            .views
            .iter()
            .map(|view| format!("SB-{}", view.id.as_str()))
            .collect();
        for segment_id in resolver.segment_ids() {
            let block = resolver
                .source_block_for_segment(segment_id)
                .expect("segment binding");
            assert!(
                view_blocks.contains(block.as_str()),
                "source block {} is not a projected view block",
                block.as_str()
            );
        }
    }

    #[test]
    fn unknown_identifiers_fail_closed() {
        let (_pinned, resolver) = resolver();
        let as_of = ScopeAsOfDate::parse("2024-01-01").expect("a valid scope selector");

        assert!(resolver
            .resolve_evidence_span(&EvidenceSpanId::parse("EV-UNKNOWN").unwrap())
            .is_none());
        assert!(resolver
            .resolve_source_block(&SourceBlockId::parse("SB-UNKNOWN").unwrap())
            .is_none());
        assert!(resolver
            .resolve_source_document(&SourceDocumentId::parse("SD-UNKNOWN").unwrap())
            .is_none());
        assert!(resolver
            .resolve_legal_unit(&LegalUnitId::parse("LU-UNKNOWN").unwrap())
            .is_none());
        assert!(resolver
            .resolve_act_edition(&ActEditionId::parse("ED-UNKNOWN").unwrap())
            .is_none());
        assert!(resolver
            .resolve_valid_edition(&LegalUnitId::parse("LU-UNKNOWN").unwrap(), &as_of)
            .is_none());
        assert_eq!(
            resolver.resolve_citation_key(
                resolver.scope_id(),
                &CitationKey::parse("CIT-UNKNOWN").unwrap()
            ),
            CitationKeyResolution::Unresolved
        );
        // A citation key that exists only under the projection scope is
        // unresolved under any other scope; no cross-scope repair.
        let known_key = resolver
            .citation_key_for_segment(
                resolver
                    .segment_ids()
                    .next()
                    .expect("the pinned fixture must project a segment"),
            )
            .expect("segment binding")
            .clone();
        assert_eq!(
            resolver
                .resolve_citation_key(&OutputScopeId::parse("SCOPE-OTHER").unwrap(), &known_key),
            CitationKeyResolution::Unresolved
        );
    }

    #[test]
    fn edition_resolves_only_inside_its_validity_window() {
        let (_pinned, resolver) = resolver();
        let covered = ScopeAsOfDate::parse("2024-06-15").expect("a valid scope selector");
        let below_floor = ScopeAsOfDate::parse("0000-12-31").expect("a valid scope selector");

        assert_eq!(
            resolver.resolve_valid_edition(resolver.legal_unit_id(), &covered),
            Some(resolver.act_edition_id().clone())
        );
        assert!(resolver.edition_covers(&covered));
        assert_eq!(
            resolver.resolve_valid_edition(resolver.legal_unit_id(), &below_floor),
            None
        );
        assert!(!resolver.edition_covers(&below_floor));

        let edition = resolver
            .resolve_act_edition(resolver.act_edition_id())
            .expect("the edition must resolve");
        assert_eq!(edition.valid_from, EDITION_VALID_FROM);
        assert!(edition.valid_to.is_none());
    }

    #[test]
    fn active_spans_are_never_superseded() {
        let (_pinned, resolver) = resolver();
        let as_of = ScopeAsOfDate::parse("2024-01-01").expect("a valid scope selector");
        for span in resolver.evidence_span_ids() {
            assert!(
                !resolver.is_superseded(span, &as_of),
                "an active span must not be reported superseded"
            );
        }
        assert!(!resolver.is_superseded(&EvidenceSpanId::parse("EV-UNKNOWN").unwrap(), &as_of));
    }

    #[test]
    fn adapter_does_not_mutate_the_projection() {
        let pinned = pinned();
        let before = pinned.projection.clone();
        let resolver =
            ProjectionGraphResolver::new(&pinned.projection).expect("the graph must derive");
        for span in resolver.evidence_span_ids() {
            let _ = resolver.resolve_evidence_span(span);
        }
        let _ = resolver.resolve_source_document(resolver.source_document_id());
        assert_eq!(
            pinned.projection, before,
            "the resolver must not mutate the borrowed projection"
        );
    }

    #[test]
    fn derivation_is_deterministic_across_runs() {
        let pinned = pinned();
        let first = ProjectionGraphResolver::new(&pinned.projection).expect("first derivation");
        let second = ProjectionGraphResolver::new(&pinned.projection).expect("second derivation");
        assert_eq!(first.scope_id(), second.scope_id());
        let first_spans: Vec<String> = first
            .evidence_span_ids()
            .map(|id| id.as_str().to_owned())
            .collect();
        let second_spans: Vec<String> = second
            .evidence_span_ids()
            .map(|id| id.as_str().to_owned())
            .collect();
        assert_eq!(first_spans, second_spans);
    }

    #[test]
    fn duplicate_view_nodes_fail_closed() {
        let pinned = pinned();
        let mut projection = pinned.projection.clone();
        assert!(
            projection.projection.views.len() >= 2,
            "the pinned fixture must project at least two views"
        );
        let duplicate = projection.projection.views[0].id.clone();
        projection.projection.views[1].id = duplicate;
        let error =
            ProjectionGraphResolver::new(&projection).expect_err("a duplicate view must fail");
        assert_eq!(error.kind(), "duplicate view");
    }

    #[test]
    fn segment_without_owning_view_fails_closed() {
        let pinned = pinned();
        let mut projection = pinned.projection.clone();
        assert!(
            !projection.projection.segments.is_empty(),
            "the pinned fixture must project at least one segment"
        );
        projection.projection.views.clear();
        let error = ProjectionGraphResolver::new(&projection)
            .expect_err("a segment without an owning view must fail");
        assert_eq!(error.kind(), "missing owning view");
    }

    #[test]
    fn unrepresentable_source_identity_fails_closed() {
        let pinned = pinned();
        let mut projection = pinned.projection.clone();
        projection.source.sha256 = "not a sha".to_owned();
        let error = ProjectionGraphResolver::new(&projection)
            .expect_err("an unrepresentable identifier must fail");
        assert_eq!(error.kind(), "invalid identifier");
    }

    /// A deterministic corpus exercising every closed query kind and selection
    /// reason on the pinned mixed-wordml projection.
    fn proof_cases(resolver: &ProjectionGraphResolver) -> Vec<OfflineRetrievalCase> {
        let scope_id = resolver.scope_id().as_str().to_owned();
        let exact_segment = resolver
            .evidence_span_ids()
            .next()
            .and_then(|span| resolver.segment_id_for_evidence_span(span))
            .expect("the pinned fixture must project a segment")
            .to_owned();
        let case =
            |case_id: &str,
             query_kind: RetrievalQueryKind,
             selector: &str,
             expected_result: OfflineExpectedResult| OfflineRetrievalCase {
                case_id: case_id.to_owned(),
                query_id: format!("Q-{case_id}"),
                scope_id: scope_id.clone(),
                as_of_date: "2024-06-15".to_owned(),
                query_kind,
                selector: selector.to_owned(),
                expected_result,
            };
        vec![
            case(
                "c01",
                RetrievalQueryKind::ExactNodeAddress,
                &exact_segment,
                OfflineExpectedResult::Selected,
            ),
            case(
                "c02",
                RetrievalQueryKind::MarkerKind,
                "view:note",
                OfflineExpectedResult::Selected,
            ),
            case(
                "c03",
                RetrievalQueryKind::ScopedNoCandidate,
                "",
                OfflineExpectedResult::ScopedNoAnswer,
            ),
            case(
                "c04",
                RetrievalQueryKind::MarkerKind,
                "reference:endnote_reference",
                OfflineExpectedResult::ScopedNoAnswer,
            ),
            case(
                "c05",
                RetrievalQueryKind::AmbiguousLookup,
                "",
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c06",
                RetrievalQueryKind::MarkerKind,
                "semantic:body",
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c07",
                RetrievalQueryKind::ExactNodeAddress,
                "v3",
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c08",
                RetrievalQueryKind::InvalidCandidate,
                "raw_legal_text",
                OfflineExpectedResult::Rejected,
            ),
        ]
    }

    #[test]
    fn proof_harness_covers_every_case_class() {
        let (pinned, resolver) = resolver();
        let cases = proof_cases(&resolver);
        let outcomes = run_offline_citation_retrieval_cases(&cases, &pinned.projection, &resolver);
        assert_eq!(outcomes.len(), cases.len());
        assert!(
            outcomes.iter().all(|outcome| outcome.matched),
            "every authored case must match its expected result"
        );

        let by_id = |id: &str| {
            outcomes
                .iter()
                .find(|outcome| outcome.case_id == id)
                .expect("case outcome")
        };

        let exact = by_id("c01");
        assert_eq!(
            exact.selection_reason,
            OfflineSelectionReason::ExactNodeAddressMatch
        );
        assert_eq!(exact.validator_verdict, Some(OutputVerdict::Accepted));
        assert_eq!(exact.primary_code, None);

        let marker = by_id("c02");
        assert_eq!(
            marker.selection_reason,
            OfflineSelectionReason::MarkerKindMatch
        );
        assert_eq!(marker.validator_verdict, Some(OutputVerdict::Accepted));

        let scoped = by_id("c03");
        assert_eq!(
            scoped.selection_reason,
            OfflineSelectionReason::ScopedNoCandidate
        );
        assert_eq!(
            scoped.validator_verdict,
            Some(OutputVerdict::AcceptedScopedNoAnswer)
        );
        assert_eq!(
            scoped.primary_code,
            Some(OutputDiagnosticCode::ScopedNoAnswer)
        );

        let marker_scoped = by_id("c04");
        assert_eq!(
            marker_scoped.selection_reason,
            OfflineSelectionReason::ScopedNoCandidate
        );
        assert_eq!(
            marker_scoped.validator_verdict,
            Some(OutputVerdict::AcceptedScopedNoAnswer)
        );

        let ambiguous = by_id("c05");
        assert_eq!(
            ambiguous.selection_reason,
            OfflineSelectionReason::AmbiguousCandidateSet
        );
        assert_eq!(ambiguous.validator_verdict, None);
        assert_eq!(ambiguous.primary_code, None);

        let marker_ambiguous = by_id("c06");
        assert_eq!(
            marker_ambiguous.selection_reason,
            OfflineSelectionReason::AmbiguousCandidateSet
        );
        assert_eq!(marker_ambiguous.validator_verdict, None);

        let unresolved = by_id("c07");
        assert_eq!(
            unresolved.selection_reason,
            OfflineSelectionReason::UnresolvedCandidateEvidence
        );
        assert_eq!(unresolved.validator_verdict, Some(OutputVerdict::Rejected));
        assert_eq!(
            unresolved.primary_code,
            Some(OutputDiagnosticCode::UnresolvedEvidenceSpan)
        );

        let unsafe_case = by_id("c08");
        assert_eq!(
            unsafe_case.selection_reason,
            OfflineSelectionReason::UnsafePayloadRejected
        );
        assert_eq!(unsafe_case.validator_verdict, None);
        assert_eq!(unsafe_case.primary_code, None);
    }

    #[test]
    fn proof_summary_is_bounded_and_mismatch_free() {
        let (pinned, resolver) = resolver();
        let cases = proof_cases(&resolver);
        let summary = run_offline_citation_retrieval_proof(&cases, &pinned.projection, &resolver);

        assert_eq!(summary.total_cases, 8);
        assert_eq!(summary.selected_count, 2);
        assert_eq!(summary.scoped_no_answer_count, 2);
        assert_eq!(summary.rejected_count, 4);
        assert_eq!(summary.validator_accepted_count, 2);
        assert_eq!(summary.validator_rejected_count, 1);
        assert_eq!(summary.mismatch_count, 0);

        let allowed: BTreeSet<&str> = OutputDiagnosticCode::ALL
            .iter()
            .map(|code| code.as_str())
            .chain([
                "scoped_no_candidate",
                "ambiguous_candidate_set",
                "unresolved_candidate_evidence",
                "unsafe_payload_rejected",
            ])
            .collect();
        assert!(!summary.diagnostic_code_inventory.is_empty());
        for code in &summary.diagnostic_code_inventory {
            assert!(allowed.contains(code), "unexpected diagnostic code {code}");
        }
        let mut sorted = summary.diagnostic_code_inventory.clone();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(
            summary.diagnostic_code_inventory, sorted,
            "the code inventory must be sorted and de-duplicated"
        );
    }

    #[test]
    fn proof_run_is_deterministic_and_does_not_mutate_the_projection() {
        let pinned = pinned();
        let resolver = ProjectionGraphResolver::new(&pinned.projection).expect("the graph");
        let before = pinned.projection.clone();
        let cases = proof_cases(&resolver);

        let first_outcomes =
            run_offline_citation_retrieval_cases(&cases, &pinned.projection, &resolver);
        let first_summary =
            run_offline_citation_retrieval_proof(&cases, &pinned.projection, &resolver);
        let second_outcomes =
            run_offline_citation_retrieval_cases(&cases, &pinned.projection, &resolver);
        let second_summary =
            run_offline_citation_retrieval_proof(&cases, &pinned.projection, &resolver);

        assert_eq!(first_outcomes, second_outcomes);
        assert_eq!(first_summary, second_summary);
        assert_eq!(
            pinned.projection, before,
            "the proof run must not mutate the borrowed projection"
        );
    }

    #[test]
    fn unresolvable_citation_never_yields_an_accepted_answer() {
        let (pinned, resolver) = resolver();
        let cases = proof_cases(&resolver);
        let outcomes = run_offline_citation_retrieval_cases(&cases, &pinned.projection, &resolver);
        for outcome in &outcomes {
            if matches!(
                outcome.selection_reason,
                OfflineSelectionReason::UnresolvedCandidateEvidence
                    | OfflineSelectionReason::AmbiguousCandidateSet
                    | OfflineSelectionReason::UnsafePayloadRejected
            ) {
                assert_ne!(outcome.validator_verdict, Some(OutputVerdict::Accepted));
                assert_ne!(
                    outcome.validator_verdict,
                    Some(OutputVerdict::AcceptedScopedNoAnswer)
                );
                assert_eq!(outcome.expected_result, OfflineExpectedResult::Rejected);
            }
        }
        let summary = run_offline_citation_retrieval_proof(&cases, &pinned.projection, &resolver);
        assert_eq!(summary.mismatch_count, 0);
    }

    #[test]
    fn diagnostics_stay_bounded_and_carry_no_fixture_text() {
        let (pinned, resolver) = resolver();
        let cases = proof_cases(&resolver);
        let summary = run_offline_citation_retrieval_proof(&cases, &pinned.projection, &resolver);
        let sentinels = [
            "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa",
            "Lambda", "Mu", "Nu",
        ];
        for entry in &summary.diagnostic_code_inventory {
            assert!(
                sentinels.iter().all(|sentinel| !entry.contains(sentinel)),
                "a diagnostic code leaked fixture text: {entry}"
            );
        }
        let outcomes = run_offline_citation_retrieval_cases(&cases, &pinned.projection, &resolver);
        for outcome in &outcomes {
            let reason = outcome.selection_reason.as_str();
            assert!(sentinels.iter().all(|sentinel| !reason.contains(sentinel)));
            if let Some(code) = outcome.primary_code {
                assert!(sentinels
                    .iter()
                    .all(|sentinel| !code.as_str().contains(sentinel)));
            }
        }
    }

    #[test]
    fn validator_still_rejects_forbidden_payload_and_unknown_namespace() {
        let (_pinned, resolver) = resolver();
        let scope = OutputScope::new(
            resolver.scope_id().clone(),
            QueryId::parse("Q-validator").expect("a valid query id"),
            RetrievalRunId::parse("RUN-validator").expect("a valid run id"),
            ScopeAsOfDate::parse("2024-06-15").expect("a valid as-of date"),
            resolver.source_corpus_id().clone(),
            ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION)
                .expect("the contract version token"),
        );

        let forbidden = RetrievalOutputEnvelope {
            retrieval_output_id: FieldShape::Value(
                RetrievalOutputId::parse("RET-validator").expect("a valid id"),
            ),
            output_kind: FieldShape::Value(OutputKind::RetrievalCandidate),
            scope: ScopeShape::Complete(scope.clone()),
            citations: FieldShape::Value(Vec::new()),
            answer_claims: FieldShape::Value(Vec::new()),
            extra_field_names: vec![BoundedToken::parse("raw_legal_text").expect("a bounded token")],
        };
        let outcome = validate_retrieval_output(&forbidden, &resolver);
        assert_eq!(outcome.verdict(), OutputVerdict::Rejected);
        assert_eq!(
            outcome.primary_code(),
            Some(OutputDiagnosticCode::ForbiddenPayloadField)
        );

        let unknown_namespace = RetrievalOutputEnvelope {
            retrieval_output_id: FieldShape::Value(
                RetrievalOutputId::parse("NOPE-validator").expect("a bounded id token"),
            ),
            output_kind: FieldShape::Value(OutputKind::RetrievalCandidate),
            scope: ScopeShape::Complete(scope),
            citations: FieldShape::Value(Vec::new()),
            answer_claims: FieldShape::Value(Vec::new()),
            extra_field_names: Vec::new(),
        };
        let outcome = validate_retrieval_output(&unknown_namespace, &resolver);
        assert_eq!(outcome.verdict(), OutputVerdict::Rejected);
        assert_eq!(
            outcome.primary_code(),
            Some(OutputDiagnosticCode::UnknownIdNamespace)
        );
    }
}
