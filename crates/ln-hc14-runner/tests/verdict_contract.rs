use std::process::Command;

#[test]
fn verdict_mode_executes_hc14_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc14-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc14-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-14-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-14\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":5"));
    assert!(stdout.contains("\"first_apply_then_suppress\":true"));
    assert!(stdout.contains("\"corrupt_fail_closed\":true"));
    assert!(stdout.contains("\"incompatible_rule\":true"));
    assert!(stdout.contains("\"incomplete_missing\":true"));
    assert!(stdout.contains("\"hostile_no_duplicate\":true"));
    assert!(stdout.contains("\"publication_authority_never_granted\":true"));
    assert!(stdout.contains("\"lineage_never_rewritten\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":6"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"checkpoint_store_selected\":false"));
    assert!(stdout.contains("\"exactly_once_infra_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
