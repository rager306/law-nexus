use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc05-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc05_runner_error:unknown_scenario"));
}

#[test]
fn honest_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc05-runner"))
        .arg("honest-structural-only")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc05-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"honest-structural-only\""));
    assert!(stdout.contains("\"candidate_count\":1"));
    assert!(stdout.contains("\"raw_payload_absent\":true"));
    assert!(stdout.contains("\"positive_control_present\":true"));
    assert!(stdout.contains("\"pass\":true"));
}
