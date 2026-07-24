use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc13-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc13_runner_error:unknown_scenario"));
}

#[test]
fn bound_unknown_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc13-runner"))
        .arg("bound-unknown-pauses")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc13-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"bound-unknown-pauses\""));
    assert!(stdout.contains("\"decision\":\"paused\""));
    assert!(stdout.contains("\"reason\":\"bound-unknown\""));
    assert!(stdout.contains("\"capacity_unknown\":true"));
    assert!(stdout.contains("\"pass\":true"));
}
