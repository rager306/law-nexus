//! Bounded document-context closure for the proposed NPA contour.
//!
//! This crate-level model is intentionally independent from document decoding:
//! callers provide source-local blocks, frames, and evidence.  All resolution
//! is deterministic, bounded, and fail-closed; no text span is minted across
//! block boundaries.

use std::collections::{BTreeMap, BTreeSet};

pub const MAX_LINKING_PASSES: usize = 1;
pub const PROPOSED_MAX_CANDIDATES: usize = 8;
pub const PROPOSED_MAX_WORKLIST_STEPS: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct DocumentVersion(String);
impl DocumentVersion {
    pub fn new(value: impl Into<String>) -> Result<Self, ContextError> {
        let value = value.into();
        if value.trim().is_empty() {
            return Err(ContextError::InvalidDocumentVersion);
        }
        Ok(Self(value))
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct BlockId(usize);
impl BlockId {
    pub const fn new(value: usize) -> Self {
        Self(value)
    }
    pub const fn get(self) -> usize {
        self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct FrameId(usize);
impl FrameId {
    pub const fn new(value: usize) -> Self {
        Self(value)
    }
    pub const fn get(self) -> usize {
        self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct TextSpan {
    start: usize,
    end: usize,
}
impl TextSpan {
    pub fn new(start: usize, end: usize) -> Result<Self, ContextError> {
        if start > end {
            return Err(ContextError::InvalidSpan);
        }
        Ok(Self { start, end })
    }
    pub const fn start(self) -> usize {
        self.start
    }
    pub const fn end(self) -> usize {
        self.end
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBlock {
    id: BlockId,
    order: usize,
    text: String,
}
impl SourceBlock {
    pub fn new(id: BlockId, order: usize, text: impl Into<String>) -> Self {
        Self {
            id,
            order,
            text: text.into(),
        }
    }
    pub const fn id(&self) -> BlockId {
        self.id
    }
    pub const fn order(&self) -> usize {
        self.order
    }
    pub fn text(&self) -> &str {
        &self.text
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ContainerRole {
    Document,
    Section,
    Article,
    Requisites,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Container {
    id: usize,
    role: ContainerRole,
    parent: Option<usize>,
}
impl Container {
    pub const fn new(id: usize, role: ContainerRole, parent: Option<usize>) -> Self {
        Self { id, role, parent }
    }
    pub const fn id(&self) -> usize {
        self.id
    }
    pub const fn role(&self) -> ContainerRole {
        self.role
    }
    pub const fn parent(&self) -> Option<usize> {
        self.parent
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentStructureIndex {
    version: DocumentVersion,
    blocks: Vec<SourceBlock>,
    containers: Vec<Container>,
    membership: BTreeMap<BlockId, usize>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContextError {
    InvalidDocumentVersion,
    InvalidSpan,
    EmptyDocument,
    DuplicateBlock,
    NonContiguousOrder,
    MissingContainer,
    ConflictingStructure,
    /// RC28-F12: an alias declaration needs a non-empty wording; an empty one
    /// cannot be used, so it is refused at construction instead of resolving
    /// to a wildcard key later.
    EmptyAliasWording,
    /// RC28-F12: an alias declaration must point at a frame the overlay
    /// actually holds. A dangling declaration would authorize a frame that
    /// does not exist, so it is refused at build time.
    UnknownFrame,
}
impl DocumentStructureIndex {
    pub fn build(
        version: DocumentVersion,
        blocks: Vec<SourceBlock>,
        containers: Vec<Container>,
        membership: BTreeMap<BlockId, usize>,
    ) -> Result<Self, ContextError> {
        if blocks.is_empty() {
            return Err(ContextError::EmptyDocument);
        }
        let mut ids = BTreeSet::new();
        for (expected, block) in blocks.iter().enumerate() {
            if !ids.insert(block.id) {
                return Err(ContextError::DuplicateBlock);
            }
            if block.order != expected {
                return Err(ContextError::NonContiguousOrder);
            }
        }
        for container in &containers {
            if let Some(parent) = container.parent {
                if !containers.iter().any(|x| x.id == parent) {
                    return Err(ContextError::MissingContainer);
                }
            }
        }
        if membership.keys().any(|id| !ids.contains(id))
            || membership
                .values()
                .any(|id| !containers.iter().any(|x| x.id == *id))
        {
            return Err(ContextError::MissingContainer);
        }
        Ok(Self {
            version,
            blocks,
            containers,
            membership,
        })
    }
    pub fn version(&self) -> &DocumentVersion {
        &self.version
    }
    pub fn blocks(&self) -> &[SourceBlock] {
        &self.blocks
    }
    pub fn containers(&self) -> &[Container] {
        &self.containers
    }
    pub fn ancestor_path(&self, block: BlockId) -> Result<Vec<usize>, ContextError> {
        let mut current = *self
            .membership
            .get(&block)
            .ok_or(ContextError::MissingContainer)?;
        let mut path = Vec::new();
        let mut seen = BTreeSet::new();
        loop {
            if !seen.insert(current) {
                return Err(ContextError::ConflictingStructure);
            }
            path.push(current);
            let c = self
                .containers
                .iter()
                .find(|x| x.id == current)
                .ok_or(ContextError::MissingContainer)?;
            match c.parent {
                Some(parent) => current = parent,
                None => break,
            }
        }
        Ok(path)
    }
    pub fn adjacent(&self, block: BlockId, radius: usize) -> Vec<BlockId> {
        let Some(source) = self.blocks.iter().find(|x| x.id == block) else {
            return Vec::new();
        };
        self.blocks
            .iter()
            .filter(|x| x.id != block && x.order.abs_diff(source.order) <= radius)
            .map(|x| x.id)
            .collect()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ThisRefEvidence {
    span: TextSpan,
    surface: String,
}
impl ThisRefEvidence {
    pub fn span(&self) -> TextSpan {
        self.span
    }
    pub fn surface(&self) -> &str {
        &self.surface
    }
}
pub fn detect_this_ref(text: &str) -> Vec<ThisRefEvidence> {
    [
        "настоящего Федерального закона",
        "настоящего Закона",
        "настоящего приказа",
        "настоящего Порядка",
        "настоящего положения",
        "настоящей статьи",
    ]
    .iter()
    .filter_map(|surface| {
        text.find(surface).and_then(|start| {
            TextSpan::new(start, start + surface.len())
                .ok()
                .map(|span| ThisRefEvidence {
                    span,
                    surface: (*surface).to_owned(),
                })
        })
    })
    .collect()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Frame {
    id: FrameId,
    block: BlockId,
    opens_series: bool,
    continues: bool,
}
impl Frame {
    pub const fn new(id: FrameId, block: BlockId, opens_series: bool, continues: bool) -> Self {
        Self {
            id,
            block,
            opens_series,
            continues,
        }
    }
    pub const fn id(&self) -> FrameId {
        self.id
    }
    pub const fn block(&self) -> BlockId {
        self.block
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisOverlay {
    frames: Vec<Frame>,
    aliases: BTreeMap<String, FrameId>,
    continuation_heads: BTreeMap<FrameId, Vec<FrameId>>,
    scoped_alias_declarations: Vec<ScopedAliasDeclaration>,
}
impl AnalysisOverlay {
    pub fn new(
        frames: Vec<Frame>,
        aliases: BTreeMap<String, FrameId>,
        continuation_heads: BTreeMap<FrameId, Vec<FrameId>>,
    ) -> Result<Self, ContextError> {
        let ids: BTreeSet<_> = frames.iter().map(|f| f.id).collect();
        if ids.len() != frames.len()
            || continuation_heads
                .values()
                .flatten()
                .any(|id| !ids.contains(id))
        {
            return Err(ContextError::ConflictingStructure);
        }
        Ok(Self {
            frames,
            aliases,
            continuation_heads,
            scoped_alias_declarations: Vec::new(),
        })
    }
    /// RC28-F12 declare surface. The declaration record keeps the wording, the
    /// structural scope it was declared in, the frame it names and its own
    /// source anchor, so a later use can be authorized (or refused) without
    /// inventing a scope from proximity.
    pub fn with_scoped_aliases(
        mut self,
        declarations: Vec<ScopedAliasDeclaration>,
    ) -> Result<Self, ContextError> {
        let ids: BTreeSet<_> = self.frames.iter().map(|f| f.id).collect();
        for declaration in &declarations {
            if !ids.contains(&declaration.frame) {
                return Err(ContextError::UnknownFrame);
            }
        }
        self.scoped_alias_declarations = declarations;
        Ok(self)
    }
    pub fn frames(&self) -> &[Frame] {
        &self.frames
    }
    pub fn aliases(&self) -> &BTreeMap<String, FrameId> {
        &self.aliases
    }
    pub fn continuation_heads(&self, frame: FrameId) -> &[FrameId] {
        self.continuation_heads
            .get(&frame)
            .map(Vec::as_slice)
            .unwrap_or(&[])
    }
    /// Every declared scoped alias, in declaration order.
    pub fn scoped_alias_declarations(&self) -> &[ScopedAliasDeclaration] {
        &self.scoped_alias_declarations
    }
    fn frame(&self, id: FrameId) -> Option<&Frame> {
        self.frames.iter().find(|frame| frame.id == id)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum RequestKind {
    AncestorPath,
    AdjacentBlocks,
    OpenSeriesHead,
    ScopedAlias,
    CurrentDocumentRequisites,
    ExplicitAnchorLookup,
}
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ContextRequest {
    pub kind: RequestKind,
    pub origin: FrameId,
    pub key: Option<String>,
    pub scope: Option<usize>,
    pub path: Vec<FrameId>,
    /// Typed current-document `ThisRef` grammar evidence (RC28-F08). It is
    /// part of the request identity so two requests can never share an
    /// authorization result while admitting different evidence. Empty means
    /// "no admitted grammar proof", never "self-reference proven".
    pub evidence: Vec<ThisRefEvidence>,
}
impl ContextRequest {
    pub fn new(kind: RequestKind, origin: FrameId) -> Self {
        Self {
            kind,
            origin,
            key: None,
            scope: None,
            path: Vec::new(),
            evidence: Vec::new(),
        }
    }
    pub fn key(mut self, key: impl Into<String>) -> Self {
        self.key = Some(key.into());
        self
    }
    /// Attaches admitted `ThisRef` grammar evidence to the request.
    pub fn with_evidence(mut self, evidence: Vec<ThisRefEvidence>) -> Self {
        self.evidence = evidence;
        self
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Terminal {
    Resolved,
    Partial,
    Conflicting,
    Unavailable,
    Cycle,
    Limit,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextResult {
    pub terminal: Terminal,
    pub provenance: Vec<String>,
    pub candidates: Vec<FrameId>,
}
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RunStats {
    pub steps: usize,
    pub memo_hits: usize,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextRun {
    pub results: BTreeMap<ContextRequest, ContextResult>,
    pub stats: RunStats,
}

pub fn resolve(
    request: &ContextRequest,
    index: &DocumentStructureIndex,
    overlay: &AnalysisOverlay,
    requisites_available: bool,
    max_steps: usize,
) -> ContextResult {
    let provenance = vec![
        format!("document:{}", index.version.as_str()),
        format!("frame:{}", request.origin.get()),
    ];
    if request.path.contains(&request.origin) {
        return ContextResult {
            terminal: Terminal::Cycle,
            provenance,
            candidates: Vec::new(),
        };
    }
    if max_steps == 0 {
        return ContextResult {
            terminal: Terminal::Limit,
            provenance,
            candidates: Vec::new(),
        };
    }
    match request.kind {
        RequestKind::AncestorPath => {
            match index.ancestor_path(BlockId::new(request.origin.get())) {
                Ok(path) => ContextResult {
                    terminal: Terminal::Resolved,
                    provenance: path.into_iter().map(|x| format!("container:{x}")).collect(),
                    candidates: Vec::new(),
                },
                Err(_) => ContextResult {
                    terminal: Terminal::Unavailable,
                    provenance,
                    candidates: Vec::new(),
                },
            }
        }
        RequestKind::AdjacentBlocks => {
            let candidates = index.adjacent(BlockId::new(request.origin.get()), 1);
            let terminal = if candidates.is_empty() {
                Terminal::Unavailable
            } else {
                Terminal::Resolved
            };
            ContextResult {
                terminal,
                provenance,
                candidates: candidates
                    .into_iter()
                    .map(|x| FrameId::new(x.get()))
                    .collect(),
            }
        }
        RequestKind::OpenSeriesHead => {
            let candidates = overlay.continuation_heads(request.origin).to_vec();
            let terminal = match candidates.len() {
                0 => Terminal::Unavailable,
                1 => Terminal::Resolved,
                _ => Terminal::Conflicting,
            };
            ContextResult {
                terminal,
                provenance,
                candidates,
            }
        }
        RequestKind::CurrentDocumentRequisites => {
            // RC28-F08 alignment with the owning ln-decode contract: a missing
            // sidecar is Unavailable, an available sidecar with an empty
            // grammar evidence set is a refusal (Partial) and never Resolved.
            let terminal = if !requisites_available {
                Terminal::Unavailable
            } else if request.evidence.is_empty() {
                Terminal::Partial
            } else {
                Terminal::Resolved
            };
            ContextResult {
                terminal,
                provenance,
                candidates: Vec::new(),
            }
        }
        RequestKind::ScopedAlias | RequestKind::ExplicitAnchorLookup => {
            let terminal = if request.key.is_some() {
                Terminal::Resolved
            } else {
                Terminal::Unavailable
            };
            ContextResult {
                terminal,
                provenance,
                candidates: Vec::new(),
            }
        }
    }
}

/// RC28-F12: a declared scoped alias. `wording` is the written alias, `scope`
/// is the structural container the declaration lives in, `frame` is the frame
/// it names and `anchor` is the declaration's own source-local span.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ScopedAliasDeclaration {
    wording: String,
    scope: usize,
    frame: FrameId,
    anchor: TextSpan,
}
impl ScopedAliasDeclaration {
    pub fn new(
        wording: impl Into<String>,
        scope: usize,
        frame: FrameId,
        anchor: TextSpan,
    ) -> Result<Self, ContextError> {
        let wording = wording.into();
        if wording.trim().is_empty() {
            return Err(ContextError::EmptyAliasWording);
        }
        if anchor.start() == anchor.end() {
            return Err(ContextError::InvalidSpan);
        }
        Ok(Self {
            wording,
            scope,
            frame,
            anchor,
        })
    }
    pub fn wording(&self) -> &str {
        &self.wording
    }
    pub const fn scope(&self) -> usize {
        self.scope
    }
    pub const fn frame(&self) -> FrameId {
        self.frame
    }
    pub const fn anchor(&self) -> TextSpan {
        self.anchor
    }
}

/// RC28-F12: self-reference, an earlier cited act, an explicitly declared
/// scoped alias and a coordinating head are *different* constructions. Each
/// one carries its own authorization input, and recognizing one never
/// authorizes another.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ReferenceConstruction {
    /// `настоящего Закона` — the current document speaks about itself.
    CurrentDocumentSelf,
    /// A citation of an earlier act, proven by source-block document order.
    EarlierCitedAct,
    /// An explicitly declared scoped alias (`(далее — Закон)`).
    DeclaredScopedAlias,
    /// The coordinating head of an open series.
    CoordinatingHead,
}

/// RC28-F12 typed abstentions. Every variant is an explicit "not proven"
/// outcome; none of them may be read as a resolved reference.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum ConstructionAbstention {
    /// No admitted `ThisRef` grammar evidence for a self-reference.
    MissingSelfEvidence,
    /// No requisites sidecar: the self-reference cannot be authorized.
    MissingRequisites,
    /// No antecedent frame was offered or the offered frame is unknown.
    MissingAntecedent,
    /// The cited act is not earlier in source-block document order.
    AntecedentNotEarlier,
    /// The supplied anchor is empty, out of the target block, or off a UTF-8
    /// character boundary, so it cannot prove a source-backed antecedent.
    AnchorOutOfBlock,
    /// No alias with this wording was ever declared.
    UndeclaredAlias,
    /// The request carries no alias wording to look up.
    MissingAliasWording,
}

/// One typed construction request. `anchor` is the source-local anchor that
/// proves the requested target. Byte offsets are fragment-local, so the anchor
/// carries the block it was minted in and can never be re-used across blocks
/// (RC28-F07 lesson: fragment-local offsets are not comparable).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ConstructionRequest {
    pub construction: ReferenceConstruction,
    pub origin: FrameId,
    pub scope: usize,
    pub key: Option<String>,
    pub anchor: Option<SourceAnchor>,
    pub explicit_target: Option<FrameId>,
    pub evidence: Vec<ThisRefEvidence>,
}
impl ConstructionRequest {
    pub fn new(construction: ReferenceConstruction, origin: FrameId, scope: usize) -> Self {
        Self {
            construction,
            origin,
            scope,
            key: None,
            anchor: None,
            explicit_target: None,
            evidence: Vec::new(),
        }
    }
    pub fn key(mut self, key: impl Into<String>) -> Self {
        self.key = Some(key.into());
        self
    }
    pub fn anchor(mut self, anchor: SourceAnchor) -> Self {
        self.anchor = Some(anchor);
        self
    }
    pub fn explicit_target(mut self, target: FrameId) -> Self {
        self.explicit_target = Some(target);
        self
    }
    pub fn with_evidence(mut self, evidence: Vec<ThisRefEvidence>) -> Self {
        self.evidence = evidence;
        self
    }
}

/// A source-local anchor: the block it was minted in plus the byte span inside
/// that block's own text. The block identity is part of the value, so an
/// anchor minted in one block can never be offered as evidence for another.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SourceAnchor {
    block: BlockId,
    span: TextSpan,
}
impl SourceAnchor {
    pub fn new(block: BlockId, span: TextSpan) -> Result<Self, ContextError> {
        if span.start() == span.end() {
            return Err(ContextError::InvalidSpan);
        }
        Ok(Self { block, span })
    }
    pub const fn block(self) -> BlockId {
        self.block
    }
    pub const fn span(self) -> TextSpan {
        self.span
    }
}

/// The typed result of one construction. `Resolved` means "this construction
/// is authorized for this target"; `Conflicting`, `OutOfScope` and `Unproven`
/// all mean "not resolved" and are never interchangeable with each other.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstructionOutcome {
    Resolved {
        construction: ReferenceConstruction,
        target: FrameId,
        evidence: Vec<TextSpan>,
    },
    Conflicting {
        construction: ReferenceConstruction,
        retained: Vec<FrameId>,
        evidence: Vec<TextSpan>,
    },
    /// The wording exists, but only outside the requested structural scope.
    OutOfScope {
        construction: ReferenceConstruction,
        wording: String,
    },
    Unproven {
        construction: ReferenceConstruction,
        reason: ConstructionAbstention,
    },
}
impl ConstructionOutcome {
    pub const fn construction(&self) -> ReferenceConstruction {
        match self {
            Self::Resolved { construction, .. }
            | Self::Conflicting { construction, .. }
            | Self::OutOfScope { construction, .. }
            | Self::Unproven { construction, .. } => *construction,
        }
    }
    /// The shared terminal classification. `Unproven` maps to `Partial` and
    /// `OutOfScope` to `Unavailable`, so a caller that only needs the terminal
    /// still cannot mistake an abstention for a resolution.
    pub const fn terminal(&self) -> Terminal {
        match self {
            Self::Resolved { .. } => Terminal::Resolved,
            Self::Conflicting { .. } => Terminal::Conflicting,
            Self::OutOfScope { .. } => Terminal::Unavailable,
            Self::Unproven { .. } => Terminal::Partial,
        }
    }
    pub const fn is_resolved(&self) -> bool {
        matches!(self, Self::Resolved { .. })
    }
}

/// Source-block document order of a frame, or `None` when the frame is not in
/// the overlay or its block is not in the index. Document order is the only
/// ordering used here; fragment-local offsets are never compared (RC28-F07).
fn frame_order(
    index: &DocumentStructureIndex,
    overlay: &AnalysisOverlay,
    frame: FrameId,
) -> Option<usize> {
    let block = overlay.frame(frame)?.block;
    index
        .blocks()
        .iter()
        .find(|candidate| candidate.id() == block)
        .map(SourceBlock::order)
}

/// The source text of the block a frame belongs to.
fn frame_source<'a>(
    index: &'a DocumentStructureIndex,
    overlay: &AnalysisOverlay,
    frame: FrameId,
) -> Option<&'a str> {
    let block = overlay.frame(frame)?.block;
    index
        .blocks()
        .iter()
        .find(|candidate| candidate.id() == block)
        .map(SourceBlock::text)
}

fn anchor_is_source_backed(text: &str, anchor: TextSpan) -> bool {
    anchor.start() < anchor.end()
        && anchor.end() <= text.len()
        && text.is_char_boundary(anchor.start())
        && text.is_char_boundary(anchor.end())
}

/// Resolve exactly one RC28-F12 construction. The four constructions share no
/// authorization input: an admitted `ThisRef` evidence set authorizes only
/// self-reference, a document-ordered antecedent frame authorizes only the
/// earlier cited act, a matching declaration authorizes only the alias in its
/// own scope, and overlay heads authorize only the coordinating head.
/// Recognized `в ред.` wording never appears here: edition relations are
/// candidates (`detect_edition_relations`), not authorization.
pub fn resolve_construction(
    request: &ConstructionRequest,
    index: &DocumentStructureIndex,
    overlay: &AnalysisOverlay,
    requisites_available: bool,
) -> ConstructionOutcome {
    let construction = request.construction;
    match construction {
        ReferenceConstruction::CurrentDocumentSelf => {
            if !requisites_available {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingRequisites,
                };
            }
            if request.evidence.is_empty() {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingSelfEvidence,
                };
            }
            ConstructionOutcome::Resolved {
                construction,
                target: request.origin,
                evidence: request.evidence.iter().map(ThisRefEvidence::span).collect(),
            }
        }
        ReferenceConstruction::EarlierCitedAct => {
            let Some(target) = request.explicit_target else {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAntecedent,
                };
            };
            if overlay.frame(target).is_none() {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAntecedent,
                };
            }
            let Some(anchor) = request.anchor else {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::AnchorOutOfBlock,
                };
            };
            let Some(target_text) = frame_source(index, overlay, target) else {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAntecedent,
                };
            };
            // The anchor's block identity is part of the value: an anchor
            // minted in another block has fragment-local offsets that happen to
            // be in range here, so it must be refused before any span check.
            let target_block = overlay.frame(target).map(Frame::block);
            if target_block != Some(anchor.block())
                || !anchor_is_source_backed(target_text, anchor.span())
            {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::AnchorOutOfBlock,
                };
            }
            let (Some(target_order), Some(origin_order)) = (
                frame_order(index, overlay, target),
                frame_order(index, overlay, request.origin),
            ) else {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAntecedent,
                };
            };
            if target_order >= origin_order {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::AntecedentNotEarlier,
                };
            }
            ConstructionOutcome::Resolved {
                construction,
                target,
                evidence: vec![anchor.span()],
            }
        }
        ReferenceConstruction::DeclaredScopedAlias => {
            let Some(wording) = request.key.as_deref() else {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAliasWording,
                };
            };
            let matching: Vec<&ScopedAliasDeclaration> = overlay
                .scoped_alias_declarations()
                .iter()
                .filter(|declaration| declaration.wording() == wording)
                .collect();
            if matching.is_empty() {
                return ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::UndeclaredAlias,
                };
            }
            let in_scope: Vec<&ScopedAliasDeclaration> = matching
                .iter()
                .copied()
                .filter(|declaration| declaration.scope() == request.scope)
                .collect();
            match in_scope.len() {
                0 => ConstructionOutcome::OutOfScope {
                    construction,
                    wording: wording.to_owned(),
                },
                1 => ConstructionOutcome::Resolved {
                    construction,
                    target: in_scope[0].frame(),
                    evidence: vec![in_scope[0].anchor()],
                },
                _ => ConstructionOutcome::Conflicting {
                    construction,
                    retained: in_scope.iter().map(|d| d.frame()).collect(),
                    evidence: in_scope.iter().map(|d| d.anchor()).collect(),
                },
            }
        }
        ReferenceConstruction::CoordinatingHead => {
            let heads = overlay.continuation_heads(request.origin);
            match heads.len() {
                0 => ConstructionOutcome::Unproven {
                    construction,
                    reason: ConstructionAbstention::MissingAntecedent,
                },
                1 => ConstructionOutcome::Resolved {
                    construction,
                    target: heads[0],
                    evidence: Vec::new(),
                },
                _ => ConstructionOutcome::Conflicting {
                    construction,
                    retained: heads.to_vec(),
                    evidence: Vec::new(),
                },
            }
        }
    }
}

/// RC28-F12: `в ред.` (and its full form `в редакции`) is preserved as a
/// source-backed **relation candidate**. It is not Expression identity, not
/// `edition_date`, not CTV and not force: the record below carries nothing but
/// the original surface and its source-local anchor, so no downstream step can
/// read an edition fact out of it.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct EditionRelationCandidate {
    anchor: TextSpan,
    surface: String,
}
impl EditionRelationCandidate {
    pub const fn anchor(&self) -> TextSpan {
        self.anchor
    }
    pub fn surface(&self) -> &str {
        &self.surface
    }
}

/// Case-insensitive match of one closed surface at `start`, returning the end
/// byte offset in the original text. No normalization or rewriting is applied.
fn match_surface_case_insensitive(text: &str, start: usize, surface: &str) -> Option<usize> {
    let mut cursor = start;
    for expected in surface.chars() {
        let actual = text.get(cursor..)?.chars().next()?;
        if !actual.to_lowercase().eq(expected.to_lowercase()) {
            return None;
        }
        cursor += actual.len_utf8();
    }
    Some(cursor)
}

fn is_token_boundary_before(text: &str, start: usize) -> bool {
    text.get(..start)
        .and_then(|prefix| prefix.chars().next_back())
        .map(|previous| !previous.is_alphanumeric())
        .unwrap_or(true)
}

fn is_token_boundary_after(text: &str, end: usize) -> bool {
    text.get(end..)
        .and_then(|suffix| suffix.chars().next())
        .map(|next| !next.is_alphanumeric())
        .unwrap_or(true)
}

/// Detect the closed edition-relation surface with token boundaries, keeping
/// the original UTF-8 span and the original spelling of every match.
pub fn detect_edition_relations(text: &str) -> Vec<EditionRelationCandidate> {
    const SURFACES: [&str; 2] = ["в ред.", "в редакции"];
    let mut out = Vec::new();
    for (start, _) in text.char_indices() {
        for surface in SURFACES {
            let Some(end) = match_surface_case_insensitive(text, start, surface) else {
                continue;
            };
            if !is_token_boundary_before(text, start) || !is_token_boundary_after(text, end) {
                continue;
            }
            if let Ok(anchor) = TextSpan::new(start, end) {
                out.push(EditionRelationCandidate {
                    anchor,
                    surface: text[start..end].to_owned(),
                });
            }
        }
    }
    out.sort_by_key(|candidate| (candidate.anchor.start(), candidate.anchor.end()));
    out.dedup();
    out
}

pub fn run_worklist(
    requests: impl IntoIterator<Item = ContextRequest>,
    index: &DocumentStructureIndex,
    overlay: &AnalysisOverlay,
    requisites_available: bool,
    max_steps: usize,
) -> ContextRun {
    let mut results = BTreeMap::new();
    let mut stats = RunStats::default();
    for request in requests {
        if results.contains_key(&request) {
            stats.memo_hits += 1;
            continue;
        }
        if stats.steps >= max_steps {
            results.insert(
                request,
                ContextResult {
                    terminal: Terminal::Limit,
                    provenance: vec!["diagnostic:context_query_limit_reached".into()],
                    candidates: Vec::new(),
                },
            );
            continue;
        }
        stats.steps += 1;
        let result = resolve(
            &request,
            index,
            overlay,
            requisites_available,
            max_steps - stats.steps,
        );
        results.insert(request, result);
    }
    ContextRun { results, stats }
}
