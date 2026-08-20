//! Two-factor document group detection contract (M171 S01 T02).
//!
//! Factor A (metadata): ranked kind/type/path needles, `classify_corpus_role`
//! ranking semantics (lower rank wins; same-rank different groups is
//! Conflict). Factor B (structural probe): unit-marker presence over decoded
//! blocks. Both factors must agree; conflicts, missing metadata, and absent
//! structure are Unknown (fail-closed, never guess).
//!
//! Hostile cases from Review 8:
//! - R8-05: FAS decisions carry numbered lists (90% of files, depth up to 4)
//!   that are NOT structure — the text-only profile (court_practice) must
//!   ignore them and never produce a structural group.
//! - R8-07: ~10% of laws lack statya markers — metadata saying law without a
//!   probe-confirmed statya must be Unknown, not guessed.
//!
//! Non-claim: detection is a `system_observation` heuristic, never legal
//! classification; determinism is mandatory.

use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::structural_profile::{
    DetectionFactor, GroupDetection, MetadataOutcome, ProbeVerdict, StructuralProfile,
    UnknownReason,
};

fn block(style: ParagraphStyle, text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:structural-profile").unwrap(),
            SourceSpan::try_new(10, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("block")
}

fn profile() -> StructuralProfile {
    StructuralProfile::embedded().expect("embedded kb-ontology.yaml")
}

/// Minimal fixture YAML exercising custom groups: statya-unit law, paren-style
/// punkt-unit order, and two same-rank groups for the Conflict contract.
const FIXTURE_YAML: &str = r#"schema_version: test/v1
fsm:
  current: O0
  states:
    O0:
      name: zero
  transitions:
    - {from: O0, to: O0, when: x}
vocabulary:
  hierarchy_levels:
    - statya
    - punkt
  node_kinds:
    - Work
  edge_kinds:
    - expression_of
  forbidden_node_kinds:
    - ApplicableDecision
  presence_change_kinds:
    - include
  membership_change_kinds:
    - attach
  industrial_op_kinds:
    - split
  force_status_values:
    - unknown
  decode_level_aliases:
    Statya: statya
    Punkt: punkt
  decode_marker_prefixes:
    Statya: [Статья, СТАТЬЯ, статья]
  decode_numbered_markers:
    Punkt: {number_style: digit, suffix: ")", allow_compound: true}
  decode_prefix_space_policy:
    default: required
  decode_number_styles:
    Statya: digit
    Punkt: digit
document_groups:
  non_claims:
    - fixture
  structural_roles:
    - container
    - unit
    - subunit
    - subunit-text
    - text-only
  structural_only_tokens:
    - primechanie
    - prilozhenie
  groups:
    - id: fixture_law
      granularity: statya
      text_boundary: [unit, container]
      needles:
        - {field: path, needle: fixture-law, rank: 10}
      ladder:
        - {token: statya, role: unit}
    - id: fixture_order
      granularity: punkt
      text_boundary: [unit, container]
      needles:
        - {field: path, needle: fixture-order, rank: 10}
      ladder:
        - {token: punkt, role: unit, suffix: ")", number_style: digit}
    - id: fixture_alpha
      needles:
        - {field: path, needle: shared-doc, rank: 10}
      ladder:
        - {token: statya, role: unit}
    - id: fixture_beta
      needles:
        - {field: path, needle: shared-doc, rank: 10}
      ladder:
        - {token: punkt, role: unit, suffix: ")", number_style: digit}
"#;

// ─── catalog shape and non-claims ──────────────────────────────────────────

#[test]
fn embedded_profile_exposes_five_groups_and_non_claims() {
    let profile = profile();
    let ids: Vec<&str> = profile
        .groups
        .iter()
        .map(|group| group.id.as_str())
        .collect();
    assert_eq!(
        ids,
        [
            "federal_law@v1",
            "code",
            "government_resolution",
            "departmental_order",
            "court_practice"
        ]
    );
    let joined = profile.non_claims.join("\n");
    assert!(
        joined.contains("system_observation"),
        "detection must be framed as a system_observation heuristic: {joined}"
    );
    assert!(
        joined.contains("not an AST"),
        "practice != AST must be declared (ADR-0020): {joined}"
    );
}

// ─── factor A: ranked metadata needles ─────────────────────────────────────

#[test]
fn metadata_path_needle_binds_law() {
    let profile = profile();
    match profile.detect_metadata(Some("federalnyi-zakon-44-fz"), None, None) {
        MetadataOutcome::Bound { group, needle } => {
            assert_eq!(group, "federal_law@v1");
            // Lower rank wins: federalnyi-zakon (10) beats law_ (20).
            assert_eq!(needle, "federalnyi-zakon");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
}

#[test]
fn metadata_kind_and_type_needles_bind() {
    let profile = profile();
    assert_eq!(
        profile.detect_metadata(None, Some("law"), None),
        MetadataOutcome::Bound {
            group: "federal_law@v1".to_owned(),
            needle: "law".to_owned(),
        }
    );
    assert_eq!(
        profile.detect_metadata(None, None, Some("order")),
        MetadataOutcome::Bound {
            group: "departmental_order".to_owned(),
            needle: "order".to_owned(),
        }
    );
    assert_eq!(
        profile.detect_metadata(None, Some("court"), None),
        MetadataOutcome::Bound {
            group: "court_practice".to_owned(),
            needle: "court".to_owned(),
        }
    );
}

#[test]
fn metadata_path_needles_bind_resolution_and_order() {
    let profile = profile();
    match profile.detect_metadata(Some("postanovlenie-pravitelstva-2024"), None, None) {
        MetadataOutcome::Bound { group, .. } => assert_eq!(group, "government_resolution"),
        other => panic!("expected Bound government_resolution, got {other:?}"),
    }
    match profile.detect_metadata(Some("prikaz-minzdrava-2024"), None, None) {
        MetadataOutcome::Bound { group, .. } => assert_eq!(group, "departmental_order"),
        other => panic!("expected Bound departmental_order, got {other:?}"),
    }
}

#[test]
fn metadata_no_match_is_unknown() {
    let profile = profile();
    assert_eq!(
        profile.detect_metadata(Some("mystery-file.docx"), None, None),
        MetadataOutcome::Unknown
    );
    assert_eq!(
        profile.detect_metadata(None, None, None),
        MetadataOutcome::Unknown
    );
}

#[test]
fn metadata_same_rank_different_groups_is_conflict() {
    let profile = StructuralProfile::parse_yaml(FIXTURE_YAML).expect("fixture");
    match profile.detect_metadata(Some("shared-doc-1"), None, None) {
        MetadataOutcome::Conflict { groups } => {
            assert_eq!(groups, ["fixture_alpha", "fixture_beta"]);
        }
        other => panic!("expected Conflict, got {other:?}"),
    }
}

#[test]
fn metadata_custom_fixture_binds_fixture_groups() {
    let profile = StructuralProfile::parse_yaml(FIXTURE_YAML).expect("fixture");
    match profile.detect_metadata(Some("fixture-law-1"), None, None) {
        MetadataOutcome::Bound { group, .. } => assert_eq!(group, "fixture_law"),
        other => panic!("expected Bound fixture_law, got {other:?}"),
    }
}

// ─── factor B: structural probe over blocks ────────────────────────────────

#[test]
fn probe_finds_statya_markers_for_law() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "Глава 1. Общие положения"),
        block(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        block(
            ParagraphStyle::BodyText,
            "Настоящий Федеральный закон регулирует отношения,",
        ),
        block(ParagraphStyle::Heading, "Статья 2. Определения"),
    ];
    match profile.probe("federal_law@v1", &blocks) {
        ProbeVerdict::StructureFound {
            unit_token,
            marker_count,
        } => {
            assert_eq!(unit_token, "statya");
            assert_eq!(marker_count, 2);
        }
        other => panic!("expected StructureFound, got {other:?}"),
    }
}

#[test]
fn probe_counts_compound_and_flat_punkt_for_order() {
    // departmental_order punkt is paren-style; compound lines like "1.1)"
    // are covered by the flat "1)" unit rule via the group's own suffix.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1) Организовать"),
        block(ParagraphStyle::Heading, "1.1) Назначить ответственного"),
        block(ParagraphStyle::BodyText, "Исполнителям в срок до 1 марта."),
    ];
    match profile.probe("departmental_order", &blocks) {
        ProbeVerdict::StructureFound {
            unit_token,
            marker_count,
        } => {
            assert_eq!(unit_token, "punkt");
            assert_eq!(marker_count, 2);
        }
        other => panic!("expected StructureFound, got {other:?}"),
    }
}

#[test]
fn probe_ignores_numbering_for_text_only() {
    // R8-05 hostile: FAS decision with depth-4 numbered lists. The text-only
    // profile declares no structure — the probe must be trivially NoStructure.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::BodyText, "1. Комиссия решила"),
        block(ParagraphStyle::BodyText, "1.1. Рекомендовать заказчику"),
        block(ParagraphStyle::BodyText, "1.1.1. Принять меры"),
        block(ParagraphStyle::BodyText, "1.1.1.1. Уведомить стороны"),
    ];
    assert_eq!(
        profile.probe("court_practice", &blocks),
        ProbeVerdict::NoStructure
    );
}

#[test]
fn probe_unknown_group_is_no_structure() {
    let profile = profile();
    let blocks = vec![block(ParagraphStyle::Heading, "Статья 1. Тест")];
    assert_eq!(
        profile.probe("does-not-exist", &blocks),
        ProbeVerdict::NoStructure
    );
}

#[test]
fn probe_skips_provider_comments() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::ProviderComment, "Статья 1. Комментарий"),
        block(ParagraphStyle::BodyText, "Обычный текст без маркеров."),
    ];
    assert_eq!(
        profile.probe("federal_law@v1", &blocks),
        ProbeVerdict::NoStructure
    );
}

#[test]
fn custom_fixture_probe_uses_group_suffix() {
    let profile = StructuralProfile::parse_yaml(FIXTURE_YAML).expect("fixture");
    // Paren-style punkt matches for the fixture order.
    let paren = vec![block(ParagraphStyle::Heading, "1) Пункт приказа")];
    assert!(matches!(
        profile.probe("fixture_order", &paren),
        ProbeVerdict::StructureFound { .. }
    ));
    // Dot-style does not match a paren-style punkt profile.
    let dot = vec![block(ParagraphStyle::Heading, "1. Пункт приказа")];
    assert_eq!(
        profile.probe("fixture_order", &dot),
        ProbeVerdict::NoStructure
    );
}

// ─── two-factor combination (the contract) ─────────────────────────────────

#[test]
fn law_with_statya_markers_binds_needle_and_probe() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        block(ParagraphStyle::BodyText, "Настоящий закон регулирует."),
    ];
    assert_eq!(
        profile.detect(Some("federalnyi-zakon-44-fz"), None, None, &blocks),
        GroupDetection::Bound {
            group: "federal_law@v1".to_owned(),
            factor: DetectionFactor::NeedleAndProbe,
        }
    );
}

#[test]
fn law_without_statya_is_probe_conflict_fail_closed() {
    // R8-07 hostile: ~10% of laws lack statya markers. Metadata says law but
    // the probe finds no statya — Unknown, never guess.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1. Основные положения"),
        block(ParagraphStyle::BodyText, "1.1. Ратифицировать соглашение."),
    ];
    assert_eq!(
        profile.detect(Some("federalnyi-zakon-123"), None, None, &blocks),
        GroupDetection::Unknown {
            reason: UnknownReason::ProbeConflict {
                metadata_group: "federal_law@v1".to_owned(),
            },
        }
    );
}

#[test]
fn law_with_empty_blocks_is_unknown() {
    let profile = profile();
    assert_eq!(
        profile.detect(Some("federalnyi-zakon-44-fz"), None, None, &[]),
        GroupDetection::Unknown {
            reason: UnknownReason::ProbeConflict {
                metadata_group: "federal_law@v1".to_owned(),
            },
        }
    );
}

#[test]
fn government_resolution_dot_punkt_binds() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1. Утвердить правила"),
        block(ParagraphStyle::Heading, "2. Признать утратившим силу"),
        block(ParagraphStyle::BodyText, "Постановление вступает в силу."),
    ];
    assert_eq!(
        profile.detect(Some("postanovlenie-pravitelstva-2024"), None, None, &blocks),
        GroupDetection::Bound {
            group: "government_resolution".to_owned(),
            factor: DetectionFactor::NeedleAndProbe,
        }
    );
}

#[test]
fn detect_pp60_basename_binds_government_resolution() {
    // S02 anchor proof: the Garant reference filename `PP_60_27-01-2022.odt`
    // carries no latin `postanovlenie-pravitelstva` token, so detect must
    // bind government_resolution through the bounded `pp_` path needle with
    // kind left at None (inspect stays `inspect <path>`).
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1. Утвердить правила"),
        block(ParagraphStyle::Heading, "2. Признать утратившим силу"),
        block(ParagraphStyle::BodyText, "Постановление вступает в силу."),
    ];
    match profile.detect_metadata(Some("PP_60_27-01-2022.odt"), None, None) {
        MetadataOutcome::Bound { group, needle } => {
            assert_eq!(group, "government_resolution");
            assert_eq!(needle, "pp_");
        }
        other => panic!("expected Bound government_resolution via pp_, got {other:?}"),
    }
    assert_eq!(
        profile.detect(Some("PP_60_27-01-2022.odt"), None, None, &blocks),
        GroupDetection::Bound {
            group: "government_resolution".to_owned(),
            factor: DetectionFactor::NeedleAndProbe,
        }
    );
}

#[test]
fn cyrillic_postanovlenie_does_not_invent_units_on_unknown_path() {
    // Hostile guard for the new needle: a Cyrillic named resolution with no
    // known path needle stays Unknown (no silent government_resolution
    // guess), and lettered punkt (а/б) do not mint unit bodies.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1. Утвердить правила"),
        block(ParagraphStyle::BodyText, "а) подпункт"),
    ];
    assert_eq!(
        profile.detect(Some("Постановление Пленума РФ"), None, None, &blocks),
        GroupDetection::Unknown {
            reason: UnknownReason::NoMetadata,
        }
    );
}

#[test]
fn departmental_order_paren_punkt_binds() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1) Утвердить стандарт"),
        block(ParagraphStyle::BodyText, "Приказываю:"),
    ];
    assert_eq!(
        profile.detect(Some("prikaz-minzdrava-2024"), None, None, &blocks),
        GroupDetection::Bound {
            group: "departmental_order".to_owned(),
            factor: DetectionFactor::NeedleAndProbe,
        }
    );
}

#[test]
fn departmental_order_wrong_numbering_style_is_conflict() {
    // Metadata says order (paren-style punkt) but the blocks use dot-style
    // numbering — the probe finds no unit markers → Unknown, not a guess.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "1. Утвердить стандарт"),
        block(ParagraphStyle::Heading, "2. Ввести в действие"),
    ];
    assert_eq!(
        profile.detect(Some("prikaz-minzdrava-2024"), None, None, &blocks),
        GroupDetection::Unknown {
            reason: UnknownReason::ProbeConflict {
                metadata_group: "departmental_order".to_owned(),
            },
        }
    );
}

#[test]
fn court_practice_ignores_depth4_numbering() {
    // R8-05 hostile: FAS decision with depth-4 numbered lists. The text-only
    // profile ignores numbered lists — no structure is detected and the
    // needle factor binds court_practice directly.
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::BodyText, "1. Комиссия решила"),
        block(ParagraphStyle::BodyText, "1.1. Рекомендовать заказчику"),
        block(ParagraphStyle::BodyText, "1.1.1. Принять меры"),
        block(ParagraphStyle::BodyText, "1.1.1.1. Уведомить стороны"),
    ];
    assert_eq!(
        profile.detect(Some("reshenie-fas-2024-123"), None, None, &blocks),
        GroupDetection::Bound {
            group: "court_practice".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
}

#[test]
fn court_practice_ignores_statya_markers() {
    // A court decision quoting "Статья 5 Конституции" is still text-only:
    // the empty profile declares no structure at all (token valid only
    // within the declaring group).
    let profile = profile();
    let blocks = vec![block(
        ParagraphStyle::BodyText,
        "Статья 5 Конституции Российской Федерации гарантирует.",
    )];
    assert_eq!(
        profile.detect(Some("opredelenie-verhovnogo-suda-7"), None, None, &blocks),
        GroupDetection::Bound {
            group: "court_practice".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
}

#[test]
fn no_metadata_with_statya_blocks_is_unknown() {
    // No data → Unknown even when the blocks look structural (fail-closed:
    // the probe alone never binds).
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        block(ParagraphStyle::BodyText, "Текст."),
    ];
    assert_eq!(
        profile.detect(None, None, None, &blocks),
        GroupDetection::Unknown {
            reason: UnknownReason::NoMetadata,
        }
    );
}

#[test]
fn metadata_conflict_is_unknown_not_guess() {
    let profile = StructuralProfile::parse_yaml(FIXTURE_YAML).expect("fixture");
    let blocks = vec![block(ParagraphStyle::Heading, "Статья 1. Тест")];
    assert_eq!(
        profile.detect(Some("shared-doc-1"), None, None, &blocks),
        GroupDetection::Conflict {
            groups: vec!["fixture_alpha".to_owned(), "fixture_beta".to_owned()],
        }
    );
}

#[test]
fn detection_is_deterministic() {
    let profile = profile();
    let blocks = vec![
        block(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        block(ParagraphStyle::BodyText, "Настоящий закон регулирует."),
    ];
    let first = profile.detect(Some("federalnyi-zakon-44-fz"), None, None, &blocks);
    let second = profile.detect(Some("federalnyi-zakon-44-fz"), None, None, &blocks);
    assert_eq!(
        first, second,
        "detection must be a pure function of its inputs"
    );
}
