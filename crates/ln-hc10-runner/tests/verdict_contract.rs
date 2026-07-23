use std::process::Command;

#[test]
fn verdict_mode_executes_hc10_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc10-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc10-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-10-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-10\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":4"));
    assert!(stdout.contains("\"cancel_resume_domain_unchanged\":true"));
    assert!(stdout.contains("\"stale_checkpoint_typed\":true"));
    assert!(stdout.contains("\"forbidden_legal_mapping_matrix\":true"));
    assert!(stdout.contains("\"hostile_freeze_holds\":true"));
    assert!(stdout.contains("\"legal_mapping_never_applied\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":10"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"workflow_engine_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
