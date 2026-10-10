//! M211 S02 T04: local act-requisite grammar on the canonical typed stream.
//!
//! These tests exercise `extract_act_list_frames_from_typed`, which groups
//! `npa_typed::scan_typed_diagnosed` members by `LocalSpan.block`. The frame
//! is strictly intra-block: a TYPE written in block 0 is never inherited by an
//! anchor in block 1 (S03/RC28-F07), competing TYPE hypotheses survive as
//! explicit `alternatives` (RC28-F09/MEM1394), and every frame span stays in
//! the block it came from.

use ln_decode::local_grammar::{
    DerivationSource, FrameDiagnostic, FrameKind, FrameStatus, extract_act_list_frames_from_typed,
};
use ln_decode::npa_anchor::{self, LocalSpan};
use ln_decode::npa_typed;

fn frames(paras: &[&str]) -> Vec<ln_decode::local_grammar::CoordinatingFrame> {
    let owned: Vec<String> = paras.iter().map(|p| p.to_string()).collect();
    extract_act_list_frames_from_typed(&owned)
}

/// Demo criterion: a Federal-law list becomes one intra-block frame with three
/// independent members, each carrying its own date and number.
#[test]
fn demo_federal_law_list_yields_three_independent_members() {
    let frames = frames(&[
        "федеральных законов от 01.01.2020 N 1-ФЗ, от 02.02.2021 N 2-ФЗ и от 03.03.2022 N 3-ФЗ",
    ]);
    assert_eq!(frames.len(), 1, "one block => one frame");
    let frame = &frames[0];
    assert_eq!(frame.frame_kind, FrameKind::ActRequisites);
    assert_eq!(frame.members.len(), 3);
    assert_eq!(frame.status, FrameStatus::Proposed);
    assert!(frame.alternatives.is_empty());

    let dates: Vec<&str> = frame
        .members
        .iter()
        .filter_map(|m| m.date.as_deref())
        .collect();
    assert_eq!(dates, ["01.01.2020", "02.02.2021", "03.03.2022"]);
    let numbers: Vec<&str> = frame
        .members
        .iter()
        .filter_map(|m| m.doc_no.as_deref())
        .collect();
    assert_eq!(numbers, ["1-ФЗ", "2-ФЗ", "3-ФЗ"]);

    assert_eq!(frame.head_roles, vec!["Федеральный закон".to_string()]);
    assert_eq!(
        frame.members[0].derivation,
        DerivationSource::ExplicitMember
    );
    assert_eq!(
        frame.members[1].derivation,
        DerivationSource::SameSeriesHead,
        "an inherited (intra-block) series head is recorded, not silenced"
    );
    assert_eq!(
        frame.members[2].derivation,
        DerivationSource::SameSeriesHead
    );
    assert!(
        frame
            .members
            .iter()
            .all(|m| m.value_span.start() < m.value_span.end())
    );
}

/// The frame no longer silently picks one reading: a competing TYPE hypothesis
/// is retained as a `FrameMember` in `alternatives` and folded into `head_roles`.
#[test]
fn competing_type_hypotheses_fill_frame_alternatives() {
    let frames = frames(&["дополнительное соглашение к контракту от 23.03.2023 N 2"]);
    assert_eq!(frames.len(), 1);
    let frame = &frames[0];

    assert_eq!(frame.members.len(), 1);
    assert!(
        !frame.alternatives.is_empty(),
        "the losing reading must survive as an explicit alternative"
    );
    assert!(
        frame.alternatives.iter().any(|m| m.value == "соглашение"),
        "expected `соглашение` among alternatives: {:?}",
        frame
            .alternatives
            .iter()
            .map(|m| m.value.as_str())
            .collect::<Vec<_>>()
    );
    assert!(frame.head_roles.iter().any(|r| r == "контракт"));
    assert!(frame.head_roles.iter().any(|r| r == "соглашение"));
    assert_eq!(frame.status, FrameStatus::Ambiguous);
    assert_eq!(
        frame.diagnostic,
        Some(FrameDiagnostic::ConflictingFramesRetained)
    );
}

/// A TYPE written in block 0 is not inherited by an anchor in block 1: the
/// second block yields its own frame with empty `head_roles` and
/// `TypeUnresolved` (the S03 boundary stays intact).
#[test]
fn cross_block_type_is_not_inherited() {
    let frames = frames(&[
        "федеральных законов от 01.01.2020 N 1-ФЗ",
        "от 02.02.2021 N 2-ФЗ",
    ]);
    assert_eq!(frames.len(), 2, "one frame per block");

    assert_eq!(frames[0].head_roles, vec!["Федеральный закон".to_string()]);
    assert_eq!(frames[0].status, FrameStatus::Proposed);

    let second = &frames[1];
    assert!(
        second.head_roles.is_empty(),
        "block 1 has no local TYPE head: {:?}",
        second.head_roles
    );
    assert_eq!(second.diagnostic, Some(FrameDiagnostic::TypeUnresolved));
    assert_eq!(second.status, FrameStatus::Ambiguous);
    assert_eq!(second.members.len(), 1);
    assert_eq!(second.members[0].doc_no.as_deref(), Some("2-ФЗ"));
    assert_eq!(
        second.members[0].derivation,
        DerivationSource::ExplicitMember,
        "no cross-block series head is authorized"
    );
}

/// Every frame is intra-block: its anchor and all member/alternative spans are
/// bounded by the block text they came from, and `value_span` is the typed
/// anchor itself.
#[test]
fn frame_spans_stay_within_their_block() {
    let paras = [
        "федеральных законов от 01.01.2020 N 1-ФЗ",
        "от 02.02.2021 N 2-ФЗ",
    ];
    let frames = frames(&paras);
    assert_eq!(frames.len(), 2);

    let typed = npa_typed::scan_typed(&paras.iter().map(|p| p.to_string()).collect::<Vec<_>>());
    assert_eq!(typed.len(), 2);

    for (index, frame) in frames.iter().enumerate() {
        let block_len = paras[index].len();
        assert!(
            frame.local_anchor.start() < frame.local_anchor.end()
                && frame.local_anchor.end() <= block_len,
            "frame {index} local_anchor leaves its block"
        );
        for member in &frame.members {
            assert!(
                member.value_span.end() <= block_len,
                "member span leaves block {index}"
            );
            npa_anchor::check_span(
                paras[index],
                LocalSpan {
                    block: index,
                    start: member.value_span.start(),
                    end: member.value_span.end(),
                },
            )
            .expect("frame member span must be a valid local UTF-8 bound");
        }
        // The member's value_span is the typed anchor, not a re-derived span.
        assert_eq!(frame.members[0].value_span.start(), typed[index].span.start);
        assert_eq!(frame.members[0].value_span.end(), typed[index].span.end);
    }
}

/// The competing hypotheses carry valid local spans too, so a consumer can
/// re-read every reading without leaving the block.
#[test]
fn alternative_spans_are_valid_local_utf8_bounds() {
    let para = "дополнительное соглашение к контракту от 23.03.2023 N 2";
    let frames = frames(&[para]);
    let frame = &frames[0];

    for alt in &frame.alternatives {
        npa_anchor::check_span(
            para,
            LocalSpan {
                block: 0,
                start: alt.value_span.start(),
                end: alt.value_span.end(),
            },
        )
        .expect("alternative span must be a valid local UTF-8 bound");
    }
}

/// Empty and blank inputs stay empty and panic-free.
#[test]
fn empty_and_blank_inputs_are_empty() {
    assert!(extract_act_list_frames_from_typed(&[]).is_empty());
    assert!(extract_act_list_frames_from_typed(&[String::new()]).is_empty());
    assert!(extract_act_list_frames_from_typed(&["   ".to_string()]).is_empty());
}

/// D602: the local-grammar module stays serde/fs/env-free.
#[test]
fn local_grammar_source_is_serde_free() {
    let src = std::fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/local_grammar.rs"),
    )
    .expect("local_grammar.rs must be readable");
    for forbidden in [
        "serde",
        "Deserialize",
        "Serialize",
        "serde_json",
        "std::fs",
        "std::env",
    ] {
        assert!(
            !src.contains(forbidden),
            "local_grammar.rs must stay serde/fs/env-free (D602): found {forbidden}"
        );
    }
}
