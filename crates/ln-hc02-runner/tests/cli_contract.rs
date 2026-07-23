use std::process::Command;

fn runner() -> Command {
    Command::new(env!("CARGO_BIN_EXE_ln-hc02-runner"))
}

#[test]
fn inventory_and_re_inventory_emit_bounded_receipts() {
    let first = runner().arg("inventory").output().expect("run inventory");
    assert!(first.status.success());
    let first_out = String::from_utf8(first.stdout).expect("utf8");
    assert!(first_out.contains("\"schema\":\"law-nexus-hc02-receipt/v1\""));
    assert!(first_out.contains("\"case_id\":\"HC-02\""));
    assert!(first_out.contains("\"attempt_count\":1"));
    assert!(first_out.contains("\"disposition\":\"pending\""));
    assert!(first_out.contains("\"visibility\":\"inventory-review\""));
    assert!(first_out.contains("\"input_digest\":\"fnv1a64:"));
    assert!(first_out.contains("\"curated_label_absent\":true"));
    assert!(first_out.contains("\"current_label_absent\":true"));
    assert!(first_out.contains("\"promotion_id_absent\":true"));
    assert!(first_out.contains("\"publication_id_absent\":true"));
    assert!(!first_out.contains("SYNTHETIC-IMMUTABLE-DROP"));

    // re-inventory scenario executes two inventories in one process and reports
    // the second observation, proving append-only history without product storage.
    let second = runner()
        .arg("re-inventory")
        .output()
        .expect("run re-inventory");
    assert!(second.status.success());
    let second_out = String::from_utf8(second.stdout).expect("utf8");
    assert!(second_out.contains("\"attempt_count\":2"));
    assert!(second_out.contains("\"disposition\":\"pending\""));
    assert!(second_out.contains("\"visibility\":\"inventory-review\""));
    let digest_key = "\"input_digest\":\"";
    let d1 = first_out
        .split(digest_key)
        .nth(1)
        .unwrap()
        .split('"')
        .next()
        .unwrap();
    let d2 = second_out
        .split(digest_key)
        .nth(1)
        .unwrap()
        .split('"')
        .next()
        .unwrap();
    assert_eq!(d1, d2);
    assert!(!second_out.contains("SYNTHETIC-IMMUTABLE-DROP"));
}

#[test]
fn unknown_scenario_is_typed_failure() {
    let output = runner().arg("unknown").output().expect("run");
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(String::from_utf8(output.stdout).unwrap(), "");
    assert_eq!(
        String::from_utf8(output.stderr).unwrap(),
        "hc02_runner_error:unknown_scenario\n"
    );
}
