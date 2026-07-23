use std::process::Command;

#[test]
fn verdict_mode_executes_hc02_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc02-runner"))
        .arg("verdict")
        .output()
        .expect("run HC-02 verdict mode");

    assert!(output.status.success());
    assert_eq!(String::from_utf8(output.stderr).expect("stderr"), "");
    let stdout = String::from_utf8(output.stdout).expect("stdout");
    assert!(stdout.starts_with('{') && stdout.trim_end().ends_with('}'));
    assert!(stdout.contains("\"schema\":\"law-nexus-hc02-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-02-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-02\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":2"));
    assert!(stdout.contains("\"stable_digest\":true"));
    assert!(stdout.contains("\"append_only_attempts\":true"));
    assert!(stdout.contains("\"staging_visibility_only\":true"));
    assert!(stdout.contains("\"authority_absent\":true"));
    assert!(stdout.contains("\"raw_canary_absent\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":18"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
    assert!(!stdout.contains("SYNTHETIC-IMMUTABLE-DROP"));
}
