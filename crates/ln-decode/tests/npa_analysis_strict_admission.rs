//! Bounded R29-F07c admission checks; seals are computed independently of the reader.
use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::analyze_document;
use ln_decode::npa_analysis_verify::{
    AnalysisVerifyCode, read_back_npa_analysis, verify_npa_analysis_wire,
};
use ln_decode::npa_analysis_wire::*;
use ln_decode::npa_context_records::build_context_records;
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use sha2::{Digest, Sha256};

fn with_envelope(
    context: bool,
    scope: AnalysisScope,
    check: impl FnOnce(String, &dyn Fn(&str) -> bool),
) {
    let xml = b"<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body><w:p><w:r><w:t>Alpha</w:t></w:r></w:p></w:body></w:wordDocument>";
    let p = capture(xml, &Limits::default()).unwrap();
    let index = ReaderRecordIndex::new(p.records()).unwrap();
    let projection = build_projection(p.records()).unwrap();
    let identity = SourceIdentity::try_new(
        p.manifest().source.sha256.clone(),
        p.manifest().source.bytes,
        "law-nexus/source-package-model/v1".into(),
        p.footer().records_seal_hash.clone(),
        p.footer().manifest_hash.clone(),
    )
    .unwrap();
    let version = DocumentVersionRef::try_new(
        "doc-version-1".into(),
        "rev-1".into(),
        "reader_wordml_profile/v1".into(),
    )
    .unwrap();
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .unwrap();
    }
    let analysis = analyze_document(&projection, &index, &mapping).unwrap();
    let request = AnalysisEnvelopeRequest {
        analysis: &analysis,
        projection: &projection,
        index: &index,
        mapping: &mapping,
        limits: AnalysisLimits::default(),
        scope,
    };
    let wire = if context {
        render_npa_analysis_with_context(
            &request,
            &build_context_records(&analysis.layout, &mapping),
        )
        .unwrap()
    } else {
        render_npa_analysis(&request).unwrap()
    };
    assert!(verify_npa_analysis_wire(&wire, &projection, &index, &mapping).is_ok());
    check(
        wire,
        &|text| match verify_npa_analysis_wire(text, &projection, &index, &mapping) {
            Ok(()) => true,
            Err(findings) => {
                assert!(
                    !findings
                        .iter()
                        .any(|f| f.code() == AnalysisVerifyCode::SealMismatch),
                    "must reject admission, not the independent seals: {findings:?}"
                );
                false
            }
        },
    );
}

// Only the canonical footer is split here: no parser under test or production
// seal helper is used, so even malformed manifests can be independently sealed.
fn reseal(text: &str) -> String {
    let mut lines: Vec<String> = text.lines().map(str::to_owned).collect();
    let last = lines.len() - 1;
    let body = format!(
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
        Sha256::digest(format!("{}\n{records}\n{body}", lines[0]).as_bytes())
    );
    for (key, value) in [("manifest_hash", manifest), ("records_seal_hash", records)] {
        let needle = format!("\"{key}\":\"");
        let start = lines[last].find(&needle).unwrap() + needle.len();
        lines[last].replace_range(start..start + 64, &value);
    }
    format!("{}\n", lines.join("\n"))
}

#[test]
fn valid_six_and_seven_family_complete_and_incomplete_envelopes() {
    for context in [false, true] {
        for scope in [AnalysisScope::Bounded, AnalysisScope::CallerScope] {
            with_envelope(context, scope, |wire, verify| {
                assert_eq!(reseal(&wire), wire, "independent seal oracle");
                assert!(verify(&reseal(&wire)));
                assert_eq!(
                    inspect_npa_analysis_wire(&wire).unwrap().completion,
                    if scope == AnalysisScope::Bounded {
                        "complete"
                    } else {
                        "incomplete"
                    }
                );
            });
        }
    }
}

#[test]
fn resealed_wrong_version_is_refused() {
    with_envelope(false, AnalysisScope::Bounded, |wire, verify| {
        for value in ["2", "0", "-1", "1.0", "1e0", "\"1\"", "null"] {
            assert!(
                !verify(&reseal(
                    &wire.replace("\"version\":1", &format!("\"version\":{value}"))
                )),
                "accepted version {value}"
            );
        }
    });
}

#[test]
fn resealed_forged_capability_is_refused() {
    with_envelope(false, AnalysisScope::Bounded, |wire, verify| {
        assert!(!verify(&reseal(&wire.replace(CAPABILITY, "forged"))));
    });
}

#[test]
fn resealed_forged_schema_on_each_line_is_refused() {
    with_envelope(true, AnalysisScope::Bounded, |wire, verify| {
        for (i, line) in wire.lines().enumerate() {
            let start = line.find("\"schema\":\"").unwrap() + "\"schema\":\"".len();
            // Manifest also has parent.schema; use the last schema on that line.
            let start = if i == 0 {
                line.rfind("\"schema\":\"").unwrap() + "\"schema\":\"".len()
            } else {
                start
            };
            let end = start + line[start..].find('"').unwrap();
            let mut changed = line.to_string();
            changed.replace_range(start..end, "law-nexus/forged/v9");
            assert!(
                !verify(&reseal(&wire.replacen(line, &changed, 1))),
                "accepted forged schema at line {i}"
            );
        }
    });
}

#[test]
fn resealed_leading_zero_version_is_refused() {
    with_envelope(false, AnalysisScope::Bounded, |wire, verify| {
        assert!(!verify(&reseal(
            &wire.replace("\"version\":1", "\"version\":01")
        )));
    });
}

#[test]
fn resealed_escaped_duplicate_key_is_refused() {
    with_envelope(false, AnalysisScope::Bounded, |wire, verify| {
        // `"version"` and `"\u0076ersion"` decode to the same key. The escaped
        // copy must be refused as a duplicate after an independent reseal, at
        // every admission surface (inspect, read-back, full verify), not merely
        // ignored as an unknown member.
        let changed = wire.replacen("\"version\":1", "\"version\":1,\"\\u0076ersion\":2", 1);
        assert_ne!(changed, wire, "manifest version member must exist");
        let escaped = reseal(&changed);
        assert!(
            !verify(&escaped),
            "verify accepted a decoded-equivalent escaped duplicate key"
        );
        assert!(
            inspect_npa_analysis_wire(&escaped).is_err(),
            "inspect accepted a decoded-equivalent escaped duplicate key"
        );
        assert!(
            read_back_npa_analysis(&escaped).is_err(),
            "read-back accepted a decoded-equivalent escaped duplicate key"
        );

        // The literal duplicate is refused the same way, so the decoded-key
        // comparison is not narrower than the previous raw-byte comparison.
        let literal = reseal(&wire.replacen("\"version\":1", "\"version\":1,\"version\":2", 1));
        assert!(!verify(&literal));
        assert!(inspect_npa_analysis_wire(&literal).is_err());
        assert!(read_back_npa_analysis(&literal).is_err());
    });
}

#[test]
fn malformed_ignored_json_values_are_refused() {
    with_envelope(false, AnalysisScope::Bounded, |wire, verify| {
        for value in [
            "01",
            "+1",
            "1.",
            "1e",
            "truefalse",
            "[1,]",
            "[1 2]",
            "{\"a\":1,}",
            "{\"a\":1,\"a\":2}",
            "{\"a\":1,\"\\u0061\":2}",
            "{\"a\" 1}",
            "[}",
            "\"\\q\"",
            "\"\\u00xz\"",
            "\"raw\tcontrol\"",
        ] {
            let changed = wire.replacen('{', &format!("{{\"extra\":{value},"), 1);
            assert!(
                !verify(&reseal(&changed)),
                "accepted malformed value {value:?}"
            );
        }
        let deep = format!("{}0{}", "[".repeat(100), "]".repeat(100));
        assert!(!verify(&reseal(&wire.replacen(
            '{',
            &format!("{{\"extra\":{deep},"),
            1
        ))));
        let first = wire.lines().next().unwrap();
        let trailing = format!("{},}}", first.strip_suffix('}').unwrap());
        assert!(!verify(&reseal(&wire.replacen(first, &trailing, 1))));
    });
}
