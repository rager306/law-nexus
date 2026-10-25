//! T02 CLI contract (M213 S04): deterministic `cleaned-project` argv
//! semantics, atomic publication, counts-only read-back, and the
//! artifact/package verify pair.
//!
//! The strict stdlib parser and the runner live in `ln_decode::cleaned_cli`,
//! so this battery exercises library functions through the `run_cleaned_with`
//! writer seam instead of spawning a subprocess. It is a handwritten oracle:
//! it shares no code with the module under test beyond the public API.
//!
//! Fixtures are tracked synthetic non-legal WordML documents under
//! `tests/fixtures/reader/`; the temporary publication directory is
//! OS-provided and per-test unique. No decoded text is ever asserted against a
//! diagnostic output, and no corpus bytes are added.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::cleaned_cli::{
    CleanedCli, CleanedCommand, EXIT_INPUT_UNREADABLE, EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_USAGE,
    EXIT_VERIFY_FAILED, parse_cleaned_args, run_cleaned_with,
};
use ln_decode::cleaned_completion::ScopeDeclaration;
use ln_decode::cleaned_wire::{
    WireCompletion, WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture, write_package};

const MIXED: &str = include_str!("fixtures/reader/mixed-wordml.xml");
const TEXT_ONLY: &str = include_str!("fixtures/reader/diverse/text-only.xml");

// ---------------------------------------------------------------- helpers #

fn args(items: &[&str]) -> Vec<String> {
    items.iter().map(|item| (*item).to_string()).collect()
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_dir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "ln-decode-cleaned-cli-t02-{}-{tag}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp cli root must be creatable");
    dir
}

fn s(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn write_file(path: &Path, bytes: &[u8]) {
    fs::write(path, bytes).expect("fixture write must succeed");
}

/// Renders the cleaned artifact for `xml` directly through the frozen writer.
fn fixture_artifact(xml: &str) -> String {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    export_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export")
}

/// Serializes the frozen source package for `xml` into JSONL bytes.
fn package_bytes(xml: &str) -> Vec<u8> {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let mut out = Vec::new();
    write_package(&package, &mut out, &Limits::default()).expect("package must write");
    out
}

/// Runs the parsed invocation with captured writers.
fn run(cli: &CleanedCli) -> (u8, String, String) {
    let mut out = Vec::new();
    let mut err = Vec::new();
    let code = run_cleaned_with(cli, &mut out, &mut err);
    (
        code,
        String::from_utf8(out).expect("stdout is utf-8"),
        String::from_utf8(err).expect("stderr is utf-8"),
    )
}

fn has_tmp(dir: &Path) -> bool {
    fs::read_dir(dir)
        .expect("read dir")
        .filter_map(Result::ok)
        .any(|entry| entry.file_name().to_string_lossy().ends_with(".tmp"))
}

fn export_cli(xml_path: &Path, out_path: &Path) -> CleanedCli {
    parse_cleaned_args(args(&[
        "export",
        "--from-xml",
        &s(xml_path),
        "--out",
        &s(out_path),
    ]))
    .expect("export from xml parses")
}

// ------------------------------------------------------------- parsing #

#[test]
fn parse_defaults_and_overrides() {
    let cli = parse_cleaned_args(args(&["export", "--from-xml", "in.xml"]))
        .expect("export from xml parses");
    assert_eq!(cli.command, CleanedCommand::Export);
    assert_eq!(cli.from_xml.as_deref(), Some(Path::new("in.xml")));
    assert_eq!(cli.package, None);
    assert_eq!(cli.out, None);
    assert_eq!(cli.completion, ScopeDeclaration::WholeProjection);

    let cli = parse_cleaned_args(args(&[
        "export",
        "--package",
        "p.jsonl",
        "--completion",
        "hold",
        "--out",
        "o.jsonl",
    ]))
    .expect("export from package parses");
    assert_eq!(cli.package.as_deref(), Some(Path::new("p.jsonl")));
    assert_eq!(cli.out.as_deref(), Some(Path::new("o.jsonl")));
    assert_eq!(cli.completion, ScopeDeclaration::StructureHold);

    let cli = parse_cleaned_args(args(&["read", "--artifact", "a.jsonl"])).expect("read parses");
    assert_eq!(cli.command, CleanedCommand::Read);
    assert_eq!(cli.artifact.as_deref(), Some(Path::new("a.jsonl")));

    let cli = parse_cleaned_args(args(&[
        "verify",
        "--artifact",
        "a.jsonl",
        "--package",
        "p.jsonl",
    ]))
    .expect("verify parses");
    assert_eq!(cli.command, CleanedCommand::Verify);
    assert_eq!(cli.artifact.as_deref(), Some(Path::new("a.jsonl")));
    assert_eq!(cli.package.as_deref(), Some(Path::new("p.jsonl")));
}

#[test]
fn usage_errors_are_closed_and_deterministic() {
    assert_eq!(parse_cleaned_args(Vec::new()).unwrap_err(), EXIT_USAGE);
    assert_eq!(
        parse_cleaned_args(args(&["frobnicate"])).unwrap_err(),
        EXIT_USAGE
    );
    assert_eq!(
        parse_cleaned_args(args(&["export", "--from-xml", "x", "--bogus"])).unwrap_err(),
        EXIT_USAGE
    );
    // Missing flag value.
    assert_eq!(
        parse_cleaned_args(args(&["export", "--from-xml"])).unwrap_err(),
        EXIT_USAGE
    );
    // Export needs exactly one input.
    assert_eq!(
        parse_cleaned_args(args(&["export"])).unwrap_err(),
        EXIT_USAGE
    );
    assert_eq!(
        parse_cleaned_args(args(&["export", "--from-xml", "x", "--package", "p"])).unwrap_err(),
        EXIT_USAGE
    );
    // Unknown completion token (limit_reached is writer-only, not a declaration).
    assert_eq!(
        parse_cleaned_args(args(&[
            "export",
            "--from-xml",
            "x",
            "--completion",
            "limit_reached"
        ]))
        .unwrap_err(),
        EXIT_USAGE
    );
    // Read must not carry an export input.
    assert_eq!(
        parse_cleaned_args(args(&["read", "--artifact", "a", "--from-xml", "x"])).unwrap_err(),
        EXIT_USAGE
    );
    // Verify needs both artifact and package.
    assert_eq!(
        parse_cleaned_args(args(&["verify", "--artifact", "a"])).unwrap_err(),
        EXIT_USAGE
    );
}

// ------------------------------------------------------------- export #

#[test]
fn export_is_byte_identical_and_leaves_no_tmp() {
    let dir = temp_dir("export");
    let xml_path = dir.join("mixed.xml");
    write_file(&xml_path, MIXED.as_bytes());
    let out_path = dir.join("mixed.jsonl");
    let cli = export_cli(&xml_path, &out_path);

    let (code, out, err) = run(&cli);
    assert_eq!(code, EXIT_OK, "export failed: {err}");
    assert!(out.is_empty(), "file export must not write stdout");
    let first = fs::read(&out_path).expect("artifact must exist");

    let (code, _, err) = run(&cli);
    assert_eq!(code, EXIT_OK, "re-export failed: {err}");
    let second = fs::read(&out_path).expect("artifact must exist");
    assert_eq!(first, second, "repeated export must be byte-identical");
    assert!(!has_tmp(&dir), "export must leave no *.tmp");

    let text = String::from_utf8(first).expect("artifact is utf-8");
    assert!(
        read_cleaned_wire(&text).is_ok(),
        "published artifact must read back"
    );
}

#[test]
fn export_from_package_matches_from_xml() {
    let dir = temp_dir("export-package");
    let xml_path = dir.join("mixed.xml");
    write_file(&xml_path, MIXED.as_bytes());
    let package_path = dir.join("mixed.pkg.jsonl");
    write_file(&package_path, &package_bytes(MIXED));
    let from_xml_path = dir.join("from-xml.jsonl");
    let from_pkg_path = dir.join("from-package.jsonl");

    let (code, _, err) = run(&export_cli(&xml_path, &from_xml_path));
    assert_eq!(code, EXIT_OK, "xml export failed: {err}");
    let cli = parse_cleaned_args(args(&[
        "export",
        "--package",
        &s(&package_path),
        "--out",
        &s(&from_pkg_path),
    ]))
    .expect("export from package parses");
    let (code, _, err) = run(&cli);
    assert_eq!(code, EXIT_OK, "package export failed: {err}");

    let from_xml = fs::read(&from_xml_path).expect("xml artifact");
    let from_pkg = fs::read(&from_pkg_path).expect("package artifact");
    assert_eq!(
        from_xml, from_pkg,
        "the two export inputs must render the same artifact"
    );
}

#[test]
fn export_honours_completion_declaration() {
    let dir = temp_dir("export-completion");
    let xml_path = dir.join("mixed.xml");
    write_file(&xml_path, MIXED.as_bytes());
    let package_path = dir.join("mixed.pkg.jsonl");
    write_file(&package_path, &package_bytes(MIXED));

    // Both incomplete declarations must route through the writer (never around
    // it) and the published artifact must survive the independent `verify` path —
    // a CLI bypass that dropped or duplicated decoded text would be refused
    // there.
    for (token, basis) in [("hold", "hold"), ("text_only", "text_only")] {
        let out_path = dir.join(format!("{token}.jsonl"));
        let cli = parse_cleaned_args(args(&[
            "export",
            "--from-xml",
            &s(&xml_path),
            "--completion",
            token,
            "--out",
            &s(&out_path),
        ]))
        .expect("export parses");
        let (code, _, err) = run(&cli);
        assert_eq!(code, EXIT_OK, "{token}: export failed: {err}");

        let read =
            parse_cleaned_args(args(&["read", "--artifact", &s(&out_path)])).expect("read parses");
        let (code, out, err) = run(&read);
        assert_eq!(code, EXIT_OK, "{token}: read failed: {err}");
        assert!(out.contains("completion=incomplete"), "{token}: {out}");
        assert!(
            out.contains(&format!("completion_basis={basis}")),
            "{token}: {out}"
        );
        assert!(
            out.contains(&format!("incomplete_reasons={basis}")),
            "{token}: {out}"
        );

        let verify = parse_cleaned_args(args(&[
            "verify",
            "--artifact",
            &s(&out_path),
            "--package",
            &s(&package_path),
        ]))
        .expect("verify parses");
        let (code, out, err) = run(&verify);
        assert_eq!(code, EXIT_OK, "{token}: verify failed: {out}{err}");
        assert!(
            !out.contains("findings="),
            "{token}: a clean verify must not report findings: {out}"
        );
    }
}

#[test]
fn export_missing_input_is_unreadable() {
    let dir = temp_dir("export-missing");
    let cli = export_cli(&dir.join("absent.xml"), &dir.join("out.jsonl"));
    let (code, _, err) = run(&cli);
    assert_eq!(code, EXIT_INPUT_UNREADABLE, "stderr: {err}");
    assert!(err.contains("not_found"), "expected closed io token: {err}");
}

#[test]
fn export_to_missing_out_parent_is_unwritable() {
    let dir = temp_dir("export-bad-out");
    let xml_path = dir.join("mixed.xml");
    write_file(&xml_path, MIXED.as_bytes());
    let cli = export_cli(&xml_path, &dir.join("absent").join("out.jsonl"));
    let (code, _, err) = run(&cli);
    assert_eq!(code, EXIT_OUT_UNWRITABLE, "stderr: {err}");
    assert!(err.contains("write_failed"), "expected closed kind: {err}");
    assert!(!has_tmp(&dir), "refused publish must leave no *.tmp");
}

// --------------------------------------------------------------- read #

#[test]
fn read_prints_counts_only_without_raw_text() {
    let dir = temp_dir("read");
    let xml_path = dir.join("mixed.xml");
    write_file(&xml_path, MIXED.as_bytes());
    let out_path = dir.join("mixed.jsonl");
    let (code, _, err) = run(&export_cli(&xml_path, &out_path));
    assert_eq!(code, EXIT_OK, "export failed: {err}");

    let cli =
        parse_cleaned_args(args(&["read", "--artifact", &s(&out_path)])).expect("read parses");
    let (code, out, err) = run(&cli);
    assert_eq!(code, EXIT_OK, "read failed: {err}");
    assert!(out.contains("contract_version="), "unexpected: {out}");
    assert!(out.contains("completion=complete"), "unexpected: {out}");
    assert!(out.contains("text_chars="), "unexpected: {out}");
    assert!(out.contains("inline_chars="), "unexpected: {out}");

    for token in [
        "Alpha", "Gamma", "Epsilon", "Zeta", "Theta", "Kappa", "Lambda",
    ] {
        assert!(
            !out.contains(token),
            "read summary must not leak decoded text token {token:?}"
        );
        assert!(
            !err.contains(token),
            "read stderr must not leak decoded text token {token:?}"
        );
    }
}

#[test]
fn read_missing_artifact_fails_verify() {
    let dir = temp_dir("read-missing");
    let cli = parse_cleaned_args(args(&["read", "--artifact", &s(&dir.join("absent.jsonl"))]))
        .expect("read parses");
    let (code, _, err) = run(&cli);
    assert_eq!(code, EXIT_VERIFY_FAILED, "stderr: {err}");
    assert!(err.contains("not_found"), "expected closed io token: {err}");
}

// ------------------------------------------------------------- verify #

#[test]
fn verify_correct_pair_succeeds() {
    let dir = temp_dir("verify-ok");
    let package_path = dir.join("mixed.pkg.jsonl");
    write_file(&package_path, &package_bytes(MIXED));
    let artifact_path = dir.join("mixed.jsonl");
    write_file(&artifact_path, fixture_artifact(MIXED).as_bytes());

    let cli = parse_cleaned_args(args(&[
        "verify",
        "--artifact",
        &s(&artifact_path),
        "--package",
        &s(&package_path),
    ]))
    .expect("verify parses");
    let (code, out, err) = run(&cli);
    assert_eq!(code, EXIT_OK, "verify failed: {out}{err}");
    assert!(
        !out.contains("findings="),
        "clean verify must not report findings"
    );
}

#[test]
fn verify_mismatched_pair_reports_closed_code() {
    let dir = temp_dir("verify-mismatch");
    let mixed_package = dir.join("mixed.pkg.jsonl");
    write_file(&mixed_package, &package_bytes(MIXED));
    let text_artifact = dir.join("text.jsonl");
    write_file(&text_artifact, fixture_artifact(TEXT_ONLY).as_bytes());

    let cli = parse_cleaned_args(args(&[
        "verify",
        "--artifact",
        &s(&text_artifact),
        "--package",
        &s(&mixed_package),
    ]))
    .expect("verify parses");
    let (code, out, err) = run(&cli);
    assert_eq!(code, EXIT_VERIFY_FAILED, "stderr: {err}");
    let combined = format!("{out}{err}");
    assert!(
        combined.contains("findings="),
        "expected findings: {combined}"
    );
    assert!(
        combined.contains("parent_source_pin_mismatch"),
        "expected a closed verifier code: {combined}"
    );
}

#[test]
fn verify_rejects_contract_and_version_tamper() {
    let dir = temp_dir("verify-admission");
    let package_path = dir.join("mixed.pkg.jsonl");
    write_file(&package_path, &package_bytes(MIXED));
    let artifact = fixture_artifact(MIXED);

    // A forged closed contract value (model) and a non-canonical JSON number
    // (`version:01`) are both refused by the full verifier. The envelope
    // admission check runs before seal recomputation, so the artifact's own
    // seals are never trusted.
    let forged_model = artifact.replacen(
        "law-nexus/cleaned-projection-model/v1",
        "law-nexus/cleaned-projection-model/v9",
        1,
    );
    let non_canonical = artifact.replacen("\"version\":1}", "\"version\":01}", 1);
    assert_ne!(
        forged_model, artifact,
        "the model tamper must change the artifact"
    );
    assert_ne!(
        non_canonical, artifact,
        "the version tamper must change the artifact"
    );

    for (tag, text) in [("model", &forged_model), ("version", &non_canonical)] {
        let artifact_path = dir.join(format!("{tag}.jsonl"));
        write_file(&artifact_path, text.as_bytes());
        let cli = parse_cleaned_args(args(&[
            "verify",
            "--artifact",
            &s(&artifact_path),
            "--package",
            &s(&package_path),
        ]))
        .expect("verify parses");
        let (code, out, err) = run(&cli);
        assert_eq!(code, EXIT_VERIFY_FAILED, "{tag}: stderr: {err}");
        let combined = format!("{out}{err}");
        assert!(
            combined.contains("artifact_unreadable"),
            "{tag}: expected the closed read-back refusal code: {combined}"
        );
    }
}
