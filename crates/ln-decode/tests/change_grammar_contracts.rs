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

    // Additional real amending statutes from consru_export:
    // - 333-FZ (header-scoped `часть 1 статьи 95`: 4/4 operations, 0 refusals)
    // - 432-FZ (header-scoped `статья 112`: 2/2 operations, 0 refusals)
    // - 124-FZ (multi-op with WholeComponent, ExactAnchor, Attach, and 2 Repeals: 0 refusals)
    // - 494-FZ (multi-act law amending Land Code, 29-FZ, Urban Planning Code, 44-FZ)
    let p333 = root.join(
        "consru_export/consru_export/exports/npa/law_2025-07-31_333-fz_rev-unknown_de3ad12f.xml",
    );
    let p432 = root.join(
        "consru_export/consru_export/exports/npa/law_2024-11-30_432-fz_rev-unknown_67ced536.xml",
    );
    let p124 = root.join(
        "consru_export/consru_export/exports/npa/law_2024-05-29_124-fz_rev-unknown_13541fea.xml",
    );
    let p494 = root.join(
        "consru_export/consru_export/exports/npa/law_2024-12-26_494-fz_rev-unknown_5c5ff12e.xml",
    );
    if p333.exists() && p432.exists() && p124.exists() && p494.exists() {
        let p333_lines = extract_paras(&p333);
        let p333_refs: Vec<&str> = p333_lines.iter().map(String::as_str).collect();
        let r333 = parse_amending_blocks(&p333_refs);
        assert_eq!(r333.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);
        assert!(
            r333.refusals.is_empty(),
            "333-FZ refusals: {:?}",
            r333.refusals
        );
        assert_eq!(r333.candidates.len(), 4);
        assert_eq!(
            r333.candidates
                .iter()
                .map(|c| c.target_locator.canonical_path())
                .collect::<Vec<_>>(),
            vec![
                "statya-95/chast-1/punkt-1.2",
                "statya-95/chast-1/punkt-1.3",
                "statya-95/chast-1/punkt-10",
                "statya-95/chast-1/punkt-14",
            ]
        );
        assert_eq!(r333.candidates[3].kind, ChangeOpKind::Attach);

        let p432_lines = extract_paras(&p432);
        let p432_refs: Vec<&str> = p432_lines.iter().map(String::as_str).collect();
        let r432 = parse_amending_blocks(&p432_refs);
        assert_eq!(r432.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);
        assert!(
            r432.refusals.is_empty(),
            "432-FZ refusals: {:?}",
            r432.refusals
        );
        assert_eq!(r432.candidates.len(), 2);
        assert_eq!(
            r432.candidates
                .iter()
                .map(|c| c.target_locator.canonical_path())
                .collect::<Vec<_>>(),
            vec!["statya-112/chast-66", "statya-112/chast-67"]
        );

        let p124_lines = extract_paras(&p124);
        let p124_refs: Vec<&str> = p124_lines.iter().map(String::as_str).collect();
        let r124 = parse_amending_blocks(&p124_refs);
        assert_eq!(r124.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);
        assert!(
            r124.refusals.is_empty(),
            "124-FZ refusals: {:?}",
            r124.refusals
        );
        assert_eq!(r124.candidates.len(), 9);
        assert_eq!(
            r124.candidates
                .iter()
                .filter(|c| c.kind == ChangeOpKind::Repeal)
                .count(),
            2
        );

        let p494_lines = extract_paras(&p494);
        let p494_refs: Vec<&str> = p494_lines.iter().map(String::as_str).collect();
        let r494 = parse_amending_blocks(&p494_refs);
        assert_eq!(r494.non_claims, CHANGE_GRAMMAR_NON_CLAIMS);
        eprintln!(
            "[smoke multi-act] 333-FZ={}/{} 432-FZ={}/{} 124-FZ={}/{} 494-FZ={}/{}",
            r333.candidates.len(),
            r333.refusals.len(),
            r432.candidates.len(),
            r432.refusals.len(),
            r124.candidates.len(),
            r124.refusals.len(),
            r494.candidates.len(),
            r494.refusals.len()
        );
        assert!(r494.candidates.len() >= 20);
        // Header-scoped 29-FZ Article 3 (`пункт 3 статьи 4` -> `абзац 2` & `абзац 3`)
        assert!(r494.candidates.iter().any(|c| {
            c.owner_act.number.as_deref() == Some("29-ФЗ")
                && c.target_locator.canonical_path() == "statya-4/punkt-3/abzats-2"
        }));
        assert_eq!(r494, parse_amending_blocks(&p494_refs));
    } else {
        eprintln!("SKIP [smoke]: consru_export 333-FZ/432-FZ/124-FZ/494-FZ not all present");
    }
}

#[test]
fn parses_nested_ascii_quotes_code_parts_fkz_and_refuses_hostile_edges_fail_closed() {
    // 1. Valid nested ASCII quotes in both `loc_value` and `value`, inline
    //    `дополнить предложением следующего содержания: "..."`, and `, а ` conjunction.
    let valid_blocks = [
        "Статья 1",
        "Внести изменения в статью 217 части второй Налогового кодекса Российской Федерации следующие изменения:",
        "1) в пункте 1 слова \"пунктами 2, 3, 4,\" заменить словами \"подпунктами \"в\" - \"д\" пункта 5, пунктами\";",
        "2) в пункте 2 слова \"подпунктом \"а\" части 1\" заменить словами \"подпунктами \"а\" и \"б\" пункта 5\", а слова \"устаревшее\" исключить;",
        "3) пункт 3 дополнить предложением следующего содержания: \"Новое предложение.\";",
        "Статья 2",
        "1. Внести в часть первую Гражданского кодекса Российской Федерации следующие изменения:",
        "1) в пункте 1 статьи 10 слово \"а\" заменить словом \"б\";",
        "2) слово \"а\" заменить словом \"б\";",
        "Статья 3",
        "Внести в Федеральный конституционный закон от 31 декабря 1996 года N 1-ФКЗ \"О судебной системе\" (Собрание законодательства Российской Федерации, 1997, N 1, ст. 1; в редакции Указа Президента) следующие изменения:",
        "1) в статье 4 слово \"суд\" заменить словом \"орган\";",
        "2) слово \"указанных\" заменить словом \"иных\";",
    ];
    let r_valid = parse_amending_blocks(&valid_blocks);
    assert_eq!(r_valid.candidates.len(), 6);
    // Code Part `части второй` stripped -> `statya-217/punkt-1`, NOT `statya-217/chast-2/punkt-1`!
    assert_eq!(
        r_valid.candidates[0].target_locator.canonical_path(),
        "statya-217/punkt-1"
    );
    assert_eq!(
        r_valid.candidates[0].value.as_deref(),
        Some("подпунктами \"в\" - \"д\" пункта 5, пунктами")
    );
    assert_eq!(
        r_valid.candidates[1].loc_value.as_deref(),
        Some("подпунктом \"а\" части 1")
    );
    assert_eq!(
        r_valid.candidates[1].value.as_deref(),
        Some("подпунктами \"а\" и \"б\" пункта 5")
    );
    assert_eq!(r_valid.candidates[2].kind, ChangeOpKind::DeleteText);
    assert_eq!(
        r_valid.candidates[3].param,
        ChangePositionParam::EndOfComponent
    );
    assert_eq!(
        r_valid.candidates[3].value.as_deref(),
        Some("Новое предложение.")
    );
    // Code Part `часть первую ГК РФ` yields empty act_scope -> clause 1 targets statya-10/punkt-1,
    // clause 2 without article fails closed as AmbiguousTarget (never bogus `chast-1`)!
    assert_eq!(
        r_valid.candidates[4].target_locator.canonical_path(),
        "statya-10/punkt-1"
    );
    // FKZ header with `(СЗ РФ ... ст. 1; в редакции Указа ...)` never extracts `statya-1`!
    assert_eq!(
        r_valid.candidates[5].target_locator.canonical_path(),
        "statya-4"
    );
    assert_eq!(r_valid.refusals.len(), 2);
    assert!(
        r_valid
            .refusals
            .iter()
            .all(|r| matches!(r, ChangeParseRefusal::AmbiguousTarget { .. }))
    );

    // 2. Hostile fail-closed cases:
    //    - Unclosed nested ASCII quotes in loc_value & value -> IncompleteSource (0 corrupted candidates)
    //    - Refused container header under header-scoped act poisons children -> AmbiguousTarget
    //    - Compound clause ending with next-line `дополнить предложением следующего содержания:` -> UnsupportedOperation
    //    - Coordinated plurals: `подпункта "а", "б"`, `подпункта «а» и «б»`, `в абзаце первом и втором` -> AmbiguousTarget
    let hostile = [
        "Статья 1",
        "Внести в статью 112 Федерального закона от 5 апреля 2013 года N 44-ФЗ следующие изменения:",
        "1) в части 1 слова \"подпунктами \"а\" заменить словом \"в\";",
        "2) в части 2 слово \"х\" заменить словами \"подпунктом \"а\";",
        "3) в наименовании:",
        "а) слово \"х\" заменить словом \"у\";",
        "4) в части 3 слово \"а\" заменить словом \"б\" и дополнить предложением следующего содержания:",
        "\"Дополнительное предложение.\";",
        "5) в подпункте \"а\", \"б\" части 4 слово \"а\" заменить словом \"б\";",
        "6) в подпункте «а» и «б» части 4 слово \"а\" заменить словом \"б\";",
        "7) в абзаце первом и втором части 4 слово \"а\" заменить словом \"б\";",
        "8) в части 5 слово \"да\" заменить словом \"нет\";",
    ];
    let r_hostile = parse_amending_blocks(&hostile);
    // Only clause 8) is clean — all 7 hostile/poisoned clauses MUST fail closed!
    assert_eq!(r_hostile.candidates.len(), 1);
    assert_eq!(
        r_hostile.candidates[0].target_locator.canonical_path(),
        "statya-112/chast-5"
    );
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::IncompleteSource { block_index: 2, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::IncompleteSource { block_index: 3, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 4, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 5, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::UnsupportedOperation { block_index: 6, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 8, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget { block_index: 9, .. }
    )));
    assert!(r_hostile.refusals.iter().any(|r| matches!(
        r,
        ChangeParseRefusal::AmbiguousTarget {
            block_index: 10,
            ..
        }
    )));
}

#[test]
fn parses_header_scoped_act_headers_next_line_sentence_append_and_conjunction_chains() {
    let blocks = [
        "Статья 1",
        "Внести в часть 1 статьи 95 Федерального закона от 5 апреля 2013 года N 44-ФЗ следующие изменения:",
        "1) пункт 1.2 после слова \"строительства,\" дополнить словами \"благоустройству территории,\";",
        "2) дополнить пунктом 14 следующего содержания:",
        "\"14) новый пункт.\";",
        "3) в пункте 10 слово \"три\" заменить словом \"шесть\" и после цифры \"3,\" дополнить цифрой \"6,\";",
        "4) пункт 11 дополнить предложением следующего содержания:",
        "\"Дополнительное предложение в конце пункта.\";",
        "Статья 2",
        "Внести в статьи 31 и 43 Федерального закона от 5 апреля 2013 года N 44-ФЗ следующие изменения:",
        "1) слово \"а\" заменить словом \"б\";",
        "2) в части 1 статьи 31 слово \"а\" заменить словом \"б\";",
    ];

    let report = parse_amending_blocks(&blocks);
    assert_eq!(report.candidates.len(), 6);
    assert_eq!(
        report.candidates[0].target_locator.canonical_path(),
        "statya-95/chast-1/punkt-1.2"
    );
    assert_eq!(
        report.candidates[1].target_locator.canonical_path(),
        "statya-95/chast-1/punkt-14"
    );
    assert_eq!(report.candidates[1].kind, ChangeOpKind::Attach);
    // Chained `и` conjunction emits two candidates on the same locator.
    assert_eq!(
        report.candidates[2].target_locator.canonical_path(),
        "statya-95/chast-1/punkt-10"
    );
    assert_eq!(report.candidates[2].kind, ChangeOpKind::ReplaceText);
    assert_eq!(
        report.candidates[3].target_locator.canonical_path(),
        "statya-95/chast-1/punkt-10"
    );
    assert_eq!(report.candidates[3].kind, ChangeOpKind::InsertText);
    // Next-line `дополнить предложением следующего содержания:` emits EndOfComponent.
    assert_eq!(
        report.candidates[4].target_locator.canonical_path(),
        "statya-95/chast-1/punkt-11"
    );
    assert_eq!(report.candidates[4].kind, ChangeOpKind::InsertText);
    assert_eq!(
        report.candidates[4].param,
        ChangePositionParam::EndOfComponent
    );
    assert_eq!(
        report.candidates[4].value.as_deref(),
        Some("Дополнительное предложение в конце пункта.")
    );
    // Plural header `Внести в статьи 31 и 43 ...:` refuses targetless clause 1) fail-closed
    // while allowing explicit target in clause 2).
    assert_eq!(
        report.candidates[5].target_locator.canonical_path(),
        "statya-31/chast-1"
    );
    assert_eq!(report.refusals.len(), 1);
    assert!(matches!(
        report.refusals[0],
        ChangeParseRefusal::AmbiguousTarget {
            block_index: 10,
            ..
        }
    ));
}
