use std::process::Command;

#[test]
fn verdict_mode_executes_hc05_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc05-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc05-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-05-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-05\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":2"));
    assert!(stdout.contains("\"honest_structural_only\":true"));
    assert!(stdout.contains("\"malicious_reject_all\":true"));
    assert!(stdout.contains("\"gate_owned_claims_absent\":true"));
    assert!(stdout.contains("\"raw_payload_absent\":true"));
    assert!(stdout.contains("\"positive_control_present\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":15"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"parser_format_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
