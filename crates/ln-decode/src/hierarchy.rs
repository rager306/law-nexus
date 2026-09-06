//! Bounded provider-neutral hierarchy extraction from decoded block text.

use crate::domain::{HierarchyLevel, HierarchyNode, ParagraphStyle, ParsedBlock, TextSpan};
use crate::prefix_catalog::{DecodePrefixCatalog, NumberStyle, NumberedStyle, SpacePolicy};

/// Extract a supported hierarchy marker at the start of decoded block text.
///
/// Structural-only role tokens (primechanie/prilozhenie, R8-09) have no
/// `HierarchyLevel` — "Примечание"/"Приложение" markers are recognized by
/// the profile collector's catalog `surface` prefix (article_body.rs), never
/// here. A bare surface marker ("Приложение" without a number) is Unknown.
///
/// This function intentionally does not translate decoded [`TextSpan`] values
/// into source-stream coordinates. The owning [`ParsedBlock`] retains its
/// separate [`crate::domain::SourceLocation`] for an adapter to map with
/// additional evidence.
pub fn extract_hierarchy(block: &ParsedBlock) -> Option<HierarchyNode> {
    let text = block.text();
    let marker_start = text
        .char_indices()
        .find_map(|(index, character)| (!character.is_whitespace()).then_some(index))?;
    let candidate = &text[marker_start..];
    // Try explicit prefixes first (Статья, Глава), then numbered markers (1. 1) а))
    let (level, number_start) =
        marker_prefix(candidate).or_else(|| numbered_marker_prefix(candidate))?;
    let number_end = number_end(candidate, number_start, level)?;
    let number = &candidate[number_start..number_end];
    let punctuation = candidate.as_bytes().get(number_end).copied()?;
    // Accept '.', ':' (explicit prefixes) and ')' (numbered Punkt/Podpunkt markers)
    if !matches!(punctuation, b'.' | b':' | b')') {
        return None;
    }

    let marker_end = marker_start + number_end + 1;
    let suffix = &text[marker_end..];
    if suffix
        .chars()
        .next()
        .is_some_and(|character| !character.is_whitespace())
    {
        return None;
    }
    let title = suffix.trim();
    HierarchyNode::try_new(
        level,
        number.to_owned(),
        (!title.is_empty()).then(|| title.to_owned()),
        text.to_owned(),
        TextSpan::try_new(marker_start, marker_end).ok()?,
    )
    .ok()
}

/// Catalog token for a hierarchy level: lowercase decode-level aliases
/// mirroring the `decode_level_aliases` values in `kb-ontology.yaml`
/// (`statya`, not `Statya`). The Title-case [`HierarchyLevel::as_str`]
/// decode-facing contract stays pinned by `parser_domain_contract` and is
/// deliberately not reused here.
pub fn catalog_token(level: HierarchyLevel) -> &'static str {
    match level {
        HierarchyLevel::Razdel => "razdel",
        HierarchyLevel::Glava => "glava",
        HierarchyLevel::Paragraph => "paragraph",
        HierarchyLevel::Statya => "statya",
        HierarchyLevel::Chast => "chast",
        HierarchyLevel::Punkt => "punkt",
        HierarchyLevel::Podpunkt => "podpunkt",
    }
}

/// One extraction candidate: a validated hierarchy marker plus its
/// catalog-token ladder path. Carries identifiers only — never raw block
/// text. A candidate is a proposal, not a binding: it mints no
/// ComponentConcept, writes no YAML and holds no legal authority (see
/// [`HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS`]).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyCandidate {
    level: HierarchyLevel,
    number: String,
    /// Slash-joined non-container ladder path (`statya-4/punkt-1`);
    /// `None` when flat (D192).
    path: Option<String>,
    /// Registry identity key: ladder path when nested, bare number when flat.
    key_path: String,
    title: Option<String>,
    marker_span: TextSpan,
}

impl HierarchyCandidate {
    pub fn level(&self) -> HierarchyLevel {
        self.level
    }

    /// Lowercase catalog token (`punkt`), not the Rust variant name.
    pub fn catalog_token(&self) -> &'static str {
        catalog_token(self.level)
    }

    pub fn number(&self) -> &str {
        &self.number
    }

    /// Ladder path; `None` when flat (containers and single segments, D192).
    pub fn path(&self) -> Option<&str> {
        self.path.as_deref()
    }

    /// Identity key: [`Self::path`] when nested, bare [`Self::number`] when flat.
    pub fn key_path(&self) -> &str {
        &self.key_path
    }

    /// Ladder path segment count; 1 when flat.
    pub fn depth(&self) -> usize {
        self.path
            .as_deref()
            .map(|path| path.split('/').count())
            .unwrap_or(1)
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    /// Marker span in decoded block text, unchanged from [`extract_hierarchy`].
    pub fn marker_span(&self) -> TextSpan {
        self.marker_span
    }
}

/// Typed extraction diagnostics. Identifiers only — variants must never
/// carry raw block text (same fail-closed rule as the other decode types).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HierarchyExtractDiagnostic {
    /// A later hit repeated an already-emitted `(level, key_path)` and was
    /// skipped (first-wins). Indices address the raw document-order
    /// extracted hit stream (duplicates included).
    DuplicateKey {
        level: HierarchyLevel,
        key_path: String,
        first_index: usize,
        later_index: usize,
    },
}

/// Extraction-only report over a decoded block stream: unique candidates in
/// document order, typed diagnostics and raw hit counts. Never legal truth
/// and never registry input on its own.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyCandidateReport {
    candidates: Vec<HierarchyCandidate>,
    diagnostics: Vec<HierarchyExtractDiagnostic>,
    extracted: usize,
}

impl HierarchyCandidateReport {
    /// D185 extraction boundary carried on the type itself: what these
    /// candidates are NOT. Any admission of them is a separate gated step.
    pub const HIERARCHY_CANDIDATE_NON_CLAIMS: &'static [&'static str] = &[
        "Candidates are not ComponentConcept and never mint ComponentConcept identifiers (Review 4).",
        "Candidates are not kb-hierarchy-registry.yaml and are never auto-applied as YAML (D185).",
        "Candidates are never admitted to the registry: admission is a separate human-gated step.",
        "Candidates are not legal hierarchy truth: not InForce, not Applicable, not authority.",
    ];

    /// First-wins unique candidates in document order.
    pub fn candidates(&self) -> &[HierarchyCandidate] {
        &self.candidates
    }

    /// Typed diagnostics in document order.
    pub fn diagnostics(&self) -> &[HierarchyExtractDiagnostic] {
        &self.diagnostics
    }

    /// Raw document-order [`extract_hierarchy`] hits, duplicates included.
    /// `ProviderComment` blocks are excluded before this count.
    pub fn extracted_count(&self) -> usize {
        self.extracted
    }

    /// Unique candidate count (always `candidates().len()`).
    pub fn unique_count(&self) -> usize {
        self.candidates.len()
    }
}

/// Fold [`extract_hierarchy`] over decoded blocks in document order and
/// build catalog-token ladder-path candidate bindings.
///
/// `ParagraphStyle::ProviderComment` blocks are skipped by style before
/// extraction (provider comments are not structure; aligned with inspect)
/// and never inflate counts. Blocks without a hierarchy marker are silent
/// skips, not errors or diagnostics. Candidates are unique first-wins by
/// `(level, key_path)`; every skipped repeat emits one
/// [`HierarchyExtractDiagnostic::DuplicateKey`]. Extraction only: never
/// mints ComponentConcepts, never writes YAML, never performs registry
/// admission — see
/// [`HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS`].
pub fn extract_hierarchy_candidates(blocks: &[ParsedBlock]) -> HierarchyCandidateReport {
    let mut ladder: Vec<(HierarchyLevel, String)> = Vec::new();
    let mut seen: Vec<(HierarchyLevel, String, usize)> = Vec::new();
    let mut candidates: Vec<HierarchyCandidate> = Vec::new();
    let mut diagnostics: Vec<HierarchyExtractDiagnostic> = Vec::new();
    let mut extracted = 0usize;

    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        let Some(node) = extract_hierarchy(block) else {
            continue;
        };
        extracted += 1;
        let hit_index = extracted - 1;
        let level = node.level();
        let number = node.number().to_owned();

        // Pop while the top is at or below the incoming level, then push:
        // the ladder stays nested in document order (R8-11).
        let own_depth = level_depth(level);
        while ladder
            .last()
            .is_some_and(|(top, _)| level_depth(*top) >= own_depth)
        {
            ladder.pop();
        }
        ladder.push((level, number.clone()));

        // Non-container segments form the catalog-token ladder path; a
        // single-segment path stays flat (D192: key defaults to number).
        let path = ladder
            .iter()
            .filter(|(top, _)| !is_container_level(*top))
            .map(|(top, top_number)| format!("{}-{top_number}", catalog_token(*top)))
            .collect::<Vec<_>>()
            .join("/");
        let path = (path.split('/').count() >= 2).then_some(path);
        let key_path = path.clone().unwrap_or_else(|| number.clone());

        if let Some((_, _, first_index)) =
            seen.iter().find(|(existing_level, existing_key_path, _)| {
                *existing_level == level && existing_key_path == &key_path
            })
        {
            diagnostics.push(HierarchyExtractDiagnostic::DuplicateKey {
                level,
                key_path,
                first_index: *first_index,
                later_index: hit_index,
            });
            continue;
        }
        seen.push((level, key_path.clone(), hit_index));
        candidates.push(HierarchyCandidate {
            level,
            number,
            path,
            key_path,
            title: node.title().map(str::to_owned),
            marker_span: node.marker_span(),
        });
    }

    HierarchyCandidateReport {
        candidates,
        diagnostics,
        extracted,
    }
}

/// Container levels never enter a ladder path (R8-11 / D192:
/// `statya-93/punkt-4` has no `glava-3/...` prefix).
fn is_container_level(level: HierarchyLevel) -> bool {
    matches!(
        level,
        HierarchyLevel::Razdel | HierarchyLevel::Glava | HierarchyLevel::Paragraph
    )
}

/// Enum order is nesting depth (`Razdel < ... < Podpunkt`). The
/// `usize::MAX` fallback is defensive only — `extract_hierarchy` returns
/// the closed 7-set — and behaves as a fail-closed reset.
fn level_depth(level: HierarchyLevel) -> usize {
    HierarchyLevel::all()
        .iter()
        .position(|candidate| *candidate == level)
        .unwrap_or(usize::MAX)
}

fn marker_prefix(candidate: &str) -> Option<(HierarchyLevel, usize)> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    for rule in &catalog.prefixes {
        let Some(rest) = candidate.strip_prefix(rule.marker.as_str()) else {
            continue;
        };
        let whitespace_len = rest
            .char_indices()
            .take_while(|(_, character)| character.is_whitespace())
            .map(|(_, character)| character.len_utf8())
            .sum::<usize>();
        let space_ok = match rule.space {
            SpacePolicy::Required => whitespace_len > 0,
            SpacePolicy::Optional => true,
        };
        if space_ok {
            return Some((rule.level, rule.marker.len() + whitespace_len));
        }
    }
    None
}

fn number_end(candidate: &str, start: usize, level: HierarchyLevel) -> Option<usize> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    let style = catalog.number_style(level)?;
    let bytes = candidate.as_bytes();
    let first = *bytes.get(start)?;
    if first.is_ascii_digit() {
        let mut end = start;
        while let Some(byte) = bytes.get(end) {
            if byte.is_ascii_digit()
                || (*byte == b'.' && bytes.get(end + 1).is_some_and(u8::is_ascii_digit))
            {
                end += 1;
            } else {
                break;
            }
        }
        return (end > start).then_some(end);
    }
    if style != NumberStyle::RomanOrDigit {
        return None;
    }
    let mut end = start;
    while bytes.get(end).is_some_and(|byte| {
        matches!(
            byte.to_ascii_uppercase(),
            b'I' | b'V' | b'X' | b'L' | b'C' | b'D' | b'M'
        )
    }) {
        end += 1;
    }
    (end > start).then_some(end)
}

/// Try to match a numbered-list pattern (digit., digit), letter)) as a hierarchy marker.
/// Falls back when explicit prefixes (Статья, Глава) don't match.
/// All matching logic is driven by YAML NumberedMarkerRule fields.
fn numbered_marker_prefix(candidate: &str) -> Option<(HierarchyLevel, usize)> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    let first_byte = candidate.as_bytes().first()?;
    for rule in &catalog.numbered_markers {
        let matches = match rule.number_style {
            NumberedStyle::Digit => first_byte.is_ascii_digit(),
            NumberedStyle::LetterCyrillic => {
                candidate.starts_with(|c: char| ('а'..='я').contains(&c))
            }
        };
        if !matches {
            continue;
        }
        // Walk the number: digits, and optionally dots-between-digits (YAML allow_compound)
        let bytes = candidate.as_bytes();
        let mut end = 0;
        while end < bytes.len() {
            let is_digit = bytes[end].is_ascii_digit();
            let is_compound_dot = rule.allow_compound
                && bytes[end] == b'.'
                && bytes.get(end + 1).is_some_and(u8::is_ascii_digit);
            if is_digit || is_compound_dot {
                end += 1;
            } else {
                break;
            }
        }
        if end == 0 {
            continue;
        }
        // Check that the suffix matches
        if let Some(&suffix_byte) = bytes.get(end) {
            if suffix_byte as char == rule.suffix {
                return Some((rule.level, 0));
            }
        }
    }
    None
}
