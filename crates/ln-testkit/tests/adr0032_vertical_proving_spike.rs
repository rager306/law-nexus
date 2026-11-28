//! ADR-0032 D4 End-to-End Vertical Proving Spike:
//! `AmendingAct text -> ChangeGrammar (ln-decode) -> MicroOperation -> CompilerFold (ln-temporal) -> EditionOracle`
//!
//! Proves:
//! 1. Offline always-run vertical chain on real 44-ФЗ + 484-ФЗ + 138-ФЗ clause patterns
//!    with `INV-01` (identical SHA-256 `root_hash`), `INV-04` (future effects excluded),
//!    `INV-05` (bitemporal `known_as_of` cutoff), `INV-06` (source mentions preserved),
//!    and `INV-10` (typed `MC-RES` refusals);
//! 2. Offline synthetic non-44-ФЗ control act (`402-ФЗ О бухгалтерском учете` shape)
//!    proving zero 44-ФЗ hardcoding, `MC-SEED` (`NotYetInForce` on `Attach`), and
//!    four-axis `MC-REPEAL` (a bounded offline control, not yet a real multi-edition corpus pair);
//! 3. Skip-capable `[smoke]` real-corpus verification over `consru_export`
//!    (`edition-0112` + `484-ФЗ` -> `1 matched (drift = 0 on ст. 3 ч. 1 п. 8)` +
//!    `1 honest TextMismatch on п. 8.1` surfacing a parallel same-day amending act).

use ln_decode::change_grammar::{
    ChangeClauseCandidate, ChangeOpKind, ChangePositionParam, parse_amending_blocks,
};
use ln_temporal::amendment_compiler::{
    ApplyOutcome, AssertionFoldStatus, BaseComponent, COMPILER_FOLD_NON_CLAIMS,
    CompilerMicroOperation, DiscrepancyKind, EditorialPresence, MicroOperationKind,
    OracleComponentExpectation, TextAnchorMode, TextAvailability, compile_at,
    verify_against_edition_oracle,
};
use ln_temporal::domain::NormativeState;

fn map_candidate_to_op(
    idx: usize,
    act_id: &str,
    cand: &ChangeClauseCandidate,
    legal_effective_day: i64,
    recorded_day: i64,
    status: AssertionFoldStatus,
) -> CompilerMicroOperation {
    let kind = match cand.kind {
        ChangeOpKind::ReplaceText => MicroOperationKind::ReplaceText,
        ChangeOpKind::InsertText => MicroOperationKind::InsertText,
        ChangeOpKind::DeleteText => MicroOperationKind::DeleteText,
        ChangeOpKind::Attach => MicroOperationKind::Attach,
        ChangeOpKind::Repeal => MicroOperationKind::Repeal,
    };
    let anchor_mode = match cand.param {
        ChangePositionParam::WholeComponent | ChangePositionParam::NewComponent => {
            TextAnchorMode::WholeComponent
        }
        ChangePositionParam::ExactAnchor => TextAnchorMode::ExactAnchor,
        ChangePositionParam::AfterAnchor => TextAnchorMode::AfterAnchor,
        ChangePositionParam::BeforeAnchor => TextAnchorMode::BeforeAnchor,
        ChangePositionParam::EndOfComponent => TextAnchorMode::EndOfComponent,
    };
    CompilerMicroOperation {
        op_id: format!("{act_id}:op-{idx:03}"),
        amending_act_id: act_id.to_owned(),
        target_locator: cand.target_locator.canonical_path(),
        kind,
        anchor_mode,
        loc_value: cand.loc_value.clone(),
        value: cand.value.clone(),
        legal_effective_day,
        recorded_day,
        assertion_status: status,
    }
}

#[test]
fn vertical_spike_44fz_484fz_and_138fz_proves_zero_drift_and_invariants() {
    let base = vec![
        BaseComponent {
            locator: "statya-3/chast-1/punkt-8".to_owned(),
            text: "8) государственный контракт, муниципальный контракт - гражданско-правовой договор, предметом которого являются поставка товара, выполнение работы, оказание услуги;".to_owned(),
            force_status: NormativeState::InForce,
            preserved_mentions: vec!["mention:base-st3-p8".to_owned()],
        },
        BaseComponent {
            locator: "statya-3/chast-1/punkt-8.1".to_owned(),
            text: "8.1) контракт - гражданско-правовой договор, предметом которого являются поставка товара, выполнение работы, оказание услуги;".to_owned(),
            force_status: NormativeState::InForce,
            preserved_mentions: vec!["mention:base-st3-p8.1".to_owned()],
        },
        BaseComponent {
            locator: "statya-31/chast-9".to_owned(),
            text: "9. Отстранение участника закупки осуществляется в любой момент до заключения контракта.".to_owned(),
            force_status: NormativeState::InForce,
            preserved_mentions: vec!["mention:base-st31-ch9".to_owned()],
        },
    ];

    let fz484_blocks = [
        "Статья 1",
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ \"О контрактной системе\" следующие изменения:",
        "1) в части 1 статьи 3:",
        "а) пункт 8 после слов \"гражданско-правовой договор,\" дополнить словами \"который заключен в письменной форме и\";",
        "б) пункт 8.1 после слов \"гражданско-правовой договор,\" дополнить словами \"который заключен в письменной форме и\";",
    ];
    let fz138_blocks = [
        "Статья 1",
        "Внести в Федеральный закон от 5 апреля 2013 года N 44-ФЗ \"О контрактной системе\" следующие изменения:",
        "1) часть 9 статьи 31 изложить в следующей редакции:",
        "\"9. Комиссия по осуществлению закупок обязана отстранить участника закупки не позднее даты подведения итогов.\";",
        "2) статью 43 дополнить частью 12 следующего содержания:",
        "\"12. Ответственность за недостоверность информации несет участник закупки.\".",
    ];

    let r484 = parse_amending_blocks(&fz484_blocks);
    assert_eq!(r484.candidates.len(), 2);
    assert!(r484.refusals.is_empty());

    let r138 = parse_amending_blocks(&fz138_blocks);
    assert_eq!(r138.candidates.len(), 2);
    assert!(r138.refusals.is_empty());

    let mut ops: Vec<CompilerMicroOperation> = r484
        .candidates
        .iter()
        .enumerate()
        .map(|(i, c)| {
            map_candidate_to_op(
                i,
                "484-fz",
                c,
                20241226,
                20241227,
                AssertionFoldStatus::AuthoritativeInternal,
            )
        })
        .collect();
    ops.extend(r138.candidates.iter().enumerate().map(|(i, c)| {
        map_candidate_to_op(
            i,
            "138-fz",
            c,
            20260101,
            20250610,
            AssertionFoldStatus::Validated,
        )
    }));
    // Unadmitted Proposed operation MUST be excluded from fold!
    ops.push(CompilerMicroOperation {
        op_id: "unadmitted:op-999".to_owned(),
        amending_act_id: "draft-fz".to_owned(),
        target_locator: "statya-31/chast-9".to_owned(),
        kind: MicroOperationKind::Repeal,
        anchor_mode: TextAnchorMode::WholeComponent,
        loc_value: None,
        value: None,
        legal_effective_day: 20241226,
        recorded_day: 20241226,
        assertion_status: AssertionFoldStatus::Proposed,
    });

    // Horizon 1: legal_as_of = 2024-12-26, known_as_of = 2025-12-31
    let snap_2024 = compile_at(&base, &ops, 20241226, 20251231);
    assert_eq!(snap_2024.non_claims, COMPILER_FOLD_NON_CLAIMS);
    assert_eq!(snap_2024.excluded_future_count, 2);
    assert_eq!(snap_2024.excluded_unadmitted_count, 1);
    assert_eq!(snap_2024.audit.len(), 2);
    assert!(
        snap_2024
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::Applied)
    );

    // INV-01 & INV-02: reversed input slice yields identical SHA-256 root_hash.
    let mut reversed_ops = ops.clone();
    reversed_ops.reverse();
    let snap_2024_reversed = compile_at(&base, &reversed_ops, 20241226, 20251231);
    assert_eq!(snap_2024.root_hash, snap_2024_reversed.root_hash);

    // INV-05: earlier known_as_of (2024-12-26, before 484-ФЗ was recorded on 2024-12-27)
    let snap_before_record = compile_at(&base, &ops, 20241226, 20241226);
    assert_eq!(snap_before_record.excluded_unrecorded_count, 4);
    assert!(snap_before_record.audit.is_empty());

    // INV-06: source mentions remain untouched after target text compilation.
    assert_eq!(
        snap_2024.components["statya-3/chast-1/punkt-8"].preserved_mentions,
        vec!["mention:base-st3-p8"]
    );

    let oracle_2024 = vec![
        OracleComponentExpectation {
            locator: "statya-3/chast-1/punkt-8".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("8) государственный контракт, муниципальный контракт - гражданско-правовой договор, который заключен в письменной форме и предметом которого являются поставка товара, выполнение работы, оказание услуги;".to_owned()),
        },
        OracleComponentExpectation {
            locator: "statya-3/chast-1/punkt-8.1".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("8.1) контракт - гражданско-правовой договор, который заключен в письменной форме и предметом которого являются поставка товара, выполнение работы, оказание услуги;".to_owned()),
        },
        OracleComponentExpectation {
            locator: "statya-31/chast-9".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("9. Отстранение участника закупки осуществляется в любой момент до заключения контракта.".to_owned()),
        },
    ];
    let ver_2024 = verify_against_edition_oracle(&snap_2024, &oracle_2024);
    assert_eq!(ver_2024.non_claims, COMPILER_FOLD_NON_CLAIMS);
    assert_eq!(
        ver_2024.drift_count, 0,
        "discrepancies: {:?}",
        ver_2024.discrepancies
    );
    assert_eq!(ver_2024.matched_count, 3);

    // Horizon 2: legal_as_of = 2026-01-01, known_as_of = 2026-01-01
    let snap_2026 = compile_at(&base, &ops, 20260101, 20260101);
    assert_eq!(snap_2026.excluded_future_count, 0);
    assert_eq!(snap_2026.audit.len(), 4);
    assert_eq!(
        snap_2026.components["statya-43/chast-12"].force_status,
        NormativeState::NotYetInForce
    );
    let oracle_2026 = vec![
        OracleComponentExpectation {
            locator: "statya-31/chast-9".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("9. Комиссия по осуществлению закупок обязана отстранить участника закупки не позднее даты подведения итогов.".to_owned()),
        },
        OracleComponentExpectation {
            locator: "statya-43/chast-12".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("12. Ответственность за недостоверность информации несет участник закупки.".to_owned()),
        },
    ];
    let ver_2026 = verify_against_edition_oracle(&snap_2026, &oracle_2026);
    assert_eq!(
        ver_2026.drift_count, 0,
        "discrepancies: {:?}",
        ver_2026.discrepancies
    );
    assert_eq!(ver_2026.matched_count, 2);
}

#[test]
fn vertical_spike_synthetic_non_44fz_control_act_proves_delete_repeal_four_axes() {
    // Offline synthetic non-44-ФЗ control act (`402-ФЗ` shape, not real multi-edition files).
    let base = vec![
        BaseComponent {
            locator: "statya-7/chast-2".to_owned(),
            text: "2. Руководитель экономического субъекта обязан организовать ведение учета иных документов и отчетности.".to_owned(),
            force_status: NormativeState::InForce,
            preserved_mentions: vec!["mention:402-st7-ch2".to_owned()],
        },
        BaseComponent {
            locator: "statya-9/punkt-3".to_owned(),
            text: "3. Первичный учетный документ должен быть составлен при совершении факта хозяйственной жизни.".to_owned(),
            force_status: NormativeState::InForce,
            preserved_mentions: vec!["mention:402-st9-p3".to_owned()],
        },
    ];

    let amending = [
        "Статья 1",
        "Внести в Федеральный закон от 6 декабря 2011 года N 402-ФЗ \"О бухгалтерском учете\" следующие изменения:",
        "1) в части 2 статьи 7 слова \"иных документов \" исключить;",
        "2) пункт 3 статьи 9 признать утратившим силу.",
    ];
    let parsed = parse_amending_blocks(&amending);
    assert_eq!(parsed.candidates.len(), 2);
    assert!(parsed.refusals.is_empty());

    let mut ops: Vec<CompilerMicroOperation> = parsed
        .candidates
        .iter()
        .enumerate()
        .map(|(i, c)| {
            map_candidate_to_op(
                i,
                "control-amend-fz",
                c,
                20250301,
                20250301,
                AssertionFoldStatus::AuthoritativeInternal,
            )
        })
        .collect();

    ops.push(CompilerMicroOperation {
        op_id: "control-amend-fz:op-missing-anchor".to_owned(),
        amending_act_id: "control-amend-fz".to_owned(),
        target_locator: "statya-7/chast-2".to_owned(),
        kind: MicroOperationKind::ReplaceText,
        anchor_mode: TextAnchorMode::ExactAnchor,
        loc_value: Some("несуществующая фраза".to_owned()),
        value: Some("замена".to_owned()),
        legal_effective_day: 20250301,
        recorded_day: 20250301,
        assertion_status: AssertionFoldStatus::AuthoritativeInternal,
    });

    let snap = compile_at(&base, &ops, 20250301, 20250301);
    let outcome_of = |id: &str| {
        snap.audit
            .iter()
            .find(|a| a.op_id == id)
            .expect("audit entry")
            .outcome
    };
    assert_eq!(outcome_of("control-amend-fz:op-000"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("control-amend-fz:op-001"), ApplyOutcome::Applied);
    assert_eq!(
        outcome_of("control-amend-fz:op-missing-anchor"),
        ApplyOutcome::PreconditionMismatch
    );

    let repealed = &snap.components["statya-9/punkt-3"];
    assert_eq!(repealed.force_status, NormativeState::Repealed);
    assert!(!repealed.structural_membership);
    assert_eq!(repealed.editorial_presence, EditorialPresence::Tombstone);
    assert_eq!(repealed.text_availability, TextAvailability::HistoricalOnly);
    assert_eq!(
        repealed.text,
        "3. Первичный учетный документ должен быть составлен при совершении факта хозяйственной жизни."
    );

    let oracle = vec![
        OracleComponentExpectation {
            locator: "statya-7/chast-2".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("2. Руководитель экономического субъекта обязан организовать ведение учета и отчетности.".to_owned()),
        },
        OracleComponentExpectation {
            locator: "statya-9/punkt-3".to_owned(),
            expected_presence: EditorialPresence::Tombstone,
            expected_text: Some("3. Первичный учетный документ должен быть составлен при совершении факта хозяйственной жизни.".to_owned()),
        },
    ];
    let report = verify_against_edition_oracle(&snap, &oracle);
    assert_eq!(
        report.drift_count, 0,
        "discrepancies: {:?}",
        report.discrepancies
    );
    assert_eq!(report.matched_count, 2);
}

#[test]
fn smoke_real_consru_export_ed112_plus_484fz_proves_p8_zero_drift_and_p81_discrepancy() {
    use ln_decode::adapters::ConsultantWordMlBlockDecoder;
    use ln_decode::domain::{DecodeRequest, FamilyFormat, PayloadRef};
    use ln_decode::ports::BlockDecoderPort;

    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let p_ed112 = root.join(
        "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0112_rev-2024-11-30_from-unknown_28bc016d.xml",
    );
    let p_ed113 = root.join(
        "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0113_rev-2024-12-26_from-unknown_03bd934e.xml",
    );
    let p_484 = root.join(
        "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml",
    );
    if !p_ed112.exists() || !p_ed113.exists() || !p_484.exists() {
        eprintln!("SKIP [smoke]: consru_export 44-FZ ed112/ed113 or 484-FZ not present");
        return;
    }

    let decode_lines = |path: &std::path::Path| -> Vec<String> {
        let bytes = std::fs::read(path).expect("read xml");
        let req = DecodeRequest::new(
            PayloadRef::parse("payload:adr0032-spike-smoke").expect("payload"),
            FamilyFormat::parse("family:consultant-wordml").expect("format"),
            &bytes,
        );
        ConsultantWordMlBlockDecoder
            .decode_blocks(&req)
            .expect("decode")
            .into_iter()
            .map(|b| b.text().to_owned())
            .collect()
    };

    let ed112_lines = decode_lines(&p_ed112);
    let ed113_lines = decode_lines(&p_ed113);
    let fz484_lines = decode_lines(&p_484);

    let find_para = |lines: &[String], prefix: &str| -> String {
        lines
            .iter()
            .find(|l| {
                l.trim_start().starts_with(prefix) && l.contains("гражданско-правовой договор,")
            })
            .unwrap_or_else(|| panic!("expected paragraph starting with '{prefix}'"))
            .clone()
    };

    let ed112_p8 = find_para(&ed112_lines, "8) государственный контракт");
    let ed112_p81 = find_para(&ed112_lines, "8.1) контракт -");
    let ed113_p8 = find_para(&ed113_lines, "8) государственный контракт");
    let ed113_p81 = find_para(&ed113_lines, "8.1) контракт -");

    let fz484_refs: Vec<&str> = fz484_lines.iter().map(String::as_str).collect();
    let parsed = parse_amending_blocks(&fz484_refs);
    let scoped_ops: Vec<CompilerMicroOperation> = parsed
        .candidates
        .iter()
        .enumerate()
        .filter(|(_, c)| {
            matches!(
                c.target_locator.canonical_path().as_str(),
                "statya-3/chast-1/punkt-8" | "statya-3/chast-1/punkt-8.1"
            )
        })
        .map(|(i, c)| {
            map_candidate_to_op(
                i,
                "484-fz-real",
                c,
                20241226,
                20241226,
                AssertionFoldStatus::AuthoritativeInternal,
            )
        })
        .collect();
    assert_eq!(scoped_ops.len(), 2);

    let base = vec![
        BaseComponent {
            locator: "statya-3/chast-1/punkt-8".to_owned(),
            text: ed112_p8,
            force_status: NormativeState::InForce,
            preserved_mentions: Vec::new(),
        },
        BaseComponent {
            locator: "statya-3/chast-1/punkt-8.1".to_owned(),
            text: ed112_p81,
            force_status: NormativeState::InForce,
            preserved_mentions: Vec::new(),
        },
    ];

    let compiled = compile_at(&base, &scoped_ops, 20241226, 20241226);
    assert!(
        compiled
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::Applied)
    );

    let strip_editorial_tag = |s: &str| -> String {
        if let Some(pos) = s.find("(в ред. Федерального закона") {
            s[..pos].trim().to_owned()
        } else {
            s.trim().to_owned()
        }
    };

    let oracle = vec![
        OracleComponentExpectation {
            locator: "statya-3/chast-1/punkt-8".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some(strip_editorial_tag(&ed113_p8)),
        },
        OracleComponentExpectation {
            locator: "statya-3/chast-1/punkt-8.1".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some(strip_editorial_tag(&ed113_p81)),
        },
    ];

    let report = verify_against_edition_oracle(&compiled, &oracle);
    eprintln!(
        "[smoke real 44-FZ ed112 + 484-FZ -> ed113] matched={}/{} drift={} root_hash={}",
        report.matched_count, report.checked_count, report.drift_count, compiled.root_hash
    );

    // 1. statya-3/chast-1/punkt-8 matches real edition-0113 with ZERO drift.
    assert_eq!(report.matched_count, 1);
    assert!(
        !report
            .discrepancies
            .iter()
            .any(|d| d.locator == "statya-3/chast-1/punkt-8")
    );

    // 2. statya-3/chast-1/punkt-8.1 applies 484-FZ insertion AND honestly reports
    //    the missing parallel amendment (`4, 4.1, 4.3 и 5` vs `4, 4.3 и 4.4`) as TextMismatch.
    assert!(
        compiled.components["statya-3/chast-1/punkt-8.1"]
            .text
            .contains("гражданско-правовой договор, который заключен в письменной форме и")
    );
    assert_eq!(report.drift_count, 1);
    assert_eq!(
        report.discrepancies[0].locator,
        "statya-3/chast-1/punkt-8.1"
    );
    assert_eq!(report.discrepancies[0].kind, DiscrepancyKind::TextMismatch);
}
