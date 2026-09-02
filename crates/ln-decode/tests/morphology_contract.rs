use ln_decode::morphology::{find_legal_markers, LegalMarkerKind};

fn matched_text(text: &str, start: usize, end: usize) -> &str {
    &text[start..end]
}

#[test]
fn finds_supported_inflections_in_source_order_with_exact_utf8_spans() {
    let text = "Статьей 5 предусмотрены пункты 2 и 3; организация обязана действовать.";

    let matches = find_legal_markers(text);

    assert_eq!(matches.len(), 3);
    assert_eq!(matches[0].kind(), LegalMarkerKind::Statya);
    assert_eq!(
        matched_text(text, matches[0].start(), matches[0].end()),
        "Статьей"
    );
    assert_eq!(matches[1].kind(), LegalMarkerKind::Punkt);
    assert_eq!(
        matched_text(text, matches[1].start(), matches[1].end()),
        "пункты"
    );
    assert_eq!(matches[2].kind(), LegalMarkerKind::Obyazan);
    assert_eq!(
        matched_text(text, matches[2].start(), matches[2].end()),
        "обязана"
    );
    assert!(matches.iter().all(|item| !item.negated()));
}

#[test]
fn classifies_immediate_ne_context_without_inventing_modality() {
    let text = "Заказчик не вправе изменять условия и не обязан продлевать срок.";

    let matches = find_legal_markers(text);

    assert_eq!(matches.len(), 2);
    assert_eq!(matches[0].kind(), LegalMarkerKind::Vprave);
    assert!(matches[0].negated());
    assert_eq!(matches[1].kind(), LegalMarkerKind::Obyazan);
    assert!(matches[1].negated());
}

#[test]
fn recognizes_prohibition_forms_case_insensitively() {
    let text = "ЗАПРЕЩАЕТСЯ передача; такие действия запрещены.";

    let matches = find_legal_markers(text);

    assert_eq!(matches.len(), 2);
    assert!(matches
        .iter()
        .all(|item| item.kind() == LegalMarkerKind::Zapret));
}

#[test]
fn rejects_prefix_false_positives_and_distant_negation() {
    let text = "Обязанность изучить пунктуацию не означает, что орган завтра вправе действовать.";

    let matches = find_legal_markers(text);

    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].kind(), LegalMarkerKind::Vprave);
    assert!(!matches[0].negated());
}

#[test]
fn punctuation_breaks_immediate_negation_context() {
    let matches = find_legal_markers("Орган не, вправе действовать.");

    assert_eq!(matches.len(), 1);
    assert_eq!(matches[0].kind(), LegalMarkerKind::Vprave);
    assert!(!matches[0].negated());
}

#[test]
fn empty_or_unrelated_text_has_no_markers() {
    assert!(find_legal_markers("").is_empty());
    assert!(find_legal_markers("Техническое описание процедуры.").is_empty());
}

#[test]
fn classifies_full_inflection_tables_for_free_text_hierarchical_markers() {
    // 38 forms: Glava x10, Chast x8, Podpunkt x10, Razdel x10 (ADR-0028 §2).
    let cases: [(&str, LegalMarkerKind); 38] = [
        // Glava
        ("глава", LegalMarkerKind::Glava),
        ("главы", LegalMarkerKind::Glava),
        ("главе", LegalMarkerKind::Glava),
        ("главу", LegalMarkerKind::Glava),
        ("главой", LegalMarkerKind::Glava),
        ("главою", LegalMarkerKind::Glava),
        ("главам", LegalMarkerKind::Glava),
        ("главами", LegalMarkerKind::Glava),
        ("главах", LegalMarkerKind::Glava),
        ("глав", LegalMarkerKind::Glava),
        // Chast
        ("часть", LegalMarkerKind::Chast),
        ("части", LegalMarkerKind::Chast),
        ("частью", LegalMarkerKind::Chast),
        ("частею", LegalMarkerKind::Chast),
        ("частей", LegalMarkerKind::Chast),
        ("частям", LegalMarkerKind::Chast),
        ("частями", LegalMarkerKind::Chast),
        ("частях", LegalMarkerKind::Chast),
        // Podpunkt
        ("подпункт", LegalMarkerKind::Podpunkt),
        ("подпункта", LegalMarkerKind::Podpunkt),
        ("подпункту", LegalMarkerKind::Podpunkt),
        ("подпунктом", LegalMarkerKind::Podpunkt),
        ("подпункте", LegalMarkerKind::Podpunkt),
        ("подпункты", LegalMarkerKind::Podpunkt),
        ("подпунктов", LegalMarkerKind::Podpunkt),
        ("подпунктам", LegalMarkerKind::Podpunkt),
        ("подпунктами", LegalMarkerKind::Podpunkt),
        ("подпунктах", LegalMarkerKind::Podpunkt),
        // Razdel
        ("раздел", LegalMarkerKind::Razdel),
        ("раздела", LegalMarkerKind::Razdel),
        ("разделу", LegalMarkerKind::Razdel),
        ("разделом", LegalMarkerKind::Razdel),
        ("разделе", LegalMarkerKind::Razdel),
        ("разделы", LegalMarkerKind::Razdel),
        ("разделов", LegalMarkerKind::Razdel),
        ("разделам", LegalMarkerKind::Razdel),
        ("разделами", LegalMarkerKind::Razdel),
        ("разделах", LegalMarkerKind::Razdel),
    ];

    for (form, kind) in cases {
        let matches = find_legal_markers(form);
        assert_eq!(matches.len(), 1, "{form}: expected exactly one match");
        assert_eq!(matches[0].kind(), kind, "{form}: wrong LegalMarkerKind");
        assert_eq!(
            matched_text(form, matches[0].start(), matches[0].end()),
            form,
            "{form}: span oracle mismatch"
        );
        assert!(!matches[0].negated(), "{form}: unexpected negation");
    }
}

#[test]
fn chains_four_hierarchical_markers_in_source_order_with_exact_spans() {
    let text = "подпунктом части главы раздела";

    let matches = find_legal_markers(text);

    assert_eq!(matches.len(), 4);
    assert_eq!(matches[0].kind(), LegalMarkerKind::Podpunkt);
    assert_eq!(matches[1].kind(), LegalMarkerKind::Chast);
    assert_eq!(matches[2].kind(), LegalMarkerKind::Glava);
    assert_eq!(matches[3].kind(), LegalMarkerKind::Razdel);
    assert_eq!(
        matched_text(text, matches[0].start(), matches[0].end()),
        "подпунктом"
    );
    assert_eq!(
        matched_text(text, matches[1].start(), matches[1].end()),
        "части"
    );
    assert_eq!(
        matched_text(text, matches[2].start(), matches[2].end()),
        "главы"
    );
    assert_eq!(
        matched_text(text, matches[3].start(), matches[3].end()),
        "раздела"
    );
    assert!(matches.iter().all(|item| !item.negated()));
}

#[test]
fn keeps_yo_and_ye_doublets_distinct_without_folding() {
    // T02 regression table: every doublet pair (ё/е stems and instrumental
    // -ой/-ою forms) maps both variants to one kind; spans reproduce the
    // source slice and nothing folds ё→е (MEM1283: tokenize never folds).
    let cases = [
        ("статьёй", LegalMarkerKind::Statya),
        ("статьей", LegalMarkerKind::Statya),
        ("запрещён", LegalMarkerKind::Zapret),
        ("запрещен", LegalMarkerKind::Zapret),
        ("главой", LegalMarkerKind::Glava),
        ("главою", LegalMarkerKind::Glava),
        ("частью", LegalMarkerKind::Chast),
        ("частею", LegalMarkerKind::Chast),
    ];

    for (form, kind) in cases {
        let matches = find_legal_markers(form);
        assert_eq!(matches.len(), 1, "{form}: expected exactly one match");
        assert_eq!(matches[0].kind(), kind, "{form}: wrong LegalMarkerKind");
        assert_eq!(
            matched_text(form, matches[0].start(), matches[0].end()),
            form,
            "{form}: span oracle mismatch"
        );
        assert!(!matches[0].negated(), "{form}: unexpected negation");
    }
}

#[test]
fn rejects_stem_overlap_prefix_nouns_and_bogus_yo_whole_tokens() {
    // Hostile unmatched surface (T02): stem overlap (глав-/част-/раздел-),
    // prefix nouns (подстатья, пунктуация), a bogus stem ё (частёю must not
    // fold onto the live form частею), and a whole-token lookalike (воглаве
    // is never split by the tokenizer) all yield exactly zero markers.
    for word in [
        "главный",
        "главенство",
        "частный",
        "частность",
        "разделение",
        "разделённый",
        "разделенный",
        "подстатья",
        "пунктуация",
        "частёю",
        "воглаве",
    ] {
        let matches = find_legal_markers(word);
        assert!(
            matches.is_empty(),
            "{word} must stay unmatched, got {matches:?}"
        );
    }
}

#[test]
fn finds_four_markers_in_fz44_036_running_text_shape_in_source_order() {
    // fz44-036 running-text shape, morphology-only surface: unit string, no
    // fixture XML and no references.rs / extract_reference_mentions here.
    let text = "подпунктом \"а\" пункта 1 части 2 настоящей статьи";

    let matches = find_legal_markers(text);

    let expected = [
        (LegalMarkerKind::Podpunkt, "подпунктом"),
        (LegalMarkerKind::Punkt, "пункта"),
        (LegalMarkerKind::Chast, "части"),
        (LegalMarkerKind::Statya, "статьи"),
    ];
    assert_eq!(matches.len(), expected.len());
    for ((kind, slice), item) in expected.iter().zip(matches.iter()) {
        assert_eq!(item.kind(), *kind, "{slice}: wrong kind or order");
        assert_eq!(
            matched_text(text, item.start(), item.end()),
            *slice,
            "{slice}: span oracle mismatch"
        );
        assert!(!item.negated(), "{slice}: unexpected negation");
    }
}
