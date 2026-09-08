//! Double-coded semantic annotation contract for the proposed C5 contour.
//!
//! Annotation is evidence bookkeeping, not legal authority.  In particular,
//! validation does not mint a human acceptance verdict; that event belongs to
//! the external corpus-control process.

use crate::document_context::{BlockId, TextSpan};
use crate::semantic_scope::{CandidateSlot, SemanticClaimKind};
use std::collections::{BTreeMap, BTreeSet};

pub const SEMANTIC_ANNOTATION_SCHEMA_VERSION: &str = "law-nexus-semantic-annotation/v1";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnnotationClaim {
    kind: String,
    block: BlockId,
    span: TextSpan,
    label: String,
}

impl AnnotationClaim {
    pub fn new(
        kind: SemanticClaimKind,
        block: BlockId,
        span: TextSpan,
        label: impl Into<String>,
    ) -> Self {
        Self {
            kind: kind_name(kind).to_owned(),
            block,
            span,
            label: label.into(),
        }
    }

    pub fn with_kind_name(
        kind: impl Into<String>,
        block: BlockId,
        span: TextSpan,
        label: impl Into<String>,
    ) -> Self {
        Self {
            kind: kind.into(),
            block,
            span,
            label: label.into(),
        }
    }

    pub fn kind_name(&self) -> &str {
        &self.kind
    }
    pub const fn block(&self) -> BlockId {
        self.block
    }
    pub const fn span(&self) -> TextSpan {
        self.span
    }
    pub fn label(&self) -> &str {
        &self.label
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateSlotVerdict {
    candidate_ref: String,
    slot: String,
    label: String,
}

impl CandidateSlotVerdict {
    pub fn new(
        candidate_ref: impl Into<String>,
        slot: CandidateSlot,
        label: impl Into<String>,
    ) -> Self {
        Self {
            candidate_ref: candidate_ref.into(),
            slot: slot_name(slot).to_owned(),
            label: label.into(),
        }
    }

    pub fn with_slot_name(
        candidate_ref: impl Into<String>,
        slot: impl Into<String>,
        label: impl Into<String>,
    ) -> Self {
        Self {
            candidate_ref: candidate_ref.into(),
            slot: slot.into(),
            label: label.into(),
        }
    }

    pub fn candidate_ref(&self) -> &str {
        &self.candidate_ref
    }
    pub fn slot_name(&self) -> &str {
        &self.slot
    }
    pub fn label(&self) -> &str {
        &self.label
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnnotationRecord {
    schema_version: String,
    document_version: String,
    coder_id: String,
    claims: Vec<AnnotationClaim>,
    candidate_slot_verdicts: Vec<CandidateSlotVerdict>,
}

impl AnnotationRecord {
    pub fn new(
        document_version: impl Into<String>,
        coder_id: impl Into<String>,
        claims: Vec<AnnotationClaim>,
        candidate_slot_verdicts: Vec<CandidateSlotVerdict>,
    ) -> Self {
        Self {
            schema_version: SEMANTIC_ANNOTATION_SCHEMA_VERSION.to_owned(),
            document_version: document_version.into(),
            coder_id: coder_id.into(),
            claims,
            candidate_slot_verdicts,
        }
    }

    pub fn with_schema_version(mut self, schema_version: impl Into<String>) -> Self {
        self.schema_version = schema_version.into();
        self
    }
    pub fn schema_version(&self) -> &str {
        &self.schema_version
    }
    pub fn document_version(&self) -> &str {
        &self.document_version
    }
    pub fn coder_id(&self) -> &str {
        &self.coder_id
    }
    pub fn claims(&self) -> &[AnnotationClaim] {
        &self.claims
    }
    pub fn candidate_slot_verdicts(&self) -> &[CandidateSlotVerdict] {
        &self.candidate_slot_verdicts
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AnnotationValidationError {
    SchemaVersionMismatch,
    EmptyDocumentVersion,
    EmptyCoderId,
    DuplicateCoderId,
    UnknownClaimKind,
    EmptyClaimSpan,
    EmptyClaimLabel,
    EmptyCandidateReference,
    UnknownCandidateSlot,
    EmptyVerdictLabel,
    DuplicateClaimAnchor,
}

fn kind_name(kind: SemanticClaimKind) -> &'static str {
    match kind {
        SemanticClaimKind::Actor => "Actor",
        SemanticClaimKind::Action => "Action",
        SemanticClaimKind::Object => "Object",
        SemanticClaimKind::Polarity => "Polarity",
        SemanticClaimKind::Condition => "Condition",
        SemanticClaimKind::Exception => "Exception",
        SemanticClaimKind::TemporalQualifier => "TemporalQualifier",
    }
}

fn slot_name(slot: CandidateSlot) -> &'static str {
    match slot {
        CandidateSlot::Actor => "Actor",
        CandidateSlot::Action => "Action",
        CandidateSlot::Object => "Object",
        CandidateSlot::Polarity => "Polarity",
    }
}

fn known_kind(value: &str) -> bool {
    [
        "Actor",
        "Action",
        "Object",
        "Polarity",
        "Condition",
        "Exception",
        "TemporalQualifier",
    ]
    .contains(&value)
}
fn known_slot(value: &str) -> bool {
    ["Actor", "Action", "Object", "Polarity"].contains(&value)
}

pub fn validate(record: &AnnotationRecord) -> Result<(), AnnotationValidationError> {
    if record.schema_version != SEMANTIC_ANNOTATION_SCHEMA_VERSION {
        return Err(AnnotationValidationError::SchemaVersionMismatch);
    }
    if record.document_version.trim().is_empty() {
        return Err(AnnotationValidationError::EmptyDocumentVersion);
    }
    if record.coder_id.trim().is_empty() {
        return Err(AnnotationValidationError::EmptyCoderId);
    }
    let mut anchors = BTreeSet::new();
    for claim in &record.claims {
        if !known_kind(&claim.kind) {
            return Err(AnnotationValidationError::UnknownClaimKind);
        }
        if claim.span.start() >= claim.span.end() {
            return Err(AnnotationValidationError::EmptyClaimSpan);
        }
        if claim.label.trim().is_empty() {
            return Err(AnnotationValidationError::EmptyClaimLabel);
        }
        if !anchors.insert((
            claim.kind.clone(),
            claim.block,
            claim.span,
            claim.label.clone(),
        )) {
            return Err(AnnotationValidationError::DuplicateClaimAnchor);
        }
    }
    for verdict in &record.candidate_slot_verdicts {
        if verdict.candidate_ref.trim().is_empty() {
            return Err(AnnotationValidationError::EmptyCandidateReference);
        }
        if !known_slot(&verdict.slot) {
            return Err(AnnotationValidationError::UnknownCandidateSlot);
        }
        if verdict.label.trim().is_empty() {
            return Err(AnnotationValidationError::EmptyVerdictLabel);
        }
    }
    Ok(())
}

pub fn validate_pair(
    first: &AnnotationRecord,
    second: &AnnotationRecord,
) -> Result<(), AnnotationValidationError> {
    validate(first)?;
    validate(second)?;
    if first.coder_id == second.coder_id {
        return Err(AnnotationValidationError::DuplicateCoderId);
    }
    if first.document_version != second.document_version {
        return Err(AnnotationValidationError::EmptyDocumentVersion);
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct KindAgreement {
    total: usize,
    agreed: usize,
    disagreements: usize,
}
impl KindAgreement {
    pub const fn total(&self) -> usize {
        self.total
    }
    pub const fn agreed(&self) -> usize {
        self.agreed
    }
    pub const fn disagreements(&self) -> usize {
        self.disagreements
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementSummary {
    by_kind: BTreeMap<String, KindAgreement>,
}
impl AgreementSummary {
    pub fn by_kind(&self) -> &BTreeMap<String, KindAgreement> {
        &self.by_kind
    }
    pub fn kind(&self, kind: SemanticClaimKind) -> Option<&KindAgreement> {
        self.by_kind.get(kind_name(kind))
    }
}

pub fn agreement(
    first: &AnnotationRecord,
    second: &AnnotationRecord,
) -> Result<AgreementSummary, AnnotationValidationError> {
    validate_pair(first, second)?;
    let mut left = BTreeMap::<(String, BlockId, TextSpan), String>::new();
    let mut right = BTreeMap::<(String, BlockId, TextSpan), String>::new();
    for claim in &first.claims {
        left.insert(
            (claim.kind.clone(), claim.block, claim.span),
            claim.label.clone(),
        );
    }
    for claim in &second.claims {
        right.insert(
            (claim.kind.clone(), claim.block, claim.span),
            claim.label.clone(),
        );
    }
    let mut all = BTreeSet::new();
    all.extend(left.keys().cloned());
    all.extend(right.keys().cloned());
    let mut by_kind = BTreeMap::<String, KindAgreement>::new();
    for (kind, _, _) in &all {
        let entry = by_kind.entry(kind.clone()).or_default();
        entry.total += 1;
    }
    for key in all_keys(&left, &right) {
        let kind = key.0.clone();
        let entry = by_kind.get_mut(&kind).expect("kind was seeded");
        if left.get(&key) == right.get(&key) {
            entry.agreed += 1;
        }
    }
    for entry in by_kind.values_mut() {
        entry.disagreements = entry.total - entry.agreed;
    }
    Ok(AgreementSummary { by_kind })
}

fn all_keys(
    left: &BTreeMap<(String, BlockId, TextSpan), String>,
    right: &BTreeMap<(String, BlockId, TextSpan), String>,
) -> BTreeSet<(String, BlockId, TextSpan)> {
    let mut keys = BTreeSet::new();
    keys.extend(left.keys().cloned());
    keys.extend(right.keys().cloned());
    keys
}

fn json_string(value: &str) -> String {
    let mut out = String::from("\"");
    for ch in value.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn render_json(record: &AnnotationRecord) -> String {
    let mut claims = record.claims.clone();
    claims.sort_by(|a, b| {
        (&a.kind, a.block, a.span, &a.label).cmp(&(&b.kind, b.block, b.span, &b.label))
    });
    let mut verdicts = record.candidate_slot_verdicts.clone();
    verdicts.sort_by(|a, b| {
        (&a.candidate_ref, &a.slot, &a.label).cmp(&(&b.candidate_ref, &b.slot, &b.label))
    });
    let claim_json = claims
        .iter()
        .map(|c| {
            format!(
                "{{\"kind\":{},\"block\":{},\"span\":{{\"start\":{},\"end\":{}}},\"label\":{}}}",
                json_string(&c.kind),
                c.block.get(),
                c.span.start(),
                c.span.end(),
                json_string(&c.label)
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    let verdict_json = verdicts
        .iter()
        .map(|v| {
            format!(
                "{{\"candidate_ref\":{},\"slot\":{},\"label\":{}}}",
                json_string(&v.candidate_ref),
                json_string(&v.slot),
                json_string(&v.label)
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    format!("{{\"schema_version\":{},\"document_version\":{},\"coder_id\":{},\"claims\":[{}],\"candidate_slot_verdicts\":[{}]}}", json_string(&record.schema_version), json_string(&record.document_version), json_string(&record.coder_id), claim_json, verdict_json)
}
