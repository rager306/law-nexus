use crate::domain::{AnchorId, SourceAuthority, SourceRef};

pub trait CitationSourcePort: Send + Sync {
    fn resolve(&self, source: &SourceRef) -> Option<(AnchorId, SourceAuthority)>;
}
