use ln_decode::change_grammar::{
    CHANGE_GRAMMAR_NON_CLAIMS, ChangeOpKind, ChangeParseRefusal, ChangePositionParam,
    StructuralLevel, StructuralLocator, StructuralStep, parse_amending_blocks,
};

#[test]
fn parses_real_484_fz_clause_patterns_with_nested_scopes_and_editorial_filtering() {
    let blocks = [
        "Статья 1",
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ \"О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд\" следующие изменения:",
        "1) в части 1 статьи 3:",
        "а) пункт 8 после слов \"гражданско-правовой договор,\" дополнить словами \"который заключен в письменной форме и\";",
        "б) пункт 8.1 после слов \"гражданско-правовой договор,\" дополнить словами \"который заключен в письменной форме и\";",
        "КонсультантПлюс: примечание.",
        "П. 2 ст. 1 вступает в силу с 01.01.2026.",
        "2) в части 12.1 статьи 24.2 слово \"электронные\" заменить словами \"информацию и\", слова \"электронных документов)\" заменить словами \"информации и документов)\", дополнить новым вторым предложением следующего содержания: \"Если...\";",
        "7) в подпункте \"а\" пункта 1 части 1 статьи 72 слово \"подпунктами\" заменить словом \"пунктами\";",
    ];

    let report = parse_amending_blocks(&blocks);
    assert_eq!(report.editorial_notes_skipped, 1);
    assert_eq!(report.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);

    assert_eq!(report.candidates.len(), 5);

    let c0 = &report.candidates[0];
    assert_eq!(c0.owner_act.date.as_deref(), Some("2013-04-05"));
    assert_eq!(c0.owner_act.number.as_deref(), Some("44-ФЗ"));
    assert_eq!(
        c0.target_locator.canonical_path(),
        "statya-3/chast-1/punkt-8"
    );
    assert_eq!(c0.kind, ChangeOpKind::InsertText);
    assert_eq!(c0.param, ChangePositionParam::AfterAnchor);
    assert_eq!(
        c0.loc_value.as_deref(),
        Some("гражданско-правовой договор,")
    );
    assert_eq!(
        c0.value.as_deref(),
        Some("который заключен в письменной форме и")
    );

    assert_eq!(
        report.candidates[1].target_locator.canonical_path(),
        "statya-3/chast-1/punkt-8.1"
    );
    assert_eq!(report.candidates[1].kind, ChangeOpKind::InsertText);

    assert_eq!(
        report.candidates[2].target_locator.canonical_path(),
        "statya-24.2/chast-12.1"
    );
    assert_eq!(report.candidates[2].kind, ChangeOpKind::ReplaceText);
    assert_eq!(report.candidates[2].param, ChangePositionParam::ExactAnchor);
    assert_eq!(
        report.candidates[2].loc_value.as_deref(),
        Some("электронные")
    );
    assert_eq!(report.candidates[2].value.as_deref(), Some("информацию и"));

    assert_eq!(report.candidates[3].kind, ChangeOpKind::ReplaceText);
    assert_eq!(report.candidates[3].param, ChangePositionParam::ExactAnchor);
    assert_eq!(
        report.candidates[3].loc_value.as_deref(),
        Some("электронных документов)")
    );
    assert_eq!(
        report.candidates[3].value.as_deref(),
        Some("информации и документов)")
    );

    assert_eq!(
        report.candidates[4].target_locator.canonical_path(),
        "statya-72/chast-1/punkt-1/podpunkt-а"
    );
    assert_eq!(report.candidates[4].kind, ChangeOpKind::ReplaceText);
    assert_eq!(report.candidates[4].param, ChangePositionParam::ExactAnchor);

    // Unsupported trailing tail MUST fail closed!
    assert_eq!(report.refusals.len(), 1);
    assert!(matches!(
        &report.refusals[0],
        ChangeParseRefusal::UnsupportedOperation { block_index: 7, .. }
    ));
}

#[test]
fn parses_before_anchor_end_of_component_guillemets_and_nested_abbrevs() {
    let blocks = [
        "Статья 1",
        "Внести в Федеральный закон От 5 апреля 2013 года N 44-ФЗ «О контрактной системе» следующие изменения:",
        "1) в ч. 1 ст. 3 перед цифрами «10» дополнить словом «до»;",
        "2) в п. 2 ч. 1 ст. 5 перед словами «заказчик обязан» дополнить словами «в установленный срок »;",
        "3) подп. «а» п. 1 ст. 10 дополнить словами «(включая «вложенные» условия)»;",
        "4) ч. 2 ст. 12 изложить в следующей редакции:",
        "«2. Первая строка ссылается на «Закон о закупках».",
        "Вторая строка завершает новую редакцию.»;",
    ];

    let report = parse_amending_blocks(&blocks);
    assert!(
        report.refusals.is_empty(),
        "unexpected refusals: {:?}",
        report.refusals
    );
    assert_eq!(report.candidates.len(), 4);

    // Capitalized Cyrillic "От" extracts date properly.
    assert_eq!(
        report.candidates[0].owner_act.date.as_deref(),
        Some("2013-04-05")
    );
    // BeforeAnchor with "перед цифрами" (P1 fix verification)
    assert_eq!(
        report.candidates[0].target_locator.canonical_path(),
        "statya-3/chast-1"
    );
    assert_eq!(report.candidates[0].kind, ChangeOpKind::InsertText);
    assert_eq!(
        report.candidates[0].param,
        ChangePositionParam::BeforeAnchor
    );
    assert_eq!(report.candidates[0].loc_value.as_deref(), Some("10"));
    assert_eq!(report.candidates[0].value.as_deref(), Some("до"));

    // BeforeAnchor with "перед словами"
    assert_eq!(
        report.candidates[1].param,
        ChangePositionParam::BeforeAnchor
    );
    assert_eq!(
        report.candidates[1].loc_value.as_deref(),
        Some("заказчик обязан")
    );

    // EndOfComponent with nested guillemets «... «...» ...»
    assert_eq!(
        report.candidates[2].target_locator.canonical_path(),
        "statya-10/punkt-1/podpunkt-а"
    );
    assert_eq!(
        report.candidates[2].param,
        ChangePositionParam::EndOfComponent
    );
    assert_eq!(
        report.candidates[2].value.as_deref(),
        Some("(включая «вложенные» условия)")
    );

    // Multi-line guillemet block with nested «...» inside line 1 must not truncate early!
    assert_eq!(
        report.candidates[3].target_locator.canonical_path(),
        "statya-12/chast-2"
    );
    assert_eq!(report.candidates[3].kind, ChangeOpKind::ReplaceText);
    assert_eq!(
        report.candidates[3].param,
        ChangePositionParam::WholeComponent
    );
    assert!(
        report.candidates[3]
            .value
            .as_deref()
            .expect("quoted")
            .contains("Вторая строка завершает новую редакцию.")
    );
}

#[test]
fn parses_138_fz_whole_replacement_attach_and_non_44fz_delete_and_repeal() {
    let blocks = [
        "Статья 1",
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ \"О контрактной системе\" следующие изменения:",
        "1) часть 9 статьи 31 изложить в следующей редакции:",
        "\"9. Комиссия по осуществлению закупок обязана отстранить участника закупки.\";",
        "2) статью 43 дополнить частью 12 следующего содержания:",
        "\"12. Ответственность за недостоверность информации несет участник закупки.\".",
        "Статья 2",
        "Внести в Федеральный закон от 6 декабря 2011 года N 402-ФЗ \"О бухгалтерском учете\" следующие изменения:",
        "1) в части 2 статьи 7 слова \"иных документов\" исключить;",
        "2) пункт 3 статьи 9 признать утратившим силу.",
    ];

    let report = parse_amending_blocks(&blocks);
    assert!(
        report.refusals.is_empty(),
        "got refusals: {:?}",
        report.refusals
    );
    assert_eq!(report.candidates.len(), 4);

    assert_eq!(
        report.candidates[0].target_locator.canonical_path(),
        "statya-31/chast-9"
    );
    assert_eq!(report.candidates[0].kind, ChangeOpKind::ReplaceText);
    assert_eq!(
        report.candidates[0].param,
        ChangePositionParam::WholeComponent
    );

    assert_eq!(
        report.candidates[1].target_locator.canonical_path(),
        "statya-43/chast-12"
    );
    assert_eq!(report.candidates[1].kind, ChangeOpKind::Attach);
    assert_eq!(
        report.candidates[1].param,
        ChangePositionParam::NewComponent
    );
    assert_eq!(
        report.candidates[1]
            .child_spec
            .as_ref()
            .map(|c| (c.level, c.value.as_str())),
        Some((StructuralLevel::Chast, "12"))
    );

    assert_eq!(
        report.candidates[2].owner_act.number.as_deref(),
        Some("402-ФЗ")
    );
    assert_eq!(
        report.candidates[2].target_locator.canonical_path(),
        "statya-7/chast-2"
    );
    assert_eq!(report.candidates[2].kind, ChangeOpKind::DeleteText);
    assert_eq!(report.candidates[2].param, ChangePositionParam::ExactAnchor);

    assert_eq!(
        report.candidates[3].owner_act.number.as_deref(),
        Some("402-ФЗ")
    );
    assert_eq!(
        report.candidates[3].target_locator.canonical_path(),
        "statya-9/punkt-3"
    );
    assert_eq!(report.candidates[3].kind, ChangeOpKind::Repeal);
    assert_eq!(
        report.candidates[3].param,
        ChangePositionParam::WholeComponent
    );
}

#[test]
fn hostile_utf8_edge_cases_scope_isolation_and_fail_closed_refusals() {
    // 1. Empty input and editorial note at EOF are panic-free.
    let empty = parse_amending_blocks(&[]);
    assert!(empty.candidates.is_empty() && empty.refusals.is_empty());

    let eof_note = parse_amending_blocks(&["КонсультантПлюс: примечание."]);
    assert_eq!(eof_note.editorial_notes_skipped, 1);
    assert!(eof_note.candidates.is_empty());

    // 2. StructuralLocator::with_overlay prunes finer sibling descendants.
    let parent = StructuralLocator::new(vec![
        StructuralStep::new(StructuralLevel::Statya, "3"),
        StructuralStep::new(StructuralLevel::Chast, "1"),
        StructuralStep::new(StructuralLevel::Punkt, "2"),
        StructuralStep::new(StructuralLevel::Podpunkt, "а"),
    ]);
    let child = parent.with_overlay(&[StructuralStep::new(StructuralLevel::Punkt, "3")]);
    assert_eq!(child.canonical_path(), "statya-3/chast-1/punkt-3");

    // 3. Turkish dotted İ (U+0130 -> 2 chars lowercase) MUST NOT panic on slicing.
    let utf8_hostile = [
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ следующие изменения:",
        "1) в ст. 1 \"İ\" дополнить 1пунктом следующего содержания:",
        "2) пункт 1 статьи 2 признать утратившİм aсилу аб",
    ];
    let r_utf8 = parse_amending_blocks(&utf8_hostile);
    assert!(!r_utf8.refusals.is_empty());

    // 4. Truncated unclosed quote after valid first op fails closed (`INV-10`),
    //    unrecognized container header clears prior scope, plural targets refuse,
    //    and new top-level `Статья 2` resets `current_act`.
    let hostile_clauses = [
        "Статья 1",
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ следующие изменения:",
        "1) слово \"а\" заменить словом \"б\";",
        "2) часть 9 статьи 31 изложить в следующей редакции:",
        "\";",
        "3) в пункте 1 статьи 3 слово \"а\" заменить словом \"б\", слова \"незакрытая",
        "4) в наименовании:",
        "а) слово \"х\" заменить словом \"у\";",
        "5) в пунктах 1 и 2 статьи 5 слово \"а\" заменить словом \"б\";",
        "Статья 2",
        "1. Настоящий Федеральный закон вступает в силу с 1 января 2026 года.",
        "2. Положения статьи 5 не применяются.",
    ];
    let report = parse_amending_blocks(&hostile_clauses);
    // Only the valid first op of clause 3 should become a candidate; clause 4a MUST NOT inherit prior scope!
    assert_eq!(report.candidates.len(), 1);
    assert_eq!(
        report.candidates[0].target_locator.canonical_path(),
        "statya-3/punkt-1"
    );
    // Refusals: clause 1 AmbiguousTarget, clause 2 IncompleteSource (empty `";`),
    // clause 3 IncompleteSource (unclosed quote tail), clause 4 AmbiguousTarget,
    // clause 4a AmbiguousTarget, clause 5 AmbiguousTarget (plural).
    // Article 2 has no current_act so its transitional clauses produce 0 bogus candidates/refusals!
    assert!(report.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 2, .. }
    )));
    assert!(report.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::IncompleteSource { block_index: 3, .. }
    )));
    assert!(report.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::IncompleteSource { block_index: 5, .. }
    )));
    assert!(report.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 6, .. }
    )));
    assert!(report.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 8, .. }
    )));
}

#[test]
fn smoke_real_consru_export_484_fz_and_138_fz_parse_deterministically() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let p138 = root.join(
        "consru_export/consru_export/exports/npa/law_2025-06-07_138-fz_rev-unknown_1c01dbd3.xml",
    );
    let p484 = root.join(
        "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml",
    );
    if !p138.exists() || !p484.exists() {
        eprintln!("SKIP [smoke]: consru_export 138-FZ/484-FZ not present");
        return;
    }

    let extract_paras = |path: &std::path::Path| -> Vec<String> {
        use ln_decode::adapters::ConsultantWordMlBlockDecoder;
        use ln_decode::domain::{DecodeRequest, FamilyFormat, PayloadRef};
        use ln_decode::ports::BlockDecoderPort;

        let bytes = std::fs::read(path).expect("read xml");
        let req = DecodeRequest::new(
            PayloadRef::parse("payload:adr0032-change-grammar-smoke").expect("payload ref"),
            FamilyFormat::parse("family:consultant-wordml").expect("family format"),
            &bytes,
        );
        let blocks = ConsultantWordMlBlockDecoder
            .decode_blocks(&req)
            .expect("decode wordml");
        blocks.into_iter().map(|b| b.text().to_owned()).collect()
    };

    let p138_lines = extract_paras(&p138);
    let p138_refs: Vec<&str> = p138_lines.iter().map(String::as_str).collect();
    let r138 = parse_amending_blocks(&p138_refs);
    assert_eq!(r138.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);
    assert_eq!(
        r138.candidates.len(),
        2,
        "138-FZ has exactly 2 clauses (ReplaceText + Attach)"
    );
    assert_eq!(
        r138.candidates[0].target_locator.canonical_path(),
        "statya-31/chast-9"
    );
    assert_eq!(r138.candidates[0].kind, ChangeOpKind::ReplaceText);
    assert_eq!(
        r138.candidates[1].target_locator.canonical_path(),
        "statya-43/chast-12"
    );
    assert_eq!(r138.candidates[1].kind, ChangeOpKind::Attach);
    assert!(
        r138.refusals.is_empty(),
        "138-FZ refusals: {:?}",
        r138.refusals
    );

    let p484_lines = extract_paras(&p484);
    let p484_refs: Vec<&str> = p484_lines.iter().map(String::as_str).collect();
    let r484 = parse_amending_blocks(&p484_refs);
    eprintln!(
        "[smoke 484-FZ] candidates={} refusals={} editorial_skipped={}",
        r484.candidates.len(),
        r484.refusals.len(),
        r484.editorial_notes_skipped
    );
    assert!(
        r484.candidates.len() >= 25,
        "expected >=25 real parsed operations on 484-FZ, got {}",
        r484.candidates.len()
    );
    // INV-01 determinism: second parse is byte-for-byte identical.
    assert_eq!(r484, parse_amending_blocks(&p484_refs));
}
