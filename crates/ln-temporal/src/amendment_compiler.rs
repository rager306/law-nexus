//! Deterministic amendment compiler fold and `EditionOracle` verifier
//! (ADR-0032 D1 & D4; `MC-PIPE` steps 3-7).
//!
//! Lifecycle: `[proposed]`. Proves causal forward compilation from a base
//! component map plus bounded `MicroOperation` events (`ReplaceText`,
//! `InsertText`, `DeleteText`, `Attach`, `Repeal`) into a deterministic
//! snapshot with length-prefixed SHA-256 `root_hash` (`INV-01`), permutation
//! invariance for independent ops (`INV-02`), same-day cross-act contention
//! detection (`INV-03` `OrderingConflict`), future-effect exclusion (`INV-04`),
//! bitemporal `known_as_of` exclusion (`INV-05`), immutable source mentions
//! (`INV-06`), four-axis `MC-REPEAL`, `MC-SEED` no-auto-InForce, and typed
//! `MC-RES` non-successes (`INV-10`).

use std::collections::{BTreeMap, BTreeSet};

use sha2::{Digest, Sha256};

use crate::domain::NormativeState;

/// D098 non-claims embedded in every compiled snapshot and oracle report.
pub const COMPILER_FOLD_NON_CLAIMS: &[&str] = &[
    "Lifecycle [proposed] (ADR-0032 D4 vertical proving spike); not full corpus or legal validation",
    "EditionOracle is an external verification checksum only; discrepancies never rewrite causal history",
    "Text presence never implies ForceStatus InForce (MC-SEED); Attach seeds NotYetInForce",
    "Repeal preserves four orthogonal axes (MC-REPEAL) and keeps the last text citable as HistoricalOnly",
];

/// Closed 5-operation initial `MC-OPS` subset (ADR-0032 D3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MicroOperationKind {
    ReplaceText,
    InsertText,
    DeleteText,
    Attach,
    Repeal,
}

/// Anchor placement mode for text micro-operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TextAnchorMode {
    WholeComponent,
    ExactAnchor,
    AfterAnchor,
    BeforeAnchor,
    EndOfComponent,
}

/// Admission status of the ledger assertion carrying a micro-operation (E.2.7).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AssertionFoldStatus {
    Proposed,
    Validated,
    AuthoritativeInternal,
    Rejected,
    Superseded,
}

impl AssertionFoldStatus {
    pub const fn enters_fold(self) -> bool {
        matches!(self, Self::Validated | Self::AuthoritativeInternal)
    }
}

/// Closed 9-value typed apply result (`MC-RES` / `INV-10`); never `None`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ApplyOutcome {
    Applied,
    TargetNotFound,
    AmbiguousTarget,
    PreconditionMismatch,
    BaseVersionMismatch,
    OrderingConflict,
    UnknownEffect,
    UnsupportedOperation,
    IncompleteSource,
}

impl ApplyOutcome {
    const fn stable_tag(self) -> u8 {
        match self {
            Self::Applied => 1,
            Self::TargetNotFound => 2,
            Self::AmbiguousTarget => 3,
            Self::PreconditionMismatch => 4,
            Self::BaseVersionMismatch => 5,
            Self::OrderingConflict => 6,
            Self::UnknownEffect => 7,
            Self::UnsupportedOperation => 8,
            Self::IncompleteSource => 9,
        }
    }
}

/// Editorial presence axis (`MC-SEPARATION` / `MC-REPEAL`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EditorialPresence {
    Present,
    Tombstone,
    Absent,
}

impl EditorialPresence {
    const fn stable_tag(self) -> u8 {
        match self {
            Self::Present => 1,
            Self::Tombstone => 2,
            Self::Absent => 3,
        }
    }
}

/// Text availability axis (`MC-REPEAL`: repealed text remains citable as `HistoricalOnly`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TextAvailability {
    Current,
    HistoricalOnly,
}

impl TextAvailability {
    const fn stable_tag(self) -> u8 {
        match self {
            Self::Current => 1,
            Self::HistoricalOnly => 2,
        }
    }
}

fn force_status_tag(status: NormativeState) -> u8 {
    match status {
        NormativeState::InForce => 1,
        NormativeState::NotYetInForce => 2,
        NormativeState::Suspended => 3,
        NormativeState::Repealed => 4,
        NormativeState::Expired => 5,
        NormativeState::Invalidated => 6,
        NormativeState::Unknown => 7,
    }
}

/// One seed component from the earliest available edition baseline.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BaseComponent {
    pub locator: String,
    pub text: String,
    pub force_status: NormativeState,
    pub preserved_mentions: Vec<String>,
}

/// One typed micro-operation input to [`compile_at`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompilerMicroOperation {
    pub op_id: String,
    pub amending_act_id: String,
    pub target_locator: String,
    pub kind: MicroOperationKind,
    pub anchor_mode: TextAnchorMode,
    pub loc_value: Option<String>,
    pub value: Option<String>,
    pub legal_effective_day: i64,
    pub recorded_day: i64,
    pub assertion_status: AssertionFoldStatus,
}

/// Compiled state of one normative component at `(legal_as_of, known_as_of)`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompiledComponent {
    pub locator: String,
    pub text: String,
    pub force_status: NormativeState,
    pub structural_membership: bool,
    pub editorial_presence: EditorialPresence,
    pub text_availability: TextAvailability,
    pub provenance_ops: Vec<String>,
    /// Frozen source mentions carried through unchanged (`INV-06`).
    pub preserved_mentions: Vec<String>,
}

/// Per-operation audit entry recorded in deterministic replay order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OperationAuditEntry {
    pub op_id: String,
    pub amending_act_id: String,
    pub target_locator: String,
    pub outcome: ApplyOutcome,
    pub detail: String,
}

/// Deterministic compiled projection produced by [`compile_at`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompiledSnapshot {
    pub legal_as_of: i64,
    pub known_as_of: i64,
    pub components: BTreeMap<String, CompiledComponent>,
    pub audit: Vec<OperationAuditEntry>,
    pub excluded_future_count: usize,
    pub excluded_unrecorded_count: usize,
    pub excluded_unadmitted_count: usize,
    pub root_hash: String,
    pub non_claims: &'static [&'static str],
}

/// Normalize whitespace and NBSP for explicit `INV-09c` oracle comparison.
pub fn normalize_for_oracle(text: &str) -> String {
    text.replace('\u{00a0}', " ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

fn hash_bytes(hasher: &mut Sha256, bytes: &[u8]) {
    hasher.update((bytes.len() as u64).to_be_bytes());
    hasher.update(bytes);
}

fn hash_str(hasher: &mut Sha256, s: &str) {
    hash_bytes(hasher, s.as_bytes());
}

fn hash_str_slice(hasher: &mut Sha256, items: &[String]) {
    hasher.update((items.len() as u64).to_be_bytes());
    for item in items {
        hash_str(hasher, item);
    }
}

/// Collision-free length-prefixed SHA-256 snapshot digest (`INV-01`/`INV-06`/`INV-11`).
///
/// Commits to `(legal_as_of, known_as_of)`, every component's fields including
/// `preserved_mentions` (`INV-06`), exclusion counters, and audit outcomes using
/// explicit stable byte tags instead of `Debug` formatting.
fn compute_root_hash(
    legal_as_of: i64,
    known_as_of: i64,
    components: &BTreeMap<String, CompiledComponent>,
    audit: &[OperationAuditEntry],
    excluded_future_count: usize,
    excluded_unrecorded_count: usize,
    excluded_unadmitted_count: usize,
) -> String {
    let mut hasher = Sha256::new();
    hash_bytes(&mut hasher, b"law-nexus:compiled-snapshot/v2");
    hasher.update(legal_as_of.to_be_bytes());
    hasher.update(known_as_of.to_be_bytes());
    hasher.update((excluded_future_count as u64).to_be_bytes());
    hasher.update((excluded_unrecorded_count as u64).to_be_bytes());
    hasher.update((excluded_unadmitted_count as u64).to_be_bytes());

    hasher.update((components.len() as u64).to_be_bytes());
    for (locator, comp) in components {
        hash_str(&mut hasher, locator);
        hash_str(&mut hasher, &comp.text);
        hasher.update([
            force_status_tag(comp.force_status),
            u8::from(comp.structural_membership),
            comp.editorial_presence.stable_tag(),
            comp.text_availability.stable_tag(),
        ]);
        hash_str_slice(&mut hasher, &comp.provenance_ops);
        hash_str_slice(&mut hasher, &comp.preserved_mentions);
    }

    hasher.update((audit.len() as u64).to_be_bytes());
    for entry in audit {
        hash_str(&mut hasher, &entry.op_id);
        hash_str(&mut hasher, &entry.amending_act_id);
        hash_str(&mut hasher, &entry.target_locator);
        hasher.update([entry.outcome.stable_tag()]);
    }

    let digest = hasher.finalize();
    let mut hex = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        let _ = write!(hex, "{byte:02x}");
    }
    hex
}

fn find_unique_match(haystack: &str, needle: &str) -> Result<usize, ApplyOutcome> {
    if needle.is_empty() {
        return Err(ApplyOutcome::IncompleteSource);
    }
    let mut iter = haystack.match_indices(needle);
    let Some((first, _)) = iter.next() else {
        return Err(ApplyOutcome::PreconditionMismatch);
    };
    if iter.next().is_some() {
        return Err(ApplyOutcome::AmbiguousTarget);
    }
    Ok(first)
}

/// Apply one admitted operation deterministically onto `components`.
fn apply_one_operation(
    components: &mut BTreeMap<String, CompiledComponent>,
    op: &CompilerMicroOperation,
) -> (ApplyOutcome, String) {
    if op.target_locator.trim().is_empty() {
        return (
            ApplyOutcome::IncompleteSource,
            "target_locator must be non-empty".to_owned(),
        );
    }

    match op.kind {
        MicroOperationKind::Attach => {
            let Some(new_text) = op.value.as_deref() else {
                return (
                    ApplyOutcome::IncompleteSource,
                    "Attach missing quoted payload".to_owned(),
                );
            };
            // Never overwrite an active component OR a repealed tombstone (`MC-REPEAL`/`INV-06`).
            if components.contains_key(&op.target_locator) {
                return (
                    ApplyOutcome::PreconditionMismatch,
                    "target locator already exists (active or tombstone)".to_owned(),
                );
            }
            // MC-SEED: newly attached text NEVER auto-seeds InForce.
            components.insert(
                op.target_locator.clone(),
                CompiledComponent {
                    locator: op.target_locator.clone(),
                    text: new_text.to_owned(),
                    force_status: NormativeState::NotYetInForce,
                    structural_membership: true,
                    editorial_presence: EditorialPresence::Present,
                    text_availability: TextAvailability::Current,
                    provenance_ops: vec![op.op_id.clone()],
                    preserved_mentions: Vec::new(),
                },
            );
            (ApplyOutcome::Applied, "attached new component".to_owned())
        }
        MicroOperationKind::Repeal => {
            let Some(comp) = components.get_mut(&op.target_locator) else {
                return (
                    ApplyOutcome::TargetNotFound,
                    "target component not found".to_owned(),
                );
            };
            if comp.force_status == NormativeState::Repealed && !comp.structural_membership {
                return (
                    ApplyOutcome::PreconditionMismatch,
                    "component already repealed".to_owned(),
                );
            }
            // MC-REPEAL: four orthogonal axes, last text stays citable as HistoricalOnly.
            comp.force_status = NormativeState::Repealed;
            comp.structural_membership = false;
            comp.editorial_presence = EditorialPresence::Tombstone;
            comp.text_availability = TextAvailability::HistoricalOnly;
            comp.provenance_ops.push(op.op_id.clone());
            (
                ApplyOutcome::Applied,
                "repealed across 4 axes (Tombstone/HistoricalOnly)".to_owned(),
            )
        }
        MicroOperationKind::ReplaceText => {
            let Some(new_val) = op.value.as_deref() else {
                return (
                    ApplyOutcome::IncompleteSource,
                    "ReplaceText missing replacement value".to_owned(),
                );
            };
            let Some(comp) = components.get_mut(&op.target_locator) else {
                return (
                    ApplyOutcome::TargetNotFound,
                    "target component not found".to_owned(),
                );
            };
            if !comp.structural_membership {
                return (
                    ApplyOutcome::PreconditionMismatch,
                    "cannot replace text on non-member/repealed component".to_owned(),
                );
            }
            match op.anchor_mode {
                TextAnchorMode::WholeComponent => {
                    comp.text = new_val.to_owned();
                    comp.provenance_ops.push(op.op_id.clone());
                    (
                        ApplyOutcome::Applied,
                        "replaced whole component text".to_owned(),
                    )
                }
                TextAnchorMode::ExactAnchor => {
                    let Some(needle) = op.loc_value.as_deref() else {
                        return (
                            ApplyOutcome::IncompleteSource,
                            "ExactAnchor ReplaceText missing loc_value".to_owned(),
                        );
                    };
                    match find_unique_match(&comp.text, needle) {
                        Ok(pos) => {
                            let mut updated =
                                String::with_capacity(comp.text.len() + new_val.len());
                            updated.push_str(&comp.text[..pos]);
                            updated.push_str(new_val);
                            updated.push_str(&comp.text[pos + needle.len()..]);
                            comp.text = updated;
                            comp.provenance_ops.push(op.op_id.clone());
                            (ApplyOutcome::Applied, "replaced unique anchor".to_owned())
                        }
                        Err(err) => (err, format!("anchor '{needle}' failed: {err:?}")),
                    }
                }
                _ => (
                    ApplyOutcome::UnsupportedOperation,
                    format!("unsupported ReplaceText anchor mode {:?}", op.anchor_mode),
                ),
            }
        }
        MicroOperationKind::InsertText => {
            let Some(insert_val) = op.value.as_deref() else {
                return (
                    ApplyOutcome::IncompleteSource,
                    "InsertText missing value".to_owned(),
                );
            };
            let Some(comp) = components.get_mut(&op.target_locator) else {
                return (
                    ApplyOutcome::TargetNotFound,
                    "target component not found".to_owned(),
                );
            };
            if !comp.structural_membership {
                return (
                    ApplyOutcome::PreconditionMismatch,
                    "cannot insert text into non-member/repealed component".to_owned(),
                );
            }
            match op.anchor_mode {
                TextAnchorMode::AfterAnchor => {
                    let Some(needle) = op.loc_value.as_deref() else {
                        return (
                            ApplyOutcome::IncompleteSource,
                            "AfterAnchor InsertText missing loc_value".to_owned(),
                        );
                    };
                    match find_unique_match(&comp.text, needle) {
                        Ok(pos) => {
                            let split = pos + needle.len();
                            let needs_space = !comp.text[..split].ends_with(char::is_whitespace)
                                && !insert_val.starts_with(|c: char| {
                                    c.is_whitespace() || matches!(c, ',' | '.' | ';' | ':' | ')')
                                });
                            let mut updated =
                                String::with_capacity(comp.text.len() + insert_val.len() + 1);
                            updated.push_str(&comp.text[..split]);
                            if needs_space {
                                updated.push(' ');
                            }
                            updated.push_str(insert_val);
                            updated.push_str(&comp.text[split..]);
                            comp.text = updated;
                            comp.provenance_ops.push(op.op_id.clone());
                            (
                                ApplyOutcome::Applied,
                                "inserted after unique anchor".to_owned(),
                            )
                        }
                        Err(err) => (err, format!("anchor '{needle}' failed: {err:?}")),
                    }
                }
                TextAnchorMode::BeforeAnchor => {
                    let Some(needle) = op.loc_value.as_deref() else {
                        return (
                            ApplyOutcome::IncompleteSource,
                            "BeforeAnchor InsertText missing loc_value".to_owned(),
                        );
                    };
                    match find_unique_match(&comp.text, needle) {
                        Ok(pos) => {
                            let needs_space = !insert_val.ends_with(char::is_whitespace)
                                && !comp.text[pos..].starts_with(char::is_whitespace);
                            let mut updated =
                                String::with_capacity(comp.text.len() + insert_val.len() + 1);
                            updated.push_str(&comp.text[..pos]);
                            updated.push_str(insert_val);
                            if needs_space {
                                updated.push(' ');
                            }
                            updated.push_str(&comp.text[pos..]);
                            comp.text = updated;
                            comp.provenance_ops.push(op.op_id.clone());
                            (
                                ApplyOutcome::Applied,
                                "inserted before unique anchor".to_owned(),
                            )
                        }
                        Err(err) => (err, format!("anchor '{needle}' failed: {err:?}")),
                    }
                }
                TextAnchorMode::EndOfComponent => {
                    let trimmed = comp.text.trim_end();
                    let (base, trailing_punct) = if let Some(b) = trimmed.strip_suffix(';') {
                        (b, Some(';'))
                    } else if let Some(b) = trimmed.strip_suffix('.') {
                        (b, Some('.'))
                    } else {
                        (trimmed, None)
                    };
                    let mut updated = String::with_capacity(base.len() + insert_val.len() + 2);
                    updated.push_str(base);
                    if !base.is_empty()
                        && !base.ends_with(char::is_whitespace)
                        && !insert_val.starts_with(|c: char| {
                            c.is_whitespace() || matches!(c, ',' | '.' | ';' | ':')
                        })
                    {
                        updated.push(' ');
                    }
                    updated.push_str(insert_val);
                    let insert_has_terminator = insert_val.ends_with(['.', ';']);
                    if let Some(p) = trailing_punct
                        && !insert_has_terminator
                    {
                        updated.push(p);
                    }
                    comp.text = updated;
                    comp.provenance_ops.push(op.op_id.clone());
                    (
                        ApplyOutcome::Applied,
                        "appended to component end".to_owned(),
                    )
                }
                _ => (
                    ApplyOutcome::UnsupportedOperation,
                    format!("unsupported InsertText anchor mode {:?}", op.anchor_mode),
                ),
            }
        }
        MicroOperationKind::DeleteText => {
            if op.anchor_mode != TextAnchorMode::ExactAnchor {
                return (
                    ApplyOutcome::UnsupportedOperation,
                    format!("unsupported DeleteText anchor mode {:?}", op.anchor_mode),
                );
            }
            let Some(needle) = op.loc_value.as_deref() else {
                return (
                    ApplyOutcome::IncompleteSource,
                    "DeleteText missing loc_value".to_owned(),
                );
            };
            let Some(comp) = components.get_mut(&op.target_locator) else {
                return (
                    ApplyOutcome::TargetNotFound,
                    "target component not found".to_owned(),
                );
            };
            if !comp.structural_membership {
                return (
                    ApplyOutcome::PreconditionMismatch,
                    "cannot delete text on non-member/repealed component".to_owned(),
                );
            }
            match find_unique_match(&comp.text, needle) {
                Ok(pos) => {
                    let before = &comp.text[..pos];
                    let after = &comp.text[pos + needle.len()..];
                    // Collapse only a local double ASCII space created at the splice
                    // point; never rewrite untouched NBSP or newlines elsewhere in `comp.text`.
                    let after_trimmed = if before.ends_with(' ') && after.starts_with(' ') {
                        &after[1..]
                    } else {
                        after
                    };
                    let mut updated = String::with_capacity(before.len() + after_trimmed.len());
                    updated.push_str(before);
                    updated.push_str(after_trimmed);
                    comp.text = updated;
                    comp.provenance_ops.push(op.op_id.clone());
                    (ApplyOutcome::Applied, "deleted unique anchor".to_owned())
                }
                Err(err) => (err, format!("anchor '{needle}' failed: {err:?}")),
            }
        }
    }
}

fn anchored_edit_span<'a>(
    text: &str,
    op: &'a CompilerMicroOperation,
) -> Option<(usize, usize, Option<&'a str>)> {
    let needle = op.loc_value.as_deref()?;
    let valid_mode = matches!(
        (op.kind, op.anchor_mode),
        (MicroOperationKind::ReplaceText, TextAnchorMode::ExactAnchor)
            | (
                MicroOperationKind::InsertText,
                TextAnchorMode::AfterAnchor | TextAnchorMode::BeforeAnchor
            )
            | (MicroOperationKind::DeleteText, TextAnchorMode::ExactAnchor)
    );
    if !valid_mode {
        return None;
    }
    if matches!(
        op.kind,
        MicroOperationKind::ReplaceText | MicroOperationKind::InsertText
    ) && op.value.is_none()
    {
        return None;
    }
    let start = find_unique_match(text, needle).ok()?;
    Some((start, start + needle.len(), op.value.as_deref()))
}

/// Maximum number of operations in a same-day multi-act bucket for which
/// exhaustive op-level permutation verification (`k! <= 24`) is performed.
/// Larger same-day cross-act buckets fail closed with `OrderingConflict`.
const MAX_COMMUTATIVE_BUCKET_OPS: usize = 4;

fn all_permutations_yield_same_text(
    base_comp: &CompiledComponent,
    target_locator: &str,
    bucket: &[&CompilerMicroOperation],
) -> bool {
    let simulate = |ordered: &[&CompilerMicroOperation]| -> Option<String> {
        let mut scratch: BTreeMap<String, CompiledComponent> = BTreeMap::new();
        scratch.insert(target_locator.to_owned(), base_comp.clone());
        for op in ordered {
            let (outcome, _) = apply_one_operation(&mut scratch, op);
            if outcome != ApplyOutcome::Applied {
                return None;
            }
        }
        scratch.remove(target_locator).map(|c| c.text)
    };

    let Some(canonical_text) = simulate(bucket) else {
        return false;
    };

    // Exhaustively check all `n!` op-level permutations (Heap's algorithm;
    // `n <= MAX_COMMUTATIVE_BUCKET_OPS = 4`, so at most 24 simulations) so
    // neither 3+ act cross-boundary anchor synthesis nor intra-act + cross-act
    // interleavings can slip past `INV-03`.
    let n = bucket.len();
    let mut perm: Vec<&CompilerMicroOperation> = bucket.to_vec();
    let mut c = vec![0usize; n];
    let mut i = 0usize;
    while i < n {
        if c[i] < i {
            if i.is_multiple_of(2) {
                perm.swap(0, i);
            } else {
                perm.swap(c[i], i);
            }
            if simulate(&perm).as_deref() != Some(canonical_text.as_str()) {
                return false;
            }
            c[i] += 1;
            i = 0;
        } else {
            c[i] = 0;
            i += 1;
        }
    }
    true
}

/// Prove that a same-day multi-act bucket targeting the same active component
/// consists exclusively of strictly disjoint, non-interfering anchored text
/// edits whose final text is identical under EVERY op-level permutation
/// (`INV-02` & `INV-03` / `MC-DAG`).
///
/// Any `WholeComponent`, `EndOfComponent`, `Attach`, `Repeal`, missing/ambiguous
/// anchor, touching/overlapping byte span, bucket exceeding 4 operations, or
/// permutation-sensitive interaction returns `false` so the caller fails closed
/// with [`ApplyOutcome::OrderingConflict`].
fn is_provably_commutative_same_day_bucket(
    components: &BTreeMap<String, CompiledComponent>,
    target_locator: &str,
    bucket: &[&CompilerMicroOperation],
) -> bool {
    if bucket.len() > MAX_COMMUTATIVE_BUCKET_OPS {
        return false;
    }
    let Some(base_comp) = components.get(target_locator) else {
        return false;
    };
    if !base_comp.structural_membership
        || base_comp.editorial_presence != EditorialPresence::Present
    {
        return false;
    }

    let mut spans: Vec<(usize, usize, &str, Option<&str>)> = Vec::with_capacity(bucket.len());
    for op in bucket {
        let Some((start, end, val)) = anchored_edit_span(&base_comp.text, op) else {
            return false;
        };
        let needle = op.loc_value.as_deref().unwrap_or("");
        spans.push((start, end, needle, val));
    }

    // Require strict byte separation (`prev.end < next.start`) between every
    // pair of matched spans so edits never overlap or share an insertion edge.
    let mut sorted_spans: Vec<(usize, usize)> = spans.iter().map(|&(s, e, _, _)| (s, e)).collect();
    sorted_spans.sort_unstable();
    for pair in sorted_spans.windows(2) {
        if pair[0].1 >= pair[1].0 {
            return false;
        }
    }

    // Fast static reject if any op's replacement/insertion text contains another
    // op's anchor.
    for (i, &(_, _, _, maybe_val)) in spans.iter().enumerate() {
        if let Some(val) = maybe_val {
            for (j, &(_, _, other_needle, _)) in spans.iter().enumerate() {
                if i != j && val.contains(other_needle) {
                    return false;
                }
            }
        }
    }

    all_permutations_yield_same_text(base_comp, target_locator, bucket)
}

/// Deterministically fold `base_components` and `operations` at `(legal_as_of, known_as_of)`.
///
/// Enforces:
/// - `INV-01`: identical inputs yield identical length-prefixed SHA-256 `root_hash`;
/// - `INV-02`: permuting independent operations yields identical snapshot & `root_hash`;
/// - `INV-03`: same-day (`legal_effective_day`) operations targeting the same
///   `target_locator` from distinct `amending_act_id`s are applied only when
///   provably commutative (strictly disjoint anchored text edits with verified
///   order-independent post-text); otherwise every op in the conflicting bucket
///   fails closed with [`ApplyOutcome::OrderingConflict`];
/// - `INV-04`: `legal_effective_day > legal_as_of` excluded;
/// - `INV-05`: `recorded_day > known_as_of` excluded first (before admission check).
pub fn compile_at(
    base_components: &[BaseComponent],
    operations: &[CompilerMicroOperation],
    legal_as_of: i64,
    known_as_of: i64,
) -> CompiledSnapshot {
    let mut components: BTreeMap<String, CompiledComponent> = BTreeMap::new();
    let mut audit: Vec<OperationAuditEntry> = Vec::new();

    for base in base_components {
        if base.locator.trim().is_empty() {
            audit.push(OperationAuditEntry {
                op_id: "base:seed".to_owned(),
                amending_act_id: "base".to_owned(),
                target_locator: base.locator.clone(),
                outcome: ApplyOutcome::IncompleteSource,
                detail: "base component locator must be non-empty".to_owned(),
            });
            continue;
        }
        if components.contains_key(&base.locator) {
            audit.push(OperationAuditEntry {
                op_id: "base:seed".to_owned(),
                amending_act_id: "base".to_owned(),
                target_locator: base.locator.clone(),
                outcome: ApplyOutcome::BaseVersionMismatch,
                detail: "duplicate base component locator ignored fail-closed".to_owned(),
            });
            continue;
        }
        let is_repealed = base.force_status == NormativeState::Repealed;
        components.insert(
            base.locator.clone(),
            CompiledComponent {
                locator: base.locator.clone(),
                text: base.text.clone(),
                force_status: base.force_status,
                structural_membership: !is_repealed,
                editorial_presence: if is_repealed {
                    EditorialPresence::Tombstone
                } else {
                    EditorialPresence::Present
                },
                text_availability: if is_repealed {
                    TextAvailability::HistoricalOnly
                } else {
                    TextAvailability::Current
                },
                provenance_ops: Vec::new(),
                preserved_mentions: base.preserved_mentions.clone(),
            },
        );
    }

    let mut excluded_future_count = 0usize;
    let mut excluded_unrecorded_count = 0usize;
    let mut excluded_unadmitted_count = 0usize;

    let mut eligible: Vec<&CompilerMicroOperation> = Vec::new();
    for op in operations {
        // INV-05 checked first so operations recorded after `known_as_of` are
        // invisible regardless of their later admission status.
        if op.recorded_day > known_as_of {
            excluded_unrecorded_count += 1;
            continue;
        }
        if !op.assertion_status.enters_fold() {
            excluded_unadmitted_count += 1;
            continue;
        }
        if op.legal_effective_day > legal_as_of {
            excluded_future_count += 1;
            continue;
        }
        eligible.push(op);
    }

    eligible.sort_by(|a, b| {
        (
            a.legal_effective_day,
            a.target_locator.as_str(),
            a.amending_act_id.as_str(),
            a.op_id.as_str(),
            a.recorded_day,
        )
            .cmp(&(
                b.legal_effective_day,
                b.target_locator.as_str(),
                b.amending_act_id.as_str(),
                b.op_id.as_str(),
                b.recorded_day,
            ))
    });

    // Detect duplicate op_ids (fail closed so input order never picks a winner).
    let mut op_id_counts: BTreeMap<&str, usize> = BTreeMap::new();
    for op in &eligible {
        *op_id_counts.entry(op.op_id.as_str()).or_insert(0) += 1;
    }

    // Process eligible operations in contiguous `(legal_effective_day, target_locator)`
    // buckets so same-day multi-act commutativity is evaluated against the exact
    // component state accumulated from all strictly earlier effective days.
    let mut idx = 0usize;
    while idx < eligible.len() {
        let day = eligible[idx].legal_effective_day;
        let locator = eligible[idx].target_locator.as_str();
        let mut end = idx + 1;
        while end < eligible.len()
            && eligible[end].legal_effective_day == day
            && eligible[end].target_locator.as_str() == locator
        {
            end += 1;
        }

        let slice = &eligible[idx..end];
        let mut valid_bucket: Vec<&CompilerMicroOperation> = Vec::with_capacity(slice.len());
        let mut acts: BTreeSet<&str> = BTreeSet::new();
        for &op in slice {
            if op_id_counts.get(op.op_id.as_str()).copied().unwrap_or(0) > 1 {
                audit.push(OperationAuditEntry {
                    op_id: op.op_id.clone(),
                    amending_act_id: op.amending_act_id.clone(),
                    target_locator: op.target_locator.clone(),
                    outcome: ApplyOutcome::PreconditionMismatch,
                    detail: "duplicate op_id rejected fail-closed".to_owned(),
                });
            } else {
                if !locator.trim().is_empty() {
                    acts.insert(op.amending_act_id.as_str());
                }
                valid_bucket.push(op);
            }
        }

        let conflicting_same_day = acts.len() > 1
            && !is_provably_commutative_same_day_bucket(&components, locator, &valid_bucket);

        for op in valid_bucket {
            if conflicting_same_day {
                audit.push(OperationAuditEntry {
                    op_id: op.op_id.clone(),
                    amending_act_id: op.amending_act_id.clone(),
                    target_locator: op.target_locator.clone(),
                    outcome: ApplyOutcome::OrderingConflict,
                    detail: "multiple distinct amending acts target the same component on the same legal_effective_day with non-commutative mutations".to_owned(),
                });
                continue;
            }
            let (outcome, detail) = apply_one_operation(&mut components, op);
            audit.push(OperationAuditEntry {
                op_id: op.op_id.clone(),
                amending_act_id: op.amending_act_id.clone(),
                target_locator: op.target_locator.clone(),
                outcome,
                detail,
            });
        }

        idx = end;
    }

    let root_hash = compute_root_hash(
        legal_as_of,
        known_as_of,
        &components,
        &audit,
        excluded_future_count,
        excluded_unrecorded_count,
        excluded_unadmitted_count,
    );
    CompiledSnapshot {
        legal_as_of,
        known_as_of,
        components,
        audit,
        excluded_future_count,
        excluded_unrecorded_count,
        excluded_unadmitted_count,
        root_hash,
        non_claims: COMPILER_FOLD_NON_CLAIMS,
    }
}

/// Kind of mismatch between compiled projection and an `EditionOracle`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiscrepancyKind {
    MissingInCompiled,
    TextMismatch,
    MembershipMismatch,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OracleDiscrepancy {
    pub locator: String,
    pub kind: DiscrepancyKind,
    pub compiled_text: Option<String>,
    pub oracle_text: Option<String>,
}

/// Expected component state in an `EditionOracle` checkpoint (`INV-09c`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OracleComponentExpectation {
    pub locator: String,
    pub expected_presence: EditorialPresence,
    /// Optional expected text: compared when `Some(...)`; omit (`None`) for
    /// `Tombstone`/`Absent` entries where an oracle only records repeal status.
    pub expected_text: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OracleVerificationReport {
    pub checked_count: usize,
    pub matched_count: usize,
    pub drift_count: usize,
    pub discrepancies: Vec<OracleDiscrepancy>,
    pub non_claims: &'static [&'static str],
}

/// Compare a [`CompiledSnapshot`] against scoped [`OracleComponentExpectation`]
/// rows (`INV-09c`). Never mutates the snapshot (`EditionOracle` is an exam, not canon).
pub fn verify_against_edition_oracle(
    compiled: &CompiledSnapshot,
    oracle: &[OracleComponentExpectation],
) -> OracleVerificationReport {
    let mut matched_count = 0usize;
    let mut discrepancies = Vec::new();

    for expected in oracle {
        let Some(actual) = compiled.components.get(&expected.locator) else {
            if expected.expected_presence == EditorialPresence::Absent {
                matched_count += 1;
            } else {
                discrepancies.push(OracleDiscrepancy {
                    locator: expected.locator.clone(),
                    kind: DiscrepancyKind::MissingInCompiled,
                    compiled_text: None,
                    oracle_text: expected.expected_text.clone(),
                });
            }
            continue;
        };

        let presence_matches = match expected.expected_presence {
            EditorialPresence::Present => {
                actual.structural_membership
                    && actual.editorial_presence == EditorialPresence::Present
                    && actual.text_availability == TextAvailability::Current
            }
            EditorialPresence::Tombstone => {
                !actual.structural_membership
                    && actual.force_status == NormativeState::Repealed
                    && actual.editorial_presence == EditorialPresence::Tombstone
                    && actual.text_availability == TextAvailability::HistoricalOnly
            }
            EditorialPresence::Absent => {
                !actual.structural_membership
                    && actual.editorial_presence == EditorialPresence::Absent
            }
        };

        if !presence_matches {
            discrepancies.push(OracleDiscrepancy {
                locator: expected.locator.clone(),
                kind: DiscrepancyKind::MembershipMismatch,
                compiled_text: Some(actual.text.clone()),
                oracle_text: expected.expected_text.clone(),
            });
            continue;
        }

        if let Some(expected_text) = expected.expected_text.as_deref() {
            let norm_actual = normalize_for_oracle(&actual.text);
            let norm_expected = normalize_for_oracle(expected_text);
            if norm_actual == norm_expected {
                matched_count += 1;
            } else {
                discrepancies.push(OracleDiscrepancy {
                    locator: expected.locator.clone(),
                    kind: DiscrepancyKind::TextMismatch,
                    compiled_text: Some(norm_actual),
                    oracle_text: Some(norm_expected),
                });
            }
        } else {
            matched_count += 1;
        }
    }

    OracleVerificationReport {
        checked_count: oracle.len(),
        matched_count,
        drift_count: discrepancies.len(),
        discrepancies,
        non_claims: COMPILER_FOLD_NON_CLAIMS,
    }
}
