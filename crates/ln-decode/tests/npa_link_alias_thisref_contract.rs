//! M211 S03 T04: scoped alias resolution + this-document references contract.
//!
//! Hand-rolled fixture reader (D602): the frozen 40-doc seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` (doc -> frag) and the
//! fragment texts from `tests/fixtures/npa-lawref/`. A missing source fails
//! closed instead of silently skipping.
//!
//! Covers: doc-027 `(далее - Закон N 2487-1)` / `(далее - Закон N 44-ФЗ)`
//! declarations plus a short-reference binding; doc-032 / doc-035 party aliases
//! (`Заявитель`, `Организатор`, `Оператор`, `Продажа`, `Конкурсный отбор`)
//! never create a binding while `Протокол` does; doc-028 no-declaration
//! fail-closed; doc-002/007/009/010 this-references staying requisites-free and
//! never binding a foreign act; a head-backed this-reference; `указанного
//! Федерального закона`; determinism / immutability; evidence-span validity;
//! serde/fs/env-free sources.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_link::{self, LinkDerivation, LinkDiagnostic, LinkedRelationKind};

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn fixture_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn read_fixture() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(fixture_tsv()).expect("typed parity fixture must exist");
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
            let path = fixture_dir().join(frag);
            std::fs::read_to_string(&path)
                .unwrap_or_else(|e| panic!("MISSING SOURCE: {}: {e}", path.display()))
        })
        .collect()
}

const PARTY_ALIASES: &[&str] = &[
    "заявитель",
    "организатор",
    "оператор",
    "продажа",
    "конкурсный отбор",
];

/// doc-027/frag-122: `(далее - Закон N 2487-1)` binds the `Законом Российской
/// Федерации от 11.03.1992 N 2487-1` anchor; frag-120 short reference
/// `Закона N 44-ФЗ` resolves through the frag-119 declaration.
#[test]
fn frozen_doc027_declaration_resolves_and_a_short_ref_binds() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-027");

    let bindings = npa_link::collect_aliases(&paras);
    let zakon = bindings
        .iter()
        .find(|b| b.target_number == "2487-1")
        .unwrap_or_else(|| panic!("no `(далее - Закон N 2487-1)` binding: {bindings:?}"));
    assert_eq!(zakon.target_date, "11.03.1992");
    assert!(
        zakon.target_type.to_lowercase().contains("закон"),
        "{}",
        zakon.target_type
    );
    assert!(
        zakon.keys.iter().any(|k| k == "2487-1"),
        "bare-number key missing: {:?}",
        zakon.keys
    );

    let fz44 = bindings
        .iter()
        .find(|b| b.target_number == "44-ФЗ")
        .unwrap_or_else(|| panic!("no `(далее - Закон N 44-ФЗ)` binding: {bindings:?}"));
    assert_eq!(fz44.target_date, "05.04.2013");

    let (members, relations, _) = npa_link::link_aliases_and_this_refs(&paras);
    let resolved = members
        .iter()
        .find(|m| m.derivation == LinkDerivation::ScopedAlias && m.number == "44-ФЗ")
        .unwrap_or_else(|| panic!("short ref «Закона N 44-ФЗ» not resolved: {members:?}"));
    assert_eq!(resolved.date, "05.04.2013");
    assert!(
        relations
            .iter()
            .any(|r| r.kind == LinkedRelationKind::ScopedAlias && r.from_id == resolved.id),
        "{relations:?}"
    );
}

/// doc-032/frag-142 party aliases (`Заявитель`, `Организатор торгов`,
/// `Оператор`, `Продажа`) never create an alias binding, while the real
/// `(далее - Закон о защите конкуренции)` declaration still binds 135-ФЗ.
#[test]
fn frozen_doc032_party_aliases_create_no_binding() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-032");

    let bindings = npa_link::collect_aliases(&paras);
    for forbidden in PARTY_ALIASES {
        assert!(
            !bindings
                .iter()
                .any(|b| b.alias.to_lowercase().contains(forbidden)),
            "party alias {forbidden} bound: {bindings:?}"
        );
    }
    let zakon = bindings
        .iter()
        .find(|b| b.target_number == "135-ФЗ")
        .unwrap_or_else(|| {
            panic!("no `(далее - Закон о защите конкуренции)` binding: {bindings:?}")
        });
    assert_eq!(zakon.target_date, "26.07.2006");

    let (members, _, _) = npa_link::link_aliases_and_this_refs(&paras);
    assert!(
        !members.iter().any(|m| {
            m.alias
                .as_deref()
                .map(|a| PARTY_ALIASES.iter().any(|p| a.to_lowercase().contains(p)))
                .unwrap_or(false)
        }),
        "a party alias leaked into a derived member: {members:?}"
    );
}

/// doc-035/frag-158: `(далее - Протокол)` resolves the `протокол` anchor, and
/// the frag-156 `(далее - Заявитель)` (plus `Организатор`, `Оператор`,
/// `Конкурсный отбор`) never binds.
#[test]
fn frozen_doc035_protocol_alias_resolves_and_party_does_not() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-035");

    let bindings = npa_link::collect_aliases(&paras);
    let protocol = bindings
        .iter()
        .find(|b| b.alias.to_lowercase() == "протокол")
        .unwrap_or_else(|| panic!("no `(далее - Протокол)` binding: {bindings:?}"));
    assert_eq!(protocol.target_number, "1");
    assert_eq!(protocol.target_type.to_lowercase(), "протокол");
    assert!(
        !bindings
            .iter()
            .any(|b| b.alias.to_lowercase().contains("заявитель")),
        "{bindings:?}"
    );
}

/// doc-028 has no `(далее - …)` declaration: `Закон N 44-ФЗ` in frag-126 must
/// stay unresolved (fail-closed) and emit `AliasWithoutDeclaration`.
#[test]
fn frozen_doc028_short_ref_without_declaration_is_fail_closed() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-028");

    assert!(
        npa_link::collect_aliases(&paras).is_empty(),
        "doc-028 declares no aliases"
    );

    let (members, _, diagnostics) = npa_link::link_aliases_and_this_refs(&paras);
    assert!(
        !members.iter().any(|m| m.number == "44-ФЗ"),
        "no declaration -> no binding: {members:?}"
    );
    assert!(
        diagnostics.contains(&LinkDiagnostic::AliasWithoutDeclaration),
        "{diagnostics:?}"
    );
}

/// doc-002/007/009/010: `настоящего Кодекса` / `настоящего Федерального
/// закона` do not borrow a foreign act's requisites; the derived member stays
/// requisites-free and reports `HeadUnavailable`.
#[test]
fn frozen_this_ref_never_binds_a_foreign_act() {
    let docs = read_fixture();
    for doc in ["npa-doc-002", "npa-doc-007", "npa-doc-009", "npa-doc-010"] {
        let paras = load_doc(&docs, doc);
        let (members, _, diagnostics) = npa_link::link_aliases_and_this_refs(&paras);
        let refs: Vec<_> = members
            .iter()
            .filter(|m| m.derivation == LinkDerivation::ThisDocumentRef)
            .collect();
        assert!(!refs.is_empty(), "{doc}: expected a this-ref member");
        for reference in &refs {
            assert_eq!(
                reference.date, "—",
                "{doc}: {} leaked a date",
                reference.type_name
            );
            assert_eq!(
                reference.number, "—",
                "{doc}: {} leaked a number",
                reference.type_name
            );
        }
        if doc == "npa-doc-002" {
            assert!(
                refs.iter().any(|m| m.type_name == "Кодекс"),
                "{doc}: {refs:?}"
            );
        } else {
            assert!(
                refs.iter().any(|m| m.type_name == "Федеральный закон"),
                "{doc}: {refs:?}"
            );
        }
        assert!(
            diagnostics.contains(&LinkDiagnostic::HeadUnavailable),
            "{doc}: {diagnostics:?}"
        );
    }
}

/// A `настоящего Федерального закона` reference resolves to this XML's own
/// recognized letterhead when one is present.
#[test]
fn this_ref_uses_the_document_letterhead_when_present() {
    let paras = vec![
        "МИНИСТЕРСТВО ВНУТРЕННИХ ДЕЛ РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "ПРИКАЗ".to_string(),
        "от 12.03.2020 N 123".to_string(),
        "Положения настоящего Федерального закона применяются к отношениям".to_string(),
    ];
    let (members, _, diagnostics) = npa_link::link_aliases_and_this_refs(&paras);
    let reference = members
        .iter()
        .find(|m| m.derivation == LinkDerivation::ThisDocumentRef)
        .unwrap_or_else(|| panic!("no this-ref member: {members:?}"));
    assert_eq!(reference.type_name, "Приказ МВД России");
    assert_eq!(reference.date, "12.03.2020");
    assert_eq!(reference.number, "123");
    assert!(
        !diagnostics.contains(&LinkDiagnostic::HeadUnavailable),
        "{diagnostics:?}"
    );
}

/// `указанного Федерального закона` resolves to the nearest preceding FZ with
/// DATE+N in the same block; without one it is skipped.
#[test]
fn ukazanny_binds_only_to_a_preceding_fz_in_the_same_block() {
    let bound = vec![
        "Федеральный закон от 29.07.2017 N 218-ФЗ регулирует отношения. \
         Положения указанного Федерального закона применяются к фонду."
            .to_string(),
    ];
    let (members, relations, _) = npa_link::link_aliases_and_this_refs(&bound);
    let reference = members
        .iter()
        .find(|m| m.derivation == LinkDerivation::ScopedAlias && m.number == "218-ФЗ")
        .unwrap_or_else(|| panic!("ukazanny did not bind: {members:?}"));
    assert!(
        relations
            .iter()
            .any(|r| { r.kind == LinkedRelationKind::ScopedAlias && r.from_id == reference.id }),
        "{relations:?}"
    );

    let orphan = vec!["Положения указанного Федерального закона применяются.".to_string()];
    let (members, _, _) = npa_link::link_aliases_and_this_refs(&orphan);
    assert!(
        !members
            .iter()
            .any(|m| m.derivation == LinkDerivation::ScopedAlias),
        "no preceding FZ -> no binding: {members:?}"
    );
}

/// Deterministic replay and input immutability.
#[test]
fn alias_and_this_ref_linking_is_deterministic_and_leaves_input_untouched() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-027");
    let before = paras.clone();
    let first = npa_link::link_aliases_and_this_refs(&paras);
    let second = npa_link::link_aliases_and_this_refs(&paras);
    assert_eq!(first, second, "replay must be stable");
    assert_eq!(paras, before, "linking must not mutate its input");
    assert_eq!(
        npa_link::collect_aliases(&paras),
        npa_link::collect_aliases(&paras),
        "alias replay must be stable"
    );
}

/// Every declared/derived/relation evidence span is a valid source-local
/// `LocalSpan`.
#[test]
fn every_alias_and_this_ref_evidence_span_is_valid() {
    let docs = read_fixture();
    for doc in [
        "npa-doc-027",
        "npa-doc-032",
        "npa-doc-035",
        "npa-doc-002",
        "npa-doc-007",
        "npa-doc-009",
        "npa-doc-010",
    ] {
        let paras = load_doc(&docs, doc);
        for binding in npa_link::collect_aliases(&paras) {
            for span in [binding.declaration_evidence, binding.target_evidence] {
                let source = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: evidence block out of range: {span:?}"));
                npa_anchor::check_span(source, span)
                    .unwrap_or_else(|e| panic!("{doc}: invalid span {span:?}: {e:?}"));
            }
        }
        let (members, relations, _) = npa_link::link_aliases_and_this_refs(&paras);
        for member in &members {
            let source = paras
                .get(member.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: member block out of range"));
            npa_anchor::check_span(source, member.evidence)
                .unwrap_or_else(|e| panic!("{doc}: invalid member span: {e:?}"));
        }
        for relation in &relations {
            assert_eq!(relation.evidence.len(), 2, "{doc}: two local anchors");
            for span in &relation.evidence {
                let source = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: relation block out of range"));
                npa_anchor::check_span(source, *span)
                    .unwrap_or_else(|e| panic!("{doc}: invalid relation span: {e:?}"));
            }
        }
    }
}

/// The linked module stays free of the external (de)serializer and of
/// filesystem / environment access (D602).
#[test]
fn linked_module_stays_serde_fs_env_free() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/npa_link.rs");
    let source = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read npa_link.rs: {e}"));
    for forbidden in [
        "serde",
        "Deserialize",
        "Serialize",
        "serde_json",
        "std::fs",
        "std::env",
    ] {
        assert!(
            !source.contains(forbidden),
            "npa_link.rs must stay serde/fs/env-free (D602): found {forbidden}"
        );
    }
}
