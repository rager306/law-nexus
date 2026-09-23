//! M209/S03 T03: the fail-closed commencement and transitional boundary of the
//! named `cc:44-fz` chain, asserted through the admitted public API only.
//!
//! R070's third leg (applicable commencement and transitional rules) is
//! slot-filled-not-proven. The M208/S03 commencement admission stands at
//! `not-adopted` with `owner_admission_ref: none`, the M208/S04 checkpoint
//! stands the same way, and the M207/S04 C4 human pilot was not run, so no
//! commencement source of any class is admitted. This suite pins the honesty
//! surface that keeps that absence explicit instead of inferring commencement
//! from a date, a file name or an edition (D289 / D406 / D415):
//!
//! - `HypothesizedFromOracleDiff` and `EditorialHint` are stored or refused, and
//!   are never upgraded into a proven class;
//! - a missing commencement slot (`MissingCommencement`) stays distinguishable
//!   both from an unproven hint (`UnprovenCommencement`) and from the
//!   affirmative `TransitionalEvidence::ExplicitlyAbsent` slot (D406);
//! - `TransitionalEvidence::try_declared` and `try_explicitly_absent` keep
//!   their fail-closed semantics and never produce each other's variant;
//! - every runtime surface the two M208 admission records declare stays absent,
//!   with the declared paths read out of those records rather than guessed;
//! - no M208 selector identifier is minted anywhere under
//!   `crates/ln-temporal/src`.
//!
//! No neighbouring contour PASS is quoted as S03 evidence: this suite asserts
//! only its own boundary, and R070 stays active (D416).

use std::fs;
use std::path::{Path, PathBuf};

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    edition_delta, AmendingActId, AmendmentFacetKind, C1Candidate, CanonRecordId,
    ComponentConceptId, EvidenceClass, NormativeState, ThreeCanonEventLog,
};
use ln_temporal::provenance::{
    CommencementEvidence, EditionDeltaError, EditionProvenanceEnvelope, ProvenanceAdmission,
    ProvenanceConstructionError, TransitionalEvidence, PROVENANCE_NON_CLAIMS,
};

const TARGET: &str = "cc:44-fz:statya-93";
const AMENDING_ACT: &str = "act:484-fz:2024-12-26";
const AMENDMENT_RECORD: &str = "rec:amend:484-93";
const COMMENCEMENT_RULE_REF: &str = "rec:commencement:484-93:hypothesized";
const EFFECT_ISO: &str = "2024-12-26";
const FROM_ISO: &str = "2024-12-01";
const TO_ISO: &str = "2024-12-26";

/// The single source-bound absence justification this boundary may state.
const JUSTIFICATION: &str = "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).";

/// The two M208 admission records that declare the absent runtime surfaces.
const M208_ADMISSION_DOCS: [&str; 2] = [
    "prd/architecture/m208-s03-admission-commencement.md",
    "prd/architecture/m208-s04-admission-bounded-replay.md",
];

/// Headline declared surfaces that must stay absent, read from those records.
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

/// Minimum number of distinct declared-absent paths the records must declare,
/// so a rewritten record cannot silently shrink this guard to nothing.
const DECLARED_ABSENT_MINIMUM: usize = 18;

/// The two identifier families this boundary must never mint (D216).
const FORBIDDEN_IDENTIFIERS: [&str; 2] = ["ActivationTrigger", "TransitionalResolver"];

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn cc(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("valid component concept")
}

fn rid(value: &str) -> CanonRecordId {
    CanonRecordId::parse(value).expect("valid canon record id")
}

fn act(value: &str) -> AmendingActId {
    AmendingActId::parse(value).expect("valid amending act id")
}

fn day(value: &str) -> i64 {
    legal_act_effect_day_to_ordinal(value).expect("valid civil day")
}

fn absent() -> TransitionalEvidence {
    TransitionalEvidence::try_explicitly_absent(JUSTIFICATION).expect("source-bound justification")
}

fn commencement(class: EvidenceClass) -> CommencementEvidence {
    CommencementEvidence::try_new(day(EFFECT_ISO), class, COMMENCEMENT_RULE_REF)
        .expect("valid commencement evidence")
}

fn envelope_with(commencement: CommencementEvidence) -> EditionProvenanceEnvelope {
    EditionProvenanceEnvelope::try_new(
        vec![act(AMENDING_ACT)],
        vec![cc(TARGET)],
        commencement,
        absent(),
        vec![rid(AMENDMENT_RECORD)],
    )
    .expect("valid provenance packet")
}

fn tracked_log() -> ThreeCanonEventLog {
    let mut log = ThreeCanonEventLog::empty();
    log.append_c1_candidate(
        rid(AMENDMENT_RECORD),
        C1Candidate::LegislativeAmendment {
            target: cc(TARGET),
            effect_day: day(EFFECT_ISO),
            amending_act_raw: AMENDING_ACT.to_owned(),
            evidence: EvidenceClass::HypothesizedFromOracleDiff,
            facets: vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
            force_transition: Some(NormativeState::InForce),
        },
    )
    .expect("bounded C1 event");
    log
}

fn admission_with_class(class: EvidenceClass) -> ProvenanceAdmission {
    ProvenanceAdmission::try_new(
        cc(TARGET),
        day(EFFECT_ISO),
        class,
        COMMENCEMENT_RULE_REF,
        absent(),
    )
    .expect("a caller-supplied admission stores the raw class (D410)")
}

// ---------------------------------------------------------------------------
// the admitted public API
// ---------------------------------------------------------------------------

#[test]
fn hypothesized_class_is_preserved_and_an_editorial_hint_is_refused_not_upgraded() {
    let envelope = envelope_with(commencement(EvidenceClass::HypothesizedFromOracleDiff));
    assert_eq!(
        envelope.commencement().evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
    assert_eq!(
        envelope.commencement().rule_ref().as_str(),
        COMMENCEMENT_RULE_REF
    );
    assert_ne!(
        envelope.commencement().evidence_class(),
        EvidenceClass::Legislative,
        "a hypothesized class is stored as-is and never upgraded"
    );

    // The envelope refuses an editorial hint outright rather than storing it as
    // a proven class; that refusal is the D406 distinction and is asserted here.
    assert_eq!(
        CommencementEvidence::try_new(
            day(EFFECT_ISO),
            EvidenceClass::EditorialHint,
            COMMENCEMENT_RULE_REF
        ),
        Err(ProvenanceConstructionError::UnprovenCommencement)
    );

    // The admission, by contrast, stores the raw class (D410) and never
    // rewrites it, so the caller learns which kept target is unresolved.
    for class in [
        EvidenceClass::HypothesizedFromOracleDiff,
        EvidenceClass::EditorialHint,
    ] {
        let admission = admission_with_class(class);
        assert_eq!(admission.evidence_class(), class);
        assert_ne!(admission.evidence_class(), EvidenceClass::Legislative);
        assert_eq!(admission.rule_ref(), COMMENCEMENT_RULE_REF);
        assert_eq!(admission.target().as_str(), TARGET);
    }
}

#[test]
fn missing_commencement_stays_distinguishable_from_the_affirmative_absence_slot() {
    // A commencement leg with no reference at all is MissingCommencement.
    assert_eq!(
        CommencementEvidence::try_new(
            day(EFFECT_ISO),
            EvidenceClass::HypothesizedFromOracleDiff,
            ""
        ),
        Err(ProvenanceConstructionError::MissingCommencement)
    );
    assert_eq!(
        CommencementEvidence::try_new(
            day(EFFECT_ISO),
            EvidenceClass::HypothesizedFromOracleDiff,
            "   "
        ),
        Err(ProvenanceConstructionError::MissingCommencement)
    );
    // An unproven hint is UnprovenCommencement, never MissingCommencement.
    assert_eq!(
        CommencementEvidence::try_new(
            day(EFFECT_ISO),
            EvidenceClass::EditorialHint,
            COMMENCEMENT_RULE_REF
        ),
        Err(ProvenanceConstructionError::UnprovenCommencement)
    );
    assert_ne!(
        ProvenanceConstructionError::MissingCommencement,
        ProvenanceConstructionError::UnprovenCommencement,
        "D406: a missing slot and an unproven hint are distinct refusals"
    );

    // The transitional absence slot is an affirmative claim with a source, and
    // it is a different leg: it never answers a missing commencement.
    let affirmative = absent();
    assert_eq!(affirmative.justification(), Some(JUSTIFICATION));
    assert!(
        matches!(affirmative, TransitionalEvidence::ExplicitlyAbsent { .. }),
        "the affirmative absence slot is its own variant, not a commencement"
    );
    assert_eq!(
        TransitionalEvidence::try_declared(""),
        Err(ProvenanceConstructionError::MissingTransitional)
    );
    assert_ne!(
        ProvenanceConstructionError::MissingTransitional,
        ProvenanceConstructionError::MissingCommencement,
        "a missing transitional slot is not a missing commencement slot"
    );

    // Both legs coexist on one envelope without leaking into each other.
    let envelope = envelope_with(commencement(EvidenceClass::HypothesizedFromOracleDiff));
    assert_eq!(envelope.transitional().justification(), Some(JUSTIFICATION));
    assert_eq!(
        envelope.commencement().evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
}

#[test]
fn transitional_constructors_keep_their_fail_closed_semantics() {
    for value in ["", "   ", "\n\t"] {
        assert_eq!(
            TransitionalEvidence::try_explicitly_absent(value),
            Err(ProvenanceConstructionError::MissingTransitionalJustification)
        );
        assert_eq!(
            TransitionalEvidence::try_declared(value),
            Err(ProvenanceConstructionError::MissingTransitional)
        );
    }

    let declared = TransitionalEvidence::try_declared("rec:transition:1").expect("declared rule");
    assert!(matches!(declared, TransitionalEvidence::Declared(_)));
    assert_eq!(declared.justification(), None);

    let absent = absent();
    assert!(matches!(
        absent,
        TransitionalEvidence::ExplicitlyAbsent { .. }
    ));
    assert_eq!(absent.justification(), Some(JUSTIFICATION));

    // Neither constructor can produce the other's variant: the absence path is
    // affirmative and source-bound, the declared path names a rule.
    assert_ne!(declared, absent);
}

#[test]
fn an_editorial_hint_admission_surfaces_as_an_unresolved_whole_edition() {
    assert_eq!(
        edition_delta(
            &tracked_log(),
            day(FROM_ISO),
            day(TO_ISO),
            &[admission_with_class(EvidenceClass::EditorialHint)],
        ),
        Err(EditionDeltaError::Unresolved {
            target: cc(TARGET),
            cause: ProvenanceConstructionError::UnprovenCommencement,
        })
    );
    // A kept target with no admission at all is a different refusal, so the
    // boundary never collapses a packet gap into an unproven hint.
    assert_eq!(
        edition_delta(&tracked_log(), day(FROM_ISO), day(TO_ISO), &[]),
        Err(EditionDeltaError::MissingAdmission { target: cc(TARGET) })
    );
}

#[test]
fn provenance_non_claims_bound_the_commencement_and_transitional_slots() {
    let joined = PROVENANCE_NON_CLAIMS.join(" ");
    for fragment in [
        "R070 stays open",
        "Not ActivationTrigger",
        "Not TransitionalResolver",
        "ExplicitlyAbsent is an affirmative claim",
        "ADR-0021 stays [proposed]",
    ] {
        assert!(
            joined.contains(fragment),
            "the honesty surface must keep the non-claim {fragment}"
        );
    }
}

// ---------------------------------------------------------------------------
// the declared M208 absence, read out of the admission records
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// no minted selector vocabulary under the temporal source tree
// ---------------------------------------------------------------------------

/// Removes line comments, block comments, string literals and char literals, so
/// an identifier mentioned only in prose or in a string is not a minted symbol.
fn strip_comments_and_literals(source: &str) -> String {
    let bytes = source.as_bytes();
    let mut out = String::with_capacity(bytes.len());
    let mut index = 0usize;
    while index < bytes.len() {
        let byte = bytes[index];
        if byte == b'/' && bytes.get(index + 1) == Some(&b'/') {
            while index < bytes.len() && bytes[index] != b'\n' {
                index += 1;
            }
            continue;
        }
        if byte == b'/' && bytes.get(index + 1) == Some(&b'*') {
            index += 2;
            while index < bytes.len()
                && !(bytes[index] == b'*' && bytes.get(index + 1) == Some(&b'/'))
            {
                index += 1;
            }
            index = (index + 2).min(bytes.len());
            out.push(' ');
            continue;
        }
        if byte == b'"' {
            index += 1;
            while index < bytes.len() {
                if bytes[index] == b'\\' {
                    index += 2;
                    continue;
                }
                if bytes[index] == b'"' {
                    index += 1;
                    break;
                }
                index += 1;
            }
            out.push(' ');
            continue;
        }
        if byte == b'\'' {
            let escaped = bytes.get(index + 1) == Some(&b'\\');
            let closes = if escaped {
                bytes.get(index + 3) == Some(&b'\'')
            } else {
                bytes.get(index + 2) == Some(&b'\'')
            };
            if closes {
                index += if escaped { 4 } else { 3 };
                out.push(' ');
                continue;
            }
        }
        out.push(if byte.is_ascii() { byte as char } else { ' ' });
        index += 1;
    }
    out
}

/// True when `needle` occurs as a whole identifier in `haystack`.
fn identifier_occurs(haystack: &str, needle: &str) -> bool {
    let mut from = 0usize;
    while let Some(offset) = haystack[from..].find(needle) {
        let start = from + offset;
        let end = start + needle.len();
        let bounded = |character: Option<char>| {
            !character.is_some_and(|value| value.is_alphanumeric() || value == '_')
        };
        if bounded(haystack[..start].chars().next_back()) && bounded(haystack[end..].chars().next())
        {
            return true;
        }
        from = end;
    }
    false
}

fn rust_sources(directory: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(directory).expect("the source directory is readable") {
        let entry = entry.expect("a readable directory entry");
        let path = entry.path();
        if path.is_dir() {
            rust_sources(&path, out);
        } else if path.extension().is_some_and(|value| value == "rs") {
            out.push(path);
        }
    }
}

#[test]
fn no_m208_selector_identifier_is_minted_under_ln_temporal_src() {
    let root = repo_root();
    let source_root = root.join("crates/ln-temporal/src");
    let mut files = Vec::new();
    rust_sources(&source_root, &mut files);
    assert!(
        files.len() >= 10,
        "the temporal source tree must be walked, found {} files",
        files.len()
    );
    for file in &files {
        let source = fs::read_to_string(file).expect("a readable rust source");
        let code = strip_comments_and_literals(&source);
        for identifier in FORBIDDEN_IDENTIFIERS {
            assert!(
                !identifier_occurs(&code, identifier),
                "{identifier} is minted in {}",
                file.display()
            );
        }
    }

    // The stripper is load-bearing: the same tree does mention both identifiers
    // in prose and in a non-claim string, so an unstripped scan would fire.
    let provenance = fs::read_to_string(source_root.join("provenance.rs")).expect("provenance.rs");
    assert!(
        FORBIDDEN_IDENTIFIERS
            .iter()
            .all(|identifier| provenance.contains(identifier)),
        "the honesty surface mentions both identifiers in prose, so stripping is required"
    );
    let stripped = strip_comments_and_literals(&provenance);
    assert!(
        FORBIDDEN_IDENTIFIERS
            .iter()
            .all(|identifier| !identifier_occurs(&stripped, identifier)),
        "no identifier survives comment and literal stripping"
    );
}
