use std::process::Command;

#[test]
fn verdict_mode_executes_hc12_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc12-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc12-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-12-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-12\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":5"));
    assert!(stdout.contains("\"partial_non_authoritative\":true"));
    assert!(stdout.contains("\"stale_cancelled_failed_matrix\":true"));
    assert!(stdout.contains("\"rebuilt_disposable_non_authoritative\":true"));
    assert!(stdout.contains("\"hostile_demotion\":true"));
    assert!(stdout.contains("\"hostile_cannot_hide_gaps\":true"));
    assert!(stdout.contains("\"publication_authority_never_granted\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":8"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"projection_store_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
