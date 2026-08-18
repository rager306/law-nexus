//! Article body extraction: decoded text between hierarchy markers (M170 S01).
//!
//! Bounded structural observation: a marker "owns" the body text of the
//! blocks that follow it until the next hierarchy marker. No legal meaning,
//! no citation authority, no cross-provider claims. `ProviderComment` blocks
//! never contribute.

use crate::domain::{ParagraphStyle, ParsedBlock};
use crate::hierarchy::extract_hierarchy;
use crate::structural_profile::{GroupProfile, LadderEntry};

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

/// One unit body's full text (M171 S01 T03 contract).
///
/// The unit marker line is NOT part of `text` — the marker title lives in
/// `title`. `text` holds the direct prose and every nested sub-marker
/// (chast/punkt/podpunkt) line and body up to the next unit or container
/// marker of the structural profile (statya for federal_law@v1, punkt for
/// departmental_order / government_resolution).
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

/// Collect unit bodies in document order per the structural profile.
///
/// The profile's ladder is the authority for what is a unit, a container, a
/// subunit, or a subunit-text marker — replacing the M170 hardcoded
/// `is_statya` / `is_boundary` (Statya|Glava|Razdel|Paragraph). Boundaries
/// come from the roles:
///
/// - `unit` markers start a new body (statya for federal_law@v1, punkt for
///   departmental_order / government_resolution);
/// - `container` markers reset accumulation (glava/paragraph for
///   federal_law@v1 — razdel is absent from the federal-law family, R8-08;
///   prilozhenie recognized by its surface marker);
/// - `subunit` markers (chast/punkt/podpunkt) belong to the owning unit:
///   their marker line and following prose join the unit body;
/// - `subunit-text` markers (primechanie — a note) are excluded from the
///   unit body: the note marker and its text never join the unit text
///   (fail-closed reset, nothing invented);
/// - text-only profiles (court_practice) declare no structure and collect
///   nothing (numbered lists are never structure, R8-05).
///
/// Structural-only markers (tokens with no decode `HierarchyLevel`, e.g.
/// primechanie/prilozhenie, R8-09) are recognized by their catalog `surface`
/// prefix — `extract_hierarchy` has no level for them. Marker levels not
/// declared in the profile's ladder fail closed as boundaries (reset).
/// `ProviderComment` blocks never contribute. Unit markers with no content
/// at all are emitted with an empty `text` (fail-closed, caller decides).
pub fn collect_article_texts(profile: &GroupProfile, blocks: &[ParsedBlock]) -> Vec<ArticleText> {
    if profile.text_only || profile.ladder.is_empty() {
        return Vec::new();
    }
    // Surface markers for structural-only tokens (lowercased for a
    // case-insensitive prefix match with a word boundary).
    let surfaces: Vec<(String, &LadderEntry)> = profile
        .ladder
        .iter()
        .filter_map(|entry| {
            entry
                .surface
                .as_ref()
                .map(|surface| (surface.to_lowercase(), entry))
        })
        .collect();

    let mut out: Vec<ArticleText> = Vec::new();
    let mut current: Option<usize> = None;
    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        let text = block.text().trim();
        if text.is_empty() {
            continue;
        }
        if let Some((_, entry)) = surfaces
            .iter()
            .find(|(surface, _)| surface_prefix(text, surface))
        {
            // Structural-only marker ("Примечание", "Приложение"): the
            // note/annex region is not part of any unit body.
            if matches!(entry.role.as_str(), "subunit-text" | "container") {
                current = None;
            }
            continue;
        }
        if let Some(node) = extract_hierarchy(block) {
            let level = node.level().as_str();
            let entry = entry_for(&profile.ladder, level).or_else(|| {
                // Decode-level marker not declared in this group's ladder:
                // the group's own number styles are authoritative (R8-04).
                // Reclassify the decoded node via the ladder style match
                // (e.g. PP "1." points decode as Chast but are punkt units
                // for government_resolution). No style match -> fail-closed
                // boundary below. federal_law@v1 declares all seven decode
                // levels, so this fallback never fires for it (anchor).
                profile.style_match(text)
            });
            let Some(entry) = entry else {
                // Undeclared marker level: fail-closed boundary (reset).
                current = None;
                continue;
            };
            match entry.role.as_str() {
                "unit" => {
                    out.push(ArticleText {
                        number: node.number().to_owned(),
                        title: node.title().map(str::to_owned),
                        text: String::new(),
                    });
                    current = Some(out.len() - 1);
                }
                "container" => current = None,
                _ => {
                    // subunit / subunit-text marker line belongs to the
                    // owning unit body.
                    if let Some(idx) = current {
                        append_line(&mut out[idx].text, text);
                    }
                }
            }
            continue;
        }
        if let Some(idx) = current {
            append_line(&mut out[idx].text, text);
        }
    }
    out
}

/// Look up a ladder entry by decode marker level (case-insensitive token
/// match — ladder tokens are lowercase, `HierarchyLevel::as_str` is title
/// case).
fn entry_for<'a>(ladder: &'a [LadderEntry], level: &str) -> Option<&'a LadderEntry> {
    ladder
        .iter()
        .find(|entry| entry.token.eq_ignore_ascii_case(level))
}

/// Case-insensitive surface-prefix match with a word boundary: the character
/// after the surface must not be a letter, so "Примечание" does not match
/// "Примечания" (plural) or "Примечанием".
fn surface_prefix(text: &str, surface_lower: &str) -> bool {
    let text_lower = text.to_lowercase();
    let Some(rest) = text_lower.strip_prefix(surface_lower) else {
        return false;
    };
    !rest.chars().next().is_some_and(char::is_alphabetic)
}

fn append_line(target: &mut String, line: &str) {
    if target.is_empty() {
        target.push_str(line);
    } else {
        target.push('\n');
        target.push_str(line);
    }
}
