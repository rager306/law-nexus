//! S02 cleaned-projection read-back battery: round-trip, re-sealed semantic
//! tamper and record-group order.
//!
//! The battery is a handwritten oracle. It shares no code with the module under
//! test: it recomputes both §7 seals with its own `sha2` over the exact rendered
//! line bytes and edits the artifact with its own line-level JSON reader. Every
//! semantic tamper is re-sealed so the artifact stays internally consistent
//! (`read_cleaned_wire` must still accept it); only the independent
//! `cleaned_verifier` can reject the rewrite.
//!
//! Pinned fixtures: `mixed-wordml.xml` plus the nine positive diverse fixtures
//! (the same positive selection as `reader_projection_diverse.rs`), each pinned
//! by sha256 and failing loud if the bytes move.
//!
//! Non-claims: this battery is `[bounded]` to the ten self-authored non-legal
//! synthetic fixtures named here; it is not corpus coverage, not source
//! authenticity and not a legal-completeness claim. Seals and counts are
//! integrity, not coverage. R1000 stays active. Raw decoded legal text is never
//! logged.

use std::collections::HashMap;

use ln_decode::cleaned_verifier::{CleanedFinding, CleanedVerifyCode, verify_cleaned_wire};
use ln_decode::cleaned_wire::{
    IncompleteReason, KIND_FOOTER, KIND_MANIFEST, KIND_POLICIES, KIND_REFERENCE, KIND_SEGMENT,
    KIND_VIEW, WireCompletion, WireErrorKind, WireLimits, export_cleaned_projection,
    read_cleaned_wire,
};
use ln_decode::reader_projection::{ReaderProjection, build_projection};
use ln_decode::reader_verifier::VerifyCode;
use ln_decode::source_package::{Limits, Package, Record, capture};
use sha2::{Digest, Sha256};

// ---------------------------------------------------------------- fixtures #

#[derive(Clone, Copy)]
struct Fixture {
    file: &'static str,
    xml: &'static str,
    sha256: &'static str,
}

const MIXED: Fixture = Fixture {
    file: "mixed-wordml.xml",
    xml: include_str!("fixtures/reader/mixed-wordml.xml"),
    sha256: "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db",
};

const ALL: &[Fixture] = &[
    MIXED,
    Fixture {
        file: "controls.xml",
        xml: include_str!("fixtures/reader/diverse/controls.xml"),
        sha256: "86440c8cf2f16b88f9da919c77f04e9a2487ed3a0032305dd195aaf48e40988f",
    },
    Fixture {
        file: "unknown-wordml.xml",
        xml: include_str!("fixtures/reader/diverse/unknown-wordml.xml"),
        sha256: "afdfbd3f50377e95d31e736a14cbb2d72d1b2cd13446c4a672ebbc2037a20232",
    },
    Fixture {
        file: "residual-and-tails.xml",
        xml: include_str!("fixtures/reader/diverse/residual-and-tails.xml"),
        sha256: "424f7f117255472e320a1d86adb2a63d8985b97b435a262e3d2403c2767a6834",
    },
    Fixture {
        file: "encoding.xml",
        xml: include_str!("fixtures/reader/diverse/encoding.xml"),
        sha256: "6eaff6f86c7c542f875065f1ba383e52b0bd0703576d5fc58f90d7316807dbb2",
    },
    Fixture {
        file: "empty-structure.xml",
        xml: include_str!("fixtures/reader/diverse/empty-structure.xml"),
        sha256: "84a17e721a37879a8bd3e424a991168639766ec02921892bdc8994e9fcddeec4",
    },
    Fixture {
        file: "notes-nested.xml",
        xml: include_str!("fixtures/reader/diverse/notes-nested.xml"),
        sha256: "36d874f81bc456583687b6189d21ae2c7f5c3621a0373c6248cbe733e4fa9a75",
    },
    Fixture {
        file: "fields-revisions.xml",
        xml: include_str!("fixtures/reader/diverse/fields-revisions.xml"),
        sha256: "4e6ca62093eefb95fa49471b41de072a8e144ac2a867ffe894c0ce507ff17b0e",
    },
    Fixture {
        file: "navigation-demo.xml",
        xml: include_str!("fixtures/reader/diverse/navigation-demo.xml"),
        sha256: "b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0",
    },
    Fixture {
        file: "text-only.xml",
        xml: include_str!("fixtures/reader/diverse/text-only.xml"),
        sha256: "e13b8c7424100989028d95bd4c37bfadcd3970972329d93624c8da384507c55f",
    },
];

fn project(fixture: &Fixture) -> (Package, ReaderProjection) {
    let package = capture(fixture.xml.as_bytes(), &Limits::default())
        .unwrap_or_else(|error| panic!("{} must capture: {error:?}", fixture.file));
    assert_eq!(
        package.manifest().source.sha256,
        fixture.sha256,
        "{}: content changed; re-pin the sha256 oracle",
        fixture.file
    );
    let projection = build_projection(package.records())
        .unwrap_or_else(|error| panic!("{} must project: {error:?}", fixture.file));
    (package, projection)
}

fn mixed() -> (Package, ReaderProjection) {
    project(&MIXED)
}

fn exported(package: &Package, projection: &ReaderProjection) -> String {
    export_cleaned_projection(
        package,
        projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("a verified package and its projection must export")
}

// ------------------------------------------- independent JSON line reader #
//
// The writer emits one compact ascending-key object per line. This reader and
// writer are local to the battery: the module under test shares none of it.

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

// ------------------------------------------------------------ seal oracle #
//
// A handwritten §7 oracle: the same formulas as the writer, but computed here
// over the exact rendered line bytes. It never calls into the module under test.

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

// ------------------------------------------------------------ line finders #

fn first_source_segment_line(lines: &[String]) -> Option<usize> {
    lines.iter().position(|line| {
        is_kind(line, KIND_SEGMENT)
            && str_field(line, "origin").as_deref() == Some("source_fragment")
    })
}

fn first_view_line_with_two_segment_refs(lines: &[String]) -> Option<usize> {
    lines.iter().position(|line| {
        is_kind(line, KIND_VIEW)
            && raw_value(line, "segment_refs")
                .map(|raw| parse_str_array(raw).len() >= 2)
                .unwrap_or(false)
    })
}

fn first_view_line_with_parent(lines: &[String]) -> Option<usize> {
    lines.iter().position(|line| {
        is_kind(line, KIND_VIEW)
            && raw_value(line, "parent_view")
                .map(|raw| raw.trim() != "null")
                .unwrap_or(false)
    })
}

fn other_view_id(lines: &[String], exclude: &str) -> Option<String> {
    lines
        .iter()
        .filter(|line| is_kind(line, KIND_VIEW))
        .find_map(|line| {
            let id = str_field(line, "id")?;
            if id == exclude { None } else { Some(id) }
        })
}

fn remove_str_array_item(raw: &str, victim: &str) -> String {
    let kept: Vec<String> = parse_str_array(raw)
        .into_iter()
        .filter(|item| item != victim)
        .collect();
    render_str_array(&kept)
}

// ------------------------------------------------------------- assertions #

fn findings_of(artifact: &str, package: &Package) -> Vec<CleanedFinding> {
    verify_cleaned_wire(artifact, package)
        .expect_err("the tampered artifact must be refused by the independent verifier")
}

fn codes(findings: &[CleanedFinding]) -> Vec<CleanedVerifyCode> {
    findings.iter().map(|finding| finding.code).collect()
}

/// True when the verifier reported a `ProjectionInvalid` wrapping `code`.
fn projection_finding(findings: &[CleanedFinding], code: VerifyCode) -> bool {
    findings.iter().any(|finding| {
        finding.code == CleanedVerifyCode::ProjectionInvalid
            && finding.detail.contains(code.as_str())
    })
}

/// Flips one ASCII letter inside a raw JSON string value without changing its
/// byte length, so declared `text_bytes` / `text_chars` stay consistent.
fn tamper_ascii_letter(raw: &str) -> Option<String> {
    let bytes = raw.as_bytes();
    if bytes.len() < 3 {
        return None;
    }
    let mut out = bytes.to_vec();
    let end = bytes.len() - 1;
    let mut index = 1usize;
    while index < end {
        match bytes[index] {
            b'\\' => {
                index += 2;
                continue;
            }
            byte if byte.is_ascii_alphabetic() => {
                out[index] = if byte == b'a' { b'b' } else { b'a' };
                return String::from_utf8(out).ok();
            }
            _ => index += 1,
        }
    }
    None
}

fn mutate_first_hex(hex: &str) -> String {
    let mut chars: Vec<char> = hex.chars().collect();
    chars[0] = if chars[0] == '0' { '1' } else { '0' };
    chars.into_iter().collect()
}

fn parse_u64(raw: &str) -> u64 {
    raw.trim().parse().expect("field must be a u64")
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

/// Recomputes the §7 oracle seals over `lines` and asserts the footer carries
/// exactly them: proves a mutation was re-sealed into a self-consistent
/// envelope before the verifier was asked to reject it.
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

// ------------------------------------------------------------- round-trip #

#[test]
fn round_trips_and_recomputes_seals_for_every_fixture() {
    for fixture in ALL {
        let (package, projection) = project(fixture);
        let artifact = exported(&package, &projection);
        let lines = lines_of(&artifact);
        let footer_index = lines.len() - 1;

        // Own §7 oracle must agree with the writer's footer seals.
        let records_seal = oracle_records_seal(&lines);
        let manifest_seal = oracle_manifest_seal(&lines, &records_seal);
        assert_eq!(
            str_field(&lines[footer_index], "records_seal_hash").as_deref(),
            Some(records_seal.as_str()),
            "{}: battery records seal must match the writer",
            fixture.file
        );
        assert_eq!(
            str_field(&lines[footer_index], "manifest_hash").as_deref(),
            Some(manifest_seal.as_str()),
            "{}: battery manifest seal must match the writer",
            fixture.file
        );

        let readback = read_cleaned_wire(&artifact).unwrap_or_else(|error| {
            panic!(
                "{}: exported artifact must read back: {error}",
                fixture.file
            )
        });

        // Full-text invariant: every substrate text record is carried exactly
        // once by a source inline entry, with self-consistent declared counts.
        let substrate: HashMap<&str, &str> = package
            .records()
            .iter()
            .filter_map(|record| match record {
                Record::Text(text) => Some((text.id.as_str(), text.value.as_str())),
                Record::Element(_) => None,
            })
            .collect();
        let mut inline_by_fragment: HashMap<&str, (&str, u64, u64)> = HashMap::new();
        for inline in &readback.inline_texts {
            if let Some(fragment) = &inline.fragment_ref {
                let previous = inline_by_fragment.insert(
                    fragment.as_str(),
                    (inline.text.as_str(), inline.chars, inline.text_bytes),
                );
                assert!(
                    previous.is_none(),
                    "{}: fragment {fragment} carries more than one inline text",
                    fixture.file
                );
            }
        }
        for record in package.records() {
            if let Record::Text(text) = record {
                let (value, chars, bytes) = inline_by_fragment
                    .get(text.id.as_str())
                    .copied()
                    .unwrap_or_else(|| {
                        panic!("{}: fragment {} has no inline text", fixture.file, text.id)
                    });
                assert_eq!(value, text.value, "{}: inline text drift", fixture.file);
                assert_eq!(
                    chars,
                    text.value.chars().count() as u64,
                    "{}: declared text_chars drift",
                    fixture.file
                );
                assert_eq!(
                    bytes,
                    text.value.len() as u64,
                    "{}: declared text_bytes drift",
                    fixture.file
                );
            }
        }
        assert_eq!(
            inline_by_fragment.len(),
            substrate.len(),
            "{}: inline text membership must equal the substrate",
            fixture.file
        );

        verify_cleaned_wire(&artifact, &package).unwrap_or_else(|findings| {
            panic!(
                "{}: independent verification must accept the round-trip: {:?}",
                fixture.file,
                codes(&findings)
            )
        });
    }
}

// ------------------------------------------ incomplete completion (F05) #

/// The declared `Hold` / `TextOnly` basis, exactly as the S04 corpus battery
/// maps `ScopeDeclaration::StructureHold` / `TextOnlyScope`. Written here rather
/// than imported so this battery never derives its expectation from the module
/// under test.
fn declared_incomplete_completion(basis: IncompleteReason) -> WireCompletion {
    WireCompletion::Incomplete {
        basis,
        reasons: vec![basis],
    }
}

#[test]
fn incomplete_completions_pass_independent_verification() {
    let (package, projection) = mixed();
    for basis in [IncompleteReason::Hold, IncompleteReason::TextOnly] {
        let completion = declared_incomplete_completion(basis);
        let artifact =
            export_cleaned_projection(&package, &projection, &completion, &WireLimits::default())
                .unwrap_or_else(|error| panic!("{basis:?}: honest partial export: {error}"));
        assert!(
            read_cleaned_wire(&artifact).is_ok(),
            "{basis:?}: the writer must not forbid an honest partial scope"
        );
        verify_cleaned_wire(&artifact, &package).unwrap_or_else(|findings| {
            panic!(
                "{basis:?}: independent verification must accept the incomplete artifact: {:?}",
                codes(&findings)
            )
        });
    }
}

#[test]
fn resealed_dropped_inline_under_hold_is_membership_mismatch() {
    let (package, projection) = mixed();
    let hold = declared_incomplete_completion(IncompleteReason::Hold);
    let artifact = export_cleaned_projection(&package, &projection, &hold, &WireLimits::default())
        .expect("honest Hold export");

    // Drop a whole source segment (its inline decoded-text entry) and the
    // owning view's reference to it, then re-seal: the envelope stays internally
    // consistent, so only the independent verifier can see that a substrate text
    // record is now covered by no source inline text.
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

    let artifact = resealed(&lines);
    assert!(
        read_cleaned_wire(&artifact).is_ok(),
        "a re-sealed Hold artifact stays internally consistent"
    );
    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::TextChannelMembershipMismatch),
        "a dropped inline entry must surface as TextChannelMembershipMismatch, got {:?}",
        codes(&findings)
    );
}

// ---------------------------------------------- re-sealed semantic tamper #

#[test]
fn resealed_inline_text_tamper_is_caught_by_text_channel() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let raw = raw_value(&lines[index], "text").expect("segment.text");
    let tampered = tamper_ascii_letter(raw).expect("source text must carry an ASCII letter");
    lines[index] = set_raw_value(&lines[index], "text", &tampered);

    let artifact = resealed(&lines);
    assert!(
        read_cleaned_wire(&artifact).is_ok(),
        "a re-sealed semantic tamper still reads back"
    );
    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::TextChannelMismatch),
        "expected TextChannelMismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_segment_chars_tamper_is_caught_as_source_mismatch() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let current = parse_u64(raw_value(&lines[index], "chars").expect("segment.chars"));
    lines[index] = set_raw_value(&lines[index], "chars", &(current + 1).to_string());

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::SegmentSourceMismatch),
        "expected ProjectionInvalid/segment_source_mismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_declared_text_chars_tamper_is_caught_by_text_channel() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let current = parse_u64(raw_value(&lines[index], "text_chars").expect("segment.text_chars"));
    lines[index] = set_raw_value(&lines[index], "text_chars", &(current + 1).to_string());

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::TextChannelMismatch),
        "expected TextChannelMismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_declared_text_bytes_tamper_is_caught_by_text_channel() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let current = parse_u64(raw_value(&lines[index], "text_bytes").expect("segment.text_bytes"));
    lines[index] = set_raw_value(&lines[index], "text_bytes", &(current + 1).to_string());

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::TextChannelMismatch),
        "expected TextChannelMismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_segment_ref_swap_is_caught_by_membership_order() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_view_line_with_two_segment_refs(&lines)
        .expect("mixed must carry a view owning at least two segments");
    let raw = raw_value(&lines[index], "segment_refs").expect("view.segment_refs");
    let mut items = parse_str_array(raw);
    items.swap(0, 1);
    lines[index] = set_raw_value(&lines[index], "segment_refs", &render_str_array(&items));

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::SegmentMembershipOrOrderMismatch),
        "expected ProjectionInvalid/segment_membership_or_order_mismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_segment_view_reassign_is_caught_by_ownership() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let current_view = str_field(&lines[index], "view").expect("segment.view");
    let target = other_view_id(&lines, &current_view).expect("mixed must carry another view");
    lines[index] = set_str_value(&lines[index], "view", &target);

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::FragmentInWrongView),
        "expected ProjectionInvalid/fragment_in_wrong_view, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_dropped_source_segment_is_caught_by_missing_reference() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
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

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::MissingFragmentReference),
        "expected ProjectionInvalid/missing_fragment_reference, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_duplicated_source_segment_is_caught_by_duplicate_reference() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_source_segment_line(&lines).expect("mixed must carry a source segment");
    let segment_id = str_field(&lines[index], "id").expect("segment.id");
    let duplicate_id = format!("{segment_id}-dup");
    let mut duplicate = lines[index].clone();
    duplicate = set_str_value(&duplicate, "id", &duplicate_id);
    lines.insert(index + 1, duplicate);

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::DuplicateFragmentReference),
        "expected ProjectionInvalid/duplicate_fragment_reference, got {:?}",
        codes(&findings)
    );
}

#[test]
fn resealed_parent_view_tamper_is_caught_by_forest() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let index = first_view_line_with_parent(&lines)
        .expect("mixed must carry a nested view with a parent_view");
    lines[index] = set_raw_value(&lines[index], "parent_view", "null");

    let artifact = resealed(&lines);
    assert!(read_cleaned_wire(&artifact).is_ok());
    let findings = findings_of(&artifact, &package);
    assert!(
        projection_finding(&findings, VerifyCode::ViewParentMismatch),
        "expected ProjectionInvalid/view_parent_mismatch, got {:?}",
        codes(&findings)
    );
}

// ------------------------------------------------- record-group ordering #

#[test]
fn record_group_order_corruption_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let reference = lines
        .iter()
        .position(|line| is_kind(line, KIND_REFERENCE))
        .expect("mixed must carry a reference record");
    let segment = lines
        .iter()
        .position(|line| is_kind(line, KIND_SEGMENT))
        .expect("mixed must carry a segment record");
    assert!(reference > segment, "references render after segments");
    let moved = lines.remove(reference);
    lines.insert(segment, moved);

    let artifact = join_lines(&lines);
    let error = read_cleaned_wire(&artifact).expect_err("misordered record groups must refuse");
    assert_eq!(error.kind(), WireErrorKind::RecordGroupOrder);

    let findings = findings_of(&artifact, &package);
    assert_eq!(
        codes(&findings),
        vec![CleanedVerifyCode::ArtifactUnreadable]
    );
    assert_eq!(findings[0].detail, WireErrorKind::RecordGroupOrder.as_str());
}

#[test]
fn structural_envelope_damage_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let lines = lines_of(&artifact);

    // Missing footer.
    let mut without_footer = lines.clone();
    without_footer.pop();
    let truncated = join_lines(&without_footer);
    assert_eq!(
        read_cleaned_wire(&truncated)
            .expect_err("a document without a footer must refuse")
            .kind(),
        WireErrorKind::MissingFooter
    );
    let findings = findings_of(&truncated, &package);
    assert_eq!(
        codes(&findings),
        vec![CleanedVerifyCode::ArtifactUnreadable]
    );

    // Swapped manifest and policies.
    let mut swapped = lines.clone();
    swapped.swap(0, 1);
    let swapped = join_lines(&swapped);
    assert_eq!(
        read_cleaned_wire(&swapped)
            .expect_err("policies before the manifest must refuse")
            .kind(),
        WireErrorKind::MisorderedPolicies
    );
}

// ------------------------------------------------- seal mismatch (no reseal) #

#[test]
fn seal_mismatch_without_reseal_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let lines = lines_of(&artifact);
    let footer_index = lines.len() - 1;

    let records_seal = str_field(&lines[footer_index], "records_seal_hash").expect("footer seal");
    let mut tampered = lines.clone();
    tampered[footer_index] = set_str_value(
        &tampered[footer_index],
        "records_seal_hash",
        &mutate_first_hex(&records_seal),
    );
    assert_eq!(
        read_cleaned_wire(&join_lines(&tampered))
            .expect_err("a drifted records seal must refuse")
            .kind(),
        WireErrorKind::HashMismatch
    );

    let manifest_seal = str_field(&lines[footer_index], "manifest_hash").expect("footer manifest");
    let mut tampered = lines.clone();
    tampered[footer_index] = set_str_value(
        &tampered[footer_index],
        "manifest_hash",
        &mutate_first_hex(&manifest_seal),
    );
    assert_eq!(
        read_cleaned_wire(&join_lines(&tampered))
            .expect_err("a drifted manifest seal must refuse")
            .kind(),
        WireErrorKind::HashMismatch
    );
}

// ------------------------------------------------------------- parent pins #

#[test]
fn parent_source_pin_mismatch_is_reported() {
    let (package, projection) = mixed();
    let mut manifest = package.manifest().clone();
    manifest.source.sha256 = "a".repeat(64);
    manifest.source.bytes = manifest.source.bytes.wrapping_add(1);
    let other = Package::from_parts(
        manifest,
        package.records().to_vec(),
        package.footer().clone(),
    );
    let artifact = exported(&other, &projection);

    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::ParentSourcePinMismatch),
        "expected ParentSourcePinMismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn parent_seal_pin_mismatch_is_reported() {
    let (package, projection) = mixed();
    let mut footer = package.footer().clone();
    footer.records_seal_hash = None;
    footer.manifest_hash = None;
    let other = Package::from_parts(
        package.manifest().clone(),
        package.records().to_vec(),
        footer,
    );
    let artifact = exported(&other, &projection);

    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::ParentSealPinMismatch),
        "expected ParentSealPinMismatch, got {:?}",
        codes(&findings)
    );
}

#[test]
fn counts_mismatch_after_reseal_is_reported() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let mut lines = lines_of(&artifact);
    let footer_index = lines.len() - 1;
    let current =
        parse_u64(raw_value(&lines[footer_index], "text_chars").expect("footer text_chars"));
    lines[footer_index] = set_raw_value(
        &lines[footer_index],
        "text_chars",
        &(current + 1).to_string(),
    );

    let artifact = resealed(&lines);
    assert!(
        read_cleaned_wire(&artifact).is_ok(),
        "the re-sealed footer is internally consistent"
    );
    let findings = findings_of(&artifact, &package);
    assert!(
        codes(&findings).contains(&CleanedVerifyCode::CountsMismatch),
        "expected CountsMismatch, got {:?}",
        codes(&findings)
    );
}

// --------------------------------------- re-sealed envelope integrity #

#[test]
fn resealed_manifest_contract_tamper_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);

    // model / profile / capability / non_authoritative: every F01 manifest
    // parameter-tampering surface, each resealed so the envelope is internally
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
        assert_eq!(
            read_cleaned_wire(&tampered)
                .expect_err("a resealed contract tamper must be refused")
                .kind(),
            WireErrorKind::ContractFieldInvalid,
            "manifest.{key} must fail the closed contract check"
        );
        let findings = findings_of(&tampered, &package);
        assert_eq!(
            codes(&findings),
            vec![CleanedVerifyCode::ArtifactUnreadable]
        );
        assert_eq!(
            findings[0].detail,
            WireErrorKind::ContractFieldInvalid.as_str()
        );
    }

    // A removed limits object is the same class.
    let mut lines = lines_of(&artifact);
    lines[0] = set_raw_value(&lines[0], "limits", "null");
    let tampered = resealed(&lines);
    assert_seals_recompute(&lines_of(&tampered));
    assert_eq!(
        read_cleaned_wire(&tampered)
            .expect_err("a removed limits object must be refused")
            .kind(),
        WireErrorKind::ContractFieldInvalid
    );
}

#[test]
fn resealed_policies_contract_tamper_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    for (key, replacement) in [
        ("cleaning_mode", "\"display_and_suppression\""),
        ("text_retention", "\"summary_only\""),
        ("hold_text_only", "\"loss_permitted\""),
        ("counts_scope", "\"coverage\""),
        ("display_scope", "\"display_cleaned_suppressed\""),
        ("unknown_context", "\"dropped\""),
        ("normalization", "\"nfc\""),
        ("authenticity", "\"authenticity_proven\""),
        ("non_authoritative", "false"),
    ] {
        let mut lines = lines_of(&artifact);
        lines[1] = set_raw_value(&lines[1], key, replacement);
        let tampered = resealed(&lines);
        assert_seals_recompute(&lines_of(&tampered));
        assert_eq!(
            read_cleaned_wire(&tampered)
                .expect_err("a resealed policies tamper must be refused")
                .kind(),
            WireErrorKind::ContractFieldInvalid,
            "policies.{key} must fail the closed contract check"
        );
        let findings = findings_of(&tampered, &package);
        assert_eq!(
            codes(&findings),
            vec![CleanedVerifyCode::ArtifactUnreadable]
        );
    }

    // An artifact that omits `display_scope` entirely must be refused too
    // (closed-contract admission, additive-tightening under the same version).
    let mut lines = lines_of(&artifact);
    lines[1] = lines[1].replacen(
        "\"display_scope\":\"source_content_retained_no_suppression\",",
        "",
        1,
    );
    let without_scope = resealed(&lines);
    assert_seals_recompute(&lines_of(&without_scope));
    assert_eq!(
        read_cleaned_wire(&without_scope)
            .expect_err("an absent policies.display_scope must be refused")
            .kind(),
        WireErrorKind::ContractFieldInvalid
    );
    let without_scope_findings = findings_of(&without_scope, &package);
    assert_eq!(
        codes(&without_scope_findings),
        vec![CleanedVerifyCode::ArtifactUnreadable]
    );
}

#[test]
fn resealed_non_canonical_version_token_is_refused() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);

    // `01`/`+1` are invalid JSON number grammar; `1.0`/`1e0` are valid JSON but
    // not the canonical contract token. All are refused after resealing; the
    // canonical `version:1` positive control is `accepts_a_round_tripped_artifact`.
    for (token, expected) in [
        ("01", WireErrorKind::UnknownKind),
        ("+1", WireErrorKind::UnknownKind),
        ("1.0", WireErrorKind::VersionMismatch),
        ("1e0", WireErrorKind::VersionMismatch),
    ] {
        let mut lines = lines_of(&artifact);
        lines[0] = set_last_raw_value(&lines[0], "version", token);
        let tampered = resealed(&lines);
        assert_seals_recompute(&lines_of(&tampered));
        let error =
            read_cleaned_wire(&tampered).expect_err("a non-canonical version token must refuse");
        assert_eq!(error.kind(), expected, "version token {token}");
        let findings = findings_of(&tampered, &package);
        assert_eq!(
            codes(&findings),
            vec![CleanedVerifyCode::ArtifactUnreadable]
        );
        assert_eq!(findings[0].detail, expected.as_str());
    }
}

#[test]
fn canonical_version_one_still_verifies() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    assert!(read_cleaned_wire(&artifact).is_ok());
    verify_cleaned_wire(&artifact, &package).expect("canonical version 1 must verify");
}

// --------------------------------------------------------------- constants #

#[test]
fn kind_constants_match_the_rendered_artifact() {
    let (package, projection) = mixed();
    let artifact = exported(&package, &projection);
    let lines = lines_of(&artifact);
    assert_eq!(kind_of(&lines[0]).as_deref(), Some(KIND_MANIFEST));
    assert_eq!(kind_of(&lines[1]).as_deref(), Some(KIND_POLICIES));
    assert_eq!(
        kind_of(lines.last().expect("footer")).as_deref(),
        Some(KIND_FOOTER)
    );
    assert!(lines.iter().any(|line| is_kind(line, KIND_VIEW)));
    assert!(lines.iter().any(|line| is_kind(line, KIND_SEGMENT)));
    assert!(lines.iter().any(|line| is_kind(line, KIND_REFERENCE)));
}
