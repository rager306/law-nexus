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
