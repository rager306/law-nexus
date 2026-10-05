//! T04 hostile battery (M214-es3jvw S03).
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8B.4
//! and §12 H17–H19: a resealed substitution of a member span, a relation
//! target, a fragment `content_sha256`, a context `status` or a deleted record
//! is still detected because `verify_npa_analysis_wire` re-derives the canonical
//! records from the pinned parent instead of trusting the artifact seals. A
//! resealed manifest `source`/`parent`/version/`profile`/`model` substitution or
//! a `document` record contradiction is a `manifest_identity_mismatch` (F01):
//! a recomputed seal is not identity proof. A non-resealed tamper is a
//! `seal_mismatch`; a malformed envelope is refused, never a panic.
//!
//! Fixtures are inline synthetic WordML documents. Raw decoded corpus text is
//! never logged.

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::{analyze_document, DocumentAnalysis};
use ln_decode::npa_analysis_verify::{
    verify_npa_analysis_wire, AnalysisVerifyCode, AnalysisVerifyFinding,
};
use ln_decode::npa_analysis_wire::{
    recompute_analysis_seals, render_npa_analysis_with_context, AnalysisEnvelopeRequest,
    AnalysisLimits, AnalysisScope,
};
use ln_decode::npa_context_records::build_context_records;
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, Limits};

fn wrap(body: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{body}</w:body></w:wordDocument>"
    )
}

struct Pipeline {
    analysis: DocumentAnalysis,
    projection: ReaderProjection,
    index: ReaderRecordIndex,
    mapping: SourceMapping,
}

fn pipeline(xml: &str) -> Pipeline {
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
    Pipeline {
        analysis,
        projection,
        index,
        mapping,
    }
}

fn context_envelope(p: &Pipeline) -> String {
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    let request = AnalysisEnvelopeRequest {
        analysis: &p.analysis,
        projection: &p.projection,
        index: &p.index,
        mapping: &p.mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    };
    render_npa_analysis_with_context(&request, &contexts).expect("valid context envelope renders")
}

fn verify(p: &Pipeline, text: &str) -> Result<(), Vec<AnalysisVerifyFinding>> {
    verify_npa_analysis_wire(text, &p.projection, &p.index, &p.mapping)
}

fn has_code(findings: &[AnalysisVerifyFinding], code: AnalysisVerifyCode) -> bool {
    findings.iter().any(|finding| finding.code() == code)
}

// ------------------------------------------------------ envelope editing #

fn envelope_lines(text: &str) -> Vec<String> {
    assert!(text.ends_with('\n'), "envelope ends with one trailing LF");
    text[..text.len() - 1]
        .split('\n')
        .map(str::to_string)
        .collect()
}

fn join_envelope(lines: &[String]) -> String {
    let mut out = lines.join("\n");
    out.push('\n');
    out
}

fn family_of(line: &str) -> Option<String> {
    let value: serde_json::Value = serde_json::from_str(line).ok()?;
    value.get("family")?.as_str().map(str::to_string)
}

/// Recomputes the two non-cyclic seals over the (tampered) content and patches
/// the footer, emulating an attacker who reseals after a substitution.
fn reseal(text: &str) -> String {
    let seals = recompute_analysis_seals(text).expect("seals recompute");
    let mut lines = envelope_lines(text);
    let last = lines.len() - 1;
    let mut footer = lines[last].clone();
    footer = replace_hex(&footer, "records_seal_hash", &seals.records_seal_hash);
    footer = replace_hex(&footer, "manifest_hash", &seals.manifest_hash);
    lines[last] = footer;
    join_envelope(&lines)
}

fn replace_hex(line: &str, key: &str, value: &str) -> String {
    let needle = format!("\"{key}\":\"");
    let start = line.find(&needle).expect("seal key present") + needle.len();
    let end = start + 64;
    let mut out = line.to_string();
    out.replace_range(start..end, value);
    out
}

/// Replaces the first `"<key>":{...}` object (balanced braces, string-aware).
fn replace_field_object(line: &str, key: &str, new_obj: &str) -> String {
    let needle = format!("\"{key}\":{{");
    let pos = line.find(&needle).expect("field present");
    let obj_start = pos + format!("\"{key}\":").len();
    let bytes = line.as_bytes();
    let mut depth = 0i32;
    let mut index = obj_start;
    loop {
        match bytes[index] {
            b'"' => {
                index += 1;
                while bytes[index] != b'"' {
                    if bytes[index] == b'\\' {
                        index += 1;
                    }
                    index += 1;
                }
            }
            b'{' => depth += 1,
            b'}' => {
                depth -= 1;
                if depth == 0 {
                    break;
                }
            }
            _ => {}
        }
        index += 1;
    }
    let end = index + 1;
    let mut out = line.to_string();
    out.replace_range(obj_start..end, new_obj);
    out
}

fn bound_span_of(line: &str, key: &str) -> Option<(String, usize, usize)> {
    let value: serde_json::Value = serde_json::from_str(line).ok()?;
    let object = value.get(key)?;
    let fragment = object.get("fragment")?.as_str()?.to_string();
    let start = object.get("start")?.as_u64()? as usize;
    let end = object.get("end")?.as_u64()? as usize;
    Some((fragment, start, end))
}

/// A different, valid, in-fragment span on UTF-8 code point boundaries.
fn alternate_span(
    index: &ReaderRecordIndex,
    fragment: &str,
    start: usize,
    end: usize,
) -> Option<(usize, usize)> {
    let value = &index.text(fragment)?.value;
    let length = value.len();
    if end < length {
        let mut candidate = end + 1;
        while candidate < length && !value.is_char_boundary(candidate) {
            candidate += 1;
        }
        if candidate > start && value.is_char_boundary(candidate) {
            return Some((start, candidate));
        }
    }
    if start > 0 {
        let mut candidate = start - 1;
        while candidate > 0 && !value.is_char_boundary(candidate) {
            candidate -= 1;
        }
        if candidate < end && value.is_char_boundary(candidate) {
            return Some((candidate, end));
        }
    }
    None
}

/// A span whose end leaves the fragment (out of bounds), still parseable.
fn out_of_bounds_span(
    index: &ReaderRecordIndex,
    fragment: &str,
    start: usize,
) -> Option<(usize, usize)> {
    let value = &index.text(fragment)?.value;
    Some((start, value.len() + 5))
}

fn mutate_first_member_span(text: &str, p: &Pipeline) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("member") {
            continue;
        }
        for key in ["span", "evidence"] {
            if let Some((fragment, start, end)) = bound_span_of(&lines[index], key) {
                if let Some((new_start, new_end)) = alternate_span(&p.index, &fragment, start, end)
                {
                    let new_obj = format!(
                        r#"{{"end":{new_end},"fragment":"{fragment}","start":{new_start}}}"#
                    );
                    lines[index] = replace_field_object(&lines[index], key, &new_obj);
                    return join_envelope(&lines);
                }
            }
        }
    }
    panic!("the fixture must expose a member span with an in-fragment alternative");
}

fn mutate_first_member_span_out_of_bounds(text: &str, p: &Pipeline) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("member") {
            continue;
        }
        for key in ["span", "evidence"] {
            if let Some((fragment, start, _)) = bound_span_of(&lines[index], key) {
                if let Some((new_start, new_end)) = out_of_bounds_span(&p.index, &fragment, start) {
                    let new_obj = format!(
                        r#"{{"end":{new_end},"fragment":"{fragment}","start":{new_start}}}"#
                    );
                    lines[index] = replace_field_object(&lines[index], key, &new_obj);
                    return join_envelope(&lines);
                }
            }
        }
    }
    panic!("the fixture must expose a member span");
}

fn mutate_first_relation_target(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("relation") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("relation line parses");
        let from = value.get("from").and_then(|v| v.as_u64()).expect("from");
        let to = value.get("to").and_then(|v| v.as_u64()).expect("to");
        if from == to {
            continue;
        }
        lines[index] = lines[index].replacen(&format!("\"to\":{to}"), &format!("\"to\":{from}"), 1);
        return join_envelope(&lines);
    }
    panic!("the fixture must expose a relation with distinct endpoints");
}

fn mutate_first_relation_target_dangling(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("relation") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("relation line parses");
        let to = value.get("to").and_then(|v| v.as_u64()).expect("to");
        lines[index] = lines[index].replacen(&format!("\"to\":{to}"), "\"to\":999999", 1);
        return join_envelope(&lines);
    }
    panic!("the fixture must expose a relation");
}

fn mutate_first_classification_member(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("classification") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("classification line parses");
        let member_id = value
            .get("member_id")
            .and_then(|v| v.as_u64())
            .expect("member_id");
        lines[index] = lines[index].replacen(
            &format!("\"member_id\":{member_id}"),
            "\"member_id\":999999",
            1,
        );
        return join_envelope(&lines);
    }
    panic!("the fixture must expose a classification");
}

fn mutate_first_fragment_hash(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("fragment") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("fragment line parses");
        let hash = value
            .get("content_sha256")
            .and_then(|v| v.as_str())
            .expect("content_sha256");
        let mut chars: Vec<char> = hash.chars().collect();
        chars[0] = if chars[0] == 'a' { 'b' } else { 'a' };
        let new_hash: String = chars.into_iter().collect();
        lines[index] = lines[index].replacen(hash, &new_hash, 1);
        return join_envelope(&lines);
    }
    panic!("the fixture must expose a fragment record");
}

fn mutate_first_context_status(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("context") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("context line parses");
        if value.get("kind").and_then(|v| v.as_str()) != Some("result") {
            continue;
        }
        let status = value
            .get("status")
            .and_then(|v| v.as_str())
            .expect("status");
        let new_status = if status == "resolved" {
            "partial"
        } else {
            "resolved"
        };
        lines[index] = lines[index].replacen(
            &format!("\"status\":\"{status}\""),
            &format!("\"status\":\"{new_status}\""),
            1,
        );
        return join_envelope(&lines);
    }
    panic!("the fixture must expose a context result line");
}

fn delete_first_record(text: &str, family: &str) -> String {
    let mut lines = envelope_lines(text);
    let position = lines
        .iter()
        .position(|line| family_of(line).as_deref() == Some(family))
        .unwrap_or_else(|| panic!("the fixture must expose a {family} record"));
    lines.remove(position);
    join_envelope(&lines)
}

// -------------------------------------------------- manifest identity #

/// Re-serializes the manifest line after `mutate` and reseals the footer.
///
/// Emulates an attacker who substitutes a manifest identity field and then
/// recomputes and patches both footer seals, so a seal-only verifier accepts it
/// (M221 F01).
fn mutate_manifest<F: FnOnce(&mut serde_json::Value)>(text: &str, mutate: F) -> String {
    let mut lines = envelope_lines(text);
    let mut manifest: serde_json::Value =
        serde_json::from_str(&lines[0]).expect("manifest line parses");
    mutate(&mut manifest);
    lines[0] = serde_json::to_string(&manifest).expect("manifest line serializes");
    reseal(&join_envelope(&lines))
}

/// Re-serializes the first record of `family` after `mutate` and reseals the
/// footer, emulating a resealed cross-field record-identity contradiction.
fn mutate_first_record<F: FnOnce(&mut serde_json::Value)>(
    text: &str,
    family: &str,
    mutate: F,
) -> String {
    let mut lines = envelope_lines(text);
    let position = lines
        .iter()
        .position(|line| family_of(line).as_deref() == Some(family))
        .unwrap_or_else(|| panic!("the fixture must expose a {family} record"));
    let mut record: serde_json::Value =
        serde_json::from_str(&lines[position]).expect("record line parses");
    mutate(&mut record);
    lines[position] = serde_json::to_string(&record).expect("record line serializes");
    reseal(&join_envelope(&lines))
}

/// Asserts a resealed identity substitution is a `manifest_identity_mismatch`
/// and is *not* misreported as a `seal_mismatch`: the two invariants are
/// separate, and a correctly recomputed seal is not identity proof.
fn assert_identity_mismatch(tampered: &str, p: &Pipeline) {
    let findings = verify(p, tampered).expect_err("a resealed identity substitution is rejected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::ManifestIdentityMismatch),
        "an identity substitution is manifest_identity_mismatch: {findings:?}"
    );
    assert!(
        !has_code(&findings, AnalysisVerifyCode::SealMismatch),
        "a correctly resealed substitution is not a seal mismatch: {findings:?}"
    );
}

// A heading designation frame plus two act-requisites paragraphs (the second
// bare `от ДАТА N` is the continuation tail), then a trailing heading block
// carrying a this-ref surface. No letterhead is present, so the emitted
// current-document-requisites result stays non-resolved and the hostile
// context-status substitution has a result line to mutate.
const CONTEXT_BODY: &str = "<w:p><w:r><w:t>Статья 1. Предмет регулирования</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Федерального закона от 01.01.2020 N 1-ФЗ,</w:t></w:r></w:p>\
     <w:p><w:r><w:t>от 02.02.2021 N 2-ФЗ</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Статья 2. Настоящего Федерального закона</w:t></w:r></w:p>";

// ------------------------------------------------------------- baseline #

#[test]
fn untouched_context_envelope_verifies_ok() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    assert_eq!(verify(&p, &text), Ok(()), "an untouched envelope verifies");
}

// --------------------------------------------------- resealed substitutions #

#[test]
fn resealed_member_span_move_is_source_ref_substitution() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_member_span(&text, &p));
    assert_ne!(tampered, text, "the mutation changed the envelope");
    let findings = verify(&p, &tampered).expect_err("a resealed span move must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::SourceRefSubstitution),
        "an in-fragment span move is source_ref_substitution: {findings:?}"
    );
}

#[test]
fn resealed_out_of_bounds_span_is_span_slice_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_member_span_out_of_bounds(&text, &p));
    let findings = verify(&p, &tampered).expect_err("an out-of-bounds span must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::SpanSliceMismatch),
        "an out-of-bounds span is span_slice_mismatch: {findings:?}"
    );
}

#[test]
fn resealed_relation_target_is_relation_substitution() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_relation_target(&text));
    let findings = verify(&p, &tampered).expect_err("a resealed relation target must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::RelationSubstitution),
        "a relation target substitution is relation_substitution: {findings:?}"
    );
}

#[test]
fn resealed_fragment_hash_is_fragment_hash_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_fragment_hash(&text));
    let findings = verify(&p, &tampered).expect_err("a resealed fragment hash must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::FragmentHashMismatch),
        "a fragment hash substitution is fragment_hash_mismatch: {findings:?}"
    );
}

#[test]
fn resealed_context_status_is_context_outcome_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_context_status(&text));
    let findings = verify(&p, &tampered).expect_err("a resealed context status must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::ContextOutcomeMismatch),
        "a context status substitution is context_outcome_mismatch: {findings:?}"
    );
}

#[test]
fn deleted_record_is_detected() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&delete_first_record(&text, "member"));
    let findings = verify(&p, &tampered).expect_err("a deleted record must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::MemberRefMissing),
        "a deleted member record is member_ref_missing: {findings:?}"
    );
}

// ------------------------------------------------------ referential gaps #

#[test]
fn dangling_relation_ref_is_relation_ref_missing() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_relation_target_dangling(&text));
    let findings = verify(&p, &tampered).expect_err("a dangling relation target must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::RelationRefMissing),
        "a dangling relation endpoint is relation_ref_missing: {findings:?}"
    );
}

#[test]
fn dangling_classification_member_is_member_ref_missing() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = reseal(&mutate_first_classification_member(&text));
    let findings =
        verify(&p, &tampered).expect_err("a dangling classification member must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::MemberRefMissing),
        "a dangling classification member is member_ref_missing: {findings:?}"
    );
}

// ---------------------------------------------------- non-resealed tamper #

#[test]
fn non_resealed_tamper_is_seal_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_first_member_span(&text, &p);
    let findings = verify(&p, &tampered).expect_err("a non-resealed tamper must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::SealMismatch),
        "a non-resealed tamper is seal_mismatch: {findings:?}"
    );
}

// ------------------------------------------------ manifest identity reseals #

#[test]
fn resealed_manifest_source_sha_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["source"]["sha256"] = serde_json::json!("0".repeat(64));
    });
    assert_ne!(tampered, text, "the mutation changed the envelope");
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_source_bytes_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["source"]["bytes"] = serde_json::json!(999_999);
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_source_revision_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["source_revision"] = serde_json::json!("forged-revision");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_document_version_ref_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["document_version_ref"] = serde_json::json!("forged-version-ref");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_decoder_profile_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["decoder_profile"] = serde_json::json!("forged/decoder_profile/v0");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_parent_schema_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["parent"]["schema"] = serde_json::json!("forged/parent-model/v0");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_parent_records_seal_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["parent"]["records_seal_hash"] = serde_json::json!("0".repeat(64));
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_parent_manifest_hash_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["parent"]["manifest_hash"] = serde_json::json!("0".repeat(64));
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_profile_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["profile"] = serde_json::json!("forged_profile/v0");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_manifest_model_is_identity_mismatch() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_manifest(&text, |manifest| {
        manifest["model"] = serde_json::json!("forged/model/v0");
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn resealed_document_record_identity_is_identity_mismatch() {
    // Cross-field record identity: a `document` record that contradicts the
    // pinned parent must be rejected even after a reseal.
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = mutate_first_record(&text, "document", |record| {
        record["source_sha256"] = serde_json::json!("0".repeat(64));
    });
    assert_identity_mismatch(&tampered, &p);
}

#[test]
fn non_resealed_manifest_identity_is_seal_mismatch() {
    // The identity and seal invariants stay separate: an unsealed identity
    // substitution is still a `seal_mismatch`.
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);
    let tampered = {
        let mut lines = envelope_lines(&text);
        let mut manifest: serde_json::Value =
            serde_json::from_str(&lines[0]).expect("manifest line parses");
        manifest["source"]["sha256"] = serde_json::json!("0".repeat(64));
        lines[0] = serde_json::to_string(&manifest).expect("manifest line serializes");
        join_envelope(&lines)
    };
    let findings = verify(&p, &tampered).expect_err("a non-resealed identity tamper is rejected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::SealMismatch),
        "a non-resealed identity tamper is seal_mismatch: {findings:?}"
    );
}

// -------------------------------------------------------------- malformed #

#[test]
fn malformed_envelopes_never_panic() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let text = context_envelope(&p);

    let mut truncated = text.clone();
    truncated.truncate(truncated.len() / 2);
    let cr = text.replace('\n', "\r\n");
    let cases = [
        "".to_string(),
        "not jsonl".to_string(),
        "{}".to_string(),
        "\n".to_string(),
        truncated,
        cr,
        text.replacen("\"kind\":\"manifest\"", "\"kind\":\"bogus\"", 1),
        text.replacen("\"family\":\"member\"", "\"family\":\"bogus\"", 1),
        text.replacen("\"kind\":\"result\"", "\"kind\":\"bogus\"", 1),
    ];
    for case in cases {
        // Both entry points must fail closed with a typed error, never panic.
        let _ = verify(&p, &case);
        let _ = ln_decode::npa_analysis_verify::read_back_npa_analysis(&case);
    }
}
