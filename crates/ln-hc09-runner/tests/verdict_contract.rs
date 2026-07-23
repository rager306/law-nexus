use std::process::Command;

#[test]
fn verdict_mode_executes_hc09_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc09-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc09-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-09-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-09\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":3"));
    assert!(stdout.contains("\"matrix_all_clocks_reject_substitution\":true"));
    assert!(stdout.contains("\"missing_anchor_without_substitutes\":true"));
    assert!(stdout.contains("\"present_anchor_resolves\":true"));
    assert!(stdout.contains("\"wall_clock_never_authorizes\":true"));
    assert!(stdout.contains("\"substitution_never_used\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":11"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"applicable_law_claimed\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
