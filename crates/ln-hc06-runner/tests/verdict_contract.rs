use std::process::Command;

#[test]
fn verdict_mode_executes_hc06_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc06-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc06-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-06-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-06\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":3"));
    assert!(stdout.contains("\"confidence_only_reject\":true"));
    assert!(stdout.contains("\"in_place_reject\":true"));
    assert!(stdout.contains("\"accepted_new_outcome\":true"));
    assert!(stdout.contains("\"original_type_preserved\":true"));
    assert!(stdout.contains("\"gate_version_ok\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":14"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"confidence_threshold_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
