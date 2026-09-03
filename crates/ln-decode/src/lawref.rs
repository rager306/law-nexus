//! LawRef capture layer over the frozen covering lexer (M199 S02, ADR-0028).
//!
//! `LawRef` is the first product reference type: an unresolved capture
//! candidate over a non-empty byte span of the decoded text, carrying the
//! eight protocol slots (S01 annotation protocol §5). It is deliberately
//! NOT a [`crate::lexer::TokenKind`] (the closed nine-kind lexer set stays
//! closed) and deliberately NOT a resolution: identity and anchor fields
//! belong to later steps and are absent here by design - a capture never
//! mints an anchor it cannot prove.
//!
//! Precedence is data (KBO-R025/R030): the `npa_lawref_precedence` table in
//! `prd/architecture/kb-ontology.yaml` is the single canon for pattern ids,
//! frozen lexer start orders, overlap policy, and matcher allowlists. This
//! module only parses and validates that table; matchers (T02) must consume
//! [`LawRefPrecedence`], never a src-side copy of the allowlists. Errors
//! name keys and headings only, never captured source text.

use crate::domain::{ParserDomainError, TextSpan};

/// The eight protocol slots of a captured reference (protocol §5 / SLOT_KEYS).
///
/// Exactly these eight fields, nothing more: identity/anchor fields are
/// absent by design - an `Option` placeholder would still be a false
/// affordance on a capture type.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LawRefSlots {
    /// Ordered abbreviation markers heading the candidate (`ch`, `st`, ...).
    pub marker_chain: Vec<String>,
    /// Hierarchy numbers captured behind the markers (`2`, `15`, `15.1`).
    pub hier_nums: Vec<String>,
    /// `dd.mm.yyyy` capture, when the candidate window holds one.
    pub date: Option<String>,
    /// Document number capture (`318-ФЗ`), when the window holds one.
    pub doc_no: Option<String>,
    /// Exact law-code token (`ФЗ`, `ФКЗ`), when the window holds one.
    pub law_code: Option<String>,
    /// Anaphora head capture (`того же`), unresolved by construction.
    pub anaphora: Option<String>,
    /// Unexpanded range endpoints (`1.1`, `4.1`); ranges never enumerate.
    pub range: Option<(String, String)>,
    /// Quoted subpoint letter (`а`) of a quoted enumeration.
    pub quoted_enum: Option<String>,
}

/// One captured reference candidate over a non-empty byte span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LawRef {
    /// Non-empty half-open byte range on char boundaries.
    pub span: TextSpan,
    /// Closed string id from the `npa_lawref_precedence` YAML table
    /// (KBO-R025/R030: a data table, not a Rust enum, no vocabularies row).
    pub pattern_id: String,
    /// Frozen-lexer kind sequence covering the span (`Abbrev,Space,HierNum`).
    pub token_kind_seq: String,
    /// The eight protocol slots.
    pub slots: LawRefSlots,
}

impl LawRef {
    /// Fail-closed constructor: [`TextSpan::try_new`] rejects an empty or
    /// reversed range, so every candidate provably covers source bytes.
    pub fn try_new(
        start: usize,
        end: usize,
        pattern_id: String,
        token_kind_seq: String,
        slots: LawRefSlots,
    ) -> Result<Self, ParserDomainError> {
        Ok(Self {
            span: TextSpan::try_new(start, end)?,
            pattern_id,
            token_kind_seq,
            slots,
        })
    }

    /// Source slice covered by this candidate. Lexemes are never stored;
    /// spans minted over [`crate::lexer::lex`] output sit on char boundaries.
    pub fn user_text<'s>(&self, src: &'s str) -> &'s str {
        debug_assert!(src.is_char_boundary(self.span.start()));
        debug_assert!(src.is_char_boundary(self.span.end()));
        &src[self.span.start()..self.span.end()]
    }
}

/// Captures reference candidates over `src` through the frozen covering
/// lexer ([`crate::lexer::lex`]).
///
/// T01 ships the capture surface: the call consumes the frozen lexer (the
/// covering token stream is the only text view capture may scan - no regex
/// over raw text, no digit rescan) and returns no candidates yet. T02
/// implements the precedence-table matchers; until then the empty result is
/// the honest stub, not a `todo!` on a library path.
pub fn capture_lawrefs(src: &str) -> Vec<LawRef> {
    let _tokens = crate::lexer::lex(src);
    Vec::new()
}

// ---------------------------------------------------------------------------
// Precedence-as-data (KBO-R025/R030): the npa_lawref_precedence YAML table.
// ---------------------------------------------------------------------------

/// Closed canon of the seven S02 capture patterns. The YAML `pattern_ids`
/// row must carry exactly this set: unknown, duplicate, or missing ids fail
/// closed.
const PATTERN_ID_CANON: [&str; 7] = [
    "abbrev-hier-chain",
    "abbrev-amendment-window",
    "date-docno-window",
    "fullword-ref",
    "quoted-enum",
    "range_candidate",
    "anaphora_candidate",
];

/// Layer A: frozen lexer first-match order on digit-led tokens (ADR-0028
/// step 1). Capture documents the order; it never rescans digits.
const DIGIT_START_ORDER_FROZEN: [&str; 4] = ["Date", "HierNum", "DocNo", "EnumMarker"];

/// Layer A: frozen lexer first-match order on letter-led tokens (abbrev fold
/// match, start-local letter enum marker, alphabetic run classified as an
/// exact law code or a word).
const LETTER_START_ORDER_FROZEN: [&str; 4] = ["Abbrev", "EnumMarker", "LawCode", "Word"];

/// Layer B: candidates order lexicographically by (start, end, pattern_id).
const SORT_KEY_FROZEN: [&str; 3] = ["start", "end", "pattern_id"];

/// Closed overlap-policy vocabulary (layer B). `drop` is the only documented
/// adjudication; anything else fails closed instead of being ignored.
const OVERLAP_POLICIES: [&str; 1] = ["drop"];

/// Closed lexer kind names the layer-A order rows may reference.
const LEXER_KIND_NAMES: [&str; 9] = [
    "Word",
    "Abbrev",
    "HierNum",
    "Date",
    "DocNo",
    "EnumMarker",
    "LawCode",
    "Punct",
    "Space",
];

/// Closed list-valued key set of the `npa_lawref_precedence:` heading.
const LIST_KEYS: [&str; 9] = [
    "pattern_ids",
    "digit_start_order",
    "letter_start_order",
    "sort_key",
    "chain_abbrev_ids",
    "amendment_abbrev_ids",
    "quoted_marker_abbrev_ids",
    "fullword_tails",
    "anaphora_heads",
];

/// Closed scalar-valued key set of the `npa_lawref_precedence:` heading.
const SCALAR_KEYS: [&str; 2] = [
    "overlap_date_docno_inside_amendment",
    "overlap_same_pattern_containment",
];

/// Dotted-key error prefix for the precedence table.
const TABLE: &str = "npa_lawref_precedence";

/// Parsed `npa_lawref_precedence` table - precedence as data (KBO-R025).
///
/// Every field is a closed, validated view of the YAML; T02 matchers must
/// consume this table, never a src-side copy of the allowlists.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LawRefPrecedence {
    pub pattern_ids: Vec<String>,
    pub digit_start_order: Vec<String>,
    pub letter_start_order: Vec<String>,
    pub overlap_date_docno_inside_amendment: String,
    pub overlap_same_pattern_containment: String,
    pub sort_key: Vec<String>,
    pub chain_abbrev_ids: Vec<String>,
    pub amendment_abbrev_ids: Vec<String>,
    pub quoted_marker_abbrev_ids: Vec<String>,
    pub fullword_tails: Vec<String>,
    pub anaphora_heads: Vec<String>,
}

impl LawRefPrecedence {
    /// Parses the embedded ontology YAML
    /// ([`crate::prefix_catalog::EMBEDDED_ONTOLOGY_YAML`]).
    pub fn embedded() -> Result<Self, String> {
        Self::parse_yaml(crate::prefix_catalog::EMBEDDED_ONTOLOGY_YAML)
    }

    /// Fail-closed parse of the `npa_lawref_precedence:` sibling map. Errors
    /// name the offending key or the heading and never carry captured source
    /// text; the library path never panics.
    pub fn parse_yaml(text: &str) -> Result<Self, String> {
        const HEADING: &str = "npa_lawref_precedence:";
        let entries = heading_entries(text, HEADING)?;

        let mut lists: Vec<(String, Vec<String>)> = Vec::new();
        let mut scalars: Vec<(String, String)> = Vec::new();
        for (key, raw) in &entries {
            if LIST_KEYS.contains(&key.as_str()) {
                let items =
                    parse_inline_list(raw).map_err(|err| format!("{TABLE}.{key}: {err}"))?;
                lists.push((key.clone(), items));
            } else if SCALAR_KEYS.contains(&key.as_str()) {
                scalars.push((key.clone(), unquote(raw)));
            } else {
                return Err(format!(
                    "{TABLE}: unknown key '{key}' (closed key set; invented keys fail closed)"
                ));
            }
        }

        let pattern_ids = take_list(&mut lists, "pattern_ids", "the pattern table")?;
        validate_pattern_ids(&pattern_ids)?;

        let digit_start_order = take_list(&mut lists, "digit_start_order", "layer A")?;
        validate_frozen_order(
            &digit_start_order,
            &DIGIT_START_ORDER_FROZEN,
            "digit_start_order",
        )?;
        let letter_start_order = take_list(&mut lists, "letter_start_order", "layer A")?;
        validate_frozen_order(
            &letter_start_order,
            &LETTER_START_ORDER_FROZEN,
            "letter_start_order",
        )?;

        let overlap_date_docno_inside_amendment = take_scalar(
            &mut scalars,
            "overlap_date_docno_inside_amendment",
            "layer B",
        )?;
        validate_overlap_policy(
            &overlap_date_docno_inside_amendment,
            "overlap_date_docno_inside_amendment",
        )?;
        let overlap_same_pattern_containment =
            take_scalar(&mut scalars, "overlap_same_pattern_containment", "layer B")?;
        validate_overlap_policy(
            &overlap_same_pattern_containment,
            "overlap_same_pattern_containment",
        )?;
        let sort_key = take_list(&mut lists, "sort_key", "layer B")?;
        validate_sort_key(&sort_key)?;

        let lexicon = lexicon_ids(text)?;
        let chain_abbrev_ids = take_list(&mut lists, "chain_abbrev_ids", "the matcher allowlists")?;
        validate_abbrev_allowlist(&chain_abbrev_ids, &lexicon, "chain_abbrev_ids")?;
        let amendment_abbrev_ids =
            take_list(&mut lists, "amendment_abbrev_ids", "the matcher allowlists")?;
        validate_abbrev_allowlist(&amendment_abbrev_ids, &lexicon, "amendment_abbrev_ids")?;
        let quoted_marker_abbrev_ids = take_list(
            &mut lists,
            "quoted_marker_abbrev_ids",
            "the matcher allowlists",
        )?;
        validate_abbrev_allowlist(
            &quoted_marker_abbrev_ids,
            &lexicon,
            "quoted_marker_abbrev_ids",
        )?;
        let fullword_tails = take_list(&mut lists, "fullword_tails", "the matcher allowlists")?;
        validate_word_allowlist(&fullword_tails, "fullword_tails")?;
        let anaphora_heads = take_list(&mut lists, "anaphora_heads", "the matcher allowlists")?;
        validate_word_allowlist(&anaphora_heads, "anaphora_heads")?;

        if !lists.is_empty() || !scalars.is_empty() {
            // Unreachable behind the closed key set + duplicate-key guard;
            // kept fail-closed so a future key edit cannot silently drop data.
            return Err(format!(
                "{TABLE}: unhandled keys survived closed-key dispatch"
            ));
        }

        Ok(Self {
            pattern_ids,
            digit_start_order,
            letter_start_order,
            overlap_date_docno_inside_amendment,
            overlap_same_pattern_containment,
            sort_key,
            chain_abbrev_ids,
            amendment_abbrev_ids,
            quoted_marker_abbrev_ids,
            fullword_tails,
            anaphora_heads,
        })
    }
}

fn take_list(
    rows: &mut Vec<(String, Vec<String>)>,
    key: &str,
    layer: &str,
) -> Result<Vec<String>, String> {
    let position = rows
        .iter()
        .position(|(name, _)| name == key)
        .ok_or_else(|| format!("{TABLE}: {layer} is missing key '{key}'"))?;
    Ok(rows.remove(position).1)
}

fn take_scalar(rows: &mut Vec<(String, String)>, key: &str, layer: &str) -> Result<String, String> {
    let position = rows
        .iter()
        .position(|(name, _)| name == key)
        .ok_or_else(|| format!("{TABLE}: {layer} is missing key '{key}'"))?;
    Ok(rows.remove(position).1)
}

fn validate_pattern_ids(pattern_ids: &[String]) -> Result<(), String> {
    const KEY: &str = "npa_lawref_precedence.pattern_ids";
    if pattern_ids.is_empty() {
        return Err(format!("{KEY}: empty pattern table"));
    }
    let mut seen: Vec<&str> = Vec::new();
    for id in pattern_ids {
        if !PATTERN_ID_CANON.contains(&id.as_str()) {
            return Err(format!(
                "{KEY}: unknown pattern id '{id}' (closed seven-pattern canon)"
            ));
        }
        if seen.contains(&id.as_str()) {
            return Err(format!("{KEY}: duplicate pattern id '{id}'"));
        }
        seen.push(id.as_str());
    }
    for id in PATTERN_ID_CANON {
        if !seen.contains(&id) {
            return Err(format!(
                "{KEY}: missing pattern id '{id}' from the closed seven-pattern canon"
            ));
        }
    }
    Ok(())
}

fn validate_frozen_order(order: &[String], frozen: &[&str], key: &str) -> Result<(), String> {
    for kind in order {
        if !LEXER_KIND_NAMES.contains(&kind.as_str()) {
            return Err(format!("{TABLE}.{key}: unknown lexer kind '{kind}'"));
        }
    }
    let got: Vec<&str> = order.iter().map(String::as_str).collect();
    if got != frozen {
        return Err(format!(
            "{TABLE}.{key}: must document the frozen lexer order {frozen:?} (layer A documents the lexer; capture never rescans)"
        ));
    }
    Ok(())
}

fn validate_overlap_policy(value: &str, key: &str) -> Result<(), String> {
    if OVERLAP_POLICIES.contains(&value) {
        return Ok(());
    }
    Err(format!(
        "{TABLE}.{key}: unknown overlap policy '{value}' (closed policy set: drop)"
    ))
}

fn validate_sort_key(sort_key: &[String]) -> Result<(), String> {
    let got: Vec<&str> = sort_key.iter().map(String::as_str).collect();
    if got == SORT_KEY_FROZEN {
        return Ok(());
    }
    Err(format!(
        "{TABLE}.sort_key: must be the frozen candidate order {SORT_KEY_FROZEN:?}"
    ))
}

fn validate_abbrev_allowlist(ids: &[String], lexicon: &[String], key: &str) -> Result<(), String> {
    if ids.is_empty() {
        return Err(format!("{TABLE}.{key}: empty allowlist"));
    }
    let mut seen: Vec<&str> = Vec::new();
    for id in ids {
        if !lexicon.contains(id) {
            return Err(format!(
                "{TABLE}.{key}: id '{id}' is outside npa_abbrev_lexicon"
            ));
        }
        if seen.contains(&id.as_str()) {
            return Err(format!("{TABLE}.{key}: duplicate id '{id}'"));
        }
        seen.push(id.as_str());
    }
    Ok(())
}

fn validate_word_allowlist(words: &[String], key: &str) -> Result<(), String> {
    if words.is_empty() {
        return Err(format!("{TABLE}.{key}: empty allowlist"));
    }
    let mut seen: Vec<&str> = Vec::new();
    for word in words {
        if word.is_empty() {
            return Err(format!("{TABLE}.{key}: empty word entry"));
        }
        if seen.contains(&word.as_str()) {
            return Err(format!("{TABLE}.{key}: duplicate word entry '{word}'"));
        }
        seen.push(word.as_str());
    }
    Ok(())
}

/// Ids of the sibling `npa_abbrev_lexicon:` map: the closed S01 abbreviation
/// canon in data form. Abbrev matcher allowlists are validated against it, so
/// a typo in the precedence table fails closed instead of silently
/// de-sensitizing a T02 matcher - without a second src-side id copy.
fn lexicon_ids(text: &str) -> Result<Vec<String>, String> {
    const HEADING: &str = "npa_abbrev_lexicon:";
    let rows = heading_entries(text, HEADING)
        .map_err(|err| format!("{TABLE}: allowlist validation needs the sibling lexicon: {err}"))?;
    Ok(rows.into_iter().map(|(id, _)| id).collect())
}

/// Hand-rolled sibling-map reader (the private `prefix_catalog` / lexer
/// parser family pattern, no serde): after `heading`, collect `key: raw`
/// rows until the first line whose indent is <= the heading's own (the next
/// sibling key). Comments are stripped by the `#` rule; values stay raw
/// (inline lists included). Errors never panic the library path.
fn heading_entries(text: &str, heading: &str) -> Result<Vec<(String, String)>, String> {
    let mut entries: Vec<(String, String)> = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let line = strip_comment(raw);
        if line.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if !in_map {
            if line.trim() == heading {
                in_map = true;
                heading_indent = indent;
            }
            continue;
        }
        if indent <= heading_indent {
            break;
        }
        let Some((key, value)) = line.trim().split_once(':') else {
            return Err(format!(
                "{heading} non 'key: value' line inside the map (closed scalar/inline-list form only)"
            ));
        };
        let key = key.trim();
        if key.is_empty() {
            return Err(format!("{heading} empty key inside the map"));
        }
        if entries.iter().any(|(name, _)| name == key) {
            return Err(format!("{heading} duplicate key '{key}'"));
        }
        entries.push((key.to_owned(), value.trim().to_owned()));
    }
    if !in_map {
        return Err(format!("{heading} heading is missing"));
    }
    Ok(entries)
}

/// Inline list reader: `[a, b]` with optional quotes, no block lists.
fn parse_inline_list(raw: &str) -> Result<Vec<String>, String> {
    let Some(body) = raw
        .strip_prefix('[')
        .and_then(|value| value.strip_suffix(']'))
    else {
        return Err("must be an inline list ([a, b])".to_owned());
    };
    if body.trim().is_empty() {
        return Ok(Vec::new());
    }
    let mut items = Vec::new();
    for part in body.split(',') {
        let item = unquote(part.trim());
        if item.is_empty() {
            return Err("empty list item".to_owned());
        }
        items.push(item);
    }
    Ok(items)
}

fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => &line[..index],
        None => line,
    }
}

fn unquote(value: &str) -> String {
    value.trim().trim_matches('"').trim_matches('\'').to_owned()
}
