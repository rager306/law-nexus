//! M206/S06 red reproduction oracle for RC28-F06..F10.
//! These tests intentionally assert the admitted desired contract; they must fail
//! against the pre-remediation runtime and pass after the minimal fix.

use ln_decode::capture_bounds::{
    arbitrate_pair, span_relation, PairDiagnostic, PairOutcome, SpanRelation,
};
use ln_decode::current_requisites::{
    CurrentDocumentRequisites, RequisitesClaim, RequisitesExtractionStatus, RequisitesField,
    RequisitesSourceKind, SourceAnchor, ThisRefGrammarEvidence,
};
use ln_decode::document_context::{
    build_document_analysis_overlay, build_document_structure_index, detect_this_ref_grammar,
    open_series_head, BlockId, ContainerRole, ContextBudgets, ContextClaimStatus,
    ContextDiagnostic, ContextEnvironment, ContextRequest, ContextStatus, ContextWorklist,
    ContextualEdge, ContextualEdgeKind, DocumentAnalysisOverlay, DocumentStructureIndex,
    DocumentVersionRef, FrameRef, StructureEdgeStatus,
};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    TextSpan,
};
use ln_decode::lawref::capture_lawrefs;
use ln_decode::lexer::lex;
use ln_decode::local_grammar::{extract_act_list_frames, extract_structural_frames, FrameStatus};
use ln_decode::morphology::find_legal_markers;
use ln_decode::sentence::split_legal_sentences;

fn block(text: &str, style: ParagraphStyle, order: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:m206-s06").unwrap(),
            SourceSpan::try_new(order * 100, order * 100 + text.len()).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

fn index(
    blocks: &[ParsedBlock],
) -> Result<
    ln_decode::document_context::DocumentStructureIndex,
    ln_decode::document_context::IndexBuildError,
> {
    build_document_structure_index(
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap(),
        blocks,
    )
}

#[test]
fn rc28_f06_sibling_heading_closes_previous_container() {
    let blocks = vec![
        block("Закон", ParagraphStyle::Title, 0),
        block("Статья 1. Первый", ParagraphStyle::Heading, 1),
        block("Первый текст", ParagraphStyle::BodyText, 2),
        block("Статья 2. Второй", ParagraphStyle::Heading, 3),
        block("Второй текст", ParagraphStyle::BodyText, 4),
    ];
    let built = index(&blocks);
    assert!(
        built.is_ok(),
        "RC28-F06 structure index must admit sibling headings: {built:?}"
    );
    let built = built.unwrap();
    let path = built
        .ancestor_path(&BlockId::parse("block-4").unwrap())
        .unwrap_or_else(|error| panic!("RC28-F06 expected a sibling path, got {error:?}"));
    assert_eq!(
        path[0].role(),
        ContainerRole::Article,
        "RC28-F06 sibling body must be in the second article"
    );
    assert_eq!(
        path.iter()
            .filter(|node| node.role() == ContainerRole::Article)
            .count(),
        1,
        "RC28-F06 sibling closure must not retain the first article"
    );
    assert_eq!(
        path[0].designation(),
        Some("statya:2"),
        "RC28-F06 case identifier: sibling article 2"
    );
}

#[test]
fn rc28_f07_three_unrelated_blocks_have_no_parent_edges() {
    let blocks = vec![
        block(
            "федерального закона от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            0,
        ),
        block(
            "федерального закона от 02.02.2021 N 2-ФЗ",
            ParagraphStyle::BodyText,
            1,
        ),
        block(
            "федерального закона от 03.03.2022 N 3-ФЗ",
            ParagraphStyle::BodyText,
            2,
        ),
    ];
    let built = index(&blocks).unwrap();
    let frames = blocks
        .iter()
        .map(|source| {
            (
                BlockId::parse(&format!(
                    "block-{}",
                    source.source_location().span().start() / 100
                ))
                .unwrap(),
                extract_act_list_frames(source.text(), &capture_lawrefs(source.text())),
                Vec::new(),
            )
        })
        .collect::<Vec<_>>();
    let overlay = build_document_analysis_overlay(&built, &frames, &[]).unwrap();
    let continuations = overlay
        .edges()
        .iter()
        .filter(|edge| edge.relation == ContextualEdgeKind::ContinuesSeries)
        .count();
    assert_eq!(
        continuations, 0,
        "RC28-F07 case identifier: unrelated citations must not gain ContinuesSeries edges"
    );
}

fn full_requisites() -> CurrentDocumentRequisites {
    CurrentDocumentRequisites::try_new("doc-v1".into(), all_field_claims("m206-s07", "value"))
        .unwrap()
}

/// One observed claim per closed requisites field, all from the document head.
/// Values differ per field so no cross-field equality is implied.
fn all_field_claims(prefix: &str, value_prefix: &str) -> Vec<RequisitesClaim> {
    RequisitesField::ALL
        .into_iter()
        .enumerate()
        .map(|(index, field)| {
            RequisitesClaim::try_new(
                format!("{prefix}-{index}"),
                "doc-v1".into(),
                field,
                format!("{value_prefix}-{index}"),
                RequisitesSourceKind::DocumentHead,
                SourceAnchor::try_new(
                    TextSpan::try_new(index, index + 1).unwrap(),
                    format!("anchor-{index}"),
                )
                .unwrap(),
                "profile-v1".into(),
                RequisitesExtractionStatus::Observed,
            )
            .unwrap()
        })
        .collect()
}

/// Requisites environment for the single-block ThisRef fixture.
fn this_ref_environment<'a>(
    index: &'a ln_decode::document_context::DocumentStructureIndex,
    overlay: &'a ln_decode::document_context::DocumentAnalysisOverlay,
    sidecar: &'a CurrentDocumentRequisites,
) -> ContextEnvironment<'a> {
    ContextEnvironment {
        index,
        overlay,
        requisites: Some(sidecar),
    }
}

fn this_ref_fixture() -> (
    ln_decode::document_context::DocumentStructureIndex,
    ln_decode::document_context::DocumentAnalysisOverlay,
) {
    let blocks = vec![block(
        "Настоящего Закона следует придерживаться.",
        ParagraphStyle::BodyText,
        0,
    )];
    let built = index(&blocks).unwrap();
    let overlay = build_document_analysis_overlay(&built, &[], &[]).unwrap();
    (built, overlay)
}

fn this_ref_request(evidence: ThisRefGrammarEvidence) -> ContextRequest {
    ContextRequest::current_document_requisites(FrameRef::parse("block-0").unwrap(), evidence)
}

#[test]
fn rc28_f08_this_ref_survives_nonempty_worklist_and_empty_or_cited_negatives() {
    let blocks = vec![block(
        "Настоящего Закона следует придерживаться.",
        ParagraphStyle::BodyText,
        0,
    )];
    let built = index(&blocks).unwrap();
    let overlay = build_document_analysis_overlay(&built, &[], &[]).unwrap();
    let evidence = detect_this_ref_grammar(blocks[0].text());
    assert!(
        !evidence.is_empty(),
        "RC28-F08 case identifier: ThisRef evidence must be nonempty"
    );
    let request = ContextRequest::current_document_requisites(
        ln_decode::document_context::FrameRef::parse("block-0").unwrap(),
        ln_decode::current_requisites::ThisRefGrammarEvidence::new([
            ln_decode::current_requisites::RequisitesField::Type,
        ]),
    );
    let sidecar = full_requisites();
    let environment = ContextEnvironment {
        index: &built,
        overlay: &overlay,
        requisites: Some(&sidecar),
    };
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(environment, &[request]);
    let result = report.results.values().next().unwrap();
    assert_eq!(
        result.status,
        ContextStatus::Resolved,
        "RC28-F08 case identifier: nonempty ThisRef must resolve through worklist"
    );
    assert!(
        detect_this_ref_grammar("").is_empty(),
        "RC28-F08 empty ThisRef must remain negative"
    );
    assert!(
        detect_this_ref_grammar("согласно статье 5").is_empty(),
        "RC28-F08 cited-act wording must remain negative"
    );
}

#[test]
fn rc28_f09_independent_sentences_and_incomplete_tail_keep_local_origins() {
    let first = "федерального закона от 01.01.2020 N 1-ФЗ";
    let second = "федерального закона от 02.02.2021 N 2-ФЗ";
    let source = format!("{first}. {second}.");
    let captures = capture_lawrefs(&source);
    let frames = extract_act_list_frames(&source, &captures);
    assert_eq!(
        frames.len(),
        2,
        "RC28-F09 case identifier: independent sentences must not be merged"
    );
    assert!(
        frames
            .iter()
            .all(|frame| frame.local_anchor.start() < frame.local_anchor.end()),
        "RC28-F09 every frame needs an origin span"
    );
    let incomplete = extract_act_list_frames(
        "федерального закона от 03.03.2022",
        &capture_lawrefs("федерального закона от 03.03.2022"),
    );
    assert_eq!(
        incomplete.len(),
        1,
        "RC28-F09 case identifier: incomplete tail must remain observable"
    );
    assert_eq!(
        incomplete[0].status,
        FrameStatus::Ambiguous,
        "RC28-F09 incomplete tail must be ambiguous, not silently dropped"
    );
}

#[test]
fn rc28_f10_original_spans_accept_en_and_em_dash_range_variants() {
    for dash in ["–", "—"] {
        let source = format!("статьями 7.29 {dash} 7.32");
        let captures = capture_lawrefs(&source);
        let range = captures
            .captures()
            .iter()
            .find(|capture| capture.slots.range.is_some());
        assert!(
            range.is_some(),
            "RC28-F10 case identifier: original {dash} range must be captured"
        );
        let capture = range.unwrap();
        assert_eq!(
            capture.user_text(&source),
            source,
            "RC28-F10 original span must preserve the source dash"
        );
    }
    let _ = extract_structural_frames(
        &lex("статьями 7.29 – 7.32"),
        "статьями 7.29 – 7.32",
        &find_legal_markers("статьями 7.29 – 7.32"),
    );
}

/// Overlay built from the act-list frames of the given blocks, in document
/// order. Used by the F07 continuation-eligibility scenarios.
fn overlay_from_blocks(
    built: &DocumentStructureIndex,
    blocks: &[ParsedBlock],
) -> DocumentAnalysisOverlay {
    let frames = blocks
        .iter()
        .enumerate()
        .map(|(order, source)| {
            (
                BlockId::parse(&format!("block-{order}")).unwrap(),
                extract_act_list_frames(source.text(), &capture_lawrefs(source.text())),
                Vec::new(),
            )
        })
        .collect::<Vec<_>>();
    build_document_analysis_overlay(built, &frames, &[]).unwrap()
}

fn continuations(overlay: &DocumentAnalysisOverlay) -> Vec<&ContextualEdge> {
    overlay
        .edges()
        .iter()
        .filter(|edge| edge.relation == ContextualEdgeKind::ContinuesSeries)
        .collect()
}

/// `F07-series-positive`: open coordination, source-block order, compatible
/// owner/boundary and a retained derivation path are all present.
#[test]
fn rc28_f07_series_positive_proven_head_open_tail_and_document_order() {
    // The head proves its own act type after a long prefix, so its
    // fragment-local anchor starts *later* than the tail's. Eligibility must
    // therefore be decided by source-block document order and never by
    // comparing fragment-local offsets.
    let blocks = vec![
        block(
            "Действующее законодательство и федеральный закон от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            0,
        ),
        block("от 02.02.2021 N 2-ФЗ", ParagraphStyle::BodyText, 1),
    ];
    let built = index(&blocks).unwrap();
    let overlay = overlay_from_blocks(&built, &blocks);
    let edges = continuations(&overlay);
    assert_eq!(
        edges.len(),
        1,
        "F07-series-positive: exactly one eligible origin must mint one edge"
    );
    let edge = edges[0];
    assert_eq!(edge.from, "block-0-frame-0");
    assert_eq!(edge.to, "block-1-frame-0");
    assert_eq!(edge.status, StructureEdgeStatus::Proposed);
    assert_eq!(
        edge.evidence.len(),
        2,
        "F07-series-positive: both local derivations must be retained"
    );
    assert!(
        edge.evidence[0].start() > edge.evidence[1].start(),
        "F07-series-positive: document order, not fragment-local offsets, decides eligibility"
    );
    let outcome = open_series_head(&overlay, &FrameRef::parse("block-1-frame-0").unwrap());
    assert_eq!(outcome.status, ContextStatus::Resolved);
    assert_eq!(outcome.candidates.len(), 1);
    assert_eq!(outcome.candidates[0].node_ref, "block-0-frame-0");
}

/// `F07-series-invalid`: missing order, incompatible owner/boundary, or an
/// unproven head must never prove continuation eligibility.
#[test]
fn rc28_f07_series_invalid_order_boundary_and_unproven_head_mint_nothing() {
    // (a) the open tail precedes every proven head in document order.
    let reversed = vec![
        block("от 02.02.2021 N 2-ФЗ", ParagraphStyle::BodyText, 0),
        block(
            "федеральный закон от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            1,
        ),
    ];
    let built = index(&reversed).unwrap();
    let overlay = overlay_from_blocks(&built, &reversed);
    assert!(
        continuations(&overlay).is_empty(),
        "F07-series-invalid: a head after the tail must not authorize it"
    );

    // (b) head and tail sit in different owner/boundary containers.
    let split = vec![
        block("Закон", ParagraphStyle::Title, 0),
        block("Статья 1. Первый", ParagraphStyle::Heading, 1),
        block(
            "федеральный закон от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            2,
        ),
        block("Статья 2. Второй", ParagraphStyle::Heading, 3),
        block("от 02.02.2021 N 2-ФЗ", ParagraphStyle::BodyText, 4),
    ];
    let built = index(&split).unwrap();
    let overlay = overlay_from_blocks(&built, &split);
    assert!(
        continuations(&overlay).is_empty(),
        "F07-series-invalid: cross-container heads must not cross the owner boundary"
    );

    // (c) no frame proves its own act type, so no head exists at all. This is
    // also the bounded-hop case: an open coordination can never head another.
    let unproven = vec![
        block("от 01.01.2020 N 1-ФЗ", ParagraphStyle::BodyText, 0),
        block("от 02.02.2021 N 2-ФЗ", ParagraphStyle::BodyText, 1),
    ];
    let built = index(&unproven).unwrap();
    let overlay = overlay_from_blocks(&built, &unproven);
    assert!(
        continuations(&overlay).is_empty(),
        "F07-series-invalid: an unproven head must not authorize a continuation"
    );

    // (d) the earlier citation is incomplete (date without a document number),
    // so it is an ambiguous frame and cannot prove a series head. The frame
    // must exist with a proven act type, so the refusal is by frame status and
    // not by an empty frame list.
    let incomplete_head = vec![
        block(
            "федеральный закон от 01.01.2020",
            ParagraphStyle::BodyText,
            0,
        ),
        block("от 02.02.2021 N 2-ФЗ", ParagraphStyle::BodyText, 1),
    ];
    let head_frames = extract_act_list_frames(
        incomplete_head[0].text(),
        &capture_lawrefs(incomplete_head[0].text()),
    );
    assert_eq!(
        head_frames.len(),
        1,
        "F07-series-invalid: head frame exists"
    );
    assert_eq!(
        head_frames[0].status,
        FrameStatus::Ambiguous,
        "F07-series-invalid: an incomplete citation is ambiguous, not proposed"
    );
    assert!(
        !head_frames[0].head_roles.is_empty(),
        "F07-series-invalid: the act type is proven, only the requisites are incomplete"
    );
    let built = index(&incomplete_head).unwrap();
    let overlay = overlay_from_blocks(&built, &incomplete_head);
    assert!(
        continuations(&overlay).is_empty(),
        "F07-series-invalid: an incomplete citation must not authorize a continuation"
    );
}

/// `F08-self-positive`: detector evidence, request, dispatch and the sidecar
/// guard form one vertical.
#[test]
fn rc28_f08_self_positive_authorizes_through_typed_request_evidence() {
    let (built, overlay) = this_ref_fixture();
    let spans = detect_this_ref_grammar("Настоящего Закона следует придерживаться.");
    assert_eq!(
        spans.len(),
        1,
        "F08-self-positive: sentence-initial capitalization is the written form"
    );
    assert_eq!((spans[0].start(), spans[0].end()), (0, 33));
    let request = this_ref_request(ThisRefGrammarEvidence::new([RequisitesField::Type]));
    assert!(
        request.this_ref_evidence().is_some(),
        "F08-self-positive: evidence must be persisted on the request, not in a label"
    );
    let sidecar = full_requisites();
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(this_ref_environment(&built, &overlay, &sidecar), &[request]);
    let result = report.results.values().next().unwrap();
    assert_eq!(result.status, ContextStatus::Resolved);
    assert_eq!(result.candidate_claims.len(), 1);
    assert_eq!(
        result.candidate_claims[0].claim_status,
        ContextClaimStatus::Inherited
    );
    assert!(!result.candidate_claims[0].source_node_ref.is_empty());
}

/// `F08-cited-act-negative`: an ordinary citation stays an earlier cited act,
/// and a missing sidecar stays unavailable even with admitted evidence.
#[test]
fn rc28_f08_cited_act_negative_and_missing_sidecar_stay_refused() {
    let (built, overlay) = this_ref_fixture();
    assert!(
        detect_this_ref_grammar("согласно статье 5").is_empty(),
        "F08-cited-act-negative: ordinary citation must not admit ThisRef grammar"
    );
    let sidecar = full_requisites();
    let empty_request = this_ref_request(ThisRefGrammarEvidence::default());
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        this_ref_environment(&built, &overlay, &sidecar),
        &[empty_request],
    );
    let result = report.results.values().next().unwrap();
    assert_eq!(
        result.status,
        ContextStatus::Partial,
        "F08-cited-act-negative: an available sidecar alone is not authorization"
    );
    assert!(
        result.candidate_claims.is_empty(),
        "F08-cited-act-negative: no self-reference may be fabricated"
    );
    assert!(result
        .diagnostics
        .contains(&ContextDiagnostic::InheritedFieldConflict));

    let admitted_request = this_ref_request(ThisRefGrammarEvidence::new([RequisitesField::Type]));
    let no_sidecar = ContextEnvironment {
        index: &built,
        overlay: &overlay,
        requisites: None,
    };
    let report =
        ContextWorklist::new(ContextBudgets::default()).run(no_sidecar, &[admitted_request]);
    let result = report.results.values().next().unwrap();
    assert_eq!(result.status, ContextStatus::Unavailable);
    assert!(result
        .diagnostics
        .contains(&ContextDiagnostic::MissingCurrentRequisites));
    assert!(result.candidate_claims.is_empty());
}

/// `F08-self-missing-conflict`: missing or conflicting required sidecar fields
/// fail closed even when the grammar evidence is admitted.
#[test]
fn rc28_f08_self_missing_or_conflicting_sidecar_fails_closed() {
    let (built, overlay) = this_ref_fixture();
    let mut claims = all_field_claims("m206-s07", "value");
    claims.push(
        RequisitesClaim::try_new(
            "catalog-type".into(),
            "doc-v1".into(),
            RequisitesField::Type,
            "other-type".into(),
            RequisitesSourceKind::SourceCatalog,
            SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), "catalog-anchor".into())
                .unwrap(),
            "profile-v1".into(),
            RequisitesExtractionStatus::Observed,
        )
        .unwrap(),
    );
    let conflicting = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    let date_only = CurrentDocumentRequisites::try_new(
        "doc-v1".into(),
        vec![RequisitesClaim::try_new(
            "date-only".into(),
            "doc-v1".into(),
            RequisitesField::Date,
            "2026-01-01".into(),
            RequisitesSourceKind::DocumentHead,
            SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), "date-anchor".into()).unwrap(),
            "profile-v1".into(),
            RequisitesExtractionStatus::Observed,
        )
        .unwrap()],
    )
    .unwrap();

    for (label, sidecar) in [
        ("conflicting required field", &conflicting),
        ("missing required field", &date_only),
    ] {
        let request = this_ref_request(ThisRefGrammarEvidence::new([RequisitesField::Type]));
        let mut worklist = ContextWorklist::new(ContextBudgets::default());
        let report = worklist.run(this_ref_environment(&built, &overlay, sidecar), &[request]);
        let result = report.results.values().next().unwrap();
        assert_eq!(
            result.status,
            ContextStatus::Partial,
            "F08-self-missing-conflict: {label} must not resolve"
        );
        assert!(
            result.candidate_claims.is_empty(),
            "F08-self-missing-conflict: {label} must not mint a claim"
        );
    }
}

/// `F08-self-positive` contra `F08-cited-act-negative`: one worklist must keep
/// the empty and the non-empty authorization apart in either arrival order,
/// and requests without a typed evidence surface must keep their exact memo
/// identity (the documented cycle-detection label contract).
#[test]
fn rc28_f08_memo_identity_separates_empty_and_nonempty_evidence_in_both_orders() {
    let (built, overlay) = this_ref_fixture();
    let sidecar = full_requisites();
    let empty = this_ref_request(ThisRefGrammarEvidence::default());
    let admitted = this_ref_request(ThisRefGrammarEvidence::new([RequisitesField::Type]));
    assert_ne!(
        empty.memo_key(),
        admitted.memo_key(),
        "F08: authorization evidence is part of the memo identity"
    );
    assert_eq!(empty.memo_key().authorization_evidence.as_deref(), Some(""));
    assert_eq!(
        admitted.memo_key().authorization_evidence.as_deref(),
        Some("type")
    );
    assert_eq!(
        ContextRequest::new(
            ln_decode::document_context::ContextRequestKind::AncestorPath,
            "doc-v1".into(),
            FrameRef::parse("block-0").unwrap(),
            Vec::new(),
            None,
            None,
            Vec::new(),
            1,
            "structural".into(),
        )
        .memo_key()
        .authorization_evidence,
        None,
        "F08: structural requests keep their recorded memo label"
    );

    for order in [
        vec![empty.clone(), admitted.clone()],
        vec![admitted.clone(), empty.clone()],
    ] {
        let mut worklist = ContextWorklist::new(ContextBudgets::default());
        let report = worklist.run(this_ref_environment(&built, &overlay, &sidecar), &order);
        assert_eq!(
            report.results.len(),
            2,
            "F08: two authorizations must not collapse into one memo entry"
        );
        assert_eq!(report.stats.memo_hits, 0);
        let statuses: Vec<(Option<&str>, ContextStatus)> = report
            .results
            .iter()
            .map(|(key, result)| (key.authorization_evidence.as_deref(), result.status))
            .collect();
        assert!(statuses.contains(&(Some("type"), ContextStatus::Resolved)));
        assert!(statuses.contains(&(Some(""), ContextStatus::Partial)));

        let replay = worklist.run(this_ref_environment(&built, &overlay, &sidecar), &order);
        assert_eq!(replay.results, report.results);
        assert_eq!(replay.stats.memo_hits, 2);
    }
}

// ---------------------------------------------------------------------------
// S02 scenario map owned by this file. The S02 rows name the RC28-F09 and
// RC28-F10 runtime scenarios that S07 executes; their literal ids are carried
// in every assertion message so the runtime battery can map scenario -> test.
// ---------------------------------------------------------------------------

/// `F09-independent-sentences`: unrelated mixed-act sentences must not be
/// merged, and each keeps its own local origin.
#[test]
fn m206_s02_f09_independent_sentences_are_not_merged() {
    let first = "федерального закона от 01.01.2020 N 1-ФЗ";
    let second = "федерального закона от 02.02.2021 N 2-ФЗ";
    let source = format!("{first}. {second}.");
    let frames = extract_act_list_frames(&source, &capture_lawrefs(&source));
    assert_eq!(
        frames.len(),
        2,
        "F09-independent-sentences: independent sentences must not be merged"
    );
    assert!(
        frames[0].local_anchor.end() < frames[1].local_anchor.start(),
        "F09-independent-sentences: each frame keeps its own local origin"
    );
    for frame in &frames {
        assert!(
            source.is_char_boundary(frame.local_anchor.start())
                && source.is_char_boundary(frame.local_anchor.end()),
            "F09-independent-sentences: origins stay on UTF-8 character boundaries"
        );
    }
}

/// `F09-incomplete-tail`: a tail without the required requisites stays
/// observable and is never rewritten as a complete member.
#[test]
fn m206_s02_f09_incomplete_tail_stays_observable() {
    let source = "федерального закона от 03.03.2022";
    let frames = extract_act_list_frames(source, &capture_lawrefs(source));
    assert_eq!(
        frames.len(),
        1,
        "F09-incomplete-tail: the tail remains observable"
    );
    assert_eq!(
        frames[0].status,
        FrameStatus::Ambiguous,
        "F09-incomplete-tail: an incomplete tail is ambiguous, never complete"
    );
    assert!(
        frames[0].local_anchor.start() < frames[0].local_anchor.end(),
        "F09-incomplete-tail: the ambiguous tail keeps a source-local origin"
    );
    assert!(
        frames[0]
            .members
            .iter()
            .all(|member| member.doc_no.is_none()),
        "F09-incomplete-tail: the missing requisite is never fabricated"
    );
}

/// `F09-boundaries`: sentence, heading and paragraph boundaries stay
/// distinguishable and are not silently merged.
#[test]
fn m206_s02_f09_sentence_and_heading_boundaries_stay_distinct() {
    let source = "Федеральный закон от 01.01.2020 N 1-ФЗ. Статья 2. Иной текст.";
    let sentences = split_legal_sentences(source);
    assert!(
        sentences.len() >= 2,
        "F09-boundaries: sentence boundaries must be found, got {sentences:?}"
    );
    for sentence in &sentences {
        assert!(
            source.is_char_boundary(sentence.start()) && source.is_char_boundary(sentence.end()),
            "F09-boundaries: sentence spans stay on UTF-8 character boundaries"
        );
    }
    let heading = block("Статья 2. Второй", ParagraphStyle::Heading, 1);
    let body = block("Второй текст", ParagraphStyle::BodyText, 2);
    assert_ne!(
        heading.style(),
        body.style(),
        "F09-boundaries: heading and paragraph stay distinguishable"
    );
    let built = index(&[block("Закон", ParagraphStyle::Title, 0), heading, body]).unwrap();
    assert_eq!(
        built
            .ancestor_path(&BlockId::parse("block-2").unwrap())
            .unwrap()[0]
            .role(),
        ContainerRole::Article,
        "F09-boundaries: the paragraph keeps its own container instead of merging upward"
    );
}

/// `F09-refused-token-only`: evidence that is not an admitted, complete capture
/// never completes a frame member. A separator-only input mints nothing, and an
/// unproven tail stays ambiguous with its missing requisite absent instead of
/// being filled in from token evidence alone.
#[test]
fn m206_s02_f09_refused_token_only_evidence_never_completes_a_member() {
    assert!(
        extract_act_list_frames("  , ,  ", &capture_lawrefs("")).is_empty(),
        "F09-refused-token-only: separator-only token evidence never mints a frame"
    );
    let source = "законов от 01.01.2020";
    let frames = extract_act_list_frames(source, &capture_lawrefs(source));
    assert_eq!(
        frames.len(),
        1,
        "F09-refused-token-only: the unproven tail stays observable"
    );
    assert_eq!(
        frames[0].status,
        FrameStatus::Ambiguous,
        "F09-refused-token-only: token evidence alone never completes the frame"
    );
    assert!(
        frames[0]
            .members
            .iter()
            .all(|member| member.date.is_some() && member.doc_no.is_none()),
        "F09-refused-token-only: only the source-proven slot is filled; the rest stays absent"
    );
}

/// `F09-identical-origins`: identical same-span evidence merges only when
/// every closed slot agrees; otherwise both origins are retained in a conflict
/// set and no winner is invented.
#[test]
fn m206_s02_f09_identical_origins_keep_slot_fingerprint() {
    let merged = arbitrate_pair((10, 15), (10, 15), true);
    assert_eq!(
        merged,
        PairOutcome::MergeEvidence(PairDiagnostic::DuplicateMatcherEvidenceMerged),
        "F09-identical-origins: equal slots merge the duplicate matcher evidence"
    );
    assert_eq!(
        merged,
        arbitrate_pair((10, 15), (10, 15), true),
        "F09-identical-origins: the merge is deterministic"
    );
    let conflict = arbitrate_pair((10, 15), (10, 15), false);
    assert_eq!(
        conflict,
        PairOutcome::ConflictSet(PairDiagnostic::ExactSpanSlotConflict),
        "F09-identical-origins: a same-span slot conflict retains both origins"
    );
}

/// `F09-overlap`: partial overlap is a conflict set; containment without a
/// selected pair policy stays ambiguous; no order-based resolution exists.
#[test]
fn m206_s02_f09_overlap_is_a_conflict_set_not_order_resolution() {
    assert_eq!(
        span_relation((0, 10), (5, 15)),
        SpanRelation::PartialOverlap,
        "F09-overlap: partial intersection is classified before arbitration"
    );
    for slots_equal in [true, false] {
        assert_eq!(
            arbitrate_pair((0, 10), (5, 15), slots_equal),
            PairOutcome::ConflictSet(PairDiagnostic::PartialOverlapConflict),
            "F09-overlap: overlap is a conflict set for every slot fingerprint"
        );
    }
    assert_eq!(
        arbitrate_pair((0, 20), (5, 10), true),
        PairOutcome::RetainBoth(Some(PairDiagnostic::ContainmentWithoutPairPolicy)),
        "F09-overlap: containment without a selected policy stays ambiguous_both"
    );
}

/// `F09-order`: producer order is not precedence. Every arbitration outcome is
/// invariant under argument order, and no origin is discarded.
#[test]
fn m206_s02_f09_producer_order_is_not_precedence() {
    for (a, b) in [
        ((0usize, 10usize), (5usize, 15usize)),
        ((0, 20), (5, 10)),
        ((0, 10), (20, 30)),
        ((10, 15), (10, 15)),
    ] {
        for slots_equal in [true, false] {
            assert_eq!(
                arbitrate_pair(a, b, slots_equal),
                arbitrate_pair(b, a, slots_equal),
                "F09-order: arbitration must not depend on producer order ({a:?} vs {b:?})"
            );
            assert_eq!(
                span_relation(a, b),
                span_relation(b, a),
                "F09-order: the span relation is order-independent"
            );
        }
    }
    assert_eq!(
        arbitrate_pair((0, 10), (20, 30), true),
        PairOutcome::RetainBoth(None),
        "F09-order: disjoint evidence retains both origins"
    );
}

/// `F10-original-spans`: original UTF-8 anchors and dash variants are retained,
/// and morphology that cannot be obtained stays an explicit absence instead of
/// a guessed match.
#[test]
fn m206_s02_f10_original_spans_and_unavailable_morphology_stay_explicit() {
    for dash in ["-", "–", "—"] {
        let source = format!("статьями 7.29 {dash} 7.32");
        let captures = capture_lawrefs(&source);
        let capture = captures
            .captures()
            .iter()
            .find(|capture| capture.slots.range.is_some())
            .unwrap_or_else(|| panic!("F10-original-spans: {dash} range must be captured"));
        assert!(
            capture.user_text(&source).contains(dash),
            "F10-original-spans: the captured range keeps the written {dash} variant"
        );
        assert_eq!(
            capture.user_text(&source),
            &source[capture.span.start()..capture.span.end()],
            "F10-original-spans: the capture span indexes the original source text"
        );
        assert!(
            source.is_char_boundary(capture.span.start())
                && source.is_char_boundary(capture.span.end()),
            "F10-original-spans: the anchor covers whole UTF-8 characters"
        );
        assert!(
            source[dash_range(&source, dash)] == *dash,
            "F10-original-spans: the source dash byte range still holds the written dash"
        );
    }

    // Morphology is a closed lexical surface: a form outside the lexicon is an
    // explicit absence, never an invented marker.
    let marked = find_legal_markers("статьями 7.29 – 7.32");
    assert!(
        !marked.is_empty(),
        "F10-original-spans: the closed lexicon still marks the admitted surface"
    );
    let source = "статьями 7.29 – 7.32";
    for marker in &marked {
        let span = marker.text_span();
        assert!(
            source.is_char_boundary(span.start()) && source.is_char_boundary(span.end()),
            "F10-original-spans: morphology markers stay on UTF-8 character boundaries"
        );
        assert!(
            span.end() <= source.len(),
            "F10-original-spans: morphology markers stay source-local"
        );
    }
    assert!(
        find_legal_markers("zzzqqq").is_empty(),
        "F10-original-spans: unavailable morphology is an explicit absence"
    );
}

/// The byte range of the written dash in `source`.
fn dash_range(source: &str, dash: &str) -> std::ops::Range<usize> {
    let start = source.find(dash).expect("fixture dash");
    start..start + dash.len()
}
