use ln_temporal::document_context::*;

#[test]
fn this_ref_grammar_is_exact_and_preserves_local_spans() {
    let text = "согласно настоящего Закона и настоящей статьи";
    let evidence = detect_this_ref(text);
    assert_eq!(evidence.len(), 2);
    assert_eq!(evidence[0].surface(), "настоящего Закона");
    assert_eq!(
        &text[evidence[0].span().start()..evidence[0].span().end()],
        evidence[0].surface()
    );
    assert_eq!(evidence[1].surface(), "настоящей статьи");
}

#[test]
fn foreign_surface_does_not_authorize_reference() {
    assert!(detect_this_ref("настоящим документом не является").is_empty());
}
