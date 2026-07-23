use std::process::Command;

#[test]
fn verdict_mode_executes_all_hc01_scenarios_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc01-runner"))
        .arg("verdict")
        .output()
        .expect("run HC-01 verdict mode");

    assert!(output.status.success());
    assert_eq!(String::from_utf8(output.stderr).expect("stderr"), "");
    let stdout = String::from_utf8(output.stdout).expect("stdout");
    assert!(stdout.starts_with('{') && stdout.trim_end().ends_with('}'));
    assert!(stdout.contains("\"schema\":\"law-nexus-hc01-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-01-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-01\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":4"));
    assert!(stdout.contains("\"typed_outcomes\":true"));
    assert!(stdout.contains("\"failed_work_transitions\":true"));
    assert!(stdout.contains("\"safe_diagnostics\":true"));
    assert!(stdout.contains("\"authority_absent\":true"));
    assert!(stdout.contains("\"raw_canary_absent\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":19"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(!stdout.contains("HC01-RAW-PARTIAL-CANARY"));
}
