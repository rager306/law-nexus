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

const CONSULTANT_EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
const CONSULTANT_EXPORT_DIR_DEFAULT: &str = "consru_export";

/// CONSULTANT_EXPORT_DIR with empty-as-unset semantics (M185 S03): unset,
/// empty, or whitespace-only values fall back to the default export dir.
fn consultant_export_dir() -> String {
    match std::env::var(CONSULTANT_EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => CONSULTANT_EXPORT_DIR_DEFAULT.to_owned(),
    }
}

/// Real consru_export corpus paths (skip when the export is absent).
fn real_corpus_dir() -> Option<std::path::PathBuf> {
    let dir = consultant_export_dir();
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
fn real_484fz_canon_title_classifies_as_c1() {
    // M186 S01: 484-ФЗ canon (1a599b98 carries <o:Title>). The path itself has
    // no C1 signal; the title marker classifies before any Work event log
    // (R080). Title excerpt is a verbatim prefix of the tracked pin
    // c1-484-fz-provenance.yaml title_excerpt.
    let cat = catalog();
    match cat.classify_corpus_role(
        "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml",
        "О внесении изменений в Федеральный закон \"О контрактной системе",
    ) {
        CorpusRoleOutcome::Bound { role } => assert_eq!(role, "C1_amending_act"),
        other => panic!("484 canon title must classify as C1, got {other:?}"),
    }
}

#[test]
fn real_484fz_canon_path_only_does_not_classify_c1() {
    // Q7 negative: the catalog carries no path-borne C1 signal, so the canon
    // path with an empty title must stay non-C1 (classification is title-only).
    let cat = catalog();
    match cat.classify_corpus_role(
        "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml",
        "",
    ) {
        CorpusRoleOutcome::Unknown => {}
        CorpusRoleOutcome::Bound { role } => {
            assert_ne!(role, "C1_amending_act", "path-only must not be C1")
        }
        CorpusRoleOutcome::Conflict { roles } => {
            assert!(!roles.iter().any(|r| r == "C1_amending_act"))
        }
    }
}

#[test]
fn real_484fz_titleless_twin_does_not_classify_c1() {
    // Q7 negative: the 49a92fbb twin has no <o:Title> (pin twin_pin_not_canon);
    // by path alone it must never pass for the C1 canon.
    let cat = catalog();
    match cat.classify_corpus_role(
        "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_49a92fbb.xml",
        "",
    ) {
        CorpusRoleOutcome::Unknown => {}
        CorpusRoleOutcome::Bound { role } => {
            assert_ne!(role, "C1_amending_act", "titleless twin must not be C1")
        }
        CorpusRoleOutcome::Conflict { roles } => {
            assert!(!roles.iter().any(|r| r == "C1_amending_act"))
        }
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
