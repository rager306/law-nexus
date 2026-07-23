use std::process::Command;

#[test]
fn verdict_mode_executes_hc07_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc07-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc07-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-07-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-07\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":3"));
    assert!(stdout.contains("\"one_sided_reject\":true"));
    assert!(stdout.contains("\"similarity_only_reject\":true"));
    assert!(stdout.contains("\"bilateral_same_no_merge\":true"));
    assert!(stdout.contains("\"both_identities_survive\":true"));
    assert!(stdout.contains("\"no_merge_observation\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":13"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"similarity_model_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
