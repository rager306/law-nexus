use ln_decode::{
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    },
    unknown_forms::{
        apply_patch_candidates, apply_structural_patch_candidates, census_structural_near_misses,
        census_unknown_forms, collect_unknown_forms_from_text, rank_structural_near_misses,
        rank_unknown_forms, render_ranked_census_report, render_structural_census_report,
        render_structural_patch_candidates, render_yaml_patch_candidates, PatchParseError,
        StructuralNearMiss, StructuralNearMissCensus, StructuralNearMissKind,
        StructuralPatchParseError, UnknownFormCensus, UnknownFormKind,
    },
};

fn block(text: &str, style: ParagraphStyle) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:unknown-forms").unwrap(),
            SourceSpan::try_new(10, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

#[test]
fn detects_unsupported_temporal_near_misses_in_source_order() {
    let text = "Закон вступала ранее; норма утрачивавшая значение.";
    let forms = collect_unknown_forms_from_text(text);
    assert_eq!(forms.len(), 2);
    assert_eq!(
        forms[0].kind(),
        UnknownFormKind::UnsupportedTemporalNearMiss
    );
    assert_eq!(
        &text[forms[0].span().start()..forms[0].span().end()],
        "вступала"
    );
    assert_eq!(
        forms[1].kind(),
        UnknownFormKind::UnsupportedTemporalNearMiss
    );
    assert_eq!(
        &text[forms[1].span().start()..forms[1].span().end()],
        "утрачивавшая"
    );
}

#[test]
fn detects_unsupported_deontic_near_misses_case_insensitively() {
    let text = "Нельзя нарушать; запретить действия; запрещение нормы.";
    let forms = collect_unknown_forms_from_text(text);
    assert_eq!(forms.len(), 3);
    assert_eq!(forms[0].kind(), UnknownFormKind::UnsupportedDeonticNearMiss);
    assert_eq!(forms[1].kind(), UnknownFormKind::UnsupportedDeonticNearMiss);
    assert_eq!(forms[2].kind(), UnknownFormKind::UnsupportedDeonticNearMiss);
}

#[test]
fn detects_unsupported_hierarchy_prefixes() {
    let text = "Подпункты части параграфа абзаца не применяются.";
    let forms = collect_unknown_forms_from_text(text);
    assert_eq!(forms.len(), 4);
    assert_eq!(forms[0].kind(), UnknownFormKind::UnsupportedHierarchyPrefix);
    assert_eq!(forms[1].kind(), UnknownFormKind::UnsupportedHierarchyPrefix);
    assert_eq!(forms[2].kind(), UnknownFormKind::UnsupportedHierarchyPrefix);
    assert_eq!(forms[3].kind(), UnknownFormKind::UnsupportedHierarchyPrefix);
}

#[test]
fn exact_supported_forms_do_not_emit_unknown_candidates() {
    let text = "Орган обязан и вправе действовать; акт вступает в силу и утрачивает силу.";
    assert!(collect_unknown_forms_from_text(text).is_empty());
}

#[test]
fn rejects_embedded_terms_and_unrelated_nouns() {
    let text = "Обязанность изучить пунктуацию и подстатью не означает правоспособности.";
    assert!(collect_unknown_forms_from_text(text).is_empty());
}

#[test]
fn provider_comment_excludes_and_census_is_repeat_deterministic() {
    let body = block("Нельзя и запретить.", ParagraphStyle::BodyText);
    let comment = block("Нельзя и запретить.", ParagraphStyle::ProviderComment);
    let first = census_unknown_forms(&body);
    let second = census_unknown_forms(&body);
    assert_eq!(first, second);
    assert_eq!(first.deontic_unsupported(), 2);
    assert_eq!(first.temporal_unsupported(), 0);
    assert_eq!(first.hierarchy_prefix_unsupported(), 0);
    assert_eq!(census_unknown_forms(&comment), UnknownFormCensus::default());
}

// ─── M169 S04 T01: ranked census + YAML patch candidate ────────────────────

#[test]
fn ranked_census_counts_sorts_and_excludes_provider_comments() {
    let text = "абзац подпункт подпункт абзац вступала вступала вступала";
    let blocks = vec![
        block(text, ParagraphStyle::BodyText),
        block("абзац абзац абзац", ParagraphStyle::ProviderComment),
    ];
    let ranked = rank_unknown_forms(&blocks);
    assert!(!ranked.is_empty());
    // counts non-increasing; ties broken by token asc
    for w in ranked.windows(2) {
        assert!(
            w[0].count() > w[1].count()
                || (w[0].count() == w[1].count() && w[0].token() <= w[1].token()),
            "sorted: {ranked:?}"
        );
    }
    assert_eq!(ranked[0].token(), "вступала");
    assert_eq!(ranked[0].count(), 3);
    // provider-comment text must not contribute
    assert!(ranked.iter().all(|r| r.count() < 4));
}

#[test]
fn yaml_patch_candidates_are_deterministic_and_lexeme_only() {
    let blocks = vec![block("подпунктам абзац абзац", ParagraphStyle::BodyText)];
    let ranked = rank_unknown_forms(&blocks);
    let yaml = render_yaml_patch_candidates(&ranked);
    assert!(yaml.contains("# ranked unknown-form candidates"), "{yaml}");
    assert!(
        yaml.contains("- {kind: UnsupportedHierarchyPrefix, token: абзац, count: 2}"),
        "{yaml}"
    );
    assert!(yaml.contains("token: подпунктам, count: 1"), "{yaml}");
    // deterministic across repeated renders
    let rerendered = {
        let blocks2 = vec![block("подпунктам абзац абзац", ParagraphStyle::BodyText)];
        render_yaml_patch_candidates(&rank_unknown_forms(&blocks2))
    };
    assert_eq!(yaml, rerendered);
    // no raw block text: every emitted token is a single lexeme (no spaces)
    for line in yaml.lines().filter(|l| l.starts_with("- {")) {
        let token = line
            .split("token: ")
            .nth(1)
            .unwrap()
            .split(',')
            .next()
            .unwrap();
        assert!(!token.contains(' '), "lexeme only: {line}");
    }
}

#[test]
fn ranked_census_empty_when_no_unknowns() {
    let blocks = vec![block("обычный текст без опор", ParagraphStyle::BodyText)];
    assert!(rank_unknown_forms(&blocks).is_empty());
    assert!(render_yaml_patch_candidates(&rank_unknown_forms(&blocks)).contains("(none)"));
}

// ─── M169 S04 T01: fingerprints, census report, apply loop ──────────────────

#[test]
fn unknown_form_records_carry_kind_span_and_fingerprint() {
    let text = "вступала норма";
    let forms = collect_unknown_forms_from_text(text);
    assert_eq!(forms.len(), 1);
    assert_eq!(
        forms[0].kind(),
        UnknownFormKind::UnsupportedTemporalNearMiss
    );
    assert_eq!(
        &text[forms[0].span().start()..forms[0].span().end()],
        "вступала"
    );
    assert!(
        forms[0].fingerprint().starts_with("fnv1a64:"),
        "{}",
        forms[0].fingerprint()
    );
}

#[test]
fn ranked_census_carries_stable_fingerprint_ids() {
    let blocks = vec![
        block("вступала вступала абзац", ParagraphStyle::BodyText),
        block("вступала", ParagraphStyle::BodyText),
    ];
    let ranked = rank_unknown_forms(&blocks);
    let temporal = ranked
        .iter()
        .find(|r| r.kind() == UnknownFormKind::UnsupportedTemporalNearMiss)
        .expect("temporal entry");
    assert_eq!(temporal.count(), 3);
    assert!(temporal.fingerprint().starts_with("fnv1a64:"));
    assert_eq!(temporal.fingerprint().len(), "fnv1a64:".len() + 16);
    // same lexeme → same fingerprint across separate runs (stable identity)
    let single = rank_unknown_forms(&[block("вступала", ParagraphStyle::BodyText)]);
    assert_eq!(single[0].fingerprint(), temporal.fingerprint());
    // distinct lexemes → distinct fingerprints
    let hierarchy = ranked
        .iter()
        .find(|r| r.kind() == UnknownFormKind::UnsupportedHierarchyPrefix)
        .expect("hierarchy entry");
    assert_ne!(hierarchy.fingerprint(), temporal.fingerprint());
}

#[test]
fn applying_full_patch_candidate_drops_census_to_zero() {
    let text = "вступала абзац вступала подпункт абзац";
    let blocks = vec![block(text, ParagraphStyle::BodyText)];
    // collect through the public API before apply
    let collected = collect_unknown_forms_from_text(text);
    assert_eq!(collected.len(), 5);
    assert!(!rank_unknown_forms(&blocks).is_empty());
    // render the candidate and apply it through the public apply API
    let yaml = render_yaml_patch_candidates(&rank_unknown_forms(&blocks));
    let applied = apply_patch_candidates(&yaml).expect("rendered candidate applies cleanly");
    assert!(!applied.is_empty());
    // after applying, the census for these forms drops to zero
    assert!(applied.collect_unknown_forms(text).is_empty());
    assert!(applied.rank_unknown_forms(&blocks).is_empty());
    let after = render_yaml_patch_candidates(&applied.rank_unknown_forms(&blocks));
    assert!(after.contains("(none)"), "{after}");
}

#[test]
fn applied_patch_excludes_only_approved_forms() {
    let text = "вступала абзац";
    let yaml = "- {kind: UnsupportedHierarchyPrefix, token: абзац, count: 1}\n";
    let applied = apply_patch_candidates(yaml).expect("patch applies");
    assert_eq!(applied.len(), 1);
    let ranked = rank_unknown_forms(&[block("абзац", ParagraphStyle::BodyText)]);
    assert!(applied.covers(ranked[0].kind(), ranked[0].fingerprint()));
    let remaining = applied.collect_unknown_forms(text);
    assert_eq!(remaining.len(), 1);
    assert_eq!(
        remaining[0].kind(),
        UnknownFormKind::UnsupportedTemporalNearMiss
    );
}

#[test]
fn applying_empty_patch_is_a_noop() {
    let text = "вступала абзац";
    for yaml in ["", "# comment only\n", "(none)\n"] {
        let applied = apply_patch_candidates(yaml).expect("empty patch applies");
        assert!(applied.is_empty());
        assert_eq!(applied.collect_unknown_forms(text).len(), 2);
    }
}

#[test]
fn apply_patch_deduplicates_identical_candidates() {
    let yaml = "- {kind: UnsupportedHierarchyPrefix, token: абзац, count: 2}\n\
                - {kind: UnsupportedHierarchyPrefix, token: абзац, count: 1}\n";
    let applied = apply_patch_candidates(yaml).expect("patch applies");
    assert_eq!(applied.len(), 1);
}

#[test]
fn apply_patch_rejects_unknown_kind_label() {
    let yaml = "- {kind: UnsupportedFoo, token: абзац, count: 1}\n";
    let err = apply_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(
            &err,
            PatchParseError::UnknownKind { label, line_number: 1 } if label == "UnsupportedFoo"
        ),
        "{err}"
    );
}

#[test]
fn apply_patch_rejects_invalid_token() {
    for bad in ["абз ац", "абзац:", "абзац#", "{абзац}", ""] {
        let yaml = format!("- {{kind: UnsupportedHierarchyPrefix, token: {bad}, count: 1}}\n");
        let err = apply_patch_candidates(&yaml).unwrap_err();
        assert!(
            matches!(&err, PatchParseError::InvalidToken { .. }),
            "{bad:?} => {err}"
        );
    }
}

#[test]
fn apply_patch_rejects_invalid_count() {
    let yaml = "- {kind: UnsupportedHierarchyPrefix, token: абзац, count: nope}\n";
    let err = apply_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(&err, PatchParseError::InvalidCount { .. }),
        "{err}"
    );
}

#[test]
fn apply_patch_rejects_malformed_lines() {
    for yaml in [
        "garbage line\n",
        "- {kind: UnsupportedTemporalNearMiss, count: 1}\n",
        "- {kind: UnsupportedTemporalNearMiss, token: вступала}\n",
        "- kind: UnsupportedTemporalNearMiss, token: вступала, count: 1\n",
        "- {kind: UnsupportedTemporalNearMiss, token: вступала, count: 1}\n- {broken}\n",
        "- {kind: UnsupportedHierarchyPrefix, token: абзац,, count: 1}\n",
    ] {
        assert!(apply_patch_candidates(yaml).is_err(), "{yaml:?}");
    }
}

#[test]
fn ranked_report_is_deterministic_and_text_free() {
    let blocks = vec![block("вступала абзац абзац", ParagraphStyle::BodyText)];
    let ranked = rank_unknown_forms(&blocks);
    let report = render_ranked_census_report(&ranked);
    assert!(report.starts_with("# ranked unknown-form census"));
    assert!(report.contains("fingerprint: fnv1a64:"));
    assert!(report.contains("count: 2"));
    // fingerprint-only view: no lexemes, no raw text, no token field
    assert!(!report.contains("вступала"));
    assert!(!report.contains("абзац"));
    assert!(!report.contains("token:"));
    // deterministic across runs
    let again = render_ranked_census_report(&rank_unknown_forms(&blocks));
    assert_eq!(report, again);
    // empty case
    assert!(render_ranked_census_report(&[]).contains("(none)"));
}

// ─── M171 S03 T01: StructuralNearMiss census + profile-extension candidates ──

#[test]
fn structural_near_miss_events_carry_closed_kind_identity_and_fingerprint() {
    let overflow = StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2);
    assert_eq!(overflow.kind(), StructuralNearMissKind::DepthOverflow);
    assert_eq!(overflow.group(), "government_resolution");
    assert_eq!(overflow.token(), "punkt");
    assert_eq!(overflow.observed_depth(), Some(4));
    assert_eq!(overflow.profile_cap(), Some(2));
    assert!(overflow.fingerprint().starts_with("fnv1a64:"));
    assert_eq!(overflow.fingerprint().len(), "fnv1a64:".len() + 16);

    let non_catalog = StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel");
    assert_eq!(non_catalog.kind(), StructuralNearMissKind::NonCatalogToken);
    assert_eq!(non_catalog.observed_depth(), None);
    assert_eq!(non_catalog.profile_cap(), None);

    // same (kind, group, token) identity → same fingerprint across runs;
    // distinct identities → distinct fingerprints (depth is not identity)
    let deeper = StructuralNearMiss::depth_overflow("government_resolution", "punkt", 5, 2);
    assert_eq!(deeper.fingerprint(), overflow.fingerprint());
    assert_ne!(non_catalog.fingerprint(), overflow.fingerprint());
    let other = StructuralNearMiss::depth_overflow("government_resolution", "podpunkt", 3, 2);
    assert_ne!(other.fingerprint(), overflow.fingerprint());
}

#[test]
fn structural_census_counts_by_kind_and_is_repeat_deterministic() {
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 3, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
    ];
    let first = census_structural_near_misses(&events);
    let second = census_structural_near_misses(&events);
    assert_eq!(first, second);
    assert_eq!(first.depth_overflow(), 2);
    assert_eq!(first.non_catalog_token(), 1);
    assert_eq!(
        census_structural_near_misses(&[]),
        StructuralNearMissCensus::default()
    );
}

#[test]
fn structural_rank_sorts_by_count_then_token_and_aggregates_max_depth() {
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 5, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::depth_overflow("departmental_order", "podpunkt", 3, 2),
    ];
    let ranked = rank_structural_near_misses(&events);
    assert_eq!(ranked.len(), 3);
    // counts non-increasing; ties broken by token asc
    for w in ranked.windows(2) {
        assert!(
            w[0].count() > w[1].count()
                || (w[0].count() == w[1].count() && w[0].token() <= w[1].token()),
            "sorted: {ranked:?}"
        );
    }
    assert_eq!(ranked[0].token(), "razdel");
    assert_eq!(ranked[0].count(), 3);
    let punkt = ranked
        .iter()
        .find(|r| r.token() == "punkt")
        .expect("punkt entry");
    assert_eq!(punkt.count(), 2);
    assert_eq!(punkt.kind(), StructuralNearMissKind::DepthOverflow);
    // proposed cap = max observed depth across the aggregated events
    assert_eq!(punkt.max_depth(), Some(5));
    assert!(ranked
        .iter()
        .all(|r| r.fingerprint().starts_with("fnv1a64:")));
}

#[test]
fn structural_census_report_is_fingerprint_only_and_text_free() {
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
    ];
    let ranked = rank_structural_near_misses(&events);
    let report = render_structural_census_report(&ranked);
    assert!(report.starts_with("# ranked structural near-miss census"));
    assert!(report.contains("fingerprint: fnv1a64:"));
    assert!(report.contains("count: 2"));
    // fingerprint-only view: no group ids, no token names, no raw text
    assert!(!report.contains("government_resolution"));
    assert!(!report.contains("razdel"));
    assert!(!report.contains("punkt"));
    assert!(!report.contains("group:"));
    assert!(!report.contains("token:"));
    // deterministic across runs
    let again = render_structural_census_report(&rank_structural_near_misses(&events));
    assert_eq!(report, again);
    // empty case
    assert!(render_structural_census_report(&[]).contains("(none)"));
}

#[test]
fn structural_patch_candidates_are_deterministic_profile_extensions() {
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 5, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
    ];
    let ranked = rank_structural_near_misses(&events);
    let yaml = render_structural_patch_candidates(&ranked);
    assert!(
        yaml.starts_with("# ranked structural profile-extension candidates"),
        "{yaml}"
    );
    // depth overflow proposes raising the group cap to the max observed depth
    assert!(
        yaml.contains(
            "- {kind: DepthOverflow, group: government_resolution, token: punkt, max_depth: 5, count: 2}"
        ),
        "{yaml}"
    );
    // non-catalog token proposes adding the token; no max_depth field
    assert!(
        yaml.contains("- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: 2}"),
        "{yaml}"
    );
    // deterministic across repeated renders
    let rerendered = render_structural_patch_candidates(&rank_structural_near_misses(&events));
    assert_eq!(yaml, rerendered);
    // empty case
    assert!(render_structural_patch_candidates(&[]).contains("(none)"));
}

#[test]
fn structural_depth_overflow_apply_loop_drops_census_to_zero() {
    // demo cycle: depth-переполнение → near-miss → apply → ноль
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 5, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
    ];
    // census before apply is non-zero
    let census = census_structural_near_misses(&events);
    assert!(census.depth_overflow() > 0 && census.non_catalog_token() > 0);
    assert!(!rank_structural_near_misses(&events).is_empty());
    // render the candidates and apply them through the structural apply API
    let yaml = render_structural_patch_candidates(&rank_structural_near_misses(&events));
    let applied =
        apply_structural_patch_candidates(&yaml).expect("rendered candidate applies cleanly");
    assert!(!applied.is_empty());
    assert_eq!(applied.len(), 2);
    // after applying, the census for these classes drops to zero
    assert!(applied.rank_structural_near_misses(&events).is_empty());
    assert!(applied.collect_structural_near_misses(&events).is_empty());
    assert_eq!(
        applied.census_structural_near_misses(&events),
        StructuralNearMissCensus::default()
    );
    let after = render_structural_census_report(&applied.rank_structural_near_misses(&events));
    assert!(after.contains("(none)"), "{after}");
}

#[test]
fn structural_patch_excludes_only_approved_classes() {
    let events = vec![
        StructuralNearMiss::depth_overflow("government_resolution", "punkt", 4, 2),
        StructuralNearMiss::non_catalog_token("federal_law@v1", "razdel"),
    ];
    let yaml =
        "- {kind: DepthOverflow, group: government_resolution, token: punkt, max_depth: 4, count: 1}\n";
    let applied = apply_structural_patch_candidates(yaml).expect("patch applies");
    assert_eq!(applied.len(), 1);
    let ranked = rank_structural_near_misses(&events);
    let punkt = ranked.iter().find(|r| r.token() == "punkt").expect("punkt");
    assert!(applied.covers(punkt.kind(), punkt.fingerprint()));
    let razdel = ranked
        .iter()
        .find(|r| r.token() == "razdel")
        .expect("razdel");
    assert!(!applied.covers(razdel.kind(), razdel.fingerprint()));
    let remaining = applied.rank_structural_near_misses(&events);
    assert_eq!(remaining.len(), 1);
    assert_eq!(remaining[0].token(), "razdel");
}

#[test]
fn structural_apply_deduplicates_identical_candidates() {
    let yaml = "- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: 3}\n\
                - {kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: 1}\n";
    let applied = apply_structural_patch_candidates(yaml).expect("patch applies");
    assert_eq!(applied.len(), 1);
}

#[test]
fn applying_empty_structural_patch_is_a_noop() {
    let events = vec![StructuralNearMiss::non_catalog_token(
        "federal_law@v1",
        "razdel",
    )];
    for yaml in ["", "# comment only\n", "(none)\n"] {
        let applied = apply_structural_patch_candidates(yaml).expect("empty patch applies");
        assert!(applied.is_empty());
        assert_eq!(applied.rank_structural_near_misses(&events).len(), 1);
    }
}

#[test]
fn structural_apply_rejects_unknown_kind_label() {
    let yaml = "- {kind: StructuralFoo, group: federal_law@v1, token: razdel, count: 1}\n";
    let err = apply_structural_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(
            &err,
            StructuralPatchParseError::UnknownKind { label, line_number: 1 }
                if label == "StructuralFoo"
        ),
        "{err}"
    );
}

#[test]
fn structural_apply_rejects_invalid_token_and_group() {
    for bad in ["raz del", "razdel:", "razdel#", "{razdel}", ""] {
        let yaml =
            format!("- {{kind: NonCatalogToken, group: federal_law@v1, token: {bad}, count: 1}}\n");
        let err = apply_structural_patch_candidates(&yaml).unwrap_err();
        assert!(
            matches!(&err, StructuralPatchParseError::InvalidToken { .. }),
            "{bad:?} => {err}"
        );
    }
    for bad in ["federal law@v1", "group{1}", ""] {
        let yaml = format!("- {{kind: NonCatalogToken, group: {bad}, token: razdel, count: 1}}\n");
        let err = apply_structural_patch_candidates(&yaml).unwrap_err();
        assert!(
            matches!(&err, StructuralPatchParseError::InvalidGroup { .. }),
            "{bad:?} => {err}"
        );
    }
}

#[test]
fn structural_apply_rejects_invalid_count_and_max_depth() {
    let yaml = "- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: nope}\n";
    let err = apply_structural_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(&err, StructuralPatchParseError::InvalidCount { .. }),
        "{err}"
    );

    let yaml =
        "- {kind: DepthOverflow, group: government_resolution, token: punkt, max_depth: deep, count: 1}\n";
    let err = apply_structural_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(&err, StructuralPatchParseError::InvalidMaxDepth { .. }),
        "{err}"
    );
}

#[test]
fn structural_apply_requires_max_depth_for_depth_overflow_and_forbids_for_non_catalog() {
    // DepthOverflow without the proposed cap → fail-closed
    let yaml = "- {kind: DepthOverflow, group: government_resolution, token: punkt, count: 1}\n";
    let err = apply_structural_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(
            &err,
            StructuralPatchParseError::MissingMaxDepth { line_number: 1 }
        ),
        "{err}"
    );
    // NonCatalogToken with max_depth → malformed (field meaningless for the class)
    let yaml =
        "- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, max_depth: 2, count: 1}\n";
    let err = apply_structural_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(&err, StructuralPatchParseError::MalformedLine { .. }),
        "{err}"
    );
}

#[test]
fn structural_apply_rejects_malformed_lines() {
    for yaml in [
        "garbage line\n",
        "- {kind: NonCatalogToken, count: 1}\n",
        "- {kind: NonCatalogToken, group: federal_law@v1}\n",
        "- kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: 1\n",
        "- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, count: 1}\n- {broken}\n",
        "- {kind: NonCatalogToken, group: federal_law@v1, token: razdel, max_depth: 1, count: 1}\n",
    ] {
        assert!(apply_structural_patch_candidates(yaml).is_err(), "{yaml:?}");
    }
}

#[test]
fn lexical_apply_grammar_remains_closed_to_structural_kinds() {
    // D185 boundary: the existing apply grammar stays closed — a structural
    // kind label is rejected by the lexical apply API, so the structural
    // census routes through its own fail-closed apply instead.
    let yaml = "- {kind: DepthOverflow, group: government_resolution, token: punkt, count: 1}\n";
    let err = apply_patch_candidates(yaml).unwrap_err();
    assert!(
        matches!(
            &err,
            PatchParseError::UnknownKind { label, .. } if label == "DepthOverflow"
        ),
        "{err}"
    );
}

#[test]
fn structural_census_consumes_events_not_text() {
    // No-lexical-scanner boundary: the structural census takes structural
    // events only — there is no text/block input and no tokenizer in this
    // contour. A token that would be a lexical near-miss in running text
    // never appears here; only catalog identifiers reach the candidate view,
    // and the report stays fingerprint-only.
    let events = vec![StructuralNearMiss::depth_overflow(
        "government_resolution",
        "punkt",
        3,
        2,
    )];
    let ranked = rank_structural_near_misses(&events);
    assert_eq!(ranked.len(), 1);
    let report = render_structural_census_report(&ranked);
    assert!(!report.contains("punkt"));
    assert!(!report.contains("government_resolution"));
    let yaml = render_structural_patch_candidates(&ranked);
    assert!(yaml.contains("token: punkt"));
    assert!(render_structural_patch_candidates(&[]).contains("(none)"));
}
