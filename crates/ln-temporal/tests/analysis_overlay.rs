use ln_temporal::document_context::*;
use std::collections::BTreeMap;

#[test]
fn overlay_is_immutable_and_keeps_multiple_heads() {
    let frames = vec![
        Frame::new(FrameId::new(1), BlockId::new(0), true, false),
        Frame::new(FrameId::new(2), BlockId::new(1), false, true),
        Frame::new(FrameId::new(3), BlockId::new(2), false, true),
    ];
    let heads = BTreeMap::from([(FrameId::new(2), vec![FrameId::new(1), FrameId::new(3)])]);
    let overlay = AnalysisOverlay::new(frames.clone(), BTreeMap::new(), heads).unwrap();
    assert_eq!(overlay.frames(), frames.as_slice());
    assert_eq!(overlay.continuation_heads(FrameId::new(2)).len(), 2);
    assert_eq!(overlay.aliases().len(), 0);
}
