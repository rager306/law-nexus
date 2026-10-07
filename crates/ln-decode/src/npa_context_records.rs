//! M214-es3jvw S03 T02: reader-native document context records.
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8B
//! (D661/D662/D663): the existing document-context path
//! (`build_document_structure_index` → `build_document_analysis_overlay` →
//! `ContextWorklist`) is driven from an [`AnalysisBlockLayout`] through a
//! synthetic [`ParsedBlock`] per analysis block. No second coordinate system is
//! minted: every context anchor is a block-relative `TextSpan` localized to
//! exactly one pinned reader fragment through the same S01 seam the S02 records
//! use (`AnalysisBlockLayout::localize` + `SourceMapping`). A localization
//! failure is a closed refusal — never a drop, never a rebase.
//!
//! `document_context` and `npa_context_baseline` are not rewritten; the
//! synthetic `SourceLocation` is never serialized.
//!
//! Claim-derivation vocabulary note: the contract §8B.2 parenthetical names
//! `DerivationRelation` (`derived_from`/`supports`) for a claim's `derivation`,
//! but the underlying `document_context::ContextClaim::derivation` is a closed
//! [`DerivationSource`] (RC28-F08). The claim token table below preserves that
//! actual closed source vocabulary instead of collapsing four distinct
//! derivations into one invented relation (see the S03 decision record).
//!
//! S03 successor revision (§8C): the requisites sidecar is rebuilt
//! deterministically from the pinned parent inside this module
//! (`npa_link::recognize_letterhead` over the layout block texts) and the
//! request trigger policy is deliberate — `current_document_requisites` only
//! for a block carrying a this-ref surface, `open_series_head` only for a
//! proven continuation tail, `explicit_anchor_lookup` only for a block with a
//! captured explicit mention. No external sidecar and no new
//! `build_context_records` parameter are introduced, so the verifier's
//! re-derivation is byte-equal by construction.

use std::collections::BTreeMap;

use crate::analysis_source_mapping::SourceMapping;
use crate::current_requisites::{
    CurrentDocumentRequisites, RequisitesClaim, RequisitesExtractionStatus, RequisitesField,
    RequisitesSourceKind, SourceAnchor, ThisRefGrammarEvidence,
};
use crate::document_context::{
    build_document_analysis_overlay, build_document_structure_index, detect_this_ref_grammar,
    explicit_anchor_lookup, open_series_head, BlockId, ContextClaimStatus, ContextDiagnostic,
    ContextEnvironment, ContextRequest, ContextRequestKind, ContextStatus, ContextWorklist,
    ContextualEdgeKind, DerivationRelation, DocumentAnalysisOverlay, DocumentStructureIndex,
    FrameRef, StructureEdgeStatus, PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
};
use crate::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    TextSpan,
};
use crate::lawref::capture_lawrefs;
use crate::local_grammar::{extract_act_list_frames, extract_structural_frames, DerivationSource};
use crate::morphology::find_legal_markers;
use crate::npa_analysis_records::{
    resolve_span, AnalysisBlockLayout, AnalysisRefusal, AnalysisRefusalKind, SourceRef,
};
use crate::npa_anchor::LocalSpan;

/// Per-line schema of the S03 context family (§8B.1).
pub const SCHEMA_CONTEXT: &str = "law-nexus/npa-analysis-context/v1";
/// Wire `kind` token for one context result derived from a worklist request.
pub const KIND_RESULT: &str = "result";
/// Wire `kind` token for the single aggregate context run line.
pub const KIND_RUN: &str = "run";
/// Wire `view` token for token-derived request kinds (§6 rule 1).
pub const VIEW_COVERING: &str = "covering";

/// Synthetic source stream id for the adapter `SourceLocation`. The location
/// exists only to satisfy [`ParsedBlock`] construction and is never emitted.
const SYNTHETIC_STREAM: &str = "npa-context-records";
/// Producer rule token carried on adapter-built context requests.
const CONTEXT_RULE: &str = "npa_context_records::build_context_records";
/// The single aggregate context line reference.
const RUN_REFERENCE: &str = "ctx:run";

// ---------------------------------------------------------- token tables #

/// Closed wire token for a `ContextRequestKind` (§8B.2).
pub const fn request_kind_token(kind: ContextRequestKind) -> &'static str {
    match kind {
        ContextRequestKind::AncestorPath => "ancestor_path",
        ContextRequestKind::AdjacentBlocks => "adjacent_blocks",
        ContextRequestKind::OpenSeriesHead => "open_series_head",
        ContextRequestKind::ScopedAlias => "scoped_alias",
        ContextRequestKind::CurrentDocumentRequisites => "current_document_requisites",
        ContextRequestKind::ExplicitAnchorLookup => "explicit_anchor_lookup",
    }
}

/// Closed wire token for a `ContextStatus` (§8B.2).
pub const fn status_token(status: ContextStatus) -> &'static str {
    match status {
        ContextStatus::Resolved => "resolved",
        ContextStatus::Partial => "partial",
        ContextStatus::Conflicting => "conflicting",
        ContextStatus::Unavailable => "unavailable",
        ContextStatus::Cycle => "cycle",
        ContextStatus::Limit => "limit",
    }
}

/// Closed wire token for a `ContextClaimStatus` (§8B.2).
pub const fn claim_status_token(status: ContextClaimStatus) -> &'static str {
    match status {
        ContextClaimStatus::Explicit => "explicit",
        ContextClaimStatus::Inherited => "inherited",
        ContextClaimStatus::Conflicting => "conflicting",
        ContextClaimStatus::Unresolved => "unresolved",
    }
}

/// Closed wire token for the claim derivation source vocabulary.
///
/// This is the actual closed [`DerivationSource`] carried by
/// `document_context::ContextClaim`; it is deliberately not collapsed onto
/// `DerivationRelation` (see the module note).
pub const fn claim_derivation_token(source: DerivationSource) -> &'static str {
    match source {
        DerivationSource::ExplicitMember => "explicit_member",
        DerivationSource::SameSeriesHead => "same_series_head",
        DerivationSource::PriorFrame => "prior_frame",
        DerivationSource::AuthorizedCurrentDocumentRequisites => {
            "authorized_current_document_requisites"
        }
    }
}

/// Closed wire token for a `DerivationRelation` (§8B.2 derivation edges).
pub const fn derivation_relation_token(relation: DerivationRelation) -> &'static str {
    match relation {
        DerivationRelation::DerivedFrom => "derived_from",
        DerivationRelation::Supports => "supports",
    }
}

/// Closed wire token for the status carried by a derivation edge.
pub const fn edge_status_token(status: StructureEdgeStatus) -> &'static str {
    match status {
        StructureEdgeStatus::Proposed => "proposed",
        StructureEdgeStatus::Accepted => "accepted",
        StructureEdgeStatus::Conflicting => "conflicting",
        StructureEdgeStatus::Rejected => "rejected",
    }
}

/// Closed wire token for a `ContextDiagnostic` (§8B.2). Delegates to the
/// existing closed `document_context` surface rather than minting a second
/// vocabulary.
pub fn diagnostic_token(diagnostic: ContextDiagnostic) -> &'static str {
    diagnostic.as_str()
}

/// Nullable `view` token for a request kind (§6 rule 1): `Some(covering)` for
/// the token-derived kinds, `None` for the structural-only kinds.
pub const fn view_token(kind: ContextRequestKind) -> Option<&'static str> {
    match kind {
        ContextRequestKind::OpenSeriesHead
        | ContextRequestKind::ScopedAlias
        | ContextRequestKind::CurrentDocumentRequisites
        | ContextRequestKind::ExplicitAnchorLookup => Some(VIEW_COVERING),
        ContextRequestKind::AncestorPath | ContextRequestKind::AdjacentBlocks => None,
    }
}

// --------------------------------------------------------------- records #

/// A context claim sub-record: the closed claim vocabulary plus its localized
/// source anchor (span or closed refusal).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextClaimRecord {
    /// Claimed field name.
    pub field: String,
    /// Closed claim status token source.
    pub claim_status: ContextClaimStatus,
    /// Closed derivation-source token source.
    pub derivation: DerivationSource,
    /// The source node the claim names.
    pub source_node_ref: String,
    /// The localized claim anchor or its closed refusal.
    pub anchor: SourceRef,
}

/// A context derivation edge sub-record: `from`/`to`/`relation`/`status` plus
/// the localized anchor of the edge evidence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextDerivationRecord {
    /// Source node.
    pub from: String,
    /// Target node.
    pub to: String,
    /// Closed relation token source.
    pub relation: DerivationRelation,
    /// Edge status token source.
    pub status: StructureEdgeStatus,
    /// The localized edge anchor or its closed refusal.
    pub anchor: SourceRef,
}

/// One context result record (`kind: "result"`, §8B.2): one worklist request's
/// closed outcome plus its localized anchors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextResultRecord {
    /// Wire `ref` (stable family-local id, `ctx:<n>`).
    pub reference: String,
    /// The producing worklist request identity.
    pub request_ref: String,
    /// The request kind.
    pub request_kind: ContextRequestKind,
    /// Nullable `view` token (never `Some` for structural-only kinds).
    pub view: Option<&'static str>,
    /// Closed context status.
    pub status: ContextStatus,
    /// Claim sub-records (deterministic producer order).
    pub claims: Vec<ContextClaimRecord>,
    /// Derivation edge sub-records (deterministic producer order).
    pub derivations: Vec<ContextDerivationRecord>,
    /// Closed diagnostics, in producer order.
    pub diagnostics: Vec<ContextDiagnostic>,
    /// Localized anchors consumed by the result, in producer order.
    pub anchors: Vec<SourceRef>,
}

/// The single aggregate context run record (`kind: "run"`, §8B.2). The counts
/// are derived from the emitted result records, so a failed or empty build is
/// represented honestly instead of being dropped.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextRunRecord {
    /// Wire `ref` (`ctx:run`).
    pub reference: String,
    /// Number of emitted context result records.
    pub requests: usize,
    /// Result records with `status == resolved`.
    pub resolved: usize,
    /// Result records with any non-resolved status.
    pub non_resolved: usize,
    /// Per-status counts, sorted by `ContextStatus` ordinal.
    pub status_counts: Vec<(ContextStatus, usize)>,
    /// True when any result reached `ContextStatus::Limit`.
    pub limit_reached: bool,
    /// The union of the result diagnostics, in first-seen order.
    pub diagnostics: Vec<ContextDiagnostic>,
}

impl ContextRunRecord {
    /// A zero-request run record carrying the given closed diagnostics.
    pub fn empty(diagnostics: Vec<ContextDiagnostic>) -> Self {
        Self {
            reference: RUN_REFERENCE.to_owned(),
            requests: 0,
            resolved: 0,
            non_resolved: 0,
            status_counts: Vec::new(),
            limit_reached: false,
            diagnostics,
        }
    }
}

/// A single emitted context line: a result or the aggregate run record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContextRecord {
    /// One `kind: "result"` line.
    Result(ContextResultRecord),
    /// The only `kind: "run"` line.
    Run(ContextRunRecord),
}

impl ContextRecord {
    /// The closed wire `kind` token.
    pub const fn kind_token(&self) -> &'static str {
        match self {
            ContextRecord::Result(_) => KIND_RESULT,
            ContextRecord::Run(_) => KIND_RUN,
        }
    }

    /// The stable family-local `ref`.
    pub fn reference(&self) -> &str {
        match self {
            ContextRecord::Result(record) => &record.reference,
            ContextRecord::Run(record) => &record.reference,
        }
    }
}

/// True when `records` is the trivially empty context stream of §8B.1: exactly
/// one aggregate `run` record with zero `requests`, zero `resolved`, zero
/// `non_resolved`, an empty per-status count map, `limit_reached` false and no
/// diagnostics. A zero-request run carrying `missing_document_structure` is
/// **not** trivially empty — the six-family admission of §8B.4 must refuse it
/// rather than treat a failed context build as a silent pass. `[bounded]`
/// (R29-F03, D690)
pub fn context_stream_is_trivially_empty(records: &[ContextRecord]) -> bool {
    matches!(
        records,
        [ContextRecord::Run(run)]
            if run.requests == 0
                && run.resolved == 0
                && run.non_resolved == 0
                && run.status_counts.is_empty()
                && !run.limit_reached
                && run.diagnostics.is_empty()
    )
}

// ----------------------------------------------------------------- build #

/// Builds the deterministic context record stream from an analysis block
/// layout and its pinned parent mapping (§8B.5).
///
/// The chain is the unchanged document-context path: a synthetic
/// [`ParsedBlock`] per analysis block feeds
/// `build_document_structure_index` → `build_document_analysis_overlay` →
/// `ContextWorklist::run`; requests come deterministically from the overlay
/// frames (`OpenSeriesHead`, `ExplicitAnchorLookup`, `CurrentDocumentRequisites`).
/// Every anchor is localized through the same [`AnalysisBlockLayout`] and S01
/// seam as the S02 records; a refusal is carried in place of a span, never
/// dropped. The result records are followed by exactly one aggregate run
/// record.
///
/// An index/overlay build failure (for example `ConflictingRoleEvidence`) is a
/// closed outcome: the stream is a single run record carrying
/// `missing_document_structure` and zero requests. The input layout and mapping
/// are read-only.
pub fn build_context_records(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> Vec<ContextRecord> {
    let blocks = match synthesize_blocks(layout) {
        Ok(blocks) => blocks,
        Err(()) => {
            return vec![ContextRecord::Run(ContextRunRecord::empty(vec![
                ContextDiagnostic::MissingDocumentStructure,
            ]))]
        }
    };
    let version = mapping.version().clone();
    let index = match build_document_structure_index(version, &blocks) {
        Ok(index) => index,
        Err(_) => {
            return vec![ContextRecord::Run(ContextRunRecord::empty(vec![
                ContextDiagnostic::MissingDocumentStructure,
            ]))]
        }
    };
    let overlay = match build_overlay(&index, &blocks) {
        Some(overlay) => overlay,
        None => {
            return vec![ContextRecord::Run(ContextRunRecord::empty(vec![
                ContextDiagnostic::MissingDocumentStructure,
            ]))]
        }
    };

    let requisites = build_requisites_sidecar(layout, mapping);
    let doc_ref = mapping.version().document_version_ref();
    let requests = build_requests(&overlay, layout, doc_ref);
    if requests.is_empty() {
        return vec![ContextRecord::Run(ContextRunRecord::empty(Vec::new()))];
    }

    let mut worklist = ContextWorklist::new(Default::default());
    let report = worklist.run(
        ContextEnvironment {
            index: &index,
            overlay: &overlay,
            requisites: requisites.as_ref(),
        },
        &requests,
    );

    let mut records: Vec<ContextRecord> = Vec::new();
    let mut status_counts: BTreeMap<ContextStatus, usize> = BTreeMap::new();
    let mut aggregate_diagnostics: Vec<ContextDiagnostic> = Vec::new();
    for (position, request) in requests.iter().enumerate() {
        let key = request.memo_key();
        let Some(result) = report.results.get(&key) else {
            continue;
        };
        *status_counts.entry(result.status).or_default() += 1;
        for diagnostic in &result.diagnostics {
            if !aggregate_diagnostics.contains(diagnostic) {
                aggregate_diagnostics.push(*diagnostic);
            }
        }
        records.push(ContextRecord::Result(ContextResultRecord {
            reference: format!("ctx:{position}"),
            request_ref: result.request_ref.clone(),
            request_kind: request.kind(),
            view: view_token(request.kind()),
            status: result.status,
            claims: claim_records(result, &overlay, &index, layout, mapping),
            derivations: derivation_records(result, &overlay, layout, mapping),
            diagnostics: result.diagnostics.clone(),
            anchors: anchor_records(request, result, &overlay, layout, mapping),
        }));
    }

    let requests_emitted = records.len();
    let resolved = status_counts
        .get(&ContextStatus::Resolved)
        .copied()
        .unwrap_or(0);
    let limit_reached = status_counts.contains_key(&ContextStatus::Limit);
    records.push(ContextRecord::Run(ContextRunRecord {
        reference: RUN_REFERENCE.to_owned(),
        requests: requests_emitted,
        resolved,
        non_resolved: requests_emitted - resolved,
        status_counts: status_counts.into_iter().collect(),
        limit_reached,
        diagnostics: aggregate_diagnostics,
    }));
    records
}

/// Synthesizes one `ParsedBlock` per analysis block (§8B.5). Style is `Heading`
/// when `find_legal_markers` finds a structural marker, otherwise `BodyText`.
/// The synthetic `SourceLocation` is never serialized.
fn synthesize_blocks(layout: &AnalysisBlockLayout) -> Result<Vec<ParsedBlock>, ()> {
    let stream = SourceStreamId::parse(SYNTHETIC_STREAM).map_err(|_| ())?;
    let mut blocks = Vec::with_capacity(layout.blocks.len());
    for block in &layout.blocks {
        let text = sanitize_block_text(&block.text);
        if text.is_empty() {
            return Err(());
        }
        let span = SourceSpan::try_new(0, text.len()).map_err(|_| ())?;
        let style = if find_legal_markers(&text).is_empty() {
            ParagraphStyle::BodyText
        } else {
            ParagraphStyle::Heading
        };
        let parsed = ParsedBlock::try_new(
            text,
            None,
            style,
            SourceLocation::new(stream.clone(), span),
            SourceFormatId::ConsultantWordMl,
        )
        .map_err(|_| ())?;
        blocks.push(parsed);
    }
    Ok(blocks)
}

/// `ParsedBlock` requires non-blank text. Analysis blocks are non-empty by
/// construction, but a whitespace-only block is possible; replace every code
/// point by `len_utf8` ASCII `x` bytes so the byte length (and therefore every
/// downstream byte offset) is preserved while the text becomes non-blank. The
/// substituted text feeds only the structural index/overlay, never the wire.
fn sanitize_block_text(text: &str) -> String {
    if !text.trim().is_empty() {
        return text.to_owned();
    }
    let mut out = String::with_capacity(text.len());
    for character in text.chars() {
        for _ in 0..character.len_utf8() {
            out.push('x');
        }
    }
    out
}

/// Builds the unchanged derived overlay for the synthesized blocks.
fn build_overlay(
    index: &DocumentStructureIndex,
    blocks: &[ParsedBlock],
) -> Option<DocumentAnalysisOverlay> {
    let mut frame_rows = Vec::with_capacity(blocks.len());
    let mut capture_rows = Vec::with_capacity(blocks.len());
    for (position, block) in blocks.iter().enumerate() {
        let block_id = BlockId::parse(&format!("block-{position}")).ok()?;
        let tokens = crate::lexer::lex(block.text());
        let captures = capture_lawrefs(block.text());
        let acts = extract_act_list_frames(block.text(), &captures);
        let structural =
            extract_structural_frames(&tokens, block.text(), &find_legal_markers(block.text()));
        frame_rows.push((block_id.clone(), acts, structural));
        capture_rows.push((block_id, captures.captures().to_vec()));
    }
    build_document_analysis_overlay(index, &frame_rows, &capture_rows).ok()
}

/// Deterministic requests from the overlay frames under the §8C.2 trigger
/// policy. `current_document_requisites` is emitted at most once and only when
/// a block carries a this-ref surface; `open_series_head` only for a frame with
/// a non-rejected incoming `ContinuesSeries` edge (a proven continuation tail);
/// `explicit_anchor_lookup` only for a frame whose block carries at least one
/// captured explicit mention. `ancestor_path`/`adjacent_blocks`/`scoped_alias`
/// are never emitted.
fn build_requests(
    overlay: &DocumentAnalysisOverlay,
    layout: &AnalysisBlockLayout,
    doc_ref: &str,
) -> Vec<ContextRequest> {
    let mut requests = Vec::new();

    // Exactly one requisites request per document: the first block (document
    // order) with a non-empty this-ref surface and at least one frame. Origin
    // is that block's first frame; the grammar evidence authorizes `Type`.
    for (position, block) in layout.blocks.iter().enumerate() {
        if detect_this_ref_grammar(&block.text).is_empty() {
            continue;
        }
        let block_id = format!("block-{position}");
        let Some(frame) = overlay
            .frames()
            .iter()
            .find(|frame| frame.block_id.as_str() == block_id)
        else {
            continue;
        };
        requests.push(ContextRequest::current_document_requisites(
            frame.frame_ref.clone(),
            ThisRefGrammarEvidence::new([RequisitesField::Type]),
        ));
        break;
    }

    // Only a frame proven to be a continuation tail (a non-rejected inbound
    // `ContinuesSeries` edge) can ask for its open series head.
    for frame in overlay.frames() {
        let is_tail = overlay.edges().iter().any(|edge| {
            edge.relation == ContextualEdgeKind::ContinuesSeries
                && edge.to == frame.frame_ref.as_str()
                && edge.status != StructureEdgeStatus::Rejected
        });
        if is_tail {
            requests.push(ContextRequest::new(
                ContextRequestKind::OpenSeriesHead,
                doc_ref.to_owned(),
                frame.frame_ref.clone(),
                Vec::new(),
                None,
                None,
                Vec::new(),
                PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
                CONTEXT_RULE.to_owned(),
            ));
        }
    }

    // Only a frame whose own block carries a captured explicit mention can ask
    // for the exact designation lookup.
    for frame in overlay.frames() {
        let has_mention = overlay
            .mentions()
            .iter()
            .any(|mention| mention.block_id == frame.block_id);
        if has_mention {
            requests.push(ContextRequest::new(
                ContextRequestKind::ExplicitAnchorLookup,
                doc_ref.to_owned(),
                frame.frame_ref.clone(),
                Vec::new(),
                None,
                Some(frame.frame_ref.as_str().to_owned()),
                Vec::new(),
                PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
                CONTEXT_RULE.to_owned(),
            ));
        }
    }

    requests
}

/// Extractor profile carried by every letterhead-derived requisites claim.
const LETTERHEAD_PROFILE: &str = "npa_link::recognize_letterhead/v1";

/// Rebuilds the `CurrentDocumentRequisites` sidecar deterministically from the
/// pinned parent (§8C.1). The layout block texts (document order) feed
/// `npa_link::recognize_letterhead`; a recognized letterhead yields `Type` from
/// its kind, `Org` from a non-empty issuer, and `Date`/`Number` only from a
/// real value (never the `—` placeholder). No recognized letterhead → `None`.
/// This is a pure function of `layout` + `mapping`, so the independent
/// verifier's re-derivation reproduces it exactly.
fn build_requisites_sidecar(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> Option<CurrentDocumentRequisites> {
    let paras = layout.block_texts();
    let letterhead = crate::npa_link::recognize_letterhead(&paras)?;
    let doc_ref = mapping.version().document_version_ref().to_owned();
    let span = TextSpan::try_new(letterhead.evidence.start, letterhead.evidence.end).ok()?;
    let make_anchor =
        || SourceAnchor::try_new(span, format!("block-{}", letterhead.evidence.block)).ok();

    let mut claims: Vec<RequisitesClaim> = Vec::new();
    let mut push = |field: RequisitesField, raw_value: String| -> Option<()> {
        let anchor = make_anchor()?;
        let claim = RequisitesClaim::try_new(
            format!("letterhead-{}", field.as_str()),
            doc_ref.clone(),
            field,
            raw_value,
            RequisitesSourceKind::DocumentHead,
            anchor,
            LETTERHEAD_PROFILE.to_owned(),
            RequisitesExtractionStatus::Observed,
        )
        .ok()?;
        claims.push(claim);
        Some(())
    };

    push(RequisitesField::Type, letterhead.kind.clone())?;
    if !letterhead.issuer.trim().is_empty() {
        push(RequisitesField::Org, letterhead.issuer.clone())?;
    }
    if let Some(value) = real_requisite_value(&letterhead.date) {
        push(RequisitesField::Date, value)?;
    }
    if let Some(value) = real_requisite_value(&letterhead.number) {
        push(RequisitesField::Number, value)?;
    }

    CurrentDocumentRequisites::try_new(doc_ref, claims).ok()
}

/// A requisites value is real only when it is present and not the `—`
/// placeholder; an absent value is never minted as an observed claim.
fn real_requisite_value(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() || trimmed == "—" {
        return None;
    }
    Some(trimmed.to_owned())
}

/// Closed refusal for a node/span whose block cannot be recovered.
fn unmapped_refusal() -> SourceRef {
    SourceRef::Refused(AnalysisRefusal::local(AnalysisRefusalKind::UnmappedBlock))
}

/// Localizes `(block, span)` or carries a closed refusal when the block is
/// unknown or the seam refuses the span.
fn localize(
    block: Option<usize>,
    span: TextSpan,
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> SourceRef {
    match block {
        Some(block) => SourceRef::from(resolve_span(
            layout,
            mapping,
            LocalSpan {
                block,
                start: span.start(),
                end: span.end(),
            },
        )),
        None => unmapped_refusal(),
    }
}

/// Parses `block-<i>` into its analysis block index.
fn parse_block_index(block_id: &str) -> Option<usize> {
    block_id.strip_prefix("block-")?.parse().ok()
}

/// The analysis block index of an overlay frame, by frame reference.
fn block_index_for_frame(overlay: &DocumentAnalysisOverlay, frame_ref: &str) -> Option<usize> {
    overlay
        .frames()
        .iter()
        .find(|frame| frame.frame_ref.as_str() == frame_ref)
        .and_then(|frame| parse_block_index(frame.block_id.as_str()))
}

/// Resolves a claim/derivation source node reference to `(block, span)` using
/// only the overlay/index nodes (frames, mentions, source blocks).
fn source_node_anchor(
    overlay: &DocumentAnalysisOverlay,
    index: &DocumentStructureIndex,
    node_ref: &str,
) -> Option<(usize, TextSpan)> {
    if let Some(frame) = overlay
        .frames()
        .iter()
        .find(|frame| frame.frame_ref.as_str() == node_ref)
    {
        return Some((
            parse_block_index(frame.block_id.as_str())?,
            frame.local_anchor,
        ));
    }
    if let Some(mention) = overlay
        .mentions()
        .iter()
        .find(|mention| mention.mention_ref.as_str() == node_ref)
    {
        return Some((
            parse_block_index(mention.block_id.as_str())?,
            mention.local_anchor,
        ));
    }
    if let Some(block) = index
        .source_blocks()
        .iter()
        .find(|block| block.block_id().as_str() == node_ref)
    {
        return Some((block.order(), block.local_anchor()));
    }
    None
}

/// Builds the claim sub-records for one result, localizing each claim's source
/// node or carrying a closed refusal.
fn claim_records(
    result: &crate::document_context::ContextResult,
    overlay: &DocumentAnalysisOverlay,
    index: &DocumentStructureIndex,
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> Vec<ContextClaimRecord> {
    result
        .candidate_claims
        .iter()
        .map(|claim| {
            let anchor = match source_node_anchor(overlay, index, &claim.source_node_ref) {
                Some((block, span)) => localize(Some(block), span, layout, mapping),
                None => unmapped_refusal(),
            };
            ContextClaimRecord {
                field: claim.field.clone(),
                claim_status: claim.claim_status,
                derivation: claim.derivation,
                source_node_ref: claim.source_node_ref.clone(),
                anchor,
            }
        })
        .collect()
}

/// Builds the derivation sub-records for one result. Derivation edges carry a
/// bare `TextSpan`; their block is recovered from the `from` node or refused.
fn derivation_records(
    result: &crate::document_context::ContextResult,
    overlay: &DocumentAnalysisOverlay,
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> Vec<ContextDerivationRecord> {
    result
        .derivation_edges
        .iter()
        .map(|edge| {
            let block = block_index_for_frame(overlay, &edge.from);
            ContextDerivationRecord {
                from: edge.from.clone(),
                to: edge.to.clone(),
                relation: edge.relation,
                status: edge.status,
                anchor: localize(block, edge.evidence, layout, mapping),
            }
        })
        .collect()
}

/// Builds the localized anchors of one result. Requests that did not reach the
/// leaf (Limit/Cycle) carry no anchors, matching the worklist result. The
/// block of each candidate evidence span is recovered from the candidate's
/// node reference (the head frame) or the request origin (the tail frame);
/// when it cannot be recovered the anchor is a closed refusal, never dropped.
fn anchor_records(
    request: &ContextRequest,
    result: &crate::document_context::ContextResult,
    overlay: &DocumentAnalysisOverlay,
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> Vec<SourceRef> {
    if matches!(result.status, ContextStatus::Limit | ContextStatus::Cycle) {
        return Vec::new();
    }
    let key = request.memo_key();
    let origin = key.origin_frame_ref.as_str().to_owned();
    let mut anchors = Vec::new();
    match request.kind() {
        ContextRequestKind::ExplicitAnchorLookup => {
            let Some(explicit) = key.explicit_key.as_deref() else {
                return anchors;
            };
            let outcome = explicit_anchor_lookup(overlay, explicit);
            for candidate in &outcome.candidates {
                let block = block_index_for_frame(overlay, &candidate.node_ref);
                for span in &candidate.evidence {
                    anchors.push(localize(block, *span, layout, mapping));
                }
            }
        }
        ContextRequestKind::OpenSeriesHead => {
            let Ok(frame) = FrameRef::parse(&origin) else {
                return anchors;
            };
            let outcome = open_series_head(overlay, &frame);
            let origin_block = block_index_for_frame(overlay, &origin);
            for candidate in &outcome.candidates {
                let head_block = block_index_for_frame(overlay, &candidate.node_ref);
                for (position, span) in candidate.evidence.iter().enumerate() {
                    let block = if position == 0 {
                        head_block
                    } else {
                        origin_block
                    };
                    anchors.push(localize(block, *span, layout, mapping));
                }
            }
        }
        _ => {
            // These request kinds are not emitted by `build_requests`; their raw
            // block-relative anchors carry no recoverable block here, so they
            // are refused closed rather than dropped.
            for _ in &result.source_anchors {
                anchors.push(unmapped_refusal());
            }
        }
    }
    anchors
}
