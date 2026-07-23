use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc09-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc09_runner_error:unknown_scenario"));
}

#[test]
fn matrix_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc09-runner"))
        .arg("matrix-all-clocks-reject-substitution")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc09-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"matrix-all-clocks-reject-substitution\""));
    assert!(stdout.contains("\"outcome\":\"substitute-rejected\""));
    assert!(stdout.contains("\"wall_clock_rejected\":true"));
    assert!(stdout.contains("\"pass\":true"));
}
