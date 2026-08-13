//! Corpus-role classification is YAML-driven. Unclassified files stay Unknown.

use ln_kb_ontology::catalog::{CorpusRoleOutcome, OntologyCatalog};

fn catalog() -> OntologyCatalog {
    OntologyCatalog::embedded().expect("yaml")
}

#[test]
fn overview_path_is_c2hint_not_legislative() {
    match catalog().classify_corpus_role(
        "law-source/consultant/obzor-izmenenii-federalnogo-zakona-ot-05-04-2013-n-44-fz.xml",
        "Обзор изменений Федерального закона от 05.04.2013 N 44-ФЗ",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C2hint_change_overview"),
        other => panic!("{other:?}"),
    }
}

#[test]
fn consolidated_red_ot_path_is_edition_oracle() {
    match catalog().classify_corpus_role(
        "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025.xml",
        "Федеральный закон от 05.04.2013 N 44-ФЗ (ред. от 28.12.2025)",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C2_edition_oracle"),
        other => panic!("{other:?}"),
    }
}

#[test]
fn fas_decision_is_alien_work() {
    match catalog().classify_corpus_role(
        "law-source/consultant/reshenie-fas-rossii-ot-19-06-2026-po-delu-n-28-06-105.xml",
        "Решение ФАС России",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C3_alien_work"),
        other => panic!("{other:?}"),
    }
}

#[test]
fn unclassified_filename_is_unknown() {
    assert_eq!(
        catalog().classify_corpus_role("law-source/consultant/unknown-scan.xml", "Документ"),
        CorpusRoleOutcome::Unknown
    );
}

#[test]
fn overview_beats_red_ot_in_same_filename() {
    match catalog().classify_corpus_role(
        "law-source/consultant/obzor-izmenenii-44-fz-red-ot-2025.xml",
        "",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C2hint_change_overview"),
        other => panic!("{other:?}"),
    }
}

#[test]
fn unknown_role_token_in_signal_fails_catalog_parse() {
    let yaml = r#"
schema_version: law-nexus-kb-ontology/v1
fsm:
  current: O0
  states:
    O0:
      name: open
  transitions:
    - {from: O0, to: O0, when: stay}
vocabulary:
  hierarchy_levels:
    - statya
  node_kinds:
    - Work
  forbidden_node_kinds:
    - ApplicableDecision
  corpus_roles:
    - C2_edition_oracle
  corpus_role_signals:
    - {role: NotARole, field: path, needle: x, rank: 1}
"#;
    let err = OntologyCatalog::parse_yaml(yaml).expect_err("unknown role");
    assert!(err.to_string().contains("unknown role"));
}
