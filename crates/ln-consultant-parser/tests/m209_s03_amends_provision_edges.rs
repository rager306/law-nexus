//! M209/S03 T02: the amending-act and affected-provision leg of R070 for the
//! named `cc:44-fz` chain, measured live against the licensed provider export.
//!
//! The suite is skip-capable exactly like `tests/classifier_recall_test.rs`:
//! `CONSULTANT_EXPORT_DIR` (empty-as-unset) with the default `consru_export`,
//! and `SKIP` plus an early return when the catalog relation database is absent.
//!
//! What is asserted when the corpus is present:
//! - the golden relation set carries `amends` / `explicit` edges only, read
//!   through the additive read-only `SqliteCatalog::amends_edge_set`;
//! - the declared denominators (120 explicit amends edges, 122 layer1 records,
//!   121 amending records, 94 statya bindings of the chain needle) are
//!   re-derived from the live corpus and reproduce;
//! - repeat reads are deterministic byte-for-byte;
//! - every edge lands in exactly one outcome and the outcome partition sums to
//!   the declared denominator;
//! - absent or malformed inputs raise the named fail-closed codes.
//!
//! Echo discipline: counts, catalog identifiers and reason codes only. No
//! tooltip, no XML and no article text is printed or asserted on.

use std::fs;
use std::path::{Path, PathBuf};

use ln_consultant_parser::amendment_provenance::{
    collect_amends_provisions, render_amends_provisions, validate_amends_provisions,
    AmendsProvisionEvidence, AMENDS_EDGE_LIMIT, AMENDS_PROVISION_FAIL_CLOSED_CODES,
    AMENDS_PROVISION_REASON_CODES,
};
use ln_consultant_parser::catalog_sqlite::SqliteCatalog;

const CONSULTANT_EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
const CONSULTANT_EXPORT_DIR_DEFAULT: &str = "consru_export";

/// Expected grounding pins of the accepted corpus revision (T02 plan).
const EXPECTED_ROOT_SOURCE_ID: &str = "cp:LAW:508812";
const EXPECTED_PROFILE: &str = "procurement-core";
const EXPECTED_AMENDS_EDGES: usize = 120;
const EXPECTED_LAYER1_RECORDS: u64 = 122;
const EXPECTED_LAYER1_AMENDING: u64 = 121;
const EXPECTED_REGISTRY_STATYA: u64 = 94;
const EXPECTED_REGISTRY_TOTAL: u64 = 102;
const REGISTRY_NEEDLE: &str = "law_2013-04-05_44-fz";

fn consultant_export_dir() -> String {
    match std::env::var(CONSULTANT_EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => CONSULTANT_EXPORT_DIR_DEFAULT.to_owned(),
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The catalog relation database, or `None` when the licensed export is absent.
fn catalog_path() -> Option<PathBuf> {
    let export_root = repo_root()
        .join(consultant_export_dir())
        .join("consru_export");
    let mut names: Vec<PathBuf> = fs::read_dir(&export_root)
        .ok()?
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| {
            let name = path.file_name().unwrap_or_default().to_string_lossy();
            name.starts_with("catalog-links-") && name.ends_with(".sqlite")
        })
        .collect();
    names.sort();
    names.into_iter().next()
}

#[test]
fn golden_set_carries_explicit_amends_edges_only() {
    let Some(path) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let catalog = SqliteCatalog::open_read_only(&path).expect("read-only catalog");
    assert!(
        catalog.is_read_only().expect("read-only probe"),
        "the catalog relation database must stay read-only"
    );
    let set = catalog
        .amends_edge_set(AMENDS_EDGE_LIMIT)
        .expect("amends edge set")
        .expect("relation run present");

    assert_eq!(set.runs_total, 1, "exactly one relation run is declared");
    assert_eq!(set.root_source_id, EXPECTED_ROOT_SOURCE_ID);
    assert_eq!(set.profile, EXPECTED_PROFILE);
    assert_eq!(set.status, "complete");
    assert_eq!(set.edges.len(), EXPECTED_AMENDS_EDGES);
    assert!(
        set.edges.iter().all(|edge| edge.relation_type == "amends"
            && edge.normalization_status == "explicit"
            && edge.bank == "LAW"
            && edge.export_status == "exported"
            && edge.document_key > 0),
        "the golden set must carry explicit LAW amends edges only"
    );

    // The bound is a real refusal boundary, not a silent truncation.
    let bounded = catalog
        .amends_edge_set(8)
        .expect("bounded edge set")
        .expect("relation run present");
    assert_eq!(bounded.edges.len(), 8);

    eprintln!(
        "[golden] edges={} runs={} run_id={} root={} profile={}",
        set.edges.len(),
        set.runs_total,
        set.run_id,
        set.root_source_id,
        set.profile
    );
}

#[test]
fn declared_denominators_reproduce_from_the_live_catalog() {
    let Some(_) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let evidence = collect_amends_provisions(&repo_root(), &consultant_export_dir())
        .expect("live amending-act leg");
    validate_amends_provisions(&evidence).expect("the leg validates");

    assert_eq!(evidence.amends_edges_total, EXPECTED_AMENDS_EDGES as u64);
    assert_eq!(evidence.layer1_records_total, EXPECTED_LAYER1_RECORDS);
    assert_eq!(evidence.layer1_amending_acts, EXPECTED_LAYER1_AMENDING);
    assert_eq!(evidence.registry_needle, REGISTRY_NEEDLE);
    assert_eq!(evidence.registry_statya_bindings, EXPECTED_REGISTRY_STATYA);
    assert_eq!(evidence.registry_bindings_total, EXPECTED_REGISTRY_TOTAL);
    assert_eq!(evidence.rows.len(), EXPECTED_AMENDS_EDGES);

    eprintln!(
        "[denominator] edges={} layer1={} amending={} registry_statya={} registry_total={}",
        evidence.amends_edges_total,
        evidence.layer1_records_total,
        evidence.layer1_amending_acts,
        evidence.registry_statya_bindings,
        evidence.registry_bindings_total
    );
}

#[test]
fn repeat_reads_are_deterministic() {
    let Some(_) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let first =
        collect_amends_provisions(&repo_root(), &consultant_export_dir()).expect("first live read");
    let second = collect_amends_provisions(&repo_root(), &consultant_export_dir())
        .expect("second live read");
    assert_eq!(
        render_amends_provisions(&first),
        render_amends_provisions(&second),
        "two live reads must render identical canonical bytes"
    );
}

#[test]
fn resolution_outcomes_sum_to_the_declared_denominator() {
    let Some(_) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let evidence = collect_amends_provisions(&repo_root(), &consultant_export_dir())
        .expect("live amending-act leg");

    let sum: u64 = evidence.by_outcome.values().sum();
    assert_eq!(
        sum, evidence.amends_edges_total,
        "every edge must land in exactly one outcome"
    );
    assert_eq!(
        evidence.by_outcome.len(),
        AMENDS_PROVISION_REASON_CODES.len()
    );
    for code in AMENDS_PROVISION_REASON_CODES {
        assert!(
            evidence.by_outcome.contains_key(code),
            "outcome {code} must be declared"
        );
    }
    let coverage: u64 = evidence.by_layer1_coverage.values().sum();
    assert_eq!(coverage, evidence.layer1_amending_acts);

    // Every row's recorded outcome is justified by its own counts.
    assert_eq!(
        evidence
            .rows
            .iter()
            .filter(|row| row.outcome == "resolved-provision")
            .count() as u64,
        evidence.by_outcome["resolved-provision"]
    );
    assert!(evidence
        .rows
        .iter()
        .filter(|row| row.outcome == "resolved-provision")
        .all(|row| row.statya_refs_resolved > 0));

    eprintln!(
        "[outcomes] resolved={} not_in_registry={} no_statya={} target_not_44fz={} unparsed={} no_export={} no_layer1={}",
        evidence.by_outcome["resolved-provision"],
        evidence.by_outcome["provision-not-in-registry"],
        evidence.by_outcome["no-statya-reference"],
        evidence.by_outcome["target-not-44fz"],
        evidence.by_outcome["unparsed-act"],
        evidence.by_outcome["no-export-file"],
        evidence.by_outcome["no-layer1-record"]
    );
}

#[test]
fn the_rendered_artifact_is_count_only_and_ascii() {
    let Some(_) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let evidence = collect_amends_provisions(&repo_root(), &consultant_export_dir())
        .expect("live amending-act leg");
    let rendered = render_amends_provisions(&evidence);

    assert!(rendered.is_ascii(), "the artifact must be pure ascii");
    assert!(!rendered.contains('\n'), "canonical bytes are single-line");
    assert!(
        !rendered.contains("consultantplus://") && !rendered.contains("<w:"),
        "no corpus prose marker may reach the artifact"
    );
    assert!(
        !rendered.contains("raw_tooltip") && !rendered.contains("offline_uri"),
        "no prose column name is carried"
    );
    for code in AMENDS_PROVISION_FAIL_CLOSED_CODES {
        assert!(
            rendered.contains(&format!("\"{code}\"")),
            "every fail-closed code is declared in the artifact: {code}"
        );
    }
    assert_eq!(rendered, render_amends_provisions(&evidence));
}

#[test]
fn absent_and_malformed_inputs_raise_named_fail_closed_codes() {
    let root = repo_root();

    // Absent export root: the catalog relation database cannot be located.
    let absent = collect_amends_provisions(&root, "consru_export-does-not-exist")
        .expect_err("an absent export root must fail closed");
    assert_eq!(absent.code(), Some("input_absent"));
    assert_eq!(absent.exit_code(), 3);

    // Malformed input: two catalog relation databases under one export root.
    let fixture = std::env::temp_dir().join(format!(
        "ln-consultant-parser-m209-s03-t02-{}",
        std::process::id()
    ));
    let export_root = fixture.join("consru_export").join("consru_export");
    fs::create_dir_all(&export_root).expect("create fixture tree");
    fs::write(
        export_root.join("catalog-links-a.sqlite"),
        b"not-a-database",
    )
    .expect("write a");
    fs::write(
        export_root.join("catalog-links-b.sqlite"),
        b"not-a-database",
    )
    .expect("write b");
    let ambiguous = collect_amends_provisions(&fixture, "consru_export")
        .expect_err("two catalog databases must fail closed");
    assert_eq!(ambiguous.code(), Some("family_count_unsupported"));
    assert_eq!(ambiguous.exit_code(), 6);

    // Malformed input: a single catalog file that is not a database. The file
    // exists but cannot be read as a catalog, so this is a count failure and
    // not an absence.
    fs::remove_file(export_root.join("catalog-links-b.sqlite")).expect("remove b");
    let unreadable = collect_amends_provisions(&fixture, "consru_export")
        .expect_err("a malformed catalog must fail closed");
    assert_eq!(unreadable.code(), Some("family_count_unsupported"));
    assert_eq!(unreadable.exit_code(), 6);
    fs::remove_dir_all(&fixture).expect("clean fixture tree");
}

#[test]
fn the_leg_is_bound_to_one_named_chain_root() {
    let Some(_) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog-links sqlite not available");
        return;
    };
    let evidence = collect_amends_provisions(&repo_root(), &consultant_export_dir())
        .expect("live amending-act leg");
    assert_eq!(evidence.run.root_source_id, EXPECTED_ROOT_SOURCE_ID);
    assert_eq!(evidence.run.profile, EXPECTED_PROFILE);
    assert!(evidence.run.source_artifact_sha256.starts_with("sha256:"));
    assert!(evidence.run.table_artifact_sha256.starts_with("sha256:"));
    let ids: Vec<&str> = evidence
        .inputs
        .iter()
        .map(|pin| pin.input_id.as_str())
        .collect();
    assert_eq!(
        ids,
        vec![
            "catalog_links_sqlite",
            "layer1_manifest",
            "kb_hierarchy_registry"
        ]
    );
    for pin in &evidence.inputs {
        assert!(
            !Path::new(&pin.relative_path).is_absolute(),
            "anchors stay repository-relative"
        );
        assert_eq!(pin.input_sha256.len(), 71);
        assert!(pin.input_bytes > 0);
    }
    assert_eq!(
        render_amends_provisions(&evidence)
            .matches("\"outcome\":")
            .count(),
        EXPECTED_AMENDS_EDGES
    );
    let _: &AmendsProvisionEvidence = &evidence;
}
