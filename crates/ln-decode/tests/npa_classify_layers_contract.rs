//! M211 S04 T03: NPA classification axes B..H, graph class and identity key.
//!
//! Unit contract for the layer ports (letter / KS / plenum / UFAS / GOST /
//! ТР ТС / corporate приказ / government vs organ распоряжение / codex
//! abbreviations / bare homograph) plus the full differential consumer over
//! the tracked Python reference fixture `classification-parity-fixture.tsv`.
//!
//! The fixture is a *differential reference* (D519). For frozen rows the
//! Python exporter used `doc_text` = the raw `npa-lawref/` fragment files of
//! the document concatenated with a single `"\n"` and no trimming; the Rust
//! side reproduces exactly that convention. For synthetic rows the body is the
//! recorded single-line snippet. `why` is free text and is never compared.
//! The reader is a hand-rolled TSV split (no external de/serializer, D602).

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use ln_decode::npa_classify::{
    Admin, Binding, Competence, IdentityKey, LegalClass, Normativity, classify,
};

fn lawref_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn typed_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn reference_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/classification-parity-fixture.tsv")
}

/// Number of tab-separated columns in `m211-classification-parity-fixture/v1`.
const COLUMNS: usize = 10;

struct ReferenceRow {
    kind: String,
    doc: String,
    canon: String,
    body: String,
    lemma: String,
    bucket: String,
    verdict: String,
    graph: String,
    identity_key: String,
}

fn read_reference() -> Vec<ReferenceRow> {
    let text = std::fs::read_to_string(reference_tsv())
        .expect("MISSING SOURCE: classification parity fixture is mandatory");
    let mut rows = Vec::new();
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        assert_eq!(
            cols.len(),
            COLUMNS,
            "MISSING SOURCE: malformed fixture row with {} columns: {line:?}",
            cols.len()
        );
        rows.push(ReferenceRow {
            kind: cols[0].to_string(),
            doc: cols[1].to_string(),
            canon: cols[2].to_string(),
            body: cols[3].to_string(),
            lemma: cols[4].to_string(),
            bucket: cols[5].to_string(),
            verdict: cols[6].to_string(),
            graph: cols[7].to_string(),
            identity_key: cols[8].to_string(),
        });
    }
    assert!(!rows.is_empty(), "MISSING SOURCE: fixture has no data rows");
    rows
}

/// doc -> ordered fragment file names (the raw `npa-lawref/` texts).
fn read_doc_frags() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(typed_tsv()).expect("typed parity fixture must exist");
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
    assert!(
        !docs.is_empty(),
        "MISSING SOURCE: typed fixture is mandatory"
    );
    docs
}

/// Python `doc_text`: raw fragment files concatenated with a single `"\n"`,
/// no trimming.
fn doc_text(docs: &BTreeMap<String, Vec<String>>, doc: &str) -> String {
    let frags = docs
        .get(doc)
        .unwrap_or_else(|| panic!("MISSING SOURCE: {doc} absent from typed fixture"));
    assert!(!frags.is_empty(), "MISSING SOURCE: {doc} has no fragments");
    frags
        .iter()
        .map(|frag| {
            std::fs::read_to_string(lawref_dir().join(frag))
                .unwrap_or_else(|e| panic!("MISSING SOURCE: {frag}: {e}"))
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[test]
fn letter_form_is_clarification_letter_and_refuses() {
    let row = classify("Письмо Минфина России", "");
    assert_eq!(row.legal_class, LegalClass::ClarificationLetter);
    assert_eq!(row.competence, Competence::Federal);
    assert_eq!(row.normativity, Normativity::No);
    assert_eq!(row.binding, Binding::No);
    assert_eq!(row.admin, Admin::AdministrativeClarification);
    assert_eq!(row.graph.as_str(), "refuse");
    assert_eq!(row.identity_key, IdentityKey::DoNotProject);
    assert_eq!(row.issuer, "Минфина России");
}

#[test]
fn ks_resolution_is_judicial_overlay_with_g_exception() {
    let row = classify("Постановление КС РФ", "");
    assert_eq!(row.legal_class, LegalClass::JudicialAct);
    assert_eq!(row.normativity, Normativity::No);
    assert_eq!(row.binding, Binding::YesAsToReviewedNorm);
    assert_eq!(row.graph.as_str(), "overlay");
    assert_eq!(row.identity_key, IdentityKey::OverlayNotRank);
    assert_eq!(row.issuer, "КС РФ");
}

#[test]
fn plenum_is_judicial_overlay() {
    for canon in [
        "Постановление Пленума ВАС РФ",
        "Постановление Пленума ВС РФ",
    ] {
        let row = classify(canon, "");
        assert_eq!(row.legal_class, LegalClass::JudicialAct, "{canon}");
        assert_eq!(row.binding, Binding::No, "{canon}");
        assert_eq!(row.graph.as_str(), "overlay", "{canon}");
        assert_eq!(row.identity_key, IdentityKey::OverlayNotRank, "{canon}");
        assert!(!row.issuer.is_empty(), "{canon}: plenary issuer");
    }
}

#[test]
fn ufas_decision_is_individual_act_overlay() {
    let row = classify("Решение УФАС по Челябинской области", "");
    assert_eq!(row.legal_class, LegalClass::IndividualLegalAct);
    assert_eq!(row.competence, Competence::Federal);
    assert_eq!(row.normativity, Normativity::No);
    assert_eq!(row.admin, Admin::AdministrativeIndividual);
    assert_eq!(row.graph.as_str(), "overlay");
    assert_eq!(row.identity_key, IdentityKey::Hold);
    assert_eq!(row.geo, "Челябинской области");
}

#[test]
fn gost_is_unknown_standard_overlay() {
    let row = classify("ГОСТ 1234-2020", "");
    assert_eq!(row.legal_class, LegalClass::Unknown);
    assert_eq!(row.competence, Competence::Federal);
    assert_eq!(row.graph.as_str(), "overlay");
    assert_eq!(row.identity_key, IdentityKey::DoNotProject);
}

#[test]
fn tr_ts_is_international_npa_overlay() {
    let row = classify("ТР ТС 005/2011", "");
    assert_eq!(row.legal_class, LegalClass::Npa);
    assert_eq!(row.competence, Competence::International);
    assert_eq!(row.normativity, Normativity::Yes);
    assert_eq!(row.binding, Binding::YesIfInForce);
    assert_eq!(row.graph.as_str(), "overlay");
    assert_eq!(row.identity_key, IdentityKey::DeferredUndefined);
}

#[test]
fn corporate_prikaz_refuses_primary_instrument() {
    let row = classify("Приказ", "ООО Ромашка");
    assert_eq!(row.legal_class, LegalClass::PrimaryInstrument);
    assert_eq!(row.competence, Competence::NotApplicable);
    assert_eq!(row.graph.as_str(), "refuse");
    assert_eq!(row.identity_key, IdentityKey::DoNotProject);
}

#[test]
fn prikaz_without_issuer_holds() {
    let row = classify("Приказ", "");
    assert_eq!(row.legal_class, LegalClass::Unknown);
    assert_eq!(row.graph.as_str(), "hold");
    assert_eq!(row.identity_key, IdentityKey::DoNotProject);
}

#[test]
fn government_rasporyazhenie_vs_organ() {
    let government = classify("распоряжение Правительства РФ", "");
    assert_eq!(government.legal_class, LegalClass::Npa);
    assert_eq!(government.graph.as_str(), "identifying_act");
    assert_eq!(government.identity_key, IdentityKey::PresidentialAgency);

    let organ = classify("Распоряжение", "");
    assert_eq!(organ.legal_class, LegalClass::Unknown);
    assert_eq!(organ.graph.as_str(), "hold");
    assert_eq!(organ.identity_key, IdentityKey::DoNotProject);
}

#[test]
fn codex_abbreviations_are_npa() {
    for canon in ["КоАП РФ", "Гражданский кодекс", "Трудовой кодекс", "НК РФ"]
    {
        let row = classify(canon, "");
        assert_eq!(row.legal_class, LegalClass::Npa, "{canon}");
        assert_eq!(row.graph.as_str(), "identifying_act", "{canon}");
        assert_eq!(row.identity_key, IdentityKey::Federal, "{canon}");
    }
    let koap = classify("КоАП РФ", "");
    assert_eq!(koap.admin, Admin::LegislativeOnAdminSubject);
}

#[test]
fn bare_homograph_tk_and_vk_refuse() {
    for canon in ["ТК", "ТК РФ", "ВК", "ВК РФ"] {
        let row = classify(canon, "");
        assert_eq!(row.graph.as_str(), "refuse", "{canon}");
        assert_eq!(row.identity_key, IdentityKey::DoNotProject, "{canon}");
        assert_ne!(row.legal_class, LegalClass::Npa, "{canon}");
    }
}

#[test]
fn federal_law_is_npa_federal_identity() {
    let row = classify("Федеральный закон", "");
    assert_eq!(row.legal_class, LegalClass::Npa);
    assert_eq!(row.competence, Competence::Federal);
    assert_eq!(row.graph.as_str(), "identifying_act");
    assert_eq!(row.identity_key, IdentityKey::Federal);
}

#[test]
fn fixture_layer_differential() {
    let docs = read_doc_frags();
    let rows = read_reference();

    let mut reference_keys: BTreeSet<(String, String, String, String)> = BTreeSet::new();
    let mut predicted_keys: BTreeSet<(String, String, String, String)> = BTreeSet::new();
    let mut reference_rows = 0usize;
    let mut matching = 0usize;
    let mut wrong = 0usize;
    let mut frozen_rows = 0usize;
    let mut synthetic_rows = 0usize;

    for row in &rows {
        let text = if row.kind == "synthetic" {
            synthetic_rows += 1;
            row.body.clone()
        } else {
            frozen_rows += 1;
            doc_text(&docs, &row.doc)
        };
        reference_rows += 1;
        let key = (
            row.kind.clone(),
            row.doc.clone(),
            row.canon.clone(),
            row.body.clone(),
        );
        reference_keys.insert(key.clone());

        let classified = classify(&row.canon, &text);
        predicted_keys.insert(key);

        let ok = classified.lemma == row.lemma
            && classified.bucket.as_str() == row.bucket
            && classified.verdict.as_str() == row.verdict
            && classified.graph.as_str() == row.graph
            && classified.identity_key.as_str() == row.identity_key;
        if ok {
            matching += 1;
        } else {
            wrong += 1;
            eprintln!(
                "layer mismatch: kind={} doc={} canon={:?} body={:?} \
                 rust=(lemma={:?},bucket={},verdict={},graph={},key={}) \
                 ref=(lemma={:?},bucket={},verdict={},graph={},key={})",
                row.kind,
                row.doc,
                row.canon,
                row.body,
                classified.lemma,
                classified.bucket.as_str(),
                classified.verdict.as_str(),
                classified.graph.as_str(),
                classified.identity_key.as_str(),
                row.lemma,
                row.bucket,
                row.verdict,
                row.graph,
                row.identity_key,
            );
        }
    }

    let missing = reference_keys.difference(&predicted_keys).count();
    let extra = predicted_keys.difference(&reference_keys).count();

    assert!(
        reference_rows >= 40,
        "expected at least 40 reference rows, saw {reference_rows}"
    );
    assert!(frozen_rows > 0, "expected frozen reference rows");
    assert!(synthetic_rows > 0, "expected synthetic reference rows");
    assert_eq!(
        missing, 0,
        "missing reference rows (unmatched, not dropped)"
    );
    assert_eq!(extra, 0, "extra predictions absent from reference");
    assert_eq!(wrong, 0, "wrong layer rows");
    assert_eq!(matching, reference_rows);
}

#[test]
fn axis_enum_strings_are_stable() {
    assert_eq!(LegalClass::Npa.as_str(), "npa");
    assert_eq!(
        LegalClass::IndividualLegalAct.as_str(),
        "individual_legal_act"
    );
    assert_eq!(
        LegalClass::ClarificationLetter.as_str(),
        "clarification_letter"
    );
    assert_eq!(LegalClass::JudicialAct.as_str(), "judicial_act");
    assert_eq!(LegalClass::PrimaryInstrument.as_str(), "primary_instrument");
    assert_eq!(LegalClass::Unknown.as_str(), "unknown");
    assert_eq!(Competence::International.as_str(), "international");
    assert_eq!(Competence::Federal.as_str(), "federal");
    assert_eq!(Competence::Subject.as_str(), "subject");
    assert_eq!(Competence::Municipal.as_str(), "municipal");
    assert_eq!(Competence::NotApplicable.as_str(), "not_applicable");
    assert_eq!(Competence::Unknown.as_str(), "unknown");
    assert_eq!(Normativity::Yes.as_str(), "yes");
    assert_eq!(Normativity::No.as_str(), "no");
    assert_eq!(Normativity::Unknown.as_str(), "unknown");
    assert_eq!(Binding::YesIfInForce.as_str(), "yes_if_in_force");
    assert_eq!(Binding::No.as_str(), "no");
    assert_eq!(Binding::NotApplicable.as_str(), "not_applicable");
    assert_eq!(Binding::Unknown.as_str(), "unknown");
    assert_eq!(
        Binding::YesAsToReviewedNorm.as_str(),
        "yes_as_to_reviewed_norm"
    );
    assert_eq!(
        Admin::LegislativeOnAdminSubject.as_str(),
        "legislative_on_admin_subject"
    );
    assert_eq!(Admin::AdministrativeNpa.as_str(), "administrative_npa");
    assert_eq!(
        Admin::AdministrativeIndividual.as_str(),
        "administrative_individual"
    );
    assert_eq!(Admin::KoapProceedingAct.as_str(), "koap_proceeding_act");
    assert_eq!(
        Admin::AdministrativeClarification.as_str(),
        "administrative_clarification"
    );
    assert_eq!(Admin::NotAdministrative.as_str(), "not_administrative");
    assert_eq!(Admin::Unknown.as_str(), "unknown");
    assert_eq!(IdentityKey::Federal.as_str(), "federal");
    assert_eq!(
        IdentityKey::PresidentialAgency.as_str(),
        "presidential_agency"
    );
    assert_eq!(
        IdentityKey::RegionalMunicipal.as_str(),
        "regional_municipal"
    );
    assert_eq!(IdentityKey::DoNotProject.as_str(), "do_not_project");
    assert_eq!(IdentityKey::OverlayNotRank.as_str(), "overlay_not_rank");
    assert_eq!(
        IdentityKey::DeferredUndefined.as_str(),
        "deferred-undefined"
    );
    assert_eq!(IdentityKey::Hold.as_str(), "hold");
}
