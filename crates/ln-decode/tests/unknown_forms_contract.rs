use ln_decode::{
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    },
    unknown_forms::{
        census_unknown_forms, collect_unknown_forms_from_text, rank_unknown_forms,
        render_yaml_patch_candidates, UnknownFormCensus, UnknownFormKind,
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
