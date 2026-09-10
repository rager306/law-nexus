use ln_consultant_parser::promotion_gate::binding_for_paths;
use std::{fs, path::Path};

#[test]
fn binding_is_sha256_over_sorted_content_hash_lines() {
    let root = std::env::temp_dir().join(format!("ln-promotion-{}", std::process::id()));
    fs::create_dir_all(&root).unwrap();
    fs::write(root.join("b"), b"bravo").unwrap();
    fs::write(root.join("a"), b"alpha").unwrap();
    let actual = binding_for_paths(&root, &["b", "a"]).unwrap();
    let expected = std::process::Command::new("sh")
        .arg("-c")
        .arg("printf '%s\\n' $(sha256sum a | cut -d' ' -f1) $(sha256sum b | cut -d' ' -f1) | sha256sum | cut -d' ' -f1")
        .current_dir(&root)
        .output()
        .unwrap();
    let expected = format!(
        "sha256:{}",
        String::from_utf8_lossy(&expected.stdout).trim()
    );
    assert_eq!(actual, expected);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn binding_changes_when_input_changes() {
    let root = std::env::temp_dir().join(format!("ln-promotion-stale-{}", std::process::id()));
    fs::create_dir_all(&root).unwrap();
    fs::write(root.join("input"), b"before").unwrap();
    let first = binding_for_paths(&root, &["input"]).unwrap();
    fs::write(root.join("input"), b"after").unwrap();
    assert_ne!(first, binding_for_paths(&root, &["input"]).unwrap());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn contract_constants_keep_unknown_scope_outside_gate_surface() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let gates = fs::read_to_string(root.join("prd/architecture/npa-promotion-gates.json")).unwrap();
    assert!(!gates.contains("\"capability\":\"system\""));
    assert!(gates.contains("\"corpus_scope\":\"C4-full-diagnostics\""));
}

#[test]
fn durable_receipts_are_complete_and_blocked() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let receipts = fs::read_to_string(
        root.join("prd/migration/rust-evidence/m203-s09-promotion-receipts.jsonl"),
    )
    .unwrap();
    assert_eq!(receipts.lines().count(), 24);
    assert!(receipts
        .lines()
        .all(|line| line.contains("\"schema\":\"npa-promotion-receipts/v1\"")));
    assert!(receipts
        .lines()
        .all(|line| line.contains("\"human_acceptance\":null")));
    assert!(receipts
        .lines()
        .all(|line| line.contains("\"outcome\":\"blocked-")));
    assert!(receipts
        .lines()
        .all(|line| line.contains("\"requirement_debt\":[\"R035\",\"R070\"]")));
}
