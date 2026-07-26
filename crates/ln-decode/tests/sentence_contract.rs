use ln_decode::sentence::split_legal_sentences;

fn slices(text: &str) -> Vec<&str> {
    split_legal_sentences(text)
        .into_iter()
        .map(|sentence| &text[sentence.start()..sentence.end()])
        .collect()
}

#[test]
fn splits_terminal_punctuation_and_trims_external_whitespace() {
    let text = "  Первое положение. Второе положение! Третье?  ";

    assert_eq!(
        slices(text),
        vec!["Первое положение.", "Второе положение!", "Третье?"]
    );
}

#[test]
fn preserves_legal_abbreviations_inside_sentence() {
    let text =
        "Согласно ст. 5, п. 2 и ч. 1 закона в ред. 2024 г. применяется правило. Далее другое.";

    assert_eq!(
        slices(text),
        vec![
            "Согласно ст. 5, п. 2 и ч. 1 закона в ред. 2024 г. применяется правило.",
            "Далее другое.",
        ]
    );
}

#[test]
fn decimal_and_leading_numbered_clause_do_not_create_fragments() {
    let text = "1. Значение равно 5.1 процента. 2. Следующее положение.";

    assert_eq!(
        slices(text),
        vec!["1. Значение равно 5.1 процента.", "2. Следующее положение."]
    );
}

#[test]
fn includes_cyrillic_closing_quote_in_previous_sentence() {
    let text = "Установлено: «Правило действует.» Следующее положение.";

    assert_eq!(
        slices(text),
        vec!["Установлено: «Правило действует.»", "Следующее положение.",]
    );
}

#[test]
fn keeps_consecutive_terminal_punctuation_together() {
    assert_eq!(
        slices("Допускается ли это?! Следующее положение."),
        vec!["Допускается ли это?!", "Следующее положение."]
    );
}

#[test]
fn retains_trailing_unpunctuated_sentence_and_exact_utf8_offsets() {
    let text = "Статья действует. Последний абзац";
    let sentences = split_legal_sentences(text);

    assert_eq!(sentences.len(), 2);
    assert_eq!(
        &text[sentences[0].start()..sentences[0].end()],
        "Статья действует."
    );
    assert_eq!(
        &text[sentences[1].start()..sentences[1].end()],
        "Последний абзац"
    );
    assert!(sentences[0].end() <= sentences[1].start());
}

#[test]
fn empty_or_whitespace_input_has_no_sentences() {
    assert!(split_legal_sentences("").is_empty());
    assert!(split_legal_sentences(" \n\t ").is_empty());
}
