use std::process::Command;

#[test]
fn verdict_mode_executes_hc03_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc03-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc03-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-03-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-03\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":2"));
    assert!(stdout.contains("\"pending_rejects_promotion\":true"));
    assert!(stdout.contains("\"quarantined_rejects_promotion\":true"));
    assert!(stdout.contains("\"no_curated_commit\":true"));
    assert!(stdout.contains("\"authority_absent\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":17"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
