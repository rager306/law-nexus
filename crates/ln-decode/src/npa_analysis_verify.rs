//! M214-es3jvw S03 T04: analysis JSONL read-back and the independent verifier.
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8B.4
//! (D663): [`read_back_npa_analysis`] reconstructs all seven families into a
//! typed model, and [`verify_npa_analysis_wire`] re-derives the canonical
//! records from the **pinned parent** (`analyze_document` +
//! `build_context_records`) instead of trusting the artifact's records or
//! seals. A resealed substitution of a source ref, a relation or a context
//! outcome is still detected because the verifier never accepts an artifact
//! seal as a pass.
//!
//! The structural pass and the strict JSON extractor are reused from
//! [`crate::npa_analysis_wire`]; the verifier never calls `build_projection`
//! and never mints a second coordinate system.
//!
//! Failure visibility is a closed [`AnalysisVerifyCode`], never a silent pass.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use crate::analysis_source_mapping::SourceMapping;
use crate::npa_analysis_records::analyze_document;
use crate::npa_analysis_wire::{
    bool_field, inspect_npa_analysis_wire, line_token, opt_hex_field, recompute_analysis_seals,
    render_npa_analysis_with_context, sha256_hex, split_json_array_items, split_lines,
    string_array_field, string_field, u64_field, AnalysisEnvelopeRequest, AnalysisLimits,
    AnalysisScope, AnalysisWireError, AnalysisWireErrorKind, JsonFields, BASIS_COMPLETE,
    BASIS_CONTEXT_INCOMPLETE, BASIS_REFUSED_RECORD, FAMILY_CLASSIFICATION, FAMILY_CONTEXT,
    FAMILY_DIAGNOSTIC, FAMILY_DOCUMENT, FAMILY_FRAGMENT, FAMILY_MEMBER, FAMILY_RELATION, MODEL,
    PROFILE,
};
use crate::npa_context_records::{build_context_records, KIND_RESULT, KIND_RUN};
use crate::reader_contract::{FragmentRef, ReaderFragmentSpan, ReaderRecordIndex};
use crate::reader_projection::ReaderProjection;

// ------------------------------------------------------------- refusals #

/// Closed verifier finding vocabulary (§8B.4). Every code names one concrete
/// invariant; it never carries a legal claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum AnalysisVerifyCode {
    /// Missing/misordered manifest/policies/footer, CR, empty line, unknown
    /// kind/family.
    EnvelopeStructural,
    /// Footer seals differ from their recomputation (non-resealed tamper).
    SealMismatch,
    /// A manifest or `document` record identity field differs from the pinned
    /// parent; a resealed substitution is still an identity mismatch (F01).
    ManifestIdentityMismatch,
    /// `fragment.content_sha256` differs from `ReaderRecordIndex`.
    FragmentHashMismatch,
    /// A span does not resolve to its exact substrate slice.
    SpanSliceMismatch,
    /// A source ref differs from the canonical re-derivation.
    SourceRefSubstitution,
    /// A relation `from`/`to` names no readback record.
    RelationRefMissing,
    /// A relation `from`/`to`/`kind` differs from the canonical re-derivation.
    RelationSubstitution,
    /// A classification `member_id` names no readback member.
    MemberRefMissing,
    /// A context status/view/claim/derivation differs from the canonical.
    ContextOutcomeMismatch,
    /// The completion marker is inconsistent with the re-derived records.
    CompletionMismatch,
}

impl AnalysisVerifyCode {
    /// Closed diagnostic token.
    pub const fn as_str(self) -> &'static str {
        match self {
            AnalysisVerifyCode::EnvelopeStructural => "envelope_structural",
            AnalysisVerifyCode::SealMismatch => "seal_mismatch",
            AnalysisVerifyCode::ManifestIdentityMismatch => "manifest_identity_mismatch",
            AnalysisVerifyCode::FragmentHashMismatch => "fragment_hash_mismatch",
            AnalysisVerifyCode::SpanSliceMismatch => "span_slice_mismatch",
            AnalysisVerifyCode::SourceRefSubstitution => "source_ref_substitution",
            AnalysisVerifyCode::RelationRefMissing => "relation_ref_missing",
            AnalysisVerifyCode::RelationSubstitution => "relation_substitution",
            AnalysisVerifyCode::MemberRefMissing => "member_ref_missing",
            AnalysisVerifyCode::ContextOutcomeMismatch => "context_outcome_mismatch",
            AnalysisVerifyCode::CompletionMismatch => "completion_mismatch",
        }
    }
}

impl fmt::Display for AnalysisVerifyCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// One verifier finding: a closed code plus a human-readable detail.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisVerifyFinding {
    code: AnalysisVerifyCode,
    detail: String,
}

impl AnalysisVerifyFinding {
    /// Builds a finding.
    pub fn new(code: AnalysisVerifyCode, detail: impl Into<String>) -> Self {
        AnalysisVerifyFinding {
            code,
            detail: detail.into(),
        }
    }

    /// The closed finding code.
    pub const fn code(&self) -> AnalysisVerifyCode {
        self.code
    }

    /// The human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for AnalysisVerifyFinding {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "npa_analysis_verify {}: {}",
            self.code.as_str(),
            self.detail
        )
    }
}

fn wire_err(detail: impl Into<String>) -> AnalysisWireError {
    AnalysisWireError::new(AnalysisWireErrorKind::UnknownKind, detail)
}

// ---------------------------------------------------------- read-back #

/// A parsed wire source coordinate: a fragment-qualified span or a closed
/// refusal token.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReadbackRef {
    /// A bound fragment-qualified half-open UTF-8 byte range.
    Bound {
        /// The fragment the coordinate indexes.
        fragment: String,
        /// Half-open start byte.
        start: usize,
        /// Half-open end byte.
        end: usize,
    },
    /// A closed refusal token carried in place of a span.
    Refused(String),
}

/// Read-back of the manifest line: pinned parent identity, document-version
/// triple and declared writer limits.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackManifest {
    /// Source sha256 (integrity evidence).
    pub source_sha256: String,
    /// Source byte count.
    pub source_bytes: u64,
    /// Parent schema tag.
    pub parent_schema: String,
    /// Parent `records_seal_hash` (nullable for an unsealed parent).
    pub parent_records_seal_hash: Option<String>,
    /// Parent `manifest_hash` (nullable for an unsealed parent).
    pub parent_manifest_hash: Option<String>,
    /// Document version ref.
    pub document_version_ref: String,
    /// Source revision.
    pub source_revision: String,
    /// Decoder profile.
    pub decoder_profile: String,
    /// Manifest `profile` token (the analysis profile).
    pub profile: String,
    /// Manifest `model` token (the analysis model).
    pub model: String,
    /// Writer limits copied into the manifest.
    pub limits: AnalysisLimits,
}

/// Read-back of the footer line: completion marker, counts and seals.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackFooter {
    /// Closed `completion` token.
    pub completion: String,
    /// Closed `completion_basis` token.
    pub completion_basis: String,
    /// Ordered closed `incomplete_reasons` tokens.
    pub incomplete_reasons: Vec<String>,
    /// Footer counts by key (all keys present on the wire).
    pub counts: BTreeMap<String, u64>,
    /// Footer `records_seal_hash`.
    pub records_seal_hash: Option<String>,
    /// Footer `manifest_hash`.
    pub manifest_hash: Option<String>,
}

/// One fragment record: count/hash-only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackFragment {
    /// Family-local `ref` (the fragment id).
    pub reference: String,
    /// Declared decoded byte length.
    pub byte_length: u64,
    /// Declared sha256 of the decoded bytes.
    pub content_sha256: String,
}

/// One typed member record (`stage = typed`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackTypedMember {
    /// Family-local `ref` (`mt:<index>`).
    pub reference: String,
    /// Producer position.
    pub typed_index: u64,
    /// The member anchor.
    pub span: ReadbackRef,
    /// The winning TYPE head span, when one exists.
    pub type_evidence: Option<ReadbackRef>,
    /// Losing surviving hypotheses' spans.
    pub alternatives: Vec<ReadbackRef>,
    /// True when no TYPE hypothesis survived.
    pub unresolved: bool,
}

/// One linked member record (`stage = linked`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackLinkedMember {
    /// Family-local `ref` (`ml:<member_id>`).
    pub reference: String,
    /// Linked member id.
    pub member_id: u64,
    /// The member's own anchor.
    pub evidence: ReadbackRef,
    /// Every span that backs the member.
    pub provenance: Vec<ReadbackRef>,
}

/// One relation record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackRelation {
    /// Family-local `ref` (`r:<index>`).
    pub reference: String,
    /// Source member id.
    pub from_id: u64,
    /// Target member id.
    pub to_id: u64,
    /// Closed relation kind token.
    pub kind: String,
    /// The relation source anchors.
    pub evidence: Vec<ReadbackRef>,
}

/// One classification record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackClassification {
    /// Family-local `ref` (`c:<member_id>`).
    pub reference: String,
    /// The classified member id.
    pub member_id: u64,
    /// The member's own anchor.
    pub evidence: ReadbackRef,
}

/// One diagnostic record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackDiagnostic {
    /// Family-local `ref` (`d:<index>`).
    pub reference: String,
    /// The diagnostic's own span, when it has one.
    pub span: Option<ReadbackRef>,
}

/// One context line (`kind: result | run`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReadbackContext {
    /// One context result line.
    Result {
        /// Family-local `ref` (`ctx:<n>`).
        reference: String,
        /// Closed status token.
        status: String,
        /// Nullable `view` token.
        view: Option<String>,
        /// Localized result anchors.
        anchors: Vec<ReadbackRef>,
        /// Localized claim anchors.
        claim_anchors: Vec<ReadbackRef>,
        /// Localized derivation anchors.
        derivation_anchors: Vec<ReadbackRef>,
    },
    /// The single aggregate run line.
    Run {
        /// Family-local `ref` (`ctx:run`).
        reference: String,
    },
}

/// One interior record line: family, family-local ref and the raw line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadbackRecord {
    /// Family token.
    pub family: String,
    /// Family-local `ref`.
    pub reference: String,
    /// The exact rendered line.
    pub raw: String,
}

/// The typed read-back of one rendered analysis envelope (§8B.4).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisReadback {
    /// Manifest fields.
    pub manifest: ReadbackManifest,
    /// Footer fields.
    pub footer: ReadbackFooter,
    /// Fragment records.
    pub fragments: Vec<ReadbackFragment>,
    /// Typed member records.
    pub typed_members: Vec<ReadbackTypedMember>,
    /// Linked member records.
    pub linked_members: Vec<ReadbackLinkedMember>,
    /// Relation records.
    pub relations: Vec<ReadbackRelation>,
    /// Classification records.
    pub classifications: Vec<ReadbackClassification>,
    /// Diagnostic records.
    pub diagnostics: Vec<ReadbackDiagnostic>,
    /// Context records.
    pub contexts: Vec<ReadbackContext>,
    /// Every interior record line (all families).
    pub records: Vec<ReadbackRecord>,
}

impl AnalysisReadback {
    /// The linked-member id set.
    pub fn linked_member_ids(&self) -> BTreeSet<u64> {
        self.linked_members.iter().map(|m| m.member_id).collect()
    }

    /// Every read-back source coordinate with a provenance label.
    pub fn bound_refs(&self) -> Vec<(&'static str, ReadbackRef)> {
        let mut out: Vec<(&'static str, ReadbackRef)> = Vec::new();
        for member in &self.typed_members {
            out.push(("typed.span", member.span.clone()));
            if let Some(evidence) = &member.type_evidence {
                out.push(("typed.type_evidence", evidence.clone()));
            }
            for alternative in &member.alternatives {
                out.push(("typed.alternative", alternative.clone()));
            }
        }
        for member in &self.linked_members {
            out.push(("linked.evidence", member.evidence.clone()));
            for span in &member.provenance {
                out.push(("linked.provenance", span.clone()));
            }
        }
        for relation in &self.relations {
            for span in &relation.evidence {
                out.push(("relation.evidence", span.clone()));
            }
        }
        for record in &self.classifications {
            out.push(("classification.evidence", record.evidence.clone()));
        }
        for diagnostic in &self.diagnostics {
            if let Some(span) = &diagnostic.span {
                out.push(("diagnostic.span", span.clone()));
            }
        }
        for context in &self.contexts {
            if let ReadbackContext::Result {
                anchors,
                claim_anchors,
                derivation_anchors,
                ..
            } = context
            {
                for span in anchors {
                    out.push(("context.anchor", span.clone()));
                }
                for span in claim_anchors {
                    out.push(("context.claim_anchor", span.clone()));
                }
                for span in derivation_anchors {
                    out.push(("context.derivation_anchor", span.clone()));
                }
            }
        }
        out
    }
}

fn parse_readback_ref(raw: &str) -> Result<ReadbackRef, AnalysisWireError> {
    let fields = JsonFields::parse(raw)?;
    if let Some(token) = string_field(&fields, "refusal") {
        return Ok(ReadbackRef::Refused(token));
    }
    let fragment =
        string_field(&fields, "fragment").ok_or_else(|| wire_err("source ref has no fragment"))?;
    let start = u64_field(&fields, "start").ok_or_else(|| wire_err("source ref has no start"))?;
    let end = u64_field(&fields, "end").ok_or_else(|| wire_err("source ref has no end"))?;
    Ok(ReadbackRef::Bound {
        fragment,
        start: start as usize,
        end: end as usize,
    })
}

fn parse_opt_readback_ref(raw: &str) -> Result<Option<ReadbackRef>, AnalysisWireError> {
    if raw.trim() == "null" {
        return Ok(None);
    }
    Ok(Some(parse_readback_ref(raw)?))
}

fn parse_ref_array(raw: &str) -> Result<Vec<ReadbackRef>, AnalysisWireError> {
    split_json_array_items(raw)?
        .into_iter()
        .map(parse_readback_ref)
        .collect()
}

fn parse_typed_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackTypedMember, AnalysisWireError> {
    let typed_index =
        u64_field(fields, "typed_index").ok_or_else(|| wire_err("typed member has no index"))?;
    let span_raw = fields
        .get("span")
        .ok_or_else(|| wire_err("typed member has no span"))?;
    let span = parse_readback_ref(span_raw)?;
    let type_evidence = match fields.get("type_evidence") {
        Some(raw) => parse_opt_readback_ref(raw)?,
        None => None,
    };
    let mut alternatives: Vec<ReadbackRef> = Vec::new();
    if let Some(raw) = fields.get("alternatives") {
        for item in split_json_array_items(raw)? {
            let item_fields = JsonFields::parse(item)?;
            let span_raw = item_fields
                .get("span")
                .ok_or_else(|| wire_err("typed alternative has no span"))?;
            alternatives.push(parse_readback_ref(span_raw)?);
        }
    }
    let unresolved = bool_field(fields, "unresolved")
        .ok_or_else(|| wire_err("typed member has no unresolved"))?;
    Ok(ReadbackTypedMember {
        reference: reference.to_string(),
        typed_index,
        span,
        type_evidence,
        alternatives,
        unresolved,
    })
}

fn parse_linked_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackLinkedMember, AnalysisWireError> {
    let member_id =
        u64_field(fields, "member_id").ok_or_else(|| wire_err("linked member has no id"))?;
    let evidence_raw = fields
        .get("evidence")
        .ok_or_else(|| wire_err("linked member has no evidence"))?;
    let evidence = parse_readback_ref(evidence_raw)?;
    let mut provenance: Vec<ReadbackRef> = Vec::new();
    if let Some(raw) = fields.get("provenance") {
        provenance = parse_ref_array(raw)?;
    }
    Ok(ReadbackLinkedMember {
        reference: reference.to_string(),
        member_id,
        evidence,
        provenance,
    })
}

fn parse_relation_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackRelation, AnalysisWireError> {
    let from_id = u64_field(fields, "from").ok_or_else(|| wire_err("relation has no from"))?;
    let to_id = u64_field(fields, "to").ok_or_else(|| wire_err("relation has no to"))?;
    let kind = string_field(fields, "kind").ok_or_else(|| wire_err("relation has no kind"))?;
    let mut evidence: Vec<ReadbackRef> = Vec::new();
    if let Some(raw) = fields.get("evidence") {
        evidence = parse_ref_array(raw)?;
    }
    Ok(ReadbackRelation {
        reference: reference.to_string(),
        from_id,
        to_id,
        kind,
        evidence,
    })
}

fn parse_classification_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackClassification, AnalysisWireError> {
    let member_id = u64_field(fields, "member_id")
        .ok_or_else(|| wire_err("classification has no member id"))?;
    let evidence_raw = fields
        .get("evidence")
        .ok_or_else(|| wire_err("classification has no evidence"))?;
    let evidence = parse_readback_ref(evidence_raw)?;
    Ok(ReadbackClassification {
        reference: reference.to_string(),
        member_id,
        evidence,
    })
}

fn parse_diagnostic_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackDiagnostic, AnalysisWireError> {
    let span = match fields.get("span") {
        Some(raw) => parse_opt_readback_ref(raw)?,
        None => None,
    };
    Ok(ReadbackDiagnostic {
        reference: reference.to_string(),
        span,
    })
}

fn parse_context_record(
    fields: &JsonFields<'_>,
    reference: &str,
) -> Result<ReadbackContext, AnalysisWireError> {
    let kind = string_field(fields, "kind").ok_or_else(|| wire_err("context has no kind"))?;
    match kind.as_str() {
        KIND_RESULT => {
            let status =
                string_field(fields, "status").ok_or_else(|| wire_err("context has no status"))?;
            let view = string_field(fields, "view");
            let mut anchors: Vec<ReadbackRef> = Vec::new();
            if let Some(raw) = fields.get("anchors") {
                anchors = parse_ref_array(raw)?;
            }
            let mut claim_anchors: Vec<ReadbackRef> = Vec::new();
            if let Some(raw) = fields.get("claims") {
                for item in split_json_array_items(raw)? {
                    let item_fields = JsonFields::parse(item)?;
                    let anchor_raw = item_fields
                        .get("anchor")
                        .ok_or_else(|| wire_err("context claim has no anchor"))?;
                    claim_anchors.push(parse_readback_ref(anchor_raw)?);
                }
            }
            let mut derivation_anchors: Vec<ReadbackRef> = Vec::new();
            if let Some(raw) = fields.get("derivations") {
                for item in split_json_array_items(raw)? {
                    let item_fields = JsonFields::parse(item)?;
                    let anchor_raw = item_fields
                        .get("anchor")
                        .ok_or_else(|| wire_err("context derivation has no anchor"))?;
                    derivation_anchors.push(parse_readback_ref(anchor_raw)?);
                }
            }
            Ok(ReadbackContext::Result {
                reference: reference.to_string(),
                status,
                view,
                anchors,
                claim_anchors,
                derivation_anchors,
            })
        }
        KIND_RUN => Ok(ReadbackContext::Run {
            reference: reference.to_string(),
        }),
        other => Err(wire_err(format!("unknown context kind {other:?}"))),
    }
}

fn parse_manifest(fields: &JsonFields<'_>) -> Result<ReadbackManifest, AnalysisWireError> {
    let source_raw = fields
        .get("source")
        .ok_or_else(|| wire_err("manifest has no source"))?;
    let source = JsonFields::parse(source_raw)?;
    let source_sha256 =
        string_field(&source, "sha256").ok_or_else(|| wire_err("manifest source has no sha256"))?;
    let source_bytes =
        u64_field(&source, "bytes").ok_or_else(|| wire_err("manifest source has no bytes"))?;
    let parent_raw = fields
        .get("parent")
        .ok_or_else(|| wire_err("manifest has no parent"))?;
    let parent = JsonFields::parse(parent_raw)?;
    let parent_schema =
        string_field(&parent, "schema").ok_or_else(|| wire_err("manifest parent has no schema"))?;
    let parent_records_seal_hash = opt_hex_field(&parent, "records_seal_hash")?;
    let parent_manifest_hash = opt_hex_field(&parent, "manifest_hash")?;
    let document_version_ref = string_field(fields, "document_version_ref")
        .ok_or_else(|| wire_err("manifest has no document_version_ref"))?;
    let source_revision = string_field(fields, "source_revision")
        .ok_or_else(|| wire_err("manifest has no source_revision"))?;
    let decoder_profile = string_field(fields, "decoder_profile")
        .ok_or_else(|| wire_err("manifest has no decoder_profile"))?;
    let profile =
        string_field(fields, "profile").ok_or_else(|| wire_err("manifest has no profile"))?;
    let model = string_field(fields, "model").ok_or_else(|| wire_err("manifest has no model"))?;
    let limits_raw = fields
        .get("limits")
        .ok_or_else(|| wire_err("manifest has no limits"))?;
    let limits_fields = JsonFields::parse(limits_raw)?;
    let max_line_bytes = u64_field(&limits_fields, "max_line_bytes")
        .ok_or_else(|| wire_err("manifest limits has no max_line_bytes"))?;
    let max_records = u64_field(&limits_fields, "max_records")
        .ok_or_else(|| wire_err("manifest limits has no max_records"))?;
    Ok(ReadbackManifest {
        source_sha256,
        source_bytes,
        parent_schema,
        parent_records_seal_hash,
        parent_manifest_hash,
        document_version_ref,
        source_revision,
        decoder_profile,
        profile,
        model,
        limits: AnalysisLimits {
            max_line_bytes,
            max_records,
        },
    })
}

fn parse_footer(fields: &JsonFields<'_>) -> Result<ReadbackFooter, AnalysisWireError> {
    let completion =
        string_field(fields, "completion").ok_or_else(|| wire_err("footer has no completion"))?;
    let completion_basis = string_field(fields, "completion_basis")
        .ok_or_else(|| wire_err("footer has no completion_basis"))?;
    let incomplete_reasons = string_array_field(fields, "incomplete_reasons")
        .ok_or_else(|| wire_err("footer has no incomplete_reasons"))?;
    let counts_raw = fields
        .get("counts")
        .ok_or_else(|| wire_err("footer has no counts"))?;
    let counts_fields = JsonFields::parse(counts_raw)?;
    let mut counts: BTreeMap<String, u64> = BTreeMap::new();
    for key in counts_fields.keys() {
        let value = u64_field(&counts_fields, key)
            .ok_or_else(|| wire_err(format!("footer count {key} is not an unsigned integer")))?;
        counts.insert(key.to_string(), value);
    }
    let records_seal_hash = opt_hex_field(fields, "records_seal_hash")?;
    let manifest_hash = opt_hex_field(fields, "manifest_hash")?;
    Ok(ReadbackFooter {
        completion,
        completion_basis,
        incomplete_reasons,
        counts,
        records_seal_hash,
        manifest_hash,
    })
}

/// Reconstructs all seven families of a rendered analysis envelope into a typed
/// model (§8B.4). It fails closed on a structural break and reuses
/// [`inspect_npa_analysis_wire`] for the structural pass. Read-back does **not**
/// verify seals.
pub fn read_back_npa_analysis(text: &str) -> Result<AnalysisReadback, AnalysisWireError> {
    // Structural pass first: shape, limits, completion marker, temporal/corpus
    // stops and unknown kinds are all refused here.
    inspect_npa_analysis_wire(text)?;

    let lines = split_lines(text)?;
    let last = lines.len() - 1;

    let manifest = parse_manifest(&JsonFields::parse(lines[0])?)?;
    let footer = parse_footer(&JsonFields::parse(lines[last])?)?;

    let mut fragments: Vec<ReadbackFragment> = Vec::new();
    let mut typed_members: Vec<ReadbackTypedMember> = Vec::new();
    let mut linked_members: Vec<ReadbackLinkedMember> = Vec::new();
    let mut relations: Vec<ReadbackRelation> = Vec::new();
    let mut classifications: Vec<ReadbackClassification> = Vec::new();
    let mut diagnostics: Vec<ReadbackDiagnostic> = Vec::new();
    let mut contexts: Vec<ReadbackContext> = Vec::new();
    let mut records: Vec<ReadbackRecord> = Vec::new();

    for (index, &line) in lines.iter().enumerate().take(last).skip(2) {
        let fields = JsonFields::parse(line)?;
        let (token, kind) = line_token(&fields)?;
        if kind != crate::analysis_source_mapping::EnvelopeLineKind::Record {
            return Err(wire_err(format!(
                "interior line {index} is not a record ({token})"
            )));
        }
        let family = string_field(&fields, "family")
            .ok_or_else(|| wire_err(format!("record line {index} has no family")))?;
        let reference = string_field(&fields, "ref")
            .ok_or_else(|| wire_err(format!("record line {index} has no ref")))?;
        match family.as_str() {
            FAMILY_FRAGMENT => {
                let byte_length = u64_field(&fields, "byte_length")
                    .ok_or_else(|| wire_err("fragment has no byte_length"))?;
                let content_sha256 = string_field(&fields, "content_sha256")
                    .ok_or_else(|| wire_err("fragment has no content_sha256"))?;
                fragments.push(ReadbackFragment {
                    reference: reference.clone(),
                    byte_length,
                    content_sha256,
                });
            }
            FAMILY_MEMBER => {
                let stage = string_field(&fields, "stage")
                    .ok_or_else(|| wire_err("member record has no stage"))?;
                match stage.as_str() {
                    "typed" => typed_members.push(parse_typed_record(&fields, &reference)?),
                    "linked" => linked_members.push(parse_linked_record(&fields, &reference)?),
                    other => {
                        return Err(wire_err(format!("unknown member stage {other:?}")));
                    }
                }
            }
            FAMILY_RELATION => {
                relations.push(parse_relation_record(&fields, &reference)?);
            }
            FAMILY_CLASSIFICATION => {
                classifications.push(parse_classification_record(&fields, &reference)?);
            }
            FAMILY_DIAGNOSTIC => {
                diagnostics.push(parse_diagnostic_record(&fields, &reference)?);
            }
            FAMILY_CONTEXT => {
                contexts.push(parse_context_record(&fields, &reference)?);
            }
            FAMILY_DOCUMENT => {}
            other => {
                return Err(wire_err(format!("unknown record family {other:?}")));
            }
        }
        records.push(ReadbackRecord {
            family,
            reference,
            raw: line.to_string(),
        });
    }

    Ok(AnalysisReadback {
        manifest,
        footer,
        fragments,
        typed_members,
        linked_members,
        relations,
        classifications,
        diagnostics,
        contexts,
        records,
    })
}

// --------------------------------------------------------- verifier #

fn record_map(readback: &AnalysisReadback) -> BTreeMap<(String, String), String> {
    readback
        .records
        .iter()
        .map(|record| {
            (
                (record.family.clone(), record.reference.clone()),
                record.raw.clone(),
            )
        })
        .collect()
}

fn envelope_record_map(
    text: &str,
) -> Result<BTreeMap<(String, String), String>, AnalysisWireError> {
    let lines = split_lines(text)?;
    let last = lines.len() - 1;
    let mut map: BTreeMap<(String, String), String> = BTreeMap::new();
    for &line in &lines[2..last] {
        let fields = JsonFields::parse(line)?;
        let family = string_field(&fields, "family")
            .ok_or_else(|| wire_err("canonical record has no family"))?;
        let reference =
            string_field(&fields, "ref").ok_or_else(|| wire_err("canonical record has no ref"))?;
        map.insert((family, reference), line.to_string());
    }
    Ok(map)
}

fn missing_record_code(family: &str) -> AnalysisVerifyCode {
    match family {
        FAMILY_DOCUMENT => AnalysisVerifyCode::ManifestIdentityMismatch,
        FAMILY_FRAGMENT => AnalysisVerifyCode::FragmentHashMismatch,
        FAMILY_MEMBER => AnalysisVerifyCode::MemberRefMissing,
        FAMILY_RELATION => AnalysisVerifyCode::RelationRefMissing,
        FAMILY_CONTEXT => AnalysisVerifyCode::ContextOutcomeMismatch,
        FAMILY_CLASSIFICATION => AnalysisVerifyCode::MemberRefMissing,
        FAMILY_DIAGNOSTIC => AnalysisVerifyCode::SourceRefSubstitution,
        _ => AnalysisVerifyCode::EnvelopeStructural,
    }
}

fn changed_record_code(family: &str) -> AnalysisVerifyCode {
    match family {
        FAMILY_DOCUMENT => AnalysisVerifyCode::ManifestIdentityMismatch,
        FAMILY_FRAGMENT => AnalysisVerifyCode::FragmentHashMismatch,
        FAMILY_MEMBER => AnalysisVerifyCode::SourceRefSubstitution,
        FAMILY_RELATION => AnalysisVerifyCode::RelationSubstitution,
        FAMILY_CONTEXT => AnalysisVerifyCode::ContextOutcomeMismatch,
        FAMILY_CLASSIFICATION => AnalysisVerifyCode::SourceRefSubstitution,
        FAMILY_DIAGNOSTIC => AnalysisVerifyCode::SourceRefSubstitution,
        _ => AnalysisVerifyCode::EnvelopeStructural,
    }
}

fn structural_code(error: &AnalysisWireError) -> AnalysisVerifyCode {
    match error.kind() {
        AnalysisWireErrorKind::CompletionMarkerInvalid
        | AnalysisWireErrorKind::RefusedRecordNotPromoted => AnalysisVerifyCode::CompletionMismatch,
        _ => AnalysisVerifyCode::EnvelopeStructural,
    }
}

/// Independently verifies a rendered analysis envelope against its pinned
/// parent (§8B.4). It never trusts the artifact's records or seals: the
/// canonical records are re-derived from `projection` + `index` + `mapping`
/// (`analyze_document` + `build_context_records`) and compared against the
/// read-back. `build_projection` is not called.
///
/// Returns `Ok(())` for a valid envelope, else `Err(findings)` with at least
/// one closed [`AnalysisVerifyCode`].
pub fn verify_npa_analysis_wire(
    text: &str,
    projection: &ReaderProjection,
    index: &ReaderRecordIndex,
    mapping: &SourceMapping,
) -> Result<(), Vec<AnalysisVerifyFinding>> {
    // 1. Structural pass + typed read-back.
    let readback = match read_back_npa_analysis(text) {
        Ok(readback) => readback,
        Err(error) => {
            return Err(vec![AnalysisVerifyFinding::new(
                structural_code(&error),
                error.detail().to_string(),
            )]);
        }
    };

    let mut findings: Vec<AnalysisVerifyFinding> = Vec::new();

    // 2. Recompute both seals and compare with the footer (non-resealed tamper).
    match recompute_analysis_seals(text) {
        Ok(seals) => {
            if readback.footer.records_seal_hash.as_deref()
                != Some(seals.records_seal_hash.as_str())
            {
                findings.push(AnalysisVerifyFinding::new(
                    AnalysisVerifyCode::SealMismatch,
                    "footer records_seal_hash differs from recompute_analysis_seals",
                ));
            }
            if readback.footer.manifest_hash.as_deref() != Some(seals.manifest_hash.as_str()) {
                findings.push(AnalysisVerifyFinding::new(
                    AnalysisVerifyCode::SealMismatch,
                    "footer manifest_hash differs from recompute_analysis_seals",
                ));
            }
        }
        Err(error) => findings.push(AnalysisVerifyFinding::new(
            structural_code(&error),
            error.detail().to_string(),
        )),
    }

    // 2b. The manifest identity must equal the supplied pinned parent. A
    //     recomputed and patched seal is not identity proof (F01): an attacker
    //     who reseals a substituted source / parent / version / profile / model
    //     must still be rejected, and a `document` record contradiction is
    //     caught in step 6.
    let envelope = mapping.envelope();
    let version = mapping.version();
    let mut identity_fields: Vec<&str> = Vec::new();
    if readback.manifest.source_sha256 != envelope.source_sha256 {
        identity_fields.push("source.sha256");
    }
    if readback.manifest.source_bytes != envelope.source_bytes {
        identity_fields.push("source.bytes");
    }
    if readback.manifest.parent_schema != envelope.parent_schema {
        identity_fields.push("parent.schema");
    }
    if readback.manifest.parent_records_seal_hash != envelope.records_seal_hash {
        identity_fields.push("parent.records_seal_hash");
    }
    if readback.manifest.parent_manifest_hash != envelope.manifest_hash {
        identity_fields.push("parent.manifest_hash");
    }
    if readback.manifest.document_version_ref != version.document_version_ref() {
        identity_fields.push("document_version_ref");
    }
    if readback.manifest.source_revision != version.source_revision() {
        identity_fields.push("source_revision");
    }
    if readback.manifest.decoder_profile != version.decoder_profile() {
        identity_fields.push("decoder_profile");
    }
    if readback.manifest.profile != PROFILE {
        identity_fields.push("profile");
    }
    if readback.manifest.model != MODEL {
        identity_fields.push("model");
    }
    if !identity_fields.is_empty() {
        findings.push(AnalysisVerifyFinding::new(
            AnalysisVerifyCode::ManifestIdentityMismatch,
            format!(
                "manifest identity differs from the pinned parent: {}",
                identity_fields.join(", ")
            ),
        ));
    }

    // 3. Re-derive the canonical records from the pinned parent. The artifact's
    //    own records and seals are not trusted.
    let analysis = match analyze_document(projection, index, mapping) {
        Ok(analysis) => analysis,
        Err(refusal) => {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::EnvelopeStructural,
                format!("canonical re-derivation refused: {refusal}"),
            ));
            return Err(dedup(findings));
        }
    };
    let contexts = build_context_records(&analysis.layout, mapping);
    let canonical_request = AnalysisEnvelopeRequest {
        analysis: &analysis,
        projection,
        index,
        mapping,
        limits: readback.manifest.limits,
        scope: AnalysisScope::Bounded,
    };
    let canonical = match render_npa_analysis_with_context(&canonical_request, &contexts) {
        Ok(canonical) => canonical,
        Err(error) => {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::EnvelopeStructural,
                format!("canonical render refused: {}", error.detail()),
            ));
            return Err(dedup(findings));
        }
    };

    // 4. Re-hash every fragment record's decoded bytes against the substrate.
    for fragment in &readback.fragments {
        match index.text(&fragment.reference) {
            Some(record) => {
                if sha256_hex(record.value.as_bytes()) != fragment.content_sha256
                    || record.value.len() as u64 != fragment.byte_length
                {
                    findings.push(AnalysisVerifyFinding::new(
                        AnalysisVerifyCode::FragmentHashMismatch,
                        format!(
                            "fragment {} content differs from the substrate index",
                            fragment.reference
                        ),
                    ));
                }
            }
            None => findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::FragmentHashMismatch,
                format!(
                    "fragment {} is absent from the substrate index",
                    fragment.reference
                ),
            )),
        }
    }

    // 5. Re-resolve every span through the pinned parent and require the exact
    //    substrate slice.
    for (label, source_ref) in readback.bound_refs() {
        if let ReadbackRef::Bound {
            fragment,
            start,
            end,
        } = source_ref
        {
            let span = ReaderFragmentSpan::new(FragmentRef::new(fragment.clone()), start, end);
            let resolved = match mapping.resolve_fragment_span(&span) {
                Ok(resolved) => resolved,
                Err(refusal) => {
                    findings.push(AnalysisVerifyFinding::new(
                        AnalysisVerifyCode::SpanSliceMismatch,
                        format!("{label} {fragment}[{start},{end}) does not resolve: {refusal}"),
                    ));
                    continue;
                }
            };
            match mapping.slice(&resolved) {
                Ok(slice) => match index.text(&fragment) {
                    Some(record) if record.value.get(start..end) == Some(slice) => {}
                    _ => findings.push(AnalysisVerifyFinding::new(
                        AnalysisVerifyCode::SpanSliceMismatch,
                        format!("{label} does not equal the exact substrate slice"),
                    )),
                },
                Err(refusal) => findings.push(AnalysisVerifyFinding::new(
                    AnalysisVerifyCode::SpanSliceMismatch,
                    format!("{label} {fragment}[{start},{end}) does not slice: {refusal}"),
                )),
            }
        }
    }

    // 6. Compare each record's semantic fields with the canonical re-derivation.
    let readback_records = record_map(&readback);
    let canonical_records = match envelope_record_map(&canonical) {
        Ok(records) => records,
        Err(error) => {
            findings.push(AnalysisVerifyFinding::new(
                structural_code(&error),
                error.detail().to_string(),
            ));
            return Err(dedup(findings));
        }
    };
    for (key, canonical_line) in &canonical_records {
        match readback_records.get(key) {
            None => findings.push(AnalysisVerifyFinding::new(
                missing_record_code(&key.0),
                format!("record {} {} is missing from the envelope", key.0, key.1),
            )),
            Some(readback_line) if readback_line != canonical_line => {
                findings.push(AnalysisVerifyFinding::new(
                    changed_record_code(&key.0),
                    format!(
                        "record {} {} differs from the canonical re-derivation",
                        key.0, key.1
                    ),
                ));
            }
            Some(_) => {}
        }
    }
    for key in readback_records.keys() {
        if !canonical_records.contains_key(key) {
            findings.push(AnalysisVerifyFinding::new(
                changed_record_code(&key.0),
                format!(
                    "record {} {} is not in the canonical re-derivation",
                    key.0, key.1
                ),
            ));
        }
    }

    // 7. Referential integrity: relations and classifications must name a
    //    readback member.
    let member_ids = readback.linked_member_ids();
    for relation in &readback.relations {
        if !member_ids.contains(&relation.from_id) || !member_ids.contains(&relation.to_id) {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::RelationRefMissing,
                format!(
                    "relation {} names a member that is not in the read-back",
                    relation.reference
                ),
            ));
        }
    }
    for classification in &readback.classifications {
        if !member_ids.contains(&classification.member_id) {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::MemberRefMissing,
                format!(
                    "classification {} names member {} that is not in the read-back",
                    classification.reference, classification.member_id
                ),
            ));
        }
    }

    // 8. Completion marker and counts against the re-derived records.
    if let Ok(canonical_summary) = inspect_npa_analysis_wire(&canonical) {
        let family_count =
            |family: &str| -> u64 { canonical_summary.families.get(family).copied().unwrap_or(0) };
        let expected: [(&str, u64); 8] = [
            ("documents", family_count(FAMILY_DOCUMENT)),
            ("fragments", family_count(FAMILY_FRAGMENT)),
            ("members", family_count(FAMILY_MEMBER)),
            ("relations", family_count(FAMILY_RELATION)),
            ("classifications", family_count(FAMILY_CLASSIFICATION)),
            ("diagnostics", family_count(FAMILY_DIAGNOSTIC)),
            ("contexts", family_count(FAMILY_CONTEXT)),
            ("records", canonical_summary.records),
        ];
        for (key, value) in expected {
            let matches = match readback.footer.counts.get(key) {
                Some(actual) => *actual == value,
                None => key == "contexts" && value == 0,
            };
            if !matches {
                findings.push(AnalysisVerifyFinding::new(
                    AnalysisVerifyCode::CompletionMismatch,
                    format!("footer count {key} is inconsistent with the re-derived records"),
                ));
            }
        }

        let canonical_completion = canonical_summary.completion.as_str();
        let canonical_basis = canonical_summary.completion_basis.as_str();
        let readback_completion = readback.footer.completion.as_str();
        let readback_basis = readback.footer.completion_basis.as_str();
        let record_basis = matches!(
            canonical_basis,
            BASIS_REFUSED_RECORD | BASIS_CONTEXT_INCOMPLETE
        );
        if record_basis {
            if readback_completion != canonical_completion || readback_basis != canonical_basis {
                findings.push(AnalysisVerifyFinding::new(
                    AnalysisVerifyCode::CompletionMismatch,
                    "completion marker is inconsistent with the re-derived records",
                ));
            }
        } else if matches!(
            readback_basis,
            BASIS_REFUSED_RECORD | BASIS_CONTEXT_INCOMPLETE
        ) {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::CompletionMismatch,
                "completion basis claims a refusal/context outcome the records do not support",
            ));
        }
        if readback_completion == "complete" && canonical_completion == "incomplete" && record_basis
        {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::CompletionMismatch,
                "a complete envelope hides a refused or non-resolved context record",
            ));
        }
        if readback_basis == BASIS_COMPLETE && canonical_completion == "incomplete" {
            findings.push(AnalysisVerifyFinding::new(
                AnalysisVerifyCode::CompletionMismatch,
                "a bounded-complete basis cannot hide an incomplete canonical derivation",
            ));
        }
    }

    let findings = dedup(findings);
    if findings.is_empty() {
        Ok(())
    } else {
        Err(findings)
    }
}

/// Deduplicates findings by `(code, detail)` preserving first-seen order.
fn dedup(findings: Vec<AnalysisVerifyFinding>) -> Vec<AnalysisVerifyFinding> {
    let mut seen: BTreeSet<(AnalysisVerifyCode, String)> = BTreeSet::new();
    let mut out: Vec<AnalysisVerifyFinding> = Vec::new();
    for finding in findings {
        if seen.insert((finding.code, finding.detail.clone())) {
            out.push(finding);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verify_codes_are_closed_tokens() {
        assert_eq!(
            AnalysisVerifyCode::EnvelopeStructural.as_str(),
            "envelope_structural"
        );
        assert_eq!(AnalysisVerifyCode::SealMismatch.as_str(), "seal_mismatch");
        assert_eq!(
            AnalysisVerifyCode::ManifestIdentityMismatch.as_str(),
            "manifest_identity_mismatch"
        );
        assert_eq!(
            AnalysisVerifyCode::FragmentHashMismatch.as_str(),
            "fragment_hash_mismatch"
        );
        assert_eq!(
            AnalysisVerifyCode::SpanSliceMismatch.as_str(),
            "span_slice_mismatch"
        );
        assert_eq!(
            AnalysisVerifyCode::SourceRefSubstitution.as_str(),
            "source_ref_substitution"
        );
        assert_eq!(
            AnalysisVerifyCode::RelationRefMissing.as_str(),
            "relation_ref_missing"
        );
        assert_eq!(
            AnalysisVerifyCode::RelationSubstitution.as_str(),
            "relation_substitution"
        );
        assert_eq!(
            AnalysisVerifyCode::MemberRefMissing.as_str(),
            "member_ref_missing"
        );
        assert_eq!(
            AnalysisVerifyCode::ContextOutcomeMismatch.as_str(),
            "context_outcome_mismatch"
        );
        assert_eq!(
            AnalysisVerifyCode::CompletionMismatch.as_str(),
            "completion_mismatch"
        );
    }
}
