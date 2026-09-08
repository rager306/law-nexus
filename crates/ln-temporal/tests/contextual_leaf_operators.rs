use ln_temporal::document_context::*;
use std::collections::BTreeMap;

fn context() -> (DocumentStructureIndex, AnalysisOverlay) {
    let version = DocumentVersion::new("leaf-v1").unwrap();
    let blocks = vec![
        SourceBlock::new(BlockId::new(0), 0, "head"),
        SourceBlock::new(BlockId::new(1), 1, "tail"),
    ];
    let containers = vec![Container::new(0, ContainerRole::Document, None)];
    let membership = BTreeMap::from([(BlockId::new(0), 0), (BlockId::new(1), 0)]);
    let index = DocumentStructureIndex::build(version, blocks, containers, membership).unwrap();
    let overlay = AnalysisOverlay::new(
        vec![Frame::new(FrameId::new(0), BlockId::new(0), true, false)],
        BTreeMap::from([("X".to_owned(), FrameId::new(0))]),
        BTreeMap::new(),
    )
    .unwrap();
    (index, overlay)
}

#[test]
fn explicit_anchor_requires_an_explicit_key() {
    let (index, overlay) = context();
    let missing = ContextRequest::new(RequestKind::ExplicitAnchorLookup, FrameId::new(0));
    assert_eq!(
        resolve(&missing, &index, &overlay, true, 2).terminal,
        Terminal::Unavailable
    );
    let keyed = ContextRequest::new(RequestKind::ExplicitAnchorLookup, FrameId::new(0)).key("X");
    assert_eq!(
        resolve(&keyed, &index, &overlay, true, 2).terminal,
        Terminal::Resolved
    );
}

#[test]
fn scoped_alias_and_missing_requisites_fail_closed() {
    let (index, overlay) = context();
    let alias = ContextRequest::new(RequestKind::ScopedAlias, FrameId::new(0)).key("X");
    assert_eq!(
        resolve(&alias, &index, &overlay, true, 2).terminal,
        Terminal::Resolved
    );
    let requisites = ContextRequest::new(RequestKind::CurrentDocumentRequisites, FrameId::new(0));
    assert_eq!(
        resolve(&requisites, &index, &overlay, false, 2).terminal,
        Terminal::Unavailable
    );
}
