//! D384 structural designation contract tests.
//! Fixtures are synthetic, span-exact strings; no vendor corpus or parser is used.

use ln_decode::lexer::lex;
use ln_decode::local_grammar::{
    extract_structural_frames, DerivationSource, FrameDiagnostic, FrameStatus, OwnerPathState,
};
use ln_decode::morphology::find_legal_markers;

fn extract(src: &str) -> Vec<ln_decode::local_grammar::StructuralDesignationFrame> {
    let tokens = lex(src);
    let markers = find_legal_markers(src);
    extract_structural_frames(&tokens, src, &markers)
}

#[test]
fn dotted_range_keeps_endpoint_pair_and_head_evidence() {
    let src = "статьями 7.29 - 7.32";
    let frames = extract(src);
    assert_eq!(frames.len(), 1);
    let frame = &frames[0];
    assert_eq!(
        frame
            .values
            .iter()
            .map(|m| m.value.as_str())
            .collect::<Vec<_>>(),
        ["7.29", "7.32"]
    );
    assert_eq!(frame.values[0].derivation, DerivationSource::ExplicitMember);
    assert_eq!(frame.values[1].derivation, DerivationSource::SameSeriesHead);
    assert_eq!(
        frame.values[1].evidence,
        vec![find_legal_markers(src)[0].text_span()]
    );
    assert_eq!(frame.status, FrameStatus::Ambiguous);
    assert_eq!(frame.diagnostic, Some(FrameDiagnostic::OwnerUnresolved));
}

#[test]
fn owner_after_range_is_proved_by_marker_and_value_spans() {
    let src = "частями 2.1 - 2.3 статьи 19";
    let frame = &extract(src)[0];
    assert_eq!(frame.values[0].value, "2.1");
    assert_eq!(frame.values[1].value, "2.3");
    assert_eq!(frame.owner_path.len(), 1);
    assert_eq!(frame.owner_path[0].value, "19");
    assert_eq!(frame.owner_path[0].state, OwnerPathState::Resolved);
    assert_eq!(frame.owner_path[0].evidence.len(), 2);
    assert_eq!(frame.diagnostic, None);
}

#[test]
fn owner_before_designation_is_supported() {
    let src = "статьи 19 части 2";
    let frames = extract(src);
    assert_eq!(frames.len(), 2);
    let part = frames
        .iter()
        .find(|frame| frame.marker == ln_decode::morphology::LegalMarkerKind::Chast)
        .unwrap();
    assert_eq!(part.owner_path[0].value, "19");
    assert_eq!(part.owner_path[0].evidence.len(), 2);
}

#[test]
fn comma_and_i_members_are_explicit_without_invented_inheritance() {
    let src = "пунктами 4.1, 4.2 и 4.4";
    let frame = &extract(src)[0];
    assert_eq!(frame.values.len(), 3);
    assert!(frame
        .values
        .iter()
        .all(|member| member.derivation == DerivationSource::ExplicitMember));
    assert!(frame.values.iter().all(|member| member.evidence.len() == 1));
}

#[test]
fn dash_variants_share_endpoint_pair_policy() {
    for dash in ["-", "–", "—"] {
        let src = format!("пунктами 4.1 {dash} 4.4 статьи 19");
        let frames = extract(&src);
        assert_eq!(frames.len(), 1, "{src}");
        assert_eq!(frames[0].values.len(), 2, "{src}");
    }
}
