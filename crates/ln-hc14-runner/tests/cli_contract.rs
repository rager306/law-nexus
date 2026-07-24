use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc14-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc14_runner_error:unknown_scenario"));
}

#[test]
fn suppress_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc14-runner"))
        .arg("first-apply-then-suppress")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc14-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"first-apply-then-suppress\""));
    assert!(stdout.contains("\"outcome\":\"suppressed\""));
    assert!(stdout.contains("\"effect_suppressed\":true"));
    assert!(stdout.contains("\"applied_count\":1"));
    assert!(stdout.contains("\"pass\":true"));
}
