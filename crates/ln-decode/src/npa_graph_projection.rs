//! S07 graph-projection consumer over the saved `npa-analysis` JSONL
//! (M223 / S07 / T03).
//!
//! Executable core of
//! `prd/architecture/intermediate-source-consumer-acceptance-contract.md`
//! (`npa_graph_projection`, §3). The module turns the **saved `npa-analysis`
//! JSONL** into a typed graph of fragments, members, classifications and
//! relations whose every node/edge/member key is the **composite document
//! identity** `SourceIdentity ⊕ DocumentVersionRef` — never a bare local
//! `tN` / `eN` / `member_id`, which are local to one document and collide
//! across the corpus.
//!
//! # Consumers without XML re-parse
//!
//! The consumer reads only the materialized JSONL layer: the artifact is
//! reconstructed through [`read_back_npa_analysis`] (the S03 read-back of the
//! seven families) and the `document` record's own identity fields are parsed
//! with the strict JSON extractor. There is **no** `quick_xml`, no `capture`,
//! and no byte re-parse anywhere on the read path; the source XML is never
//! opened and the source package is never required.
//!
//! # Graph document identity (acceptance contract §6)
//!
//! The identity is the composite pinned by the analysis contract §4.1/§4.2 and
//! represented in code by the frozen primitives
//! [`crate::analysis_source_mapping::SourceIdentity`] and
//! [`crate::document_context::DocumentVersionRef`]:
//!
//! * `SourceIdentity` — `source_sha256` (copied from the parent manifest, never
//!   recomputed) + `source_bytes` + `parent_schema` + `records_seal_hash` +
//!   `manifest_hash`; integrity evidence, not authenticity;
//! * `DocumentVersionRef` — the triple (`document_version_ref`,
//!   `source_revision`, `decoder_profile`).
//!
//! Binding rules:
//!
//! 1. All records in one unit belong to exactly one document version: the
//!    envelope's own manifest identity.
//! 2. Two units sharing `document_version_ref` but differing in
//!    `source_revision` / `decoder_profile` are different versions and must not
//!    be merged ([`GraphErrorKind::DocumentVersionMismatch`]).
//! 3. A record citing a fragment (or member) whose parent identity differs from
//!    the unit's pinned identity is refused ([`GraphErrorKind::CrossDocument`] /
//!    [`GraphErrorKind::SourceIdentityMismatch`]) and is **never rebased** onto
//!    the unit's source.
//! 4. **Repeat import is idempotent.** Importing the same JSONL twice into the
//!    same graph produces byte-identical node/edge counts and no duplicates: an
//!    already-present identity key is a no-op, not a second node.
//! 5. Cross-document relations remain out of scope: a relation/classification
//!    endpoint absent from the envelope is a closed [`GraphErrorKind::CrossDocument`]
//!    refusal, never a silent rebase.
//!
//! Machine-readable consumer model (T06 parses this block; keep one entry per
//! line):
//!
//! ```text
//! <!-- consumer-model:npa_graph_projection:begin -->
//! graph_identity:SourceIdentity
//! graph_identity:DocumentVersionRef
//! graph_identity:composite_source_identity_xor_document_version_ref
//! graph_node:member
//! graph_node:fragment
//! graph_node:classification
//! graph_edge:relation
//! graph_refusal:cross_document
//! graph_refusal:source_identity_mismatch
//! graph_refusal:document_version_mismatch
//! graph_refusal:unknown_fragment
//! <!-- consumer-model:npa_graph_projection:end -->
//! ```
//!
//! # Non-claims
//!
//! This is a bounded structural consumer. It asserts document structure and
//! identity, **not** legal authority, legal completeness, or normative citation
//! resolution; its `kind` labels are working labels. It is not authenticity (a
//! pin is integrity evidence), not normalization, not physical pagination, and
//! not an R1000 closure artifact (R1000 stays `active/unclosed`). It is
//! serialization-free: no `serde`, no JSON writer. Decoded legal text is never
//! logged or interpolated into diagnostics; only ids, closed codes and counters
//! appear in errors.

use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use crate::analysis_source_mapping::{MappingRefusal, SourceIdentity};
use crate::document_context::DocumentVersionRef;
use crate::npa_analysis_verify::{
    AnalysisReadback, ReadbackManifest, ReadbackRef, read_back_npa_analysis,
};
use crate::npa_analysis_wire::{AnalysisWireError, FAMILY_DOCUMENT, JsonFields, string_field};
use crate::reader_contract::FragmentRef;

// ------------------------------------------------------------- constants #

/// Pinned graph-projection profile id.
pub const NPA_GRAPH_PROJECTION_PROFILE: &str = "npa_graph_projection/v1";

/// The composite identity components (consumer-model block).
pub const NPA_GRAPH_IDENTITY_COMPONENTS: [&str; 3] = [
    "SourceIdentity",
    "DocumentVersionRef",
    "composite_source_identity_xor_document_version_ref",
];

/// The three projected node kinds, in pinned order (consumer-model block).
pub const NPA_GRAPH_NODE_KINDS: [GraphNodeKind; 3] = [
    GraphNodeKind::Member,
    GraphNodeKind::Fragment,
    GraphNodeKind::Classification,
];

/// The one projected edge kind (consumer-model block).
pub const NPA_GRAPH_EDGE_KINDS: [&str; 1] = ["relation"];

/// The four closed graph refusals, in pinned order (consumer-model block).
pub const NPA_GRAPH_REFUSALS: [&str; 4] = [
    "cross_document",
    "source_identity_mismatch",
    "document_version_mismatch",
    "unknown_fragment",
];

// ----------------------------------------------------------------- errors #

/// Closed graph-projection error vocabulary. Every failure is a typed refusal,
/// never a partial or clamped graph.
///
/// The four `graph_refusal:` tokens of the consumer-model block are
/// [`GraphErrorKind::CrossDocument`], [`GraphErrorKind::SourceIdentityMismatch`],
/// [`GraphErrorKind::DocumentVersionMismatch`] and
/// [`GraphErrorKind::UnknownFragment`]; [`GraphErrorKind::EnvelopeUnreadable`]
/// is the input-admission arm for an artifact that is not a readable analysis
/// envelope (it is not a model refusal).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum GraphErrorKind {
    /// The analysis JSONL could not be read back (malformed/structural).
    EnvelopeUnreadable,
    /// A record or a pinned identity names another document.
    CrossDocument,
    /// The source identity (sha / bytes / schema / seals) differs from the pin.
    SourceIdentityMismatch,
    /// The version triple differs for the same `document_version_ref`.
    DocumentVersionMismatch,
    /// A span cites a fragment absent from the envelope.
    UnknownFragment,
}

impl GraphErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            GraphErrorKind::EnvelopeUnreadable => "envelope_unreadable",
            GraphErrorKind::CrossDocument => "cross_document",
            GraphErrorKind::SourceIdentityMismatch => "source_identity_mismatch",
            GraphErrorKind::DocumentVersionMismatch => "document_version_mismatch",
            GraphErrorKind::UnknownFragment => "unknown_fragment",
        }
    }

    /// True when the kind is one of the four model refusals.
    pub const fn is_model_refusal(self) -> bool {
        !matches!(self, GraphErrorKind::EnvelopeUnreadable)
    }
}

impl fmt::Display for GraphErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed graph-projection error. Carries no serialization dependency and never
/// embeds decoded legal text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphError {
    kind: GraphErrorKind,
    detail: String,
}

impl GraphError {
    /// Builds an error from a class and a diagnostic detail.
    pub fn new(kind: GraphErrorKind, detail: impl Into<String>) -> Self {
        GraphError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> GraphErrorKind {
        self.kind
    }

    /// Diagnostic detail (never parsed; ids and closed codes only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for GraphError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for GraphError {}

fn map_wire_error(error: AnalysisWireError) -> GraphError {
    GraphError::new(GraphErrorKind::EnvelopeUnreadable, error.kind().as_str())
}

// ------------------------------------------------------------- identity #

/// The verified composite document identity `SourceIdentity ⊕
/// DocumentVersionRef` (acceptance contract §6 / this contract §3). Fragment
/// ids (`tN`, `eN`) and member ids are local to one document and are never used
/// as a graph key on their own.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct GraphIdentity {
    /// Pinned parent evidence identity (sha / bytes / schema / seals).
    pub source: SourceIdentity,
    /// Pinned document-version triple.
    pub version: DocumentVersionRef,
}

impl GraphIdentity {
    /// Builds a graph identity from its two halves.
    pub const fn new(source: SourceIdentity, version: DocumentVersionRef) -> Self {
        GraphIdentity { source, version }
    }

    /// Builds the identity from the read-back manifest: the parent evidence pin
    /// and the document-version triple.
    ///
    /// The `source_sha256` / seals are copied verbatim from the wire — never
    /// recomputed — and are integrity evidence, not authenticity.
    pub fn from_readback(manifest: &ReadbackManifest) -> Result<Self, GraphError> {
        let source = SourceIdentity::try_new(
            manifest.source_sha256.clone(),
            manifest.source_bytes,
            manifest.parent_schema.clone(),
            manifest.parent_records_seal_hash.clone(),
            manifest.parent_manifest_hash.clone(),
        )
        .map_err(|error: MappingRefusal| {
            GraphError::new(GraphErrorKind::EnvelopeUnreadable, error.kind().as_str())
        })?;
        let version = DocumentVersionRef::try_new(
            manifest.document_version_ref.clone(),
            manifest.source_revision.clone(),
            manifest.decoder_profile.clone(),
        )
        .map_err(|error| GraphError::new(GraphErrorKind::EnvelopeUnreadable, error.to_string()))?;
        Ok(GraphIdentity { source, version })
    }
}

/// Deterministic total order over the composite identity, so the graph keys
/// live in a `BTreeMap` and repeat import is byte-stable.
impl Ord for GraphIdentity {
    fn cmp(&self, other: &Self) -> Ordering {
        let this = (
            &self.source.source_sha256,
            self.source.source_bytes,
            &self.source.parent_schema,
            &self.source.records_seal_hash,
            &self.source.manifest_hash,
            self.version.document_version_ref(),
            self.version.source_revision(),
            self.version.decoder_profile(),
        );
        let that = (
            &other.source.source_sha256,
            other.source.source_bytes,
            &other.source.parent_schema,
            &other.source.records_seal_hash,
            &other.source.manifest_hash,
            other.version.document_version_ref(),
            other.version.source_revision(),
            other.version.decoder_profile(),
        );
        this.cmp(&that)
    }
}

impl PartialOrd for GraphIdentity {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

// ------------------------------------------------------------------ keys #

/// The projected node kinds (consumer-model block).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum GraphNodeKind {
    /// A declared fragment (`tN`).
    Fragment,
    /// A linked member (`ml:<member_id>`).
    Member,
    /// A classification (`c:<member_id>`).
    Classification,
}

impl GraphNodeKind {
    /// Closed string form.
    pub const fn as_str(self) -> &'static str {
        match self {
            GraphNodeKind::Fragment => "fragment",
            GraphNodeKind::Member => "member",
            GraphNodeKind::Classification => "classification",
        }
    }
}

/// The document-local half of a node key. It is **never** used on its own: it is
/// always paired with a [`GraphIdentity`] in a [`GraphNodeKey`].
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum LocalNodeKey {
    /// A fragment id local to the document.
    Fragment(FragmentRef),
    /// A linked-member id local to the document.
    Member(u64),
    /// A classified member id local to the document.
    Classification(u64),
}

impl LocalNodeKey {
    /// The node kind this local key denotes.
    pub const fn kind(&self) -> GraphNodeKind {
        match self {
            LocalNodeKey::Fragment(_) => GraphNodeKind::Fragment,
            LocalNodeKey::Member(_) => GraphNodeKind::Member,
            LocalNodeKey::Classification(_) => GraphNodeKind::Classification,
        }
    }

    /// A closed, human-readable token (`fragment:tN` / `member:3`).
    pub fn token(&self) -> String {
        match self {
            LocalNodeKey::Fragment(fragment) => format!("fragment:{}", fragment.as_str()),
            LocalNodeKey::Member(id) => format!("member:{id}"),
            LocalNodeKey::Classification(id) => format!("classification:{id}"),
        }
    }
}

/// The composite node key: `document identity ⊕ local id`. This is the only key
/// the graph stores, so two documents never collide on a bare `tN` / member id.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct GraphNodeKey {
    /// The owning document identity.
    pub identity: GraphIdentity,
    /// The document-local id.
    pub local: LocalNodeKey,
}

impl GraphNodeKey {
    /// Builds a composite node key.
    pub const fn new(identity: GraphIdentity, local: LocalNodeKey) -> Self {
        GraphNodeKey { identity, local }
    }

    /// The projected node kind.
    pub const fn kind(&self) -> GraphNodeKind {
        self.local.kind()
    }
}

/// The composite edge key: `document identity ⊕ relation ref` (`r:<index>`).
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct GraphEdgeKey {
    /// The owning document identity.
    pub identity: GraphIdentity,
    /// The family-local relation ref.
    pub relation_ref: String,
}

// ----------------------------------------------------------------- nodes #

/// One projected graph node. Every variant carries its composite
/// [`GraphNodeKey`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GraphNode {
    /// A declared fragment node (count/hash-only, no inline text).
    Fragment {
        /// The composite key.
        key: GraphNodeKey,
        /// Declared decoded byte length.
        byte_length: u64,
        /// Declared sha256 of the decoded bytes.
        content_sha256: String,
    },
    /// A linked-member node.
    Member {
        /// The composite key.
        key: GraphNodeKey,
        /// The family-local ref (`ml:<member_id>`).
        reference: String,
        /// The member's own anchor (a fragment-qualified span or a refusal).
        evidence: ReadbackRef,
    },
    /// A classification node, linked to its member node by composite key.
    Classification {
        /// The composite key.
        key: GraphNodeKey,
        /// The family-local ref (`c:<member_id>`).
        reference: String,
        /// The composite key of the classified member node.
        member: GraphNodeKey,
    },
}

impl GraphNode {
    /// The composite key.
    pub const fn key(&self) -> &GraphNodeKey {
        match self {
            GraphNode::Fragment { key, .. }
            | GraphNode::Member { key, .. }
            | GraphNode::Classification { key, .. } => key,
        }
    }

    /// The node kind.
    pub const fn kind(&self) -> GraphNodeKind {
        match self {
            GraphNode::Fragment { .. } => GraphNodeKind::Fragment,
            GraphNode::Member { .. } => GraphNodeKind::Member,
            GraphNode::Classification { .. } => GraphNodeKind::Classification,
        }
    }
}

/// One projected relation edge. Both endpoints are **composite** node keys, so
/// an endpoint is never a bare member id.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphEdge {
    /// The composite edge key.
    pub key: GraphEdgeKey,
    /// Closed relation kind token.
    pub kind: String,
    /// The composite key of the source member node.
    pub from: GraphNodeKey,
    /// The composite key of the target member node.
    pub to: GraphNodeKey,
}

// ---------------------------------------------------------------- counts #

/// Projected graph counts, split by kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct GraphCounts {
    /// Fragment nodes.
    pub fragments: usize,
    /// Member nodes.
    pub members: usize,
    /// Classification nodes.
    pub classifications: usize,
    /// Relation edges.
    pub relations: usize,
}

impl GraphCounts {
    /// Total projected nodes.
    pub const fn nodes(&self) -> usize {
        self.fragments + self.members + self.classifications
    }

    /// Total projected edges.
    pub const fn edges(&self) -> usize {
        self.relations
    }
}

/// Per-unit counts recorded for a successfully imported document version.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct UnitSummary {
    /// Fragment nodes contributed by the unit.
    pub fragments: usize,
    /// Member nodes contributed by the unit.
    pub members: usize,
    /// Classification nodes contributed by the unit.
    pub classifications: usize,
    /// Relation edges contributed by the unit.
    pub relations: usize,
}

/// The outcome of one import.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ImportReport {
    /// The imported unit's composite identity.
    pub identity: GraphIdentity,
    /// True when the same identity key was already present (idempotent no-op).
    pub already_present: bool,
    /// Nodes actually inserted by this import (0 on a repeat import).
    pub added_nodes: usize,
    /// Edges actually inserted by this import (0 on a repeat import).
    pub added_edges: usize,
    /// The graph counts after the import.
    pub counts: GraphCounts,
}

// ----------------------------------------------------------------- graph #

/// A corpus graph keyed by composite document identity. Re-importing the same
/// document version is a no-op (idempotent); a same-`document_version_ref`
/// conflict is a closed refusal.
#[derive(Debug, Clone, Default)]
pub struct NpaGraph {
    nodes: BTreeMap<GraphNodeKey, GraphNode>,
    edges: BTreeMap<GraphEdgeKey, GraphEdge>,
    units: BTreeMap<GraphIdentity, UnitSummary>,
}

impl NpaGraph {
    /// A new empty graph.
    pub fn new() -> Self {
        NpaGraph::default()
    }

    /// Imports one `npa-analysis` JSONL artifact, self-identifying from its
    /// manifest. A repeat import of the same document version is a no-op.
    pub fn import(&mut self, artifact: &str) -> Result<ImportReport, GraphError> {
        self.import_with(artifact, None)
    }

    /// Imports one artifact while asserting the caller's pinned identity (the
    /// "unit's pinned identity"). A unit belonging to a different
    /// `document_version_ref` is [`GraphErrorKind::CrossDocument`]; a differing
    /// source identity is [`GraphErrorKind::SourceIdentityMismatch`]; a
    /// differing version triple is [`GraphErrorKind::DocumentVersionMismatch`].
    pub fn import_pinned(
        &mut self,
        artifact: &str,
        pinned: &GraphIdentity,
    ) -> Result<ImportReport, GraphError> {
        self.import_with(artifact, Some(pinned))
    }

    fn import_with(
        &mut self,
        artifact: &str,
        pinned: Option<&GraphIdentity>,
    ) -> Result<ImportReport, GraphError> {
        let unit = project_unit(artifact, pinned)?;

        // Rule 2 / rule 3: a same-`document_version_ref` unit must agree on the
        // source identity and the version triple, or the merge is refused.
        for existing in self.units.keys() {
            if existing.version.document_version_ref()
                != unit.identity.version.document_version_ref()
            {
                continue;
            }
            if existing.source != unit.identity.source {
                return Err(GraphError::new(
                    GraphErrorKind::SourceIdentityMismatch,
                    format!(
                        "document_version_ref {} already pinned to a different source identity",
                        unit.identity.version.document_version_ref()
                    ),
                ));
            }
            if existing.version != unit.identity.version {
                return Err(GraphError::new(
                    GraphErrorKind::DocumentVersionMismatch,
                    format!(
                        "document_version_ref {} already pinned to a different version triple",
                        unit.identity.version.document_version_ref()
                    ),
                ));
            }
        }

        let already_present = self.units.contains_key(&unit.identity);
        let mut added_nodes = 0usize;
        for (key, node) in unit.nodes {
            if self.nodes.insert(key, node).is_none() {
                added_nodes += 1;
            }
        }
        let mut added_edges = 0usize;
        for (key, edge) in unit.edges {
            if self.edges.insert(key, edge).is_none() {
                added_edges += 1;
            }
        }
        self.units.insert(unit.identity.clone(), unit.summary);

        Ok(ImportReport {
            identity: unit.identity,
            already_present,
            added_nodes,
            added_edges,
            counts: self.counts(),
        })
    }

    /// Projects one artifact into a fresh single-document graph.
    pub fn project_document(artifact: &str) -> Result<NpaGraph, GraphError> {
        let mut graph = NpaGraph::new();
        graph.import(artifact)?;
        Ok(graph)
    }

    /// The graph counts by kind.
    pub fn counts(&self) -> GraphCounts {
        let mut counts = GraphCounts::default();
        for node in self.nodes.values() {
            match node.kind() {
                GraphNodeKind::Fragment => counts.fragments += 1,
                GraphNodeKind::Member => counts.members += 1,
                GraphNodeKind::Classification => counts.classifications += 1,
            }
        }
        counts.relations = self.edges.len();
        counts
    }

    /// Every projected node, in deterministic key order.
    pub fn nodes(&self) -> impl Iterator<Item = &GraphNode> {
        self.nodes.values()
    }

    /// Every projected edge, in deterministic key order.
    pub fn edges(&self) -> impl Iterator<Item = &GraphEdge> {
        self.edges.values()
    }

    /// Every imported document identity, in deterministic key order.
    pub fn identities(&self) -> impl Iterator<Item = &GraphIdentity> {
        self.units.keys()
    }

    /// The recorded per-unit counts for one identity, when present.
    pub fn unit(&self, identity: &GraphIdentity) -> Option<&UnitSummary> {
        self.units.get(identity)
    }

    /// The nodes contributed by one identity.
    pub fn nodes_for(&self, identity: &GraphIdentity) -> Vec<&GraphNode> {
        self.nodes
            .values()
            .filter(|node| &node.key().identity == identity)
            .collect()
    }

    /// The edges contributed by one identity.
    pub fn edges_for(&self, identity: &GraphIdentity) -> Vec<&GraphEdge> {
        self.edges
            .values()
            .filter(|edge| &edge.key.identity == identity)
            .collect()
    }
}

// ------------------------------------------------------------- read path #

/// The fully projected (not yet merged) content of one unit.
struct ProjectedUnit {
    identity: GraphIdentity,
    nodes: BTreeMap<GraphNodeKey, GraphNode>,
    edges: BTreeMap<GraphEdgeKey, GraphEdge>,
    summary: UnitSummary,
}

/// Reads one artifact, validates identity/provenance, and projects its nodes and
/// edges keyed by the composite document identity. Never opens the source XML.
fn project_unit(
    artifact: &str,
    pinned: Option<&GraphIdentity>,
) -> Result<ProjectedUnit, GraphError> {
    let readback = read_back_npa_analysis(artifact).map_err(map_wire_error)?;
    let identity = GraphIdentity::from_readback(&readback.manifest)?;
    check_document_record(&readback, &identity)?;
    if let Some(pinned) = pinned {
        check_pinned(&identity, pinned)?;
    }

    // Rule 3: every span must cite a fragment the envelope declares.
    let declared: BTreeSet<&str> = readback
        .fragments
        .iter()
        .map(|fragment| fragment.reference.as_str())
        .collect();
    for (label, reference) in readback.bound_refs() {
        if let ReadbackRef::Bound { fragment, .. } = &reference
            && !declared.contains(fragment.as_str())
        {
            return Err(GraphError::new(
                GraphErrorKind::UnknownFragment,
                format!("{label} cites undeclared fragment {fragment}"),
            ));
        }
    }

    let mut nodes: BTreeMap<GraphNodeKey, GraphNode> = BTreeMap::new();
    let mut edges: BTreeMap<GraphEdgeKey, GraphEdge> = BTreeMap::new();

    // Fragment nodes.
    for fragment in &readback.fragments {
        let key = GraphNodeKey::new(
            identity.clone(),
            LocalNodeKey::Fragment(FragmentRef::new(fragment.reference.clone())),
        );
        nodes.insert(
            key.clone(),
            GraphNode::Fragment {
                key,
                byte_length: fragment.byte_length,
                content_sha256: fragment.content_sha256.clone(),
            },
        );
    }

    // Member nodes (linked members carry the `member_id` graph identity).
    let mut members: BTreeMap<u64, GraphNodeKey> = BTreeMap::new();
    for member in &readback.linked_members {
        let key = GraphNodeKey::new(identity.clone(), LocalNodeKey::Member(member.member_id));
        members.insert(member.member_id, key.clone());
        nodes.insert(
            key.clone(),
            GraphNode::Member {
                key,
                reference: member.reference.clone(),
                evidence: member.evidence.clone(),
            },
        );
    }

    // Classification nodes; an endpoint absent from the envelope is refused.
    for classification in &readback.classifications {
        let member = members
            .get(&classification.member_id)
            .cloned()
            .ok_or_else(|| {
                GraphError::new(
                    GraphErrorKind::CrossDocument,
                    format!(
                        "classification {} names member {} absent from the envelope",
                        classification.reference, classification.member_id
                    ),
                )
            })?;
        let key = GraphNodeKey::new(
            identity.clone(),
            LocalNodeKey::Classification(classification.member_id),
        );
        nodes.insert(
            key.clone(),
            GraphNode::Classification {
                key,
                reference: classification.reference.clone(),
                member,
            },
        );
    }

    // Relation edges; both endpoints must be members of this envelope.
    for relation in &readback.relations {
        let from = endpoint(&members, relation.from_id, &relation.reference)?;
        let to = endpoint(&members, relation.to_id, &relation.reference)?;
        let key = GraphEdgeKey {
            identity: identity.clone(),
            relation_ref: relation.reference.clone(),
        };
        edges.insert(
            key.clone(),
            GraphEdge {
                key,
                kind: relation.kind.clone(),
                from,
                to,
            },
        );
    }

    let summary = UnitSummary {
        fragments: nodes
            .values()
            .filter(|node| node.kind() == GraphNodeKind::Fragment)
            .count(),
        members: nodes
            .values()
            .filter(|node| node.kind() == GraphNodeKind::Member)
            .count(),
        classifications: nodes
            .values()
            .filter(|node| node.kind() == GraphNodeKind::Classification)
            .count(),
        relations: edges.len(),
    };

    Ok(ProjectedUnit {
        identity,
        nodes,
        edges,
        summary,
    })
}

fn endpoint(
    members: &BTreeMap<u64, GraphNodeKey>,
    id: u64,
    relation_ref: &str,
) -> Result<GraphNodeKey, GraphError> {
    members.get(&id).cloned().ok_or_else(|| {
        GraphError::new(
            GraphErrorKind::CrossDocument,
            format!("relation {relation_ref} cites member {id} absent from the envelope"),
        )
    })
}

/// The `document` record re-carries the identity; it must agree with the
/// manifest pin, or the unit is refused without any rebase.
fn check_document_record(
    readback: &AnalysisReadback,
    identity: &GraphIdentity,
) -> Result<(), GraphError> {
    let record = readback
        .records
        .iter()
        .find(|record| record.family == FAMILY_DOCUMENT)
        .ok_or_else(|| {
            GraphError::new(
                GraphErrorKind::EnvelopeUnreadable,
                "envelope has no document record",
            )
        })?;
    let fields = JsonFields::parse(&record.raw).map_err(map_wire_error)?;
    let source_sha256 = string_field(&fields, "source_sha256").ok_or_else(|| {
        GraphError::new(
            GraphErrorKind::EnvelopeUnreadable,
            "document record has no source_sha256",
        )
    })?;
    if source_sha256 != identity.source.source_sha256 {
        return Err(GraphError::new(
            GraphErrorKind::SourceIdentityMismatch,
            "document record source_sha256 differs from the manifest pin",
        ));
    }
    for (key, expected) in [
        (
            "document_version_ref",
            identity.version.document_version_ref(),
        ),
        ("source_revision", identity.version.source_revision()),
        ("decoder_profile", identity.version.decoder_profile()),
    ] {
        let value = string_field(&fields, key).ok_or_else(|| {
            GraphError::new(
                GraphErrorKind::EnvelopeUnreadable,
                format!("document record has no {key}"),
            )
        })?;
        if value != expected {
            return Err(GraphError::new(
                GraphErrorKind::DocumentVersionMismatch,
                format!("document record {key} differs from the manifest pin"),
            ));
        }
    }
    Ok(())
}

/// The caller's pinned identity must agree with the unit's own manifest
/// identity; a mismatch is never rebased onto the unit's source.
fn check_pinned(identity: &GraphIdentity, pinned: &GraphIdentity) -> Result<(), GraphError> {
    if identity.version.document_version_ref() != pinned.version.document_version_ref() {
        return Err(GraphError::new(
            GraphErrorKind::CrossDocument,
            "the unit belongs to a different document_version_ref than the pinned unit",
        ));
    }
    if identity.source != pinned.source {
        return Err(GraphError::new(
            GraphErrorKind::SourceIdentityMismatch,
            "the unit source identity differs from the pinned identity",
        ));
    }
    if identity.version != pinned.version {
        return Err(GraphError::new(
            GraphErrorKind::DocumentVersionMismatch,
            "the unit document version differs from the pinned version",
        ));
    }
    Ok(())
}

// ----------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;

    const HEX_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const HEX_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const HEX_C: &str = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
    const HEX_D: &str = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";
    const HEX_F: &str = "1111111111111111111111111111111111111111111111111111111111111111";
    const HEX_G: &str = "2222222222222222222222222222222222222222222222222222222222222222";

    fn manifest_line(sha256: &str, bytes: u64, doc: &str, revision: &str) -> String {
        format!(
            concat!(
                "{{\"kind\":\"npa_analysis_manifest\",",
                "\"schema\":\"law-nexus/npa-analysis-manifest/v1\",",
                "\"model\":\"law-nexus/npa-analysis-model/v1\",",
                "\"profile\":\"npa_analysis_wordml/v1\",",
                "\"version\":1,\"capability\":\"npa_analysis_jsonl\",",
                "\"generator\":{{\"name\":\"ln-decode.npa_analysis_wire\",\"version\":\"0.0.0\"}},",
                "\"source\":{{\"sha256\":\"{}\",\"bytes\":{}}},",
                "\"parent\":{{\"schema\":\"law-nexus/cleaned-projection/v1\",",
                "\"records_seal_hash\":null,\"manifest_hash\":null}},",
                "\"document_version_ref\":\"{}\",\"source_revision\":\"{}\",",
                "\"decoder_profile\":\"npa_analysis_wordml/v1\",",
                "\"limits\":{{\"max_line_bytes\":1048576,\"max_records\":100000}},",
                "\"non_authoritative\":true}}"
            ),
            sha256, bytes, doc, revision
        )
    }

    const POLICIES: &str = concat!(
        "{\"kind\":\"npa_analysis_policies\",",
        "\"schema\":\"law-nexus/npa-analysis-policies/v1\",",
        "\"counts_scope\":\"integrity_not_coverage\",",
        "\"semantic_scope\":\"not_legal_gold\",",
        "\"temporal_scope\":\"identity_and_coordinates_only\",",
        "\"promotion\":\"none\",",
        "\"authenticity\":\"integrity_only_not_authenticity\",",
        "\"corpus_transfer\":\"no_restricted_corpus\",",
        "\"non_authoritative\":true}"
    );

    fn document_line(sha256: &str, doc: &str, revision: &str) -> String {
        format!(
            concat!(
                "{{\"family\":\"document\",",
                "\"schema\":\"law-nexus/npa-analysis-document/v1\",\"ref\":\"doc\",",
                "\"document_version_ref\":\"{}\",\"source_revision\":\"{}\",",
                "\"decoder_profile\":\"npa_analysis_wordml/v1\",",
                "\"source_sha256\":\"{}\",\"projection_content_hash\":null,",
                "\"blocks\":1,\"primary_views\":1}}"
            ),
            doc, revision, sha256
        )
    }

    fn fragment_line(reference: &str, byte_length: u64, content_sha256: &str) -> String {
        format!(
            concat!(
                "{{\"family\":\"fragment\",",
                "\"schema\":\"law-nexus/npa-analysis-fragment/v1\",",
                "\"ref\":\"{}\",\"fragment_ref\":\"{}\",",
                "\"byte_length\":{},\"content_sha256\":\"{}\"}}"
            ),
            reference, reference, byte_length, content_sha256
        )
    }

    fn linked_member_line(member_id: u64, fragment: &str, start: usize, end: usize) -> String {
        format!(
            concat!(
                "{{\"family\":\"member\",",
                "\"schema\":\"law-nexus/npa-analysis-member/v1\",",
                "\"ref\":\"ml:{}\",\"stage\":\"linked\",\"member_id\":{},",
                "\"kind\":\"anchored\",\"derivation\":\"typed_anchor\",",
                "\"alias\":null,\"approved_by\":null,",
                "\"evidence\":{{\"fragment\":\"{}\",\"start\":{},\"end\":{}}},",
                "\"provenance\":[{{\"fragment\":\"{}\",\"start\":{},\"end\":{}}}]}}"
            ),
            member_id, member_id, fragment, start, end, fragment, start, end
        )
    }

    fn typed_member_line(index: usize, fragment: &str, start: usize, end: usize) -> String {
        format!(
            concat!(
                "{{\"family\":\"member\",",
                "\"schema\":\"law-nexus/npa-analysis-member/v1\",",
                "\"ref\":\"mt:{}\",\"stage\":\"typed\",\"typed_index\":{},",
                "\"date\":\"01.01.2020\",\"number\":\"123\",\"type_name\":\"Приказ\",",
                "\"approved_by\":\"\",\"derivation\":\"written_here\",\"unresolved\":false,",
                "\"span\":{{\"fragment\":\"{}\",\"start\":{},\"end\":{}}},",
                "\"type_evidence\":null,\"alternatives\":[]}}"
            ),
            index, index, fragment, start, end
        )
    }

    fn relation_line(
        index: usize,
        kind: &str,
        from: u64,
        to: u64,
        fragment: &str,
        start: usize,
        end: usize,
    ) -> String {
        format!(
            concat!(
                "{{\"family\":\"relation\",",
                "\"schema\":\"law-nexus/npa-analysis-relation/v1\",",
                "\"ref\":\"r:{}\",\"kind\":\"{}\",\"from\":{},\"to\":{},",
                "\"evidence\":[{{\"fragment\":\"{}\",\"start\":{},\"end\":{}}}],",
                "\"why\":\"npa_link::build_linked_document\"}}"
            ),
            index, kind, from, to, fragment, start, end
        )
    }

    fn classification_line(
        member_id: u64,
        graph: &str,
        legal_class: &str,
        identity_key: &str,
        fragment: &str,
        start: usize,
        end: usize,
    ) -> String {
        format!(
            concat!(
                "{{\"family\":\"classification\",",
                "\"schema\":\"law-nexus/npa-analysis-classification/v1\",",
                "\"ref\":\"c:{}\",\"member_id\":{},",
                "\"graph\":\"{}\",\"legal_class\":\"{}\",\"competence\":\"federal\",",
                "\"identity_key\":\"{}\",",
                "\"evidence\":{{\"fragment\":\"{}\",\"start\":{},\"end\":{}}},",
                "\"why\":\"npa_classify::classify_members\"}}"
            ),
            member_id, member_id, graph, legal_class, identity_key, fragment, start, end
        )
    }

    fn footer_line(counts: &str) -> String {
        format!(
            concat!(
                "{{\"kind\":\"npa_analysis_footer\",",
                "\"schema\":\"law-nexus/npa-analysis-footer/v1\",",
                "\"completion\":\"complete\",",
                "\"completion_basis\":\"bounded_analysis_complete\",",
                "\"incomplete_reasons\":[],\"counts\":{},",
                "\"records_seal_hash\":null,\"manifest_hash\":null}}"
            ),
            counts
        )
    }

    /// A hand-written, well-formed envelope: two fragments, one typed member,
    /// two linked members, one relation and two classifications.
    fn envelope_a() -> String {
        envelope_a_with_source(HEX_A)
    }

    /// The same envelope with a caller-chosen source digest (the manifest and
    /// the `document` record stay internally consistent).
    fn envelope_a_with_source(sha256: &str) -> String {
        let mut lines = vec![
            manifest_line(sha256, 42, "doc-1", "rev-1"),
            POLICIES.to_string(),
            document_line(sha256, "doc-1", "rev-1"),
            fragment_line("t7", 13, HEX_F),
            fragment_line("t8", 9, HEX_G),
            typed_member_line(0, "t7", 0, 4),
            linked_member_line(3, "t7", 0, 4),
            linked_member_line(4, "t8", 0, 4),
            relation_line(0, "approved_by", 3, 4, "t7", 0, 4),
            classification_line(3, "identifying_act", "npa", "federal", "t7", 0, 4),
            classification_line(4, "refuse", "unknown", "do_not_project", "t8", 0, 4),
            footer_line(
                "{\"documents\":1,\"fragments\":2,\"members\":3,\"relations\":1,\"classifications\":2,\"diagnostics\":0,\"records\":9}",
            ),
        ];
        lines.push(String::new());
        lines.join("\n")
    }

    /// A second document (`doc-2`) with a different source identity.
    fn envelope_b() -> String {
        let mut lines = vec![
            manifest_line(HEX_B, 7, "doc-2", "rev-1"),
            POLICIES.to_string(),
            document_line(HEX_B, "doc-2", "rev-1"),
            fragment_line("t7", 5, HEX_F),
            linked_member_line(3, "t7", 0, 4),
            footer_line(
                "{\"documents\":1,\"fragments\":1,\"members\":1,\"relations\":0,\"classifications\":0,\"diagnostics\":0,\"records\":3}",
            ),
        ];
        lines.push(String::new());
        lines.join("\n")
    }

    /// The same `document_version_ref` as [`envelope_a`] but a different source
    /// revision (a genuinely different version that must not be merged).
    fn envelope_a_v2() -> String {
        let mut lines = vec![
            manifest_line(HEX_A, 42, "doc-1", "rev-2"),
            POLICIES.to_string(),
            document_line(HEX_A, "doc-1", "rev-2"),
            fragment_line("t7", 13, HEX_F),
            linked_member_line(3, "t7", 0, 4),
            footer_line(
                "{\"documents\":1,\"fragments\":1,\"members\":1,\"relations\":0,\"classifications\":0,\"diagnostics\":0,\"records\":3}",
            ),
        ];
        lines.push(String::new());
        lines.join("\n")
    }

    fn identity_of(artifact: &str) -> GraphIdentity {
        let readback =
            read_back_npa_analysis(artifact).expect("hand-written envelope must read back");
        GraphIdentity::from_readback(&readback.manifest).expect("identity must build")
    }

    #[test]
    fn identity_key_composition() {
        let artifact = envelope_a();
        let identity = identity_of(&artifact);
        assert_eq!(identity.source.source_sha256, HEX_A);
        assert_eq!(identity.version.document_version_ref(), "doc-1");
        assert_eq!(identity.version.source_revision(), "rev-1");
        assert_eq!(identity.version.decoder_profile(), "npa_analysis_wordml/v1");

        let graph = NpaGraph::project_document(&artifact).expect("projection must succeed");
        // Every node key is the composite identity ⊕ local id.
        for node in graph.nodes() {
            assert_eq!(node.key().identity, identity);
            assert!(matches!(
                node.key().kind(),
                GraphNodeKind::Fragment | GraphNodeKind::Member | GraphNodeKind::Classification
            ));
        }
        // Two documents never collide on a bare `t7`: a distinct identity makes
        // a distinct key.
        let other = identity_of(&envelope_b());
        assert_ne!(identity, other);
        let key_a = GraphNodeKey::new(
            identity.clone(),
            LocalNodeKey::Fragment(FragmentRef::new("t7")),
        );
        let key_b = GraphNodeKey::new(
            other.clone(),
            LocalNodeKey::Fragment(FragmentRef::new("t7")),
        );
        assert_ne!(key_a, key_b);
    }

    #[test]
    fn member_relation_classification_nodes_are_built() {
        let graph = NpaGraph::project_document(&envelope_a()).expect("projection must succeed");
        let counts = graph.counts();
        assert_eq!(counts.fragments, 2);
        assert_eq!(counts.members, 2);
        assert_eq!(counts.classifications, 2);
        assert_eq!(counts.relations, 1);
        assert_eq!(counts.nodes(), 6);
        assert_eq!(counts.edges(), 1);

        let edge = graph.edges().next().expect("one relation edge");
        assert_eq!(edge.kind, "approved_by");
        // Endpoints are composite keys, never bare member ids.
        assert_eq!(edge.from.local, LocalNodeKey::Member(3));
        assert_eq!(edge.to.local, LocalNodeKey::Member(4));
        assert_eq!(edge.from.identity, edge.to.identity);

        // The classification node points at its member node by composite key.
        let classification = graph
            .nodes()
            .find(|node| node.kind() == GraphNodeKind::Classification)
            .expect("a classification node");
        match classification {
            GraphNode::Classification { member, .. } => {
                assert_eq!(member.local, LocalNodeKey::Member(3))
            }
            other => panic!("expected a classification node, got {other:?}"),
        }
    }

    #[test]
    fn repeat_import_is_idempotent() {
        let artifact = envelope_a();
        let mut graph = NpaGraph::new();
        let first = graph.import(&artifact).expect("first import");
        assert!(!first.already_present);
        assert_eq!(first.added_nodes, 6);
        assert_eq!(first.added_edges, 1);
        let after_first = graph.counts();

        let second = graph.import(&artifact).expect("repeat import");
        assert!(second.already_present);
        assert_eq!(second.added_nodes, 0);
        assert_eq!(second.added_edges, 0);
        assert_eq!(second.counts, after_first);
        assert_eq!(graph.counts(), after_first);
        assert_eq!(graph.identities().count(), 1);
    }

    #[test]
    fn distinct_documents_are_distinct_keys() {
        let mut graph = NpaGraph::new();
        graph.import(&envelope_a()).expect("document a");
        graph.import(&envelope_b()).expect("document b");
        assert_eq!(graph.identities().count(), 2);
        // `doc-1` has 2 fragments + 2 members + 2 classifications; `doc-2` adds
        // 1 fragment + 1 member. A bare `t7` never collides.
        assert_eq!(graph.counts().fragments, 3);
        assert_eq!(graph.counts().members, 3);
    }

    #[test]
    fn same_document_version_ref_with_a_new_revision_is_refused() {
        let mut graph = NpaGraph::new();
        graph.import(&envelope_a()).expect("document a");
        let error = graph.import(&envelope_a_v2()).expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::DocumentVersionMismatch);
    }

    #[test]
    fn same_document_version_ref_with_a_new_source_is_refused() {
        // A second, internally-consistent envelope keeps
        // `document_version_ref = doc-1` but re-points the source digest.
        let mut graph = NpaGraph::new();
        graph.import(&envelope_a()).expect("document a");
        let error = graph
            .import(&envelope_a_with_source(HEX_C))
            .expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::SourceIdentityMismatch);
    }

    #[test]
    fn pinned_identity_mismatch_is_refused() {
        let artifact = envelope_a();
        let pinned = identity_of(&envelope_b());
        let mut graph = NpaGraph::new();
        let error = graph
            .import_pinned(&artifact, &pinned)
            .expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::CrossDocument);

        // Same document_version_ref, different source identity.
        let readback = read_back_npa_analysis(&artifact).expect("read back");
        let source = SourceIdentity::try_new(
            HEX_C.to_string(),
            readback.manifest.source_bytes,
            readback.manifest.parent_schema.clone(),
            None,
            None,
        )
        .expect("source identity");
        let pinned = GraphIdentity::new(source, identity_of(&artifact).version);
        let error = graph
            .import_pinned(&artifact, &pinned)
            .expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::SourceIdentityMismatch);
    }

    #[test]
    fn undeclared_fragment_is_refused() {
        // A relation whose evidence cites a fragment the envelope never declares.
        let tampered = envelope_a().replace(
            "\"evidence\":[{\"fragment\":\"t7\",\"start\":0,\"end\":4}],\"why\":\"npa_link::build_linked_document\"",
            "\"evidence\":[{\"fragment\":\"t99\",\"start\":0,\"end\":4}],\"why\":\"npa_link::build_linked_document\"",
        );
        assert_ne!(tampered, envelope_a(), "tamper must apply");
        let mut graph = NpaGraph::new();
        let error = graph.import(&tampered).expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::UnknownFragment);
    }

    #[test]
    fn dangling_relation_endpoint_is_cross_document() {
        // A relation whose `to` names a member the envelope never declares.
        let tampered = envelope_a().replace(
            "\"ref\":\"r:0\",\"kind\":\"approved_by\",\"from\":3,\"to\":4,",
            "\"ref\":\"r:0\",\"kind\":\"approved_by\",\"from\":3,\"to\":99,",
        );
        assert_ne!(tampered, envelope_a(), "tamper must apply");
        let mut graph = NpaGraph::new();
        let error = graph.import(&tampered).expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::CrossDocument);
    }

    #[test]
    fn document_record_identity_mismatch_is_refused() {
        // The manifest stays pinned to HEX_A while the `document` record points
        // at a different source digest.
        let tampered = envelope_a().replacen(
            &document_line(HEX_A, "doc-1", "rev-1"),
            &document_line(HEX_D, "doc-1", "rev-1"),
            1,
        );
        assert_ne!(tampered, envelope_a(), "tamper must apply");
        let mut graph = NpaGraph::new();
        let error = graph.import(&tampered).expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::SourceIdentityMismatch);
    }

    #[test]
    fn malformed_envelope_is_unreadable() {
        let mut graph = NpaGraph::new();
        let error = graph
            .import("not a jsonl envelope\n")
            .expect_err("must refuse");
        assert_eq!(error.kind(), GraphErrorKind::EnvelopeUnreadable);
    }

    #[test]
    fn model_declarations_match_the_consumer_model_block() {
        let identity: Vec<&str> = NPA_GRAPH_IDENTITY_COMPONENTS.to_vec();
        assert_eq!(
            identity,
            [
                "SourceIdentity",
                "DocumentVersionRef",
                "composite_source_identity_xor_document_version_ref"
            ]
        );
        let nodes: Vec<&str> = NPA_GRAPH_NODE_KINDS
            .iter()
            .map(|kind| kind.as_str())
            .collect();
        assert_eq!(nodes, ["member", "fragment", "classification"]);
        assert_eq!(NPA_GRAPH_EDGE_KINDS, ["relation"]);
        assert_eq!(
            NPA_GRAPH_REFUSALS,
            [
                "cross_document",
                "source_identity_mismatch",
                "document_version_mismatch",
                "unknown_fragment"
            ]
        );
        for kind in [
            GraphErrorKind::CrossDocument,
            GraphErrorKind::SourceIdentityMismatch,
            GraphErrorKind::DocumentVersionMismatch,
            GraphErrorKind::UnknownFragment,
        ] {
            assert!(kind.is_model_refusal());
            assert!(NPA_GRAPH_REFUSALS.contains(&kind.as_str()));
        }
    }

    #[test]
    fn graph_source_is_serialization_free_and_opens_no_xml() {
        let path =
            std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/npa_graph_projection.rs");
        let source = std::fs::read_to_string(path).expect("source must be readable");
        // Scan the module proper, not this test module (whose literals name the
        // forbidden crates).
        let code_end = source.find("#[cfg(test)]").unwrap_or(source.len());
        let code: String = source[..code_end]
            .lines()
            .filter(|line| !line.trim_start().starts_with("//"))
            .collect::<Vec<_>>()
            .join("\n");
        for forbidden in [
            "serde",
            "Serialize",
            "Deserialize",
            "quick_xml",
            "XmlReader",
            "XmlNsReader",
            "from_xml",
            "parse_xml",
        ] {
            assert!(
                !code.contains(forbidden),
                "npa_graph_projection must stay serialization-free and XML-free, found {forbidden}"
            );
        }
        assert!(
            code.contains("read_back_npa_analysis"),
            "the consumer must read the materialized JSONL through the read-back"
        );
    }
}
