//! R070 proof-gate pins (M201 S04).
//!
//! Count-only honesty gate over tracked evidence. The S04 JSON must keep
//! R070 `active` (D416), name all four coverage legs as bounded and
//! incomplete, and carry the mandatory non-claims. This suite refuses
//! `validated`/`complete` upgrades, refuses legal-commencement or ADR-0021
//! resolver claims, and pins the frozen S03 tracked chain
//! (`authoritative: false`, `HypothesizedFromOracleDiff`).
//!
//! No product code is exercised here: this is the evidence/lifecycle
//! honesty contour of the ADR-0015 verification matrix. Compile-red until
//! `prd/migration/rust-evidence/m201-s04-r070-proof-gate.json` exists is
//! the intended TDD red state of T01.

const PROOF_GATE_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m201-s04-r070-proof-gate.json");
const TRACKED_CHAIN_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m201-s03-tracked-chain.json");
const TRACKED_CHAIN_YAML: &str =
    include_str!("../../../prd/architecture/fz44-tracked-edition-chain.yaml");

/// sha256 of the frozen S03 tracked-chain JSON at pin time (2777 bytes).
/// T02 must recompute and cite the same value; any byte drift is a red test.
const S03_JSON_SHA256: &str = "9db7a0650ef8ba7054c620e97ec4bc6e037dbf80ef1349d1f0f6266d7bdc6531";

/// sha256 of the frozen S03 tracked-chain YAML pin (4143 bytes).
const S03_YAML_SHA256: &str = "5f7a7a17cb898f693bcb17f729286fb07d3d720c0726d9ced44caef10ab0a2e8";

/// sha256 of the cited 484-FZ C1 provenance source (canon_sha256 in both
/// frozen S03 artifacts).
const C1_484_CANON_SHA256: &str =
    "67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d";

fn assert_contains(haystack: &str, needle: &str, what: &str) {
    assert!(
        haystack.contains(needle),
        "{what} must contain {needle} (fail-closed honesty pin)"
    );
}

fn assert_count(haystack: &str, needle: &str, expected: usize, what: &str) {
    assert_eq!(
        haystack.matches(needle).count(),
        expected,
        "{what}: expected exactly {expected} occurrence(s) of {needle}"
    );
}

#[test]
fn proof_gate_json_pins_active_r070_bounded_non_authoritative() {
    for expected in [
        "\"schema_version\": \"law-nexus/r070-proof-gate/v1\"",
        "\"kind\": \"m201-s04-r070-proof-gate\"",
        "\"milestone\": \"M201-w8ljqx\"",
        "\"slice\": \"S04\"",
        "\"lifecycle\": \"[bounded]\"",
        "\"authoritative\": false",
        "\"requirement_id\": \"R070\"",
        "\"disposition\": \"active\"",
        "\"disposition_decision\": \"D416\"",
        "\"coverage_verdict\": \"incomplete-because-not-every-edition\"",
        S03_JSON_SHA256,
        S03_YAML_SHA256,
    ] {
        assert_contains(PROOF_GATE_JSON, expected, "R070 proof-gate JSON");
    }
    assert!(
        !PROOF_GATE_JSON.contains("\"authoritative\": true"),
        "proof-gate JSON stays non-authoritative"
    );
    // Frozen S03 artifacts are cited by recomputed source binding, not
    // re-inlined: their hashes must be pinned verbatim in the S04 JSON.
    assert_count(
        PROOF_GATE_JSON,
        S03_JSON_SHA256,
        1,
        "S03 JSON source binding",
    );
    assert_count(
        PROOF_GATE_JSON,
        S03_YAML_SHA256,
        1,
        "S03 YAML source binding",
    );
    assert_count(
        PROOF_GATE_JSON,
        C1_484_CANON_SHA256,
        1,
        "484-FZ C1 canon sha256 citation",
    );
}

#[test]
fn four_coverage_legs_are_named_and_not_validated_or_complete() {
    assert_contains(
        PROOF_GATE_JSON,
        "\"coverage_legs\": [",
        "R070 proof-gate JSON",
    );
    for leg_id in [
        "\"leg_id\": \"amending-acts\"",
        "\"leg_id\": \"affected-provisions\"",
        "\"leg_id\": \"commencement-and-transitional\"",
        "\"leg_id\": \"edition-delta\"",
    ] {
        assert_contains(PROOF_GATE_JSON, leg_id, "coverage inventory");
    }
    // Exactly four legs: jq `.coverage_legs[3]` set, `.coverage_legs[4]` null.
    assert_count(PROOF_GATE_JSON, "\"leg_id\":", 4, "coverage inventory");
    for banned in [
        "\"leg_verdict\": \"validated\"",
        "\"leg_verdict\": \"complete",
        "\"leg_verdict\": \"proven",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "no coverage leg may be upgraded: {banned}"
        );
    }
    // The tracked evidence stays one bounded chain, never corpus coverage.
    assert_contains(
        PROOF_GATE_JSON,
        "\"kept_lines\": 1",
        "tracked-chain citation",
    );
}

#[test]
fn non_claims_name_hypothesized_explicitly_absent_118_constructor_and_keep_r070_active() {
    assert_contains(PROOF_GATE_JSON, "\"non_claims\": [", "R070 proof-gate JSON");
    for mandatory in [
        // commencement stays hypothesized, never a legal determination
        "not a legal commencement determination",
        "hypothesized_from_oracle_diff",
        // ExplicitlyAbsent is an affirmative fixture slot, not a resolver
        "explicitly_absent",
        "not an ADR-0021 resolver",
        // corpus quantor: one chain != 118 editions
        "not the 118-edition corpus",
        "118",
        // constructor-as-evidence does not close R070 (D289/D308)
        "D289",
        "constructor-as-evidence",
        // no runtime vocabulary minted
        "no ActivationTrigger",
        // the disposition itself
        "R070 stays active",
    ] {
        assert_contains(PROOF_GATE_JSON, mandatory, "mandatory non-claim");
    }
    for banned in [
        "\"commencement\": \"legislative\"",
        "\"evidence_class\": \"legislative\"",
        "ADR-0021 resolver implemented",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "proof gate must not claim: {banned}"
        );
    }
}

#[test]
fn s03_tracked_json_still_carries_bounded_hypothesized_chain() {
    for expected in [
        "\"kind\": \"m201-s03-tracked-chain\"",
        "\"lifecycle\": \"[bounded]\"",
        "\"authoritative\": false",
        "act:484-fz:2024-12-26",
        "cc:44-fz:statya-93",
        "rec:amend:484-93",
        "\"evidence_class\": \"hypothesized_from_oracle_diff\"",
        "\"commencement_rule_ref\": \"rec:commencement:484-93:hypothesized\"",
        "\"transitional\": \"explicitly_absent\"",
        "\"kept_lines\": 1",
        "\"admissions\": 1",
        "R070 stays active",
        "not the 118-edition corpus",
        C1_484_CANON_SHA256,
    ] {
        assert_contains(TRACKED_CHAIN_JSON, expected, "frozen S03 tracked chain");
    }
    assert!(
        !TRACKED_CHAIN_JSON.contains("\"evidence_class\": \"legislative\""),
        "S03 chain must stay hypothesized, never Legislative"
    );
    assert_contains(
        TRACKED_CHAIN_YAML,
        "authoritative: false",
        "frozen S03 YAML pin",
    );
    assert_contains(
        TRACKED_CHAIN_YAML,
        "evidence_class: hypothesized_from_oracle_diff",
        "frozen S03 YAML pin",
    );
    assert_contains(
        TRACKED_CHAIN_YAML,
        "explicitly_absent",
        "frozen S03 YAML pin",
    );
}

#[test]
fn tracked_proof_gate_file_disposition_is_not_validated() {
    for banned in [
        "\"disposition\": \"validated\"",
        "\"disposition\": \"complete",
        "\"status\": \"validated\"",
        // the bare JSON string value anywhere: prose may warn against it,
        // a value may never carry it (D416)
        "\"validated\"",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "R070 proof gate must never carry {banned}: active until every edition is proven"
        );
    }
    assert_contains(
        TRACKED_CHAIN_YAML,
        "authoritative: false",
        "frozen S03 YAML pin",
    );
}
