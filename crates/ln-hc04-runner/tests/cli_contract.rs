use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc04-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc04_runner_error:unknown_scenario"));
}

#[test]
fn cancel_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc04-runner"))
        .arg("cancel-no-effect")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc04-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"cancel-no-effect\""));
    assert!(stdout.contains("\"outcome\":\"cancelled\""));
    assert!(stdout.contains("\"committed_count\":0"));
    assert!(stdout.contains("\"curated_effect\":false"));
    assert!(stdout.contains("\"publication_authority_absent\":true"));
}
