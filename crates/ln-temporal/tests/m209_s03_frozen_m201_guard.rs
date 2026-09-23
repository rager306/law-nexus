//! M209/S03 T05: the frozen-boundary guard for the R070 scoped coverage ledger.
//!
//! S03 must prove it neither widened the frozen M201 R070 proof gate nor
//! promoted any requirement, and that the scoped coverage ledger it hands to
//! S04 stays bounded, non-authoritative and non-promoting (D416 / D430 / D539).
//! This suite is the always-on honesty contour of that claim:
//!
//! - the three frozen pins (tracked-chain JSON, tracked-chain YAML and the
//!   cited 484-FZ C1 canon) are re-hashed from live bytes, not quoted: a single
//!   changed byte is a red test, and the C1 canon arm is corpus-gated because
//!   the licensed export stays untracked;
//! - the frozen M201 R070 proof gate is re-hashed and its verdicts re-asserted;
//! - the ledger keeps R070 `active`, `gates_promoted` 0 and the aggregate
//!   coverage verdict `incomplete-because-not-every-edition`;
//! - every leg verdict stays `bounded-supporting` or `slot-filled-not-proven`,
//!   and no `validated` / `complete` / `proven` upgrade may appear;
//! - no S03 artifact claims `authoritative: true`;
//! - every runtime surface the two M208 admission records declare stays absent.
//!
//! This suite is evidence/lifecycle honesty only: it exercises no product code
//! and quotes no neighbouring contour PASS.

use std::fs;
use std::path::{Path, PathBuf};

const TRACKED_CHAIN_JSON: &[u8] =
    include_bytes!("../../../prd/migration/rust-evidence/m201-s03-tracked-chain.json");
const TRACKED_CHAIN_YAML: &[u8] =
    include_bytes!("../../../prd/architecture/fz44-tracked-edition-chain.yaml");
const M201_GATE_JSON: &[u8] =
    include_bytes!("../../../prd/migration/rust-evidence/m201-s04-r070-proof-gate.json");
const C1_PROVENANCE_YAML: &str =
    include_str!("../../../prd/architecture/c1-484-fz-provenance.yaml");

const FAMILY_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m209-s03-family-denominator.json");
const AMENDS_JSON: &str = include_str!(
    "../../../prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json"
);
const COMMENCEMENT_JSON: &str = include_str!(
    "../../../prd/migration/rust-evidence/m209-s03-commencement-transition-evidence.json"
);
const EDITION_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json");
const LEDGER_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m209-s03-r070-scope-ledger.json");

/// The five S03 artifacts this guard refuses to let claim authority.
const S03_ARTIFACTS: [(&str, &str); 5] = [
    ("m209-s03-family-denominator.json", FAMILY_JSON),
    ("m209-s03-amending-act-provision-evidence.json", AMENDS_JSON),
    (
        "m209-s03-commencement-transition-evidence.json",
        COMMENCEMENT_JSON,
    ),
    ("m209-s03-edition-delta-evidence.json", EDITION_JSON),
    ("m209-s03-r070-scope-ledger.json", LEDGER_JSON),
];

/// sha256 of the frozen S03 tracked-chain JSON (2777 bytes).
const S03_JSON_SHA256: &str = "9db7a0650ef8ba7054c620e97ec4bc6e037dbf80ef1349d1f0f6266d7bdc6531";
/// sha256 of the frozen S03 tracked-chain YAML pin (4143 bytes).
const S03_YAML_SHA256: &str = "5f7a7a17cb898f693bcb17f729286fb07d3d720c0726d9ced44caef10ab0a2e8";
/// sha256 of the cited 484-FZ C1 provenance source.
const C1_484_CANON_SHA256: &str =
    "67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d";
/// sha256 of the frozen M201 R070 proof gate.
const M201_GATE_SHA256: &str = "02db1cf033ec987bcca90bdb3a5d7d90a13f999048c41ef2d8999448e2ff3704";

/// Repository-relative path of the cited C1 canon (untracked, corpus-gated).
const C1_CANON_RELATIVE: &str =
    "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml";

/// The only leg verdicts the ledger may carry.
const ALLOWED_LEG_VERDICTS: [&str; 2] = ["bounded-supporting", "slot-filled-not-proven"];
/// The four R070 leg identifiers, in declaration order.
const LEG_IDS: [&str; 4] = [
    "amending-acts",
    "affected-provisions",
    "commencement-and-transitional",
    "edition-delta",
];

/// The two M208 admission records that declare the absent runtime surfaces.
const M208_ADMISSION_DOCS: [&str; 2] = [
    "prd/architecture/m208-s03-admission-commencement.md",
    "prd/architecture/m208-s04-admission-bounded-replay.md",
];

/// Headline declared surfaces that must stay absent.
const DECLARED_ABSENT_FLOOR: [&str; 12] = [
    "crates/ln-temporal/src/operation_admission.rs",
    "crates/ln-decode/src/change_commencement.rs",
    "crates/ln-decode/src/change_operand.rs",
    "crates/ln-decode/src/change_operation.rs",
    "crates/ln-decode/src/change_target.rs",
    "crates/ln-temporal/src/bounded_chain_replay.rs",
    "crates/ln-temporal/src/oracle_exam.rs",
    "crates/ln-temporal/tests/m208_s03_frozen_surface_guard.rs",
    "crates/ln-temporal/tests/m208_s04_frozen_surface_guard.rs",
    "scripts/m208_s03_admission_commencement_battery.test.mjs",
    "scripts/m208_s04_bounded_replay_battery.test.mjs",
    "prd/migration/rust-evidence/m208-s03-admission-commencement-battery.json",
];

/// Minimum number of distinct declared-absent paths the records must declare.
const DECLARED_ABSENT_MINIMUM: usize = 18;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

// ---------------------------------------------------------------------------
// dependency-free SHA-256, so the frozen pins are re-hashed from live bytes
// instead of quoted from strings the emitter itself wrote
// ---------------------------------------------------------------------------

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

const SHA256_H: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

/// SHA-256 digest of `bytes`, lowercase hex.
fn sha256_hex(bytes: &[u8]) -> String {
    let mut message = bytes.to_vec();
    let bit_len = (bytes.len() as u64).wrapping_mul(8);
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());

    let mut state = SHA256_H;
    for chunk in message.as_chunks::<64>().0 {
        let mut words = [0u32; 64];
        for (word, bytes) in words.iter_mut().zip(chunk.as_chunks::<4>().0) {
            *word = u32::from_be_bytes(*bytes);
        }
        for index in 16..64 {
            let s0 = words[index - 15].rotate_right(7)
                ^ words[index - 15].rotate_right(18)
                ^ (words[index - 15] >> 3);
            let s1 = words[index - 2].rotate_right(17)
                ^ words[index - 2].rotate_right(19)
                ^ (words[index - 2] >> 10);
            words[index] = words[index - 16]
                .wrapping_add(s0)
                .wrapping_add(words[index - 7])
                .wrapping_add(s1);
        }

        let mut a = state[0];
        let mut b = state[1];
        let mut c = state[2];
        let mut d = state[3];
        let mut e = state[4];
        let mut f = state[5];
        let mut g = state[6];
        let mut h = state[7];
        for (constant, word) in SHA256_K.iter().zip(words.iter()) {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choice = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(choice)
                .wrapping_add(*constant)
                .wrapping_add(*word);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        for (slot, value) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *slot = slot.wrapping_add(value);
        }
    }

    state
        .iter()
        .map(|word| format!("{word:08x}"))
        .collect::<String>()
}

/// The `## Owning surfaces` section of a M208 admission record.
fn owning_surfaces_section(text: &str) -> String {
    let mut section = String::new();
    let mut inside = false;
    for line in text.lines() {
        if let Some(heading) = line.strip_prefix("## ") {
            inside = heading.trim() == "Owning surfaces";
            continue;
        }
        if inside {
            section.push_str(line);
            section.push('\n');
        }
    }
    section
}

/// One line per bullet, with continuation lines folded in.
fn bullets(section: &str) -> Vec<String> {
    let mut bullets: Vec<String> = Vec::new();
    let mut current = String::new();
    for line in section.lines() {
        if let Some(rest) = line.trim_start().strip_prefix("- ") {
            if !current.is_empty() {
                bullets.push(std::mem::take(&mut current));
            }
            current.push_str(rest);
        } else if !current.is_empty() {
            let trimmed = line.trim();
            if !trimmed.is_empty() {
                current.push(' ');
                current.push_str(trimmed);
            }
        }
    }
    if !current.is_empty() {
        bullets.push(current);
    }
    bullets
}

/// Backticked repository paths of one text fragment.
fn backticked_paths(text: &str) -> Vec<String> {
    let mut paths = Vec::new();
    let mut rest = text;
    while let Some(start) = rest.find('`') {
        let after = &rest[start + 1..];
        let Some(end) = after.find('`') else {
            break;
        };
        let token = &after[..end];
        if token.starts_with("crates/")
            || token.starts_with("scripts/")
            || token.starts_with("prd/migration/")
        {
            paths.push(token.to_owned());
        }
        rest = &after[end + 1..];
    }
    paths
}

/// The paragraph(s) that declare inherited surfaces stay absent.
fn inherited_paragraphs(text: &str) -> String {
    let mut collected = String::new();
    let mut inside = false;
    for line in text.lines() {
        if line.contains("stay absent as well") {
            inside = true;
        }
        if inside {
            if line.trim().is_empty() {
                inside = false;
                continue;
            }
            collected.push_str(line);
            collected.push('\n');
        }
    }
    collected
}

// ---------------------------------------------------------------------------
// the frozen pins
// ---------------------------------------------------------------------------

#[test]
fn sha256_implementation_matches_the_known_pin_bytes() {
    // Anchors the hand-rolled digest against the frozen artifact itself: the
    // suite fails closed if the digest implementation ever drifts.
    assert_eq!(sha256_hex(TRACKED_CHAIN_JSON), S03_JSON_SHA256);
    assert_eq!(sha256_hex(b"abc"), {
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad".to_owned()
    });
}

#[test]
fn the_three_frozen_pins_are_byte_identical() {
    assert_eq!(
        sha256_hex(TRACKED_CHAIN_JSON),
        S03_JSON_SHA256,
        "the frozen S03 tracked-chain JSON moved"
    );
    assert_eq!(TRACKED_CHAIN_JSON.len(), 2777);
    assert_eq!(
        sha256_hex(TRACKED_CHAIN_YAML),
        S03_YAML_SHA256,
        "the frozen S03 tracked-chain YAML moved"
    );
    assert_eq!(TRACKED_CHAIN_YAML.len(), 4143);

    // The cited C1 canon is named by the tracked provenance pin, so the hex is
    // asserted against a tracked file before the corpus arm below.
    assert!(
        C1_PROVENANCE_YAML.contains(C1_484_CANON_SHA256),
        "the tracked C1 provenance pin must still cite the canon sha256"
    );

    // Corpus-gated: the licensed export stays untracked, so the canon bytes are
    // re-hashed only when they are on disk.
    let canon = repo_root().join(C1_CANON_RELATIVE);
    if canon.exists() {
        let bytes = fs::read(&canon).expect("the cited C1 canon is readable");
        assert_eq!(
            sha256_hex(&bytes),
            C1_484_CANON_SHA256,
            "the cited 484-FZ C1 canon moved"
        );
    } else {
        println!("M209_S03_C1_CANON_ABSENT");
    }
}

#[test]
fn the_frozen_m201_proof_gate_stays_active_and_unmoved() {
    assert_eq!(sha256_hex(M201_GATE_JSON), M201_GATE_SHA256);
    let gate = std::str::from_utf8(M201_GATE_JSON).expect("the gate is utf8");
    for expected in [
        "\"disposition\": \"active\"",
        "\"disposition_decision\": \"D416\"",
        "\"lifecycle\": \"[bounded]\"",
        "\"authoritative\": false",
        "\"coverage_verdict\": \"incomplete-because-not-every-edition\"",
        "\"leg_verdict\": \"bounded-supporting\"",
        "\"leg_verdict\": \"slot-filled-not-proven\"",
    ] {
        assert!(
            gate.contains(expected),
            "the frozen gate must keep {expected}"
        );
    }
    for banned in ["\"authoritative\": true", "\"leg_verdict\": \"validated\""] {
        assert!(
            !gate.contains(banned),
            "the frozen gate must not carry {banned}"
        );
    }
}

#[test]
fn the_ledger_keeps_r070_active_and_promotes_nothing() {
    for expected in [
        "\"schema\":\"law-nexus/r070-scope-ledger/v1\"",
        "\"kind\":\"m209-s03-r070-scope-ledger\"",
        "\"lifecycle\":\"[bounded]\"",
        "\"authoritative\":false",
        "\"requirement_id\":\"R070\"",
        "\"disposition\":\"active\"",
        "\"disposition_decision\":\"D416\"",
        "\"coverage_verdict\":\"incomplete-because-not-every-edition\"",
        "\"gates_promoted\":0",
        &format!("\"gate_sha256\":\"sha256:{M201_GATE_SHA256}\""),
        "\"gate_disposition\":\"active\"",
    ] {
        assert!(
            LEDGER_JSON.contains(expected),
            "the scoped coverage ledger must keep {expected}"
        );
    }
    for banned in [
        "\"authoritative\":true",
        "\"disposition\":\"validated\"",
        "\"disposition\":\"complete\"",
        "\"leg_verdict\":\"validated\"",
        "\"leg_verdict\":\"complete\"",
        "\"leg_verdict\":\"proven\"",
        "\"leg_verdict\":\"complete\"",
    ] {
        assert!(
            !LEDGER_JSON.contains(banned),
            "the ledger must never carry {banned}"
        );
    }
}

#[test]
fn every_ledger_leg_is_bounded_supporting_or_slot_filled_not_proven() {
    // Exactly four legs, in declaration order, as canonical compact JSON.
    assert_eq!(LEDGER_JSON.matches("\"leg_id\":\"").count(), LEG_IDS.len());
    for leg_id in LEG_IDS {
        assert!(
            LEDGER_JSON.contains(&format!("\"leg_id\":\"{leg_id}\"")),
            "the ledger must name the leg {leg_id}"
        );
    }
    for verdict in ALLOWED_LEG_VERDICTS {
        assert!(
            LEDGER_JSON.contains(&format!("\"leg_verdict\":\"{verdict}\"")),
            "the ledger must use the verdict {verdict}"
        );
    }
    // Exactly three bounded legs and one slot-filled leg.
    assert_eq!(
        LEDGER_JSON
            .matches("\"leg_verdict\":\"bounded-supporting\"")
            .count(),
        3
    );
    assert_eq!(
        LEDGER_JSON
            .matches("\"leg_verdict\":\"slot-filled-not-proven\"")
            .count(),
        1
    );
    // The commencement leg is the slot-filled one, and every leg declares an
    // explicit empty class-matched set (D553).
    assert_eq!(LEDGER_JSON.matches("\"class_matched_ids\":[]").count(), 4);
    let commencement = LEDGER_JSON
        .split("\"leg_id\":\"commencement-and-transitional\"")
        .nth(1)
        .expect("the commencement leg is present");
    assert!(
        commencement.starts_with(",\"leg_verdict\":\"slot-filled-not-proven\""),
        "the commencement leg must stay slot-filled-not-proven"
    );
}

#[test]
fn no_s03_artifact_claims_authority_or_a_closed_disposition() {
    for (name, artifact) in S03_ARTIFACTS {
        assert!(
            artifact.contains("\"authoritative\":false"),
            "{name} must declare authoritative false"
        );
        assert!(
            !artifact.contains("\"authoritative\":true"),
            "{name} must never claim authoritative true"
        );
        for banned in [
            "\"disposition\":\"validated\"",
            "\"disposition\":\"complete\"",
            "\"status\":\"validated\"",
        ] {
            assert!(
                !artifact.contains(banned),
                "{name} must never carry {banned}"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// the declared M208 absence, read out of the admission records
// ---------------------------------------------------------------------------

#[test]
fn m208_declared_runtime_surfaces_stay_absent() {
    let root = repo_root();
    let mut declared_absent: Vec<String> = Vec::new();
    let mut mod_registrations: Vec<(String, String)> = Vec::new();

    for doc in M208_ADMISSION_DOCS {
        let text = fs::read_to_string(root.join(doc)).expect("the admission record is tracked");
        let section = owning_surfaces_section(&text);
        assert!(
            !section.is_empty(),
            "{doc} must carry an `Owning surfaces` section"
        );
        for bullet in bullets(&section) {
            if bullet.contains("not created") {
                declared_absent.extend(backticked_paths(&bullet));
            }
            if bullet.contains("must stay absent") {
                let file = backticked_paths(&bullet)
                    .into_iter()
                    .next()
                    .expect("a registration bullet names its file");
                for token in bullet.split('`') {
                    if let Some(name) = token.strip_prefix("mod ") {
                        mod_registrations.push((file.clone(), name.to_owned()));
                    }
                }
            }
        }
        declared_absent.extend(backticked_paths(&inherited_paragraphs(&text)));
    }

    declared_absent.sort();
    declared_absent.dedup();
    assert!(
        declared_absent.len() >= DECLARED_ABSENT_MINIMUM,
        "the two records declare {} absent paths, fewer than the {} floor",
        declared_absent.len(),
        DECLARED_ABSENT_MINIMUM
    );
    for headline in DECLARED_ABSENT_FLOOR {
        assert!(
            declared_absent.iter().any(|path| path == headline),
            "the declared-absent set must still carry {headline}"
        );
    }

    for path in &declared_absent {
        assert!(
            !root.join(path).exists(),
            "a declared M208 runtime surface exists: {path}"
        );
    }

    assert!(
        mod_registrations.len() >= 3,
        "the records must declare the absent module registrations"
    );
    for (file, name) in &mod_registrations {
        let source = fs::read_to_string(root.join(file)).expect("the module file is tracked");
        assert!(
            !source.contains(&format!("mod {name}")),
            "`mod {name}` is registered in {file} while the admission is not-adopted"
        );
    }
}

/// Keeps `Path` and `PathBuf` imports load-bearing for the corpus arm.
#[test]
fn repo_root_resolves_the_repository() {
    let root: &Path = &repo_root();
    assert!(root.join("crates/ln-temporal").is_dir());
    assert!(root.join("prd/migration/rust-evidence").is_dir());
}
