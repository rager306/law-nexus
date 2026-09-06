//! TDD red contract for the sibling `registry_admission` boundary
//! (M202-9qf3ta S03): explicit candidate-backed admission of hierarchy
//! candidates into the kb-hierarchy-registry projection.
//!
//! Pins against `ln_kb_ontology::registry_admission` (implemented in T02):
//! - closed admission schema `law-nexus-kb-hierarchy-admission/v1`;
//! - lifecycle `[proposed]` and `authoritative: false` on the source and
//!   on the admitted output;
//! - bound artifact path + SHA-256 + source/identity digests (any drift
//!   fails closed before rendering);
//! - D426 admitted identities glava-1/statya-4/statya-5 bound to the
//!   already-existing CC identifiers cc:44-fz:glava-1/statya-4/statya-5;
//! - typed failures: missing candidate, level/number/key_path mismatch,
//!   same key with different CC, conflicting duplicate (exact duplicates
//!   are rejected, never silently deduplicated), malformed or empty CC,
//!   digest drift, unknown keys, authority escalation;
//! - deterministic, input-order-independent render ordering
//!   `(path_needle, level catalog order, key_path/number, cc)`;
//! - non-claims: punkt candidates stay unadmitted, output stays ASCII,
//!   evidence digests/internals never enter the projection, and the
//!   rendered bytes re-parse through the existing runtime reader
//!   `parse_hierarchy_registry`.
//!
//! Pure library boundary: normalized candidate evidence is supplied by the
//! caller (the generator parses the tracked artifact via ln-decode); this
//! suite performs no I/O, writes no registry YAML, and must not acquire an
//! ln-decode dependency (D185 / D417 / D418 / D426).

use ln_kb_ontology::registry::parse_hierarchy_registry;
use ln_kb_ontology::registry_admission::{
    admit_candidates, parse_admission_source, render_registry, AdmissionBinding,
    AdmissionProvenance, AdmissionSource, CandidateEvidence, CandidateIdentity,
    RegistryAdmissionError,
};

const CANDIDATE_ARTIFACT_SCHEMA: &str = "law-nexus-hierarchy-candidate-artifact/v1";
const ADMISSION_SCHEMA_V1: &str = "law-nexus-kb-hierarchy-admission/v1";
const CANDIDATE_ARTIFACT_PATH: &str =
    "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
/// Exact SHA-256 of the tracked S02 candidate artifact (binding pin).
const S02_ARTIFACT_SHA256: &str =
    "50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6";
const S02_SOURCE_DIGEST: &str = "fnv1a64:5ec57029f2ff9d05";
const S02_IDENTITY_DIGEST: &str = "fnv1a64:aff2a32522ccb77f";

fn candidate_identity(
    catalog_token: &str,
    number: &str,
    path: Option<&str>,
    key_path: &str,
) -> CandidateIdentity {
    CandidateIdentity {
        catalog_token: catalog_token.to_owned(),
        number: number.to_owned(),
        path: path.map(str::to_owned),
        key_path: key_path.to_owned(),
    }
}

/// Normalized view of the tracked S02 candidate artifact: 6 unique
/// identities, 3 of them punkt. The caller parses the artifact and hands
/// this evidence over; the admission library itself never reads files.
fn evidence() -> CandidateEvidence {
    CandidateEvidence {
        artifact_schema: CANDIDATE_ARTIFACT_SCHEMA.to_owned(),
        lifecycle: "[proposed]".to_owned(),
        authoritative: false,
        artifact_path: CANDIDATE_ARTIFACT_PATH.to_owned(),
        artifact_sha256: S02_ARTIFACT_SHA256.to_owned(),
        source_digest: S02_SOURCE_DIGEST.to_owned(),
        identity_digest: S02_IDENTITY_DIGEST.to_owned(),
        candidates: vec![
            candidate_identity("glava", "1", None, "1"),
            candidate_identity("statya", "4", None, "4"),
            candidate_identity("punkt", "1", Some("statya-4/punkt-1"), "statya-4/punkt-1"),
            candidate_identity(
                "punkt",
                "4.1",
                Some("statya-4/punkt-4.1"),
                "statya-4/punkt-4.1",
            ),
            candidate_identity("statya", "5", None, "5"),
            candidate_identity("punkt", "1", Some("statya-5/punkt-1"), "statya-5/punkt-1"),
        ],
    }
}

fn legacy_row(path_needle: &str, level: &str, number: &str, cc: &str) -> AdmissionBinding {
    AdmissionBinding {
        path_needle: path_needle.to_owned(),
        level: level.to_owned(),
        number: number.to_owned(),
        key_path: None,
        cc: cc.to_owned(),
        provenance: AdmissionProvenance::LegacyHuman,
    }
}

fn candidate_row(
    path_needle: &str,
    level: &str,
    number: &str,
    key_path: &str,
    cc: &str,
) -> AdmissionBinding {
    AdmissionBinding {
        path_needle: path_needle.to_owned(),
        level: level.to_owned(),
        number: number.to_owned(),
        key_path: Some(key_path.to_owned()),
        cc: cc.to_owned(),
        provenance: AdmissionProvenance::CandidateBackedM202,
    }
}

/// Canonical-shaped admission source: 9 legacy human-admitted rows plus the
/// three D426 candidate-backed rows (glava-1/statya-4/statya-5 -> existing
/// CC identifiers). Row order is deliberately unsorted so the render test
/// proves ordering is imposed, not inherited.
fn admission_yaml() -> String {
    let rows = [
        "  - {path_needle: law_2013-04-05_44-fz, level: glava, number: \"2\", cc: cc:44-fz:glava-2, provenance: legacy-human}",
        "  - {path_needle: law_2013-04-05_44-fz, level: glava, number: \"3\", cc: cc:44-fz:glava-3, provenance: legacy-human}",
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"95\", cc: cc:44-fz:statya-95, provenance: legacy-human}",
        "  - {path_needle: law_2013-04-05_44-fz, level: glava, number: \"6\", cc: cc:44-fz:glava-6, provenance: legacy-human}",
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"43\", cc: cc:44-fz:statya-43, provenance: legacy-human}",
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"31\", cc: cc:44-fz:statya-31, provenance: legacy-human}",
        "  - {path_needle: n-435-fz, level: statya, number: \"3\", cc: cc:435fz:statya-3, provenance: legacy-human}",
        "  - {path_needle: n-435-fz, level: statya, number: \"1\", cc: cc:435fz:statya-1, provenance: legacy-human}",
        "  - {path_needle: n-435-fz, level: statya, number: \"2\", cc: cc:435fz:statya-2, provenance: legacy-human}",
        // D426: only these three rows are candidate-backed, each bound to an
        // already-existing CC identifier; punkt rows stay unadmitted.
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"5\", key_path: \"5\", cc: cc:44-fz:statya-5, provenance: m202-candidate-backed}",
        "  - {path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\", key_path: \"1\", cc: cc:44-fz:glava-1, provenance: m202-candidate-backed}",
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"4\", key_path: \"4\", cc: cc:44-fz:statya-4, provenance: m202-candidate-backed}",
    ];
    format!(
        "schema: {ADMISSION_SCHEMA_V1}\n\
         lifecycle: \"[proposed]\"\n\
         authoritative: false\n\
         candidate_artifact_path: {CANDIDATE_ARTIFACT_PATH}\n\
         candidate_artifact_sha256: {S02_ARTIFACT_SHA256}\n\
         candidate_source_digest: {S02_SOURCE_DIGEST}\n\
         candidate_identity_digest: {S02_IDENTITY_DIGEST}\n\
         admissions:\n{}",
        rows.join("\n")
    )
}

fn parsed_source() -> AdmissionSource {
    parse_admission_source(&admission_yaml()).expect("parse admission source")
}

#[test]
fn admission_source_parses_closed_schema_v1() {
    let src = parsed_source();
    assert_eq!(src.schema, ADMISSION_SCHEMA_V1);
    assert_eq!(src.lifecycle, "[proposed]");
    assert!(!src.authoritative);
    assert_eq!(src.candidate_artifact_path, CANDIDATE_ARTIFACT_PATH);
    assert_eq!(src.candidate_artifact_sha256, S02_ARTIFACT_SHA256);
    assert_eq!(src.candidate_source_digest, S02_SOURCE_DIGEST);
    assert_eq!(src.candidate_identity_digest, S02_IDENTITY_DIGEST);
    assert_eq!(src.bindings.len(), 12);
    assert_eq!(
        src.bindings
            .iter()
            .filter(|row| row.provenance == AdmissionProvenance::CandidateBackedM202)
            .count(),
        3
    );
    // D426 rows carry the candidate key_path; legacy rows stay flat.
    let d426 = src
        .bindings
        .iter()
        .find(|row| row.number == "4" && row.provenance == AdmissionProvenance::CandidateBackedM202)
        .expect("statya-4 candidate-backed row");
    assert_eq!(d426.key_path.as_deref(), Some("4"));
    assert_eq!(d426.cc, "cc:44-fz:statya-4");
    let legacy = src
        .bindings
        .iter()
        .find(|row| row.number == "31")
        .expect("legacy row");
    assert!(legacy.key_path.is_none());
    assert_eq!(legacy.provenance, AdmissionProvenance::LegacyHuman);
}

#[test]
fn admission_source_rejects_unknown_top_level_key() {
    let mut yaml = admission_yaml();
    yaml.push_str("extractor_minted: true\n");
    let err = parse_admission_source(&yaml).expect_err("unknown top-level key");
    assert!(matches!(
        err,
        RegistryAdmissionError::UnknownKey { ref key } if key == "extractor_minted"
    ));
}

#[test]
fn admission_source_rejects_unknown_row_key() {
    let mut yaml = admission_yaml();
    yaml.push_str(
        "  - {path_needle: n-44-fz, level: statya, number: \"1\", cc: cc:44fz:s1, mint: auto, provenance: legacy-human}\n",
    );
    let err = parse_admission_source(&yaml).expect_err("unknown row key");
    assert!(matches!(
        err,
        RegistryAdmissionError::UnknownKey { ref key } if key == "mint"
    ));
}

#[test]
fn admission_source_rejects_unknown_provenance_value() {
    let mut yaml = admission_yaml();
    yaml.push_str(
        "  - {path_needle: n-44-fz, level: statya, number: \"2\", cc: cc:44fz:s2, provenance: auto-extracted}\n",
    );
    let err = parse_admission_source(&yaml).expect_err("unknown provenance");
    assert!(matches!(err, RegistryAdmissionError::UnknownKey { .. }));
}

#[test]
fn admission_source_rejects_unsupported_schema() {
    let yaml = admission_yaml().replace(ADMISSION_SCHEMA_V1, "law-nexus-kb-hierarchy-admission/v2");
    let err = parse_admission_source(&yaml).expect_err("schema v2");
    assert!(matches!(
        err,
        RegistryAdmissionError::UnsupportedSchema { ref got }
            if got == "law-nexus-kb-hierarchy-admission/v2"
    ));
}

#[test]
fn admission_source_rejects_missing_required_field() {
    let yaml = admission_yaml().replace("lifecycle: \"[proposed]\"\n", "");
    let err = parse_admission_source(&yaml).expect_err("missing lifecycle");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingField { ref field } if field == "lifecycle"
    ));
}

#[test]
fn admit_binds_d426_identities_to_existing_cc() {
    let src = parsed_source();
    let admitted = admit_candidates(&evidence(), &src).expect("D426 admission");
    assert_eq!(admitted.lifecycle, "[proposed]");
    assert!(!admitted.authoritative);
    assert_eq!(admitted.bindings.len(), 12);
    // D426: exactly the three scoped identities, each mapped to the
    // already-existing CC identifier supplied by the admission source.
    let has_row = |level: &str, number: &str, cc: &str| {
        admitted
            .bindings
            .iter()
            .any(|row| row.level == level && row.number == number && row.cc == cc)
    };
    assert!(has_row("glava", "1", "cc:44-fz:glava-1"));
    assert!(has_row("statya", "4", "cc:44-fz:statya-4"));
    assert!(has_row("statya", "5", "cc:44-fz:statya-5"));
    // Non-claim: punkt candidates exist in the evidence but are never
    // auto-admitted; admission is explicit rows only.
    assert!(admitted.bindings.iter().all(|row| row.level != "punkt"));
}

#[test]
fn candidate_backed_row_without_key_path_is_missing_candidate() {
    let mut src = parsed_source();
    src.bindings.push(AdmissionBinding {
        path_needle: "law_2013-04-05_44-fz".to_owned(),
        level: "statya".to_owned(),
        number: "6".to_owned(),
        key_path: None,
        cc: "cc:44-fz:statya-6".to_owned(),
        provenance: AdmissionProvenance::CandidateBackedM202,
    });
    let err = admit_candidates(&evidence(), &src).expect_err("no key path");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingCandidate { .. }
    ));
}

#[test]
fn admit_rejects_missing_candidate() {
    let mut src = parsed_source();
    src.bindings.push(candidate_row(
        "law_2013-04-05_44-fz",
        "statya",
        "99",
        "statya-99",
        "cc:44-fz:statya-99",
    ));
    let err = admit_candidates(&evidence(), &src).expect_err("missing candidate");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingCandidate { ref key_path } if key_path == "statya-99"
    ));
}

#[test]
fn admit_rejects_level_number_key_path_mismatch() {
    // key_path "4" is the statya candidate: level glava disagrees.
    let mut src = parsed_source();
    src.bindings = vec![candidate_row(
        "law_2013-04-05_44-fz",
        "glava",
        "1",
        "4",
        "cc:44-fz:glava-1",
    )];
    let err = admit_candidates(&evidence(), &src).expect_err("level mismatch");
    assert!(matches!(
        err,
        RegistryAdmissionError::IdentityMismatch { ref key_path, .. } if key_path == "4"
    ));

    // number "5" disagrees with the statya-4 candidate behind key_path "4".
    let mut src = parsed_source();
    src.bindings = vec![candidate_row(
        "law_2013-04-05_44-fz",
        "statya",
        "5",
        "4",
        "cc:44-fz:statya-5",
    )];
    let err = admit_candidates(&evidence(), &src).expect_err("number mismatch");
    assert!(matches!(
        err,
        RegistryAdmissionError::IdentityMismatch { .. }
    ));
}

#[test]
fn admit_rejects_same_key_with_different_cc() {
    let mut src = parsed_source();
    // Same registry key as the admitted D426 statya-4 row, different CC.
    src.bindings.push(candidate_row(
        "law_2013-04-05_44-fz",
        "statya",
        "4",
        "4",
        "cc:44-fz:statya-9",
    ));
    let err = admit_candidates(&evidence(), &src).expect_err("cc conflict");
    assert!(matches!(
        err,
        RegistryAdmissionError::ConflictingComponentConcept { .. }
    ));
}

#[test]
fn admit_rejects_legacy_candidate_binding_conflict() {
    let mut src = parsed_source();
    src.bindings = vec![
        candidate_row(
            "law_2013-04-05_44-fz",
            "statya",
            "4",
            "4",
            "cc:44-fz:statya-4",
        ),
        legacy_row("law_2013-04-05_44-fz", "statya", "4", "cc:44-fz:statya-6"),
    ];
    let err = admit_candidates(&evidence(), &src).expect_err("legacy vs candidate");
    assert!(matches!(
        err,
        RegistryAdmissionError::ConflictingComponentConcept { .. }
    ));
}

#[test]
fn admit_rejects_exact_duplicate_rows() {
    let mut src = parsed_source();
    // Byte-identical to the existing D426 statya-4 row: rejected, never
    // silently deduplicated (plan-pinned behavior).
    src.bindings.push(candidate_row(
        "law_2013-04-05_44-fz",
        "statya",
        "4",
        "4",
        "cc:44-fz:statya-4",
    ));
    let err = admit_candidates(&evidence(), &src).expect_err("exact duplicate");
    assert!(matches!(
        err,
        RegistryAdmissionError::ConflictingDuplicate { .. }
    ));
}

#[test]
fn admit_rejects_duplicate_key_across_provenance() {
    let mut src = parsed_source();
    // One row per registry key: legacy + candidate-backed for the same key
    // with the same CC is still a duplicate, not a merge.
    src.bindings = vec![
        candidate_row(
            "law_2013-04-05_44-fz",
            "statya",
            "4",
            "4",
            "cc:44-fz:statya-4",
        ),
        legacy_row("law_2013-04-05_44-fz", "statya", "4", "cc:44-fz:statya-4"),
    ];
    let err = admit_candidates(&evidence(), &src).expect_err("provenance duplicate");
    assert!(matches!(
        err,
        RegistryAdmissionError::ConflictingDuplicate { .. }
    ));
}

#[test]
fn admit_rejects_malformed_or_empty_cc() {
    for cc in ["", "44-fz:statya-4", "cc:"] {
        let mut src = parsed_source();
        src.bindings[0].cc = cc.to_owned();
        let err = admit_candidates(&evidence(), &src).expect_err("malformed cc");
        assert!(
            matches!(
                err,
                RegistryAdmissionError::MalformedComponentConcept { .. }
            ),
            "cc={cc:?}"
        );
    }
}

fn drifted(mut source: AdmissionSource, bound_field: &str, value: &str) -> RegistryAdmissionError {
    match bound_field {
        "candidate_artifact_path" => source.candidate_artifact_path = value.to_owned(),
        "candidate_artifact_sha256" => source.candidate_artifact_sha256 = value.to_owned(),
        "candidate_source_digest" => source.candidate_source_digest = value.to_owned(),
        "candidate_identity_digest" => source.candidate_identity_digest = value.to_owned(),
        other => unreachable!("no such bound field: {other}"),
    }
    admit_candidates(&evidence(), &source).expect_err("bound field drift")
}

#[test]
fn admit_rejects_digest_drift() {
    for (bound_field, value) in [
        (
            "candidate_artifact_path",
            "prd/migration/rust-evidence/other.json",
        ),
        ("candidate_artifact_sha256", "00"),
        ("candidate_source_digest", "fnv1a64:0000000000000000"),
        ("candidate_identity_digest", "fnv1a64:1111111111111111"),
    ] {
        let err = drifted(parsed_source(), bound_field, value);
        assert!(
            matches!(
                err,
                RegistryAdmissionError::DigestDrift { ref field, .. } if field == bound_field
            ),
            "bound_field={bound_field}"
        );
    }
}

#[test]
fn admit_rejects_authority_escalation() {
    let evidence = evidence();
    let mut src = parsed_source();
    src.authoritative = true;
    assert!(matches!(
        admit_candidates(&evidence, &src),
        Err(RegistryAdmissionError::AuthorityEscalation { .. })
    ));

    let mut src = parsed_source();
    src.lifecycle = "[active]".to_owned();
    assert!(matches!(
        admit_candidates(&evidence, &src),
        Err(RegistryAdmissionError::AuthorityEscalation { .. })
    ));

    let mut escalated = evidence();
    escalated.authoritative = true;
    assert!(matches!(
        admit_candidates(&escalated, &parsed_source()),
        Err(RegistryAdmissionError::AuthorityEscalation { .. })
    ));

    let mut activated = evidence();
    activated.lifecycle = "[active]".to_owned();
    assert!(matches!(
        admit_candidates(&activated, &parsed_source()),
        Err(RegistryAdmissionError::AuthorityEscalation { .. })
    ));
}

#[test]
fn admit_rejects_unsupported_schemas() {
    let mut src = parsed_source();
    src.schema = "law-nexus-kb-hierarchy-admission/v2".to_owned();
    assert!(matches!(
        admit_candidates(&evidence(), &src),
        Err(RegistryAdmissionError::UnsupportedSchema { .. })
    ));

    let mut wrong_artifact = evidence();
    wrong_artifact.artifact_schema = "law-nexus-hierarchy-candidate-artifact/v2".to_owned();
    assert!(matches!(
        admit_candidates(&wrong_artifact, &parsed_source()),
        Err(RegistryAdmissionError::UnsupportedSchema { .. })
    ));
}

#[test]
fn render_is_deterministic_order_independent_and_sorted() {
    let src = parsed_source();
    let admitted = admit_candidates(&evidence(), &src).expect("admit");
    let first = render_registry(&admitted);
    assert_eq!(first, render_registry(&admitted), "stable across calls");

    // Input row order must not leak into the projection bytes.
    let mut reversed_bindings = src.bindings.clone();
    reversed_bindings.reverse();
    let reversed = AdmissionSource {
        bindings: reversed_bindings,
        ..src
    };
    let admitted_reversed = admit_candidates(&evidence(), &reversed).expect("admit reversed");
    assert_eq!(
        first,
        render_registry(&admitted_reversed),
        "order-independent"
    );

    // Sort key: (path_needle, level catalog order, key_path/number, cc).
    // glava sorts before statya within a needle; numbers are string-sorted
    // ("31" < "4"); needles are lexicographic (law_* < n-*).
    let expected = [
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\", cc: cc:44-fz:glava-1}",
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"2\", cc: cc:44-fz:glava-2}",
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"3\", cc: cc:44-fz:glava-3}",
        "- {path_needle: law_2013-04-05_44-fz, level: glava, number: \"6\", cc: cc:44-fz:glava-6}",
        "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"31\", cc: cc:44-fz:statya-31}",
        "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"4\", cc: cc:44-fz:statya-4}",
        "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"43\", cc: cc:44-fz:statya-43}",
        "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"5\", cc: cc:44-fz:statya-5}",
        "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"95\", cc: cc:44-fz:statya-95}",
        "- {path_needle: n-435-fz, level: statya, number: \"1\", cc: cc:435fz:statya-1}",
        "- {path_needle: n-435-fz, level: statya, number: \"2\", cc: cc:435fz:statya-2}",
        "- {path_needle: n-435-fz, level: statya, number: \"3\", cc: cc:435fz:statya-3}",
    ];
    let mut cursor = first.find("bindings:").expect("bindings heading");
    for row in expected {
        let at = first
            .find(row)
            .unwrap_or_else(|| panic!("row missing: {row}"));
        assert!(at > cursor, "row out of order: {row}");
        cursor = at;
    }
}

#[test]
fn render_pins_registry_shape_non_claims_and_runtime_parse() {
    let src = parsed_source();
    let admitted = admit_candidates(&evidence(), &src).expect("admit");
    let yaml = render_registry(&admitted);
    assert!(yaml.contains("schema_version: law-nexus-kb-hierarchy-registry/v1"));
    assert!(yaml.contains("lifecycle: \"[proposed]\""));
    assert!(yaml.contains("authoritative: false"));
    assert!(!yaml.contains("authoritative: true"));
    assert!(yaml.contains("does not mint"), "non-claim boundary stays");
    assert!(yaml.is_ascii(), "no raw legal text enters the projection");
    assert!(!yaml.contains("fnv1a64:"), "evidence digests stay out");
    assert!(!yaml.contains("marker_span"), "artifact internals stay out");

    // The projection must round-trip through the existing runtime reader.
    let reparsed = parse_hierarchy_registry(&yaml).expect("runtime parse");
    assert_eq!(reparsed.len(), 12);
    assert!(reparsed.iter().all(|row| row.level != "punkt"));
    assert!(reparsed
        .iter()
        .any(|row| row.level == "glava" && row.number == "1" && row.cc == "cc:44-fz:glava-1"));
    assert!(reparsed
        .iter()
        .any(|row| row.level == "statya" && row.number == "4" && row.cc == "cc:44-fz:statya-4"));
    assert!(reparsed
        .iter()
        .any(|row| row.level == "statya" && row.number == "5" && row.cc == "cc:44-fz:statya-5"));
}
