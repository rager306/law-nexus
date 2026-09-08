//! Bounded, source-evidence-only document context (D385/D386).
//!
//! This module deliberately exposes a closed structural vocabulary.  It does
//! not create semantic claims, aliases, or cross-block text spans.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use crate::current_requisites::ThisRefGrammarEvidence;
use crate::domain::{ParagraphStyle, ParsedBlock, SourceLocation, TextSpan};
use crate::hierarchy::extract_hierarchy;
use crate::lawref::LawRef;
use crate::local_grammar::{
    CoordinatingFrame, DerivationSource, FrameKind, FrameStatus, StructuralDesignationFrame,
};
use crate::morphology::{find_legal_markers, LegalMarkerKind};

const MAX_ID_LEN: usize = 64;
macro_rules! id_type {
    ($name:ident, $kind:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
        pub struct $name(String);
        impl $name {
            pub fn parse(value: &str) -> Result<Self, ContextIdError> {
                if value.is_empty()
                    || value.len() > MAX_ID_LEN
                    || !value.bytes().all(|b| {
                        b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.')
                    })
                {
                    return Err(ContextIdError($kind));
                }
                Ok(Self(value.to_owned()))
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ContextIdError(&'static str);
impl fmt::Display for ContextIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "invalid {}", self.0)
    }
}
impl std::error::Error for ContextIdError {}

id_type!(BlockId, "block id");
id_type!(ContainerId, "container id");
id_type!(FrameRef, "frame ref");
id_type!(MentionRef, "mention ref");
id_type!(AliasId, "alias id");

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct DocumentVersionRef {
    document_version_ref: String,
    source_revision: String,
    decoder_profile: String,
}
impl DocumentVersionRef {
    pub fn try_new(
        document_version_ref: String,
        source_revision: String,
        decoder_profile: String,
    ) -> Result<Self, ContextIdError> {
        for (v, k) in [
            (&document_version_ref, "document version ref"),
            (&source_revision, "source revision"),
            (&decoder_profile, "decoder profile"),
        ] {
            if v.trim().is_empty() || v.len() > MAX_ID_LEN {
                return Err(ContextIdError(k));
            }
        }
        Ok(Self {
            document_version_ref,
            source_revision,
            decoder_profile,
        })
    }
    pub fn document_version_ref(&self) -> &str {
        &self.document_version_ref
    }
    pub fn source_revision(&self) -> &str {
        &self.source_revision
    }
    pub fn decoder_profile(&self) -> &str {
        &self.decoder_profile
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContainerRole {
    Document,
    Division,
    Section,
    Chapter,
    Article,
    Clause,
    Part,
    Item,
    Subitem,
    Heading,
    AmendmentBlock,
    RequisitesBlock,
}
impl ContainerRole {
    pub const ALL: [Self; 12] = [
        Self::Document,
        Self::Division,
        Self::Section,
        Self::Chapter,
        Self::Article,
        Self::Clause,
        Self::Part,
        Self::Item,
        Self::Subitem,
        Self::Heading,
        Self::AmendmentBlock,
        Self::RequisitesBlock,
    ];
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum StructureEdgeRelation {
    ParentOf,
    ChildOf,
    ImmediatelyPrecedes,
    ImmediatelyFollows,
    ContainedIn,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum StructureEdgeStatus {
    Proposed,
    Accepted,
    Conflicting,
    Rejected,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBlockNode {
    block_id: BlockId,
    order: usize,
    block_kind: ParagraphStyle,
    local_anchor: TextSpan,
    source_evidence: SourceLocation,
}
impl SourceBlockNode {
    pub fn block_id(&self) -> &BlockId {
        &self.block_id
    }
    pub fn order(&self) -> usize {
        self.order
    }
    pub fn block_kind(&self) -> ParagraphStyle {
        self.block_kind
    }
    pub fn local_anchor(&self) -> TextSpan {
        self.local_anchor
    }
    pub fn source_evidence(&self) -> &SourceLocation {
        &self.source_evidence
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralContainerNode {
    container_id: ContainerId,
    role: ContainerRole,
    designation: Option<String>,
    heading_anchor: Option<TextSpan>,
    parent_id: Option<ContainerId>,
    source_evidence: SourceLocation,
}
impl StructuralContainerNode {
    pub fn container_id(&self) -> &ContainerId {
        &self.container_id
    }
    pub fn role(&self) -> ContainerRole {
        self.role
    }
    pub fn designation(&self) -> Option<&str> {
        self.designation.as_deref()
    }
    pub fn heading_anchor(&self) -> Option<TextSpan> {
        self.heading_anchor
    }
    pub fn parent_id(&self) -> Option<&ContainerId> {
        self.parent_id.as_ref()
    }
    pub fn source_evidence(&self) -> &SourceLocation {
        &self.source_evidence
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructureEdge {
    from: String,
    to: String,
    relation: StructureEdgeRelation,
    evidence: TextSpan,
    status: StructureEdgeStatus,
}
impl StructureEdge {
    pub fn from(&self) -> &str {
        &self.from
    }
    pub fn to(&self) -> &str {
        &self.to
    }
    pub fn relation(&self) -> StructureEdgeRelation {
        self.relation
    }
    pub fn evidence(&self) -> TextSpan {
        self.evidence
    }
    pub fn status(&self) -> StructureEdgeStatus {
        self.status
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IndexBuildError {
    EmptyDocument,
    DuplicateId,
    MissingDocumentStructure,
    ConflictingRoleEvidence,
}
impl fmt::Display for IndexBuildError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "document structure index build failed: {:?}", self)
    }
}
impl std::error::Error for IndexBuildError {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentStructureIndex {
    version: DocumentVersionRef,
    source_blocks: Vec<SourceBlockNode>,
    containers: Vec<StructuralContainerNode>,
    edges: Vec<StructureEdge>,
}
impl DocumentStructureIndex {
    pub fn version(&self) -> &DocumentVersionRef {
        &self.version
    }
    pub fn source_blocks(&self) -> &[SourceBlockNode] {
        &self.source_blocks
    }
    pub fn containers(&self) -> &[StructuralContainerNode] {
        &self.containers
    }
    pub fn edges(&self) -> &[StructureEdge] {
        &self.edges
    }
    pub fn ancestor_path(
        &self,
        block: &BlockId,
    ) -> Result<Vec<&StructuralContainerNode>, ContextStatus> {
        let node = self
            .source_blocks
            .iter()
            .find(|n| n.block_id() == block)
            .ok_or(ContextStatus::Unavailable)?;
        let mut out = Vec::new();
        let mut current = self
            .edges
            .iter()
            .find(|e| {
                e.from == node.block_id.as_str() && e.relation == StructureEdgeRelation::ContainedIn
            })
            .map(|e| e.to.clone());
        while let Some(id) = current {
            let c = self
                .containers
                .iter()
                .find(|c| c.container_id.as_str() == id)
                .ok_or(ContextStatus::Partial)?;
            out.push(c);
            current = c.parent_id.as_ref().map(|p| p.as_str().to_owned());
        }
        if out.is_empty() {
            Err(ContextStatus::Unavailable)
        } else {
            Ok(out)
        }
    }
    pub fn adjacent_blocks(&self, block: &BlockId, radius: usize) -> Vec<&SourceBlockNode> {
        let Some(n) = self.source_blocks.iter().find(|n| n.block_id() == block) else {
            return Vec::new();
        };
        self.source_blocks
            .iter()
            .filter(|x| x.order.abs_diff(n.order) <= radius && x.order != n.order)
            .collect()
    }
}

pub fn build_document_structure_index(
    version: DocumentVersionRef,
    blocks: &[ParsedBlock],
) -> Result<DocumentStructureIndex, IndexBuildError> {
    if blocks.is_empty() {
        return Err(IndexBuildError::EmptyDocument);
    }
    let mut source_blocks = Vec::new();
    let mut containers = Vec::new();
    let mut edges = Vec::new();
    let mut ids = BTreeSet::new();
    let root_id = ContainerId::parse("container-document").unwrap();
    containers.push(StructuralContainerNode {
        container_id: root_id.clone(),
        role: ContainerRole::Document,
        designation: None,
        heading_anchor: None,
        parent_id: None,
        source_evidence: blocks[0].source_location().clone(),
    });
    let mut stack: Vec<(usize, ContainerId)> = Vec::new();
    for (i, b) in blocks.iter().enumerate() {
        let bid = BlockId::parse(&format!("block-{i}")).unwrap();
        if !ids.insert(bid.clone()) {
            return Err(IndexBuildError::DuplicateId);
        }
        let anchor = TextSpan::try_new(0, b.text().len())
            .map_err(|_| IndexBuildError::MissingDocumentStructure)?;
        source_blocks.push(SourceBlockNode {
            block_id: bid.clone(),
            order: i,
            block_kind: b.style(),
            local_anchor: anchor,
            source_evidence: b.source_location().clone(),
        });
        if i > 0 {
            let prev = format!("block-{}", i - 1);
            edges.push(StructureEdge {
                from: prev.clone(),
                to: bid.as_str().into(),
                relation: StructureEdgeRelation::ImmediatelyPrecedes,
                evidence: anchor,
                status: StructureEdgeStatus::Accepted,
            });
            edges.push(StructureEdge {
                from: bid.as_str().into(),
                to: prev,
                relation: StructureEdgeRelation::ImmediatelyFollows,
                evidence: anchor,
                status: StructureEdgeStatus::Accepted,
            });
        }
        let role = if b.style() == ParagraphStyle::Title && i == 0 {
            Some((ContainerRole::RequisitesBlock, None))
        } else if b.style() == ParagraphStyle::Heading {
            let m = find_legal_markers(b.text());
            if m.len() > 1
                && m.iter().any(|x| {
                    matches!(
                        x.kind(),
                        LegalMarkerKind::Razdel | LegalMarkerKind::Glava | LegalMarkerKind::Statya
                    )
                })
            {
                return Err(IndexBuildError::ConflictingRoleEvidence);
            };
            m.first().map(|x| {
                (
                    match x.kind() {
                        LegalMarkerKind::Razdel => ContainerRole::Division,
                        LegalMarkerKind::Glava => ContainerRole::Chapter,
                        LegalMarkerKind::Statya => ContainerRole::Article,
                        LegalMarkerKind::Chast => ContainerRole::Part,
                        LegalMarkerKind::Punkt => ContainerRole::Clause,
                        LegalMarkerKind::Podpunkt => ContainerRole::Subitem,
                        _ => ContainerRole::Heading,
                    },
                    Some(x.text_span()),
                )
            })
        } else {
            None
        };
        if let Some((role, heading)) = role {
            let cid = ContainerId::parse(&format!("container-{i}")).unwrap();
            let parent = stack
                .last()
                .map(|(_, p)| p.clone())
                .or(Some(root_id.clone()));
            let designation =
                extract_hierarchy(b).map(|h| format!("{}:{}", h.level().as_str(), h.number()));
            containers.push(StructuralContainerNode {
                container_id: cid.clone(),
                role,
                designation,
                heading_anchor: heading,
                parent_id: parent.clone(),
                source_evidence: b.source_location().clone(),
            });
            if let Some(p) = parent {
                edges.push(StructureEdge {
                    from: p.as_str().into(),
                    to: cid.as_str().into(),
                    relation: StructureEdgeRelation::ParentOf,
                    evidence: anchor,
                    status: StructureEdgeStatus::Accepted,
                });
            }
            stack.push((i, cid));
        }
        let parent = stack
            .last()
            .map(|(_, p)| p.clone())
            .unwrap_or(root_id.clone());
        edges.push(StructureEdge {
            from: bid.as_str().into(),
            to: parent.as_str().into(),
            relation: StructureEdgeRelation::ContainedIn,
            evidence: anchor,
            status: StructureEdgeStatus::Accepted,
        });
    }
    Ok(DocumentStructureIndex {
        version,
        source_blocks,
        containers,
        edges,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContextPhase {
    NotEvaluated,
    Requested,
    Queued,
    Resolving,
    Resolved,
    Partial,
    Conflicting,
    Unavailable,
    Cycle,
    Limit,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContextTransition {
    TypedContextRequestEmitted,
    RequestSchemaAndBudgetPass,
    DeterministicWorklistDispatch,
    UniqueAuthorizedClaimSet,
    MissingNoncriticalContext,
    IncompatibleAuthorizedClaims,
    IndexOrSidecarUnavailable,
    RepeatedDerivationPath,
    DeclaredBudgetReached,
}
impl ContextPhase {
    pub const fn transition(self, t: ContextTransition) -> Option<Self> {
        use ContextPhase::*;
        use ContextTransition::*;
        match (self, t) {
            (NotEvaluated, TypedContextRequestEmitted) => Some(Requested),
            (Requested, RequestSchemaAndBudgetPass) => Some(Queued),
            (Queued, DeterministicWorklistDispatch) => Some(Resolving),
            (Resolving, UniqueAuthorizedClaimSet) => Some(Resolved),
            (Resolving, MissingNoncriticalContext) => Some(Partial),
            (Resolving, IncompatibleAuthorizedClaims) => Some(Conflicting),
            (Resolving, IndexOrSidecarUnavailable) => Some(Unavailable),
            (Resolving, RepeatedDerivationPath) => Some(Cycle),
            (Resolving, DeclaredBudgetReached) => Some(Limit),
            _ => None,
        }
    }
    pub const fn is_terminal(self) -> bool {
        matches!(
            self,
            Self::Resolved
                | Self::Partial
                | Self::Conflicting
                | Self::Unavailable
                | Self::Cycle
                | Self::Limit
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ContextRequestKind {
    AncestorPath,
    AdjacentBlocks,
    OpenSeriesHead,
    ScopedAlias,
    CurrentDocumentRequisites,
    ExplicitAnchorLookup,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextRequest {
    kind: ContextRequestKind,
    document_version_ref: String,
    origin_frame_ref: FrameRef,
    requested_roles_or_fields: Vec<String>,
    structural_scope: Option<ContainerId>,
    explicit_key: Option<String>,
    path_so_far: Vec<String>,
    budget_remaining: usize,
    evidence_requirement: String,
}
impl ContextRequest {
    pub fn kind(&self) -> ContextRequestKind {
        self.kind
    }

    /// Creates a request with an explicit, bounded key. Empty keys are allowed
    /// only for operators which do not need one (for example ancestor_path).
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        kind: ContextRequestKind,
        document_version_ref: String,
        origin_frame_ref: FrameRef,
        requested_roles_or_fields: Vec<String>,
        structural_scope: Option<ContainerId>,
        explicit_key: Option<String>,
        path_so_far: Vec<String>,
        budget_remaining: usize,
        evidence_requirement: String,
    ) -> Self {
        Self {
            kind,
            document_version_ref,
            origin_frame_ref,
            requested_roles_or_fields,
            structural_scope,
            explicit_key,
            path_so_far,
            budget_remaining,
            evidence_requirement,
        }
    }

    pub fn current_document_requisites(origin: FrameRef, evidence: ThisRefGrammarEvidence) -> Self {
        Self {
            kind: ContextRequestKind::CurrentDocumentRequisites,
            document_version_ref: String::new(),
            origin_frame_ref: origin,
            requested_roles_or_fields: Vec::new(),
            structural_scope: None,
            explicit_key: None,
            path_so_far: Vec::new(),
            budget_remaining: 0,
            evidence_requirement: if evidence
                .contains(crate::current_requisites::RequisitesField::Type)
            {
                "authorized-fields".to_owned()
            } else {
                "grammar-evidence".to_owned()
            },
        }
    }

    pub fn memo_key(&self) -> MemoKey {
        MemoKey {
            document_version_ref: self.document_version_ref.clone(),
            request_kind: self.kind,
            origin_frame_ref: self.origin_frame_ref.clone(),
            explicit_key: self.explicit_key.clone(),
            structural_scope: self.structural_scope.clone(),
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ContextStatus {
    Resolved,
    Partial,
    Conflicting,
    Unavailable,
    Cycle,
    Limit,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContextClaimStatus {
    Explicit,
    Inherited,
    Conflicting,
    Unresolved,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextClaim {
    pub field: String,
    pub derivation: DerivationSource,
    pub source_node_ref: String,
    pub claim_status: ContextClaimStatus,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DerivationRelation {
    DerivedFrom,
    Supports,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DerivationEdge {
    pub from: String,
    pub to: String,
    pub relation: DerivationRelation,
    pub evidence: TextSpan,
    pub status: StructureEdgeStatus,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContextDiagnostic {
    MissingDocumentStructure,
    MissingCurrentRequisites,
    OpenSeriesWithoutHead,
    IncompatibleSeriesHead,
    CrossBlockContinuationAmbiguous,
    ScopedAliasAmbiguous,
    InheritedFieldConflict,
    ContextQueryLimitReached,
    UnresolvedAfterDocumentPass,
}
impl ContextDiagnostic {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MissingDocumentStructure => "missing_document_structure",
            Self::MissingCurrentRequisites => "missing_current_requisites",
            Self::OpenSeriesWithoutHead => "open_series_without_head",
            Self::IncompatibleSeriesHead => "incompatible_series_head",
            Self::CrossBlockContinuationAmbiguous => "cross_block_continuation_ambiguous",
            Self::ScopedAliasAmbiguous => "scoped_alias_ambiguous",
            Self::InheritedFieldConflict => "inherited_field_conflict",
            Self::ContextQueryLimitReached => "context_query_limit_reached",
            Self::UnresolvedAfterDocumentPass => "unresolved_after_document_pass",
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextResult {
    pub request_ref: String,
    pub status: ContextStatus,
    pub candidate_claims: Vec<ContextClaim>,
    pub source_anchors: Vec<TextSpan>,
    pub derivation_edges: Vec<DerivationEdge>,
    pub diagnostics: Vec<ContextDiagnostic>,
}

/// The stable identity used by the context memo table.  Budget counters and
/// traversal history are intentionally excluded: replaying the same typed
/// query in one document version must hit the same memo entry.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct MemoKey {
    pub document_version_ref: String,
    pub request_kind: ContextRequestKind,
    pub origin_frame_ref: FrameRef,
    pub explicit_key: Option<String>,
    pub structural_scope: Option<ContainerId>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ContextBudgets {
    pub adjacent_radius: usize,
    pub series_hops: usize,
    pub alias_candidates: usize,
    pub claims_per_field: usize,
    pub worklist_steps: usize,
}
impl Default for ContextBudgets {
    fn default() -> Self {
        Self {
            adjacent_radius: PROPOSED_MAX_ADJACENT_RADIUS,
            series_hops: PROPOSED_MAX_SERIES_HOPS,
            alias_candidates: PROPOSED_MAX_ALIAS_CANDIDATES,
            claims_per_field: PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD,
            worklist_steps: PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct ContextEnvironment<'a> {
    pub index: &'a DocumentStructureIndex,
    pub overlay: &'a DocumentAnalysisOverlay,
    pub requisites: Option<&'a crate::current_requisites::CurrentDocumentRequisites>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ContextRunStats {
    pub memo_hits: usize,
    pub steps_used: usize,
    pub terminal_distribution: BTreeMap<ContextStatus, usize>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextView {
    pub target_block_id: Option<BlockId>,
    pub target_local_anchor: Option<TextSpan>,
    pub document_version_ref: String,
    pub current_document_requisites_ref: Option<String>,
    pub ancestor_path: Vec<String>,
    pub adjacent_blocks: Vec<String>,
    pub open_series_frames: Vec<String>,
    pub scoped_aliases: Vec<String>,
    pub explicit_anchor_hits: Vec<String>,
    pub context_claims: Vec<ContextClaim>,
    pub sufficiency: ContextStatus,
    pub diagnostics: Vec<ContextDiagnostic>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextRunReport {
    pub results: BTreeMap<MemoKey, ContextResult>,
    pub views: Vec<ContextView>,
    pub stats: ContextRunStats,
}

/// Stateful only with respect to immutable memoized results.  The source
/// index, overlay and requisites are borrowed and are never altered.
pub struct ContextWorklist {
    budgets: ContextBudgets,
    memo: BTreeMap<MemoKey, ContextResult>,
}
impl ContextWorklist {
    pub fn new(budgets: ContextBudgets) -> Self {
        Self {
            budgets,
            memo: BTreeMap::new(),
        }
    }

    pub fn run<'a>(
        &mut self,
        environment: ContextEnvironment<'a>,
        requests: &[ContextRequest],
    ) -> ContextRunReport {
        let mut results = BTreeMap::new();
        let mut views = Vec::new();
        let mut stats = ContextRunStats::default();
        let mut ordered: Vec<&ContextRequest> = requests.iter().collect();
        ordered.sort_by_key(|request| request.memo_key());
        for request in ordered {
            let key = request.memo_key();
            let result = if let Some(cached) = self.memo.get(&key) {
                stats.memo_hits += 1;
                cached.clone()
            } else if stats.steps_used >= self.budgets.worklist_steps {
                limit_result(&key)
            } else if request
                .path_so_far
                .iter()
                .any(|part| part == &memo_label(&key))
                || request.path_so_far.len() > self.budgets.series_hops
                || request.path_so_far.len() > MAX_LINKING_PASSES
            {
                cycle_or_limit_result(&key, request.path_so_far.len() > MAX_LINKING_PASSES)
            } else {
                stats.steps_used += 1;
                let result = dispatch_leaf(&environment, request, &self.budgets, &key);
                self.memo.insert(key.clone(), result.clone());
                result
            };
            *stats
                .terminal_distribution
                .entry(result.status)
                .or_default() += 1;
            views.push(view_for(request, &environment, &result));
            results.insert(key, result);
        }
        ContextRunReport {
            results,
            views,
            stats,
        }
    }
}

fn memo_label(key: &MemoKey) -> String {
    format!(
        "{:?}:{}:{}",
        key.request_kind,
        key.origin_frame_ref.as_str(),
        key.explicit_key.as_deref().unwrap_or("")
    )
}
fn limit_result(key: &MemoKey) -> ContextResult {
    ContextResult {
        request_ref: memo_label(key),
        status: ContextStatus::Limit,
        candidate_claims: Vec::new(),
        source_anchors: Vec::new(),
        derivation_edges: Vec::new(),
        diagnostics: vec![ContextDiagnostic::ContextQueryLimitReached],
    }
}
fn cycle_or_limit_result(key: &MemoKey, linking_limit: bool) -> ContextResult {
    ContextResult {
        request_ref: memo_label(key),
        status: if linking_limit {
            ContextStatus::Limit
        } else {
            ContextStatus::Cycle
        },
        candidate_claims: Vec::new(),
        source_anchors: Vec::new(),
        derivation_edges: Vec::new(),
        diagnostics: vec![if linking_limit {
            ContextDiagnostic::ContextQueryLimitReached
        } else {
            ContextDiagnostic::UnresolvedAfterDocumentPass
        }],
    }
}

fn dispatch_leaf(
    environment: &ContextEnvironment<'_>,
    request: &ContextRequest,
    budgets: &ContextBudgets,
    key: &MemoKey,
) -> ContextResult {
    let outcome = match request.kind {
        ContextRequestKind::AncestorPath => BlockId::parse(request.origin_frame_ref.as_str())
            .ok()
            .map(|b| {
                environment
                    .index
                    .ancestor_path(&b)
                    .map(|path| LeafOutcome {
                        status: ContextStatus::Resolved,
                        candidates: path
                            .into_iter()
                            .map(|node| LeafCandidate {
                                node_ref: node.container_id().as_str().to_owned(),
                                evidence: node.heading_anchor().into_iter().collect(),
                                claims: Vec::new(),
                            })
                            .collect(),
                        diagnostics: Vec::new(),
                    })
                    .unwrap_or_else(|s| {
                        LeafOutcome::unavailable(if s == ContextStatus::Partial {
                            ContextDiagnostic::ContextQueryLimitReached
                        } else {
                            ContextDiagnostic::MissingDocumentStructure
                        })
                    })
            })
            .unwrap_or_else(|| {
                LeafOutcome::unavailable(ContextDiagnostic::MissingDocumentStructure)
            }),
        ContextRequestKind::AdjacentBlocks => BlockId::parse(request.origin_frame_ref.as_str())
            .ok()
            .map(|b| LeafOutcome {
                status: ContextStatus::Resolved,
                candidates: environment
                    .index
                    .adjacent_blocks(&b, budgets.adjacent_radius)
                    .into_iter()
                    .map(|node| LeafCandidate {
                        node_ref: node.block_id().as_str().to_owned(),
                        evidence: vec![node.local_anchor()],
                        claims: Vec::new(),
                    })
                    .collect(),
                diagnostics: Vec::new(),
            })
            .unwrap_or_else(|| {
                LeafOutcome::unavailable(ContextDiagnostic::MissingDocumentStructure)
            }),
        ContextRequestKind::OpenSeriesHead => FrameRef::parse(request.origin_frame_ref.as_str())
            .ok()
            .map(|f| open_series_head(environment.overlay, &f))
            .unwrap_or_else(|| {
                LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass)
            }),
        ContextRequestKind::ScopedAlias => request
            .structural_scope
            .as_ref()
            .zip(request.explicit_key.as_deref())
            .map(|(scope, alias)| scoped_alias(environment.overlay, alias, scope))
            .unwrap_or_else(|| {
                LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass)
            }),
        ContextRequestKind::CurrentDocumentRequisites => current_document_requisites(
            environment.requisites,
            ThisRefGrammarEvidence::new([]),
            &request.origin_frame_ref,
        ),
        ContextRequestKind::ExplicitAnchorLookup => request
            .explicit_key
            .as_deref()
            .and_then(|key| FrameRef::parse(key).ok())
            .map(|f| explicit_anchor_lookup(environment.overlay, f.as_str()))
            .unwrap_or_else(|| {
                LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass)
            }),
    };
    let mut claims = Vec::new();
    for candidate in &outcome.candidates {
        claims.extend(candidate.claims.clone());
    }
    claims.sort_by(|a, b| (&a.field, &a.source_node_ref).cmp(&(&b.field, &b.source_node_ref)));
    let mut diagnostics = outcome.diagnostics;
    if claims.len() > budgets.claims_per_field {
        claims.truncate(budgets.claims_per_field);
        diagnostics.push(ContextDiagnostic::ContextQueryLimitReached);
    }
    ContextResult {
        request_ref: memo_label(key),
        status: outcome.status,
        candidate_claims: claims,
        source_anchors: outcome
            .candidates
            .into_iter()
            .flat_map(|c| c.evidence)
            .collect(),
        derivation_edges: Vec::new(),
        diagnostics,
    }
}

/// Field-wise reducer: equal claims collapse, incompatible sources remain
/// visible and never become a proximity-selected winner.
pub fn reduce_context_results(results: &[ContextResult]) -> ContextResult {
    let mut claims = BTreeMap::<String, Vec<ContextClaim>>::new();
    let mut conflicting = false;
    let mut anchors = Vec::new();
    let mut diagnostics = Vec::new();
    for result in results {
        anchors.extend(result.source_anchors.iter().copied());
        diagnostics.extend(result.diagnostics.iter().copied());
        for claim in &result.candidate_claims {
            let field_claims = claims.entry(claim.field.clone()).or_default();
            if field_claims
                .iter()
                .any(|previous| previous.source_node_ref != claim.source_node_ref)
            {
                conflicting = true;
            }
            if !field_claims.iter().any(|previous| previous == claim) {
                field_claims.push(claim.clone());
                field_claims.sort_by(|a, b| a.source_node_ref.cmp(&b.source_node_ref));
            }
        }
    }
    let flattened_claims: Vec<ContextClaim> = claims.into_values().flatten().collect();
    let status = if conflicting {
        ContextStatus::Conflicting
    } else if flattened_claims.is_empty() {
        ContextStatus::Unavailable
    } else {
        ContextStatus::Resolved
    };
    ContextResult {
        request_ref: "reduced".to_owned(),
        status,
        candidate_claims: flattened_claims,
        source_anchors: anchors,
        derivation_edges: Vec::new(),
        diagnostics,
    }
}

fn view_for(
    request: &ContextRequest,
    environment: &ContextEnvironment<'_>,
    result: &ContextResult,
) -> ContextView {
    ContextView {
        target_block_id: BlockId::parse(request.origin_frame_ref.as_str()).ok(),
        target_local_anchor: None,
        document_version_ref: environment
            .index
            .version()
            .document_version_ref()
            .to_owned(),
        current_document_requisites_ref: environment
            .requisites
            .map(|r| r.document_version_ref().to_owned()),
        ancestor_path: Vec::new(),
        adjacent_blocks: Vec::new(),
        open_series_frames: result
            .candidate_claims
            .iter()
            .map(|c| c.source_node_ref.clone())
            .collect(),
        scoped_aliases: Vec::new(),
        explicit_anchor_hits: Vec::new(),
        context_claims: result.candidate_claims.clone(),
        sufficiency: result.status,
        diagnostics: result.diagnostics.clone(),
    }
}

/// [proposed] S04 bounded C4 smoke observed adjacent radius 2; 4 retains
/// at least 2x headroom. Evidence: `prd/migration/rust-evidence/m203-s04-context-baseline.json`.
pub const PROPOSED_MAX_ADJACENT_RADIUS: usize = 4;
/// [proposed] S04 bounded C4 smoke observed series hops 2; 4 retains at
/// least 2x headroom. Evidence: `prd/migration/rust-evidence/m203-s04-context-baseline.json`.
pub const PROPOSED_MAX_SERIES_HOPS: usize = 4;
/// [proposed] No aliases were observed in the bounded smoke; 8 is a
/// conservative non-zero budget with explicit headroom, not a corpus claim.
pub const PROPOSED_MAX_ALIAS_CANDIDATES: usize = 8;
/// [proposed] S04 bounded C4 smoke observed at most 4 claims per field; 8
/// retains 2x headroom. Evidence: `prd/migration/rust-evidence/m203-s04-context-baseline.json`.
pub const PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD: usize = 8;
/// [proposed] S04 bounded C4 smoke observed 32 worklist steps per document;
/// 64 retains 2x headroom. Evidence: `prd/migration/rust-evidence/m203-s04-context-baseline.json`.
pub const PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT: usize = 64;
pub const MAX_LINKING_PASSES: usize = 1;

/// Evidence-bearing node produced by the contextual layer.  These nodes are
/// additive: the source block, frame, and capture remain addressable in the
/// structure index and are never replaced by an overlay node.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeclaredAliasNode {
    pub alias_id: AliasId,
    pub wording: String,
    pub target_mention_ref: MentionRef,
    pub declaration_anchor: TextSpan,
    pub scope_container_id: ContainerId,
    pub status: StructureEdgeStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalGrammarFrameNode {
    pub frame_ref: FrameRef,
    pub block_id: BlockId,
    pub frame_kind: FrameKind,
    pub local_anchor: TextSpan,
    pub status: FrameStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LiteralMentionNode {
    pub mention_ref: MentionRef,
    pub block_id: BlockId,
    pub local_anchor: TextSpan,
    pub written_text: String,
    pub explicit_slots: Vec<String>,
    pub status: StructureEdgeStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ContextualEdgeKind {
    OpensSeries,
    ContinuesSeries,
    ClosesSeries,
    DeclaresAlias,
    AliasInScope,
    SuppliesRequisites,
    OwnsDesignation,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextualEdge {
    pub from: String,
    pub to: String,
    pub relation: ContextualEdgeKind,
    pub evidence: Vec<TextSpan>,
    pub confidence_class: ConfidenceClass,
    pub status: StructureEdgeStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ConfidenceClass {
    ExplicitEvidence,
    DerivedPath,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentAnalysisOverlay {
    version: DocumentVersionRef,
    aliases: Vec<DeclaredAliasNode>,
    frames: Vec<LocalGrammarFrameNode>,
    mentions: Vec<LiteralMentionNode>,
    edges: Vec<ContextualEdge>,
}
impl DocumentAnalysisOverlay {
    pub fn version(&self) -> &DocumentVersionRef {
        &self.version
    }
    pub fn aliases(&self) -> &[DeclaredAliasNode] {
        &self.aliases
    }
    pub fn frames(&self) -> &[LocalGrammarFrameNode] {
        &self.frames
    }
    pub fn mentions(&self) -> &[LiteralMentionNode] {
        &self.mentions
    }
    pub fn edges(&self) -> &[ContextualEdge] {
        &self.edges
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OverlayBuildError {
    UnknownBlock,
    MissingScope,
    InvalidCaptureSpan,
}
impl fmt::Display for OverlayBuildError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "document analysis overlay build failed: {:?}", self)
    }
}
impl std::error::Error for OverlayBuildError {}

/// Builds only derived, source-local nodes and edges.  In particular, no
/// node may contain a cross-block TextSpan; continuation edges carry the two
/// separate local frame anchors instead.
pub fn build_document_analysis_overlay(
    index: &DocumentStructureIndex,
    frames_per_block: &[(
        BlockId,
        Vec<CoordinatingFrame>,
        Vec<StructuralDesignationFrame>,
    )],
    captures_per_block: &[(BlockId, Vec<LawRef>)],
) -> Result<DocumentAnalysisOverlay, OverlayBuildError> {
    let mut overlay = DocumentAnalysisOverlay {
        version: index.version.clone(),
        aliases: Vec::new(),
        frames: Vec::new(),
        mentions: Vec::new(),
        edges: Vec::new(),
    };
    for (block_id, frames, designations) in frames_per_block {
        let source = index
            .source_blocks
            .iter()
            .find(|b| b.block_id == *block_id)
            .ok_or(OverlayBuildError::UnknownBlock)?;
        let scope = index
            .ancestor_path(block_id)
            .map_err(|_| OverlayBuildError::MissingScope)?;
        let scope_id = scope
            .first()
            .map(|c| c.container_id.clone())
            .ok_or(OverlayBuildError::MissingScope)?;
        for (n, frame) in frames.iter().enumerate() {
            let frame_ref = FrameRef::parse(&format!("{}-frame-{n}", block_id.as_str()))
                .map_err(|_| OverlayBuildError::InvalidCaptureSpan)?;
            overlay.frames.push(LocalGrammarFrameNode {
                frame_ref: frame_ref.clone(),
                block_id: block_id.clone(),
                frame_kind: frame.frame_kind,
                local_anchor: frame.local_anchor,
                status: frame.status,
            });
            let frame_node = frame_ref.as_str().to_owned();
            let relation = if frame.continuation {
                ContextualEdgeKind::ContinuesSeries
            } else {
                ContextualEdgeKind::OpensSeries
            };
            overlay.edges.push(ContextualEdge {
                from: frame_node,
                to: block_id.as_str().to_owned(),
                relation,
                evidence: vec![frame.local_anchor],
                confidence_class: ConfidenceClass::ExplicitEvidence,
                status: if frame.status == FrameStatus::Ambiguous {
                    StructureEdgeStatus::Conflicting
                } else {
                    StructureEdgeStatus::Proposed
                },
            });
        }
        for (n, frame) in designations.iter().enumerate() {
            let frame_ref = FrameRef::parse(&format!("{}-designation-{n}", block_id.as_str()))
                .map_err(|_| OverlayBuildError::InvalidCaptureSpan)?;
            overlay.frames.push(LocalGrammarFrameNode {
                frame_ref: frame_ref.clone(),
                block_id: block_id.clone(),
                frame_kind: FrameKind::StructuralDesignation,
                local_anchor: frame.local_anchor,
                status: frame.status,
            });
            overlay.edges.push(ContextualEdge {
                from: frame_ref.as_str().to_owned(),
                to: scope_id.as_str().to_owned(),
                relation: ContextualEdgeKind::OwnsDesignation,
                evidence: vec![frame.local_anchor],
                confidence_class: ConfidenceClass::DerivedPath,
                status: StructureEdgeStatus::Proposed,
            });
        }
        let _ = source;
    }
    for (block_id, captures) in captures_per_block {
        if index.source_blocks.iter().all(|b| b.block_id != *block_id) {
            return Err(OverlayBuildError::UnknownBlock);
        }
        for (n, capture) in captures.iter().enumerate() {
            let mention_ref = MentionRef::parse(&format!("{}-mention-{n}", block_id.as_str()))
                .map_err(|_| OverlayBuildError::InvalidCaptureSpan)?;
            overlay.mentions.push(LiteralMentionNode {
                mention_ref: mention_ref.clone(),
                block_id: block_id.clone(),
                local_anchor: capture.span,
                written_text: capture.pattern_id.clone(),
                explicit_slots: capture_slots(capture),
                status: StructureEdgeStatus::Proposed,
            });
        }
    }
    // A head is accepted only when there is exactly one candidate.  No
    // proximity tie-break is applied; competing candidates stay visible.
    let act_frames: Vec<_> = overlay
        .frames
        .iter()
        .filter(|f| f.frame_kind == FrameKind::ActRequisites)
        .collect();
    for tail in act_frames
        .iter()
        .filter(|f| f.status != FrameStatus::Rejected)
    {
        let candidates: Vec<_> = act_frames
            .iter()
            .filter(|head| head.frame_ref != tail.frame_ref && head.block_id != tail.block_id)
            .collect();
        if candidates.len() == 1 && tail.local_anchor.start() > candidates[0].local_anchor.start() {
            overlay.edges.push(ContextualEdge {
                from: candidates[0].frame_ref.as_str().to_owned(),
                to: tail.frame_ref.as_str().to_owned(),
                relation: ContextualEdgeKind::ContinuesSeries,
                evidence: vec![candidates[0].local_anchor, tail.local_anchor],
                confidence_class: ConfidenceClass::DerivedPath,
                status: StructureEdgeStatus::Proposed,
            });
        } else if candidates.len() > 1 {
            for head in candidates {
                overlay.edges.push(ContextualEdge {
                    from: head.frame_ref.as_str().to_owned(),
                    to: tail.frame_ref.as_str().to_owned(),
                    relation: ContextualEdgeKind::ContinuesSeries,
                    evidence: vec![head.local_anchor, tail.local_anchor],
                    confidence_class: ConfidenceClass::DerivedPath,
                    status: StructureEdgeStatus::Conflicting,
                });
            }
        }
    }
    Ok(overlay)
}

fn capture_slots(capture: &LawRef) -> Vec<String> {
    let mut slots = Vec::new();
    if capture.slots.date.is_some() {
        slots.push("date".to_owned());
    }
    if capture.slots.doc_no.is_some() {
        slots.push("doc_no".to_owned());
    }
    if capture.slots.law_code.is_some() {
        slots.push("law_code".to_owned());
    }
    slots
}

/// Detects the deliberately closed Russian declaration surface.  The caller
/// supplies the containing scope; the parser never performs similarity search.
pub fn detect_declared_aliases(text: &str, scope: ContainerId) -> Vec<DeclaredAliasNode> {
    let mut out = Vec::new();
    for marker in ["(далее — ", "(далее - "] {
        let mut from = 0;
        while let Some(relative) = text[from..].find(marker) {
            let start = from + relative;
            let value_start = start + marker.len();
            let Some(end_rel) = text[value_start..].find(')') else {
                break;
            };
            let end = value_start + end_rel;
            let wording = text[value_start..end].trim();
            if !wording.is_empty() {
                if let (Ok(anchor), Ok(alias_id), Ok(mention)) = (
                    TextSpan::try_new(start, end + 1),
                    AliasId::parse(&format!("alias-{start}")),
                    MentionRef::parse(&format!("alias-target-{start}")),
                ) {
                    out.push(DeclaredAliasNode {
                        alias_id,
                        wording: wording.to_owned(),
                        target_mention_ref: mention,
                        declaration_anchor: anchor,
                        scope_container_id: scope.clone(),
                        status: StructureEdgeStatus::Accepted,
                    });
                }
            }
            from = end + 1;
        }
    }
    out
}

/// Detect the closed ThisRef surface and return exact local spans. The
/// sidecar proof itself remains `current_requisites::ThisRefGrammarEvidence`.
pub fn detect_this_ref_grammar(text: &str) -> Vec<TextSpan> {
    [
        "настоящего Федерального закона",
        "настоящего Закона",
        "настоящего приказа",
        "настоящего Порядка",
        "настоящего положения",
        "настоящей статьи",
    ]
    .iter()
    .flat_map(|surface| {
        text.match_indices(surface)
            .filter_map(move |(start, _)| TextSpan::try_new(start, start + surface.len()).ok())
    })
    .collect()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LeafCandidate {
    pub node_ref: String,
    pub evidence: Vec<TextSpan>,
    pub claims: Vec<ContextClaim>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LeafOutcome {
    pub status: ContextStatus,
    pub candidates: Vec<LeafCandidate>,
    pub diagnostics: Vec<ContextDiagnostic>,
}
impl LeafOutcome {
    fn unavailable(diagnostic: ContextDiagnostic) -> Self {
        Self {
            status: ContextStatus::Unavailable,
            candidates: Vec::new(),
            diagnostics: vec![diagnostic],
        }
    }
    fn partial(diagnostic: ContextDiagnostic) -> Self {
        Self {
            status: ContextStatus::Partial,
            candidates: Vec::new(),
            diagnostics: vec![diagnostic],
        }
    }
}

/// Resolve a series head only when the overlay proves one unique candidate.
pub fn open_series_head(overlay: &DocumentAnalysisOverlay, frame_ref: &FrameRef) -> LeafOutcome {
    let candidates: Vec<_> = overlay
        .edges
        .iter()
        .filter(|edge| {
            edge.relation == ContextualEdgeKind::ContinuesSeries
                && edge.to == frame_ref.as_str()
                && edge.status != StructureEdgeStatus::Rejected
        })
        .collect();
    if candidates.is_empty() {
        return LeafOutcome::partial(ContextDiagnostic::OpenSeriesWithoutHead);
    }
    if candidates
        .iter()
        .any(|e| e.status == StructureEdgeStatus::Conflicting)
    {
        return LeafOutcome {
            status: ContextStatus::Conflicting,
            candidates: candidates
                .into_iter()
                .map(|e| LeafCandidate {
                    node_ref: e.from.clone(),
                    evidence: e.evidence.clone(),
                    claims: Vec::new(),
                })
                .collect(),
            diagnostics: vec![ContextDiagnostic::IncompatibleSeriesHead],
        };
    }
    if candidates.len() != 1 {
        return LeafOutcome::partial(ContextDiagnostic::OpenSeriesWithoutHead);
    }
    let edge = candidates[0];
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: vec![LeafCandidate {
            node_ref: edge.from.clone(),
            evidence: edge.evidence.clone(),
            claims: Vec::new(),
        }],
        diagnostics: Vec::new(),
    }
}

/// Keep aliases confined to the container in which they were declared.
pub fn scoped_alias(
    overlay: &DocumentAnalysisOverlay,
    alias_key: &str,
    scope: &ContainerId,
) -> LeafOutcome {
    let candidates: Vec<_> = overlay
        .aliases
        .iter()
        .filter(|a| a.wording == alias_key && a.scope_container_id == *scope)
        .collect();
    if candidates.is_empty() {
        return LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass);
    }
    if candidates.len() > 1 {
        return LeafOutcome::partial(ContextDiagnostic::ScopedAliasAmbiguous);
    }
    let alias = candidates[0];
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: vec![LeafCandidate {
            node_ref: alias.target_mention_ref.as_str().to_owned(),
            evidence: vec![alias.declaration_anchor],
            claims: Vec::new(),
        }],
        diagnostics: Vec::new(),
    }
}

/// Exact designation lookup; wording equality is intentional and forward
/// references are not discarded by block order.
pub fn explicit_anchor_lookup(
    overlay: &DocumentAnalysisOverlay,
    explicit_key: &str,
) -> LeafOutcome {
    let candidates: Vec<_> = overlay
        .frames
        .iter()
        .filter(|f| f.frame_ref.as_str() == explicit_key)
        .collect();
    if candidates.is_empty() {
        return LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass);
    }
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: candidates
            .into_iter()
            .map(|f| LeafCandidate {
                node_ref: f.frame_ref.as_str().to_owned(),
                evidence: vec![f.local_anchor],
                claims: Vec::new(),
            })
            .collect(),
        diagnostics: Vec::new(),
    }
}

/// Authorize current-document requisites through the sidecar guard.  No
/// sidecar means unavailable; a present but incomplete sidecar is partial.
pub fn current_document_requisites(
    requisites: Option<&crate::current_requisites::CurrentDocumentRequisites>,
    evidence: ThisRefGrammarEvidence,
    origin: &FrameRef,
) -> LeafOutcome {
    let Some(sidecar) = requisites else {
        return LeafOutcome::unavailable(ContextDiagnostic::MissingCurrentRequisites);
    };
    if !sidecar.authorize_this_document_reference(evidence) {
        return LeafOutcome::partial(ContextDiagnostic::InheritedFieldConflict);
    }
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: vec![LeafCandidate {
            node_ref: origin.as_str().to_owned(),
            evidence: Vec::new(),
            claims: vec![ContextClaim {
                field: "current_document_requisites".to_owned(),
                derivation: DerivationSource::AuthorizedCurrentDocumentRequisites,
                source_node_ref: origin.as_str().to_owned(),
                claim_status: ContextClaimStatus::Inherited,
            }],
        }],
        diagnostics: Vec::new(),
    }
}

pub fn supplies_requisites(index: &DocumentStructureIndex, container: &ContainerId) -> LeafOutcome {
    let Some(node) = index
        .containers
        .iter()
        .find(|c| c.container_id == *container && c.role == ContainerRole::RequisitesBlock)
    else {
        return LeafOutcome::unavailable(ContextDiagnostic::MissingCurrentRequisites);
    };
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: vec![LeafCandidate {
            node_ref: node.container_id.as_str().to_owned(),
            evidence: node.heading_anchor.into_iter().collect(),
            claims: Vec::new(),
        }],
        diagnostics: Vec::new(),
    }
}

pub fn owns_designation(overlay: &DocumentAnalysisOverlay, frame_ref: &FrameRef) -> LeafOutcome {
    let candidates: Vec<_> = overlay
        .edges
        .iter()
        .filter(|e| {
            e.from == frame_ref.as_str() && e.relation == ContextualEdgeKind::OwnsDesignation
        })
        .collect();
    if candidates.is_empty() {
        return LeafOutcome::unavailable(ContextDiagnostic::UnresolvedAfterDocumentPass);
    }
    LeafOutcome {
        status: ContextStatus::Resolved,
        candidates: candidates
            .into_iter()
            .map(|e| LeafCandidate {
                node_ref: e.to.clone(),
                evidence: e.evidence.clone(),
                claims: Vec::new(),
            })
            .collect(),
        diagnostics: Vec::new(),
    }
}
