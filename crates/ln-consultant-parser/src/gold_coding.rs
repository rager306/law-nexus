//! Bounded C5 double-coding envelope for NPA parser evidence.
//!
//! This module measures deterministic coder profiles only.  It never calls the
//! product extractor, never calls a result gold or accepted, and keeps
//! adjudication as an append-only derived record.

use ln_decode::{
    deontic::DeonticLexemeKind,
    domain::{HierarchyLevel, TextSpan},
    references::ReferenceMentionKind,
    temporal::TemporalPhraseKind,
};
use ln_temporal::{identity_binding::FieldKind, semantic_scope::SemanticClaimKind};
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt,
};

pub const SCHEMA: &str = "npa-c5-gold-coding/v1";
pub const ALPHA_RULE: &str = "krippendorff-nominal-two-rater-coincidence/v1";

/// Measurement state is explicit: absence of coder units is not agreement.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MeasurementStatus {
    NotMeasured,
    ProxyMeasured,
    IndependentMeasured,
}
impl MeasurementStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NotMeasured => "not-measured",
            Self::ProxyMeasured => "proxy-measured",
            Self::IndependentMeasured => "independent-measured",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CodingLayer {
    Parsing,
    Semantic,
    Identity,
    Temporal,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CodingLabel {
    layer: CodingLayer,
    value: String,
}
impl CodingLabel {
    pub fn new(layer: CodingLayer, value: impl Into<String>) -> Result<Self, CodingError> {
        let value = value.into();
        if value.trim().is_empty() {
            return Err(CodingError::EmptyLabel);
        }
        if !allowed(layer, &value) {
            return Err(CodingError::UnknownLabel);
        }
        Ok(Self { layer, value })
    }
    pub fn layer(&self) -> CodingLayer {
        self.layer
    }
    pub fn value(&self) -> &str {
        &self.value
    }
}

fn allowed(layer: CodingLayer, value: &str) -> bool {
    match layer {
        CodingLayer::Parsing => {
            HierarchyLevel::all().iter().any(|x| x.as_str() == value)
                || matches!(
                    value,
                    "Article"
                        | "Point"
                        | "EntersIntoForce"
                        | "LosesForce"
                        | "Obligation"
                        | "Permission"
                        | "Prohibition"
                )
        }
        CodingLayer::Semantic => [
            "Actor",
            "Action",
            "Object",
            "Polarity",
            "Condition",
            "Exception",
            "TemporalQualifier",
            "Abstention",
        ]
        .contains(&value),
        CodingLayer::Identity => ["Type", "Org", "Geo", "Date", "Number", "Name"].contains(&value),
        CodingLayer::Temporal => matches!(
            value,
            "EntersIntoForce" | "LosesForce" | "AsOfPairing" | "EditionPairing" | "Abstention"
        ),
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CodingUnit {
    document_relative_path: String,
    content_hash: String,
    block_index: usize,
    span: TextSpan,
    label: CodingLabel,
}
impl CodingUnit {
    pub fn new(
        path: impl Into<String>,
        hash: impl Into<String>,
        block_index: usize,
        span: TextSpan,
        block_text: &str,
        label: CodingLabel,
    ) -> Result<Self, CodingError> {
        let path = path.into();
        let hash = hash.into();
        if path.trim().is_empty() {
            return Err(CodingError::EmptyDocumentPath);
        }
        if hash.trim().is_empty() {
            return Err(CodingError::EmptyContentHash);
        }
        if span.end() > block_text.len()
            || !block_text.is_char_boundary(span.start())
            || !block_text.is_char_boundary(span.end())
        {
            return Err(CodingError::InvalidSpan);
        }
        Ok(Self {
            document_relative_path: path,
            content_hash: hash,
            block_index,
            span,
            label,
        })
    }
    pub fn key(&self) -> (&str, &str, usize, usize, usize) {
        (
            &self.document_relative_path,
            &self.content_hash,
            self.block_index,
            self.span.start(),
            self.span.end(),
        )
    }
    pub fn label(&self) -> &CodingLabel {
        &self.label
    }
    pub fn span(&self) -> TextSpan {
        self.span
    }
    pub fn document_relative_path(&self) -> &str {
        &self.document_relative_path
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoderPass {
    coder_id: String,
    coder_profile: String,
    units: Vec<CodingUnit>,
}
impl CoderPass {
    pub fn new(
        coder_id: impl Into<String>,
        coder_profile: impl Into<String>,
        units: Vec<CodingUnit>,
    ) -> Result<Self, CodingError> {
        let coder_id = coder_id.into();
        let coder_profile = coder_profile.into();
        if coder_id.trim().is_empty() {
            return Err(CodingError::EmptyCoderId);
        }
        if coder_profile.trim().is_empty() {
            return Err(CodingError::EmptyCoderProfile);
        }
        if units.is_empty() {
            return Err(CodingError::EmptyEnvelope);
        }
        let mut seen = BTreeSet::new();
        for unit in &units {
            if !seen.insert(unit.key()) {
                return Err(CodingError::DuplicateUnit);
            }
        }
        Ok(Self {
            coder_id,
            coder_profile,
            units,
        })
    }
    pub fn coder_id(&self) -> &str {
        &self.coder_id
    }
    pub fn coder_profile(&self) -> &str {
        &self.coder_profile
    }
    pub fn units(&self) -> &[CodingUnit] {
        &self.units
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CodingError {
    EmptyLabel,
    UnknownLabel,
    EmptyDocumentPath,
    EmptyContentHash,
    InvalidSpan,
    EmptyCoderId,
    EmptyCoderProfile,
    DuplicateCoderId,
    DuplicateProfile,
    EmptyEnvelope,
    DuplicateUnit,
    UnitSetMismatch,
    MissingCode,
    MissingSnapshotBinding,
}
impl fmt::Display for CodingError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "C5 coding rejected: {self:?}")
    }
}
impl std::error::Error for CodingError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AlphaRatio {
    pub numerator: i64,
    pub denominator: i64,
}
impl AlphaRatio {
    pub fn value(self) -> f64 {
        self.numerator as f64 / self.denominator as f64
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Agreement {
    pub matched: usize,
    pub total: usize,
    pub alpha: AlphaRatio,
}

impl Agreement {
    pub fn percent(self) -> f64 {
        self.matched as f64 / self.total as f64
    }
}

/// Publication cannot manufacture agreement. It is only available after the
/// two passes have been bound to the same non-empty snapshot and their units
/// have been compared by `agreement`.
pub fn publication_status(
    envelope: Option<&CodingEnvelope>,
    expected_snapshot: &str,
) -> Result<MeasurementStatus, CodingError> {
    if expected_snapshot.trim().is_empty() || !expected_snapshot.starts_with("sha256:") {
        return Err(CodingError::MissingSnapshotBinding);
    }
    let Some(envelope) = envelope else {
        return Ok(MeasurementStatus::NotMeasured);
    };
    let result = envelope.agreement()?;
    if result.total == 0 {
        return Err(CodingError::EmptyEnvelope);
    }
    Ok(MeasurementStatus::ProxyMeasured)
}

/// Exact two-rater nominal alpha. Missing or differently anchored units fail closed.
pub fn agreement(first: &CoderPass, second: &CoderPass) -> Result<Agreement, CodingError> {
    if first.units.len() != second.units.len() {
        return Err(CodingError::UnitSetMismatch);
    }
    let mut right = BTreeMap::new();
    for unit in &second.units {
        right.insert(unit.key(), unit);
    }
    let mut a = Vec::with_capacity(first.units.len());
    let mut b = Vec::with_capacity(first.units.len());
    let mut matched = 0;
    for unit in &first.units {
        let other = right.get(&unit.key()).ok_or(CodingError::UnitSetMismatch)?;
        if unit.label == other.label {
            matched += 1;
        }
        a.push(unit.label.value.as_str());
        b.push(other.label.value.as_str());
    }
    let alpha = krippendorff_nominal_alpha(&a, &b)?;
    Ok(Agreement {
        matched,
        total: a.len(),
        alpha,
    })
}

pub fn krippendorff_nominal_alpha(a: &[&str], b: &[&str]) -> Result<AlphaRatio, CodingError> {
    if a.is_empty() {
        return Err(CodingError::EmptyEnvelope);
    }
    if a.len() != b.len() {
        return Err(CodingError::UnitSetMismatch);
    }
    if a.iter().chain(b).any(|x| x.is_empty()) {
        return Err(CodingError::MissingCode);
    }
    let mut codes = BTreeSet::new();
    for code in a.iter().chain(b) {
        codes.insert(*code);
    }
    let codes: Vec<_> = codes.into_iter().collect();
    let width = codes.len();
    let mut o = vec![0i64; width * width];
    for (left, right) in a.iter().zip(b) {
        let i = codes.binary_search(left).unwrap();
        let j = codes.binary_search(right).unwrap();
        o[i * width + j] += 1;
        o[j * width + i] += 1;
    }
    let totals: Vec<i64> = (0..width)
        .map(|i| (0..width).map(|j| o[i * width + j]).sum())
        .collect();
    let n: i64 = totals.iter().sum();
    let diagonal: i64 = (0..width).map(|i| o[i * width + i]).sum();
    let expected = n * n - totals.iter().map(|x| x * x).sum::<i64>();
    let observed = n - diagonal;
    if expected == 0 {
        return Ok(if observed == 0 {
            AlphaRatio {
                numerator: 1,
                denominator: 1,
            }
        } else {
            AlphaRatio {
                numerator: 0,
                denominator: 1,
            }
        });
    }
    Ok(AlphaRatio {
        numerator: expected - observed * (n - 1),
        denominator: expected,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgreementClassification {
    Proxy,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Adjudication {
    unit_key: (String, String, usize, usize, usize),
    label: CodingLabel,
    reason: String,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CodingEnvelope {
    first: CoderPass,
    second: CoderPass,
    adjudications: Vec<Adjudication>,
}
impl CodingEnvelope {
    pub fn new(first: CoderPass, second: CoderPass) -> Result<Self, CodingError> {
        if first.coder_id == second.coder_id {
            return Err(CodingError::DuplicateCoderId);
        }
        if first.coder_profile == second.coder_profile {
            return Err(CodingError::DuplicateProfile);
        }
        agreement(&first, &second)?;
        Ok(Self {
            first,
            second,
            adjudications: Vec::new(),
        })
    }
    pub fn agreement(&self) -> Result<Agreement, CodingError> {
        agreement(&self.first, &self.second)
    }
    pub fn classification(&self) -> AgreementClassification {
        AgreementClassification::Proxy
    }
    pub fn adjudications(&self) -> &[Adjudication] {
        &self.adjudications
    }
    pub fn adjudicate(
        &self,
        unit_key: (String, String, usize, usize, usize),
        label: CodingLabel,
        reason: impl Into<String>,
    ) -> Result<Self, CodingError> {
        let mut next = self.clone();
        let reason = reason.into();
        if reason.trim().is_empty() {
            return Err(CodingError::MissingCode);
        }
        if next.adjudications.iter().any(|x| x.unit_key == unit_key) {
            return Err(CodingError::DuplicateUnit);
        }
        next.adjudications.push(Adjudication {
            unit_key,
            label,
            reason,
        });
        Ok(next)
    }
}

// Keep the closed vocabulary visibly tied to the owning domain enums.
const _: Option<TemporalPhraseKind> = None;
const _: Option<ReferenceMentionKind> = None;
const _: Option<DeonticLexemeKind> = None;
const _: Option<SemanticClaimKind> = None;
const _: Option<FieldKind> = None;
