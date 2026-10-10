//! M222-nshb29 S04 T03: audit of the remaining R29-F07 sub-claims.
//!
//! Two sub-claims are covered here and they are not homogeneous.
//!
//! **F07(b) — diagnostic determinism — is refuted.** The cleaned verifier runs
//! a fixed check order (source pin -> parent seal pin -> projection semantics
//! -> text channel -> counts); its `HashMap`s are used for lookup only and the
//! emitting loops walk the ordered `package.records()` / `readback.segments`
//! `Vec`s, and `verify_counts` sums an ordered `Vec`. The CLI verify path reads
//! no clock, locale or environment value. Two independent runs over the same
//! input therefore produce byte-identical diagnostics.
//!
//! **F07(c) — analysis capability/version/schema admission — regression.**
//! The historical M222 audit reproduced a bounded structure-only gap. These
//! tests now require typed rejection by inspection, read-back and full
//! verification, even after independent resealing. Historical receipts retain
//! the old `f07c_*_tamper_passes_structure_only` names; the corresponding live
//! tests are named `f07c_*_tamper_is_rejected`. No frozen envelope is modified.
//!
//! Fixtures are inline synthetic non-legal WordML plus tracked reader
//! fixtures. Only counts and closed tokens appear in assertions; raw decoded
//! legal text is never logged.

use std::fs;
use std::path::PathBuf;

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::cleaned_cli::{parse_cleaned_args, run_cleaned_with, EXIT_OK, EXIT_VERIFY_FAILED};
use ln_decode::cleaned_verifier::{verify_cleaned_wire, CleanedVerifyCode};
use ln_decode::cleaned_wire::{
    export_cleaned_projection, read_cleaned_wire, WireCompletion, WireLimits,
};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::{analyze_document, DocumentAnalysis};
use ln_decode::npa_analysis_verify::{
    read_back_npa_analysis, verify_npa_analysis_wire, AnalysisVerifyCode,
};
use ln_decode::npa_analysis_wire::{
    inspect_npa_analysis_wire, render_npa_analysis, AnalysisEnvelopeRequest, AnalysisLimits,
    AnalysisScope, AnalysisWireErrorKind,
};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, write_package, Limits, Package, Record};
use sha2::{Digest, Sha256};

const MIXED: &str = include_str!("fixtures/reader/mixed-wordml.xml");
const TEXT_ONLY: &str = include_str!("fixtures/reader/diverse/text-only.xml");

// ------------------------------------------------------------- F07(b) setup #

fn package_for(xml: &str) -> Package {
    capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture")
}

fn artifact_for(package: &Package) -> String {
    let projection = build_projection(package.records()).expect("fixture must project");
    export_cleaned_projection(
        package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export")
}

/// Replaces one ASCII letter in the first text record that has one, keeping the
/// code-point and byte counts identical (so only the text channel can see it).
fn replace_first_ascii_letter(records: &mut [Record]) -> bool {
    for record in records.iter_mut() {
        if let Record::Text(text) = record {
            let mut chars: Vec<char> = text.value.chars().collect();
            if let Some(index) = chars.iter().position(|c| c.is_ascii_alphabetic()) {
                chars[index] = if chars[index] == 'a' { 'b' } else { 'a' };
                text.value = chars.into_iter().collect();
                return true;
            }
        }
    }
    false
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_dir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("ln-decode-m222-f07-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp root must be creatable");
    dir
}

// ------------------------------------------------------------- F07(b) audit #

/// F07(b) refuted: the cleaned verifier's diagnostics are deterministic. The
/// same artifact is verified twice against a deliberately broken parent (a
/// changed source pin, nulled parent seals and a mutated substrate text value)
/// and the returned findings are identical, code for code and detail for
/// detail, in the verifier's fixed check order. The canonical pair verifies
/// `Ok` on both runs.
#[test]
fn f07b_cleaned_verifier_diagnostics_are_deterministic() {
    let package = package_for(MIXED);
    let artifact = artifact_for(&package);
    assert!(
        read_cleaned_wire(&artifact).is_ok(),
        "the canonical artifact must read back"
    );

    // Positive control: the canonical pair verifies Ok on both runs.
    verify_cleaned_wire(&artifact, &package).expect("first canonical verify must pass");
    verify_cleaned_wire(&artifact, &package).expect("second canonical verify must pass");

    // Build a parent with three independent defects: a changed source pin,
    // nulled parent seals and a mutated text record.
    let mut records = package.records().to_vec();
    assert!(
        replace_first_ascii_letter(&mut records),
        "the fixture must carry a mutable text record"
    );
    let mut manifest = package.manifest().clone();
    manifest.source.sha256 = "a".repeat(64);
    manifest.source.bytes += 1;
    let mut footer = package.footer().clone();
    footer.records_seal_hash = None;
    footer.manifest_hash = None;
    let broken = Package::from_parts(manifest, records, footer);

    let first = verify_cleaned_wire(&artifact, &broken).expect_err("broken parent must refuse");
    let second = verify_cleaned_wire(&artifact, &broken).expect_err("broken parent must refuse");

    assert!(!first.is_empty(), "the negative control needs findings");
    assert_eq!(
        first, second,
        "two runs over the same input must produce identical findings"
    );

    let codes: Vec<CleanedVerifyCode> = first.iter().map(|finding| finding.code).collect();
    // Fixed order: source pin -> parent seal pin -> ... -> text channel.
    assert_eq!(codes[0], CleanedVerifyCode::ParentSourcePinMismatch);
    assert_eq!(codes[1], CleanedVerifyCode::ParentSealPinMismatch);
    assert!(
        codes.contains(&CleanedVerifyCode::TextChannelMismatch),
        "the mutated text record must surface a text-channel finding"
    );
}

/// F07(b) refuted at the CLI boundary: two runs of `cleaned-project verify`
/// over the same artifact/package pair emit byte-identical stdout and stderr,
/// both for a clean pair and for a mismatched pair that reports findings.
#[test]
fn f07b_cli_verify_output_is_deterministic() {
    let dir = temp_dir("cli-determinism");

    let mixed_package = dir.join("mixed.pkg.jsonl");
    let mut package_bytes = Vec::new();
    write_package(&package_for(MIXED), &mut package_bytes, &Limits::default())
        .expect("package must write");
    fs::write(&mixed_package, &package_bytes).expect("package file");

    let mixed_artifact = dir.join("mixed.jsonl");
    fs::write(
        &mixed_artifact,
        artifact_for(&package_for(MIXED)).as_bytes(),
    )
    .expect("artifact file");

    let text_only_artifact = dir.join("text-only.jsonl");
    fs::write(
        &text_only_artifact,
        artifact_for(&package_for(TEXT_ONLY)).as_bytes(),
    )
    .expect("artifact file");

    for (tag, artifact_path, expected) in [
        ("clean", &mixed_artifact, EXIT_OK),
        ("mismatch", &text_only_artifact, EXIT_VERIFY_FAILED),
    ] {
        let cli = parse_cleaned_args(vec![
            "verify".to_string(),
            "--artifact".to_string(),
            artifact_path.to_string_lossy().into_owned(),
            "--package".to_string(),
            mixed_package.to_string_lossy().into_owned(),
        ])
        .expect("verify parses");

        let mut out_one = Vec::new();
        let mut err_one = Vec::new();
        let code_one = run_cleaned_with(&cli, &mut out_one, &mut err_one);

        let mut out_two = Vec::new();
        let mut err_two = Vec::new();
        let code_two = run_cleaned_with(&cli, &mut out_two, &mut err_two);

        assert_eq!(code_one, expected, "{tag}: first run exit code");
        assert_eq!(code_two, expected, "{tag}: second run exit code");
        assert_eq!(out_one, out_two, "{tag}: stdout must be byte-identical");
        assert_eq!(err_one, err_two, "{tag}: stderr must be byte-identical");
    }
}

// ------------------------------------------------------------- F07(c) setup #

fn wrap(body: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{body}</w:body></w:wordDocument>"
    )
}

/// A small synthetic non-legal body: it never names a real act.
const TYPED_BODY: &str = "<w:p><w:r><w:t>Example clause one</w:t></w:r></w:p>";

struct AnalysisPipeline {
    analysis: DocumentAnalysis,
    projection: ReaderProjection,
    index: ReaderRecordIndex,
    mapping: SourceMapping,
}

fn analysis_pipeline(xml: &str) -> AnalysisPipeline {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");
    let projection = build_projection(package.records()).expect("projection must build");
    let identity = SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        "law-nexus/source-package-model/v1".to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .expect("manifest identity must be well formed");
    let version = DocumentVersionRef::try_new(
        "doc-version-1".to_string(),
        "rev-1".to_string(),
        "reader_wordml_profile/v1".to_string(),
    )
    .expect("version triple must be well formed");
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .expect("every substrate fragment must pin");
    }
    let analysis = analyze_document(&projection, &index, &mapping).expect("analysis must build");
    AnalysisPipeline {
        analysis,
        projection,
        index,
        mapping,
    }
}

fn render_analysis(xml: &str) -> String {
    let pipeline = analysis_pipeline(xml);
    render_npa_analysis(&AnalysisEnvelopeRequest {
        analysis: &pipeline.analysis,
        projection: &pipeline.projection,
        index: &pipeline.index,
        mapping: &pipeline.mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    })
    .expect("a canonical analysis envelope must render")
}

// ------------------------------------------- F07(c) manifest-field helpers #
//
// The writer emits one compact ascending-key object per line. These helpers are
// local to the audit: the module under test shares none of this.

fn skip_value(line: &str, start: usize) -> usize {
    let bytes = line.as_bytes();
    let mut index = start;
    match bytes.get(index) {
        Some(b'"') => {
            index += 1;
            while index < bytes.len() {
                match bytes[index] {
                    b'\\' => index += 2,
                    b'"' => {
                        index += 1;
                        break;
                    }
                    _ => index += 1,
                }
            }
        }
        Some(b'{') | Some(b'[') => {
            let mut depth = 0usize;
            while index < bytes.len() {
                match bytes[index] {
                    b'"' => {
                        index += 1;
                        while index < bytes.len() {
                            match bytes[index] {
                                b'\\' => index += 2,
                                b'"' => {
                                    index += 1;
                                    break;
                                }
                                _ => index += 1,
                            }
                        }
                    }
                    b'{' | b'[' => {
                        depth += 1;
                        index += 1;
                    }
                    b'}' | b']' => {
                        depth = depth.saturating_sub(1);
                        index += 1;
                        if depth == 0 {
                            break;
                        }
                    }
                    _ => index += 1,
                }
            }
        }
        _ => {
            while index < bytes.len() {
                let byte = bytes[index];
                if byte == b',' || byte == b'}' || byte == b']' || byte.is_ascii_whitespace() {
                    break;
                }
                index += 1;
            }
        }
    }
    index
}

/// Replaces the raw value of the first top-level `key` in a wire line.
fn set_raw_value(line: &str, key: &str, new_raw: &str) -> String {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle).expect("field must exist") + needle.len();
    let end = skip_value(line, start);
    format!("{}{}{}", &line[..start], new_raw, &line[end..])
}

/// Replaces the raw value of the last occurrence of `key` (the manifest nests
/// `generator.version` and `parent.schema` before the top-level tokens).
fn set_last_raw_value(line: &str, key: &str, new_raw: &str) -> String {
    let needle = format!("\"{key}\":");
    let start = line.rfind(&needle).expect("field must exist") + needle.len();
    let end = skip_value(line, start);
    format!("{}{}{}", &line[..start], new_raw, &line[end..])
}

/// Rewrites only the manifest line (index 0), preserving the trailing LF.
fn tamper_manifest(document: &str, mutate: impl Fn(&str) -> String) -> String {
    let mut lines: Vec<String> = document
        .split_terminator('\n')
        .map(str::to_string)
        .collect();
    lines[0] = mutate(&lines[0]);
    format!("{}\n", lines.join("\n"))
}

/// Independent seal oracle: hashes wire bytes without production seal helpers
/// or the reader under test. The footer is a canonical flat object.
fn independently_reseal(document: &str) -> String {
    let mut lines: Vec<String> = document.lines().map(str::to_owned).collect();
    let last = lines.len() - 1;
    let footer_body = format!(
        "{{{}}}",
        lines[last]
            .trim_start_matches('{')
            .trim_end_matches('}')
            .split(',')
            .filter(|part| !part.starts_with("\"manifest_hash\":")
                && !part.starts_with("\"records_seal_hash\":"))
            .collect::<Vec<_>>()
            .join(",")
    );
    let records = format!("{:x}", Sha256::digest(lines[1..last].concat().as_bytes()));
    let manifest = format!(
        "{:x}",
        Sha256::digest(format!("{}\n{records}\n{footer_body}", lines[0]).as_bytes())
    );
    for (key, value) in [("manifest_hash", manifest), ("records_seal_hash", records)] {
        lines[last] = set_raw_value(&lines[last], key, &format!("\"{value}\""));
    }
    format!("{}\n", lines.join("\n"))
}

fn assert_resealed_manifest_is_rejected(canonical: &str, tampered: &str) {
    let pipeline = analysis_pipeline(&wrap(TYPED_BODY));
    assert_eq!(
        independently_reseal(canonical),
        canonical,
        "seal oracle baseline"
    );
    inspect_npa_analysis_wire(canonical).expect("canonical inspection must pass");
    read_back_npa_analysis(canonical).expect("canonical read-back must pass");
    verify_npa_analysis_wire(
        canonical,
        &pipeline.projection,
        &pipeline.index,
        &pipeline.mapping,
    )
    .expect("canonical full verification must pass");

    let resealed = independently_reseal(tampered);
    assert_ne!(
        resealed, tampered,
        "manifest tamper must require a new seal"
    );
    assert_eq!(
        inspect_npa_analysis_wire(&resealed)
            .expect_err("inspection must reject")
            .kind(),
        AnalysisWireErrorKind::EnvelopeStructural,
    );
    assert_eq!(
        read_back_npa_analysis(&resealed)
            .expect_err("read-back must reject")
            .kind(),
        AnalysisWireErrorKind::EnvelopeStructural,
    );
    let findings = verify_npa_analysis_wire(
        &resealed,
        &pipeline.projection,
        &pipeline.index,
        &pipeline.mapping,
    )
    .expect_err("full verification must reject independently resealed tamper");
    assert_eq!(
        findings
            .iter()
            .map(|finding| finding.code())
            .collect::<Vec<_>>(),
        vec![AnalysisVerifyCode::EnvelopeStructural],
        "admission must reject, not seal verification",
    );
}

// ------------------------------------------------------------- F07(c) audit #

/// F07(c): the canonical analysis envelope is accepted structure-only by both
/// `inspect_npa_analysis_wire` and `read_back_npa_analysis`.
#[test]
fn f07c_canonical_analysis_envelope_passes_structure_only() {
    let canonical = render_analysis(&wrap(TYPED_BODY));
    inspect_npa_analysis_wire(&canonical).expect("the canonical envelope must inspect");
    read_back_npa_analysis(&canonical).expect("the canonical envelope must read back");
}

/// F07(c) regression: a forged manifest `capability` is rejected after resealing.
#[test]
fn f07c_capability_tamper_is_rejected() {
    let canonical = render_analysis(&wrap(TYPED_BODY));
    let tampered = tamper_manifest(&canonical, |line| {
        set_raw_value(line, "capability", "\"forged_capability\"")
    });
    assert_ne!(
        tampered, canonical,
        "the capability tamper must change bytes"
    );
    assert_resealed_manifest_is_rejected(&canonical, &tampered);
}

/// F07(c) regression: a bumped manifest `version` is rejected after resealing.
#[test]
fn f07c_version_tamper_is_rejected() {
    let canonical = render_analysis(&wrap(TYPED_BODY));
    let tampered = tamper_manifest(&canonical, |line| set_last_raw_value(line, "version", "2"));
    assert_ne!(tampered, canonical, "the version tamper must change bytes");
    assert_resealed_manifest_is_rejected(&canonical, &tampered);
}

/// F07(c) regression: a forged manifest `schema` is rejected after resealing.
#[test]
fn f07c_schema_tamper_is_rejected() {
    let canonical = render_analysis(&wrap(TYPED_BODY));
    let tampered = tamper_manifest(&canonical, |line| {
        set_last_raw_value(line, "schema", "\"law-nexus/forged-manifest/v9\"")
    });
    assert_ne!(tampered, canonical, "the schema tamper must change bytes");
    assert_resealed_manifest_is_rejected(&canonical, &tampered);
}
