use std::process::Command;

#[test]
fn verdict_mode_executes_hc11_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc11-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc11-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-11-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-11\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":7"));
    assert!(stdout.contains("\"complete_eligible\":true"));
    assert!(stdout.contains("\"incomplete_missing_blocks\":true"));
    assert!(stdout.contains("\"unknown_seed_blocks\":true"));
    assert!(stdout.contains("\"unbounded_fanout_blocks\":true"));
    assert!(stdout.contains("\"rule_version_mismatch_blocks\":true"));
    assert!(stdout.contains("\"forbidden_claim_matrix\":true"));
    assert!(stdout.contains("\"hostile_freeze_holds\":true"));
    assert!(stdout.contains("\"progress_never_completeness\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":9"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"dependency_index_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
