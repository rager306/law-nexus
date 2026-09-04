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
//! T02 lifted the stub to behavior: the chain reverse (ELI 5.4.1:
//! `ч. 1 ст. 42` -> `art_42/par_1`), the per-src context stack, and
//! anaphora binding with `art_ctx` as the honest missing-frame token. T03
//! adds the range half (`range_policy: expanded_pair`): a range resolves
//! as the expanded ENDPOINT PAIR of one left-scanned unit - never an
//! integer enumeration - the false hyphen-split range stays unresolved,
//! and resolved references group under the canonical dedup key (an anchor
//! path, or the literal `from..to` range key). R070 stays open:
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
/// expanded-pair endpoints of a resolved range (exactly two anchors - never
/// an enumeration); `dedup_key` carries the canonical grouping key under
/// which written variants of one reference collapse: the anchor path for
/// single-anchor resolutions, the literal `from..to` key for a range.
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
/// Capture runs first (the resolver consumes frozen captures), the
/// embedded table is loaded once per call, and captures are walked in the
/// frozen `(start, end, pattern_id)` capture order so the per-src context
/// stack sees references in source order. One [`crate::lexer::lex`] of the
/// whole src backs the range left-scan - the covering token stream stays
/// the only text view resolution scans. A build-data defect degrades to
/// "no resolutions" - never panics a caller (same leftover-#5 idiom as
/// capture). Every unresolved outcome is honest: `anchor = None` for
/// document-level anaphora, unknown heads, amendment/date windows, false
/// ranges (equal endpoints continuing a hyphen split), and ranges whose
/// unit nothing proves; `{unit}_ctx` tokens for anaphora whose level has
/// no prior frame in the same src. The library path never unwinds and
/// `src` is never logged.
pub fn resolve_lawrefs(src: &str) -> Vec<ResolvedLawRef> {
    let captures = crate::lawref::capture_lawrefs(src);
    if captures.is_empty() {
        return Vec::new();
    }
    let Ok(resolution) = ResolutionTable::embedded() else {
        return Vec::new();
    };
    let tokens = crate::lexer::lex(src);
    let mut stack: Vec<Frame> = Vec::new();
    let mut resolved = Vec::with_capacity(captures.len());
    for (index, capture) in captures.iter().enumerate() {
        let outcome = resolve_capture(
            capture,
            index,
            &captures,
            src,
            &tokens,
            &resolution,
            &mut stack,
        );
        resolved.push(ResolvedLawRef {
            capture: capture.clone(),
            anchor: outcome.anchor,
            members: outcome.members,
            dedup_key: outcome.dedup_key,
        });
    }
    resolved
}

// ---------------------------------------------------------------------------
// T02 resolution engine: chain reverse, per-src context stack, anaphora
// bind. Private on purpose - the public surface is `resolve_lawrefs` plus
// the T01 types.
// ---------------------------------------------------------------------------

/// One context frame on the per-src stack: a minted `(unit, number)` pair
/// later anaphora binds against (eyecite-style stack update; per call,
/// never process-global, never a `ParsedBlock`).
#[derive(Debug, Clone, PartialEq, Eq)]
struct Frame {
    unit: String,
    num: String,
}

impl Frame {
    /// The frame's `unit_label` path form (`art_42`).
    fn path(&self) -> String {
        format!("{}_{}", self.unit, self.num)
    }
}

/// Structural position below the article for chain-path emission (ELI
/// 5.4.1 order `art > par > pnt > sub > aln`). `chp`/`sec` sit above
/// `eid_start_at` and return `None`: they drop out of a minted path while
/// their frames still feed the context stack.
fn below_art_rank(unit: &str) -> Option<usize> {
    match unit {
        "art" => Some(0),
        "par" => Some(1),
        "pnt" => Some(2),
        "sub" => Some(3),
        "aln" => Some(4),
        _ => None,
    }
}

/// Value of `key` in a table's `(key, value)` rows (table lookups only -
/// the mappings live in the YAML table, never in src).
fn table_lookup<'t>(rows: &'t [(String, String)], key: &str) -> Option<&'t str> {
    rows.iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.as_str())
}

/// Canonical `/`-joined path of the below-art frames in hierarchy order
/// (stable for equal ranks). `None` when no frame sits below the article:
/// a chain that never named an article-relative unit cannot mint a path
/// (its frames are still pushed).
fn ranked_path(frames: &[Frame]) -> Option<String> {
    let mut ranked: Vec<&Frame> = frames
        .iter()
        .filter(|frame| below_art_rank(&frame.unit).is_some())
        .collect();
    if ranked.is_empty() {
        return None;
    }
    ranked.sort_by_key(|frame| below_art_rank(&frame.unit));
    Some(
        ranked
            .iter()
            .map(|frame| frame.path())
            .collect::<Vec<_>>()
            .join("/"),
    )
}

/// What one capture resolved to.
struct Outcome {
    anchor: Option<CanonicalAnchor>,
    members: Vec<CanonicalAnchor>,
    dedup_key: Option<String>,
}

impl Outcome {
    /// Honestly unresolved: no anchor, no members, no dedup key.
    fn unresolved() -> Self {
        Self {
            anchor: None,
            members: Vec::new(),
            dedup_key: None,
        }
    }

    /// A single-anchor resolution (chain, fullword, anaphora, quoted
    /// enum): the dedup key is the anchor path itself.
    fn anchored(anchor: Option<CanonicalAnchor>) -> Self {
        Self {
            dedup_key: anchor.as_ref().map(|anchor| anchor.path.clone()),
            anchor,
            members: Vec::new(),
        }
    }
}

/// Resolves one capture against the table and the current frame stack,
/// pushing newly minted frames. `index`/`captures` back the range
/// look-ahead and `tokens` backs its left-scan. Pattern ids mirror the
/// closed seven-pattern capture canon; the library path never panics and
/// never logs - every failure degrades to an unresolved outcome.
fn resolve_capture(
    capture: &LawRef,
    index: usize,
    captures: &[LawRef],
    src: &str,
    tokens: &[crate::lexer::NpaToken],
    resolution: &ResolutionTable,
    stack: &mut Vec<Frame>,
) -> Outcome {
    match capture.pattern_id.as_str() {
        "abbrev-hier-chain" => Outcome::anchored(resolve_chain(capture, resolution, stack)),
        "fullword-ref" => Outcome::anchored(resolve_fullword(capture, src, resolution, stack)),
        "anaphora_candidate" => {
            Outcome::anchored(resolve_anaphora(capture, src, resolution, stack))
        }
        "quoted-enum" => Outcome::anchored(resolve_quoted_enum(capture, src, resolution, stack)),
        // Amendment / date-docno windows stay out of resolution scope (R070).
        "abbrev-amendment-window" | "date-docno-window" => Outcome::unresolved(),
        "range_candidate" => {
            resolve_range(capture, index, captures, src, tokens, resolution, stack)
        }
        // The seven-pattern canon makes this unreachable; a future pattern
        // id fails closed instead of minting an unproven anchor.
        _ => Outcome::unresolved(),
    }
}

/// Chain reverse (ELI 5.4.1, load-bearing): pairs `(marker[i], num[i])` in
/// source order - capture writes `ч.` then `ст.` and `1` then `42`, the
/// canonical path is outer-first starting at the article - maps every
/// marker through `marker_to_eid`, pushes all minted frames onto the
/// stack, and mints the path from the below-art frames in hierarchy
/// order. `[ch, st] + [1, 42]` mints `art_42/par_1`; a lone `разд. 2`
/// pushes `(sec, 2)` and mints no path (`eid_start_at: art`); dotted
/// numbers stay dotted and are never split.
fn resolve_chain(
    capture: &LawRef,
    resolution: &ResolutionTable,
    stack: &mut Vec<Frame>,
) -> Option<CanonicalAnchor> {
    let markers = &capture.slots.marker_chain;
    let nums = &capture.slots.hier_nums;
    if markers.len() != nums.len() {
        return None;
    }
    let mut frames = Vec::with_capacity(markers.len());
    for (marker, num) in markers.iter().zip(nums.iter()) {
        let unit = table_lookup(&resolution.marker_to_eid, marker)?;
        frames.push(Frame {
            unit: unit.to_owned(),
            num: num.clone(),
        });
    }
    let path = ranked_path(&frames);
    stack.extend(frames);
    path.and_then(|minted| CanonicalAnchor::try_new(&minted).ok())
}

/// Fullword resolution: the inflected head (`статьи`, `пункта`) maps
/// through `inflected_tail_to_marker` then `marker_to_eid` - the head word
/// is left-scanned out of the capture span, never stored. A numbered
/// fullword mints one frame; a document-head fullword (`закона 44-ФЗ`,
/// the `doc_no` slot) stays unresolved.
fn resolve_fullword(
    capture: &LawRef,
    src: &str,
    resolution: &ResolutionTable,
    stack: &mut Vec<Frame>,
) -> Option<CanonicalAnchor> {
    if capture.slots.doc_no.is_some() || capture.slots.hier_nums.len() != 1 {
        return None;
    }
    let marker = head_marker_id(capture, src, resolution)?;
    let unit = table_lookup(&resolution.marker_to_eid, marker)?;
    let frame = Frame {
        unit: unit.to_owned(),
        num: capture.slots.hier_nums[0].clone(),
    };
    let anchor = ranked_path(std::slice::from_ref(&frame))
        .and_then(|minted| CanonicalAnchor::try_new(&minted).ok());
    stack.push(frame);
    anchor
}

/// The anaphora level of a capture: `anaphora_target_to_level` on the LAST
/// Word of the span (`того же раздела` binds `раздела`, not the head).
fn anaphora_level<'t>(
    capture: &LawRef,
    src: &str,
    resolution: &'t ResolutionTable,
) -> Option<&'t str> {
    let text = capture.user_text(src);
    let target = last_word_of(text)?;
    table_lookup(&resolution.anaphora_target_to_level, target)
}

/// Anaphora bind: the level comes from the LAST Word of the anaphora span
/// (`того же раздела` binds `раздела`, not the head), looked up in
/// `anaphora_target_to_level`. The `doc` sink (`Кодекса`, `Положения`,
/// `закона`, `Федерального`) never mints `doc_*`. A marker level binds
/// the nearest previous matching frame on the stack or emits the honest
/// missing-frame token (`art_ctx` / `sec_ctx` / `chp_ctx`).
fn resolve_anaphora(
    capture: &LawRef,
    src: &str,
    resolution: &ResolutionTable,
    stack: &[Frame],
) -> Option<CanonicalAnchor> {
    let level = anaphora_level(capture, src, resolution)?;
    if level == DOC_SINK {
        return None;
    }
    let unit = table_lookup(&resolution.marker_to_eid, level)?;
    match stack.iter().rev().find(|frame| frame.unit == unit) {
        Some(frame) => CanonicalAnchor::try_new(&frame.path()).ok(),
        None => CanonicalAnchor::try_new(&format!("{unit}_ctx")).ok(),
    }
}

/// Quoted-enum resolution: the letter is the capture's `quoted_enum` slot
/// as written; the head is left-scanned the same way capture built it
/// (abbrev id or inflected word - capture is never "fixed" here). The
/// letter appends to the nearest previous frame of the head's own unit
/// (`п. 2.1 ... подпункта "а"` -> `pnt_2.1/sub_а`); with no such frame the
/// capture stays honestly unresolved.
fn resolve_quoted_enum(
    capture: &LawRef,
    src: &str,
    resolution: &ResolutionTable,
    stack: &[Frame],
) -> Option<CanonicalAnchor> {
    let letter = capture.slots.quoted_enum.as_deref()?;
    let marker = head_marker_id(capture, src, resolution)?;
    let unit = table_lookup(&resolution.marker_to_eid, marker)?;
    let frame = stack.iter().rev().find(|frame| frame.unit == unit)?;
    let path = format!("{}/sub_{letter}", frame.path());
    CanonicalAnchor::try_new(&path).ok()
}

// ---------------------------------------------------------------------------
// T03: ranges as the expanded endpoint pair (`range_policy: expanded_pair`).
// ---------------------------------------------------------------------------

/// Range resolution: a range is the expanded ENDPOINT PAIR of one unit -
/// never an integer enumeration, even when the endpoints share a dotted
/// prefix (`пп. 2.1 - 4.1` mints exactly the two members `pnt_2.1` and
/// `pnt_4.1`, and the dedup key is the literal `pnt_2.1..pnt_4.1` - no
/// walk over last segments).
///
/// The unit is proven, in order: (1) the reference head left of
/// `range.start` - an allowlisted Abbrev or an `inflected_tail_to_marker`
/// Word over the same covering token stream (`статьями 7.29 - 7.32` ->
/// art, `подпункты 4.1 - 4.3` -> pp -> pnt); (2) the nearest previous
/// stack frame of a numbered unit; (3) nothing - the range stays honestly
/// unresolved (fail-closed: no invented unit). Below-art endpoints carry
/// the article context: the stacked `art_N` frame, or the honest
/// `art_ctx` token when the same src holds a FOLLOWING article anaphora
/// and no frame exists (the supply is a look-ahead over the sorted
/// capture list, never a text right-scan). The false range stays
/// unresolved: equal endpoints continuing a hyphen split (`16.6 - 16.6`
/// out of the lexer split of `16.6-2`) prove no range. Units above the
/// article never mint (same `eid_start_at` contour as chains).
fn resolve_range(
    capture: &LawRef,
    index: usize,
    captures: &[LawRef],
    src: &str,
    tokens: &[crate::lexer::NpaToken],
    resolution: &ResolutionTable,
    stack: &[Frame],
) -> Outcome {
    let Some((from, to)) = capture.slots.range.as_ref() else {
        return Outcome::unresolved();
    };
    // False range: equal endpoints continuing a hyphen split (`-2` of
    // `16.6-2`, which capture already froze as `16.6 - 16.6` because the
    // trailing `-2` is not a second HierNum).
    if from == to && hyphen_split_continuation(src, capture.span.end()) {
        return Outcome::unresolved();
    }
    // Unit: the left-scan head, else the nearest previous numbered frame.
    let unit = match range_head_marker(tokens, capture.span.start(), src, resolution)
        .and_then(|marker| table_lookup(&resolution.marker_to_eid, marker))
        .map(str::to_owned)
        .or_else(|| {
            stack
                .iter()
                .rev()
                .find(|frame| below_art_rank(&frame.unit).is_some())
                .map(|frame| frame.unit.clone())
        }) {
        Some(unit) => unit,
        None => return Outcome::unresolved(),
    };
    // Units above the article never mint: a `гл.`/`разд.` head drops out
    // instead of minting chp_/sec_ ranges (same eid_start_at contour as
    // chains).
    if below_art_rank(&unit).is_none() {
        return Outcome::unresolved();
    }
    // Article prefix for below-art endpoints: the stacked art frame, or
    // the honest `art_ctx` token when a following art-level anaphora
    // supplies the current-article context and no frame exists.
    let prefix = if unit == "art" {
        None
    } else {
        stack
            .iter()
            .rev()
            .find(|frame| frame.unit == "art")
            .map(Frame::path)
            .or_else(|| {
                following_art_anaphora(captures, index, src, resolution)
                    .then_some("art_ctx".to_owned())
            })
    };
    let endpoint = |num: &str| match &prefix {
        Some(article) => CanonicalAnchor::try_new(&format!("{article}/{unit}_{num}")),
        None => CanonicalAnchor::try_new(&format!("{unit}_{num}")),
    };
    let (Ok(from_anchor), Ok(to_anchor)) = (endpoint(from), endpoint(to)) else {
        return Outcome::unresolved();
    };
    let dedup_key = format!("{}..{}", from_anchor.path, to_anchor.path);
    Outcome {
        anchor: Some(from_anchor.clone()),
        members: vec![from_anchor, to_anchor],
        dedup_key: Some(dedup_key),
    }
}

/// Left-scans for the reference head of a range over the covering token
/// stream: from the token opening at `range_start`, walk left across
/// Space; the FIRST non-Space token decides. An allowlisted Abbrev
/// contributes its `marker_to_eid` id (`пп.`, `ст.`); a Word contributes
/// its `inflected_tail_to_marker` row (`статьями`, `подпункты`); a
/// non-hitting word, a Punct, or the start of input stops the scan with
/// no head. The governing noun of a Russian reference sits immediately
/// left of its number, so the scan never reaches across one (fail-closed;
/// a comma-list member invents no head of the whole list).
fn range_head_marker<'t>(
    tokens: &[crate::lexer::NpaToken],
    range_start: usize,
    src: &str,
    resolution: &'t ResolutionTable,
) -> Option<&'t str> {
    use crate::lexer::TokenKind;
    let mut index = tokens
        .iter()
        .position(|token| token.span.start() == range_start)?;
    while index > 0 {
        index -= 1;
        match tokens[index].kind {
            TokenKind::Space => continue,
            TokenKind::Abbrev => {
                let id = tokens[index].abbrev_id?.as_str();
                return resolution
                    .marker_to_eid
                    .iter()
                    .any(|(marker, _)| marker == id)
                    .then_some(id);
            }
            TokenKind::Word => {
                return table_lookup(
                    &resolution.inflected_tail_to_marker,
                    tokens[index].lexeme(src),
                );
            }
            _ => return None,
        }
    }
    None
}

/// `true` when the source continues a hyphen-split number right after
/// `end` (`-2` of the lexer split `16.6-2`, which capture already froze
/// as the endpoint pair `16.6 - 16.6`).
fn hyphen_split_continuation(src: &str, end: usize) -> bool {
    src.as_bytes().get(end) == Some(&b'-')
        && src[end + 1..]
            .chars()
            .next()
            .is_some_and(|ch: char| ch.is_ascii_digit())
}

/// `true` when a LATER capture of the same src is an anaphora whose level
/// maps to the article unit - the roadmap `art_ctx` supplier. Ranges
/// resolve before a following anaphora is walked, so the supply is a
/// look-ahead over the already-sorted capture list, never a right-scan
/// of text; doc-level anaphora (`Кодекса`) supplies nothing.
fn following_art_anaphora(
    captures: &[LawRef],
    capture_index: usize,
    src: &str,
    resolution: &ResolutionTable,
) -> bool {
    captures[capture_index + 1..].iter().any(|capture| {
        capture.pattern_id == "anaphora_candidate"
            && anaphora_level(capture, src, resolution).is_some_and(|level| {
                level != DOC_SINK && table_lookup(&resolution.marker_to_eid, level) == Some("art")
            })
    })
}

/// The marker id of a capture's head token, sliced out of the capture span
/// over the frozen lexer (user text is never stored): an Abbrev
/// contributes its lexicon id, a Word maps through
/// `inflected_tail_to_marker`. `None` when the span opens with neither.
fn head_marker_id<'t>(
    capture: &LawRef,
    src: &str,
    resolution: &'t ResolutionTable,
) -> Option<&'t str> {
    let text = capture.user_text(src);
    let token = crate::lexer::lex(text).into_iter().find(|token| {
        matches!(
            token.kind,
            crate::lexer::TokenKind::Word | crate::lexer::TokenKind::Abbrev
        )
    })?;
    match token.kind {
        crate::lexer::TokenKind::Abbrev => {
            let id = token.abbrev_id?.as_str();
            resolution
                .marker_to_eid
                .iter()
                .any(|(marker, _)| marker == id)
                .then_some(id)
        }
        _ => table_lookup(&resolution.inflected_tail_to_marker, token.lexeme(text)),
    }
}

/// The last `Word` lexeme of an already-sliced capture span (the anaphora
/// target sits at the span end: `того же раздела` ends in `раздела`).
fn last_word_of(text: &str) -> Option<&str> {
    crate::lexer::lex(text)
        .into_iter()
        .rfind(|token| token.kind == crate::lexer::TokenKind::Word)
        .map(|token| token.lexeme(text))
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
