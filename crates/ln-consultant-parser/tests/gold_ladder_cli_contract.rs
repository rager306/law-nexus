use std::{
    fs,
    path::Path,
    process::Command,
    time::{SystemTime, UNIX_EPOCH},
};

fn temp_root(label: &str) -> std::path::PathBuf {
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let path = std::env::temp_dir().join(format!("ln-gold-ladder-{label}-{stamp}"));
    fs::create_dir_all(&path).expect("temporary root");
    path
}

fn write_inventory(root: &Path, garant: &Path) {
    for i in 0..1_000u32 {
        let path = root.join(format!("courts/acn/{i:06}-edition-{i:064x}.xml"));
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, format!("synthetic-consultant-{i}")).unwrap();
    }
    for i in 0..8u32 {
        let path = garant.join(format!("Постановление от 15 октября 2022 г N {i}.odt"));
        fs::write(path, format!("synthetic-garant-{i}")).unwrap();
    }
}

fn run(root: &Path, garant: &Path, out: &Path, seed: &str, extra: &[&str]) -> std::process::Output {
    let mut args = vec![
        "--root",
        root.to_str().unwrap(),
        "--garant-root",
        garant.to_str().unwrap(),
        "--out",
        out.to_str().unwrap(),
        "--seed",
        seed,
    ];
    args.extend_from_slice(extra);
    Command::new(env!("CARGO_BIN_EXE_npa-gold-ladder"))
        .args(args)
        .output()
        .expect("run npa-gold-ladder")
}

#[test]
fn synthetic_inventory_writes_three_rungs_and_seed_changes_draw() {
    let root = temp_root("consultant");
    let garant = temp_root("garant");
    let out = temp_root("out");
    write_inventory(&root, &garant);

    let first = run(&root, &garant, &out, "20308", &[]);
    assert!(
        first.status.success(),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    for rung in [100, 400, 800] {
        let manifest =
            fs::read_to_string(out.join(format!("m204-s02-c5-gold-manifest-{rung}.json"))).unwrap();
        assert!(manifest.contains("\"draw_seed\":20308"));
        assert_eq!(manifest.matches("\"entry_id\"").count(), rung);
    }
    let leakage = fs::read_to_string(out.join("m204-s03-sample-leakage.json")).unwrap();
    assert!(leakage.contains("m204-s03-sample-leakage/v1"));
    assert!(leakage.contains("not a Work-family holdout"));

    let second_out = temp_root("out-second");
    let second = run(&root, &garant, &second_out, "7", &["--rung", "100"]);
    assert!(
        second.status.success(),
        "{}",
        String::from_utf8_lossy(&second.stderr)
    );
    let left = fs::read_to_string(out.join("m204-s02-c5-gold-manifest-100.json")).unwrap();
    let right = fs::read_to_string(second_out.join("m204-s02-c5-gold-manifest-100.json")).unwrap();
    assert_ne!(left, right, "seed must be reflected in the selected set");

    let _ = fs::remove_dir_all(root);
    let _ = fs::remove_dir_all(garant);
    let _ = fs::remove_dir_all(out);
    let _ = fs::remove_dir_all(second_out);
}

#[test]
fn malformed_options_exit_two_before_writes() {
    let root = temp_root("invalid-root");
    let garant = temp_root("invalid-garant");
    let out = temp_root("invalid-out");
    write_inventory(&root, &garant);

    let missing_seed = run(&root, &garant, &out, "--rung", &[]);
    assert_eq!(missing_seed.status.code(), Some(2));
    assert_eq!(fs::read_dir(&out).unwrap().count(), 0);

    let invalid_rung = run(&root, &garant, &out, "20308", &["--rung", "c3"]);
    assert_eq!(invalid_rung.status.code(), Some(2));
    assert_eq!(fs::read_dir(&out).unwrap().count(), 0);

    let _ = fs::remove_dir_all(root);
    let _ = fs::remove_dir_all(garant);
    let _ = fs::remove_dir_all(out);
}
