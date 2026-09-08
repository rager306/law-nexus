//! Clean-room D384 hostile contract tests.
//! Synthetic inputs only; no vendor code/data (rutokenizer, Pullenti, razdel).
//! These tests make no C2/C3 accuracy claim and exercise only local spans/FSM.

use ln_decode::lexer::lex;
use ln_decode::local_grammar::{
    extract_structural_frames, DerivationSource, FrameDiagnostic, FrameStatus,
    PROPOSED_MAX_FRAME_MEMBERS,
};
use ln_decode::morphology::find_legal_markers;

fn extract(src: &str) -> Vec<ln_decode::local_grammar::StructuralDesignationFrame> {
    let tokens = lex(src);
    let markers = find_legal_markers(src);
    extract_structural_frames(&tokens, src, &markers)
}

#[test]
fn empty_and_whitespace_inputs_are_empty_and_panic_free() {
    assert!(extract("").is_empty());
    assert!(extract(" \n\t").is_empty());
}

#[test]
fn range_without_marker_is_not_a_structural_frame() {
    assert!(extract("7.29 – 7.32").is_empty());
}

#[test]
fn marker_without_values_is_not_a_frame() {
    assert!(extract("статьями").is_empty());
    assert!(extract("статьями -").is_empty());
}

#[test]
fn huge_member_list_is_rejected_without_silent_truncation() {
    let values = (0..PROPOSED_MAX_FRAME_MEMBERS + 1)
        .map(|index| format!("1.{index}"))
        .collect::<Vec<_>>();
    let src = format!("пунктами {}", values.join(", "));
    let frames = extract(&src);
    assert_eq!(frames.len(), 1);
    let frame = &frames[0];
    assert_eq!(frame.status, FrameStatus::Rejected);
    assert_eq!(
        frame.diagnostic,
        Some(FrameDiagnostic::FrameMemberLimitReached)
    );
    assert_eq!(frame.values.len(), PROPOSED_MAX_FRAME_MEMBERS + 1);
}

#[test]
fn covering_tokens_and_spans_are_not_mutated() {
    let src = "частями 2.1 — 2.3 статьи 19";
    let tokens = lex(src);
    let before = tokens.clone();
    let _ = extract_structural_frames(&tokens, src, &find_legal_markers(src));
    assert_eq!(tokens, before);
    assert_eq!(
        tokens
            .iter()
            .map(|token| token.lexeme(src))
            .collect::<String>(),
        src
    );
}

#[test]
fn nested_markers_retain_competing_frames_and_do_not_authorize_inheritance() {
    let src = "статьями 7.29 части 2";
    let frames = extract(src);
    assert!(frames.len() >= 2);
    assert!(frames
        .iter()
        .any(|frame| frame.diagnostic == Some(FrameDiagnostic::ConflictingFramesRetained)));
    assert!(frames.iter().flat_map(|frame| &frame.values).all(|member| {
        member.derivation != DerivationSource::AuthorizedCurrentDocumentRequisites
    }));
}

#[test]
fn malformed_tail_does_not_create_a_partial_frame() {
    assert!(extract("пунктами 4.1,").is_empty());
    assert!(extract("пунктами 4.1 и").is_empty());
}
