//! M211 S04 T06: hostile battery for the NPA classification + report pipeline
//! (ADR-0029; AUDIT RC28-F16, R077, R081).
//!
//! This is an *integration* hostile suite: it drives the real public surfaces
//! (`npa_link::recognize_letterhead` / `build_linked_document` /
//! `link_series` / `link_aliases_and_this_refs` / `link_approved_by`,
//! `npa_classify::classify` / `classify_form` / `classify_members`, and the
//! canonical `npa_report` renderer) with adversarial inputs and asserts the
//! *exact* fail-closed outcome, never a "best approximation".
//!
//! Guardrails exercised here:
//! * a court / unknown letterhead fabricates no requisites and mints no NPA
//!   identity; the letterhead guard is bounded to the head zone (documented
//!   S03 limitation) and never extends by body prose;
//! * a short reference without a `(далее — …)` declaration in *this* XML stays
//!   unresolved (`AliasWithoutDeclaration`), party aliases never bind;
//! * an orphan series tail without an eligible head refuses
//!   (`OpenSeriesWithoutHead`) instead of silently continuing;
//! * bare `ТК`/`ВК` homographs refuse and `указ`/`указание` are never merged;
//! * a corporate regulation (`ООО`/`АО`/`ПАО`/`ИП`/`ЗАО`) refuses and mints no
//!   NPA identity (`do_not_project`) and no normative citation;
//! * forged honesty declarations in report input are ignored in favour of the
//!   canonical `derived`/`[proposed]`/`authoritative=false`/`is_gold=false`/
//!   `not_human=true` keys;
//! * an invalid member span fails closed (`ClassificationDiagnostic::
//!   SpanInvalid`) without panic and without a fabricated classification.
//!
//! All negatives are named, single-case tests with a concrete expectation, not
//! a corpus average. The only tracked-source read is the frozen 40-doc seed
//! used by the doc-028 alias negative (D602 hand-rolled reader; a missing
//! source fails closed).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use ln_decode::npa_anchor;
use ln_decode::npa_classify::{
    ClassificationDiagnostic, GraphClass, IdentityKey, LegalClass, classify, classify_form,
    classify_members, lemma_match,
};
use ln_decode::npa_link::{
    self, LinkDerivation, LinkDiagnostic, LinkedDocument, LinkedMember, LinkedMemberKind,
    LinkedRelationKind,
};
use ln_decode::npa_report::{
    CorpusPlane, CorrectnessPlane, IntegrationCli, RefusalPlane, render_integration_report,
    run_integration_report,
};
use ln_decode::npa_sweep::EXIT_OK;

// ── frozen-seed fixture reader (D602 hand-rolled TSV split) ────────────────

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn fixture_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn read_fixture() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(fixture_tsv()).expect("MISSING SOURCE: typed fixture");
    let mut docs: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols.first().copied() {
            Some("doc") => {
                current = Some(cols[1].to_string());
                docs.entry(cols[1].to_string()).or_default();
            }
            Some("frag") if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref()
                    && let Some(frags) = docs.get_mut(cur)
                {
                    frags.push(cols[1].to_string());
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

/// The narrow NPA identity keys that must never be minted for a refused or
/// off-dictionary input.
fn is_npa_identity(key: IdentityKey) -> bool {
    matches!(
        key,
        IdentityKey::Federal | IdentityKey::PresidentialAgency | IdentityKey::RegionalMunicipal
    )
}

// ── 1. letterhead negatives ────────────────────────────────────────────────

/// Court letterhead: `recognize_letterhead` returns `None` (never a fabricated
/// date/number), the linked document has no letterhead and reports
/// `HeadUnavailable`, and a court-shaped TYPE classifies as refuse/hold with
/// no NPA identity.
#[test]
fn court_letterhead_never_fabricates_requisites_and_never_mints_npa_identity() {
    let court = paras(&[
        "ВЕРХОВНЫЙ СУД РОССИЙСКОЙ ФЕДЕРАЦИИ",
        "РЕШЕНИЕ",
        "от 01.01.2020 N 1",
    ]);

    // No letterhead: nothing to fabricate.
    assert_eq!(
        npa_link::recognize_letterhead(&court),
        None,
        "a court letterhead must fail closed, not invent requisites"
    );

    let linked = npa_link::build_linked_document(&court);
    assert!(
        linked.letterhead.is_none(),
        "court head leaked into the linked document: {:?}",
        linked.letterhead
    );
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::HeadUnavailable),
        "an absent head must be surfaced, not silently ignored: {:?}",
        linked.diagnostics
    );

    // Court decision TYPE is off-dictionary: refuse/hold, no NPA identity.
    let row = classify("РЕШЕНИЕ", &court[1]);
    assert!(
        matches!(row.graph, GraphClass::Refuse | GraphClass::Hold),
        "court decision must not classify as an identifying act: {:?}",
        row.graph
    );
    assert!(
        !is_npa_identity(row.identity_key),
        "court decision minted an NPA identity: {:?}",
        row.identity_key
    );
}

/// Unknown letterhead: an unrecognized head with a real anchor still yields
/// `None`, so no requisites are fabricated (fail-closed).
#[test]
fn unknown_letterhead_fails_closed_without_requisites() {
    let unknown = paras(&["ДОГОВОР О ПРИСОЕДИНЕНИИ", "от 01.01.2020 N 1"]);
    assert_eq!(
        npa_link::recognize_letterhead(&unknown),
        None,
        "an off-dictionary head with an anchor must not fabricate a letterhead"
    );
    let linked = npa_link::build_linked_document(&unknown);
    assert!(linked.letterhead.is_none());
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::HeadUnavailable)
    );
}

/// Documented S03 limitation: the letterhead guard is bounded to the head
/// zone, so a court head deeper than three paragraphs is not reclassified as
/// court — but it still fabricates no requisites (`None`, not a guessed head).
#[test]
fn court_head_outside_the_bounded_zone_is_not_court_classified() {
    let deep = paras(&[
        "Общие положения",
        "Настоящий документ определяет порядок применения.",
        "Текст раздела.",
        "АРБИТРАЖНЫЙ СУД МОСКОВСКОЙ ОБЛАСТИ",
        "РЕШЕНИЕ",
        "от 02.02.2020 N 2",
    ]);

    // The court tokens at index 3+ are outside the three-paragraph head zone;
    // no kind is recognized there, so the result is fail-closed (never a
    // fabricated head built from the deeper court paragraph).
    assert_eq!(
        npa_link::recognize_letterhead(&deep),
        None,
        "a court head outside the bounded zone must not be recognized"
    );
    let linked = npa_link::build_linked_document(&deep);
    assert!(linked.letterhead.is_none());
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::HeadUnavailable)
    );
}

// ── 2. unresolved references ───────────────────────────────────────────────

/// doc-028 declares no `(далее — …)`: the `Закон N 44-ФЗ` short reference must
/// stay unresolved and be surfaced as `AliasWithoutDeclaration`. A party-role
/// declaration (`(далее — Заявитель)`) never binds either.
#[test]
fn short_ref_without_declaration_and_party_alias_never_bind() {
    let docs = read_fixture();
    let doc_paras = load_doc(&docs, "npa-doc-028");

    assert!(
        npa_link::collect_aliases(&doc_paras).is_empty(),
        "doc-028 declares no alias"
    );

    let linked = npa_link::build_linked_document(&doc_paras);
    assert!(
        !linked.members.iter().any(|m| m.number == "44-ФЗ"),
        "no declaration -> no binding, got {:?}",
        linked.members
    );
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::AliasWithoutDeclaration),
        "an unresolved short reference must be surfaced: {:?}",
        linked.diagnostics
    );

    // A declared party role is not a resolvable act alias.
    let party = paras(&["(далее - Заявитель) обращается с жалобой", "ООО Ромашка"]);
    let bindings = npa_link::collect_aliases(&party);
    assert!(
        !bindings
            .iter()
            .any(|b| b.alias.to_lowercase().contains("заявитель")),
        "a party alias must never bind: {bindings:?}"
    );
}

/// An orphan series tail without an eligible head must refuse with
/// `OpenSeriesWithoutHead`, never silently continue a preceding unrelated
/// complete citation.
#[test]
fn orphan_series_tail_without_head_refuses_instead_of_continuing() {
    let input = paras(&[
        "Федеральный закон от 01.01.2020 N 1-ФЗ",
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ",
        "Федеральный закон от 03.03.2022 N 3-ФЗ",
        "от 04.04.2023 N 4-ФЗ",
    ]);

    let (relations, diagnostics) = npa_link::link_series(&input);
    assert!(
        relations.is_empty(),
        "no open head => no continuation: {relations:?}"
    );
    assert!(
        diagnostics.contains(&LinkDiagnostic::OpenSeriesWithoutHead),
        "orphan tail must fail closed: {diagnostics:?}"
    );

    let linked = npa_link::build_linked_document(&input);
    assert!(
        !linked
            .relations
            .iter()
            .any(|r| r.kind == LinkedRelationKind::ContinuesSeries)
    );
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::OpenSeriesWithoutHead)
    );
}

// ── 3. homographs are not merged ───────────────────────────────────────────

/// Bare `ТК`/`ВК` are homographs: they refuse and mint no identity. A full
/// codex name is still an NPA — the guard does not over-refuse.
#[test]
fn bare_codex_homographs_refuse_and_do_not_merge_with_full_names() {
    for canon in ["ТК", "ТК РФ", "ВК", "ВК РФ"] {
        let form = classify_form(canon);
        assert_eq!(form.verdict.as_str(), "unknown_kind", "{canon}");
        assert_eq!(form.graph.as_str(), "refuse", "{canon}");

        let row = classify(canon, "");
        assert_eq!(row.graph.as_str(), "refuse", "{canon}");
        assert_eq!(row.identity_key, IdentityKey::DoNotProject, "{canon}");
        assert_ne!(row.legal_class, LegalClass::Npa, "{canon}");
    }

    // Positive control: the full, non-homographic codex name is an NPA.
    let full = classify("Трудовой кодекс", "");
    assert_eq!(full.legal_class, LegalClass::Npa);
    assert_eq!(full.graph.as_str(), "identifying_act");
    assert_eq!(full.identity_key, IdentityKey::Federal);
}

/// `указ` and `указание` are distinct lemmas (exact/inflected match only, never
/// a substring match), so the two are never collapsed; the real `указ` form is
/// still recognized.
#[test]
fn ukaz_and_ukazanie_are_never_merged() {
    assert!(
        !lemma_match("указ", "указание"),
        "указ must not match указание"
    );
    assert!(
        !lemma_match("указание", "указ"),
        "указание must not match указ"
    );
    assert!(
        !lemma_match("приказ", "приказание"),
        "приказ must not match приказание"
    );
    // Positive control: the real forms still match themselves / inflections.
    assert!(lemma_match("указ", "указ"));
    assert_eq!(
        classify_form("Указ Президента РФ").verdict.as_str(),
        "form_in_dictionary"
    );
}

// ── 4. corporate actor refusal ─────────────────────────────────────────────

/// A `приказ` issued by a corporate actor (`ООО`/`АО`/`ПАО`/`ИП`/`ЗАО`) is a
/// primary instrument: refuse, `do_not_project`, never an NPA identity.
#[test]
fn corporate_regulation_refuses_and_mints_no_npa_identity() {
    for token in ["ООО", "АО", "ПАО", "ИП", "ЗАО"] {
        let body = format!("{token} Ромашка");
        let row = classify("Приказ", &body);
        assert_eq!(
            row.legal_class,
            LegalClass::PrimaryInstrument,
            "{token}: expected a primary instrument"
        );
        assert_eq!(row.graph.as_str(), "refuse", "{token}");
        assert_eq!(row.identity_key, IdentityKey::DoNotProject, "{token}");
        assert!(
            !is_npa_identity(row.identity_key),
            "{token}: a corporate actor minted an NPA identity"
        );
    }
}

/// A corporate platform regulation is refused in the linking pass: the
/// corporate body is recorded, but no normative citation and no relation are
/// minted (`HeadFamilyCarryRefused`).
#[test]
fn corporate_regulation_mints_no_normative_citation() {
    let input = paras(&[
        "Регламент работы электронной площадки",
        "утвержден генеральным директором ООО \"РТС-тендер\" 01.01.2020",
    ]);
    let (annexes, relations, diagnostics) = npa_link::link_approved_by(&input);
    assert!(
        diagnostics.contains(&LinkDiagnostic::HeadFamilyCarryRefused),
        "{diagnostics:?}"
    );
    let regulation = annexes
        .iter()
        .find(|m| m.type_name == "Регламент")
        .unwrap_or_else(|| panic!("regulation annex: {annexes:?}"));
    assert_eq!(regulation.derivation, LinkDerivation::Refused);
    let citation = regulation
        .approved_by
        .as_deref()
        .expect("corporate approver");
    assert!(citation.contains("генеральный директор"), "{citation}");
    assert!(
        !citation.contains("Постановление")
            && !citation.contains("Приказ")
            && !citation.contains("Правительства"),
        "no normative citation may be fabricated: {citation}"
    );
    assert!(
        !relations.iter().any(|r| r.from_id == regulation.id),
        "a refused annex must mint no relation: {relations:?}"
    );
}

// ── 5. forged honesty keys ─────────────────────────────────────────────────

const FORGED_LABEL: &str = "is_gold=true authoritative=true not_human=false";

fn assert_canonical_honesty(json: &str) {
    for needle in [
        "\"derived\": true",
        "\"authoritative\": false",
        "\"is_gold\": false",
        "\"not_human\": true",
        "\"not_s03_metrics\": true",
        "\"schema\": \"npa-integration-report/v1\"",
    ] {
        assert!(json.contains(needle), "missing canonical honesty {needle}");
    }
    for forged in [
        "\"is_gold\": true",
        "\"authoritative\": true",
        "\"not_human\": false",
        "\"derived\": false",
    ] {
        assert!(
            !json.contains(forged),
            "a forged honesty declaration was accepted: {forged}"
        );
    }
}

/// A hostile input that declares `is_gold=true`/`authoritative=true`/
/// `not_human=false` cannot forge the report's honesty metadata: the canonical
/// keys are emitted regardless, and the hostile text is carried only as an
/// inert label value.
#[test]
fn forged_honesty_keys_are_ignored_in_favour_of_canonical_values() {
    // Pure renderer: the only attacker-controlled scalar is the label.
    let rendered = render_integration_report(
        FORGED_LABEL,
        "complete",
        &CorrectnessPlane::default(),
        &RefusalPlane::default(),
        &CorpusPlane::default(),
    );
    assert_canonical_honesty(&rendered);
    assert!(
        rendered.contains(FORGED_LABEL),
        "the hostile label must be carried verbatim, not silently dropped"
    );

    // End-to-end through the mandatory-fixture runner.
    let cli = IntegrationCli {
        label: Some(FORGED_LABEL.to_owned()),
        ..IntegrationCli::default()
    };
    let run = run_integration_report(&cli, Path::new("/npa-hostile-absent-default-root"));
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    let json = run.json.expect("skip run still renders the report");
    assert_canonical_honesty(&json);
}

// ── 6. invalid spans fail closed ───────────────────────────────────────────

/// A member whose evidence span is out of range, inverted, or in a missing
/// block is reported as `SpanInvalid` and skipped — no panic, no fabricated
/// classification.
#[test]
fn invalid_member_spans_fail_closed_without_panic() {
    fn member(evidence: ln_decode::npa_anchor::LocalSpan) -> LinkedMember {
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

    let input = paras(&["Федеральный закон от 01.01.2020 N 1-ФЗ"]);
    let cases = [
        // Block index past the end of the paragraph slice.
        ln_decode::npa_anchor::LocalSpan {
            block: 7,
            start: 0,
            end: 1,
        },
        // Inverted / empty half-open range.
        ln_decode::npa_anchor::LocalSpan {
            block: 0,
            start: 5,
            end: 5,
        },
        // Past the byte length of the block.
        ln_decode::npa_anchor::LocalSpan {
            block: 0,
            start: 0,
            end: 10_000,
        },
        // Not a UTF-8 char boundary.
        ln_decode::npa_anchor::LocalSpan {
            block: 0,
            start: 1,
            end: 2,
        },
    ];

    for evidence in cases {
        let linked = LinkedDocument {
            members: vec![member(evidence)],
            relations: Vec::new(),
            letterhead: None,
            diagnostics: Vec::new(),
        };
        let (members, diagnostics) = classify_members(&linked, &input);
        assert!(
            members.is_empty(),
            "no member may be fabricated for {evidence:?}"
        );
        assert_eq!(
            diagnostics,
            vec![ClassificationDiagnostic::SpanInvalid],
            "invalid span must fail closed: {evidence:?}"
        );
    }
}

// ── 7. determinism / immutability of the hostile path ──────────────────────

/// Hostile inputs replay deterministically and never mutate their inputs (the
/// typed and linked streams stay read-only).
#[test]
fn hostile_inputs_replay_deterministically_and_are_never_mutated() {
    let inputs: Vec<Vec<String>> = vec![
        paras(&[
            "ВЕРХОВНЫЙ СУД РОССИЙСКОЙ ФЕДЕРАЦИИ",
            "РЕШЕНИЕ",
            "от 01.01.2020 N 1",
        ]),
        paras(&[
            "Федеральный закон от 01.01.2020 N 1-ФЗ",
            "от 04.04.2023 N 4-ФЗ",
        ]),
        paras(&["ТК", "Регламент работы электронной площадки"]),
    ];

    for input in &inputs {
        let before = input.clone();
        let first = npa_link::build_linked_document(input);
        let second = npa_link::build_linked_document(input);
        assert_eq!(first, second, "hostile replay must be stable");
        assert_eq!(*input, before, "the pipeline must not mutate its input");

        let (m1, d1) = classify_members(&first, input);
        let (m2, d2) = classify_members(&second, input);
        assert_eq!(m1, m2);
        assert_eq!(d1, d2);

        // Every emitted member still anchors to a valid source-local span.
        for member in &m1 {
            let source = input
                .get(member.evidence.block)
                .unwrap_or_else(|| panic!("member block out of range"));
            npa_anchor::check_span(source, member.evidence)
                .unwrap_or_else(|e| panic!("invalid member span {e:?}"));
        }
    }
}
