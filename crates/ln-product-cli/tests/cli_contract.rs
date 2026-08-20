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
        inspect_u64(&stdout, "hierarchy_markers") >= bound as u64,
        "marker count must be >= YAML bindings ({bound}); got: {}",
        stdout
    );
    assert!(
        inspect_u64(&stdout, "hierarchy_lifts_unknown")
            <= inspect_u64(&stdout, "hierarchy_markers"),
        "435-FZ sub-article markers (chast/punkt) are Unknown (not registered); got: {}",
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
        "435-FZ statya markers produce no attach (forest); sub-markers are Unknown; got: {}",
        stdout
    );
    assert!(
        inspect_u64(&stdout, "membership_quarantined") <= inspect_u64(&stdout, "hierarchy_markers"),
        "435-FZ sub-article markers (chast/punkt) are Unknown; quarantined > 0 is expected; got: {}",
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
    assert!(
        inspect_u64(&stdout, "hierarchy_markers") >= bound as u64,
        "marker count must be >= YAML bindings; sub-article markers add to count; {stdout}"
    );
    assert_eq!(
        inspect_u64(&stdout, "hierarchy_lifts_bound"),
        bound as u64,
        "every listed 402-FZ marker must bind; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "hierarchy_lifts_unknown")
            <= inspect_u64(&stdout, "hierarchy_markers"),
        "402-FZ sub-article markers (chast/punkt) are Unknown; got: {}",
        stdout
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
    assert!(
        inspect_u64(&stdout, "membership_quarantined") <= inspect_u64(&stdout, "hierarchy_markers"),
        "402-FZ sub-article markers may quarantine (chast/punkt unregistered); got: {}",
        stdout
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

#[test]
fn inspect_path_aware_classifier_counts_federal_law_amendment() {
    let tmp = std::env::temp_dir().join(format!(
        "federalnyi-zakon-s03-classifier-{}.xml",
        std::process::id()
    ));
    let xml = r#"<?xml version="1.0" encoding="UTF-8"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
<w:body>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr>
  <w:r><w:t>(в ред. </w:t></w:r>
  <w:hlink w:dest="consultantplus://offline/ref=TOKEN360">
    <w:r><w:t>N 360-ФЗ</w:t></w:r>
  </w:hlink>
  <w:r><w:t>)</w:t></w:r>
</w:p>
</w:body>
</w:wordDocument>"#;
    std::fs::write(&tmp, xml).expect("write classifier fixture");
    let out = Command::new(binary())
        .args(["inspect", tmp.to_str().unwrap()])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    let _ = std::fs::remove_file(&tmp);
    assert!(
        out.status.success(),
        "inspect must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert_eq!(
        inspect_u64(&stdout, "hyperlink_count"),
        1,
        "fixture must expose one hyperlink; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "edge_amends") >= 1,
        "path-aware inspect must classify «в ред. ФЗ» as amends; {stdout}"
    );
}

#[test]
fn replay_same_file_402_fz_reports_zero_facet_drafts() {
    // M170 S02 T02: light replay contract on the tracked 402-FZ fixture
    // (not the demo pair — that is covered skip-capably in real_44fz_text_ctv).
    let fixture = accounting_fixture();
    let out = Command::new(binary())
        .args(["replay", &fixture, &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "same-file replay must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Replay\""),
        "expected Replay phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"status\":\"ok\""),
        "expected ok status; got: {}",
        stdout
    );
    // Same file -> identical texts -> 0 drafts, with a real (non-empty)
    // expression_id: a legitimate zero, not a masked failure.
    assert_eq!(
        inspect_u64(&stdout, "facet_drafts"),
        0,
        "same-file replay must report zero text-facet drafts; {stdout}"
    );
    assert!(
        stdout.contains("expr:ru:federal:zakon:2011-12-06:402-fz"),
        "expression_id must carry the minted 402-fz expression; {stdout}"
    );
    // S02 (M174): presence channel must be visible in replay JSON —
    // edition_ast_at (membership fold + presence fold + filter) is part
    // of the bounded replay report, not a hidden domain path.
    assert!(
        stdout.contains("\"presence\":{\"visible\":"),
        "replay must report the presence channel; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "visible") >= 1,
        "same-file replay must have at least one visible CC; {stdout}"
    );
    assert!(
        !stdout.contains("ОБЩИЕ ПОЛОЖЕНИЯ"),
        "raw legal text must not be persisted; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

#[test]
fn replay_missing_args_exits_with_usage_error_code() {
    for args in [vec!["replay"], vec!["replay", "/tmp/seed.xml"]] {
        let out = Command::new(binary())
            .args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .expect("spawn");
        assert!(!out.status.success(), "replay {args:?} must fail");
        assert_eq!(out.status.code(), Some(2), "replay {args:?} must exit 2");
    }
}

// ─── M171 S03 T02: subordinate-acts report ─────────────────────────────────

fn pp60_fixture() -> String {
    [
        env!("CARGO_MANIFEST_DIR"),
        "..",
        "..",
        "law-source",
        "garant",
        "PP_60_27-01-2022.odt",
    ]
    .iter()
    .collect::<std::path::PathBuf>()
    .to_string_lossy()
    .into_owned()
}

/// Amendment ПП 2368 (Cyrillic-only filename, lettered subunits): hostile
/// fail-closed fixture. The filename carries no latin path needle, so the
/// inspect pack must NOT mint a group or invent punkt units out of lettered
/// а/б (or any) subunits.
fn amendment_pp2368_fixture() -> String {
    [
        env!("CARGO_MANIFEST_DIR"),
        "..",
        "..",
        "law-source",
        "garant",
        "Постановление Правительства РФ от 29 декабря 2023 г N 2368 О внесении изменений .odt",
    ]
    .iter()
    .collect::<std::path::PathBuf>()
    .to_string_lossy()
    .into_owned()
}

/// Bounded subordinate-acts report (M171 S03 T02): the binary reports CC
/// punkt counts and resolve_ctv counters for a real ПП file without any
/// YAML registry bindings and without the edition-day registry (both are
/// federal_law-only). The report is counts-only JSON — no raw legal text.
#[test]
fn subordinates_report_on_tracked_pp_is_bounded_json() {
    let fixture = pp60_fixture();
    if !std::path::Path::new(&fixture).exists() {
        eprintln!("SKIP: Garant corpus not available");
        return;
    }
    let out = Command::new(binary())
        .args(["subordinates", "resolution", &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "subordinates must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Subordinates\""),
        "expected Subordinates phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"status\":\"ok\""),
        "expected ok status; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"document_group\":\"government_resolution\""),
        "kind=resolution must bind government_resolution; got: {}",
        stdout
    );
    // Visible skip state: the document date is derivable from the filename,
    // so the report is NOT skipped and the skip_reason is empty.
    assert!(
        stdout.contains("\"skip_reason\":\"\""),
        "skip_reason must be empty when the date parses; got: {}",
        stdout
    );
    // CC punkt count and resolve_ctv counters (the slice report contract).
    assert!(
        inspect_u64(&stdout, "punkt_units") > 0,
        "punkt_units must be positive; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "cc_punkts") > 0,
        "cc_punkts must be positive; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "ctv_resolved") > 0,
        "ctv_resolved must be positive; {stdout}"
    );
    assert!(
        inspect_u64(&stdout, "effect_day") > 0,
        "effect_day must be a valid ordinal; {stdout}"
    );
    // Bounded non-claims and no raw legal text in the counts-only report.
    assert!(
        stdout.contains("Fixture-minted CCs are test-local, not registry identity"),
        "non_claims must document the fixture boundary; {stdout}"
    );
    assert!(
        !stdout.contains("Утвердить прилагаемые"),
        "raw legal text must not leak into the report; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

/// S02 first proof: the thin `inspect` (kind=None) resolves punkt-as-unit
/// text-CTV on the tracked Garant reference ПП_60 file. The `pp_` path
/// needle binds government_resolution; ctv_resolved counts unique Resolved
/// on the YAML punkt granularity. Fixture CCs stay local (membership
/// registry is federal_law-only) and the JSON must not grow punkt_units/
/// cc_punkts keys (that is the subordinates schema, R063 thin inspect).
#[test]
fn inspect_pp60_reports_punkt_ctv_resolved() {
    let fixture = pp60_fixture();
    if !std::path::Path::new(&fixture).exists() {
        eprintln!("SKIP: Garant corpus not available");
        return;
    }
    let out = Command::new(binary())
        .args(["inspect", &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "inspect PP_60 must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"phase\":\"Inspect\""),
        "expected Inspect phase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"status\":\"ok\""),
        "expected ok status; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"document_group\":\"government_resolution\""),
        "pp_ path needle must bind government_resolution with kind=None; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "detection_unknown"),
        0,
        "PP_60 must not be Unknown; got: {}",
        stdout
    );
    assert!(
        inspect_u64(&stdout, "ctv_resolved") > 0,
        "punkt text-CTV must resolve > 0; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_committed"),
        0,
        "fixture CCs must not enter the membership registry (PP has none); got: {}",
        stdout
    );
    // R063 thin inspect: no subordinates-schema keys, no raw legal text.
    assert!(
        !stdout.contains("\"punkt_units\":"),
        "inspect must not emit the subordinates punkt_units key (R063); got: {}",
        stdout
    );
    assert!(
        !stdout.contains("\"cc_punkts\":"),
        "inspect must not emit the subordinates cc_punkts key (R063); got: {}",
        stdout
    );
    assert!(
        stdout.contains(
            "punct-grade (punkt) text-CTV uses a local fixture CC map, not the membership registry"
        ),
        "non_claims must document the fixture-CC / registry boundary; got: {}",
        stdout
    );
    assert!(
        !stdout.contains("Утвердить прилагаемые"),
        "raw legal text must not leak; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

/// S02 hostile fail-closed: an amendment ПП with a Cyrillic-only filename
/// (no latin path needle) and lettered а/б subunits must NOT mint a bound
/// government_resolution or invent punkt CTV units. `inspect` reports the
/// honest Unknown quarantine (detection_unknown=1, ctv_resolved=0) — never
/// silence and never a synthetic group on an unbound executive path.
#[test]
fn inspect_amendment_pp2368_stays_fail_closed() {
    let fixture = amendment_pp2368_fixture();
    if !std::path::Path::new(&fixture).exists() {
        eprintln!("SKIP: Garant corpus not available");
        return;
    }
    let out = Command::new(binary())
        .args(["inspect", &fixture])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn");
    assert!(
        out.status.success(),
        "inspect ПП 2368 must exit 0; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert!(
        stdout.contains("\"document_group\":\"Unknown\""),
        "unbound Cyrillic-only amendment must quarantine as an explicit Unknown group, not a guessed one; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "detection_unknown"),
        1,
        "Cyrillic-only amendment must stay detection-Unknown (no latin needle), never later silently; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "hierarchy_markers"),
        0,
        "lettered а/б (and any) subunits must not mint unit markers on a no-bound path; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "ctv_resolved"),
        0,
        "hostile fail-closed: a no-bound amendment must resolve no CTV rather than invent punkt units; got: {}",
        stdout
    );
    assert_eq!(
        inspect_u64(&stdout, "membership_committed"),
        0,
        "no fixture CCs may enter the membership ledger on an Unknown path; got: {}",
        stdout
    );
    assert!(
        !stdout.contains("Утвердить прилагаемые"),
        "raw legal text must not leak; got first 400 chars: {}",
        &stdout[..stdout.len().min(400)]
    );
}

#[test]
fn subordinates_missing_args_exits_with_usage_error_code() {
    for args in [vec!["subordinates"], vec!["subordinates", "resolution"]] {
        let out = Command::new(binary())
            .args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .expect("spawn");
        assert!(!out.status.success(), "subordinates {args:?} must fail");
        assert_eq!(
            out.status.code(),
            Some(2),
            "subordinates {args:?} must exit 2"
        );
    }
}
