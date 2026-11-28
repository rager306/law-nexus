//! Clean-room `ChangeGrammar` for Russian amending statutes (ADR-0032 D3, `RC28-F13`).
//!
//! Decomposes Russian legislative amendment clauses into bounded structural
//! slots (`OWNER`, `KIND`, `CHILD`, `VALUE`, `PARAM`, `LOCVALUE`) above the
//! covering lexer (`crate::lexer::lex`) and emits `Proposed` candidates or
//! typed fail-closed refusals (`INV-10`).
//!
//! Clean-room boundary (D380): adopts architectural slot-decomposition patterns
//! from Russian legislative drafting practice only; contains zero Pullenti
//! source code, dictionaries, or uncalibrated numeric thresholds.

use crate::domain::TextSpan;
use crate::lexer::{AbbrevId, TokenKind, lex};

/// D098 non-claims carried by every [`ChangeGrammarReport`].
pub const CHANGE_GRAMMAR_NON_CLAIMS: &[&str] = &[
    "ChangeGrammar emits Proposed candidates only; never authoritative legal facts or Applied mutations",
    "Lifecycle [proposed] (ADR-0032 D3); does not close RC28-F13 or validate corpus-wide recall",
    "Clean-room Russian drafting grammar (D380); zero Pullenti code, dictionaries, or numeric thresholds",
    "Editorial annotations (e.g. ConsultantPlus notes) are skipped, never promoted to legislative events",
];

/// Closed initial 5-operation `MC-OPS` subset targeted by ADR-0032 D3.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChangeOpKind {
    ReplaceText,
    InsertText,
    DeleteText,
    Attach,
    Repeal,
}

impl ChangeOpKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ReplaceText => "ReplaceText",
            Self::InsertText => "InsertText",
            Self::DeleteText => "DeleteText",
            Self::Attach => "Attach",
            Self::Repeal => "Repeal",
        }
    }
}

/// Positional qualifier (`PARAM` slot) governing where an operation applies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChangePositionParam {
    WholeComponent,
    ExactAnchor,
    AfterAnchor,
    BeforeAnchor,
    EndOfComponent,
    NewComponent,
}

/// Ordered Russian normative hierarchy levels (coarse-to-fine rank `0..=6`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum StructuralLevel {
    Razdel = 0,
    Glava = 1,
    Statya = 2,
    Chast = 3,
    Punkt = 4,
    Podpunkt = 5,
    Abzats = 6,
}

impl StructuralLevel {
    pub const fn slug(self) -> &'static str {
        match self {
            Self::Razdel => "razdel",
            Self::Glava => "glava",
            Self::Statya => "statya",
            Self::Chast => "chast",
            Self::Punkt => "punkt",
            Self::Podpunkt => "podpunkt",
            Self::Abzats => "abzats",
        }
    }
}

/// One structural step in a normalized target locator (e.g. `statya-3`, `punkt-8.1`, `podpunkt-н`).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct StructuralStep {
    pub level: StructuralLevel,
    pub value: String,
}

impl StructuralStep {
    pub fn new(level: StructuralLevel, value: impl Into<String>) -> Self {
        Self {
            level,
            value: value.into(),
        }
    }
}

/// Canonical coarse-to-fine structural path (`OWNER` / `ComponentLocator`).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Default)]
pub struct StructuralLocator {
    steps: Vec<StructuralStep>,
}

impl StructuralLocator {
    pub fn new(mut steps: Vec<StructuralStep>) -> Self {
        steps.sort_by_key(|step| step.level);
        let mut merged: Vec<StructuralStep> = Vec::with_capacity(steps.len());
        for step in steps {
            if let Some(last) = merged.last_mut()
                && last.level == step.level
            {
                *last = step;
            } else {
                merged.push(step);
            }
        }
        Self { steps: merged }
    }

    pub fn is_empty(&self) -> bool {
        self.steps.is_empty()
    }

    pub fn steps(&self) -> &[StructuralStep] {
        &self.steps
    }

    /// Overlay child steps on top of a parent container scope, pruning any
    /// inherited steps at or finer than the coarsest overlaid level so finer
    /// descendants from a sibling never leak into a new child.
    pub fn with_overlay(&self, overlay: &[StructuralStep]) -> Self {
        let Some(min_overlay_level) = overlay.iter().map(|s| s.level).min() else {
            return self.clone();
        };
        let mut combined: Vec<StructuralStep> = self
            .steps
            .iter()
            .filter(|s| s.level < min_overlay_level)
            .cloned()
            .collect();
        combined.extend(overlay.iter().cloned());
        Self::new(combined)
    }

    /// Deterministic slash-separated locator (e.g. `statya-3/chast-1/punkt-8`).
    pub fn canonical_path(&self) -> String {
        self.steps
            .iter()
            .map(|s| format!("{}-{}", s.level.slug(), s.value))
            .collect::<Vec<_>>()
            .join("/")
    }
}

/// Requisites of the target act introduced by `Внести в ...` (`OWNER` act).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TargetActRequisites {
    pub raw_header: String,
    pub date: Option<String>,
    pub number: Option<String>,
    pub block_index: usize,
    pub span: TextSpan,
}

/// One `Proposed` amendment micro-operation candidate emitted by `ChangeGrammar`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChangeClauseCandidate {
    pub block_index: usize,
    pub evidence_span: TextSpan,
    pub owner_act: TargetActRequisites,
    pub target_locator: StructuralLocator,
    pub child_spec: Option<StructuralStep>,
    pub kind: ChangeOpKind,
    pub param: ChangePositionParam,
    pub loc_value: Option<String>,
    pub value: Option<String>,
}

/// Fail-closed typed refusal (`MC-RES` / `INV-10`); never `None`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ChangeParseRefusal {
    UnsupportedOperation {
        block_index: usize,
        span: TextSpan,
        excerpt: String,
    },
    AmbiguousTarget {
        block_index: usize,
        span: TextSpan,
        reason: &'static str,
    },
    IncompleteSource {
        block_index: usize,
        span: TextSpan,
        reason: &'static str,
    },
}

/// Output of [`parse_amending_blocks`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChangeGrammarReport {
    pub candidates: Vec<ChangeClauseCandidate>,
    pub refusals: Vec<ChangeParseRefusal>,
    pub editorial_notes_skipped: usize,
    pub non_claims: &'static [&'static str],
}

// ── UTF-8-safe case-insensitive substring span finder ───────────────────────

/// Locate the first occurrence of lowercase `needle_lower` inside `orig`,
/// returning exact `(orig_start, orig_end)` byte bounds on UTF-8 char
/// boundaries in `orig`. Safe even when `char::to_lowercase()` changes char
/// count or byte length (e.g. U+0130 `İ` -> `i\u{0307}`).
fn find_ci_span(orig: &str, needle_lower: &str) -> Option<(usize, usize)> {
    if needle_lower.is_empty() {
        return Some((0, 0));
    }
    let mut lowered = String::with_capacity(orig.len());
    let mut byte_map: Vec<(usize, usize)> = Vec::with_capacity(orig.len());
    for (orig_start, ch) in orig.char_indices() {
        let orig_end = orig_start + ch.len_utf8();
        for lower_ch in ch.to_lowercase() {
            let mut buf = [0u8; 4];
            let encoded = lower_ch.encode_utf8(&mut buf);
            lowered.push_str(encoded);
            for _ in 0..encoded.len() {
                byte_map.push((orig_start, orig_end));
            }
        }
    }
    let pos = lowered.find(needle_lower)?;
    let end_idx = pos + needle_lower.len();
    let orig_start = byte_map.get(pos)?.0;
    let orig_end = byte_map.get(end_idx - 1)?.1;
    debug_assert!(orig.is_char_boundary(orig_start));
    debug_assert!(orig.is_char_boundary(orig_end));
    Some((orig_start, orig_end))
}

// ── Quoted span extraction (UTF-8 safe, supports "..." and «...») ───────────

#[derive(Debug, Clone)]
struct QuotedSegment {
    content: String,
    end: usize,
}

fn starts_with_inline_op_keyword(s: &str) -> bool {
    let lower = s.trim_start().to_lowercase();
    lower.starts_with("после слов")
        || lower.starts_with("после цифр")
        || lower.starts_with("перед слов")
        || lower.starts_with("перед цифр")
        || lower.starts_with("слово ")
        || lower.starts_with("слова ")
        || lower.starts_with("цифру ")
        || lower.starts_with("цифры ")
        || lower.starts_with("предложение ")
        || lower.starts_with("дополнить ")
        || lower.starts_with("признать утративш")
}

fn is_valid_inline_quote_close(after: &str, expect_verb_after: bool) -> bool {
    let trimmed = after.trim_start();
    if expect_verb_after {
        let lower = trimmed.to_lowercase();
        return lower.starts_with("заменить ")
            || lower.starts_with("исключить")
            || lower.starts_with("дополнить ");
    }
    if trimmed.is_empty() {
        return true;
    }
    if let Some(rest) = trimmed.strip_prefix([',', ';', '.']) {
        let rest_trimmed = rest.trim_start();
        if rest_trimmed.is_empty() || starts_with_inline_op_keyword(rest_trimmed) {
            return true;
        }
        let lower = rest_trimmed.to_lowercase();
        if let Some(after_conj) = lower
            .strip_prefix("и ")
            .or_else(|| lower.strip_prefix("а "))
        {
            return starts_with_inline_op_keyword(after_conj);
        }
        return false;
    }
    let lower = trimmed.to_lowercase();
    if let Some(after_conj) = lower
        .strip_prefix("и ")
        .or_else(|| lower.strip_prefix("а "))
    {
        return starts_with_inline_op_keyword(after_conj);
    }
    false
}

/// Extract the next quoted payload in an inline clause (`"..."` or `«...»`),
/// tolerating Russian drafting's nested ASCII quotes around subpoint letters
/// (e.g. `"подпунктами "а" и "б" пункта 5".`) by requiring BOTH balanced even
/// quote parity AND a valid clause boundary after the closing `"`.
fn find_next_quote(src: &str, from: usize, expect_verb_after: bool) -> Option<QuotedSegment> {
    let slice = src.get(from..)?;
    let mut chars = slice.char_indices();
    while let Some((rel_idx, ch)) = chars.next() {
        if ch == '"' || ch == '«' {
            let abs_start = from + rel_idx;
            let content_start = abs_start + ch.len_utf8();
            if ch == '«' {
                let mut depth = 1usize;
                for (end_rel, end_ch) in chars.by_ref() {
                    if end_ch == '«' {
                        depth += 1;
                    } else if end_ch == '»' {
                        depth -= 1;
                        if depth == 0 {
                            let abs_end = from + end_rel;
                            return Some(QuotedSegment {
                                content: src[content_start..abs_end].to_owned(),
                                end: abs_end + end_ch.len_utf8(),
                            });
                        }
                    }
                }
                return None;
            } else {
                let mut seen_quotes = 1usize;
                let mut first_close: Option<usize> = None;
                for (end_rel, end_ch) in chars.by_ref() {
                    if end_ch == '"' {
                        seen_quotes += 1;
                        let abs_end = from + end_rel;
                        if first_close.is_none() {
                            first_close = Some(abs_end);
                        }
                        if seen_quotes.is_multiple_of(2)
                            && is_valid_inline_quote_close(&src[abs_end + 1..], expect_verb_after)
                        {
                            return Some(QuotedSegment {
                                content: src[content_start..abs_end].to_owned(),
                                end: abs_end + 1,
                            });
                        }
                    }
                }
                // Fall back ONLY for a plain unnested quote pair (`seen_quotes == 2`)
                // followed by an unsupported tail (so the leading op still parses and
                // the unsupported tail fails closed); nested quotes with non-boundary
                // tails or odd/unclosed quote counts fail closed cleanly (`INV-10`).
                if !expect_verb_after
                    && seen_quotes == 2
                    && let Some(abs_end) = first_close
                {
                    return Some(QuotedSegment {
                        content: src[content_start..abs_end].to_owned(),
                        end: abs_end + 1,
                    });
                }
                return None;
            }
        }
    }
    None
}

fn is_editorial_header(trimmed: &str) -> bool {
    let lower = trimmed.to_lowercase();
    lower.starts_with("консультантплюс: примечание")
        || lower.starts_with("гарант: примечание")
        || lower.starts_with("документ предоставлен консультантплюс")
        || lower.starts_with("консультантплюснадежная")
        || lower.starts_with("www.consultant.ru")
        || lower.starts_with("страница page из numpages")
}

/// True when a ConsultantPlus/Garant note header carries no inline body so its
/// note text lives in the immediately following paragraph.
fn is_standalone_note_header(trimmed: &str) -> bool {
    let lower = trimmed.to_lowercase();
    matches!(
        lower.trim_end_matches('.'),
        "консультантплюс: примечание" | "гарант: примечание"
    )
}

fn looks_like_legislative_block(trimmed: &str) -> bool {
    let lower = trimmed.to_lowercase();
    is_top_level_article_heading(trimmed)
        || lower.starts_with("внести в ")
        || lower.starts_with("внести изменение в ")
        || lower.starts_with("внести изменения в ")
        || matches!(
            strip_list_prefix(trimmed).0,
            ListPrefixKind::NumberedItem | ListPrefixKind::LetteredItem
        )
}

fn is_signature_or_preamble_noise(trimmed: &str) -> bool {
    trimmed.is_empty()
        || trimmed.starts_with("iVBORw0KGgo")
        || trimmed == "Президент"
        || trimmed == "Российской Федерации"
        || trimmed == "РОССИЙСКАЯ ФЕДЕРАЦИЯ"
        || trimmed == "ФЕДЕРАЛЬНЫЙ ЗАКОН"
        || trimmed.starts_with("Москва, Кремль")
        || trimmed.chars().all(|c| c.is_ascii_digit())
}

/// True only for standalone top-level article headings (`Статья 1`, `Статья 2.`).
fn is_top_level_article_heading(trimmed: &str) -> bool {
    let lower = trimmed.to_lowercase();
    let Some(rest) = lower.strip_prefix("статья ") else {
        return false;
    };
    let rest = rest.trim().trim_end_matches('.');
    !rest.is_empty() && rest.bytes().all(|b| b.is_ascii_digit() || b == b'.')
}

/// Strip leading numbered-part prefix (`1. `, `8. `) for commencement/transitional detection.
fn strip_part_number_prefix(trimmed: &str) -> &str {
    let bytes = trimmed.as_bytes();
    let mut i = 0;
    while i < bytes.len() && (bytes[i].is_ascii_digit() || bytes[i] == b'.') {
        i += 1;
    }
    if i > 1 && bytes[i - 1] == b'.' && i < bytes.len() && bytes[i].is_ascii_whitespace() {
        trimmed[i..].trim_start()
    } else {
        trimmed
    }
}

fn classify_abbrev_id(id: AbbrevId) -> Option<StructuralLevel> {
    // Dispatches strictly on ADR-0028 Decision 2 S01 canonical abbreviation IDs
    // (no duplicate runtime lexeme string table).
    match id.as_str() {
        "razd" => Some(StructuralLevel::Razdel),
        "gl" => Some(StructuralLevel::Glava),
        "st" => Some(StructuralLevel::Statya),
        "ch" => Some(StructuralLevel::Chast),
        "p" => Some(StructuralLevel::Punkt),
        "podp" => Some(StructuralLevel::Podpunkt),
        "abz" => Some(StructuralLevel::Abzats),
        _ => None,
    }
}

fn is_plural_level_token(kind: TokenKind, abbrev_id: Option<AbbrevId>, lower: &str) -> bool {
    if kind == TokenKind::Abbrev {
        return abbrev_id
            .map(AbbrevId::as_str)
            .is_some_and(|id| matches!(id, "stst" | "pp"));
    }
    matches!(
        lower,
        "статьях"
            | "статьи"
            | "статьям"
            | "статьями"
            | "частях"
            | "частям"
            | "частями"
            | "пунктах"
            | "пунктам"
            | "пунктами"
            | "пункты"
            | "подпунктах"
            | "подпунктам"
            | "подпунктами"
            | "подпункты"
            | "абзацах"
            | "абзацам"
            | "абзацами"
            | "абзацы"
    )
}

fn classify_singular_level_word(word: &str) -> Option<StructuralLevel> {
    match word {
        "раздел" | "раздела" | "разделу" | "разделом" | "разделе" => {
            Some(StructuralLevel::Razdel)
        }
        "глава" | "главы" | "главе" | "главу" | "главой" | "главою" => {
            Some(StructuralLevel::Glava)
        }
        "статья" | "статьи" | "статье" | "статью" | "статьей" | "статьёй" => {
            Some(StructuralLevel::Statya)
        }
        "часть" | "части" | "частью" | "частею" => {
            Some(StructuralLevel::Chast)
        }
        "пункт" | "пункта" | "пункту" | "пунктом" | "пункте" => {
            Some(StructuralLevel::Punkt)
        }
        "подпункт" | "подпункта" | "подпункту" | "подпунктом" | "подпункте" => {
            Some(StructuralLevel::Podpunkt)
        }
        "абзац" | "абзаца" | "абзацу" | "абзацем" | "абзаце" => {
            Some(StructuralLevel::Abzats)
        }
        _ => None,
    }
}

fn normalize_russian_ordinal(lower: &str) -> Option<&'static str> {
    match lower {
        "первый" | "первом" | "первого" | "первым" | "первую" | "первой" => {
            Some("1")
        }
        "второй" | "втором" | "второго" | "вторым" | "вторую" => {
            Some("2")
        }
        "третий" | "третьем" | "третьего" | "третьим" | "третью" | "третьей" => {
            Some("3")
        }
        "четвертый"
        | "четвёртый"
        | "четвертом"
        | "четвёртом"
        | "четвертого"
        | "четвёртого"
        | "четвертым"
        | "четвёртым" => Some("4"),
        "пятый" | "пятом" | "пятого" | "пятым" => Some("5"),
        "шестой" | "шестом" | "шестого" | "шестым" => Some("6"),
        "седьмой" | "седьмом" | "седьмого" | "седьмым" => Some("7"),
        "восьмой" | "восьмом" | "восьмого" | "восьмым" => Some("8"),
        "девятый" | "девятом" | "девятого" | "девятым" => Some("9"),
        "десятый" | "десятом" | "десятого" | "десятым" => Some("10"),
        _ => None,
    }
}

struct ExtractedSteps {
    steps: Vec<StructuralStep>,
    ambiguous_multi_target: bool,
}

fn extract_structural_steps_checked(src: &str) -> ExtractedSteps {
    let tokens = lex(src);
    let mut steps: Vec<StructuralStep> = Vec::new();
    let mut ambiguous_multi_target = false;
    let mut idx = 0usize;

    while idx < tokens.len() {
        let tok = tokens[idx];
        let raw = tok.lexeme(src);
        let lower = raw.to_lowercase();

        // Detect plural target specifiers (`в пунктах 1 и 2`, `подпунктами "в" - "е"`).
        // Note: `статьи` is genitive singular (`в части 1 статьи 3`) unless followed by range/conjunction.
        if is_plural_level_token(tok.kind, tok.abbrev_id, &lower) && lower != "статьи" {
            ambiguous_multi_target = true;
            idx += 1;
            continue;
        }

        let level = match tok.kind {
            TokenKind::Abbrev => tok.abbrev_id.and_then(classify_abbrev_id),
            TokenKind::Word => classify_singular_level_word(&lower),
            _ => None,
        };
        let Some(level) = level else {
            idx += 1;
            continue;
        };

        // Scan forward past spaces / opening quotes / `N`/`№` for the identifier value.
        let mut cursor = idx + 1;
        let mut saw_quote = false;
        while cursor < tokens.len()
            && (tokens[cursor].kind == TokenKind::Space
                || matches!(tokens[cursor].lexeme(src), "\"" | "«" | "N" | "№"))
        {
            if matches!(tokens[cursor].lexeme(src), "\"" | "«") {
                saw_quote = true;
            }
            cursor += 1;
        }
        if cursor >= tokens.len() {
            break;
        }

        let val_tok = tokens[cursor];
        let val_lex = val_tok.lexeme(src);
        let val_lower = val_lex.to_lowercase();

        let normalized_value: Option<String> = match val_tok.kind {
            TokenKind::HierNum => Some(val_lower),
            TokenKind::EnumMarker => {
                let cleaned = val_lower
                    .trim_matches(|c: char| matches!(c, '"' | '«' | '»' | ')' | '.'))
                    .to_owned();
                (!cleaned.is_empty()).then_some(cleaned)
            }
            TokenKind::Word => {
                if val_lex.bytes().all(|b| b.is_ascii_digit()) {
                    Some(val_lower)
                } else if let Some(ord) = normalize_russian_ordinal(&val_lower) {
                    Some(ord.to_owned())
                } else if level == StructuralLevel::Podpunkt
                    && val_lex.chars().count() == 1
                    && (saw_quote
                        || !matches!(val_lower.as_str(), "в" | "и" | "к" | "о" | "с" | "у" | "а"))
                {
                    Some(val_lower)
                } else {
                    None
                }
            }
            _ => None,
        };

        if let Some(value) = normalized_value {
            if steps.iter().any(|s| s.level == level) {
                ambiguous_multi_target = true;
            }
            steps.push(StructuralStep::new(level, value));

            // Detect coordinated plural targets sharing a singular/homographic level noun
            // (e.g. `статьи 31 и 43`, `части 1 - 3`, `пункта 1, 2`, `подпункта "а", "б"`,
            // `подпункта «а» и «б»`, `в абзаце первом и втором`).
            let mut look = cursor + 1;
            while look < tokens.len()
                && (tokens[look].kind == TokenKind::Space
                    || matches!(tokens[look].lexeme(src), "\"" | "»"))
            {
                look += 1;
            }
            if look < tokens.len() {
                let sep_raw = tokens[look].lexeme(src).to_lowercase();
                let sep = sep_raw.trim_matches(|c: char| matches!(c, '"' | '«' | '»'));
                if matches!(sep, "и" | "-" | "–" | "—" | ",") {
                    let mut after_sep = look + 1;
                    while after_sep < tokens.len()
                        && (tokens[after_sep].kind == TokenKind::Space
                            || matches!(tokens[after_sep].lexeme(src), "\"" | "«"))
                    {
                        after_sep += 1;
                    }
                    if after_sep < tokens.len() {
                        let next_tok = tokens[after_sep];
                        let next_lex = next_tok.lexeme(src);
                        let next_lower = next_lex.to_lowercase();
                        let is_second_id =
                            matches!(next_tok.kind, TokenKind::HierNum | TokenKind::EnumMarker)
                                || (next_tok.kind == TokenKind::Word
                                    && (next_lex.bytes().all(|b| b.is_ascii_digit())
                                        || normalize_russian_ordinal(&next_lower).is_some()
                                        || (level == StructuralLevel::Podpunkt
                                            && next_lex.chars().count() == 1
                                            && next_lex.chars().all(char::is_alphabetic))));
                        if is_second_id {
                            ambiguous_multi_target = true;
                        }
                    }
                }
            }

            idx = cursor + 1;
        } else {
            idx += 1;
        }
    }

    ExtractedSteps {
        steps,
        ambiguous_multi_target,
    }
}

#[derive(Debug)]
enum ActHeaderParse {
    NotAnActHeader,
    HeaderScope {
        act: TargetActRequisites,
        initial_scope: StructuralLocator,
    },
    InlineAmendmentInHeader(TargetActRequisites),
}

fn is_word_boundary_match(haystack: &str, start: usize, end: usize) -> bool {
    let before_ok = haystack
        .get(..start)
        .and_then(|s| s.chars().next_back())
        .is_none_or(|c| !c.is_alphanumeric());
    let after_ok = haystack
        .get(end..)
        .and_then(|s| s.chars().next())
        .is_none_or(|c| !c.is_alphanumeric());
    before_ok && after_ok
}

fn find_word_bounded_ci_span(haystack: &str, needle_lower: &str) -> Option<(usize, usize)> {
    let mut offset = 0usize;
    while offset < haystack.len() {
        let (rel_start, rel_end) = find_ci_span(&haystack[offset..], needle_lower)?;
        let abs_start = offset + rel_start;
        let abs_end = offset + rel_end;
        if is_word_boundary_match(haystack, abs_start, abs_end) {
            return Some((abs_start, abs_end));
        }
        // Advance by one UTF-8 character past `abs_start`.
        let step = haystack[abs_start..]
            .chars()
            .next()
            .map_or(1, char::len_utf8);
        offset = abs_start + step;
    }
    None
}

/// Strip Russian Code-Part suffixes (`части первой`, `часть вторую`, etc.) that
/// precede `*кодекс*` markers (e.g. `Внести в статью 217 части второй Налогового кодекса`)
/// so a Code Part is never misclassified as a sub-article `StructuralLevel::Chast`.
fn strip_trailing_code_part_suffix(scope_slice: &str) -> &str {
    let code_parts = [
        "части первой",
        "часть первую",
        "части второй",
        "часть вторую",
        "части третьей",
        "часть третью",
        "части четвертой",
        "части четвёртой",
        "часть четвертую",
        "часть четвёртую",
    ];
    let trimmed = scope_slice.trim_end();
    for suffix in code_parts {
        if let Some((start, end)) = find_word_bounded_ci_span(trimmed, suffix)
            && end == trimmed.len()
        {
            return trimmed[..start].trim_end();
        }
    }
    trimmed
}

/// Extract unambiguous singular structural scope carried by an amending act header
/// between `Внести [изменение|изменения] в ` and the act-kind noun
/// (e.g. `Внести в часть 1 статьи 95 Федерального закона ...:` -> `statya-95/chast-1`,
/// `Внести в статью 112 Федерального закона ...:` -> `statya-112`).
///
/// Fails closed (returns an empty scope) when the header prefix is plural/ambiguous
/// or refers only to a Code Part (`часть первую Гражданского кодекса`), so child
/// clauses must still supply an unambiguous target locator (`INV-10`).
fn extract_header_initial_scope(stripped: &str) -> StructuralLocator {
    let prefixes = ["внести изменения в ", "внести изменение в ", "внести в "];
    let Some((_, prefix_end)) = prefixes
        .iter()
        .find_map(|p| find_ci_span(stripped, p).filter(|(start, _)| *start == 0))
    else {
        return StructuralLocator::default();
    };
    let tail = &stripped[prefix_end..];

    // Never scan past `" от "`, `'('`, `'"'`, or `'«'` so publication citations
    // (e.g. СЗ РФ `ст. 1`) or act titles can never be misread as `act_scope`.
    let mut hard_cap = tail.len();
    for barrier in [" от ", "(", "\"", "«"] {
        if let Some((pos, _)) = find_ci_span(tail, barrier)
            && pos < hard_cap
        {
            hard_cap = pos;
        }
    }
    let search_window = &tail[..hard_cap];

    let act_kind_markers: &[(&str, bool)] = &[
        ("федерального конституционного закона", false),
        ("федеральный конституционный закон", false),
        ("федерального закона", false),
        ("федеральный закон", false),
        ("закона российской федерации", false),
        ("закон российской федерации", false),
        ("закона рсфср", false),
        ("закон рсфср", false),
        ("гражданского кодекса", true),
        ("гражданский кодекс", true),
        ("градостроительного кодекса", true),
        ("градостроительный кодекс", true),
        ("земельного кодекса", true),
        ("земельный кодекс", true),
        ("бюджетного кодекса", true),
        ("бюджетный кодекс", true),
        ("налогового кодекса", true),
        ("налоговый кодекс", true),
        ("трудового кодекса", true),
        ("трудовой кодекс", true),
        ("кодекса", true),
        ("кодекс", true),
        ("указа", false),
        ("указ", false),
        ("постановления", false),
        ("постановление", false),
        ("распоряжения", false),
        ("распоряжение", false),
        ("приказа", false),
        ("приказ", false),
        ("основ законодательства", false),
        ("основы законодательства", false),
    ];
    let Some((scope_end, is_code)) = act_kind_markers
        .iter()
        .filter_map(|&(kw, is_code)| {
            find_word_bounded_ci_span(search_window, kw).map(|(pos, _)| (pos, is_code))
        })
        .min_by_key(|&(pos, _)| pos)
    else {
        return StructuralLocator::default();
    };
    let mut scope_slice = search_window[..scope_end].trim();
    if is_code {
        scope_slice = strip_trailing_code_part_suffix(scope_slice);
    }
    if scope_slice.is_empty() {
        return StructuralLocator::default();
    }
    let extracted = extract_structural_steps_checked(scope_slice);
    if extracted.ambiguous_multi_target || extracted.steps.is_empty() {
        StructuralLocator::default()
    } else {
        StructuralLocator::new(extracted.steps)
    }
}

fn parse_target_act_header(block_index: usize, trimmed: &str) -> ActHeaderParse {
    let stripped = strip_part_number_prefix(trimmed);
    let lower = stripped.to_lowercase();
    if !(lower.starts_with("внести в ")
        || lower.starts_with("внести изменение в ")
        || lower.starts_with("внести изменения в "))
    {
        return ActHeaderParse::NotAnActHeader;
    }
    let initial_scope = extract_header_initial_scope(stripped);
    let tokens = lex(stripped);
    let mut date: Option<String> = None;
    let mut number: Option<String> = None;

    for (i, tok) in tokens.iter().enumerate() {
        let lexeme = tok.lexeme(stripped);
        if date.is_none() && tok.kind == TokenKind::Date {
            date = Some(lexeme.to_owned());
        }
        if number.is_none() && tok.kind == TokenKind::DocNo {
            number = Some(lexeme.to_owned());
        }
        if date.is_none() && tok.kind == TokenKind::Word && lexeme.to_lowercase() == "от" {
            let tail = &stripped[tok.span.end()..];
            if let Some(spelled) = extract_spelled_russian_date(tail) {
                date = Some(spelled);
            }
        }
        if number.is_none() && matches!(lexeme, "N" | "№") {
            let mut j = i + 1;
            while j < tokens.len() && tokens[j].kind == TokenKind::Space {
                j += 1;
            }
            if j < tokens.len() {
                let start = tokens[j].span.start();
                let mut end = tokens[j].span.end();
                while j + 1 < tokens.len()
                    && (tokens[j + 1].lexeme(stripped) == "-"
                        || tokens[j + 1].kind == TokenKind::Word
                        || tokens[j + 1].kind == TokenKind::HierNum)
                {
                    j += 1;
                    end = tokens[j].span.end();
                }
                let candidate = stripped[start..end].trim();
                if !candidate.is_empty() && candidate.chars().any(|c| c.is_ascii_digit()) {
                    number = Some(candidate.to_owned());
                }
            }
        }
    }

    let Ok(span) = TextSpan::try_new(0, trimmed.len()) else {
        return ActHeaderParse::NotAnActHeader;
    };
    let req = TargetActRequisites {
        raw_header: trimmed.to_owned(),
        date,
        number,
        block_index,
        span,
    };

    if trimmed.ends_with(':') {
        ActHeaderParse::HeaderScope {
            act: req,
            initial_scope,
        }
    } else {
        // Single-sentence inline amendment (`Внести в статью X ... изменение, заменив ...`)
        ActHeaderParse::InlineAmendmentInHeader(req)
    }
}

fn extract_spelled_russian_date(tail: &str) -> Option<String> {
    let parts: Vec<&str> = tail.split_whitespace().take(4).collect();
    if parts.len() < 3 {
        return None;
    }
    let day: u32 = parts[0].parse().ok()?;
    let month = match parts[1].to_lowercase().as_str() {
        "января" => 1,
        "февраля" => 2,
        "марта" => 3,
        "апреля" => 4,
        "мая" => 5,
        "июня" => 6,
        "июля" => 7,
        "августа" => 8,
        "сентября" => 9,
        "октября" => 10,
        "ноября" => 11,
        "декабря" => 12,
        _ => return None,
    };
    let year: u32 = parts[2].trim_end_matches([',', '.']).parse().ok()?;
    if (1..=31).contains(&day) && (1900..=2100).contains(&year) {
        Some(format!("{year:04}-{month:02}-{day:02}"))
    } else {
        None
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ListPrefixKind {
    NumberedItem,   // `1)`, `2)`, `1.1)`
    LetteredItem,   // `а)`, `б)`, ...
    UnmarkedClause, // `в подпункте "н" ...`
}

fn strip_list_prefix(trimmed: &str) -> (ListPrefixKind, &str) {
    let bytes = trimmed.as_bytes();
    // Check `1)` / `12)` / `1.1)`
    let mut i = 0;
    let mut has_digit = false;
    while i < bytes.len() && (bytes[i].is_ascii_digit() || bytes[i] == b'.') {
        if bytes[i].is_ascii_digit() {
            has_digit = true;
        }
        i += 1;
    }
    if has_digit && i < bytes.len() && bytes[i] == b')' {
        return (ListPrefixKind::NumberedItem, trimmed[i + 1..].trim_start());
    }

    // Check Cyrillic single-letter marker `а)`, `б)`, ...
    let mut chars = trimmed.char_indices();
    if let Some((_, first)) = chars.next()
        && first.is_alphabetic()
        && let Some((paren_idx, second)) = chars.next()
        && second == ')'
    {
        return (
            ListPrefixKind::LetteredItem,
            trimmed[paren_idx + 1..].trim_start(),
        );
    }

    (ListPrefixKind::UnmarkedClause, trimmed)
}

fn contains_amendment_verb(lower: &str) -> bool {
    lower.contains("заменить")
        || lower.contains("дополнить")
        || lower.contains("исключить")
        || lower.contains("изложить в следующей редакции")
        || lower.contains("признать утративш")
}

/// Collect subsequent quoted block(s) following `изложить в следующей редакции:`
/// or `следующего содержания:` until the matching closing delimiter terminates
/// the excerpt. Skips editorial notes without absorbing them into `value`.
fn collect_quoted_blocks(
    blocks: &[&str],
    start_idx: usize,
    editorial_notes_skipped: &mut usize,
) -> Option<(String, usize)> {
    let mut idx = start_idx;
    let mut lines: Vec<&str> = Vec::new();
    let mut opener: Option<char> = None;
    let mut guillemet_depth = 0usize;
    let mut ascii_quote_count = 0usize;

    while idx < blocks.len() {
        let t = blocks[idx].trim();
        if t.is_empty() {
            idx += 1;
            continue;
        }
        if is_editorial_header(t) {
            *editorial_notes_skipped += 1;
            if is_standalone_note_header(t)
                && idx + 1 < blocks.len()
                && !looks_like_legislative_block(blocks[idx + 1].trim())
            {
                idx += 2;
            } else {
                idx += 1;
            }
            continue;
        }

        if opener.is_none() {
            if t.starts_with('"') {
                if strip_outer_quotes(t, '"').trim().is_empty() {
                    return None;
                }
                opener = Some('"');
            } else if t.starts_with('«') {
                if strip_outer_quotes(t, '«').trim().is_empty() {
                    return None;
                }
                opener = Some('«');
            } else {
                return None;
            }
        } else if is_top_level_article_heading(t) {
            // Unclosed multi-line quote hit a new top-level article: fail closed.
            return None;
        }

        lines.push(t);
        let open_ch = opener.expect("opener set above");
        let closed = if open_ch == '«' {
            for ch in t.chars() {
                if ch == '«' {
                    guillemet_depth += 1;
                } else if ch == '»' {
                    guillemet_depth = guillemet_depth.saturating_sub(1);
                }
            }
            guillemet_depth == 0 && (t.ends_with("»;") || t.ends_with("».") || t.ends_with('»'))
        } else {
            ascii_quote_count += t.chars().filter(|&c| c == '"').count();
            let ends_quote = t.ends_with("\";") || t.ends_with("\".") || t.ends_with('"');
            // Require balanced quote parity (`ascii_quote_count >= 2 && even`)
            // so an inner quoted law title ending a mid-excerpt paragraph does
            // not close the outer replacement early.
            ends_quote && ascii_quote_count >= 2 && ascii_quote_count.is_multiple_of(2)
        };

        if closed {
            let joined = lines.join("\n");
            let unquoted = strip_outer_quotes(&joined, open_ch);
            if unquoted.trim().is_empty() {
                return None;
            }
            return Some((unquoted, idx));
        }
        idx += 1;
    }
    None
}

fn strip_outer_quotes(s: &str, opener: char) -> String {
    let trimmed = s.trim().trim_end_matches([';', '.']).trim();
    let closer = if opener == '«' { '»' } else { '"' };
    let without_open = trimmed.strip_prefix(opener).unwrap_or(trimmed);
    let without_close = without_open.strip_suffix(closer).unwrap_or(without_open);
    without_close.to_owned()
}

/// Find the UTF-8 char-aligned byte offset of the earliest amendment action
/// keyword in `body` so target structural steps are only parsed before the action.
fn action_prefix_end(body: &str) -> usize {
    let keywords = [
        "после слов",
        "после цифр",
        "перед слов",
        "перед цифр",
        "слово ",
        "слова ",
        "цифру ",
        "цифры ",
        "предложение ",
        "дополнить ",
        "заменить ",
        "исключить",
        "изложить в следующей редакции",
        "признать утративш",
    ];
    let mut best = body.len();
    for kw in keywords {
        if let Some((pos, _)) = find_ci_span(body, kw)
            && pos < best
        {
            best = pos;
        }
    }
    best
}

#[derive(Debug)]
struct ParsedInlineOp {
    kind: ChangeOpKind,
    param: ChangePositionParam,
    loc_value: Option<String>,
    value: Option<String>,
    next_cursor: usize,
}

/// Attempt to parse one inline operation starting at `cursor` inside `body`.
fn parse_one_inline_op(body: &str, cursor: usize) -> Option<ParsedInlineOp> {
    let rest = body.get(cursor..)?.trim_start();
    let offset = body.len() - rest.len();
    let lower = rest.to_lowercase();

    // 1. `после слова/слов/цифры/цифр "<LOC>" дополнить словом/словами/цифрой/цифрами "<VAL>"`
    if lower.starts_with("после слов") || lower.starts_with("после цифр") {
        let q1 = find_next_quote(body, offset, true)?;
        let after_q1 = body.get(q1.end..)?.trim_start();
        if after_q1.to_lowercase().starts_with("дополнить ") {
            let q2 = find_next_quote(body, q1.end, false)?;
            return Some(ParsedInlineOp {
                kind: ChangeOpKind::InsertText,
                param: ChangePositionParam::AfterAnchor,
                loc_value: Some(q1.content),
                value: Some(q2.content),
                next_cursor: q2.end,
            });
        }
        return None;
    }

    // 2. `перед словом/словами/цифрой/цифрами "<LOC>" дополнить словом/словами/цифрой/цифрами "<VAL>"`
    if lower.starts_with("перед слов") || lower.starts_with("перед цифр") {
        let q1 = find_next_quote(body, offset, true)?;
        let after_q1 = body.get(q1.end..)?.trim_start();
        if after_q1.to_lowercase().starts_with("дополнить ") {
            let q2 = find_next_quote(body, q1.end, false)?;
            return Some(ParsedInlineOp {
                kind: ChangeOpKind::InsertText,
                param: ChangePositionParam::BeforeAnchor,
                loc_value: Some(q1.content),
                value: Some(q2.content),
                next_cursor: q2.end,
            });
        }
        return None;
    }

    // 3. `(слово|слова|цифру|цифры|предложение) "<LOC>" (заменить ... "<VAL>" | исключить)`
    if lower.starts_with("слово ")
        || lower.starts_with("слова ")
        || lower.starts_with("цифру ")
        || lower.starts_with("цифры ")
        || lower.starts_with("предложение ")
    {
        let q1 = find_next_quote(body, offset, true)?;
        let after_q1 = body.get(q1.end..)?.trim_start();
        let after_q1_lower = after_q1.to_lowercase();
        if after_q1_lower.starts_with("заменить ") {
            let q2 = find_next_quote(body, q1.end, false)?;
            return Some(ParsedInlineOp {
                kind: ChangeOpKind::ReplaceText,
                param: ChangePositionParam::ExactAnchor,
                loc_value: Some(q1.content),
                value: Some(q2.content),
                next_cursor: q2.end,
            });
        }
        if let Some((_, rel_end)) = find_ci_span(after_q1, "исключить")
            && after_q1_lower.starts_with("исключить")
        {
            let after_q1_offset = body.len() - after_q1.len();
            return Some(ParsedInlineOp {
                kind: ChangeOpKind::DeleteText,
                param: ChangePositionParam::ExactAnchor,
                loc_value: Some(q1.content),
                value: None,
                next_cursor: (after_q1_offset + rel_end).min(body.len()),
            });
        }
        return None;
    }

    // 4. `дополнить (словом|словами|цифрой|цифрами|предложением) "<VAL>"`
    if lower.starts_with("дополнить словом ")
        || lower.starts_with("дополнить словами ")
        || lower.starts_with("дополнить цифрой ")
        || lower.starts_with("дополнить цифрами ")
        || lower.starts_with("дополнить предложением ")
    {
        let q = find_next_quote(body, offset, false)?;
        return Some(ParsedInlineOp {
            kind: ChangeOpKind::InsertText,
            param: ChangePositionParam::EndOfComponent,
            loc_value: None,
            value: Some(q.content),
            next_cursor: q.end,
        });
    }

    // 5. `признать утратившим/утратившей/утратившими силу`
    if lower.starts_with("признать утративш") {
        let end = find_ci_span(rest, "силу")
            .map(|(_, rel_end)| offset + rel_end)
            .unwrap_or(body.len());
        return Some(ParsedInlineOp {
            kind: ChangeOpKind::Repeal,
            param: ChangePositionParam::WholeComponent,
            loc_value: None,
            value: None,
            next_cursor: end.min(body.len()),
        });
    }

    None
}

/// Extract the child structural step for `дополнить (статьей|частью|пунктом|подпунктом|абзацем) <N> следующего содержания:`.
fn extract_attach_child(body: &str) -> Result<Option<StructuralStep>, &'static str> {
    let Some((_, end)) = find_ci_span(body, "дополнить ") else {
        return Ok(None);
    };
    let Some(tail) = body.get(end..) else {
        return Ok(None);
    };
    let extracted = extract_structural_steps_checked(tail);
    if extracted.ambiguous_multi_target {
        return Err("plural or multi-target structural attach is unsupported");
    }
    Ok(extracted.steps.into_iter().next())
}

/// Deterministically parse decoded paragraphs of an amending statute into
/// `Proposed` [`ChangeClauseCandidate`] items and fail-closed [`ChangeParseRefusal`]s.
pub fn parse_amending_blocks(blocks: &[&str]) -> ChangeGrammarReport {
    let mut candidates = Vec::new();
    let mut refusals = Vec::new();
    let mut editorial_notes_skipped = 0usize;

    let mut current_act: Option<TargetActRequisites> = None;
    let mut act_scope = StructuralLocator::default();
    // `None` means the active container header failed closed (poisoned scope):
    // child clauses inheriting a poisoned scope MUST fail closed as `AmbiguousTarget`
    // instead of silently falling back onto `act_scope` or `numbered_scope` (`INV-10`).
    let mut numbered_scope: Option<StructuralLocator> = Some(StructuralLocator::default());
    let mut lettered_scope: Option<StructuralLocator> = Some(StructuralLocator::default());

    let mut idx = 0usize;
    while idx < blocks.len() {
        let raw = blocks[idx];
        let trimmed = raw.trim();

        if is_editorial_header(trimmed) {
            editorial_notes_skipped += 1;
            if is_standalone_note_header(trimmed)
                && idx + 1 < blocks.len()
                && !looks_like_legislative_block(blocks[idx + 1].trim())
            {
                idx += 2;
            } else {
                idx += 1;
            }
            continue;
        }

        if is_signature_or_preamble_noise(trimmed) {
            idx += 1;
            continue;
        }

        // Entering a new top-level article resets active target act and scopes
        // so transitional/commencement articles cannot inherit prior act context.
        if is_top_level_article_heading(trimmed) {
            current_act = None;
            act_scope = StructuralLocator::default();
            numbered_scope = Some(StructuralLocator::default());
            lettered_scope = Some(StructuralLocator::default());
            idx += 1;
            continue;
        }

        // Commencement / transitional clauses (`1. Настоящий Федеральный закон вступает в силу...`,
        // `8. Установить, что ...`) stay outside ChangeGrammar clause mutation scope.
        let stripped_part = strip_part_number_prefix(trimmed);
        let stripped_lower = stripped_part.to_lowercase();
        if stripped_lower.starts_with("настоящий федеральный закон вступает в силу")
            || stripped_lower.starts_with("установить, что ")
        {
            idx += 1;
            continue;
        }

        match parse_target_act_header(idx, trimmed) {
            ActHeaderParse::HeaderScope { act, initial_scope } => {
                current_act = Some(act);
                act_scope = initial_scope.clone();
                numbered_scope = Some(initial_scope.clone());
                lettered_scope = Some(initial_scope);
                idx += 1;
                continue;
            }
            ActHeaderParse::InlineAmendmentInHeader(act) => {
                current_act = Some(act.clone());
                act_scope = StructuralLocator::default();
                numbered_scope = Some(StructuralLocator::default());
                lettered_scope = Some(StructuralLocator::default());
                refusals.push(ChangeParseRefusal::UnsupportedOperation {
                    block_index: idx,
                    span: act.span,
                    excerpt: trimmed.chars().take(120).collect(),
                });
                idx += 1;
                continue;
            }
            ActHeaderParse::NotAnActHeader => {}
        }

        let Some(owner_act) = current_act.clone() else {
            idx += 1;
            continue;
        };

        let (prefix_kind, body) = strip_list_prefix(trimmed);
        let body_lower = body.to_lowercase();
        let Ok(block_span) = TextSpan::try_new(0, raw.len()) else {
            idx += 1;
            continue;
        };

        // Case 1: Pure container header (`1) в части 1 статьи 3:`, `а) в пункте 1 части 1:`).
        if body.ends_with(':') && !contains_amendment_verb(&body_lower) {
            let extracted = extract_structural_steps_checked(body);
            if extracted.ambiguous_multi_target || extracted.steps.is_empty() {
                match prefix_kind {
                    ListPrefixKind::NumberedItem => {
                        numbered_scope = None;
                        lettered_scope = None;
                    }
                    ListPrefixKind::LetteredItem | ListPrefixKind::UnmarkedClause => {
                        lettered_scope = None;
                    }
                }
                refusals.push(ChangeParseRefusal::AmbiguousTarget {
                    block_index: idx,
                    span: block_span,
                    reason: if extracted.ambiguous_multi_target {
                        "plural or multi-target container header is unsupported"
                    } else {
                        "unrecognized container header has no structural locator"
                    },
                });
            } else {
                match prefix_kind {
                    ListPrefixKind::NumberedItem => {
                        let scope = act_scope.with_overlay(&extracted.steps);
                        numbered_scope = Some(scope.clone());
                        lettered_scope = Some(scope);
                    }
                    ListPrefixKind::LetteredItem => {
                        if let Some(parent) = numbered_scope.as_ref() {
                            lettered_scope = Some(parent.with_overlay(&extracted.steps));
                        } else {
                            lettered_scope = None;
                            refusals.push(ChangeParseRefusal::AmbiguousTarget {
                                block_index: idx,
                                span: block_span,
                                reason: "container header inherits a failed parent container scope",
                            });
                        }
                    }
                    ListPrefixKind::UnmarkedClause => {
                        if let Some(parent) = numbered_scope.as_ref() {
                            if parent == &act_scope {
                                let scope = act_scope.with_overlay(&extracted.steps);
                                numbered_scope = Some(scope.clone());
                                lettered_scope = Some(scope);
                            } else if let Some(l_parent) = lettered_scope.as_ref() {
                                lettered_scope = Some(l_parent.with_overlay(&extracted.steps));
                            } else {
                                lettered_scope = None;
                                refusals.push(ChangeParseRefusal::AmbiguousTarget {
                                    block_index: idx,
                                    span: block_span,
                                    reason: "container header inherits a failed parent container scope",
                                });
                            }
                        } else {
                            lettered_scope = None;
                            refusals.push(ChangeParseRefusal::AmbiguousTarget {
                                block_index: idx,
                                span: block_span,
                                reason: "container header inherits a failed parent container scope",
                            });
                        }
                    }
                }
            }
            idx += 1;
            continue;
        }

        // Determine inherited base scope for this clause (`None` => poisoned parent).
        let maybe_base_scope = match prefix_kind {
            ListPrefixKind::NumberedItem => {
                numbered_scope = Some(act_scope.clone());
                lettered_scope = Some(act_scope.clone());
                Some(act_scope.clone())
            }
            ListPrefixKind::LetteredItem => {
                lettered_scope = numbered_scope.clone();
                numbered_scope.clone()
            }
            ListPrefixKind::UnmarkedClause => lettered_scope.clone(),
        };

        let Some(base_scope) = maybe_base_scope else {
            refusals.push(ChangeParseRefusal::AmbiguousTarget {
                block_index: idx,
                span: block_span,
                reason: "clause inherits a failed parent container scope",
            });
            if body.ends_with(':')
                && let Some((_, last_idx)) =
                    collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
            {
                idx = last_idx + 1;
            } else {
                idx += 1;
            }
            continue;
        };

        let prefix_end = action_prefix_end(body);
        let extracted_local = extract_structural_steps_checked(&body[..prefix_end]);
        let target_locator = base_scope.with_overlay(&extracted_local.steps);

        if extracted_local.ambiguous_multi_target {
            refusals.push(ChangeParseRefusal::AmbiguousTarget {
                block_index: idx,
                span: block_span,
                reason: "plural or multi-target structural locator is unsupported",
            });
            if body.ends_with(':')
                && let Some((_, last_idx)) =
                    collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
            {
                idx = last_idx + 1;
                continue;
            }
            idx += 1;
            continue;
        }

        // Case 2: Whole-component replacement (`изложить в следующей редакции:`).
        // Sentence-scoped replacements (`второе предложение изложить в следующей редакции:`)
        // fail closed as UnsupportedOperation rather than widening to WholeComponent.
        if body_lower.contains("изложить в следующей редакции") {
            let prefix_lower = body[..prefix_end].to_lowercase();
            if prefix_lower.contains("предложени") {
                refusals.push(ChangeParseRefusal::UnsupportedOperation {
                    block_index: idx,
                    span: block_span,
                    excerpt: trimmed.chars().take(120).collect(),
                });
                if let Some((_, last_idx)) =
                    collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
                {
                    idx = last_idx + 1;
                } else {
                    idx += 1;
                }
                continue;
            }
            if target_locator.is_empty() {
                refusals.push(ChangeParseRefusal::AmbiguousTarget {
                    block_index: idx,
                    span: block_span,
                    reason: "missing structural locator for ReplaceText(WholeComponent)",
                });
                if let Some((_, last_idx)) =
                    collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
                {
                    idx = last_idx + 1;
                } else {
                    idx += 1;
                }
                continue;
            }
            match collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped) {
                Some((quoted, last_idx)) => {
                    candidates.push(ChangeClauseCandidate {
                        block_index: idx,
                        evidence_span: block_span,
                        owner_act,
                        target_locator,
                        child_spec: None,
                        kind: ChangeOpKind::ReplaceText,
                        param: ChangePositionParam::WholeComponent,
                        loc_value: None,
                        value: Some(quoted),
                    });
                    idx = last_idx + 1;
                }
                None => {
                    refusals.push(ChangeParseRefusal::IncompleteSource {
                        block_index: idx,
                        span: block_span,
                        reason: "expected quoted replacement block after 'изложить в следующей редакции'",
                    });
                    idx += 1;
                }
            }
            continue;
        }

        // Case 3: Structural attach (`дополнить статьей/частью/пунктом/подпунктом/абзацем ... следующего содержания:`)
        // or next-line end-of-component sentence append (`дополнить предложением следующего содержания:`).
        // Guard with `body.ends_with(':')` AND require `body[prefix_end..]` to start with
        // `дополнить ` so a compound colon-terminated clause carrying an earlier inline op
        // never silently drops that leading op (`INV-10`).
        if body.ends_with(':')
            && body_lower.contains("дополнить ")
            && body_lower.contains("следующего содержания")
        {
            if !body[prefix_end..]
                .trim_start()
                .to_lowercase()
                .starts_with("дополнить ")
            {
                refusals.push(ChangeParseRefusal::UnsupportedOperation {
                    block_index: idx,
                    span: block_span,
                    excerpt: trimmed.chars().take(120).collect(),
                });
                if let Some((_, last_idx)) =
                    collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
                {
                    idx = last_idx + 1;
                } else {
                    idx += 1;
                }
                continue;
            }
            if body_lower.contains("дополнить предложением следующего содержания")
            {
                if target_locator.is_empty() {
                    refusals.push(ChangeParseRefusal::AmbiguousTarget {
                        block_index: idx,
                        span: block_span,
                        reason: "missing structural locator for InsertText(EndOfComponent)",
                    });
                    if let Some((_, last_idx)) =
                        collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
                    {
                        idx = last_idx + 1;
                    } else {
                        idx += 1;
                    }
                    continue;
                }
                match collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped) {
                    Some((quoted, last_idx)) => {
                        candidates.push(ChangeClauseCandidate {
                            block_index: idx,
                            evidence_span: block_span,
                            owner_act,
                            target_locator,
                            child_spec: None,
                            kind: ChangeOpKind::InsertText,
                            param: ChangePositionParam::EndOfComponent,
                            loc_value: None,
                            value: Some(quoted),
                        });
                        idx = last_idx + 1;
                    }
                    None => {
                        refusals.push(ChangeParseRefusal::IncompleteSource {
                            block_index: idx,
                            span: block_span,
                            reason: "expected quoted sentence block after 'дополнить предложением следующего содержания'",
                        });
                        idx += 1;
                    }
                }
                continue;
            }
            match extract_attach_child(body) {
                Ok(Some(child)) => {
                    let target_with_child =
                        target_locator.with_overlay(std::slice::from_ref(&child));
                    match collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped) {
                        Some((quoted, last_idx)) => {
                            candidates.push(ChangeClauseCandidate {
                                block_index: idx,
                                evidence_span: block_span,
                                owner_act,
                                target_locator: target_with_child,
                                child_spec: Some(child),
                                kind: ChangeOpKind::Attach,
                                param: ChangePositionParam::NewComponent,
                                loc_value: None,
                                value: Some(quoted),
                            });
                            idx = last_idx + 1;
                        }
                        None => {
                            refusals.push(ChangeParseRefusal::IncompleteSource {
                                block_index: idx,
                                span: block_span,
                                reason: "expected quoted component body after 'следующего содержания'",
                            });
                            idx += 1;
                        }
                    }
                }
                Ok(None) | Err(_) => {
                    refusals.push(ChangeParseRefusal::UnsupportedOperation {
                        block_index: idx,
                        span: block_span,
                        excerpt: trimmed.chars().take(120).collect(),
                    });
                    if let Some((_, last_idx)) =
                        collect_quoted_blocks(blocks, idx + 1, &mut editorial_notes_skipped)
                    {
                        idx = last_idx + 1;
                    } else {
                        idx += 1;
                    }
                }
            }
            continue;
        }

        // Case 4: Inline single or multi-operation clause (`слово "..." заменить ...`,
        // `после/перед слов "..." дополнить ...`, `исключить`, `признать утратившим силу`).
        if contains_amendment_verb(&body_lower) {
            if target_locator.is_empty() {
                refusals.push(ChangeParseRefusal::AmbiguousTarget {
                    block_index: idx,
                    span: block_span,
                    reason: "amendment clause has no structural target locator",
                });
                idx += 1;
                continue;
            }

            let mut cursor = prefix_end;
            let mut parsed_any_in_clause = false;
            while let Some(slice) = body.get(cursor..) {
                let rem = slice.trim_start_matches([',', ';', '.', ' ', '\u{00a0}']);
                if rem.is_empty() {
                    break;
                }
                let next_offset = body.len() - rem.len();
                let maybe_op = parse_one_inline_op(body, next_offset).or_else(|| {
                    if !parsed_any_in_clause {
                        return None;
                    }
                    // Allow Russian coordinating conjunction (`и `, `а `) between
                    // chained inline operations only when the tail parses cleanly.
                    let conj_len = if let Some((_, end)) = find_ci_span(rem, "и ")
                        && rem.to_lowercase().starts_with("и ")
                    {
                        end
                    } else if let Some((_, end)) = find_ci_span(rem, "а ")
                        && rem.to_lowercase().starts_with("а ")
                    {
                        end
                    } else {
                        return None;
                    };
                    parse_one_inline_op(body, next_offset + conj_len)
                });
                if let Some(op) = maybe_op {
                    candidates.push(ChangeClauseCandidate {
                        block_index: idx,
                        evidence_span: block_span,
                        owner_act: owner_act.clone(),
                        target_locator: target_locator.clone(),
                        child_spec: None,
                        kind: op.kind,
                        param: op.param,
                        loc_value: op.loc_value,
                        value: op.value,
                    });
                    cursor = op.next_cursor;
                    parsed_any_in_clause = true;
                } else {
                    // Fail closed on ANY unparsed non-empty remainder (`INV-10`).
                    let has_unclosed_quote = (rem.matches('"').count() % 2 == 1)
                        || (rem.matches('«').count() != rem.matches('»').count());
                    if has_unclosed_quote {
                        refusals.push(ChangeParseRefusal::IncompleteSource {
                            block_index: idx,
                            span: block_span,
                            reason: "unclosed quote in inline amendment clause",
                        });
                    } else {
                        refusals.push(ChangeParseRefusal::UnsupportedOperation {
                            block_index: idx,
                            span: block_span,
                            excerpt: rem.chars().take(120).collect(),
                        });
                    }
                    break;
                }
            }
            idx += 1;
            continue;
        }

        // Fail-closed catch-all (`INV-10`): any unhandled non-noise clause inside
        // an active amending article produces UnsupportedOperation instead of
        // silently disappearing.
        refusals.push(ChangeParseRefusal::UnsupportedOperation {
            block_index: idx,
            span: block_span,
            excerpt: trimmed.chars().take(120).collect(),
        });
        idx += 1;
    }

    ChangeGrammarReport {
        candidates,
        refusals,
        editorial_notes_skipped,
        non_claims: CHANGE_GRAMMAR_NON_CLAIMS,
    }
}
