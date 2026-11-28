//! Exhaustive offline contracts for `ln_temporal::amendment_compiler`:
//! covers every `ApplyOutcome`, `TextAnchorMode`, `DiscrepancyKind`,
//! `AssertionFoldStatus`, `INV-01/02/03/04/05/06/10`, `MC-REPEAL`, `MC-SEED`,
//! collision-free hashing, and local NBSP preservation.

use ln_temporal::amendment_compiler::{
    ApplyOutcome, AssertionFoldStatus, BaseComponent, COMPILER_FOLD_NON_CLAIMS,
    CompilerMicroOperation, DiscrepancyKind, EditorialPresence, MicroOperationKind,
    OracleComponentExpectation, TextAnchorMode, TextAvailability, compile_at,
    verify_against_edition_oracle,
};
use ln_temporal::domain::NormativeState;

fn base(locator: &str, text: &str) -> BaseComponent {
    BaseComponent {
        locator: locator.to_owned(),
        text: text.to_owned(),
        force_status: NormativeState::InForce,
        preserved_mentions: vec![format!("mention:{locator}")],
    }
}

fn op(
    op_id: &str,
    act: &str,
    locator: &str,
    kind: MicroOperationKind,
    anchor_mode: TextAnchorMode,
    loc_value: Option<&str>,
    value: Option<&str>,
) -> CompilerMicroOperation {
    CompilerMicroOperation {
        op_id: op_id.to_owned(),
        amending_act_id: act.to_owned(),
        target_locator: locator.to_owned(),
        kind,
        anchor_mode,
        loc_value: loc_value.map(str::to_owned),
        value: value.map(str::to_owned),
        legal_effective_day: 20250101,
        recorded_day: 20250101,
        assertion_status: AssertionFoldStatus::AuthoritativeInternal,
    }
}

#[test]
fn covers_before_anchor_end_of_component_delete_nbsp_and_tombstone_attach_guard() {
    let seeds = vec![
        base("st-1/p-1", "Срок 10\u{00a0}дней и иных документов."),
        base("st-1/p-2", ""),
        base("st-1/p-3", "Норма действует."),
    ];

    let ops = vec![
        // BeforeAnchor
        op(
            "op-1",
            "act-1",
            "st-1/p-1",
            MicroOperationKind::InsertText,
            TextAnchorMode::BeforeAnchor,
            Some("10"),
            Some("до"),
        ),
        // DeleteText preserving untouched NBSP `\u{00a0}`!
        op(
            "op-2",
            "act-1",
            "st-1/p-1",
            MicroOperationKind::DeleteText,
            TextAnchorMode::ExactAnchor,
            Some(" и иных документов"),
            None,
        ),
        // EndOfComponent on component with trailing `.` and insert_val without `.`
        op(
            "op-3",
            "act-1",
            "st-1/p-1",
            MicroOperationKind::InsertText,
            TextAnchorMode::EndOfComponent,
            None,
            Some("включительно"),
        ),
        // EndOfComponent on empty base does not prepend leading space
        op(
            "op-4",
            "act-1",
            "st-1/p-2",
            MicroOperationKind::InsertText,
            TextAnchorMode::EndOfComponent,
            None,
            Some("Текст."),
        ),
        // Repeal st-1/p-3 then attempt Attach onto tombstone -> PreconditionMismatch!
        op(
            "op-5",
            "act-1",
            "st-1/p-3",
            MicroOperationKind::Repeal,
            TextAnchorMode::WholeComponent,
            None,
            None,
        ),
        CompilerMicroOperation {
            legal_effective_day: 20250102,
            recorded_day: 20250102,
            ..op(
                "op-6",
                "act-2",
                "st-1/p-3",
                MicroOperationKind::Attach,
                TextAnchorMode::WholeComponent,
                None,
                Some("Попытка перезаписать tombstone"),
            )
        },
        // DeleteText / ReplaceText / InsertText / second Repeal on repealed component -> PreconditionMismatch
        CompilerMicroOperation {
            legal_effective_day: 20250103,
            recorded_day: 20250103,
            ..op(
                "op-7",
                "act-3",
                "st-1/p-3",
                MicroOperationKind::DeleteText,
                TextAnchorMode::ExactAnchor,
                Some("Норма"),
                None,
            )
        },
        // Attach on active component -> PreconditionMismatch
        CompilerMicroOperation {
            legal_effective_day: 20250104,
            recorded_day: 20250104,
            ..op(
                "op-8",
                "act-4",
                "st-1/p-1",
                MicroOperationKind::Attach,
                TextAnchorMode::WholeComponent,
                None,
                Some("Дубль"),
            )
        },
    ];

    let snap = compile_at(&seeds, &ops, 20250110, 20250110);
    assert_eq!(snap.non_claims, COMPILER_FOLD_NON_CLAIMS);
    assert_eq!(
        snap.components["st-1/p-1"].text,
        "Срок до 10\u{00a0}дней включительно."
    );
    assert_eq!(snap.components["st-1/p-2"].text, "Текст.");
    // Tombstone preserved with original text and preserved_mentions intact!
    assert_eq!(snap.components["st-1/p-3"].text, "Норма действует.");
    assert_eq!(
        snap.components["st-1/p-3"].preserved_mentions,
        vec!["mention:st-1/p-3"]
    );
    assert_eq!(
        snap.components["st-1/p-3"].editorial_presence,
        EditorialPresence::Tombstone
    );
    assert_eq!(
        snap.components["st-1/p-3"].text_availability,
        TextAvailability::HistoricalOnly
    );

    let outcome_of = |id: &str| {
        snap.audit
            .iter()
            .find(|a| a.op_id == id)
            .expect("audit entry")
            .outcome
    };
    assert_eq!(outcome_of("op-1"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("op-2"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("op-3"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("op-4"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("op-5"), ApplyOutcome::Applied);
    assert_eq!(outcome_of("op-6"), ApplyOutcome::PreconditionMismatch);
    assert_eq!(outcome_of("op-7"), ApplyOutcome::PreconditionMismatch);
    assert_eq!(outcome_of("op-8"), ApplyOutcome::PreconditionMismatch);
}

#[test]
fn covers_all_typed_non_successes_ordering_conflict_and_inv02_permutation_invariance() {
    let seeds = vec![
        base("st-1", "слово и снова слово."),
        base("st-1", "дубль seed"),
        base("st-2", "текст второй статьи."),
    ];

    let ops = vec![
        // AmbiguousTarget (anchor appears twice)
        op(
            "op-ambig",
            "act-1",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("слово"),
            Some("термин"),
        ),
        // TargetNotFound
        op(
            "op-missing",
            "act-1",
            "st-999",
            MicroOperationKind::Repeal,
            TextAnchorMode::WholeComponent,
            None,
            None,
        ),
        // UnsupportedOperation (DeleteText with WholeComponent)
        op(
            "op-unsup",
            "act-1",
            "st-1",
            MicroOperationKind::DeleteText,
            TextAnchorMode::WholeComponent,
            Some("слово"),
            None,
        ),
        // IncompleteSource (empty locator)
        op(
            "op-empty-loc",
            "act-1",
            "  ",
            MicroOperationKind::Repeal,
            TextAnchorMode::WholeComponent,
            None,
            None,
        ),
        // INV-03 OrderingConflict: two distinct acts targeting st-2 on the same day!
        op(
            "op-conflict-a",
            "act-A",
            "st-2",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("второй"),
            Some("третьей"),
        ),
        op(
            "op-conflict-b",
            "act-B",
            "st-2",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("второй"),
            Some("четвертой"),
        ),
        // Excluded Rejected & Superseded assertions
        CompilerMicroOperation {
            assertion_status: AssertionFoldStatus::Rejected,
            ..op(
                "op-rej",
                "act-1",
                "st-1",
                MicroOperationKind::Repeal,
                TextAnchorMode::WholeComponent,
                None,
                None,
            )
        },
        CompilerMicroOperation {
            assertion_status: AssertionFoldStatus::Superseded,
            ..op(
                "op-sup",
                "act-1",
                "st-1",
                MicroOperationKind::Repeal,
                TextAnchorMode::WholeComponent,
                None,
                None,
            )
        },
    ];

    let snap = compile_at(&seeds, &ops, 20250101, 20250101);
    assert_eq!(snap.excluded_unadmitted_count, 2);
    // Duplicate base seed produced BaseVersionMismatch and did not overwrite st-1.
    assert!(
        snap.audit
            .iter()
            .any(|a| a.outcome == ApplyOutcome::BaseVersionMismatch)
    );
    assert_eq!(snap.components["st-1"].text, "слово и снова слово.");
    // Both conflicting cross-act ops on st-2 failed closed with OrderingConflict, leaving st-2 untouched!
    assert_eq!(snap.components["st-2"].text, "текст второй статьи.");
    let outcome_of = |id: &str| {
        snap.audit
            .iter()
            .find(|a| a.op_id == id)
            .expect("audit entry")
            .outcome
    };
    assert_eq!(outcome_of("op-ambig"), ApplyOutcome::AmbiguousTarget);
    assert_eq!(outcome_of("op-missing"), ApplyOutcome::TargetNotFound);
    assert_eq!(outcome_of("op-unsup"), ApplyOutcome::UnsupportedOperation);
    assert_eq!(outcome_of("op-empty-loc"), ApplyOutcome::IncompleteSource);
    assert_eq!(outcome_of("op-conflict-a"), ApplyOutcome::OrderingConflict);
    assert_eq!(outcome_of("op-conflict-b"), ApplyOutcome::OrderingConflict);

    // INV-02: Permuting independent operations yields identical root_hash!
    let ind_seeds = vec![base("st-1", "альфа."), base("st-2", "бета.")];
    let op_a = op(
        "op-a",
        "act-1",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("альфа"),
        Some("гамма"),
    );
    let op_b = op(
        "op-b",
        "act-2",
        "st-2",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("бета"),
        Some("дельта"),
    );
    let s1 = compile_at(
        &ind_seeds,
        &[op_a.clone(), op_b.clone()],
        20250101,
        20250101,
    );
    let s2 = compile_at(&ind_seeds, &[op_b, op_a], 20250101, 20250101);
    assert_eq!(s1.root_hash, s2.root_hash);
    assert_eq!(s1.components, s2.components);

    // Collision resistance + INV-06 mention hashing: changing delimiters or preserved_mentions MUST change root_hash.
    let h1 = compile_at(&[base("a", "b|c")], &[], 1, 1).root_hash;
    let h2 = compile_at(&[base("a|b", "c")], &[], 1, 1).root_hash;
    assert_ne!(
        h1, h2,
        "length-prefixed root_hash must prevent delimiter collisions"
    );

    let mut b_mut = base("a", "b");
    let hm1 = compile_at(std::slice::from_ref(&b_mut), &[], 1, 1).root_hash;
    b_mut.preserved_mentions.push("mention:extra".to_owned());
    let hm2 = compile_at(&[b_mut], &[], 1, 1).root_hash;
    assert_ne!(
        hm1, hm2,
        "INV-06: root_hash must commit to preserved_mentions"
    );
}

#[test]
fn covers_all_oracle_discrepancy_kinds_and_tombstone_absent_verification() {
    let seeds = vec![
        base("st-1", "Текст первый."),
        BaseComponent {
            locator: "st-2".to_owned(),
            text: "Утративший силу текст.".to_owned(),
            force_status: NormativeState::Repealed,
            preserved_mentions: Vec::new(),
        },
    ];
    let snap = compile_at(&seeds, &[], 20250101, 20250101);

    let oracle = vec![
        // MissingInCompiled
        OracleComponentExpectation {
            locator: "st-missing".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("Нет".to_owned()),
        },
        // MembershipMismatch (st-1 is Present, oracle expects Tombstone)
        OracleComponentExpectation {
            locator: "st-1".to_owned(),
            expected_presence: EditorialPresence::Tombstone,
            expected_text: None,
        },
        // Tombstone with None expected_text matches cleanly
        OracleComponentExpectation {
            locator: "st-2".to_owned(),
            expected_presence: EditorialPresence::Tombstone,
            expected_text: None,
        },
        // Absent missing component matches cleanly
        OracleComponentExpectation {
            locator: "st-absent".to_owned(),
            expected_presence: EditorialPresence::Absent,
            expected_text: None,
        },
        // TextMismatch
        OracleComponentExpectation {
            locator: "st-1".to_owned(),
            expected_presence: EditorialPresence::Present,
            expected_text: Some("Другой текст.".to_owned()),
        },
    ];

    let report = verify_against_edition_oracle(&snap, &oracle);
    assert_eq!(report.non_claims, COMPILER_FOLD_NON_CLAIMS);
    assert_eq!(report.matched_count, 2);
    assert_eq!(report.drift_count, 3);
    assert!(
        report
            .discrepancies
            .iter()
            .any(|d| d.kind == DiscrepancyKind::MissingInCompiled)
    );
    assert!(
        report
            .discrepancies
            .iter()
            .any(|d| d.kind == DiscrepancyKind::MembershipMismatch)
    );
    assert!(
        report
            .discrepancies
            .iter()
            .any(|d| d.kind == DiscrepancyKind::TextMismatch)
    );
}

#[test]
fn same_day_multi_act_commutativity_applies_disjoint_edits_and_refuses_interfering_ones() {
    // 1. Strictly disjoint anchors from two distinct acts on the same legal_effective_day
    //    commute and produce identical text and SHA-256 root_hash in either input order.
    let seed = vec![base(
        "st-3/p-8.1",
        "8.1) контракт - гражданско-правовой договор, указанными в частях 4, 4.1, 4.3 и 5 статьи 15;",
    )];
    let op_484 = op(
        "484-fz:op-1",
        "484-fz",
        "st-3/p-8.1",
        MicroOperationKind::InsertText,
        TextAnchorMode::AfterAnchor,
        Some("гражданско-правовой договор,"),
        Some("который заключен в письменной форме и"),
    );
    let op_124 = op(
        "124-fz:op-1",
        "124-fz",
        "st-3/p-8.1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("4, 4.1, 4.3 и 5 статьи 15"),
        Some("4, 4.3 и 4.4 статьи 15"),
    );
    let s_ab = compile_at(&seed, &[op_484.clone(), op_124.clone()], 20250101, 20250101);
    let s_ba = compile_at(&seed, &[op_124, op_484], 20250101, 20250101);
    assert_eq!(s_ab.root_hash, s_ba.root_hash);
    assert!(
        s_ab.audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::Applied)
    );
    assert_eq!(
        s_ab.components["st-3/p-8.1"].text,
        "8.1) контракт - гражданско-правовой договор, который заключен в письменной форме и указанными в частях 4, 4.3 и 4.4 статьи 15;"
    );

    // 2. Touching spans (`prev.end == next.start`) MUST fail closed with OrderingConflict.
    let touching_seed = vec![base("st-1", "абвг")];
    let touch_a = op(
        "t-a",
        "act-A",
        "st-1",
        MicroOperationKind::InsertText,
        TextAnchorMode::AfterAnchor,
        Some("аб"),
        Some("X"),
    );
    let touch_b = op(
        "t-b",
        "act-B",
        "st-1",
        MicroOperationKind::InsertText,
        TextAnchorMode::BeforeAnchor,
        Some("вг"),
        Some("Y"),
    );
    let s_touch = compile_at(&touching_seed, &[touch_a, touch_b], 20250101, 20250101);
    assert!(
        s_touch
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
    assert_eq!(s_touch.components["st-1"].text, "абвг");

    // 3. Cross-anchor interference (act-A inserts text containing act-B's anchor) MUST fail closed!
    let cross_seed = vec![base("st-1", "альфа — бета.")];
    let cross_a = op(
        "c-a",
        "act-A",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("альфа"),
        Some("бета"),
    );
    let cross_b = op(
        "c-b",
        "act-B",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("бета"),
        Some("гамма"),
    );
    let s_cross = compile_at(&cross_seed, &[cross_a, cross_b], 20250101, 20250101);
    assert!(
        s_cross
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
    assert_eq!(s_cross.components["st-1"].text, "альфа — бета.");

    // 4. WholeComponent + ExactAnchor on the same day across distinct acts MUST fail closed!
    let mixed_a = op(
        "m-a",
        "act-A",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::WholeComponent,
        None,
        Some("Новая редакция."),
    );
    let mixed_b = op(
        "m-b",
        "act-B",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("альфа"),
        Some("дельта"),
    );
    let s_mixed = compile_at(&cross_seed, &[mixed_a, mixed_b], 20250101, 20250101);
    assert!(
        s_mixed
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
    assert_eq!(s_mixed.components["st-1"].text, "альфа — бета.");

    // 5. Three commuting distinct acts on the same day produce identical text & root_hash
    //    across permutations.
    let tri_seed = vec![base("st-1", "раз — два — три.")];
    let t1 = op(
        "tri-1",
        "act-1",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("раз"),
        Some("один"),
    );
    let t2 = op(
        "tri-2",
        "act-2",
        "st-1",
        MicroOperationKind::DeleteText,
        TextAnchorMode::ExactAnchor,
        Some("два"),
        None,
    );
    let t3 = op(
        "tri-3",
        "act-3",
        "st-1",
        MicroOperationKind::InsertText,
        TextAnchorMode::AfterAnchor,
        Some("три"),
        Some("четыре"),
    );
    let tri_a = compile_at(
        &tri_seed,
        &[t1.clone(), t2.clone(), t3.clone()],
        20250101,
        20250101,
    );
    let tri_b = compile_at(&tri_seed, &[t3, t1, t2], 20250101, 20250101);
    assert_eq!(tri_a.root_hash, tri_b.root_hash);
    assert!(
        tri_a
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::Applied)
    );

    // 6. 3-act non-commutative trap (`ABC == CBA`, but `ACB` fails AmbiguousTarget!)
    //    MUST fail closed with OrderingConflict via exhaustive permutation check.
    let trap_seed = vec![base("st-1", "p X Z q | t u")];
    let trap_a = op(
        "trap-a",
        "act-A",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("X"),
        Some("t"),
    );
    let trap_b = op(
        "trap-b",
        "act-B",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("t u"),
        Some("V"),
    );
    let trap_c = op(
        "trap-c",
        "act-C",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("Z"),
        Some("u"),
    );
    let s_trap = compile_at(&trap_seed, &[trap_a, trap_b, trap_c], 20250101, 20250101);
    assert!(
        s_trap
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
    assert_eq!(s_trap.components["st-1"].text, "p X Z q | t u");

    // 7. 1-act multi-op + 1-act interleaving trap MUST fail closed with OrderingConflict.
    let inter_a1 = op(
        "i-a1",
        "act-A",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("t u"),
        Some("V"),
    );
    let inter_a2 = op(
        "i-a2",
        "act-A",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("X"),
        Some("t"),
    );
    let inter_b1 = op(
        "i-b1",
        "act-B",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("Z"),
        Some("u"),
    );
    let s_inter = compile_at(
        &trap_seed,
        &[inter_a1, inter_a2, inter_b1],
        20250101,
        20250101,
    );
    assert!(
        s_inter
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
    assert_eq!(s_inter.components["st-1"].text, "p X Z q | t u");

    // 8. Pure DeleteText cross-boundary anchor synthesis trap MUST fail closed!
    let del_trap_seed = vec![base("st-1", "t X m Y u | t m u")];
    let del_a = op(
        "del-a",
        "act-A",
        "st-1",
        MicroOperationKind::DeleteText,
        TextAnchorMode::ExactAnchor,
        Some("X"),
        None,
    );
    let del_b = op(
        "del-b",
        "act-B",
        "st-1",
        MicroOperationKind::ReplaceText,
        TextAnchorMode::ExactAnchor,
        Some("t m u"),
        Some("V"),
    );
    let del_c = op(
        "del-c",
        "act-C",
        "st-1",
        MicroOperationKind::DeleteText,
        TextAnchorMode::ExactAnchor,
        Some("Y"),
        None,
    );
    let s_del_trap = compile_at(&del_trap_seed, &[del_a, del_b, del_c], 20250101, 20250101);
    assert!(
        s_del_trap
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );

    // 9. Multi-act bucket exceeding MAX_COMMUTATIVE_BUCKET_OPS (5 ops) MUST fail closed!
    let five_seed = vec![base("st-1", "a | b | c | d | e")];
    let five_ops = vec![
        op(
            "f-1",
            "act-1",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("a"),
            Some("A"),
        ),
        op(
            "f-2",
            "act-2",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("b"),
            Some("B"),
        ),
        op(
            "f-3",
            "act-3",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("c"),
            Some("C"),
        ),
        op(
            "f-4",
            "act-4",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("d"),
            Some("D"),
        ),
        op(
            "f-5",
            "act-5",
            "st-1",
            MicroOperationKind::ReplaceText,
            TextAnchorMode::ExactAnchor,
            Some("e"),
            Some("E"),
        ),
    ];
    let s_five = compile_at(&five_seed, &five_ops, 20250101, 20250101);
    assert!(
        s_five
            .audit
            .iter()
            .all(|a| a.outcome == ApplyOutcome::OrderingConflict)
    );
}
