use std::process::Command;

#[test]
fn verdict_mode_executes_hc08_checks_and_emits_pass_or_fail() {
    let output = Command::new(env!("CARGO_BIN_EXE_ln-hc08-runner"))
        .arg("verdict")
        .output()
        .expect("run verdict");
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("utf8");
    assert!(stdout.contains("\"schema\":\"law-nexus-hc08-verdict/v1\""));
    assert!(stdout.contains("\"evidence_id\":\"S10-HC-08-RT\""));
    assert!(stdout.contains("\"case_id\":\"HC-08\""));
    assert!(stdout.contains("\"verdict\":\"PASS\""));
    assert!(stdout.contains("\"scenario_count\":3"));
    assert!(stdout.contains("\"unknown_predicate_reject\":true"));
    assert!(stdout.contains("\"wrong_owner_reject\":true"));
    assert!(stdout.contains("\"correct_owner_accept\":true"));
    assert!(stdout.contains("\"registry_unchanged_on_reject\":true"));
    assert!(stdout.contains("\"rejected_not_query_facts\":true"));
    assert!(stdout.contains("\"remaining_unsupported_cases\":12"));
    assert!(stdout.contains("\"product_storage_selected\":false"));
    assert!(stdout.contains("\"graph_schema_selected\":false"));
    assert!(stdout.contains("\"lifecycle\":\"[bounded]\""));
}
