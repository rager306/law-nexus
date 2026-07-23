use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc07-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc07_runner_error:unknown_scenario"));
}

#[test]
fn one_sided_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc07-runner"))
        .arg("one-sided-reject")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc07-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"one-sided-reject\""));
    assert!(stdout.contains("\"outcome\":\"candidate\""));
    assert!(stdout.contains("\"reason\":\"one-sided-evidence\""));
    assert!(stdout.contains("\"merge_performed\":false"));
    assert!(stdout.contains("\"pass\":true"));
}
