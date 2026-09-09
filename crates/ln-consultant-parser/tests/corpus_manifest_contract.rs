use ln_consultant_parser::corpus_manifest::{self, Admission};

fn repo_path(relative: &str) -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(relative)
}

const C2: &str = "prd/migration/rust-evidence/m203-s08-c2-bounded-manifest.json";
const C3: &str = "prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json";

#[test]
fn frozen_manifests_load_with_provider_caps_and_claim_ceiling() {
    let c2 = corpus_manifest::load(&repo_path(C2)).expect("C2 loader");
    let c3 = corpus_manifest::load(&repo_path(C3)).expect("C3 loader");
    assert_eq!(c2.entries.len(), 40);
    // Garant availability is capped at four holdout documents (D439), so the
    // frozen C3 manifest is 32 Consultant + 4 Garant rather than an invented
    // quota of 40 entries.
    assert_eq!(c3.entries.len(), 36);
    assert_eq!(c2.stratum, "C2");
    assert_eq!(c3.stratum, "C3");
    assert_eq!(c2.provider_strata["garant"], 8);
    assert!(c3.sealed);
    assert!(c3
        .entries
        .iter()
        .all(|e| matches!(e.admission, Admission::HoldoutSealed)));
    assert!(corpus_manifest::disjoint(&c2, &c3));
}

#[test]
fn hostile_unknown_key_and_raw_anchor_fail_closed() {
    let dir = std::env::temp_dir().join(format!("npa-manifest-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let base = r#"{"schema_version":"law-nexus-npa-corpus-manifest/v1","manifest_id":"NPA-MAN-C2-X","stratum":"C2","parser_revision":"r","corpus_snapshot_hash":"sha256:x","provider_strata":[],"environment":{"platform":"x","rust_toolchain":"x","command":"x"},"entries":[],"lifecycle":"[bounded]","sealed":false,"draw_seed":1,"nesting_rule":"x","unknown":1}"#;
    let p = dir.join("hostile.json");
    std::fs::write(&p, base).unwrap();
    assert!(corpus_manifest::load(&p).is_err());
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn digest_pin_rejects_byte_change() {
    let source = std::fs::read_to_string(repo_path(C3)).unwrap();
    let dir = std::env::temp_dir().join(format!("npa-digest-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let p = dir.join("c3.json");
    std::fs::write(
        &p,
        source.replace("NPA-MAN-C3-M203-S08", "NPA-MAN-C3-CHANGED"),
    )
    .unwrap();
    assert!(corpus_manifest::load(&p).is_err());
    let _ = std::fs::remove_dir_all(dir);
}
