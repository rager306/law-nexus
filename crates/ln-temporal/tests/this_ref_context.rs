use ln_temporal::document_context::*;
use std::collections::BTreeMap;

fn context() -> (DocumentStructureIndex, AnalysisOverlay) {
    let version = DocumentVersion::new("this-ref-v1").unwrap();
    let blocks = vec![
        SourceBlock::new(BlockId::new(0), 0, "head"),
        SourceBlock::new(BlockId::new(1), 1, "tail"),
    ];
    let containers = vec![Container::new(0, ContainerRole::Document, None)];
    let membership = BTreeMap::from([(BlockId::new(0), 0), (BlockId::new(1), 0)]);
    let index = DocumentStructureIndex::build(version, blocks, containers, membership).unwrap();
    let overlay = AnalysisOverlay::new(
        vec![Frame::new(FrameId::new(0), BlockId::new(0), true, false)],
        BTreeMap::new(),
        BTreeMap::new(),
    )
    .unwrap();
    (index, overlay)
}

#[test]
fn this_ref_grammar_is_exact_and_preserves_local_spans() {
    let text = "согласно настоящего Закона и настоящей статьи";
    let evidence = detect_this_ref(text);
    assert_eq!(evidence.len(), 2);
    assert_eq!(evidence[0].surface(), "настоящего Закона");
    assert_eq!(
        &text[evidence[0].span().start()..evidence[0].span().end()],
        evidence[0].surface()
    );
    assert_eq!(evidence[1].surface(), "настоящей статьи");
}

#[test]
fn foreign_surface_does_not_authorize_reference() {
    assert!(detect_this_ref("настоящим документом не является").is_empty());
}

/// RC28-F08 alignment: empty evidence is a refusal, never a silent resolve.
#[test]
fn f8_empty_evidence_refuses_current_document_requisites() {
    let (index, overlay) = context();
    let empty = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(1));
    assert_eq!(
        resolve(&empty, &index, &overlay, true, 4).terminal,
        Terminal::Partial,
        "F08-self-missing-conflict: no admitted grammar proof must not authorize"
    );
}

/// RC28-F08 alignment: an ordinary citation is not self-reference even when
/// the sidecar is available, because the detector admits nothing.
#[test]
fn f8_cited_act_negative_stays_a_refusal() {
    let (index, overlay) = context();
    let cited = detect_this_ref("согласно статье 5 настоящего Кодекса");
    assert!(cited.is_empty(), "F08-cited-act-negative detector input");
    let request = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(1))
        .with_evidence(cited);
    assert_eq!(
        resolve(&request, &index, &overlay, true, 4).terminal,
        Terminal::Partial
    );
}

/// RC28-F08 alignment: non-empty evidence resolves, and request identity keeps
/// the two authorization states apart.
#[test]
fn f8_admitted_evidence_resolves_and_is_part_of_request_identity() {
    let (index, overlay) = context();
    // The temporal detector keeps its own closed, case-sensitive surface
    // contract; this test only pins the authorization semantics.
    let evidence = detect_this_ref("согласно настоящего Закона");
    assert_eq!(evidence.len(), 1, "F08-self-positive detector input");
    let admitted = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(1))
        .with_evidence(evidence);
    assert_eq!(
        resolve(&admitted, &index, &overlay, true, 4).terminal,
        Terminal::Resolved
    );
    let empty = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(1));
    assert_ne!(
        admitted, empty,
        "authorization evidence is request identity"
    );
    let run = run_worklist(vec![admitted, empty], &index, &overlay, true, 8);
    assert_eq!(run.results.len(), 2, "two authorizations must not collapse");
    assert_eq!(run.stats.memo_hits, 0);
}
