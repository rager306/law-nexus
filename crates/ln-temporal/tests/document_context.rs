use ln_temporal::document_context::*;
use std::collections::BTreeMap;

fn fixture() -> (DocumentStructureIndex, AnalysisOverlay) {
    let version = DocumentVersion::new("doc-v1").unwrap();
    let blocks = vec![
        SourceBlock::new(BlockId::new(0), 0, "head"),
        SourceBlock::new(BlockId::new(1), 1, "body"),
    ];
    let containers = vec![
        Container::new(0, ContainerRole::Document, None),
        Container::new(1, ContainerRole::Article, Some(0)),
    ];
    let membership = BTreeMap::from([(BlockId::new(0), 1), (BlockId::new(1), 1)]);
    let index = DocumentStructureIndex::build(version, blocks, containers, membership).unwrap();
    let frames = vec![
        Frame::new(FrameId::new(0), BlockId::new(0), true, false),
        Frame::new(FrameId::new(1), BlockId::new(1), false, true),
    ];
    let heads = BTreeMap::from([(FrameId::new(1), vec![FrameId::new(0)])]);
    let overlay = AnalysisOverlay::new(frames, BTreeMap::new(), heads).unwrap();
    (index, overlay)
}

#[test]
fn deterministic_index_and_resolution() {
    let (index, overlay) = fixture();
    assert_eq!(index.ancestor_path(BlockId::new(1)).unwrap(), vec![1, 0]);
    let request = ContextRequest::new(RequestKind::OpenSeriesHead, FrameId::new(1));
    let first = resolve(
        &request,
        &index,
        &overlay,
        true,
        PROPOSED_MAX_WORKLIST_STEPS,
    );
    let second = resolve(
        &request,
        &index,
        &overlay,
        true,
        PROPOSED_MAX_WORKLIST_STEPS,
    );
    assert_eq!(first, second);
    assert_eq!(first.terminal, Terminal::Resolved);
    assert_eq!(first.candidates, vec![FrameId::new(0)]);
}

#[test]
fn immutable_overlay_preserves_inputs_and_cross_block_provenance() {
    let (index, overlay) = fixture();
    let before_index = index.clone();
    let before_overlay = overlay.clone();
    let result = resolve(
        &ContextRequest::new(RequestKind::OpenSeriesHead, FrameId::new(1)),
        &index,
        &overlay,
        true,
        4,
    );
    assert_eq!(result.provenance[0], "document:doc-v1");
    assert_eq!(index, before_index);
    assert_eq!(overlay, before_overlay);
    assert!(overlay.continuation_heads(FrameId::new(1)).len() == 1);
}

#[test]
fn requisites_inheritance_and_unavailable_are_typed() {
    let (index, overlay) = fixture();
    let request = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(1));
    assert_eq!(
        resolve(&request, &index, &overlay, true, 1).terminal,
        Terminal::Resolved
    );
    assert_eq!(
        resolve(&request, &index, &overlay, false, 1).terminal,
        Terminal::Unavailable
    );
}

#[test]
fn cycle_and_budget_are_fail_closed() {
    let (index, overlay) = fixture();
    let mut cycle = ContextRequest::new(RequestKind::OpenSeriesHead, FrameId::new(1));
    cycle.path.push(FrameId::new(1));
    assert_eq!(
        resolve(&cycle, &index, &overlay, true, 1).terminal,
        Terminal::Cycle
    );
    assert_eq!(
        resolve(
            &ContextRequest::new(RequestKind::OpenSeriesHead, FrameId::new(1)),
            &index,
            &overlay,
            true,
            0
        )
        .terminal,
        Terminal::Limit
    );
    let run = run_worklist(
        vec![ContextRequest::new(RequestKind::OpenSeriesHead, FrameId::new(1)); 3],
        &index,
        &overlay,
        true,
        1,
    );
    assert_eq!(run.stats.steps, 1);
    assert_eq!(
        run.results
            .values()
            .filter(|r| r.terminal == Terminal::Limit)
            .count(),
        1
    );
    assert!(run.stats.memo_hits >= 2);
}
