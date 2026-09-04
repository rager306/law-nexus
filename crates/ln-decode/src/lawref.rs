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
use crate::lexer::{NpaToken, TokenKind};

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

/// Closed pattern ids of the seven capture matchers (mirrors of the
/// `PATTERN_ID_CANON` rows below; a pattern id is table data, not an enum).
const PATTERN_CHAIN: &str = "abbrev-hier-chain";
const PATTERN_AMENDMENT: &str = "abbrev-amendment-window";
const PATTERN_DATE_DOCNO: &str = "date-docno-window";
const PATTERN_FULLWORD: &str = "fullword-ref";
const PATTERN_QUOTED_ENUM: &str = "quoted-enum";
const PATTERN_RANGE: &str = "range_candidate";
const PATTERN_ANAPHORA: &str = "anaphora_candidate";

/// Captures reference candidates over `src` through the frozen covering
/// lexer ([`crate::lexer::lex`]).
///
/// The covering token stream is the only text view capture may scan: no
/// regex over raw text, no digit rescan (layer A documents the frozen lexer
/// first-match order; it never reclassifies). Seven matchers fire over every
/// token index - the same seven pattern ids as the S01 seed, no eighth - and
/// the YAML layer-B overlap policies adjudicate the fire-all set. Candidates
/// then order by the frozen `(start, end, pattern_id)` sort key and mint via
/// the fail-closed [`LawRef::try_new`].
pub fn capture_lawrefs(src: &str) -> Vec<LawRef> {
    let tokens = crate::lexer::lex(src);
    if tokens.is_empty() {
        return Vec::new();
    }
    // Fail-closed library path: the embedded table is pinned green by the
    // precedence tests, so a parse failure here is a build-data defect that
    // must degrade to "no candidates", never panic a caller.
    let Ok(precedence) = LawRefPrecedence::embedded() else {
        return Vec::new();
    };

    let mut raw: Vec<RawCapture> = Vec::new();
    for index in 0..tokens.len() {
        match_abbrev_hier_chain(&tokens, index, &precedence, src, &mut raw);
        match_abbrev_amendment_window(&tokens, index, &precedence, src, &mut raw);
        match_date_docno_window(&tokens, index, src, &mut raw);
        match_fullword_ref(&tokens, index, &precedence, src, &mut raw);
        match_quoted_enum(&tokens, index, &precedence, src, &mut raw);
        match_range_candidate(&tokens, index, src, &mut raw);
        match_anaphora_candidate(&tokens, index, &precedence, src, &mut raw);
    }

    apply_overlap_precedence(&mut raw, &precedence);

    raw.sort_by(|left, right| {
        (left.start, left.end, left.pattern_id).cmp(&(right.start, right.end, right.pattern_id))
    });
    raw.into_iter().filter_map(RawCapture::mint).collect()
}

/// One un-adjudicated capture candidate: the data a `LawRef` is minted from.
#[derive(Clone)]
struct RawCapture {
    start: usize,
    end: usize,
    pattern_id: &'static str,
    token_kind_seq: String,
    slots: LawRefSlots,
}

impl RawCapture {
    /// Bounds a candidate over the inclusive token range `start..=end` and
    /// records the frozen-lexer kind sequence over it (`TokenKind::as_str`,
    /// comma-joined).
    fn new(
        tokens: &[NpaToken],
        start_index: usize,
        end_index: usize,
        pattern_id: &'static str,
        slots: LawRefSlots,
    ) -> Self {
        Self {
            start: tokens[start_index].span.start(),
            end: tokens[end_index].span.end(),
            pattern_id,
            token_kind_seq: tokens[start_index..=end_index]
                .iter()
                .map(|token| token.kind.as_str())
                .collect::<Vec<_>>()
                .join(","),
            slots,
        }
    }

    /// Mints the product capture; [`LawRef::try_new`] fails closed on an
    /// empty span, which a token-span-bounded candidate cannot produce.
    fn mint(self) -> Option<LawRef> {
        LawRef::try_new(
            self.start,
            self.end,
            self.pattern_id.to_owned(),
            self.token_kind_seq,
            self.slots,
        )
        .ok()
    }
}

/// `true` when `tokens[index]` is a Space token (out of range: `false`).
fn is_space(tokens: &[NpaToken], index: usize) -> bool {
    tokens
        .get(index)
        .is_some_and(|token| token.kind == TokenKind::Space)
}

/// Layer-A number token: a `HierNum`, or a digit-only `Word` (the C2 lexer
/// folds a bare `ч. 2` number into a digit `Word` - an undotted `1.` is
/// never a hier-number, so the fold is lossless for capture purposes).
fn is_number_token(token: &NpaToken, src: &str) -> bool {
    match token.kind {
        TokenKind::HierNum => true,
        TokenKind::Word => {
            let lexeme = token.lexeme(src);
            !lexeme.is_empty() && lexeme.bytes().all(|byte| byte.is_ascii_digit())
        }
        _ => false,
    }
}

/// The id string when `tokens[index]` is an Abbrev allowlisted by `ids` (the
/// YAML allowlists are the single canon - no src-side id copy).
fn allowlisted_abbrev(tokens: &[NpaToken], index: usize, ids: &[String]) -> Option<String> {
    let token = tokens.get(index)?;
    if token.kind != TokenKind::Abbrev {
        return None;
    }
    let id = token.abbrev_id?.as_str();
    ids.iter().find(|entry| entry.as_str() == id).cloned()
}

/// Forward window scan shared by the window matchers: from `anchor + 1`, the
/// first token satisfying `pred` wins while every skipped token is a
/// Space/Word/Punct filler and the token distance stays within
/// `max_distance` (the YAML gap bounds are filler counts; distance = fillers + 1).
fn scan_filler_forward(
    tokens: &[NpaToken],
    anchor: usize,
    max_distance: usize,
    pred: impl Fn(&NpaToken) -> bool,
) -> Option<usize> {
    let mut index = anchor + 1;
    while index < tokens.len() && index - anchor <= max_distance {
        let token = &tokens[index];
        if pred(token) {
            return Some(index);
        }
        if !matches!(
            token.kind,
            TokenKind::Space | TokenKind::Word | TokenKind::Punct
        ) {
            return None;
        }
        index += 1;
    }
    None
}

/// `abbrev-hier-chain`: an allowlisted chain abbrev, then Space, then a
/// number token, then `(Space Abbrev(chain) Space number)*`. Marker ids and
/// hierarchy numbers are captured as written (`15.1` stays `15.1`).
fn match_abbrev_hier_chain(
    tokens: &[NpaToken],
    index: usize,
    precedence: &LawRefPrecedence,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    let Some(first_marker) = allowlisted_abbrev(tokens, index, &precedence.chain_abbrev_ids) else {
        return;
    };
    if !is_space(tokens, index + 1) {
        return;
    }
    let Some(mut last) = tokens
        .get(index + 2)
        .filter(|token| is_number_token(token, src))
        .map(|_| index + 2)
    else {
        return;
    };
    let mut markers = vec![first_marker];
    let mut hier_nums = vec![tokens[last].lexeme(src).to_owned()];
    while is_space(tokens, last + 1) {
        let Some(link_marker) = allowlisted_abbrev(tokens, last + 2, &precedence.chain_abbrev_ids)
        else {
            break;
        };
        if !is_space(tokens, last + 3) {
            break;
        }
        let Some(next) = tokens
            .get(last + 4)
            .filter(|token| is_number_token(token, src))
            .map(|_| last + 4)
        else {
            break;
        };
        markers.push(link_marker);
        hier_nums.push(tokens[next].lexeme(src).to_owned());
        last = next;
    }
    let slots = LawRefSlots {
        marker_chain: markers,
        hier_nums,
        ..Default::default()
    };
    out.push(RawCapture::new(tokens, index, last, PATTERN_CHAIN, slots));
}

/// `abbrev-amendment-window`: `ред.`/`изм.` ... Date (filler Space/Word/Punct,
/// gap < 16) ... DocNo (gap < 4). The full window is required; `date` and
/// `doc_no` are filled from the window tokens (R070 stays open: the window
/// is lexical, not provenance).
fn match_abbrev_amendment_window(
    tokens: &[NpaToken],
    index: usize,
    precedence: &LawRefPrecedence,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    if allowlisted_abbrev(tokens, index, &precedence.amendment_abbrev_ids).is_none() {
        return;
    }
    let Some(date_index) =
        scan_filler_forward(tokens, index, 16, |token| token.kind == TokenKind::Date)
    else {
        return;
    };
    let Some(doc_no_index) = scan_filler_forward(tokens, date_index, 4, |token| {
        token.kind == TokenKind::DocNo
    }) else {
        return;
    };
    let slots = LawRefSlots {
        date: Some(tokens[date_index].lexeme(src).to_owned()),
        doc_no: Some(tokens[doc_no_index].lexeme(src).to_owned()),
        ..Default::default()
    };
    out.push(RawCapture::new(
        tokens,
        index,
        doc_no_index,
        PATTERN_AMENDMENT,
        slots,
    ));
}

/// `date-docno-window`: a Date followed within <= 4 tokens by a DocNo or a
/// LawCode (Space/Word/Punct fillers). A lone Date is not a capture; the
/// window fills `date` plus `doc_no`/`law_code` from the trailing token.
fn match_date_docno_window(
    tokens: &[NpaToken],
    index: usize,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    if !tokens
        .get(index)
        .is_some_and(|token| token.kind == TokenKind::Date)
    {
        return;
    }
    let Some(hit) = scan_filler_forward(tokens, index, 4, |token| {
        matches!(token.kind, TokenKind::DocNo | TokenKind::LawCode)
    }) else {
        return;
    };
    let extra = if tokens[hit].kind == TokenKind::DocNo {
        (Some(tokens[hit].lexeme(src).to_owned()), None)
    } else {
        (None, Some(tokens[hit].lexeme(src).to_owned()))
    };
    let slots = LawRefSlots {
        date: Some(tokens[index].lexeme(src).to_owned()),
        doc_no: extra.0,
        law_code: extra.1,
        ..Default::default()
    };
    out.push(RawCapture::new(
        tokens,
        index,
        hit,
        PATTERN_DATE_DOCNO,
        slots,
    ));
}

/// `fullword-ref`: a fullword tail (`статьи`, `пункта`, ...) then Space then
/// a DocNo or a number token. Tails stay `Word` tokens - never retagged
/// Abbrev (the C2 goldens pin that contour).
fn match_fullword_ref(
    tokens: &[NpaToken],
    index: usize,
    precedence: &LawRefPrecedence,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    let Some(token) = tokens.get(index) else {
        return;
    };
    if token.kind != TokenKind::Word
        || !precedence
            .fullword_tails
            .iter()
            .any(|tail| tail == token.lexeme(src))
    {
        return;
    }
    if !is_space(tokens, index + 1) {
        return;
    }
    let Some(number_index) = tokens
        .get(index + 2)
        .filter(|next| next.kind == TokenKind::DocNo || is_number_token(next, src))
        .map(|_| index + 2)
    else {
        return;
    };
    let mut slots = LawRefSlots::default();
    if tokens[number_index].kind == TokenKind::DocNo {
        slots.doc_no = Some(tokens[number_index].lexeme(src).to_owned());
    } else {
        slots.hier_nums = vec![tokens[number_index].lexeme(src).to_owned()];
    }
    out.push(RawCapture::new(
        tokens,
        index,
        number_index,
        PATTERN_FULLWORD,
        slots,
    ));
}

/// `quoted-enum`: an EnumMarker with an exact-`"` opening Punct behind it and
/// a closing Punct starting with `"`, three tokens behind an allowlisted
/// abbrev marker or a `подпункт*` word (`подпункта "а"`). The span covers
/// the head marker through the closing quote; `quoted_enum` is the letter.
fn match_quoted_enum(
    tokens: &[NpaToken],
    index: usize,
    precedence: &LawRefPrecedence,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    if index < 3 {
        return;
    }
    let Some(marker) = tokens
        .get(index)
        .filter(|token| token.kind == TokenKind::EnumMarker)
    else {
        return;
    };
    let opening_exact_quote =
        |token: &NpaToken| token.kind == TokenKind::Punct && token.lexeme(src) == "\"";
    let closing_quoted =
        |token: &NpaToken| token.kind == TokenKind::Punct && token.lexeme(src).starts_with('"');
    if !tokens.get(index - 1).is_some_and(opening_exact_quote) {
        return;
    }
    if !tokens.get(index + 1).is_some_and(closing_quoted) {
        return;
    }
    let head = &tokens[index - 3];
    let head_is_marker = match head.kind {
        TokenKind::Abbrev => head.abbrev_id.is_some_and(|id| {
            precedence
                .quoted_marker_abbrev_ids
                .iter()
                .any(|entry| entry == id.as_str())
        }),
        TokenKind::Word => head.lexeme(src).starts_with("подпункт"),
        _ => false,
    };
    if !head_is_marker {
        return;
    }
    let slots = LawRefSlots {
        quoted_enum: Some(marker.lexeme(src).to_owned()),
        ..Default::default()
    };
    out.push(RawCapture::new(
        tokens,
        index - 3,
        index + 1,
        PATTERN_QUOTED_ENUM,
        slots,
    ));
}

/// `range_candidate`: `HierNum Space Punct(-) Space HierNum`. Endpoints are
/// captured as written and never expanded (S03 owns enumeration).
fn match_range_candidate(tokens: &[NpaToken], index: usize, src: &str, out: &mut Vec<RawCapture>) {
    if !tokens
        .get(index)
        .is_some_and(|token| token.kind == TokenKind::HierNum)
    {
        return;
    }
    if !is_space(tokens, index + 1) {
        return;
    }
    if !tokens
        .get(index + 2)
        .is_some_and(|token| token.kind == TokenKind::Punct && token.lexeme(src) == "-")
    {
        return;
    }
    if !is_space(tokens, index + 3) {
        return;
    }
    if !tokens
        .get(index + 4)
        .is_some_and(|token| token.kind == TokenKind::HierNum)
    {
        return;
    }
    let slots = LawRefSlots {
        range: Some((
            tokens[index].lexeme(src).to_owned(),
            tokens[index + 4].lexeme(src).to_owned(),
        )),
        ..Default::default()
    };
    out.push(RawCapture::new(
        tokens,
        index,
        index + 4,
        PATTERN_RANGE,
        slots,
    ));
}

/// `anaphora_candidate`: an anaphora head word, an optional `же`, then a
/// Word (the resolution target). The span covers head through target word;
/// the `anaphora` slot carries the joined heads as written and is never
/// resolved here (S03).
fn match_anaphora_candidate(
    tokens: &[NpaToken],
    index: usize,
    precedence: &LawRefPrecedence,
    src: &str,
    out: &mut Vec<RawCapture>,
) {
    let Some(token) = tokens.get(index) else {
        return;
    };
    if token.kind != TokenKind::Word
        || !precedence
            .anaphora_heads
            .iter()
            .any(|head| head == token.lexeme(src))
    {
        return;
    }
    let mut heads_end = index;
    if is_space(tokens, index + 1)
        && tokens
            .get(index + 2)
            .is_some_and(|next| next.kind == TokenKind::Word && next.lexeme(src) == "же")
    {
        heads_end = index + 2;
    }
    if !is_space(tokens, heads_end + 1) {
        return;
    }
    if !tokens
        .get(heads_end + 2)
        .is_some_and(|next| next.kind == TokenKind::Word)
    {
        return;
    }
    let mut anaphora = tokens[index].lexeme(src).to_owned();
    if heads_end != index {
        anaphora.push(' ');
        anaphora.push_str(tokens[index + 2].lexeme(src));
    }
    let slots = LawRefSlots {
        anaphora: Some(anaphora),
        ..Default::default()
    };
    out.push(RawCapture::new(
        tokens,
        index,
        heads_end + 2,
        PATTERN_ANAPHORA,
        slots,
    ));
}

/// Layer B (precedence as data): the YAML overlap policies adjudicate the
/// fire-all set. `drop` removes a `date-docno-window` strictly contained in
/// an `abbrev-amendment-window`, and a candidate strictly contained in a
/// wider candidate of the same pattern (the chain re-fire at an inner marker
/// collapses onto the outer chain).
fn apply_overlap_precedence(raw: &mut Vec<RawCapture>, precedence: &LawRefPrecedence) {
    if precedence.overlap_date_docno_inside_amendment == "drop" {
        let snapshot = raw.clone();
        raw.retain(|candidate| {
            candidate.pattern_id != PATTERN_DATE_DOCNO
                || !snapshot.iter().any(|other| {
                    other.pattern_id == PATTERN_AMENDMENT && strictly_contained(candidate, other)
                })
        });
    }
    if precedence.overlap_same_pattern_containment == "drop" {
        let snapshot = raw.clone();
        raw.retain(|candidate| {
            !snapshot.iter().any(|other| {
                other.pattern_id == candidate.pattern_id && strictly_contained(candidate, other)
            })
        });
    }
}

/// The YAML containment contour: `other` strictly contains `candidate`
/// (`(other.start < a.start && a.end <= other.end) ||
///  (other.start <= a.start && a.end < other.end)`).
fn strictly_contained(candidate: &RawCapture, other: &RawCapture) -> bool {
    (other.start < candidate.start && candidate.end <= other.end)
        || (other.start <= candidate.start && candidate.end < other.end)
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
