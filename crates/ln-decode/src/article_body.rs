//! Article body extraction: decoded text between hierarchy markers (M170 S01).
//!
//! Bounded structural observation: a marker "owns" the body text of the
//! blocks that follow it until the next hierarchy marker. No legal meaning,
//! no citation authority, no cross-provider claims. `ProviderComment` blocks
//! never contribute.

use crate::domain::{ParagraphStyle, ParsedBlock};
use crate::hierarchy::extract_hierarchy;

/// One marker with its collected body text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarkerBody {
    level: String,
    number: String,
    title: Option<String>,
    body: String,
}

impl MarkerBody {
    pub fn level(&self) -> &str {
        &self.level
    }

    pub fn number(&self) -> &str {
        &self.number
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    /// Collected body text (marker line excluded). May be empty for markers
    /// directly followed by another marker.
    pub fn body(&self) -> &str {
        &self.body
    }
}

/// Collect marker bodies in document order.
///
/// A marker's body is the trimmed concatenation of the non-empty block texts
/// between it and the next marker block. `ProviderComment` blocks are
/// skipped. Markers with empty bodies are still emitted (the caller decides
/// whether to use the title as fallback).
pub fn collect_marker_bodies(blocks: &[ParsedBlock]) -> Vec<MarkerBody> {
    let mut out: Vec<MarkerBody> = Vec::new();
    let mut current: Option<usize> = None;
    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        if let Some(node) = extract_hierarchy(block) {
            out.push(MarkerBody {
                level: node.level().as_str().to_owned(),
                number: node.number().to_owned(),
                title: node.title().map(str::to_owned),
                body: String::new(),
            });
            current = Some(out.len() - 1);
            continue;
        }
        if let Some(idx) = current {
            let text = block.text().trim();
            if !text.is_empty() {
                let body = &mut out[idx].body;
                if body.is_empty() {
                    *body = text.to_owned();
                } else {
                    body.push('\n');
                    body.push_str(text);
                }
            }
        }
    }
    out
}

/// One statute article's full text (M170 S01 contract).
///
/// The statya marker line is NOT part of `text` — the marker title lives in
/// `title`. `text` holds the direct prose and every nested sub-marker
/// (chast/punkt/podpunkt) line and body up to the next Statya, Glava, Razdel
/// or Paragraph (§) marker.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArticleText {
    number: String,
    title: Option<String>,
    text: String,
}

impl ArticleText {
    pub fn number(&self) -> &str {
        &self.number
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    /// Full article text (statya marker line excluded): nested prose,
    /// whitespace-normalized lines joined with single newlines.
    pub fn text(&self) -> &str {
        &self.text
    }
}

/// Collect full statute texts in document order.
///
/// Contract: the statya marker line never becomes part of `ArticleText::text`
/// — the marker title is stored separately in `title`. Accumulation starts
/// with the first block after the marker and stops at the next Statya, Glava,
/// Razdel or Paragraph (§) marker; nested sub-marker (chast/punkt/podpunkt)
/// lines belong to the owning article. `ProviderComment` blocks never
/// contribute. Statya markers with no content at all are emitted with an
/// empty `text` (fail-closed, caller decides).
pub fn collect_article_texts(blocks: &[ParsedBlock]) -> Vec<ArticleText> {
    fn is_boundary(level: &str) -> bool {
        matches!(level, "Glava" | "Razdel" | "Paragraph")
    }
    fn is_statya(level: &str) -> bool {
        level == "Statya"
    }

    let mut out: Vec<ArticleText> = Vec::new();
    let mut current: Option<usize> = None;
    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        if let Some(node) = extract_hierarchy(block) {
            let level = node.level().as_str();
            if is_statya(level) {
                out.push(ArticleText {
                    number: node.number().to_owned(),
                    title: node.title().map(str::to_owned),
                    text: String::new(),
                });
                current = Some(out.len() - 1);
                continue;
            }
            if is_boundary(level) {
                current = None;
                continue;
            }
            // nested sub-marker: its line belongs to the owning statya text
            if let Some(idx) = current {
                let line = block.text().trim();
                if !line.is_empty() {
                    append_line(&mut out[idx].text, line);
                }
            }
            continue;
        }
        let text = block.text().trim();
        if text.is_empty() {
            continue;
        }
        if let Some(idx) = current {
            append_line(&mut out[idx].text, text);
        }
    }
    out
}

fn append_line(target: &mut String, line: &str) {
    if target.is_empty() {
        target.push_str(line);
    } else {
        target.push('\n');
        target.push_str(line);
    }
}
