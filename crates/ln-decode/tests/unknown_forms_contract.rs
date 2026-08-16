use ln_decode::{
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    },
    unknown_forms::{
        apply_patch_candidates, census_unknown_forms, collect_unknown_forms_from_text,
        rank_unknown_forms, render_ranked_census_report, render_yaml_patch_candidates,
        PatchParseError, UnknownFormCensus, UnknownFormKind,
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
