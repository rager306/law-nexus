//! Derive cross-act edges from classified links.
//! Maps ClassifiedLink → DerivedEdge with correct direction per kind.
//! amends: from amending act → to amended article (reversed).
//! cites/implements/specifies: from source → to target (forward).

use crate::classifier::ClassifiedLink;

/// A derived cross-act edge, not yet resolved to ComponentConceptIds.
/// The `from`/`to` fields hold consid tokens until the catalog port resolves them.
#[derive(Debug, Clone, PartialEq)]
pub struct DerivedEdge {
    pub kind: String,
    pub from_consider: String,
    pub to_consider: String,
    pub link_text: String,
    pub confidence: f64,
    pub provenance: String,
}

/// Derive edges from classified links.
/// `source_consider` = the document containing the links (e.g. 44-ФЗ).
/// For `amends`: edge direction is reversed (amending → amended).
/// For other kinds: edge direction is forward (source → target).
pub fn derive_edges(classified: &[ClassifiedLink], source_consider: &str) -> Vec<DerivedEdge> {
    classified
        .iter()
        .filter(|c| c.kind != "unknown")
        .map(|c| {
            let (from, to) = if c.kind == "amends" {
                // Amending act (link dest) → amended act (source)
                (c.dest.clone(), source_consider.to_owned())
            } else {
                // Source → cited/implemented target (link dest)
                (source_consider.to_owned(), c.dest.clone())
            };
            DerivedEdge {
                kind: c.kind.clone(),
                from_consider: from,
                to_consider: to,
                link_text: c.text.clone(),
                confidence: c.confidence,
                provenance: source_consider.to_owned(),
            }
        })
        .collect()
}
