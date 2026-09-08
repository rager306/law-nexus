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

#[derive(Debug, Clone, PartialEq, Eq)]
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
        })
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
}
impl ContextRequest {
    pub fn new(kind: RequestKind, origin: FrameId) -> Self {
        Self {
            kind,
            origin,
            key: None,
            scope: None,
            path: Vec::new(),
        }
    }
    pub fn key(mut self, key: impl Into<String>) -> Self {
        self.key = Some(key.into());
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
            let terminal = if requisites_available {
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
