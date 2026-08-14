use std::process::{Command, Stdio};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_law-nexus-inspect")
}

fn yaml_binding_count_for_needle(needle: &str) -> usize {
    let yaml = include_str!("../../../prd/architecture/kb-hierarchy-registry.yaml");
    yaml.lines()
        .filter(|line| line.contains(&format!("path_needle: {needle}")) && line.contains("level:"))
        .count()
}

fn yaml_level_count_for_needle(needle: &str, level: &str) -> usize {
    let yaml = include_str!("../../../prd/architecture/kb-hierarchy-registry.yaml");
    yaml.lines()
        .filter(|line| {
            line.contains(&format!("path_needle: {needle}"))
                && line.contains(&format!("level: {level}"))
        })
        .count()
}

fn inspect_u64(stdout: &str, key: &str) -> u64 {
    let token = format!("\"{key}\":");
    let rest = stdout
        .split(&token)
        .nth(1)
        .unwrap_or_else(|| panic!("missing JSON key {key} in {stdout}"));
    let digits: String = rest.chars().take_while(|ch| ch.is_ascii_digit()).collect();
    digits
        .parse()
        .unwrap_or_else(|_| panic!("non-integer {key} in {stdout}"))
}

fn consultant_fixture() -> String {
    [env!("CARGO_MANIFEST_DIR"), "..", "..", "law-source", "consultant",
     "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml"]
        .iter()
        .collect::<std::path::PathBuf>()
        .to_string_lossy()
        .into_owned()
}

fn accounting_fixture() -> String {
    [env!("CARGO_MANIFEST_DIR"), "..", "..", "law-source", "consultant",
     "federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025-o-bukhgalterskom-uchete--fcc0b660.xml"]
        .iter()
        .collect::<std::path::PathBuf>()
        .to_string_lossy()
        .into_owned()
}

#[test]
fn health_command_emits_json_status() {
    let out = Command::new(binary())
        .arg("health")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(out.status.success(), "health must exit 0");
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(stdout.contains("\"status\":\"ok\""));
    assert!(stdout.contains("\"phase\":\"Health\""));
    assert!(stdout.contains("\"binary\":\"law-nexus-inspect\""));
    assert!(stdout.contains("\"runtime\":\"rust\""));
}

#[test]
fn inspect_real_consultant_fixture_reports_bounded_summary() {
    let fixture = consultant_fixture();
    let out = Command::new(binary())
        .args(["inspect", &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "inspect must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Inspect\""),
        "missing phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"status\":\"ok\""),
        "missing status; got: {}",
        stdout
    );
    assert!(
        inspect_u64(&stdout, "blocks") > 0,
        "inspect must report a positive block count; got: {}",
        stdout
    );
    let bound = yaml_binding_count_for_needle("n-435-fz");
    assert!(
        stdout.contains(&format!("\"hierarchy_markers\":{bound}")),
        "marker count must match YAML bindings ({bound}); got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"hierarchy_lifts_unknown\":0"),
        "scoped 435-FZ registry must bind markers; got: {}",
        stdout
    );
    assert!(
        stdout.contains(&format!("\"hierarchy_lifts_bound\":{bound}")),
        "scoped 435-FZ registry must bind every listed marker ({bound}); got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"hierarchy_lifts_rejected\":0"),
        "decode tokens must resolve through YAML aliases; got: {}",
        stdout
    );
    assert!(
        stdout.contains("Empty hierarchy registry yields Unknown"),
        "missing lift non-claim; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"membership_proposals\":0"),
        "articles-only 435-FZ is a forest: no attach drafts; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"membership_quarantined\":0"),
        "bound same-level markers must not quarantine; got: {}",
        stdout
    );
    assert!(
        stdout.contains(&format!("\"membership_forest_roots\":{bound}")),
        "each bound article is a forest root ({bound}); got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"membership_admitted\":0"),
        "articles-only 435-FZ admits no edges; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"membership_conflict_quarantined\":0"),
        "no conflicts in 435-FZ forest; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"ast_root_count\":0"),
        "435-FZ forest has no folded AST; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"ast_node_count\":0"),
        "435-FZ forest has no folded nodes; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"reference_mentions\":"),
        "inspect must report reference_mentions; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"temporal_phrases\":"),
        "inspect must report temporal_phrases; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"deontic_lexemes\":"),
        "inspect must report deontic_lexemes; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"retrieval_count\":"),
        "expected retrieval count; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"provider_comment_candidates\":0"),
        "expected ProviderComment exclusion; got: {}",
        stdout
    );
    assert!(
        !stdout.contains("Предмет регулирования"),
        "raw legal text must not be persisted; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

#[test]
fn inspect_402_fz_reports_non_zero_attach_from_yaml_ranks() {
    let fixture = accounting_fixture();
    let out = Command::new(binary())
        .args(["inspect", &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "inspect 402-FZ must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    let bound = yaml_binding_count_for_needle("n-402-fz");
    let glava = yaml_level_count_for_needle("n-402-fz", "glava");
    assert!(bound > 0, "402-FZ YAML registry must list bindings");
    assert!(
        glava > 0,
        "402-FZ YAML registry must list at least one glava"
    );
    assert_eq!(
        inspect_u64(&stdout, "hierarchy_markers"),
        bound as u64,
        "marker count must match YAML bindings; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "hierarchy_lifts_bound"),
        bound as u64,
        "every listed 402-FZ marker must bind; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "hierarchy_lifts_unknown"),
        0,
        "scoped 402-FZ registry must not leave Unknown; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "membership_proposals") > 0,
        "glava+statya 402-FZ must draft attach; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_forest_roots"),
        glava as u64,
        "forest roots must equal YAML glava count; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_quarantined"),
        0,
        "bound 402-FZ markers must not quarantine; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_admitted"),
        inspect_u64(&stdout, "membership_proposals"),
        "clean 402-FZ proposals must all survive the conflict gate; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_conflict_quarantined"),
        0,
        "402-FZ has no two-parent or cycle conflicts; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_committed"),
        inspect_u64(&stdout, "membership_admitted"),
        "all admitted 402-FZ edges must commit; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "ast_root_count"),
        glava as u64,
        "folded AST roots must equal glava count; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "ast_node_count"),
        bound as u64,
        "folded AST nodes must cover all bound markers; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "oracle_drift"),
        0,
        "402-FZ event log must reconstruct the oracle with zero drift; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "ctv_resolved") > 0,
        "402-FZ titled articles must produce resolvable CTVs; {stdout}"
    );
    assert!(
        stdout.contains("402-fz"),
        "expression_id must contain the act number (not synthetic fallback); {stdout}"
    );
    assert!(
        !stdout.contains("ОБЩИЕ ПОЛОЖЕНИЯ"),
        "raw legal text must not be persisted; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

#[test]
fn unknown_subcommand_exits_with_usage_error_code() {
    let out = Command::new(binary())
        .arg("no-such-command")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(!out.status.success());
    assert_eq!(out.status.code(), Some(2));
    let stdout = String::from_utf8(out.stdout).unwrap();
    let stderr = String::from_utf8(out.stderr).unwrap();
    assert!(
        stdout.contains("\"status\":\"failed\"") || stderr.contains("usage:"),
        "expected structured failure; stdout={} stderr={}",
        stdout,
        stderr
    );
}

#[test]
fn missing_path_argument_exits_with_usage_error_code() {
    let out = Command::new(binary())
        .arg("inspect")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(!out.status.success());
    assert_eq!(out.status.code(), Some(2));
}

#[test]
fn truncated_consultant_fixture_fails_atomically() {
    let path = consultant_fixture();
    let mut bytes = std::fs::read(&path).expect("fixture read");
    let tmp = std::env::temp_dir().join(format!("m138-truncated-{}.xml", std::process::id()));
    bytes.truncate(bytes.len().saturating_sub(128));
    std::fs::write(&tmp, &bytes).expect("write tmp");

    let out = Command::new(binary())
        .args(["inspect", tmp.to_str().unwrap()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");

    assert!(!out.status.success());
    assert_eq!(out.status.code(), Some(1));
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Parse\""),
        "expected parse-phase failure; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"status\":\"failed\""),
        "expected failed status; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"attempt_count\":1"),
        "expected attempt_count=1; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"fingerprint\":\"fnv1a64:"),
        "expected fingerprint; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"duration_ms\":"),
        "expected duration_ms; got: {}",
        stdout
    );

    let _ = std::fs::remove_file(&tmp);
}

#[test]
fn unsupported_format_rejected_as_parse_error() {
    let tmp = std::env::temp_dir().join(format!("m139-unsupported-{}.txt", std::process::id()));
    std::fs::write(&tmp, b"not legal text").expect("write tmp");
    let out = Command::new(binary())
        .args(["inspect", tmp.to_str().unwrap()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(!out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Parse\""),
        "expected parse phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"kind\":\"UnsupportedFamily\""),
        "expected UnsupportedFamily; got: {}",
        stdout
    );
    let _ = std::fs::remove_file(&tmp);
}

#[test]
fn empty_xml_file_produces_zero_blocks() {
    let tmp = std::env::temp_dir().join(format!("m139-empty-{}.xml", std::process::id()));
    std::fs::write(&tmp, b"").expect("write tmp");
    let out = Command::new(binary())
        .args(["inspect", tmp.to_str().unwrap()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "empty XML should produce zero blocks, not fail"
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"blocks\":0"),
        "expected 0 blocks; got: {}",
        stdout
    );
    let _ = std::fs::remove_file(&tmp);
}

#[test]
fn non_existent_file_rejected_as_io_error() {
    let out = Command::new(binary())
        .args(["inspect", "/nonexistent/path/file.xml"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(!out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Io\""),
        "expected Io phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"kind\":\"ReadFailure\""),
        "expected ReadFailure; got: {}",
        stdout
    );
}

#[test]
fn directory_as_path_rejected_as_io_error() {
    let out = Command::new(binary())
        .args(["inspect", "/tmp"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(!out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Io\""),
        "expected Io phase; got: {}",
        stdout
    );
}
