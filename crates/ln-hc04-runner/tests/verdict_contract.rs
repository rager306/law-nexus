use std::process::Command;

#[test]
fn verdict_mode_executes_hc04_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc04-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc04-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-04-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-04\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":3"));
    assert!(stdout.contains("\"cancel_no_effect\":true"));
    assert!(stdout.contains("\"identical_retry_one_commit\":true"));
    assert!(stdout.contains("\"mismatch_reject\":true"));
    assert!(stdout.contains("\"one_d116_effect\":true"));
    assert!(stdout.contains("\"publication_authority_absent\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":16"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
