use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc06-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc06_runner_error:unknown_scenario"));
}

#[test]
fn confidence_only_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc06-runner"))
        .arg("confidence-only-reject")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc06-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"confidence-only-reject\""));
    assert!(stdout.contains("\"outcome\":\"insufficient-evidence\""));
    assert!(stdout.contains("\"reason\":\"confidence-only\""));
    assert!(stdout.contains("\"pass\":true"));
}
