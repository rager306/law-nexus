use std::process::Command;

#[test]
fn unknown_scenario_exits_2() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc10-runner"))
        .arg("not-a-scenario")
        .output()
        .expect("run");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf8");
    assert!(stderr.contains("hc10_runner_error:unknown_scenario"));
}

#[test]
fn cancel_resume_scenario_emits_receipt() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc10-runner"))
        .arg("cancel-resume-domain-unchanged")
        .output()
        .expect("run");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc10-receipt/v1\""));
    assert!(stdout.contains("\"scenario\":\"cancel-resume-domain-unchanged\""));
    assert!(stdout.contains("\"domain_unchanged\":true"));
    assert!(stdout.contains("\"pass\":true"));
}
