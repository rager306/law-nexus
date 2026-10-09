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

use std::collections::{BTreeMap, HashMap};
use std::error::Error;
use std::fmt;

use ln_decode::cleaned_wire::CleanedProjection;

use crate::retrieval_output::{
    ActEditionId, ActEditionRecord, CitationKey, CitationKeyResolution, EvidenceSpanId,
    EvidenceSpanRecord, EvidenceSpanStatus, LegalActId, LegalUnitId, LegalUnitRecord,
    OutputIdResolutionPort, OutputScopeId, ScopeAsOfDate, SourceBlockId, SourceBlockRecord,
    SourceCorpusId, SourceDocumentId, SourceDocumentRecord,
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

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
}
