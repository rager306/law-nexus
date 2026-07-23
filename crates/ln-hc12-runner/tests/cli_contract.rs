use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc12-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc12_runner_error:unknown_scenario"));
}

#[test]
fn partial_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc12-runner"))
        .arg("partial-non-authoritative")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc12-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"partial-non-authoritative\""));
    assert!(stdout.contains("\"outcome\":\"partial\""));
    assert!(stdout.contains("\"authoritative\":false"));
    assert!(stdout.contains("\"pass\":true"));
}
