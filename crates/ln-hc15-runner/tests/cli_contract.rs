use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc15-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc15_runner_error:unknown_scenario"));
}

#[test]
fn first_complete_publish_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc15-runner"))
        .arg("first-complete-publish")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc15-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"first-complete-publish\""));
    assert!(stdout.contains("\"outcome\":\"published\""));
    assert!(stdout.contains("\"authoritative\":true"));
    assert!(stdout.contains("\"authoritative_count\":1"));
    assert!(stdout.contains("\"pass\":true"));
}

#[test]
fn hostile_scenario_emits_rejection_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc15-runner"))
        .arg("hostile-dual-writer-one-authority")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc15-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"hostile-dual-writer-one-authority\""));
    assert!(stdout.contains("\"authoritative\":false"));
    assert!(stdout.contains("\"authoritative_count\":1"));
    assert!(stdout.contains("\"pass\":true"));
}
