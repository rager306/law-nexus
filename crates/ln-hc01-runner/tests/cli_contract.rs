use std::process::Command;

fn runner() -> Command {
    Command::new(env!("CARGO_BIN_EXE_ln-hc01-runner"))
}

#[test]
fn four_hc01_scenarios_emit_bounded_json_receipts() {
    let cases = [
        ("timeout", "timeout", true),
        ("cancelled", "cancelled", false),
        ("transport-or-tls-failure", "transport-or-tls-failure", true),
        ("access-restricted", "access-restricted", false),
    ];

    for (scenario, outcome, retryable) in cases {
        let output = runner().arg(scenario).output().expect("run HC-01 binary");
        assert!(output.status.success(), "scenario={scenario}");
        let stdout = String::from_utf8(output.stdout).expect("UTF-8 stdout");
        let stderr = String::from_utf8(output.stderr).expect("UTF-8 stderr");

        assert_eq!(stderr, "");
        assert!(stdout.starts_with('{') && stdout.trim_end().ends_with('}'));
        assert!(stdout.contains("\"schema\":\"law-nexus-hc01-receipt/v1\""));
        assert!(stdout.contains("\"case_id\":\"HC-01\""));
        assert!(stdout.contains(&format!("\"outcome\":\"{outcome}\"")));
        assert!(stdout.contains(&format!("\"retryable\":{retryable}")));
        assert!(stdout.contains("\"work_phases\":[\"started\",\"observation-failed\"]"));
        assert!(stdout.contains("\"authority_absent\":true"));
        assert!(stdout.contains("\"legal_clock_anchor_absent\":true"));
        assert!(stdout.contains("\"promotion_id_absent\":true"));
        assert!(stdout.contains("\"publication_id_absent\":true"));
        assert!(stdout.contains("\"partial_fingerprint\":\"fnv1a64:"));
        assert!(!stdout.contains("HC01-RAW-PARTIAL-CANARY"));
    }
}

#[test]
fn unknown_scenario_is_a_typed_bounded_failure() {
    let output = runner().arg("unknown").output().expect("run HC-01 binary");

    assert_eq!(output.status.code(), Some(2));
    assert_eq!(String::from_utf8(output.stdout).expect("stdout"), "");
    let stderr = String::from_utf8(output.stderr).expect("stderr");
    assert_eq!(stderr, "hc01_runner_error:unknown_scenario\n");
}
