//! M222 S04 cross-surface cleaned consumer admission battery.
//!
//! This is the end-to-end, count-only fail-closed admission proof: a consumer
//! (structure-only read, independent verifier, navigation builder + verifier,
//! and the `cleaned-project verify` CLI) may only be served by an artifact that
//! passed the independent verifier. It drives the *real* enabled pipeline over
//! one sha256-pinned synthetic, non-legal WordML fixture:
//! `capture -> gate_reader (SupportedWordml) -> build_projection ->
//! export_cleaned_projection(WireLimits::default(), Complete)`.
//!
//! The battery is a handwritten oracle: it shares no code with the module under
//! test beyond the public API. Every structural/semantic tamper is re-sealed
//! with the battery's own §7 oracle (recomputed over the exact rendered line
//! bytes) so the envelope stays internally consistent; only the independent
//! verifier can see the rewrite. Every diagnostic assertion is on closed
//! tokens/codes only — raw decoded text is never logged, only counts are.
//!
//! Negative controls, one per tamper class:
//!   * resealed manifest contract tamper (model/profile/capability/
//!     non_authoritative) -> `WireErrorKind::ContractFieldInvalid`;
//!   * non-canonical version token -> `WireErrorKind::VersionMismatch`;
//!   * resealed absent/tampered `policies.display_scope` ->
//!     `WireErrorKind::ContractFieldInvalid`;
//!   * resealed dropped inline under Hold ->
//!     `CleanedVerifyCode::TextChannelMembershipMismatch` (writer-side
//!     `TextLoss` is completion-neutral: the writer refuses a dropped text
//!     record only on the `Complete` branch, so the honest `Hold` artifact
//!     reads back and only the independent verifier can reject it).
//!
//! Non-claims: `[bounded]` to the one self-authored synthetic fixture named
//! here (not the 82-document corpus sweep). This is not corpus coverage, not
//! source authenticity and not legal completeness. Seals and counts are
//! integrity, not coverage. R1000 stays active/unclosed.

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

use ln_decode::cleaned_cli::{parse_cleaned_args, run_cleaned_with, EXIT_OK, EXIT_VERIFY_FAILED};
use ln_decode::cleaned_nav::{build_nav_index_from_wire, NavErrorKind};
use ln_decode::cleaned_nav_verifier::verify_nav_index;
use ln_decode::cleaned_verifier::{verify_cleaned_wire, CleanedFinding, CleanedVerifyCode};
use ln_decode::cleaned_wire::{
    export_cleaned_projection, read_cleaned_wire, IncompleteReason, WireCompletion, WireErrorKind,
    WireLimits, KIND_SEGMENT, KIND_VIEW,
};
use ln_decode::reader_gate::{gate_reader, ReaderSourceClass};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, write_package, Limits, Package};
use sha2::{Digest, Sha256};

// ---------------------------------------------------------------- fixture #

/// One sha256-pinned synthetic, non-legal WordML fixture. The pin is asserted
/// against the captured package manifest so a content drift fails loud.
const MIXED_XML: &str = include_str!("fixtures/reader/mixed-wordml.xml");
const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

// ------------------------------------------------------- real pipeline #

/// Drives the enabled pipeline exactly as the CLI export command does and
/// returns the frozen package, its projection and the canonical `Complete`
/// artifact rendered with the default limits.
fn pipeline() -> (Package, ReaderProjection, String) {
    let package =
        capture(MIXED_XML.as_bytes(), &Limits::default()).expect("the pinned fixture must capture");
    assert_eq!(
        package.manifest().source.sha256,
        MIXED_SHA256,
        "fixture content drift; re-pin the sha256 oracle"
    );
    let class = gate_reader(package.records()).expect("the fixture must gate as supported WordML");
    assert_eq!(class, ReaderSourceClass::SupportedWordml);
    let projection = build_projection(package.records()).expect("the fixture must project");
    let artifact = export_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("a gated, projected fixture must export");
    (package, projection, artifact)
}

// ---------------------------------------------------------- CLI seam #

static TEMP_SEQ: AtomicUsize = AtomicUsize::new(0);

/// Unique per-run temp root for the CLI `verify` pair, pre-cleaned so reruns
/// start empty.
fn unique_temp_dir(tag: &str) -> PathBuf {
    let seq = TEMP_SEQ.fetch_add(1, Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!(
        "ln-decode-consumer-admission-{}-{tag}-{seq}",
        std::process::id()
    ));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).expect("temp admission root must be creatable");
    dir
}

/// Exercises the real `cleaned-project verify` CLI seam
/// (`parse_cleaned_args` + `run_cleaned_with`) against on-disk artifact and
/// package files, returning `(exit_code, stdout, stderr)`.
fn cli_verify(artifact: &str, package: &Package) -> (u8, String, String) {
    let dir = unique_temp_dir("cli-verify");
    let artifact_path = dir.join("artifact.jsonl");
    let package_path = dir.join("package.jsonl");
    std::fs::write(&artifact_path, artifact).expect("artifact write must succeed");
    let mut package_bytes: Vec<u8> = Vec::new();
    write_package(package, &mut package_bytes, &Limits::default())
        .expect("package serialization must succeed");
    std::fs::write(&package_path, &package_bytes).expect("package write must succeed");

    let cli = parse_cleaned_args(vec![
        "verify".to_string(),
        "--artifact".to_string(),
        artifact_path.to_string_lossy().into_owned(),
        "--package".to_string(),
        package_path.to_string_lossy().into_owned(),
    ])
    .expect("the verify invocation must parse");

    let mut out: Vec<u8> = Vec::new();
    let mut err: Vec<u8> = Vec::new();
    let code = run_cleaned_with(&cli, &mut out, &mut err);
    let _ = std::fs::remove_dir_all(&dir);
    (
        code,
        String::from_utf8_lossy(&out).into_owned(),
        String::from_utf8_lossy(&err).into_owned(),
    )
}

// ------------------------------------------------- independent JSON reader #
//
// The writer emits one compact ascending-key object per line. This reader and
// oracle are local to the battery: the module under test shares none of it.

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

/// Top-level `(key, raw value)` pairs of one compact JSON object line.
fn parse_fields(line: &str) -> Vec<(&str, &str)> {
    let bytes = line.as_bytes();
    assert!(
        bytes.len() >= 2 && bytes[0] == b'{' && bytes[bytes.len() - 1] == b'}',
        "every wire line must be a compact JSON object"
    );
    let end = bytes.len() - 1;
    let mut entries: Vec<(&str, &str)> = Vec::new();
    let mut index = 1usize;
    while index < end {
        while index < end && bytes[index].is_ascii_whitespace() {
            index += 1;
        }
        if index >= end {
            break;
        }
        assert_eq!(bytes[index], b'"', "object key must be a JSON string");
        let key_start = index + 1;
        index += 1;
        let mut key_end = None;
        while index < bytes.len() {
            match bytes[index] {
                b'\\' => index += 2,
                b'"' => {
                    key_end = Some(index);
                    index += 1;
                    break;
                }
                _ => index += 1,
            }
        }
        let key = &line[key_start..key_end.expect("unterminated object key")];
        while index < end && bytes[index] != b':' {
            index += 1;
        }
        assert_eq!(bytes[index], b':');
        index += 1;
        while index < end && bytes[index].is_ascii_whitespace() {
            index += 1;
        }
        let value_start = index;
        index = skip_value(line, index);
        entries.push((key, &line[value_start..index]));
        while index < end && (bytes[index] == b',' || bytes[index].is_ascii_whitespace()) {
            index += 1;
        }
    }
    entries
}

fn unescape(raw: &str) -> Option<String> {
    let inner = raw.strip_prefix('"')?.strip_suffix('"')?;
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(ch) = chars.next() {
        if ch != '\\' {
            out.push(ch);
            continue;
        }
        match chars.next()? {
            '"' => out.push('"'),
            '\\' => out.push('\\'),
            'n' => out.push('\n'),
            'r' => out.push('\r'),
            't' => out.push('\t'),
            'b' => out.push('\u{8}'),
            'f' => out.push('\u{c}'),
            'u' => {
                let mut code = 0u32;
                for _ in 0..4 {
                    code = code * 16 + chars.next()?.to_digit(16)?;
                }
                out.push(char::from_u32(code)?);
            }
            _ => return None,
        }
    }
    Some(out)
}

/// Escapes a string exactly the way the canonical writer does (stable
/// `ensure_ascii=False`), so a battery-authored value is byte-compatible.
fn quote(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Top-level string field, unescaped.
fn str_field(line: &str, key: &str) -> Option<String> {
    parse_fields(line)
        .into_iter()
        .find(|(name, _)| *name == key)
        .and_then(|(_, value)| unescape(value))
}

fn kind_of(line: &str) -> Option<String> {
    str_field(line, "kind")
}

fn is_kind(line: &str, kind: &str) -> bool {
    kind_of(line).as_deref() == Some(kind)
}

/// Raw value slice for a key found anywhere in the line (top-level keys are
/// unique per line in this envelope).
fn raw_value<'a>(line: &'a str, key: &str) -> Option<&'a str> {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle)? + needle.len();
    let end = skip_value(line, start);
    Some(&line[start..end])
}

/// Replaces the raw value of a key in place, preserving key order and the rest
/// of the line byte-for-byte.
fn set_raw_value(line: &str, key: &str, new_raw: &str) -> String {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle).expect("field must exist") + needle.len();
    let end = skip_value(line, start);
    format!("{}{}{}", &line[..start], new_raw, &line[end..])
}

fn set_str_value(line: &str, key: &str, value: &str) -> String {
    set_raw_value(line, key, &quote(value))
}

/// Replaces the last occurrence of a top-level key's value. The manifest carries
/// a nested `generator.version` before the top-level `version`, so the last
/// occurrence is the manifest contract token.
fn set_last_raw_value(line: &str, key: &str, new_raw: &str) -> String {
    let needle = format!("\"{key}\":");
    let start = line.rfind(&needle).expect("field must exist") + needle.len();
    let end = skip_value(line, start);
    format!("{}{}{}", &line[..start], new_raw, &line[end..])
}

fn parse_str_array(raw: &str) -> Vec<String> {
    let trimmed = raw.trim();
    let inner = trimmed
        .strip_prefix('[')
        .and_then(|rest| rest.strip_suffix(']'))
        .expect("a JSON string array");
    let bytes = inner.as_bytes();
    let mut out = Vec::new();
    let mut index = 0usize;
    while index < bytes.len() {
        match bytes[index] {
            b',' | b' ' => index += 1,
            b'"' => {
                let start = index;
                index += 1;
                while index < bytes.len() && bytes[index] != b'"' {
                    if bytes[index] == b'\\' {
                        index += 1;
                    }
                    index += 1;
                }
                index += 1;
                out.push(unescape(&inner[start..index]).expect("array item is a string"));
            }
            _ => panic!("unexpected character in a string array"),
        }
    }
    out
}

fn render_str_array(items: &[String]) -> String {
    let rendered: Vec<String> = items.iter().map(|item| quote(item)).collect();
    format!("[{}]", rendered.join(","))
}

fn remove_str_array_item(raw: &str, victim: &str) -> String {
    let kept: Vec<String> = parse_str_array(raw)
        .into_iter()
        .filter(|item| item != victim)
        .collect();
    render_str_array(&kept)
}

// ------------------------------------------------------------ seal oracle #
//
// A handwritten §7 oracle: the same formulas as the writer, but computed here
// over the exact rendered line bytes. It never calls the module under test.

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn oracle_records_seal(lines: &[String]) -> String {
    let mut buffer: Vec<u8> = Vec::new();
    buffer.extend_from_slice(lines[1].as_bytes());
    for line in &lines[2..lines.len() - 1] {
        buffer.extend_from_slice(line.as_bytes());
    }
    sha256_hex(&buffer)
}

/// The footer with both seals nulled, exactly the bytes the writer hashes.
fn oracle_footer_body(footer: &str) -> String {
    let body = set_raw_value(footer, "records_seal_hash", "null");
    set_raw_value(&body, "manifest_hash", "null")
}

fn oracle_manifest_seal(lines: &[String], records_seal: &str) -> String {
    let mut buffer: Vec<u8> = Vec::new();
    buffer.extend_from_slice(lines[0].as_bytes());
    buffer.push(b'\n');
    buffer.extend_from_slice(records_seal.as_bytes());
    buffer.push(b'\n');
    buffer.extend_from_slice(oracle_footer_body(&lines[lines.len() - 1]).as_bytes());
    sha256_hex(&buffer)
}

fn oracle_reseal(lines: &mut [String]) {
    let records_seal = oracle_records_seal(lines);
    let manifest_seal = oracle_manifest_seal(lines, &records_seal);
    let footer = lines[lines.len() - 1].clone();
    let footer = set_str_value(&footer, "records_seal_hash", &records_seal);
    let footer = set_str_value(&footer, "manifest_hash", &manifest_seal);
    lines[lines.len() - 1] = footer;
}

fn lines_of(artifact: &str) -> Vec<String> {
    artifact
        .split_terminator('\n')
        .map(str::to_string)
        .collect()
}

fn join_lines(lines: &[String]) -> String {
    let mut out = String::new();
    for line in lines {
        out.push_str(line);
        out.push('\n');
    }
    out
}

/// Re-seals the mutated lines and returns the artifact. Callers assert that
/// `read_cleaned_wire` still accepts it: a re-sealed tamper is internally
/// consistent by construction.
fn resealed(lines: &[String]) -> String {
    let mut copy = lines.to_vec();
    oracle_reseal(&mut copy);
    join_lines(&copy)
}

/// Recomputes the §7 oracle seals over `lines` and asserts the footer carries
/// exactly them: proves a mutation was re-sealed into a self-consistent
/// envelope before the consumer was asked to reject it.
fn assert_seals_recompute(lines: &[String]) {
    let records_seal = oracle_records_seal(lines);
    let manifest_seal = oracle_manifest_seal(lines, &records_seal);
    let footer = lines.last().expect("footer");
    assert_eq!(
        str_field(footer, "records_seal_hash").as_deref(),
        Some(records_seal.as_str()),
        "the resealed footer must carry the oracle records seal"
    );
    assert_eq!(
        str_field(footer, "manifest_hash").as_deref(),
        Some(manifest_seal.as_str()),
        "the resealed footer must carry the oracle manifest seal"
    );
}

// ------------------------------------------------------------ assertions #

fn codes(findings: &[CleanedFinding]) -> Vec<CleanedVerifyCode> {
    findings.iter().map(|finding| finding.code).collect()
}

fn first_source_segment_line(lines: &[String]) -> Option<usize> {
    lines.iter().position(|line| {
        is_kind(line, KIND_SEGMENT)
            && str_field(line, "origin").as_deref() == Some("source_fragment")
    })
}

fn declared_incomplete_completion(basis: IncompleteReason) -> WireCompletion {
    WireCompletion::Incomplete {
        basis,
        reasons: vec![basis],
    }
}

/// A structural refusal must fail closed at every consumer boundary: the
/// structure-only reader, the independent verifier, the navigation builder and
/// the CLI `verify` command.
fn assert_structural_refusal(artifact: &str, package: &Package, expected: WireErrorKind) {
    let error = read_cleaned_wire(artifact).expect_err("the tampered envelope must be refused");
    assert_eq!(error.kind(), expected, "closed wire kind");

    let findings = verify_cleaned_wire(artifact, package)
        .expect_err("the independent verifier must refuse an unreadable artifact");
    assert_eq!(
        codes(&findings),
        vec![CleanedVerifyCode::ArtifactUnreadable],
        "an unreadable artifact is a single closed finding"
    );
    assert_eq!(findings[0].detail, expected.as_str());

    let nav = build_nav_index_from_wire(artifact, package)
        .expect_err("the navigation consumer must be refused at the same boundary");
    assert_eq!(nav.kind(), NavErrorKind::ArtifactUnreadable);

    let (code, stdout, stderr) = cli_verify(artifact, package);
    assert_eq!(code, EXIT_VERIFY_FAILED, "CLI stderr: {stderr}");
    assert!(stdout.contains("findings=1"), "CLI stdout: {stdout}");
    // The CLI reports the closed verifier code; an unreadable artifact is the
    // single `artifact_unreadable` finding whose detail (in process above) is
    // the underlying wire kind.
    assert!(
        stdout.contains(&format!(
            "code={}",
            CleanedVerifyCode::ArtifactUnreadable.as_str()
        )),
        "CLI stdout must carry the closed verifier code: {stdout}"
    );
}

/// A re-sealed semantic tamper reads back but the independent verifier and the
/// CLI must refuse it with the named closed code.
fn assert_membership_refusal(artifact: &str, package: &Package) {
    assert!(
        read_cleaned_wire(artifact).is_ok(),
        "a re-sealed membership tamper stays internally consistent"
    );
    let findings = verify_cleaned_wire(artifact, package)
        .expect_err("the independent verifier must refuse a dropped text record");
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::TextChannelMembershipMismatch),
        "expected TextChannelMembershipMismatch, got {:?}",
        codes(&findings)
    );

    let (code, stdout, stderr) = cli_verify(artifact, package);
    assert_eq!(code, EXIT_VERIFY_FAILED, "CLI stderr: {stderr}");
    assert!(
        stdout.contains(&format!(
            "code={}",
            CleanedVerifyCode::TextChannelMembershipMismatch.as_str()
        )),
        "CLI stdout must carry the closed code: {stdout}"
    );
}

// -------------------------------------------------- positive admission #

#[test]
fn canonical_artifact_is_admitted_by_read_verify_and_nav() {
    let (package, _projection, artifact) = pipeline();

    let readback = read_cleaned_wire(&artifact).expect("the canonical artifact must read back");
    verify_cleaned_wire(&artifact, &package)
        .expect("the independent verifier must admit the canonical artifact");

    let index = build_nav_index_from_wire(&artifact, &package)
        .expect("the navigation consumer must admit the canonical artifact");
    verify_nav_index(&index, &readback, &package)
        .expect("the navigation verifier must admit the canonical artifact");
}

#[test]
fn canonical_artifact_is_admitted_by_cli_verify() {
    let (package, _projection, artifact) = pipeline();
    let (code, stdout, stderr) = cli_verify(&artifact, &package);
    assert_eq!(code, EXIT_OK, "CLI stderr: {stderr}");
    assert!(
        stdout.is_empty(),
        "an admitted artifact reports no findings: {stdout}"
    );
    assert!(
        stderr.is_empty(),
        "an admitted artifact writes no diagnostics: {stderr}"
    );
}

// -------------------------------------------------- negative admission #

#[test]
fn resealed_manifest_contract_tamper_is_refused() {
    let (package, _projection, artifact) = pipeline();

    // model / profile / capability / non_authoritative: every manifest
    // parameter-tampering surface, each re-sealed so the envelope is internally
    // consistent.
    for (key, replacement) in [
        ("model", "\"law-nexus/cleaned-projection-model/v9\""),
        ("profile", "\"cleaned_projection_wordml/v9\""),
        ("capability", "\"cleaned_projection_jsonl_v9\""),
        ("non_authoritative", "false"),
    ] {
        let mut lines = lines_of(&artifact);
        lines[0] = set_raw_value(&lines[0], key, replacement);
        let tampered = resealed(&lines);
        assert_seals_recompute(&lines_of(&tampered));
        assert_structural_refusal(&tampered, &package, WireErrorKind::ContractFieldInvalid);
    }
}

#[test]
fn resealed_non_canonical_version_token_is_refused() {
    let (package, _projection, artifact) = pipeline();

    // `1.0` is valid JSON but not the canonical decimal token for the contract
    // version, so the strict version check refuses it as `VersionMismatch`.
    let mut lines = lines_of(&artifact);
    lines[0] = set_last_raw_value(&lines[0], "version", "1.0");
    let tampered = resealed(&lines);
    assert_seals_recompute(&lines_of(&tampered));
    assert_structural_refusal(&tampered, &package, WireErrorKind::VersionMismatch);

    // `01` is not valid JSON number grammar, so it is refused even earlier, by
    // the parser, as `UnknownKind` — recorded truthfully.
    let mut lines = lines_of(&artifact);
    lines[0] = set_last_raw_value(&lines[0], "version", "01");
    let tampered = resealed(&lines);
    assert_seals_recompute(&lines_of(&tampered));
    assert_eq!(
        read_cleaned_wire(&tampered)
            .expect_err("a non-JSON version token must be refused")
            .kind(),
        WireErrorKind::UnknownKind
    );
}

#[test]
fn resealed_absent_or_tampered_policies_display_scope_is_refused() {
    let (package, _projection, artifact) = pipeline();

    // A tampered closed-vocabulary value and an absent (`null`) value are the
    // same closed-contract refusal class.
    for replacement in ["\"display_cleaned_suppressed\"", "null"] {
        let mut lines = lines_of(&artifact);
        lines[1] = set_raw_value(&lines[1], "display_scope", replacement);
        let tampered = resealed(&lines);
        assert_seals_recompute(&lines_of(&tampered));
        assert_structural_refusal(&tampered, &package, WireErrorKind::ContractFieldInvalid);
    }
}

#[test]
fn resealed_dropped_inline_under_hold_is_membership_mismatch() {
    let (package, projection, _complete) = pipeline();

    // The writer's text-loss check is completion-neutral: an honest Hold
    // artifact that drops a decoded text record is not refused at write time, so
    // only the independent verifier can see the membership violation.
    let hold = declared_incomplete_completion(IncompleteReason::Hold);
    let artifact = export_cleaned_projection(&package, &projection, &hold, &WireLimits::default())
        .expect("an honest Hold export must render");

    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let segment_id = str_field(&lines[index], "id").expect("segment.id");
    let owner = str_field(&lines[index], "view").expect("segment.view");
    let owner_index = lines
        .iter()
        .position(|line| {
            is_kind(line, KIND_VIEW) && str_field(line, "id").as_deref() == Some(owner.as_str())
        })
        .expect("owning view");
    let refs = raw_value(&lines[owner_index], "segment_refs").expect("view.segment_refs");
    lines[owner_index] = set_raw_value(
        &lines[owner_index],
        "segment_refs",
        &remove_str_array_item(refs, &segment_id),
    );
    lines.remove(index);

    let tampered = resealed(&lines);
    assert_seals_recompute(&lines_of(&tampered));
    assert_membership_refusal(&tampered, &package);
}
