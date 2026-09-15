//! Typed current-document requisites sidecar (D388).
//!
//! Claims remain source-separated and immutable. This module performs only
//! exact raw-value agreement; normalization and source authority are deferred.
//! Authorization is issued only by this validated sidecar and explicit grammar
//! evidence, never by local grammar frames or cited-act tails.

use std::collections::{BTreeMap, BTreeSet};

use crate::domain::TextSpan;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum RequisitesField {
    Type,
    Org,
    Geo,
    Date,
    Number,
    Title,
    Family,
}

impl RequisitesField {
    pub const ALL: [Self; 7] = [
        Self::Type,
        Self::Org,
        Self::Geo,
        Self::Date,
        Self::Number,
        Self::Title,
        Self::Family,
    ];

    /// Closed YAML spelling (`prd/architecture/current-document-requisites.yaml`).
    /// Used only to render a closed field fingerprint; never to spell source text.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Type => "type",
            Self::Org => "org",
            Self::Geo => "geo",
            Self::Date => "date",
            Self::Number => "number",
            Self::Title => "title",
            Self::Family => "family",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum RequisitesSourceKind {
    DocumentHead,
    SourceFilename,
    SourceCatalog,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RequisitesExtractionStatus {
    Observed,
    Missing,
    Malformed,
    WrongDocument,
    Unavailable,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceAnchor {
    text_span: TextSpan,
    document_anchor: String,
}

impl SourceAnchor {
    pub fn try_new(text_span: TextSpan, document_anchor: String) -> Result<Self, &'static str> {
        if document_anchor.trim().is_empty() {
            return Err("document anchor is empty");
        }
        Ok(Self {
            text_span,
            document_anchor,
        })
    }

    pub const fn text_span(&self) -> TextSpan {
        self.text_span
    }
    pub fn document_anchor(&self) -> &str {
        &self.document_anchor
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RequisitesClaim {
    claim_id: String,
    document_version_ref: String,
    field: RequisitesField,
    raw_value: String,
    source_kind: RequisitesSourceKind,
    source_anchor: SourceAnchor,
    extractor_profile: String,
    extraction_status: RequisitesExtractionStatus,
}

impl RequisitesClaim {
    #[allow(clippy::too_many_arguments)]
    pub fn try_new(
        claim_id: String,
        document_version_ref: String,
        field: RequisitesField,
        raw_value: String,
        source_kind: RequisitesSourceKind,
        source_anchor: SourceAnchor,
        extractor_profile: String,
        extraction_status: RequisitesExtractionStatus,
    ) -> Result<Self, &'static str> {
        if claim_id.trim().is_empty()
            || document_version_ref.trim().is_empty()
            || extractor_profile.trim().is_empty()
        {
            return Err("claim identity and extractor profile must be non-empty");
        }
        if matches!(extraction_status, RequisitesExtractionStatus::Observed)
            && raw_value.trim().is_empty()
        {
            return Err("observed claim value is empty");
        }
        Ok(Self {
            claim_id,
            document_version_ref,
            field,
            raw_value,
            source_kind,
            source_anchor,
            extractor_profile,
            extraction_status,
        })
    }

    pub fn claim_id(&self) -> &str {
        &self.claim_id
    }
    pub fn document_version_ref(&self) -> &str {
        &self.document_version_ref
    }
    pub const fn field(&self) -> RequisitesField {
        self.field
    }
    pub fn raw_value(&self) -> &str {
        &self.raw_value
    }
    pub const fn source_kind(&self) -> RequisitesSourceKind {
        self.source_kind
    }
    pub const fn source_anchor(&self) -> &SourceAnchor {
        &self.source_anchor
    }
    pub fn extractor_profile(&self) -> &str {
        &self.extractor_profile
    }
    pub const fn extraction_status(&self) -> RequisitesExtractionStatus {
        self.extraction_status
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FieldResolutionStatus {
    Agreed,
    SingleSource,
    Conflicting,
    Missing,
    Invalid,
    AssociationFailed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldResolution {
    field: RequisitesField,
    status: FieldResolutionStatus,
    compatible_candidate_refs: Vec<String>,
    competing_candidate_refs: Vec<String>,
    selection_policy_ref: Option<String>,
}

impl FieldResolution {
    pub const fn field(&self) -> RequisitesField {
        self.field
    }
    pub const fn status(&self) -> FieldResolutionStatus {
        self.status
    }
    pub fn compatible_candidate_refs(&self) -> &[String] {
        &self.compatible_candidate_refs
    }
    pub fn competing_candidate_refs(&self) -> &[String] {
        &self.competing_candidate_refs
    }
    pub fn selection_policy_ref(&self) -> Option<&str> {
        self.selection_policy_ref.as_deref()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SidecarCompleteness {
    CompleteAgreed,
    UsablePartial,
    Conflicting,
    Unavailable,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RequisitesDiagnostic {
    HeadFilenameConflict,
    HeadCatalogConflict,
    FilenameCatalogConflict,
    RegionalGeoConflict,
    OrgGeoRoleCollapse,
    NumberNormalizationAmbiguous,
    TitleAliasOnly,
    WrongDocumentAssociation,
    RequiredFieldMissing,
    SourceAuthorityPolicyMissing,
}

impl RequisitesDiagnostic {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::HeadFilenameConflict => "head_filename_conflict",
            Self::HeadCatalogConflict => "head_catalog_conflict",
            Self::FilenameCatalogConflict => "filename_catalog_conflict",
            Self::RegionalGeoConflict => "regional_geo_conflict",
            Self::OrgGeoRoleCollapse => "org_geo_role_collapse",
            Self::NumberNormalizationAmbiguous => "number_normalization_ambiguous",
            Self::TitleAliasOnly => "title_alias_only",
            Self::WrongDocumentAssociation => "wrong_document_association",
            Self::RequiredFieldMissing => "required_field_missing",
            Self::SourceAuthorityPolicyMissing => "source_authority_policy_missing",
        }
    }
}

/// Opaque grammar proof supplied by the ThisRef recognizer. It records only
/// admitted fields, not source text or a way to manufacture a cited-act tail.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ThisRefGrammarEvidence {
    fields: BTreeSet<RequisitesField>,
}
impl ThisRefGrammarEvidence {
    pub fn new(fields: impl IntoIterator<Item = RequisitesField>) -> Self {
        Self {
            fields: fields.into_iter().collect(),
        }
    }
    pub fn contains(&self, field: RequisitesField) -> bool {
        self.fields.contains(&field)
    }
    pub fn is_empty(&self) -> bool {
        self.fields.is_empty()
    }
    /// Closed fingerprint over the admitted field vocabulary in deterministic
    /// order. It never carries source text, so it is safe to use as part of a
    /// context memo identity: two requests that admit different fields can
    /// never share one memoized authorization.
    pub fn fingerprint(&self) -> String {
        self.fields
            .iter()
            .map(|field| field.as_str())
            .collect::<Vec<_>>()
            .join("|")
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentHeadEllipsisEvidence {
    marker: ThisRefGrammarEvidence,
}
impl DocumentHeadEllipsisEvidence {
    pub fn new(marker: ThisRefGrammarEvidence) -> Self {
        Self { marker }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentDocumentRequisites {
    document_version_ref: String,
    raw_claims: Vec<RequisitesClaim>,
    field_resolutions: Vec<FieldResolution>,
    completeness: SidecarCompleteness,
    diagnostics: Vec<RequisitesDiagnostic>,
}

impl CurrentDocumentRequisites {
    pub fn try_new(
        document_version_ref: String,
        claims: Vec<RequisitesClaim>,
    ) -> Result<Self, &'static str> {
        if document_version_ref.trim().is_empty() {
            return Err("document version ref is empty");
        }
        let mut ids = BTreeSet::new();
        for claim in &claims {
            if claim.document_version_ref != document_version_ref
                || !ids.insert(claim.claim_id.clone())
            {
                return Err("claims must have unique ids and match document version");
            }
        }
        let mut resolutions = Vec::new();
        let mut diagnostics = Vec::new();
        for field in RequisitesField::ALL {
            let field_claims: Vec<&RequisitesClaim> =
                claims.iter().filter(|c| c.field == field).collect();
            let wrong = field_claims
                .iter()
                .any(|c| c.extraction_status == RequisitesExtractionStatus::WrongDocument);
            if wrong {
                diagnostics.push(RequisitesDiagnostic::WrongDocumentAssociation);
            }
            let usable: Vec<&RequisitesClaim> = field_claims
                .iter()
                .copied()
                .filter(|c| c.extraction_status == RequisitesExtractionStatus::Observed)
                .collect();
            let mut groups: BTreeMap<&str, Vec<String>> = BTreeMap::new();
            for claim in &usable {
                groups
                    .entry(claim.raw_value())
                    .or_default()
                    .push(claim.claim_id.clone());
            }
            let (status, compatible, competing) = if wrong && usable.is_empty() {
                (
                    FieldResolutionStatus::AssociationFailed,
                    Vec::new(),
                    Vec::new(),
                )
            } else if groups.is_empty() {
                (
                    if field_claims
                        .iter()
                        .any(|c| c.extraction_status == RequisitesExtractionStatus::Malformed)
                    {
                        FieldResolutionStatus::Invalid
                    } else {
                        FieldResolutionStatus::Missing
                    },
                    Vec::new(),
                    Vec::new(),
                )
            } else if groups.len() == 1 {
                let refs = groups.into_values().next().unwrap_or_default();
                (
                    if refs.len() > 1 {
                        FieldResolutionStatus::Agreed
                    } else {
                        FieldResolutionStatus::SingleSource
                    },
                    refs,
                    Vec::new(),
                )
            } else {
                let mut refs = Vec::new();
                for values in groups.values() {
                    refs.extend(values.iter().cloned());
                }
                let sources: BTreeSet<RequisitesSourceKind> =
                    usable.iter().map(|claim| claim.source_kind).collect();
                if sources.contains(&RequisitesSourceKind::DocumentHead)
                    && sources.contains(&RequisitesSourceKind::SourceFilename)
                {
                    diagnostics.push(RequisitesDiagnostic::HeadFilenameConflict);
                }
                if sources.contains(&RequisitesSourceKind::DocumentHead)
                    && sources.contains(&RequisitesSourceKind::SourceCatalog)
                {
                    diagnostics.push(RequisitesDiagnostic::HeadCatalogConflict);
                }
                if sources.contains(&RequisitesSourceKind::SourceFilename)
                    && sources.contains(&RequisitesSourceKind::SourceCatalog)
                {
                    diagnostics.push(RequisitesDiagnostic::FilenameCatalogConflict);
                }
                (FieldResolutionStatus::Conflicting, Vec::new(), refs)
            };
            if matches!(
                status,
                FieldResolutionStatus::Missing | FieldResolutionStatus::Invalid
            ) {
                diagnostics.push(RequisitesDiagnostic::RequiredFieldMissing);
            }
            resolutions.push(FieldResolution {
                field,
                status,
                compatible_candidate_refs: compatible,
                competing_candidate_refs: competing,
                selection_policy_ref: None,
            });
        }
        let has_conflict = resolutions.iter().any(|r| {
            matches!(
                r.status,
                FieldResolutionStatus::Conflicting | FieldResolutionStatus::AssociationFailed
            )
        });
        let observed = resolutions
            .iter()
            .filter(|r| {
                matches!(
                    r.status,
                    FieldResolutionStatus::Agreed | FieldResolutionStatus::SingleSource
                )
            })
            .count();
        let completeness = if has_conflict {
            SidecarCompleteness::Conflicting
        } else if observed == RequisitesField::ALL.len()
            && resolutions
                .iter()
                .all(|r| r.status == FieldResolutionStatus::Agreed)
        {
            SidecarCompleteness::CompleteAgreed
        } else if observed > 0 {
            SidecarCompleteness::UsablePartial
        } else {
            SidecarCompleteness::Unavailable
        };
        Ok(Self {
            document_version_ref,
            raw_claims: claims,
            field_resolutions: resolutions,
            completeness,
            diagnostics,
        })
    }

    pub fn document_version_ref(&self) -> &str {
        &self.document_version_ref
    }
    pub fn raw_claims(&self) -> &[RequisitesClaim] {
        &self.raw_claims
    }
    pub fn field_resolutions(&self) -> &[FieldResolution] {
        &self.field_resolutions
    }
    pub const fn completeness(&self) -> SidecarCompleteness {
        self.completeness
    }
    pub fn diagnostics(&self) -> &[RequisitesDiagnostic] {
        &self.diagnostics
    }

    /// Content-bound identity of this sidecar. It exists so a context memo can
    /// be bound to the exact authorization inputs it was computed from: a
    /// sidecar whose version, completeness, or claims changed can never be
    /// served a stale memoized authorization (RC28-F08). It is an identity
    /// token only and is never emitted as a claim or a report field.
    pub fn identity_fingerprint(&self) -> String {
        let mut out = format!("{}:{:?}", self.document_version_ref, self.completeness);
        for claim in &self.raw_claims {
            out.push('|');
            out.push_str(claim.claim_id());
            out.push(':');
            out.push_str(claim.field().as_str());
            out.push(':');
            out.push_str(claim.raw_value());
            out.push(':');
            out.push_str(&format!(
                "{:?}/{:?}/{}",
                claim.source_kind(),
                claim.extraction_status(),
                claim.extractor_profile()
            ));
        }
        out
    }
    fn resolution(&self, field: RequisitesField) -> &FieldResolution {
        self.field_resolutions
            .iter()
            .find(|r| r.field == field)
            .expect("all fields are reduced")
    }
    fn authorizes(&self, evidence: &ThisRefGrammarEvidence) -> bool {
        !evidence.fields.is_empty()
            && self.completeness != SidecarCompleteness::Unavailable
            && RequisitesField::ALL
                .iter()
                .filter(|f| evidence.contains(**f))
                .all(|f| {
                    matches!(
                        self.resolution(*f).status,
                        FieldResolutionStatus::Agreed | FieldResolutionStatus::SingleSource
                    )
                })
    }
    pub fn authorize_this_document_reference(&self, evidence: ThisRefGrammarEvidence) -> bool {
        self.authorizes(&evidence)
    }
    pub fn authorize_document_head_ellipsis(&self, evidence: DocumentHeadEllipsisEvidence) -> bool {
        self.authorizes(&evidence.marker)
    }
}
