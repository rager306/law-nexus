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

/// Real consru_export corpus paths (skip when the export is absent).
fn real_corpus_dir() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(&dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz");
    if root
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .exists()
    {
        Some(root)
    } else {
        None
    }
}

#[test]
fn real_edition_seed_path_is_edition_oracle() {
    let Some(dir) = real_corpus_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path = dir
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .to_string_lossy()
        .to_string();
    match catalog().classify_corpus_role(&path, "") {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C2_edition_oracle"),
        other => panic!("edition seed must classify, got {other:?} for {path}"),
    }
}

#[test]
fn real_edition_latest_path_is_edition_oracle() {
    let Some(dir) = real_corpus_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path = dir
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml")
        .to_string_lossy()
        .to_string();
    match catalog().classify_corpus_role(&path, "") {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C2_edition_oracle"),
        other => panic!("edition latest must classify, got {other:?}"),
    }
}

#[test]
fn real_c1_amending_act_title_classifies_as_c1() {
    // C1 amending act: path has no signal; the catalog title carries the marker.
    let cat = catalog();
    match cat.classify_corpus_role(
        "consru_export/consru_export/exports/npa/law_2025-06-07_138-fz_rev-unknown_1c01dbd3.xml",
        "Федеральный закон от 07.06.2025 N 138-ФЗ \"О внесении изменений в статьи 31 и 43",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C1_amending_act"),
        other => panic!("C1 title must classify, got {other:?}"),
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
