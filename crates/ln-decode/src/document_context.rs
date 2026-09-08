//! Bounded, source-evidence-only document context (D385/D386).
//!
//! This module deliberately exposes a closed structural vocabulary.  It does
//! not create semantic claims, aliases, or cross-block text spans.

use std::collections::BTreeSet;
use std::fmt;

use crate::current_requisites::ThisRefGrammarEvidence;
use crate::domain::{ParagraphStyle, ParsedBlock, SourceLocation, TextSpan};
use crate::hierarchy::extract_hierarchy;
use crate::local_grammar::DerivationSource;
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
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
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
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

pub const PROPOSED_MAX_ADJACENT_RADIUS: usize = 2;
pub const PROPOSED_MAX_SERIES_HOPS: usize = 2;
pub const PROPOSED_MAX_ALIAS_CANDIDATES: usize = 4;
pub const PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD: usize = 4;
pub const PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT: usize = 32;
pub const MAX_LINKING_PASSES: usize = 1;
