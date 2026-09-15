//! D384 structural designation contract tests.
//! Fixtures are synthetic, span-exact strings; no vendor corpus or parser is used.

use ln_decode::lawref::capture_lawrefs;
use ln_decode::lexer::lex;
use ln_decode::local_grammar::{
    extract_act_list_frames, extract_structural_frames, DerivationSource, FrameDiagnostic,
    FrameKind, FrameStatus, OwnerPathState, PROPOSED_MAX_FRAME_MEMBERS,
};
use ln_decode::morphology::find_legal_markers;

fn extract(src: &str) -> Vec<ln_decode::local_grammar::StructuralDesignationFrame> {
    let tokens = lex(src);
    let markers = find_legal_markers(src);
    extract_structural_frames(&tokens, src, &markers)
}

fn extract_act(src: &str) -> Vec<ln_decode::local_grammar::CoordinatingFrame> {
    let batch = capture_lawrefs(src);
    extract_act_list_frames(src, &batch)
}

#[test]
fn act_list_has_three_explicit_date_number_members() {
    let frames = extract_act(
        "федеральных законов от 01.01.2020 N 1-ФЗ, от 02.02.2021 N 2-ФЗ и от 03.03.2022 N 3-ФЗ",
    );
    assert_eq!(frames.len(), 1);
    let frame = &frames[0];
    assert_eq!(frame.frame_kind, FrameKind::ActRequisites);
    assert_eq!(frame.status, FrameStatus::Proposed);
    assert_eq!(frame.members.len(), 3);
    assert_eq!(frame.members[0].date.as_deref(), Some("01.01.2020"));
    assert_eq!(frame.members[0].doc_no.as_deref(), Some("1-ФЗ"));
    assert!(frame
        .members
        .iter()
        .all(|member| member.value_span.start() < member.value_span.end()));
}

#[test]
fn act_list_does_not_inherit_head_across_sentences() {
    let frames = extract_act("федеральных законов от 01.01.2020 N 1-ФЗ. от 02.02.2021 N 2-ФЗ");
    assert_eq!(frames.len(), 2);
    assert!(frames.iter().all(|frame| {
        frame.members.len() == 1 && frame.members[0].derivation == DerivationSource::ExplicitMember
    }));
}

#[test]
fn act_list_incomplete_tail_is_observable_and_not_minted_complete() {
    let frames = extract_act("федеральных законов от 01.01.2020");
    assert_eq!(frames.len(), 1);
    assert_eq!(frames[0].status, FrameStatus::Ambiguous);
    assert_eq!(frames[0].members.len(), 1);
    assert_eq!(
        frames[0].members[0].state,
        ln_decode::local_grammar::EnumerationState::Incomplete
    );
    assert!(frames[0].members[0].doc_no.is_none());
}

#[test]
fn act_list_without_type_retains_members_as_unresolved() {
    let frames = extract_act("от 01.01.2020 N 1-ФЗ, от 02.02.2021 N 2-ФЗ");
    assert_eq!(frames.len(), 1);
    assert_eq!(frames[0].status, FrameStatus::Ambiguous);
    assert_eq!(frames[0].diagnostic, Some(FrameDiagnostic::TypeUnresolved));
    assert!(frames[0].head_roles.is_empty());
}

#[test]
fn act_list_bound_refuses_without_truncation() {
    let members = (0..PROPOSED_MAX_FRAME_MEMBERS + 1)
        .map(|index| format!("от 01.01.2020 N {index}-ФЗ"))
        .collect::<Vec<_>>();
    let frames = extract_act(&format!("законов {}", members.join(", ")));
    assert_eq!(frames.len(), 1);
    assert_eq!(frames[0].status, FrameStatus::Rejected);
    assert_eq!(
        frames[0].diagnostic,
        Some(FrameDiagnostic::FrameMemberLimitReached)
    );
    assert_eq!(frames[0].members.len(), PROPOSED_MAX_FRAME_MEMBERS + 1);
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
