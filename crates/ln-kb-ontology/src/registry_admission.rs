//! Explicit candidate-backed admission into the kb-hierarchy registry
//! projection (M202-9qf3ta S03, D426).
//!
//! Pure library boundary over normalized caller-supplied evidence: the
//! generator parses the tracked candidate artifact (via ln-decode) and hands
//! over [`CandidateEvidence`]. This module performs no I/O, writes no files,
//! and never derives a ComponentConcept from level/number — admission binds
//! only the already-existing CC identifiers named explicitly by the
//! [`AdmissionSource`] rows. Output stays lifecycle `[proposed]` and
//! `authoritative: false`; rendered rows round-trip through the runtime
//! reader `crate::registry::parse_hierarchy_registry`.

use std::collections::BTreeMap;
use std::fmt;

use crate::catalog::strip_comment;

/// Closed admission-source schema handled by this module.
pub const ADMISSION_SCHEMA_V1: &str = "law-nexus-kb-hierarchy-admission/v1";
/// Candidate-artifact schema the caller-supplied evidence must carry.
pub const CANDIDATE_ARTIFACT_SCHEMA_V1: &str = "law-nexus-hierarchy-candidate-artifact/v1";
/// Registry projection schema emitted by [`render_registry`].
pub const REGISTRY_SCHEMA_V1: &str = "law-nexus-kb-hierarchy-registry/v1";

/// Only `[proposed]` evidence and sources may be admitted (authority gate).
const PROPOSED_LIFECYCLE: &str = "[proposed]";

/// One candidate identity from the S02 candidate artifact (normalized view).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateIdentity {
    pub catalog_token: String,
    pub number: String,
    /// CC-path ladder when the identity is nested (e.g. `statya-4/punkt-1`).
    pub path: Option<String>,
    /// Stable key the admission rows reference. Flat identities carry the
    /// bare number; nested ones carry the full ladder key.
    pub key_path: String,
}

/// Caller-supplied normalized view of a candidate artifact. The library
/// never reads files; binding to the artifact happens by exact equality of
/// the bound fields against [`AdmissionSource`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateEvidence {
    pub artifact_schema: String,
    pub lifecycle: String,
    pub authoritative: bool,
    pub artifact_path: String,
    pub artifact_sha256: String,
    pub source_digest: String,
    pub identity_digest: String,
    pub candidates: Vec<CandidateIdentity>,
}

/// Where an admission row came from. `m202-candidate-backed` rows must carry
/// a `key_path` that resolves against the candidate evidence; legacy rows
/// are the pre-existing human-admitted registry rows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionProvenance {
    LegacyHuman,
    CandidateBackedM202,
}

impl AdmissionProvenance {
    fn parse(value: &str) -> Option<Self> {
        match value {
            "legacy-human" => Some(Self::LegacyHuman),
            "m202-candidate-backed" => Some(Self::CandidateBackedM202),
            _ => None,
        }
    }
}

/// One explicit admission row: a registry key plus the existing CC it binds.
/// A ComponentConcept is never derived from level/number; `cc` is the only
/// CC source (D426).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionBinding {
    pub path_needle: String,
    pub level: String,
    pub number: String,
    /// Candidate key_path for `m202-candidate-backed` rows; `None` for
    /// legacy human-admitted rows.
    pub key_path: Option<String>,
    pub cc: String,
    pub provenance: AdmissionProvenance,
}

/// Closed admission source (`law-nexus-kb-hierarchy-admission/v1`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionSource {
    pub schema: String,
    pub lifecycle: String,
    pub authoritative: bool,
    pub candidate_artifact_path: String,
    pub candidate_artifact_sha256: String,
    pub candidate_source_digest: String,
    pub candidate_identity_digest: String,
    pub bindings: Vec<AdmissionBinding>,
}

/// Admitted registry projection: validated input rows plus the pinned
/// `[proposed]` / `authoritative: false` metadata, ready for
/// [`render_registry`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmittedRegistry {
    pub schema: String,
    pub lifecycle: String,
    pub authoritative: bool,
    pub bindings: Vec<AdmissionBinding>,
}

/// Typed admission failure modes. Every rejection happens before any
/// rendering, so a rendered projection only exists for fully validated
/// admissions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegistryAdmissionError {
    /// A key outside the closed admission schema was found.
    UnknownKey { key: String },
    /// Source or evidence names a schema other than the pinned v1 one.
    UnsupportedSchema { got: String },
    /// A required admission field is absent.
    MissingField { field: String },
    /// A candidate-backed row references an absent (or absent-keyed)
    /// candidate identity.
    MissingCandidate { key_path: String },
    /// The referenced candidate disagrees with the row's level/number/path.
    IdentityMismatch { key_path: String, detail: String },
    /// The row's CC is not a well-formed `cc:<authority>:<local>` string.
    MalformedComponentConcept { cc: String },
    /// Two rows share a registry key but bind different CC identifiers.
    ConflictingComponentConcept {
        key: String,
        existing: String,
        conflicting: String,
    },
    /// Two rows share a registry key and the same CC — still a duplicate,
    /// rejected instead of being silently deduplicated.
    ConflictingDuplicate { key: String },
    /// A source-bound artifact field drifted from the supplied evidence.
    DigestDrift {
        field: String,
        expected: String,
        got: String,
    },
    /// Source or evidence claims authority it may not claim.
    AuthorityEscalation { detail: String },
}

impl fmt::Display for RegistryAdmissionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnknownKey { key } => {
                write!(formatter, "admission source has unknown key {key:?}")
            }
            Self::UnsupportedSchema { got } => write!(
                formatter,
                "unsupported schema {got:?}, expected {ADMISSION_SCHEMA_V1}"
            ),
            Self::MissingField { field } => {
                write!(formatter, "admission field {field:?} is missing")
            }
            Self::MissingCandidate { key_path } => write!(
                formatter,
                "candidate-backed row references missing candidate {key_path:?}"
            ),
            Self::IdentityMismatch { key_path, detail } => {
                write!(formatter, "candidate {key_path:?} identity mismatch: {detail}")
            }
            Self::MalformedComponentConcept { cc } => {
                write!(formatter, "malformed component concept {cc:?}")
            }
            Self::ConflictingComponentConcept {
                key,
                existing,
                conflicting,
            } => write!(
                formatter,
                "registry key {key:?} binds conflicting CC identifiers {existing:?} and {conflicting:?}"
            ),
            Self::ConflictingDuplicate { key } => {
                write!(formatter, "duplicate admission rows for registry key {key:?}")
            }
            Self::DigestDrift {
                field,
                expected,
                got,
            } => write!(
                formatter,
                "bound field {field:?} drifted: expected {expected:?}, got {got:?}"
            ),
            Self::AuthorityEscalation { detail } => {
                write!(formatter, "authority escalation: {detail}")
            }
        }
    }
}

impl std::error::Error for RegistryAdmissionError {}

/// Parse the closed admission source. Unknown top-level or row keys, unknown
/// provenance values, and an unsupported schema fail closed; content after a
/// row's closing brace is re-scanned so appended fixtures cannot smuggle an
/// unknown key past the parser.
pub fn parse_admission_source(text: &str) -> Result<AdmissionSource, RegistryAdmissionError> {
    let mut schema: Option<String> = None;
    let mut lifecycle: Option<String> = None;
    let mut authoritative: Option<bool> = None;
    let mut candidate_artifact_path: Option<String> = None;
    let mut candidate_artifact_sha256: Option<String> = None;
    let mut candidate_source_digest: Option<String> = None;
    let mut candidate_identity_digest: Option<String> = None;
    let mut admissions_seen = false;
    let mut bindings: Vec<AdmissionBinding> = Vec::new();

    for raw in text.lines() {
        let trimmed = strip_comment(raw).trim();
        if trimmed.is_empty() {
            continue;
        }
        // One physical line can carry several logical segments: a fixture or
        // generator may append content directly after a row's closing brace.
        let mut rest = trimmed;
        while !rest.is_empty() {
            if rest.starts_with('-') && (rest.len() == 1 || rest.as_bytes()[1] == b' ') {
                let (binding, tail) = parse_admission_row(rest)?;
                bindings.push(binding);
                rest = tail;
                continue;
            }
            let Some((key, value)) = split_field(rest) else {
                return Err(RegistryAdmissionError::UnknownKey {
                    key: rest.to_owned(),
                });
            };
            match key {
                "schema" => schema = Some(unquote(value)),
                "lifecycle" => lifecycle = Some(unquote(value)),
                "authoritative" => authoritative = Some(parse_authoritative(value)?),
                "candidate_artifact_path" => candidate_artifact_path = Some(unquote(value)),
                "candidate_artifact_sha256" => candidate_artifact_sha256 = Some(unquote(value)),
                "candidate_source_digest" => candidate_source_digest = Some(unquote(value)),
                "candidate_identity_digest" => candidate_identity_digest = Some(unquote(value)),
                "admissions" if value.is_empty() => admissions_seen = true,
                other => {
                    return Err(RegistryAdmissionError::UnknownKey {
                        key: other.to_owned(),
                    });
                }
            }
            rest = "";
        }
    }

    let missing = |field: &str| RegistryAdmissionError::MissingField {
        field: field.to_owned(),
    };
    let schema = schema.ok_or_else(|| missing("schema"))?;
    let lifecycle = lifecycle.ok_or_else(|| missing("lifecycle"))?;
    let authoritative = authoritative.ok_or_else(|| missing("authoritative"))?;
    let candidate_artifact_path =
        candidate_artifact_path.ok_or_else(|| missing("candidate_artifact_path"))?;
    let candidate_artifact_sha256 =
        candidate_artifact_sha256.ok_or_else(|| missing("candidate_artifact_sha256"))?;
    let candidate_source_digest =
        candidate_source_digest.ok_or_else(|| missing("candidate_source_digest"))?;
    let candidate_identity_digest =
        candidate_identity_digest.ok_or_else(|| missing("candidate_identity_digest"))?;
    if !admissions_seen {
        return Err(missing("admissions"));
    }
    if schema != ADMISSION_SCHEMA_V1 {
        return Err(RegistryAdmissionError::UnsupportedSchema { got: schema });
    }
    Ok(AdmissionSource {
        schema,
        lifecycle,
        authoritative,
        candidate_artifact_path,
        candidate_artifact_sha256,
        candidate_source_digest,
        candidate_identity_digest,
        bindings,
    })
}

/// Validate the candidate evidence against the admission source and produce
/// the admitted registry projection. Gates run in a fixed order before any
/// output exists: schemas, authority, bound-field equality, CC
/// well-formedness, candidate resolution, registry-key conflicts.
pub fn admit_candidates(
    evidence: &CandidateEvidence,
    source: &AdmissionSource,
) -> Result<AdmittedRegistry, RegistryAdmissionError> {
    if source.schema != ADMISSION_SCHEMA_V1 {
        return Err(RegistryAdmissionError::UnsupportedSchema {
            got: source.schema.clone(),
        });
    }
    if evidence.artifact_schema != CANDIDATE_ARTIFACT_SCHEMA_V1 {
        return Err(RegistryAdmissionError::UnsupportedSchema {
            got: evidence.artifact_schema.clone(),
        });
    }

    // Authority gates: admission never escalates lifecycle or authority.
    if source.authoritative || source.lifecycle != PROPOSED_LIFECYCLE {
        return Err(RegistryAdmissionError::AuthorityEscalation {
            detail: "admission source must stay [proposed] and authoritative: false".to_owned(),
        });
    }
    if evidence.authoritative || evidence.lifecycle != PROPOSED_LIFECYCLE {
        return Err(RegistryAdmissionError::AuthorityEscalation {
            detail: "candidate evidence must stay [proposed] and authoritative: false".to_owned(),
        });
    }

    // Evidence binding: every bound field must match exactly.
    for (field, expected, got) in [
        (
            "candidate_artifact_path",
            &source.candidate_artifact_path,
            &evidence.artifact_path,
        ),
        (
            "candidate_artifact_sha256",
            &source.candidate_artifact_sha256,
            &evidence.artifact_sha256,
        ),
        (
            "candidate_source_digest",
            &source.candidate_source_digest,
            &evidence.source_digest,
        ),
        (
            "candidate_identity_digest",
            &source.candidate_identity_digest,
            &evidence.identity_digest,
        ),
    ] {
        if expected != got {
            return Err(RegistryAdmissionError::DigestDrift {
                field: field.to_owned(),
                expected: expected.clone(),
                got: got.clone(),
            });
        }
    }

    // Candidate index; a duplicated candidate key in the evidence is a
    // conflicting duplicate, not an input-order artifact.
    let mut candidates: BTreeMap<&str, &CandidateIdentity> = BTreeMap::new();
    for candidate in &evidence.candidates {
        if candidates
            .insert(candidate.key_path.as_str(), candidate)
            .is_some()
        {
            return Err(RegistryAdmissionError::ConflictingDuplicate {
                key: candidate.key_path.clone(),
            });
        }
    }

    // CC well-formedness is checked for every row, regardless of provenance.
    for row in &source.bindings {
        if !is_well_formed_component_concept(&row.cc) {
            return Err(RegistryAdmissionError::MalformedComponentConcept { cc: row.cc.clone() });
        }
    }

    // Candidate-backed rows must resolve to a real candidate identity and
    // agree with it on level and number (D426). The CC still comes from the
    // row, never from level/number.
    for row in &source.bindings {
        if row.provenance != AdmissionProvenance::CandidateBackedM202 {
            continue;
        }
        let Some(key_path) = row.key_path.as_deref() else {
            return Err(RegistryAdmissionError::MissingCandidate {
                key_path: format!("{}/{}", row.level, row.number),
            });
        };
        let Some(candidate) = candidates.get(key_path) else {
            return Err(RegistryAdmissionError::MissingCandidate {
                key_path: key_path.to_owned(),
            });
        };
        if candidate.catalog_token != row.level || candidate.number != row.number {
            return Err(RegistryAdmissionError::IdentityMismatch {
                key_path: key_path.to_owned(),
                detail: format!(
                    "row {}/{} does not match candidate {}/{}",
                    row.level, row.number, candidate.catalog_token, candidate.number
                ),
            });
        }
        if let Some(path) = candidate.path.as_deref() {
            if path != key_path {
                return Err(RegistryAdmissionError::IdentityMismatch {
                    key_path: key_path.to_owned(),
                    detail: format!("candidate path {path:?} disagrees with key_path"),
                });
            }
        }
    }

    // Registry-key uniqueness: same key with a different CC is a conflict;
    // same key with the same CC is still a duplicate and is rejected rather
    // than silently deduplicated.
    let mut seen: BTreeMap<(&str, &str, &str), &AdmissionBinding> = BTreeMap::new();
    for row in &source.bindings {
        let key = (
            row.path_needle.as_str(),
            row.level.as_str(),
            row.number.as_str(),
        );
        match seen.get(&key) {
            None => {
                seen.insert(key, row);
            }
            Some(existing) => {
                let key = format!("{}/{}/{}", row.path_needle, row.level, row.number);
                if existing.cc != row.cc {
                    return Err(RegistryAdmissionError::ConflictingComponentConcept {
                        key,
                        existing: existing.cc.clone(),
                        conflicting: row.cc.clone(),
                    });
                }
                return Err(RegistryAdmissionError::ConflictingDuplicate { key });
            }
        }
    }

    Ok(AdmittedRegistry {
        schema: REGISTRY_SCHEMA_V1.to_owned(),
        lifecycle: source.lifecycle.clone(),
        authoritative: false,
        bindings: source.bindings.clone(),
    })
}

/// Render the admitted registry as the deterministic complete registry YAML
/// projection. Rows sort by `(path_needle, level catalog order,
/// key_path/number, cc)`; the byte output is input-order-independent and
/// round-trips through `crate::registry::parse_hierarchy_registry`.
pub fn render_registry(admitted: &AdmittedRegistry) -> String {
    let mut rows: Vec<&AdmissionBinding> = admitted.bindings.iter().collect();
    rows.sort_by_key(|row| registry_sort_key(row));

    let mut out = String::new();
    out.push_str("# Explicit marker -> ComponentConcept bindings (KBO-R013 / R041 companion)\n");
    out.push_str("#\n");
    out.push_str("# Lifecycle: [proposed]\n");
    out.push_str("# Non-authority: not legal identity, not CTV text, not 44-FZ history,\n");
    out.push_str("# not InForce, not Applicable. Bindings are human-admitted fixture keys.\n");
    out.push_str("# A path that matches no needle gets an empty map (all markers Unknown).\n");
    out.push('\n');
    out.push_str("schema_version: ");
    out.push_str(REGISTRY_SCHEMA_V1);
    out.push('\n');
    out.push_str("lifecycle: \"[proposed]\"\n");
    out.push_str("authoritative: false\n");
    out.push_str("boundary: >\n");
    out.push_str("  Scoped fixture registry only. Number+level still does not mint a CC\n");
    out.push_str("  outside this table. Same-level articles form a forest. A fixture with\n");
    out.push_str(
        "  glava then statya drafts attach; it still does not write the membership log.\n",
    );
    out.push('\n');
    out.push_str("bindings:\n");
    for row in rows {
        out.push_str(&render_row(row));
        out.push('\n');
    }
    out
}

/// Render one binding in the registry projection's flow style. Flat keys
/// omit `path` (D192); nested ladders (`key_path` containing `/`) carry it.
fn render_row(row: &AdmissionBinding) -> String {
    let mut line = format!(
        "- {{path_needle: {}, level: {}, number: \"{}\", cc: {}",
        row.path_needle, row.level, row.number, row.cc
    );
    if let Some(path) = row.key_path.as_deref().filter(|key| key.contains('/')) {
        line.push_str(", path: ");
        line.push_str(path);
    }
    line.push('}');
    line
}

/// Catalog ordering used for deterministic render: glava before statya
/// before punkt; unknown levels sort after the known catalog (then
/// lexicographically) so the order stays total for closed inputs.
fn level_catalog_rank(level: &str) -> u8 {
    match level {
        "glava" => 0,
        "statya" => 1,
        "punkt" => 2,
        _ => 3,
    }
}

fn registry_sort_key(row: &AdmissionBinding) -> (String, u8, String, String, String) {
    (
        row.path_needle.clone(),
        level_catalog_rank(&row.level),
        row.level.clone(),
        row.key_path.clone().unwrap_or_else(|| row.number.clone()),
        row.cc.clone(),
    )
}

/// Well-formed CC check: `cc:<authority>:<local...>` with no empty segment.
/// Structural only — identity is whatever the admission row explicitly
/// names; level/number never contribute (D426).
fn is_well_formed_component_concept(cc: &str) -> bool {
    let Some(rest) = cc.strip_prefix("cc:") else {
        return false;
    };
    !rest.is_empty() && rest.split(':').all(|segment| !segment.is_empty())
}

/// Parse one `- {field: value, ...}` admission row. Returns the row and the
/// unconsumed tail after the closing brace (empty for a well-formed line).
fn parse_admission_row(line: &str) -> Result<(AdmissionBinding, &str), RegistryAdmissionError> {
    let open = line
        .find('{')
        .ok_or_else(|| RegistryAdmissionError::UnknownKey {
            key: "admissions row without flow mapping".to_owned(),
        })?;
    let close = line[open..]
        .find('}')
        .ok_or_else(|| RegistryAdmissionError::UnknownKey {
            key: "admissions row without closing brace".to_owned(),
        })?
        + open;
    let body = &line[open + 1..close];

    let mut path_needle: Option<String> = None;
    let mut level: Option<String> = None;
    let mut number: Option<String> = None;
    let mut key_path: Option<String> = None;
    let mut cc: Option<String> = None;
    let mut provenance: Option<AdmissionProvenance> = None;
    for field in body.split(',') {
        let field = field.trim();
        if field.is_empty() {
            continue;
        }
        let Some((key, value)) = split_field(field) else {
            return Err(RegistryAdmissionError::UnknownKey {
                key: field.to_owned(),
            });
        };
        match key {
            "path_needle" => path_needle = Some(unquote(value)),
            "level" => level = Some(unquote(value)),
            "number" => number = Some(unquote(value)),
            "key_path" => key_path = Some(unquote(value)),
            "cc" => cc = Some(unquote(value)),
            "provenance" => {
                provenance = Some(AdmissionProvenance::parse(value).ok_or_else(|| {
                    RegistryAdmissionError::UnknownKey {
                        key: format!("provenance={value}"),
                    }
                })?);
            }
            other => {
                return Err(RegistryAdmissionError::UnknownKey {
                    key: other.to_owned(),
                });
            }
        }
    }

    let missing = |field: &str| RegistryAdmissionError::MissingField {
        field: field.to_owned(),
    };
    let binding = AdmissionBinding {
        path_needle: path_needle.ok_or_else(|| missing("path_needle"))?,
        level: level.ok_or_else(|| missing("level"))?,
        number: number.ok_or_else(|| missing("number"))?,
        key_path,
        cc: cc.ok_or_else(|| missing("cc"))?,
        provenance: provenance.ok_or_else(|| missing("provenance"))?,
    };
    Ok((binding, line[close + 1..].trim()))
}

fn split_field(segment: &str) -> Option<(&str, &str)> {
    let colon = segment.find(':')?;
    let key = segment[..colon].trim();
    if key.is_empty() {
        return None;
    }
    Some((key, segment[colon + 1..].trim()))
}

/// Strip surrounding double quotes from a scalar value.
fn unquote(value: &str) -> String {
    let value = value.trim();
    if value.len() >= 2 && value.starts_with('"') && value.ends_with('"') {
        value[1..value.len() - 1].to_owned()
    } else {
        value.to_owned()
    }
}

fn parse_authoritative(value: &str) -> Result<bool, RegistryAdmissionError> {
    match value {
        "true" => Ok(true),
        "false" => Ok(false),
        other => Err(RegistryAdmissionError::UnknownKey {
            key: format!("authoritative={other}"),
        }),
    }
}
