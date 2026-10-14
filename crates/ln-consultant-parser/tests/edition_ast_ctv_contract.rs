//! Contract test: per-edition AST presence + text CTV over the materialized
//! cleaned-wire JSONL layer (M224/S06/T04).
//!
//! Exercises the library surface (`edition_visibility_counts`,
//! `ctv_resolution_counts`) and the `edition-timeline` bin with `--ctv`: an
//! oracle-synthesized presence filter (`edition_ast_at`) over a synthetic
//! membership fold, the fail-closed hidden>0 case when an admitted component is
//! absent from the presence set (`filter_ast_to_expression` prunes, never a
//! silent pass), the text CTV outcomes (`Resolved` / `Unknown` / `Conflict`),
//! the counts-only `edition-ast-ctv/v1` payload (determinism + ASCII posture +
//! `visible == admitted` with `hidden == 0`), the fail-closed CLI refusals
//! (`--ctv` with `chain`), and a skip-capable corpus-gated 44-FZ edition-0118
//! oracle.
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures and
//! the tracked corpus export exercised here; never corpus coverage, never
//! source authenticity, never legal amendment correctness or CTV truth. The
//! presence log is oracle-synthesized, not expression inheritance. R1000 stays
//! active.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::edition_timeline::{
    AST_CTV_NON_CLAIMS, AST_CTV_SCHEMA, AssemblyMode, EXIT_USAGE, EditionTimelineCli,
    ctv_resolution_counts, edition_visibility_counts, run_edition_timeline,
};
use ln_decode::cleaned_wire::{WireCompletion, WireLimits, render_cleaned_projection};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_kb_ontology::domain::{
    ComponentInExpressionEvent, ComponentInExpressionLog, ExpressionId, HierarchyBinding,
    HierarchyMap, build_text_log_from_articles,
};
use ln_temporal::domain::{
    AmendingActId, ComponentConceptId, MembershipChangeKind, VersionedMembershipEvent,
    VersionedMembershipLog,
};

const BIN: &str = env!("CARGO_BIN_EXE_edition-timeline");

/// Corpus-relative path of the 44-FZ edition-0118 export (gitignored [smoke]).
const CORPUS_44FZ_REL: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml";

/// `glava 1` + `statya 4` with a body line, so the text CTV resolves.
const GLANVA_STATYA_BODY_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p><w:p><w:r><w:t>Участником закупки может быть любое юридическое лицо.</w:t></w:r></w:p></w:body></w:wordDocument>"#;

// ------------------------------------------------------------ preparation #

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(label: &str) -> Self {
        let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or(0);
        let path = std::env::temp_dir().join(format!(
            "ln-edition-ast-ctv-{}-{}-{}-{label}",
            std::process::id(),
            nanos,
            seq
        ));
        fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.path);
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Run the real producer pipeline and return the materialized JSONL string.
fn build_wire(xml: &[u8]) -> String {
    let package = capture(xml, &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export")
}

fn export_wire(dir: &Path, name: &str, xml: &str) -> PathBuf {
    let artifact = build_wire(xml.as_bytes());
    let path = dir.join(name);
    fs::write(&path, artifact).expect("write cleaned wire fixture");
    path
}

fn run_bin(args: &[&str]) -> std::process::Output {
    Command::new(BIN)
        .args(args)
        .output()
        .expect("bin must launch")
}

fn cc(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("cc")
}

fn test_expression() -> ExpressionId {
    ExpressionId::parse("expr:test:presence").expect("expression")
}

fn attach(log: &mut VersionedMembershipLog, parent: &str, child: &str, day: i64) {
    let provenance = AmendingActId::parse("amendingact:test-presence").expect("provenance");
    let event = VersionedMembershipEvent::try_new(
        MembershipChangeKind::Attach,
        cc(parent),
        cc(child),
        day,
        provenance,
    )
    .expect("membership event");
    log.append(event).expect("append membership");
}

fn include(
    log: &mut ComponentInExpressionLog,
    expression: &ExpressionId,
    component: &str,
    day: i64,
) {
    let event = ComponentInExpressionEvent::try_new(
        "include",
        expression.clone(),
        cc(component),
        day,
        "amendingact:test-presence",
    )
    .expect("presence event");
    log.append(event).expect("append presence");
}

fn binding(level: &str, number: &str, component: &str) -> HierarchyBinding {
    HierarchyBinding::try_new(None, level, number, cc(component)).expect("binding")
}

// ------------------------------------------------ library presence oracle #

#[test]
fn presence_includes_admitted_components_with_zero_hidden() {
    let expression = test_expression();
    let mut membership = VersionedMembershipLog::empty();
    attach(&mut membership, "cc:test:glava-1", "cc:test:statya-4", 100);
    let mut presence = ComponentInExpressionLog::empty();
    include(&mut presence, &expression, "cc:test:statya-4", 100);

    let (visible, hidden) =
        edition_visibility_counts(&membership, &presence, &expression, 100).expect("counts");
    // glava (present descendant) + statya = the whole composition.
    assert_eq!(visible, 2, "visible == admitted");
    assert_eq!(hidden, 0, "no component is pruned");
}

#[test]
fn omitted_presence_prunes_cc_and_reports_hidden() {
    let expression = test_expression();
    let mut membership = VersionedMembershipLog::empty();
    attach(&mut membership, "cc:test:glava-1", "cc:test:statya-4", 100);
    attach(&mut membership, "cc:test:glava-1", "cc:test:statya-5", 100);
    // Only statya 4 is present: statya 5 must be pruned, never silently passed.
    let mut presence = ComponentInExpressionLog::empty();
    include(&mut presence, &expression, "cc:test:statya-4", 100);

    let (visible, hidden) =
        edition_visibility_counts(&membership, &presence, &expression, 100).expect("counts");
    assert_eq!(visible, 2, "glava + statya 4");
    assert!(hidden > 0, "the omitted CC must be reported hidden");
    assert_eq!(hidden, 1, "statya 5 is the only pruned composition CC");
}

// ----------------------------------------------------- library text CTV #

#[test]
fn ctv_resolves_a_single_body_text() {
    let mut map = HierarchyMap::empty();
    map.register(binding("statya", "4", "cc:test:statya-4"))
        .expect("register");
    let log = build_text_log_from_articles(
        &map,
        [(
            "statya",
            "4",
            Some("Требования к участникам"),
            "Участником закупки может быть любое лицо.",
        )],
        100,
        "amendingact:test-presence",
    );
    let counts = ctv_resolution_counts(&log, &[cc("cc:test:statya-4")], 100);
    assert_eq!(counts, (1, 0, 0), "one component resolves to one text");
}

#[test]
fn two_texts_of_one_cc_on_one_day_is_conflict() {
    let mut map = HierarchyMap::empty();
    map.register(binding("statya", "4", "cc:test:statya-4"))
        .expect("register");
    // Two different bodies for the same number on the same effect day.
    let log = build_text_log_from_articles(
        &map,
        [
            ("statya", "4", Some("Требования"), "первая редакция текста"),
            ("statya", "4", Some("Требования"), "вторая редакция текста"),
        ],
        100,
        "amendingact:test-presence",
    );
    let counts = ctv_resolution_counts(&log, &[cc("cc:test:statya-4")], 100);
    assert_eq!(counts, (0, 0, 1), "disagreeing same-day text is a Conflict");
}

#[test]
fn missing_text_is_unknown_not_fabricated() {
    let log = ln_kb_ontology::domain::TextVersionLog::empty();
    let counts = ctv_resolution_counts(&log, &[cc("cc:test:statya-4")], 100);
    assert_eq!(counts, (0, 1, 0), "absent text is a fail-closed Unknown");
}

#[test]
fn text_after_the_effect_day_is_unknown() {
    let mut map = HierarchyMap::empty();
    map.register(binding("statya", "4", "cc:test:statya-4"))
        .expect("register");
    let log = build_text_log_from_articles(
        &map,
        [("statya", "4", Some("Требования"), "текст")],
        200,
        "amendingact:test-presence",
    );
    // Asked before the only text event: no coverage, honest Unknown.
    let counts = ctv_resolution_counts(&log, &[cc("cc:test:statya-4")], 100);
    assert_eq!(counts, (0, 1, 0));
}

// ------------------------------------------------------- CLI AST/CTV bin #

#[test]
fn bin_ctv_assembly_payload_visible_equals_admitted_with_resolved_text() {
    let dir = TempDir::new("ctv-assembly");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_BODY_FIXTURE);
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t{}\n", wire.display()),
    )
    .expect("write tsv");

    let cli = EditionTimelineCli {
        editions: tsv.display().to_string(),
        mode: AssemblyMode::Assembly,
        ctv: true,
        out: None,
    };
    let (code, message) = run_edition_timeline(&cli);
    assert_eq!(code, 0, "ctv assembly must succeed: {message}");
    assert!(message.is_ascii(), "payload must be ASCII");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["schema"], AST_CTV_SCHEMA);
    assert_eq!(payload["editions"], 1);
    let point = &payload["per_edition"][0];
    assert_eq!(point["hidden"], 0, "presence covers every admitted child");
    assert_eq!(point["visible"], point["admitted"], "visible == admitted");
    assert_eq!(point["admitted"], 2, "glava + statya");
    assert!(
        point["ctv_resolved"].as_u64().unwrap() >= 1,
        "the statya body must resolve: {point}"
    );
    assert_eq!(point["ctv_unknown"], 0);
    assert_eq!(point["ctv_conflict"], 0);
    let claims = payload["non_claims"].as_array().expect("non_claims array");
    assert!(
        claims
            .iter()
            .any(|claim| claim == "presence_log_is_oracle_synthesized_not_expression_inheritance"),
        "the oracle-synthesized presence non-claim must be declared"
    );
}

#[test]
fn bin_ctv_is_deterministic() {
    let dir = TempDir::new("ctv-det");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_BODY_FIXTURE);
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t{}\n", wire.display()),
    )
    .expect("write tsv");
    let cli = EditionTimelineCli {
        editions: tsv.display().to_string(),
        mode: AssemblyMode::Assembly,
        ctv: true,
        out: None,
    };
    let (first_code, first) = run_edition_timeline(&cli);
    let (second_code, second) = run_edition_timeline(&cli);
    assert_eq!(first_code, 0);
    assert_eq!(second_code, 0);
    assert_eq!(first, second, "render must be deterministic");
}

#[test]
fn bin_ctv_with_chain_mode_is_usage_error() {
    let dir = TempDir::new("ctv-chain");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_BODY_FIXTURE);
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t{}\n", wire.display()),
    )
    .expect("write tsv");
    let output = run_bin(&[
        "--editions",
        &tsv.display().to_string(),
        "--mode",
        "chain",
        "--ctv",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn bin_ctv_with_missing_wire_is_unreadable() {
    let dir = TempDir::new("ctv-missing");
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t/nonexistent/m224-s06/0118.jsonl\n"),
    )
    .expect("write tsv");
    let output = run_bin(&["--editions", &tsv.display().to_string(), "--ctv"]);
    assert_eq!(
        output.status.code(),
        Some(i32::from(
            ln_consultant_parser::edition_timeline::EXIT_INPUT_UNREADABLE
        ))
    );
}

// -------------------------------------------------- corpus-gated oracle #

#[test]
fn corpus_44fz_edition_0118_ast_ctv() {
    let xml_path = repo_root().join(CORPUS_44FZ_REL);
    let Ok(xml) = fs::read(&xml_path) else {
        eprintln!("SKIP: consru_export edition-0118 not available");
        return;
    };
    let dir = TempDir::new("44fz-0118-ctv");
    let artifact = build_wire(&xml);
    let wire = dir.path().join("0118.jsonl");
    fs::write(&wire, artifact).expect("write wire");
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t{}\n", wire.display()),
    )
    .expect("write tsv");

    let cli = EditionTimelineCli {
        editions: tsv.display().to_string(),
        mode: AssemblyMode::Assembly,
        ctv: true,
        out: None,
    };
    let (code, message) = run_edition_timeline(&cli);
    assert_eq!(code, 0, "corpus ctv must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    let point = &payload["per_edition"][0];
    assert!(
        point["visible"].as_u64().unwrap() > 0,
        "presence must retain the committed composition: {point}"
    );
    assert_eq!(point["hidden"], 0, "every admitted child is present");
    assert_eq!(point["visible"], point["admitted"]);
    assert!(
        point["ctv_resolved"].as_u64().unwrap() > 0,
        "some statya text must resolve: {point}"
    );
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
}

// ------------------------------------------------- negative self-checks #

#[test]
fn ast_ctv_non_claims_are_declared() {
    assert!(
        AST_CTV_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("presence_log_is_oracle_synthesized"))
    );
    assert!(
        AST_CTV_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("missing_text_is_a_fail_closed_unknown"))
    );
    assert!(
        AST_CTV_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("text_ctv_is_raw_text"))
    );
}
