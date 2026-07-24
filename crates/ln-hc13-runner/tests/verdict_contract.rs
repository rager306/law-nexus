use std::process::Command;

#[test]
fn verdict_mode_executes_hc13_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc13-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc13-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-13-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-13\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":6"));
    assert!(stdout.contains("\"bound_unknown_pauses\":true"));
    assert!(stdout.contains("\"saturated_rejects\":true"));
    assert!(stdout.contains("\"retry_amplification_rejects\":true"));
    assert!(stdout.contains("\"measured_bound_admits\":true"));
    assert!(stdout.contains("\"hostile_vendor_rejects\":true"));
    assert!(stdout.contains("\"forbidden_inference_matrix\":true"));
    assert!(stdout.contains("\"vendor_number_never_used\":true"));
    assert!(stdout.contains("\"capacity_unknown_on_reject\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":7"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"queue_selected\":false"));
    assert!(stdout.contains("\"hardware_selected\":false"));
    assert!(stdout.contains("\"throughput_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
