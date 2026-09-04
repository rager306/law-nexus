//! LawRef resolution layer over frozen capture (M199 S03, D350; ADR-0028
//! stays `[proposed]`).
//!
//! The resolved half lives HERE, never on [`crate::lawref::LawRef`]: a
//! capture stays an unresolved candidate (S02 pins
//! `src_lawref_is_capture_type_not_tokenkind` and
//! `freeze_no_parsing_deps_and_no_lawref_tokenkind`), while resolution owns
//! identity and anchors. [`resolve_lawrefs`] consumes
//! [`crate::lawref::capture_lawrefs`] output - it never rescans text, never
//! touches the lexer, and takes its marker-to-eId canon from the
//! `npa_lawref_resolution` YAML table (resolution as data, KBO-R025
//! idiom), so src never hardcodes `статьи -> st` or `st -> art`.
//!
//! T01 ships the surface: [`CanonicalAnchor`], [`ResolvedLawRef`], the
//! parsed [`ResolutionTable`] table view, and the stub resolver that
//! mints nothing yet. T02 implements the chain reverse (ELI 5.4.1:
//! `ч. 1 ст. 42` -> `art_42/par_1`), the in-src context stack, ranges as
//! expanded pairs, and canonical dedup keys; the first-proof contract test
//! stays `#[ignore]`d until then (D373 idiom). R070 stays open:
//! resolution stays lexical, not provenance. Errors name keys, headings,
//! and rules - never captured source text - and the library path never
//! panics.

use crate::lawref::LawRef;

/// Closed eId units of a canonical anchor. `doc` is deliberately absent: it
/// is the non-eId sink value of `anaphora_target_to_level` and is never
/// minted as `doc_*`.
const EID_UNITS: [&str; 7] = ["art", "par", "pnt", "sub", "aln", "chp", "sec"];

// ---------------------------------------------------------------------------
// Resolved types (never fields on LawRef).
// ---------------------------------------------------------------------------

/// One canonical AKN eId anchor: a `/`-joined path of `unit_label` segments.
///
/// [`CanonicalAnchor::try_new`] is fail-closed: non-empty path, no leading
/// `/`, and every segment's unit is one of the closed seven with a `ctx`
/// label, an ASCII `[0-9A-Za-z.]+` label, or one Cyrillic letter (the
/// quoted-enum `а`). Only `path` is stored - never user text.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CanonicalAnchor {
    /// The canonical relative eId path (`art_42/par_1`).
    pub path: String,
}

impl CanonicalAnchor {
    /// Fail-closed constructor; the type docs pin the closed grammar.
    pub fn try_new(path: &str) -> Result<Self, String> {
        if path.is_empty() {
            return Err("canonical anchor: empty path".to_owned());
        }
        if path.starts_with('/') {
            return Err("canonical anchor: leading '/' is not a relative eId path".to_owned());
        }
        for segment in path.split('/') {
            let Some((unit, label)) = segment.split_once('_') else {
                return Err(format!(
                    "canonical anchor: segment '{segment}' is not a unit_label pair"
                ));
            };
            if !EID_UNITS.contains(&unit) {
                return Err(format!(
                    "canonical anchor: unknown eId unit '{unit}' (closed units art|par|pnt|\
                     sub|aln|chp|sec; 'doc' is a non-eId sink and never minted)"
                ));
            }
            if label.is_empty() {
                return Err(format!(
                    "canonical anchor: unit '{unit}' carries an empty label"
                ));
            }
            let label_ok = label == "ctx"
                || label
                    .chars()
                    .all(|ch| ch.is_ascii_alphanumeric() || ch == '.')
                || (label.chars().count() == 1
                    && matches!(label.chars().next(), Some('а'..='я') | Some('ё')));
            if !label_ok {
                return Err(format!(
                    "canonical anchor: label '{label}' is not 'ctx', an ASCII number/word \
                     label, or one Cyrillic letter"
                ));
            }
        }
        Ok(Self {
            path: path.to_owned(),
        })
    }
}

/// One resolved reference: the frozen capture plus what resolution proved.
///
/// `anchor: None` is an honestly unresolved capture - the resolver never
/// invents an anchor it cannot prove from the table. `members` carries the
/// expanded-pair range endpoints once ranges resolve (T02); `dedup_key`
/// carries the canonical grouping key when written variants of one
/// reference collapse (T03).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedLawRef {
    /// The untouched S02 capture candidate.
    pub capture: LawRef,
    /// Canonical anchor; `None` = honestly unresolved.
    pub anchor: Option<CanonicalAnchor>,
    /// Expanded-pair range members (empty outside a resolved range).
    pub members: Vec<CanonicalAnchor>,
    /// Canonical dedup key when variants group; `None` while unresolved.
    pub dedup_key: Option<String>,
}

/// Resolves captured reference candidates against the embedded
/// `npa_lawref_resolution` table.
///
/// T01 stub: capture runs first (the resolver consumes frozen captures, it
/// never rescans text), the embedded-table failure idiom is wired (same
/// leftover-#5 idiom as capture: a build-data defect degrades to "no
/// resolutions", never panics a caller), and nothing is minted yet - T02
/// implements the chain reverse, the context stack, ranges, and dedup.
/// The library path never unwinds and `src` is never logged.
pub fn resolve_lawrefs(src: &str) -> Vec<ResolvedLawRef> {
    let captures = crate::lawref::capture_lawrefs(src);
    if captures.is_empty() {
        return Vec::new();
    }
    let Ok(_resolution) = ResolutionTable::embedded() else {
        return Vec::new();
    };
    // T02 mints `ResolvedLawRef` from `captures` + `resolution` here.
    Vec::new()
}

// ---------------------------------------------------------------------------
// Resolution as data (KBO-R025 idiom): the npa_lawref_resolution YAML table.
// ---------------------------------------------------------------------------

/// Dotted-key error prefix for the resolution table.
const TABLE: &str = "npa_lawref_resolution";

/// Closed map-valued key set of the heading.
const MAP_KEYS: [&str; 3] = [
    "marker_to_eid",
    "inflected_tail_to_marker",
    "anaphora_target_to_level",
];

/// Closed scalar-valued key set of the heading.
const SCALAR_KEYS: [&str; 2] = ["range_policy", "eid_start_at"];

/// Closed list-valued key set of the heading.
const LIST_KEYS: [&str; 1] = ["sort_key"];

/// The only range policy: ranges stay an expanded endpoint pair, never an
/// integer enumeration.
const RANGE_POLICY: &str = "expanded_pair";

/// Canonical anchors always start at the article unit (ELI 5.4.1).
const EID_START: &str = "art";

/// Frozen canonical sort/dedup order for anchors.
const SORT_KEY_FROZEN: [&str; 3] = ["start", "end", "path"];

/// The non-eId sink level of `anaphora_target_to_level`: document-level
/// anaphora resolves to the document, never to a minted `doc_*` anchor.
const DOC_SINK: &str = "doc";

/// Parsed `npa_lawref_resolution` table - resolution as data (KBO-R025
/// idiom). Every field is a closed, validated view of the YAML; T02 must
/// consume this table, never a src-side copy of the mappings. Named
/// `ResolutionTable` (not `LawRefResolution`): the S02 pin
/// `src_lawref_is_capture_type_not_tokenkind` forbids LawRef type
/// declarations in any src file outside `src/lawref.rs`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolutionTable {
    /// Marker id -> eId unit (`ch -> par`, `pp -> pnt`); keys are
    /// `npa_abbrev_lexicon` ids, values from the closed seven-unit set.
    pub marker_to_eid: Vec<(String, String)>,
    /// Inflected fullword tail -> marker id (`статьи -> st`).
    pub inflected_tail_to_marker: Vec<(String, String)>,
    /// Anaphora target -> marker id or the `doc` sink (`Кодекса -> doc`).
    pub anaphora_target_to_level: Vec<(String, String)>,
    /// Pinned `expanded_pair`.
    pub range_policy: String,
    /// Pinned `art`: canonical anchors start at the article unit.
    pub eid_start_at: String,
    /// Pinned canonical order `[start, end, path]`.
    pub sort_key: Vec<String>,
}

impl ResolutionTable {
    /// Parses the embedded tracked ontology.
    pub fn embedded() -> Result<Self, String> {
        Self::parse_yaml(crate::prefix_catalog::EMBEDDED_ONTOLOGY_YAML)
    }

    /// Fail-closed parse of the `npa_lawref_resolution` heading. Errors name
    /// the key or heading - never captured source text. Duplicate and
    /// unknown keys fail closed; every value is validated against its
    /// closed set (marker ids must exist in the sibling
    /// `npa_abbrev_lexicon`).
    pub fn parse_yaml(text: &str) -> Result<Self, String> {
        const HEADING: &str = "npa_lawref_resolution:";
        let entries = heading_entries(text, HEADING)?;

        let mut maps: Vec<(String, Vec<(String, String)>)> = Vec::new();
        let mut scalars: Vec<(String, String)> = Vec::new();
        let mut lists: Vec<(String, Vec<String>)> = Vec::new();
        for (key, raw) in &entries {
            if MAP_KEYS.contains(&key.as_str()) {
                let rows = parse_inline_map(raw).map_err(|err| format!("{TABLE}.{key}: {err}"))?;
                maps.push((key.clone(), rows));
            } else if LIST_KEYS.contains(&key.as_str()) {
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

        let marker_to_eid = take_map(&mut maps, "marker_to_eid")?;
        let inflected_tail_to_marker = take_map(&mut maps, "inflected_tail_to_marker")?;
        let anaphora_target_to_level = take_map(&mut maps, "anaphora_target_to_level")?;
        let range_policy = take_scalar(&mut scalars, "range_policy")?;
        let eid_start_at = take_scalar(&mut scalars, "eid_start_at")?;
        let sort_key = take_list(&mut lists, "sort_key")?;

        if !maps.is_empty() || !scalars.is_empty() || !lists.is_empty() {
            return Err(format!(
                "{TABLE}: unhandled keys survived closed-key dispatch"
            ));
        }

        let lexicon = lexicon_ids(text)?;
        validate_marker_to_eid(&marker_to_eid, &lexicon)?;
        validate_inflected_tail_to_marker(&inflected_tail_to_marker, &lexicon)?;
        validate_anaphora_target_to_level(&anaphora_target_to_level, &lexicon)?;

        if range_policy != RANGE_POLICY {
            return Err(format!(
                "{TABLE}.range_policy: unknown range policy '{range_policy}' \
                 (closed policy: {RANGE_POLICY})"
            ));
        }
        if eid_start_at != EID_START {
            return Err(format!(
                "{TABLE}.eid_start_at: unknown anchor start unit '{eid_start_at}' \
                 (closed unit: {EID_START})"
            ));
        }
        if sort_key.is_empty() {
            return Err(format!("{TABLE}.sort_key: empty sort key"));
        }
        let got: Vec<&str> = sort_key.iter().map(String::as_str).collect();
        if got != SORT_KEY_FROZEN {
            return Err(format!(
                "{TABLE}.sort_key: must be the frozen canonical order {SORT_KEY_FROZEN:?}"
            ));
        }

        Ok(Self {
            marker_to_eid,
            inflected_tail_to_marker,
            anaphora_target_to_level,
            range_policy,
            eid_start_at,
            sort_key,
        })
    }
}

fn validate_marker_to_eid(rows: &[(String, String)], lexicon: &[String]) -> Result<(), String> {
    const KEY: &str = "npa_lawref_resolution.marker_to_eid";
    if rows.is_empty() {
        return Err(format!("{KEY}: empty marker table"));
    }
    for (marker, unit) in rows {
        if !lexicon.contains(marker) {
            return Err(format!(
                "{KEY}: id '{marker}' is outside npa_abbrev_lexicon"
            ));
        }
        if !EID_UNITS.contains(&unit.as_str()) {
            return Err(format!(
                "{KEY}: unknown eId unit '{unit}' (closed units art|par|pnt|sub|aln|chp|sec; \
                 '{DOC_SINK}' is a non-eId sink and never minted)"
            ));
        }
    }
    Ok(())
}

fn validate_inflected_tail_to_marker(
    rows: &[(String, String)],
    lexicon: &[String],
) -> Result<(), String> {
    const KEY: &str = "npa_lawref_resolution.inflected_tail_to_marker";
    if rows.is_empty() {
        return Err(format!("{KEY}: empty tail table"));
    }
    for (tail, marker) in rows {
        if !is_inflected_form(tail) {
            return Err(format!(
                "{KEY}: tail '{tail}' is not a Cyrillic inflected form"
            ));
        }
        if !lexicon.contains(marker) {
            return Err(format!(
                "{KEY}: marker '{marker}' is outside npa_abbrev_lexicon"
            ));
        }
    }
    Ok(())
}

fn validate_anaphora_target_to_level(
    rows: &[(String, String)],
    lexicon: &[String],
) -> Result<(), String> {
    const KEY: &str = "npa_lawref_resolution.anaphora_target_to_level";
    if rows.is_empty() {
        return Err(format!("{KEY}: empty target table"));
    }
    for (target, level) in rows {
        if !is_inflected_form(target) {
            return Err(format!(
                "{KEY}: target '{target}' is not a Cyrillic inflected form"
            ));
        }
        if level != DOC_SINK && !lexicon.contains(level) {
            return Err(format!(
                "{KEY}: level '{level}' is neither a marker id nor the '{DOC_SINK}' sink"
            ));
        }
    }
    Ok(())
}

/// An inflected tail or anaphora target must be a non-empty word of
/// Cyrillic letters (any case, `ё` included). Latin, digits, and mixed
/// forms fail closed.
fn is_inflected_form(word: &str) -> bool {
    !word.is_empty()
        && word
            .chars()
            .all(|ch| matches!(ch, 'а'..='я' | 'А'..='Я' | 'ё' | 'Ё'))
}

fn lexicon_ids(text: &str) -> Result<Vec<String>, String> {
    const HEADING: &str = "npa_abbrev_lexicon:";
    let rows = heading_entries(text, HEADING)
        .map_err(|err| format!("{TABLE}: marker validation needs the sibling lexicon: {err}"))?;
    Ok(rows.into_iter().map(|(id, _)| id).collect())
}

fn take_map(
    rows: &mut Vec<(String, Vec<(String, String)>)>,
    key: &str,
) -> Result<Vec<(String, String)>, String> {
    let position = rows
        .iter()
        .position(|(name, _)| name == key)
        .ok_or_else(|| format!("{TABLE}: the resolution table is missing key '{key}'"))?;
    Ok(rows.remove(position).1)
}

fn take_scalar(rows: &mut Vec<(String, String)>, key: &str) -> Result<String, String> {
    let position = rows
        .iter()
        .position(|(name, _)| name == key)
        .ok_or_else(|| format!("{TABLE}: the resolution table is missing key '{key}'"))?;
    Ok(rows.remove(position).1)
}

fn take_list(rows: &mut Vec<(String, Vec<String>)>, key: &str) -> Result<Vec<String>, String> {
    let position = rows
        .iter()
        .position(|(name, _)| name == key)
        .ok_or_else(|| format!("{TABLE}: the resolution table is missing key '{key}'"))?;
    Ok(rows.remove(position).1)
}

// ---------------------------------------------------------------------------
// Private sibling-map reader family. Deliberately duplicated from
// `src/lawref.rs` (which stays capture-only and private): resolution never
// widens the capture module's surface. Same hand-rolled, zero-dependency
// style as `prefix_catalog` (no serde).
// ---------------------------------------------------------------------------

/// Cuts a YAML line at the first `#` (comment), unquoted `#` never occurs in
/// this closed table.
fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => &line[..index],
        None => line,
    }
}

/// Removes symmetric surrounding double quotes, if any.
fn unquote(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.len() >= 2 && trimmed.starts_with('"') && trimmed.ends_with('"') {
        trimmed[1..trimmed.len() - 1].to_owned()
    } else {
        trimmed.to_owned()
    }
}

/// Collects the `key: value` rows of one indented heading block, until a
/// line at the heading's own indent (or shallower) ends the block.
fn heading_entries(text: &str, heading: &str) -> Result<Vec<(String, String)>, String> {
    let mut entries = Vec::new();
    let mut in_map = false;
    let heading_indent = text
        .lines()
        .find(|line| line.trim() == heading)
        .map(|line| line.len() - line.trim_start().len())
        .ok_or_else(|| format!("{heading} heading is missing"))?;
    for raw in text.lines() {
        let line = strip_comment(raw);
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if !in_map {
            if trimmed == heading {
                in_map = true;
            }
            continue;
        }
        let indent = line.len() - line.trim_start().len();
        if indent <= heading_indent {
            break;
        }
        let Some((key, value)) = trimmed.split_once(':') else {
            return Err(format!(
                "{heading} non 'key: value' line inside the map (closed-form rows only)"
            ));
        };
        let key = key.trim();
        if entries.iter().any(|(name, _)| name == key) {
            return Err(format!("{heading} duplicate key '{key}'"));
        }
        if key.is_empty() {
            return Err(format!("{heading} empty key"));
        }
        entries.push((key.to_owned(), value.trim().to_owned()));
    }
    if !in_map {
        return Err(format!("{heading} heading is missing"));
    }
    Ok(entries)
}

/// Parses an inline list `[a, b, c]`; the empty body yields an empty vec.
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

/// Parses an inline map `{k: v, k2: v2}`; the empty body yields an empty
/// vec (downstream validation decides whether an empty table is legal).
fn parse_inline_map(raw: &str) -> Result<Vec<(String, String)>, String> {
    let Some(body) = raw
        .strip_prefix('{')
        .and_then(|value| value.strip_suffix('}'))
    else {
        return Err("must be an inline map ({k: v, ...})".to_owned());
    };
    if body.trim().is_empty() {
        return Ok(Vec::new());
    }
    let mut entries: Vec<(String, String)> = Vec::new();
    for part in body.split(',') {
        let Some((key, value)) = part.split_once(':') else {
            return Err("inline map entries must be 'k: v'".to_owned());
        };
        let key = unquote(key.trim());
        let value = unquote(value.trim());
        if key.is_empty() {
            return Err("empty inline map key".to_owned());
        }
        if value.is_empty() {
            return Err("empty inline map value".to_owned());
        }
        if entries.iter().any(|(name, _)| name == &key) {
            return Err(format!("duplicate key '{key}'"));
        }
        entries.push((key, value));
    }
    Ok(entries)
}
