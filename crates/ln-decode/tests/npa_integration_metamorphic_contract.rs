//! M211 S04 T07: metamorphic battery for the NPA classification + report
//! pipeline (ADR-0029; RC28-F19, `prd/architecture/model-crystal.md` §MC-INV,
//! D519, MEM1653).
//!
//! Metamorphic properties are *separate evidence* from the differential
//! correctness plane: this file never averages the two. The metamorphic
//! denominator counts **executed properties** (`passed/executed`); a battery
//! with no executed property is `not-measured`, never 0 and never a perfect 1
//! (D519 semantics of `measured_metric`).
//!
//! Covered invariants:
//! * **INV-06** — changing a reference target, or inserting an irrelevant
//!   block, does not change the source mention of an already-linked member;
//! * **INV-08** — every derivation (`LinkedMember` / `LinkedRelation` /
//!   `ClassifiedMember`) carries a source-local `LocalSpan` that passes
//!   `npa_anchor::check_span`; an artificial out-of-block span is a diagnostic,
//!   never a panic;
//! * **INV-11** — two independent `run_integration_report` runs on the same
//!   input are byte-equal;
//! * **INV-22** — the report makes no completeness claim from counts or hashes
//!   and keeps the canonical honesty keys.
//!
//! Only the frozen tracked fixtures are read (D602 hand-rolled reader); a
//! missing source fails closed.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use ln_decode::npa_anchor::{check_span, LocalSpan};
use ln_decode::npa_classify::{classify, classify_members, ClassificationDiagnostic};
use ln_decode::npa_link::{
    self, LinkDerivation, LinkedDocument, LinkedMember, LinkedMemberKind, LinkedRelation,
};
use ln_decode::npa_report::{
    measured_metric, run_integration_report, IntegrationCli, Metric, MetricStatus,
};
use ln_decode::npa_sweep::EXIT_OK;

// ── metamorphic ledger (denominator independence) ──────────────────────────

/// A metamorphic result ledger. `executed` counts the *properties actually
/// run*; `passed` counts the ones that held. The denominator is therefore the
/// number of executed properties — never a correctness-plane row count, and
/// `not-measured` never enters numerator or denominator (D519 / MEM1653).
#[derive(Debug, Default)]
struct MetamorphicLedger {
    executed: u64,
    passed: u64,
    failed: Vec<&'static str>,
}

impl MetamorphicLedger {
    fn record(&mut self, id: &'static str, held: bool) {
        self.executed += 1;
        if held {
            self.passed += 1;
        } else {
            self.failed.push(id);
        }
    }

    const fn metric(&self) -> Metric {
        measured_metric(self.passed, self.executed)
    }
}

// ── frozen-seed fixture reader (D602 hand-rolled TSV split) ────────────────

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn fixture_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn read_docs() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(fixture_tsv()).expect("MISSING SOURCE: typed fixture");
    let mut docs: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols.first().copied() {
            Some("doc") if cols.len() >= 2 => {
                current = Some(cols[1].to_string());
                docs.entry(cols[1].to_string()).or_default();
            }
            Some("frag") if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(frags) = docs.get_mut(cur) {
                        frags.push(cols[1].to_string());
                    }
                }
            }
            _ => {}
        }
    }
    assert!(!docs.is_empty(), "MISSING SOURCE: fixture is mandatory");
    docs
}

fn load_doc(docs: &BTreeMap<String, Vec<String>>, doc: &str) -> Vec<String> {
    let frags = docs
        .get(doc)
        .unwrap_or_else(|| panic!("MISSING SOURCE: {doc} absent from fixture"));
    assert!(!frags.is_empty(), "MISSING SOURCE: {doc} has no fragments");
    frags
        .iter()
        .map(|frag| {
            std::fs::read_to_string(fixture_dir().join(frag))
                .unwrap_or_else(|e| panic!("MISSING SOURCE: {}: {e}", frag))
        })
        .collect()
}

fn paras(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| (*s).to_string()).collect()
}

/// The source mention a span points at (its local byte range in the block).
fn mention(paras: &[String], span: LocalSpan) -> String {
    paras
        .get(span.block)
        .and_then(|para| para.get(span.start..span.end))
        .unwrap_or_default()
        .to_string()
}

fn member_by_number<'a>(linked: &'a LinkedDocument, number: &str) -> &'a LinkedMember {
    linked
        .members
        .iter()
        .find(|m| m.number == number)
        .unwrap_or_else(|| panic!("member {number} absent: {:?}", linked.members))
}

fn absent_default() -> &'static Path {
    Path::new("/npa-metamorphic-absent-default-root")
}

// ── INV-06: locality of the source mention ─────────────────────────────────

/// INV-06: appending an irrelevant block, or inserting one between members,
/// never changes the source mention of an already-linked member. The mention is
/// the place in the source text, not the reference target that resolves to it.
#[test]
fn inv06_irrelevant_block_does_not_change_the_source_mention() {
    let mut ledger = MetamorphicLedger::default();

    // (a) Append an irrelevant closed citation after the member.
    let base = paras(&["Федеральный закон от 01.01.2020 N 1-ФЗ"]);
    let appended = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ",
        "Гражданский кодекс Российской Федерации от 30.11.1994 N 51-ФЗ",
    ]);
    let a = npa_link::build_linked_document(&base);
    let b = npa_link::build_linked_document(&appended);
    let am = member_by_number(&a, "1-ФЗ");
    let bm = member_by_number(&b, "1-ФЗ");
    ledger.record("INV-06 append preserves span", am.evidence == bm.evidence);
    ledger.record(
        "INV-06 append preserves mention text",
        mention(&base, am.evidence) == mention(&appended, bm.evidence),
    );
    ledger.record("INV-06 append preserves type", am.type_name == bm.type_name);

    // (b) Insert an irrelevant block between two members. The earlier member is
    // byte-identical; the later member keeps its local byte range and mention
    // text (only the block index moves).
    let base2 = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ",
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ",
    ]);
    let inserted = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ",
        "Гражданский кодекс Российской Федерации от 30.11.1994 N 51-ФЗ",
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ",
    ]);
    let c = npa_link::build_linked_document(&base2);
    let d = npa_link::build_linked_document(&inserted);
    let cm0 = member_by_number(&c, "1-ФЗ");
    let dm0 = member_by_number(&d, "1-ФЗ");
    let cm1 = member_by_number(&c, "2-ФЗ");
    let dm1 = member_by_number(&d, "2-ФЗ");
    ledger.record("INV-06 between preserves earlier member", cm0 == dm0);
    ledger.record(
        "INV-06 between preserves later local range",
        (cm1.evidence.start, cm1.evidence.end) == (dm1.evidence.start, dm1.evidence.end),
    );
    ledger.record(
        "INV-06 between preserves later mention text",
        mention(&base2, cm1.evidence) == mention(&inserted, dm1.evidence),
    );
    ledger.record(
        "INV-06 between preserves later classification",
        classify(&cm1.type_name, &base2[cm1.evidence.block])
            == classify(&dm1.type_name, &inserted[dm1.evidence.block]),
    );

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-06 locality passed={}/{}",
        metric.numerator, metric.denominator
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

/// INV-06: changing the reference target (the resolving head) does not change
/// the source mention of the dependent member. The tail's mention is a property
/// of the source text, not of what the head says.
#[test]
fn inv06_changing_the_reference_target_preserves_the_source_mention() {
    let mut ledger = MetamorphicLedger::default();

    let base = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ,",
        "от 02.02.2021 N 2-ФЗ",
    ]);
    let retargeted = paras(&[
        "Постановление Правительства РФ от 09.09.2019 N 9,",
        "от 02.02.2021 N 2-ФЗ",
    ]);

    let a = npa_link::build_linked_document(&base);
    let b = npa_link::build_linked_document(&retargeted);

    // The head target differs...
    let head_a = member_by_number(&a, "1-ФЗ");
    let head_b = member_by_number(&b, "9");
    ledger.record(
        "INV-06 target actually changed",
        head_a.type_name != head_b.type_name,
    );

    // ...but the dependent tail's source mention is byte-identical.
    let tail_a = member_by_number(&a, "2-ФЗ");
    let tail_b = member_by_number(&b, "2-ФЗ");
    ledger.record(
        "INV-06 retarget preserves tail span",
        tail_a.evidence == tail_b.evidence,
    );
    ledger.record(
        "INV-06 retarget preserves tail mention text",
        mention(&base, tail_a.evidence) == mention(&retargeted, tail_b.evidence),
    );

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-06 retarget passed={}/{}",
        metric.numerator, metric.denominator
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

// ── INV-08: anchored derivations ───────────────────────────────────────────

fn bad_span_member(evidence: LocalSpan) -> LinkedMember {
    LinkedMember {
        id: 0,
        kind: LinkedMemberKind::Anchored,
        date: String::new(),
        number: String::new(),
        type_name: "Федеральный закон".to_string(),
        approved_by: None,
        alias: None,
        derivation: LinkDerivation::TypedAnchor,
        evidence,
        provenance: Vec::new(),
    }
}

/// INV-08: every derivation emitted over the frozen 40-doc seed carries a
/// source-local `LocalSpan` that passes `check_span` (members, their
/// provenance, relations, letterheads, and classified members alike).
#[test]
fn inv08_every_derivation_carries_a_valid_source_local_anchor() {
    let docs = read_docs();
    let mut ledger = MetamorphicLedger::default();
    let mut members_seen = 0u64;
    let mut relations_seen = 0u64;
    let mut classified_seen = 0u64;

    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);

        for member in &linked.members {
            members_seen += 1;
            let para = paras
                .get(member.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: member block out of range"));
            check_span(para, member.evidence)
                .unwrap_or_else(|e| panic!("{doc}: member span {e:?}"));
            for span in &member.provenance {
                let prov = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: provenance block out of range"));
                check_span(prov, *span).unwrap_or_else(|e| panic!("{doc}: provenance {e:?}"));
            }
        }

        for relation in &linked.relations {
            relations_seen += 1;
            assert_eq!(
                relation.evidence.len(),
                2,
                "{doc}: relation evidence must be separate local anchors"
            );
            for span in &relation.evidence {
                let para = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: relation block out of range"));
                check_span(para, *span).unwrap_or_else(|e| panic!("{doc}: relation {e:?}"));
            }
        }

        if let Some(letterhead) = &linked.letterhead {
            let para = paras
                .get(letterhead.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: letterhead block out of range"));
            check_span(para, letterhead.evidence)
                .unwrap_or_else(|e| panic!("{doc}: letterhead {e:?}"));
        }

        let (members, _diagnostics) = classify_members(&linked, &paras);
        for classified in &members {
            classified_seen += 1;
            let para = paras
                .get(classified.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: classified block out of range"));
            check_span(para, classified.evidence)
                .unwrap_or_else(|e| panic!("{doc}: classified {e:?}"));
        }
    }

    ledger.record("INV-08 members anchored", members_seen > 0);
    ledger.record("INV-08 relations anchored", relations_seen > 0);
    ledger.record("INV-08 classified anchored", classified_seen > 0);

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-08 anchored derivations passed={}/{}",
        metric.numerator, metric.denominator
    );
    eprintln!(
        "INV-08 seen members={members_seen} relations={relations_seen} classified={classified_seen}"
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

/// INV-08: an artificial span outside its block is rejected by `check_span`
/// and surfaces as `ClassificationDiagnostic::SpanInvalid` — no panic, no
/// fabricated classification.
#[test]
fn inv08_artificial_out_of_block_span_is_a_diagnostic_not_a_panic() {
    let mut ledger = MetamorphicLedger::default();
    let input = paras(&["Федеральный закон от 01.01.2020 N 1-ФЗ"]);

    let cases = [
        LocalSpan {
            block: 3,
            start: 0,
            end: 1,
        },
        LocalSpan {
            block: 0,
            start: 5,
            end: 5,
        },
        LocalSpan {
            block: 0,
            start: 0,
            end: 10_000,
        },
        LocalSpan {
            block: 0,
            start: 1,
            end: 2,
        },
    ];

    ledger.record(
        "INV-08 out-of-range span rejected",
        check_span(&input[0], cases[0]).is_err(),
    );

    for evidence in cases {
        let linked = LinkedDocument {
            members: vec![bad_span_member(evidence)],
            relations: Vec::<LinkedRelation>::new(),
            letterhead: None,
            diagnostics: Vec::new(),
        };
        let (members, diagnostics) = classify_members(&linked, &input);
        assert!(members.is_empty(), "no fabrication for {evidence:?}");
        assert_eq!(
            diagnostics,
            vec![ClassificationDiagnostic::SpanInvalid],
            "invalid span must fail closed: {evidence:?}"
        );
        ledger.record("INV-08 SpanInvalid fail-closed", true);
    }

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-08 fail-closed spans passed={}/{}",
        metric.numerator, metric.denominator
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

// ── INV-11: deterministic replay ───────────────────────────────────────────

/// INV-11: two independent `run_integration_report` runs on the same input
/// render byte-equal JSON, and the linked projection replays structurally.
#[test]
fn inv11_two_independent_replays_are_byte_equal() {
    let mut ledger = MetamorphicLedger::default();

    let cli = IntegrationCli::default();
    let first = run_integration_report(&cli, absent_default());
    let second = run_integration_report(&cli, absent_default());
    assert_eq!(first.exit_code, EXIT_OK, "stderr: {}", first.stderr);
    assert_eq!(first.exit_code, second.exit_code);
    let json_first = first.json.expect("first report");
    let json_second = second.json.expect("second report");
    ledger.record("INV-11 report replay byte-equal", json_first == json_second);
    ledger.record("INV-11 stderr replay equal", first.stderr == second.stderr);

    let synthetic = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ,",
        "от 02.02.2021 N 2-ФЗ",
    ]);
    ledger.record(
        "INV-11 linked projection replay equal",
        npa_link::build_linked_document(&synthetic) == npa_link::build_linked_document(&synthetic),
    );

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-11 deterministic replay passed={}/{}",
        metric.numerator, metric.denominator
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

// ── INV-22: no completeness claim from counts or hashes ────────────────────

/// INV-22: the report makes no completeness / independent-gold claim from
/// counts or hashes, and keeps the canonical honesty keys (`[proposed]`,
/// `authoritative=false`, `is_gold=false`, `not_human=true`, `derived=true`).
#[test]
fn inv22_report_claims_no_completeness_and_keeps_honesty_keys() {
    let mut ledger = MetamorphicLedger::default();
    let run = run_integration_report(&IntegrationCli::default(), absent_default());
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    let json = run.json.expect("report");

    for needle in [
        "\"derived\": true",
        "\"lifecycle\": [",
        "\"proposed\"",
        "\"authoritative\": false",
        "\"is_gold\": false",
        "\"not_human\": true",
        "\"not_s03_metrics\": true",
        "\"schema\": \"npa-integration-report/v1\"",
    ] {
        ledger.record("INV-22 canonical honesty key", json.contains(needle));
    }

    ledger.record(
        "INV-22 explicit non-claim limit present",
        json.contains("no completeness claim from counts or hashes (INV-22)"),
    );

    // Keys/fields that would claim completeness or an independent gold from
    // counts or hashes are forbidden (INV-22). Note the value-text
    // "no completeness claim …" is deliberately not a key.
    for forbidden in [
        "\"completeness\"",
        "\"coverage_proof\"",
        "\"root_hash\"",
        "\"hash\"",
        "\"independent_gold\"",
        "\"gold\": true",
        "\"complete\": true",
        "\"is_complete\"",
        "\"covers_all\"",
    ] {
        ledger.record("INV-22 no completeness claim", !json.contains(forbidden));
    }

    assert!(ledger.failed.is_empty(), "failed: {:?}", ledger.failed);
    let metric = ledger.metric();
    eprintln!(
        "INV-22 no completeness claims passed={}/{}",
        metric.numerator, metric.denominator
    );
    assert_eq!(metric.status, MetricStatus::Measured);
}

// ── denominator independence (D519 / MEM1653) ─────────────────────────────

/// The metamorphic denominator counts *executed properties* and stays
/// independent from the differential correctness plane: it is never derived
/// from, averaged with, or folded into correctness. A battery with no executed
/// property is `not-measured` (not 0 and not 1); an executed-but-failing
/// property is a legitimate `0/1`.
#[test]
fn metamorphic_denominator_is_independent_from_the_correctness_plane() {
    let mut ledger = MetamorphicLedger::default();

    // One entry per invariant executed by this battery.
    ledger.record("INV-06", true);
    ledger.record("INV-08", true);
    ledger.record("INV-11", true);
    ledger.record("INV-22", true);
    ledger.record("denominator-independence", true);

    let metric = ledger.metric();
    assert_eq!(metric.status, MetricStatus::Measured);
    assert_eq!(metric.numerator, 5);
    assert_eq!(metric.denominator, 5);

    // The correctness plane's denominator is a different quantity entirely
    // (reference rows). The report merges neither plane into the other.
    let json = run_integration_report(&IntegrationCli::default(), absent_default())
        .json
        .expect("report");
    assert!(
        json.contains("\"total\": 78"),
        "correctness denominator is the 78 reference rows"
    );
    assert_ne!(
        metric.denominator, 78,
        "the metamorphic denominator must not be the correctness denominator"
    );
    assert!(
        !json.contains("\"metamorphic\""),
        "metamorphic evidence must not be silently folded into the report"
    );
    for forbidden in [
        "\"overall\":",
        "\"combined\":",
        "\"average\":",
        "\"accuracy\":",
    ] {
        assert!(
            !json.contains(forbidden),
            "planes must not be averaged: {forbidden}"
        );
    }

    // Denominator semantics: no executed property is `not-measured`, never 0/1.
    let empty = MetamorphicLedger::default().metric();
    assert_eq!(empty, Metric::NOT_MEASURED);
    assert_eq!(empty.status, MetricStatus::NotMeasured);
    assert_eq!(empty.numerator, 0);
    assert_eq!(empty.denominator, 0);

    // An executed property that fails is a real 0/1 measurement, not a hole.
    let failed = measured_metric(0, 1);
    assert_eq!(failed.status, MetricStatus::Measured);
    assert_eq!(failed.numerator, 0);
    assert_eq!(failed.denominator, 1);

    eprintln!(
        "metamorphic denominator passed={}/{}",
        metric.numerator, metric.denominator
    );
}
