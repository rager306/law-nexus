use std::process::Command;

fn runner() -> Command {
    Command::new(env!("CARGO_BIN_EXE_ln-hc03-runner"))
}

#[test]
fn pending_and_quarantined_emit_bounded_receipts() {
    for (scenario, state, outcome) in [
        ("pending-rejects", "pending", "rejected"),
        ("quarantined-rejects", "quarantined", "rejected"),
    ] {
        let output = runner().arg(scenario).output().expect("run");
        assert!(output.status.success(), "scenario={scenario}");
        let stdout = String::from_utf8(output.stdout).expect("utf8");
        assert!(stdout.contains("\"schema\":\"law-nexus-hc03-receipt/v1\""));
        assert!(stdout.contains("\"case_id\":\"HC-03\""));
        assert!(stdout.contains(&format!("\"disposition_state\":\"{state}\"")));
        assert!(stdout.contains(&format!("\"promotion_outcome\":\"{outcome}\"")));
        assert!(stdout.contains("\"commit_id_absent\":true"));
        assert!(stdout.contains("\"promotion_identity_absent\":true"));
        assert!(stdout.contains("\"product_storage_selected\":false"));
    }
}

#[test]
fn unknown_scenario_is_typed_failure() {
    let output = runner().arg("unknown").output().expect("run");
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(
        String::from_utf8(output.stderr).unwrap(),
        "hc03_runner_error:unknown_scenario\n"
    );
}
