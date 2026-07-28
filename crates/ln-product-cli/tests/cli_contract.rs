use std::process::{Command, Stdio};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_law-nexus-inspect")
}

fn consultant_fixture() -> String {
    [env!("CARGO_MANIFEST_DIR"), "..", "..", "law-source", "consultant",
     "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml"]
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
        stdout.contains("\"blocks\":167"),
        "expected 167 blocks; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"hierarchy_markers\":22"),
        "expected 22 hierarchy markers; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"reference_mentions\":69"),
        "expected 69 references; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"temporal_phrases\":1"),
        "expected 1 temporal phrase; got: {}",
        stdout
    );
    assert!(
        stdout.contains("\"deontic_lexemes\":4"),
        "expected 4 deontic lexemes; got: {}",
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

    let _ = std::fs::remove_file(&tmp);
}
