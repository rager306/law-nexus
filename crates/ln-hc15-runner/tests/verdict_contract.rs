use std::process::Command;

#[test]
fn verdict_mode_executes_hc15_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc15-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc15-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-15-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-15\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":5"));
    assert!(stdout.contains("\"first_complete_publish\":true"));
    assert!(stdout.contains("\"identical_duplicate\":true"));
    assert!(stdout.contains("\"competing_writer_rejected\":true"));
    assert!(stdout.contains("\"partial_incomplete_non_authoritative\":true"));
    assert!(stdout.contains("\"hostile_dual_writer_one_authority\":true"));
    assert!(stdout.contains("\"authority_surface_publication_only\":true"));
    assert!(stdout.contains("\"one_authoritative_unit_per_scope\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":5"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"fencing_selected\":false"));
    assert!(stdout.contains("\"transaction_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
