use std::collections::HashMap;

use crate::domain::{AnchorId, SourceAuthority, SourceRef};
use crate::ports::CitationSourcePort;

#[derive(Debug, Default)]
pub struct InMemoryCitationSource {
    entries: HashMap<String, (AnchorId, SourceAuthority)>,
}

impl InMemoryCitationSource {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with(mut self, source: &str, anchor: &str, authority: SourceAuthority) -> Self {
        self.entries.insert(
            source.to_owned(),
            (AnchorId::parse(anchor).unwrap(), authority),
        );
        self
    }
}

impl CitationSourcePort for InMemoryCitationSource {
    fn resolve(&self, source: &SourceRef) -> Option<(AnchorId, SourceAuthority)> {
        self.entries.get(source.as_str()).cloned()
    }
}

/// Hostile: relabels mirror sources as official.
#[derive(Debug, Default)]
pub struct HostileMirrorRelabeler {
    real: InMemoryCitationSource,
}

impl HostileMirrorRelabeler {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with(mut self, source: &str, anchor: &str) -> Self {
        self.real = self.real.with(source, anchor, SourceAuthority::Mirror);
        self
    }
}

impl CitationSourcePort for HostileMirrorRelabeler {
    fn resolve(&self, source: &SourceRef) -> Option<(AnchorId, SourceAuthority)> {
        self.real
            .resolve(source)
            .map(|(anchor, _)| (anchor, SourceAuthority::Official))
    }
}
