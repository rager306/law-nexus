//! TDD contract for the additive `m209-candidate-backed` provenance
//! vocabulary (M209-2yg6ix S02 T02, D545 / D546).
//!
//! The frozen M202 admission source cannot be edited in place without
//! breaking the `r035_proof_gate.rs` byte/sha pins (D544), so the M209
//! coverage expansion arrives as a *separate successor generation* whose
//! rows are marked with a new literal. This suite pins that the new literal
//! is additive only:
//!
//! - `m209-candidate-backed` parses as its own variant and reuses the
//!   candidate-resolution gates unchanged in *name*: `MissingCandidate` for a
//!   missing `key_path` or an absent `(level, number)` identity,
//!   `IdentityMismatch` for a `key_path`/`path` that names another identity,
//!   `ConflictingDuplicate` for a second record claiming the same identity;
//!   resolution itself is keyed by the D548 pair `(catalog_token, number)`,
//!   never by the bare `key_path` (which is shared across levels), while
//!   `key_path`/`path` stay cross-check fields;
//! - `m202-candidate-backed` keeps parsing and resolving exactly as before;
//! - `legacy-human` still requires no candidate at all;
//! - an unknown literal (`m209-candidate`) is an `UnknownKey`, never a
//!   silent legacy row;
//! - authority escalation (`authoritative: true` or a non-`[proposed]`
//!   lifecycle) is refused for both generations;
//! - the CC is always taken from the row and never derived from
//!   level/number — admitting against the M209 artifact mints nothing.
//!
//! Pure in-memory library contract: no I/O, no artifact reads, no registry
//! YAML writes, no new dependency (mirrors
//! `crates/ln-kb-ontology/tests/hierarchy_registry_admission.rs`).

use ln_kb_ontology::registry_admission::{
    admit_candidates, parse_admission_source, AdmissionBinding, AdmissionProvenance,
    AdmissionSource, CandidateEvidence, CandidateIdentity, RegistryAdmissionError,
};

const CANDIDATE_ARTIFACT_SCHEMA: &str = "law-nexus-hierarchy-candidate-artifact/v1";
const ADMISSION_SCHEMA_V1: &str = "law-nexus-kb-hierarchy-admission/v1";
/// Successor generation candidate artifact (T01 output, referenced by path).
const M209_ARTIFACT_PATH: &str =
    "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";
/// Exact SHA-256 of the live T01 M209 candidate artifact (321786 bytes).
/// The vocabulary contract is in-memory, but the fixture borrows the real pin
/// so the successor header binding it exercises is the one that ships.
const M209_ARTIFACT_SHA256: &str =
    "d0dcb90726619f551e8c14115f28fb8733be399c90ae3bb8290cafdf74410388";
const M209_SOURCE_DIGEST: &str = "fnv1a64:490f75a20886f160";
const M209_IDENTITY_DIGEST: &str = "fnv1a64:778beb9832032d4e";
/// Frozen M202 candidate artifact (the six identities of D426); its pins are
/// the ones the frozen admission source binds, so the D548 pair index must
/// resolve them byte for byte (D544 keeps that pair frozen).
const M202_ARTIFACT_PATH: &str = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
const M202_ARTIFACT_SHA256: &str =
    "50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6";
const M202_SOURCE_DIGEST: &str = "fnv1a64:5ec57029f2ff9d05";
const M202_IDENTITY_DIGEST: &str = "fnv1a64:aff2a32522ccb77f";

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

/// Normalized M209-shaped evidence: flat glava/statya identities plus one
/// nested punkt the successor source never admits (D546 keeps punkt
/// unadmitted).
fn evidence() -> CandidateEvidence {
    CandidateEvidence {
        artifact_schema: CANDIDATE_ARTIFACT_SCHEMA.to_owned(),
        lifecycle: "[proposed]".to_owned(),
        authoritative: false,
        artifact_path: M209_ARTIFACT_PATH.to_owned(),
        artifact_sha256: M209_ARTIFACT_SHA256.to_owned(),
        source_digest: M209_SOURCE_DIGEST.to_owned(),
        identity_digest: M209_IDENTITY_DIGEST.to_owned(),
        candidates: vec![
            candidate_identity("glava", "1", None, "1"),
            candidate_identity("statya", "8", None, "8"),
            candidate_identity("statya", "9", None, "9"),
            candidate_identity("punkt", "1", Some("statya-9/punkt-1"), "statya-9/punkt-1"),
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

fn m209_row(
    path_needle: &str,
    level: &str,
    number: &str,
    key_path: Option<&str>,
    cc: &str,
) -> AdmissionBinding {
    AdmissionBinding {
        path_needle: path_needle.to_owned(),
        level: level.to_owned(),
        number: number.to_owned(),
        key_path: key_path.map(str::to_owned),
        cc: cc.to_owned(),
        provenance: AdmissionProvenance::CandidateBackedM209,
    }
}

fn m202_row(
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

/// Render one admission row in the frozen flow style, optionally with a
/// `key_path`. The literal is emitted verbatim so unknown-literal tests can
/// bypass the typed helper.
fn render_row(row: &AdmissionBinding, literal: &str) -> String {
    let mut line = format!(
        "  - {{path_needle: {}, level: {}, number: \"{}\", ",
        row.path_needle, row.level, row.number
    );
    if let Some(key_path) = row.key_path.as_deref() {
        line.push_str(&format!("key_path: \"{key_path}\", "));
    }
    line.push_str(&format!("cc: {}, provenance: {literal}}}", row.cc));
    line
}

/// Canonical-shaped M209 successor admission source over a caller-supplied
/// row list. Header fields bind the M209 artifact evidence exactly.
fn source_from(rows: &[String]) -> String {
    format!(
        "schema: {ADMISSION_SCHEMA_V1}\n\
         lifecycle: \"[proposed]\"\n\
         authoritative: false\n\
         candidate_artifact_path: {M209_ARTIFACT_PATH}\n\
         candidate_artifact_sha256: {M209_ARTIFACT_SHA256}\n\
         candidate_source_digest: {M209_SOURCE_DIGEST}\n\
         candidate_identity_digest: {M209_IDENTITY_DIGEST}\n\
         admissions:\n{}",
        rows.join("\n")
    )
}

/// Mixed-generation source: one legacy row, one m202 row and the m209 rows
/// under test. Row order is deliberately unsorted.
fn mixed_text(m209: &[AdmissionBinding]) -> String {
    let mut rows = vec![
        render_row(
            &legacy_row("n-435-fz", "statya", "1", "cc:435fz:statya-1"),
            "legacy-human",
        ),
        render_row(
            &m202_row(
                "law_2013-04-05_44-fz",
                "glava",
                "1",
                "1",
                "cc:44-fz:glava-1",
            ),
            "m202-candidate-backed",
        ),
    ];
    rows.extend(
        m209.iter()
            .map(|row| render_row(row, "m209-candidate-backed")),
    );
    source_from(&rows)
}

fn parsed_mixed(m209: &[AdmissionBinding]) -> AdmissionSource {
    parse_admission_source(&mixed_text(m209)).expect("parse mixed-generation source")
}

#[test]
fn m209_literal_parses_as_its_own_candidate_backed_variant() {
    let src = parsed_mixed(&[
        m209_row(
            "law_2013-04-05_44-fz",
            "statya",
            "9",
            Some("9"),
            "cc:44-fz:statya-9",
        ),
        m209_row(
            "law_2013-04-05_44-fz",
            "statya",
            "1",
            None,
            "cc:44-fz:statya-1",
        ),
    ]);
    assert_eq!(src.bindings.len(), 4);
    let m209: Vec<_> = src
        .bindings
        .iter()
        .filter(|row| row.provenance == AdmissionProvenance::CandidateBackedM209)
        .collect();
    assert_eq!(m209.len(), 2);
    // The literal is not a relabel: m202 rows keep their own variant.
    assert_eq!(
        src.bindings
            .iter()
            .filter(|row| row.provenance == AdmissionProvenance::CandidateBackedM202)
            .count(),
        1
    );
    assert_eq!(
        src.bindings
            .iter()
            .filter(|row| row.provenance == AdmissionProvenance::LegacyHuman)
            .count(),
        1
    );
    // Predicate covers both candidate-backed generations only.
    assert!(AdmissionProvenance::CandidateBackedM209.is_candidate_backed());
    assert!(AdmissionProvenance::CandidateBackedM202.is_candidate_backed());
    assert!(!AdmissionProvenance::LegacyHuman.is_candidate_backed());
}

#[test]
fn m209_candidate_backed_row_without_key_path_is_missing_candidate() {
    let mut src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "9",
        Some("9"),
        "cc:44-fz:statya-9",
    )]);
    src.bindings.push(m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "1",
        None,
        "cc:44-fz:statya-1",
    ));
    let err = admit_candidates(&evidence(), &src).expect_err("m209 row without key_path");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingCandidate { .. }
    ));
}

#[test]
fn m209_candidate_backed_row_with_unknown_key_path_is_missing_candidate() {
    let src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "99",
        Some("statya-99"),
        "cc:44-fz:statya-99",
    )]);
    let err = admit_candidates(&evidence(), &src).expect_err("unknown candidate key_path");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingCandidate { ref key_path } if key_path == "statya-99"
    ));
}

#[test]
fn d548_row_level_number_absent_from_evidence_is_missing_candidate() {
    // D548 resolves by the row's own `(level, number)`, so a row naming a
    // level the artifact does not carry at that number cannot borrow another
    // level's candidate just because the bare `key_path` matches. The row
    // below used to be caught as a level mismatch against the `key_path`
    // index; under the pair index the glava-9 identity simply does not exist
    // and the row fails closed as a missing candidate.
    let src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "glava",
        "9",
        Some("9"),
        "cc:44-fz:glava-9",
    )]);
    let err = admit_candidates(&evidence(), &src).expect_err("no glava-9 identity");
    assert!(matches!(
        err,
        RegistryAdmissionError::MissingCandidate { ref key_path } if key_path == "9"
    ));
}

#[test]
fn d548_row_key_path_naming_another_identity_is_identity_mismatch() {
    // The pair resolves (statya-9 exists) but the row's `key_path` names
    // statya-8: the cross-check still refuses, so the pair key never lets a
    // lying `key_path` through.
    let src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "9",
        Some("8"),
        "cc:44-fz:statya-9",
    )]);
    let err = admit_candidates(&evidence(), &src).expect_err("key_path names statya-8");
    assert!(matches!(
        err,
        RegistryAdmissionError::IdentityMismatch { ref key_path, .. } if key_path == "8"
    ));
}

#[test]
fn m209_candidate_backed_row_with_number_mismatch_is_identity_mismatch() {
    let src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "8",
        Some("9"),
        "cc:44-fz:statya-8",
    )]);
    let err = admit_candidates(&evidence(), &src).expect_err("number mismatch");
    assert!(matches!(
        err,
        RegistryAdmissionError::IdentityMismatch { ref key_path, .. } if key_path == "9"
    ));
}

#[test]
fn m209_nested_candidate_path_disagreement_is_identity_mismatch() {
    // Candidate key exists and level/number agree, but its recorded ladder
    // disagrees with the row's key_path: still an identity mismatch.
    let mut nested = evidence();
    nested.candidates = vec![candidate_identity(
        "punkt",
        "1",
        Some("statya-9/punkt-2"),
        "statya-9/punkt-1",
    )];
    // Dedicated single-row source: the shared mixed fixture also carries an
    // m202 row whose candidate is absent from this narrowed evidence, so it
    // would fail first and mask the nested-path mismatch under test.
    let text = source_from(&[render_row(
        &m209_row(
            "law_2013-04-05_44-fz",
            "punkt",
            "1",
            Some("statya-9/punkt-1"),
            "cc:44-fz:statya-9-punkt-1",
        ),
        "m209-candidate-backed",
    )]);
    let src = parse_admission_source(&text).expect("parse nested source");
    let err = admit_candidates(&nested, &src).expect_err("nested path disagreement");
    assert!(matches!(
        err,
        RegistryAdmissionError::IdentityMismatch { ref key_path, .. }
            if key_path == "statya-9/punkt-1"
    ));
}

#[test]
fn m202_candidate_backed_still_parses_and_resolves() {
    let src = parsed_mixed(&[]);
    assert_eq!(src.bindings.len(), 2);
    let admitted = admit_candidates(&evidence(), &src).expect("m202 row still resolves");
    assert_eq!(admitted.bindings.len(), 2);
    // The m202 row resolves against the same evidence; the legacy row does
    // not need a candidate at all.
    assert!(admitted
        .bindings
        .iter()
        .any(|row| row.provenance == AdmissionProvenance::CandidateBackedM202));
    assert!(admitted
        .bindings
        .iter()
        .any(|row| row.provenance == AdmissionProvenance::LegacyHuman));
}

#[test]
fn legacy_human_row_needs_no_candidate() {
    let src = parsed_mixed(&[]);
    let admitted = admit_candidates(&evidence(), &src).expect("legacy row admits alone");
    let legacy = admitted
        .bindings
        .iter()
        .find(|row| row.provenance == AdmissionProvenance::LegacyHuman)
        .expect("legacy row survives admission");
    assert!(legacy.key_path.is_none());
    assert_eq!(legacy.cc, "cc:435fz:statya-1");
}

#[test]
fn unknown_m209_literal_is_rejected_not_silently_legacy() {
    let text = source_from(&[
        "  - {path_needle: law_2013-04-05_44-fz, level: statya, number: \"9\", key_path: \"9\", cc: cc:44-fz:statya-9, provenance: m209-candidate}"
            .to_string(),
    ]);
    let err = parse_admission_source(&text).expect_err("truncated literal is not a provenance");
    assert!(matches!(
        err,
        RegistryAdmissionError::UnknownKey { ref key } if key == "provenance=m209-candidate"
    ));
}

#[test]
fn m209_authority_escalation_is_refused() {
    // authoritative: true
    let escalated = mixed_text(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "9",
        Some("9"),
        "cc:44-fz:statya-9",
    )])
    .replace("authoritative: false", "authoritative: true");
    let src = parse_admission_source(&escalated).expect("source still parses");
    let err = admit_candidates(&evidence(), &src).expect_err("authoritative escalation");
    assert!(matches!(
        err,
        RegistryAdmissionError::AuthorityEscalation { .. }
    ));

    // lifecycle drift away from [proposed]
    let activated = mixed_text(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "9",
        Some("9"),
        "cc:44-fz:statya-9",
    )])
    .replace("lifecycle: \"[proposed]\"", "lifecycle: \"[active]\"");
    let src = parse_admission_source(&activated).expect("source still parses");
    let err = admit_candidates(&evidence(), &src).expect_err("lifecycle escalation");
    assert!(matches!(
        err,
        RegistryAdmissionError::AuthorityEscalation { .. }
    ));
}

#[test]
fn m209_admission_takes_cc_from_the_row_and_mints_nothing() {
    // Level/number imply nothing: the row's explicit CC is what is admitted,
    // even when it does not follow the level/number naming convention.
    let src = parsed_mixed(&[m209_row(
        "law_2013-04-05_44-fz",
        "statya",
        "9",
        Some("9"),
        "cc:legacy-authority:some-existing-identity",
    )]);
    let admitted = admit_candidates(&evidence(), &src).expect("row CC is authoritative");
    let row = admitted
        .bindings
        .iter()
        .find(|row| row.provenance == AdmissionProvenance::CandidateBackedM209)
        .expect("m209 row admitted");
    assert_eq!(row.cc, "cc:legacy-authority:some-existing-identity");
    // Non-claim: the nested punkt candidate exists but is never admitted.
    assert!(admitted.bindings.iter().all(|row| row.level != "punkt"));
    assert!(admitted
        .bindings
        .iter()
        .all(|row| row.cc != "cc:44-fz:statya-9"));
}

#[test]
fn m209_and_m202_rows_coexist_in_one_source() {
    let src = parsed_mixed(&[
        m209_row(
            "law_2013-04-05_44-fz",
            "statya",
            "9",
            Some("9"),
            "cc:44-fz:statya-9",
        ),
        m209_row(
            "law_2013-04-05_44-fz",
            "statya",
            "8",
            Some("8"),
            "cc:44-fz:statya-8",
        ),
    ]);
    let admitted = admit_candidates(&evidence(), &src).expect("mixed generations admit together");
    assert_eq!(admitted.bindings.len(), 4);
    assert_eq!(
        admitted
            .bindings
            .iter()
            .filter(|row| row.provenance == AdmissionProvenance::CandidateBackedM209)
            .count(),
        2
    );
    assert_eq!(admitted.lifecycle, "[proposed]");
    assert!(!admitted.authoritative);
}

// ---------------------------------------------------------------------------
// D548: the candidate index is keyed by the `(catalog_token, number)` pair
// ---------------------------------------------------------------------------

/// D548 sibling fixture: three candidates that share the bare `key_path`
/// `"1"` at three different levels, exactly as the live M209 artifact does
/// (glava-1 / statya-1 / paragraph-1). The pre-D548 index keyed by
/// `key_path` could hold only one of them and rejected the evidence.
fn sibling_evidence() -> CandidateEvidence {
    let mut shared = evidence();
    shared.candidates = vec![
        candidate_identity("glava", "1", None, "1"),
        candidate_identity("statya", "1", None, "1"),
        candidate_identity("paragraph", "1", None, "1"),
    ];
    shared
}

#[test]
fn d548_shared_bare_key_path_across_levels_is_not_a_conflicting_duplicate() {
    // (a) three candidates with key_path "1" and distinct (catalog_token,
    // number) coexist, and (c) both same-key_path rows resolve by their own
    // `(level, number)`: a single-slot key_path index could satisfy at most
    // one of the two rows, so admitting both is the decisive observation.
    let src = parsed_mixed(&[
        m209_row(
            "law_2013-04-05_44-fz",
            "statya",
            "1",
            Some("1"),
            "cc:44-fz:statya-1",
        ),
        m209_row(
            "law_2013-04-05_44-fz",
            "paragraph",
            "1",
            Some("1"),
            "cc:44-fz:paragraph-1",
        ),
    ]);
    let admitted =
        admit_candidates(&sibling_evidence(), &src).expect("shared key_path is not a conflict");
    assert_eq!(admitted.bindings.len(), 4);
    let m209: Vec<(&str, &str, &str)> = admitted
        .bindings
        .iter()
        .filter(|row| row.provenance == AdmissionProvenance::CandidateBackedM209)
        .map(|row| (row.level.as_str(), row.number.as_str(), row.cc.as_str()))
        .collect();
    assert!(m209.contains(&("statya", "1", "cc:44-fz:statya-1")));
    assert!(m209.contains(&("paragraph", "1", "cc:44-fz:paragraph-1")));
    // The pair key never leaks an identity into the admitted CC: the row's
    // own `cc:` field is what is bound.
    assert!(admitted
        .bindings
        .iter()
        .all(|row| row.cc != "cc:44-fz:glava-1"
            || row.provenance != AdmissionProvenance::CandidateBackedM209));
}

#[test]
fn d548_duplicate_identity_is_still_a_conflicting_duplicate() {
    // (b) a second candidate record claiming the *same* identity (same pair,
    // same key_path, same path) is still a conflicting duplicate, reported in
    // the `catalog_token/number` form; such a row could not resolve
    // unambiguously.
    let mut duplicated = evidence();
    duplicated
        .candidates
        .push(candidate_identity("statya", "8", None, "8"));
    let err = admit_candidates(&duplicated, &parsed_mixed(&[])).expect_err("duplicate identity");
    assert!(matches!(
        err,
        RegistryAdmissionError::ConflictingDuplicate { ref key } if key == "statya/8"
    ));
}

#[test]
fn d548_repeated_pair_under_different_ladders_is_not_a_conflicting_duplicate() {
    // A pair is only unique *within* one identity: `punkt` 1 recurs under
    // different parents with distinct key_path/path values, both in the live
    // M209 artifact (88 repeated pairs) and in the frozen M202 artifact. That
    // repetition is not a conflict — the ladders distinguish the identities.
    let mut repeated = evidence();
    repeated.candidates.push(candidate_identity(
        "punkt",
        "1",
        Some("statya-8/punkt-1"),
        "statya-8/punkt-1",
    ));
    admit_candidates(&repeated, &parsed_mixed(&[])).expect("repeated pair under distinct ladders");
}

/// Frozen M202 evidence: the six identities of the tracked S02 candidate
/// artifact, two of which share the pair `punkt`/1 under different ladders.
fn m202_evidence() -> CandidateEvidence {
    CandidateEvidence {
        artifact_schema: CANDIDATE_ARTIFACT_SCHEMA.to_owned(),
        lifecycle: "[proposed]".to_owned(),
        authoritative: false,
        artifact_path: M202_ARTIFACT_PATH.to_owned(),
        artifact_sha256: M202_ARTIFACT_SHA256.to_owned(),
        source_digest: M202_SOURCE_DIGEST.to_owned(),
        identity_digest: M202_IDENTITY_DIGEST.to_owned(),
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

#[test]
fn d548_frozen_m202_generation_still_resolves_unchanged() {
    // (e) the three frozen M202 candidate-backed rows (glava-1, statya-4,
    // statya-5) resolve exactly as before, and the frozen artifact's two
    // `punkt`/1 identities do not turn into a conflict.
    let rows = [
        render_row(
            &m202_row(
                "law_2013-04-05_44-fz",
                "glava",
                "1",
                "1",
                "cc:44-fz:glava-1",
            ),
            "m202-candidate-backed",
        ),
        render_row(
            &m202_row(
                "law_2013-04-05_44-fz",
                "statya",
                "4",
                "4",
                "cc:44-fz:statya-4",
            ),
            "m202-candidate-backed",
        ),
        render_row(
            &m202_row(
                "law_2013-04-05_44-fz",
                "statya",
                "5",
                "5",
                "cc:44-fz:statya-5",
            ),
            "m202-candidate-backed",
        ),
    ];
    let text = format!(
        "schema: {ADMISSION_SCHEMA_V1}\n\
         lifecycle: \"[proposed]\"\n\
         authoritative: false\n\
         candidate_artifact_path: {M202_ARTIFACT_PATH}\n\
         candidate_artifact_sha256: {M202_ARTIFACT_SHA256}\n\
         candidate_source_digest: {M202_SOURCE_DIGEST}\n\
         candidate_identity_digest: {M202_IDENTITY_DIGEST}\n\
         admissions:\n{}",
        rows.join("\n")
    );
    let src = parse_admission_source(&text).expect("frozen M202 source parses");
    let admitted = admit_candidates(&m202_evidence(), &src).expect("frozen generation resolves");
    assert_eq!(admitted.bindings.len(), 3);
    assert!(admitted
        .bindings
        .iter()
        .all(|row| row.provenance == AdmissionProvenance::CandidateBackedM202));
    assert!(admitted.bindings.iter().all(|row| row.level != "punkt"));
}
