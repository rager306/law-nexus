//! Public covering lexer for decoded legal-act text (M197, ADR-0028 step 1).
//!
//! Complements the private alphabetic [`crate::tokenizer`] with a
//! byte-span-preserving, infallible scanner over the closed S01 token set.
//! Two invariants hold for every produced token stream:
//!
//! * covering — the concatenation of all token lexemes equals the source;
//! * locality — every span is a non-empty half-open byte range on char
//!   boundaries, so lexemes are recovered by slicing the source.
//!
//! Lexemes are never stored: [`NpaToken::lexeme`] slices the source. The S01
//! sidecar JSON (`fz44_npa_tokens.json`) is the behavioral oracle.

use std::sync::OnceLock;

use crate::domain::TextSpan;

/// Closed token-kind set fixed by the S01 golden vocabulary (nine kinds).
///
/// `Editorial` is deliberately absent: it belongs to wave 2, and the S01
/// hostile fixtures already fail closed on it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenKind {
    Word,
    Abbrev,
    HierNum,
    Date,
    DocNo,
    EnumMarker,
    LawCode,
    Punct,
    Space,
}

impl TokenKind {
    /// Golden-facing kind name (matches the `fz44_npa_tokens.json` schema).
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Word => "Word",
            Self::Abbrev => "Abbrev",
            Self::HierNum => "HierNum",
            Self::Date => "Date",
            Self::DocNo => "DocNo",
            Self::EnumMarker => "EnumMarker",
            Self::LawCode => "LawCode",
            Self::Punct => "Punct",
            Self::Space => "Space",
        }
    }
}

/// Stable identifier of a canonical legal-drafting abbreviation lexeme.
///
/// A copyable newtype over the S01 table id (`st`, `pp`, ...). Deliberately
/// not an enum (no governor source-scan surface) and not a
/// `closed_vocabularies` row.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct AbbrevId(&'static str);

impl AbbrevId {
    pub const fn as_str(self) -> &'static str {
        self.0
    }
}

/// One covering token: kind, non-empty byte span into the source, and an
/// abbreviation id when [`TokenKind::Abbrev`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NpaToken {
    pub kind: TokenKind,
    pub span: TextSpan,
    pub abbrev_id: Option<AbbrevId>,
}

impl NpaToken {
    /// Source slice covered by this token. Lexemes are never stored; spans
    /// produced by [`lex`] always sit on char boundaries.
    pub fn lexeme<'s>(&self, src: &'s str) -> &'s str {
        debug_assert!(src.is_char_boundary(self.span.start()));
        debug_assert!(src.is_char_boundary(self.span.end()));
        &src[self.span.start()..self.span.end()]
    }
}

/// Closed allowlist of canonical legal-drafting abbreviation ids (the 17-id
/// S01 canon, D329/D334). Ids only: the lexemes themselves are data and come
/// from the `npa_abbrev_lexicon` map of the embedded ontology YAML — there is
/// deliberately no second runtime lexeme table (ADR-0028 decision 2).
const NPA_ABBREV_IDS: [&str; 17] = [
    "st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd", "pril", "prim", "red", "izm",
    "utv", "sm", "sr", "g",
];

/// Parsed lexicon entry: canonical id plus its lexeme (dot included), sliced
/// straight out of the embedded YAML.
type AbbrevEntry = (AbbrevId, &'static str);

/// The YAML lexicon, parsed once on the first [`lex`] call. `lex` stays
/// infallible: a malformed catalog is a build-data defect, so the parse fails
/// closed with a precise panic instead of a `Result` on the hot path.
static ABBREV_LEXICON: OnceLock<Vec<AbbrevEntry>> = OnceLock::new();

fn abbrev_lexicon() -> &'static [AbbrevEntry] {
    ABBREV_LEXICON.get_or_init(|| {
        let mut table = parse_abbrev_lexicon(crate::prefix_catalog::EMBEDDED_ONTOLOGY_YAML);
        // Longest-first so `ст.ст.` wins over `ст.` and `пп.` over `п.`
        // (stable sort keeps YAML order for equal byte lengths).
        table.sort_by_key(|entry| std::cmp::Reverse(entry.1.len()));
        table
    })
}

/// Fail-closed parse of the `npa_abbrev_lexicon` sibling map: the heading
/// must exist, every id must be in the closed S01 allowlist exactly once,
/// every lexeme must be non-empty, and every canonical id must be present.
fn parse_abbrev_lexicon(yaml: &'static str) -> Vec<AbbrevEntry> {
    let entries = yaml_map_scalars(yaml, "npa_abbrev_lexicon:")
        .expect("kb-ontology.yaml must carry the `npa_abbrev_lexicon:` map");
    assert!(
        !entries.is_empty(),
        "npa_abbrev_lexicon must list the S01 abbreviation scalars"
    );
    let mut table: Vec<AbbrevEntry> = Vec::with_capacity(entries.len());
    let mut seen: Vec<&'static str> = Vec::with_capacity(NPA_ABBREV_IDS.len());
    for (id, lexeme) in entries {
        assert!(
            !seen.contains(&id),
            "npa_abbrev_lexicon: duplicate id '{id}'"
        );
        seen.push(id);
        assert!(
            NPA_ABBREV_IDS.contains(&id),
            "npa_abbrev_lexicon: unknown id '{id}' is outside the S01 canon"
        );
        assert!(
            !lexeme.is_empty(),
            "npa_abbrev_lexicon: id '{id}' has an empty lexeme"
        );
        table.push((AbbrevId(id), lexeme));
    }
    for id in NPA_ABBREV_IDS {
        assert!(
            seen.contains(&id),
            "npa_abbrev_lexicon: missing canonical id '{id}'"
        );
    }
    table
}

/// Hand-rolled scalar reader for one YAML sibling map (the private
/// `prefix_catalog::map_scalars` pattern, not the module itself): after
/// `heading`, collect `key: scalar` pairs until the first line whose indent
/// is <= the heading's own (the next sibling key). Comments are stripped by
/// the `#` rule; quoted scalars are unquoted. Returns `None` only when the
/// heading is absent.
fn yaml_map_scalars<'y>(yaml: &'y str, heading: &str) -> Option<Vec<(&'y str, &'y str)>> {
    let mut entries = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in yaml.lines() {
        let line = raw.split('#').next().unwrap_or(raw);
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if !in_map {
            if trimmed == heading {
                in_map = true;
                heading_indent = indent;
            }
            continue;
        }
        if indent <= heading_indent {
            return Some(entries);
        }
        let Some((key, value)) = trimmed.split_once(':') else {
            panic!("npa_abbrev_lexicon: non-scalar line inside the map: '{trimmed}'");
        };
        let value = value.trim().trim_matches('"').trim_matches('\'');
        entries.push((key.trim(), value));
    }
    in_map.then_some(entries)
}

/// Lex `src` into covering tokens (infallible, single left-to-right pass).
///
/// * empty input → no tokens;
/// * whitespace-only input → a single [`TokenKind::Space`];
/// * dates (`dd.mm.yyyy`, day 1..=31, month 1..=12) win over hier-numbers;
/// * a hier-number needs inner digits on both sides of at least one dot, so
///   `1.` is never one;
/// * `EnumMarker` is start-of-input-local (`1.`, `1)`, `10)`, `а)`) plus the
///   quoted subpoint label `"а"` = `Punct('"') + EnumMarker + Punct('"')` —
///   a heading `Глава 1.` sits at pos > 0 and stays `Word + Punct`;
/// * `DocNo` keeps its inner hyphen (`318-ФЗ`, `5-ФКЗ`) and a leading Latin
///   `N` stays `Word` (D330 rule 10);
/// * `LawCode` is exact equality on a whole alphabetic run (`ФЗ`, `ФКЗ`),
///   never a prefix match — `Федеральный` is a Word;
/// * unknown bytes classify as `Word` / `Punct` / `Space` and are never
///   dropped: the concatenation of all lexemes equals `src`.
pub fn lex(src: &str) -> Vec<NpaToken> {
    let mut tokens = Vec::new();
    let mut pos = 0usize;
    while pos < src.len() {
        debug_assert!(src.is_char_boundary(pos));
        let Some(ch) = src[pos..].chars().next() else {
            break;
        };
        // Quoted subpoint label (D330 rule 6): `п "а"` splits into
        // `Punct('"') + EnumMarker` here, and the closing quote falls back to
        // the greedy Punct scan — recognized before Punct could swallow the
        // letter into the run.
        if ch == '"' {
            if let Some(letter_end) = quoted_enum_letter_end(src, pos) {
                let quote_span = TextSpan::try_new(pos, pos + 1)
                    .expect("lexer invariant: an ASCII quote is exactly one byte");
                tokens.push(NpaToken {
                    kind: TokenKind::Punct,
                    span: quote_span,
                    abbrev_id: None,
                });
                let letter_span = TextSpan::try_new(pos + 1, letter_end)
                    .expect("lexer invariant: one cyrillic letter is at least two bytes");
                tokens.push(NpaToken {
                    kind: TokenKind::EnumMarker,
                    span: letter_span,
                    abbrev_id: None,
                });
                pos = letter_end;
                continue;
            }
        }
        let (kind, abbrev_id, end) = if ch.is_whitespace() {
            (
                TokenKind::Space,
                None,
                scan_while(src, pos, |c| c.is_whitespace()),
            )
        } else if ch.is_alphabetic() {
            if let Some((end, id)) = scan_abbrev(src, pos) {
                (TokenKind::Abbrev, Some(id), end)
            } else if let Some(end) = scan_enum_marker_letter(src, pos) {
                (TokenKind::EnumMarker, None, end)
            } else {
                let end = scan_while(src, pos, |c| c.is_alphabetic());
                if is_law_code(&src[pos..end]) {
                    (TokenKind::LawCode, None, end)
                } else {
                    (TokenKind::Word, None, end)
                }
            }
        } else if ch.is_ascii_digit() {
            if let Some(end) = scan_date(src, pos) {
                (TokenKind::Date, None, end)
            } else if let Some(end) = scan_hier_num(src, pos) {
                (TokenKind::HierNum, None, end)
            } else if let Some(end) = scan_doc_no(src, pos) {
                (TokenKind::DocNo, None, end)
            } else if let Some(end) = scan_enum_marker_digits(src, pos) {
                (TokenKind::EnumMarker, None, end)
            } else {
                (
                    TokenKind::Word,
                    None,
                    scan_while(src, pos, |c| c.is_ascii_digit()),
                )
            }
        } else {
            let punct = |c: char| !c.is_whitespace() && !c.is_alphabetic() && !c.is_ascii_digit();
            (TokenKind::Punct, None, scan_while(src, pos, punct))
        };
        let span = TextSpan::try_new(pos, end)
            .expect("lexer invariant: every token consumes at least one char");
        tokens.push(NpaToken {
            kind,
            span,
            abbrev_id,
        });
        pos = end;
    }
    tokens
}

/// Advances past the maximal run of chars satisfying `pred`.
fn scan_while(src: &str, start: usize, pred: impl Fn(char) -> bool) -> usize {
    let mut end = start;
    for ch in src[start..].chars() {
        if !pred(ch) {
            break;
        }
        end += ch.len_utf8();
    }
    end
}

/// Matches a canonical abbrev lexeme (dot included), longest-first, only at
/// a word boundary (no preceding alphabetic char).
///
/// C2 match rule (M198 S02/T02, D329 NARROW follow-up): a lexeme with two
/// or more alphabetic chars folds Unicode case, so the heading forms
/// `Абз.` / `Ст.` / `Гл.` and the fully uppercased `СТ.СТ.` fold onto
/// `абз.` / `ст.` / `гл.` / `ст.ст.`; a one-letter lexeme (`ч.`, `п.`,
/// `г.`) stays lowercase-exact, so hostile initials `Ч.` / `П.` / `А.` and
/// `Г. Москва` fall through to Word + Punct instead of minting Abbrevs
/// (Q3: a global case-fold would poison the unknown-tail histogram and the
/// future LawRef — 1-letter exact is the fail-closed contour).
///
/// The fold consumes exactly the lexeme's byte length and only at a char
/// boundary, so a different-length casing or a mid-char cut (`глава`,
/// `абзац`) never matches. `eq_ignore_ascii_case` is deliberately not used:
/// Cyrillic does not fold under ASCII rules (MEM1325).
fn scan_abbrev(src: &str, start: usize) -> Option<(usize, AbbrevId)> {
    let at_word_start = src[..start]
        .chars()
        .next_back()
        .is_none_or(|prev| !prev.is_alphabetic());
    if !at_word_start {
        return None;
    }
    abbrev_lexicon().iter().find_map(|(id, lexeme)| {
        lexeme_matches(src, start, lexeme).then(|| (start + lexeme.len(), *id))
    })
}

/// One-lexeme prefix matcher behind [`scan_abbrev`]: allocation-free
/// char-wise Unicode case folding for stem-ge-2 lexemes, exact
/// `starts_with` for one-letter lexemes.
fn lexeme_matches(src: &str, start: usize, lexeme: &str) -> bool {
    if lexeme.chars().filter(|ch| ch.is_alphabetic()).count() < 2 {
        // One-letter lexemes (`ч.` / `п.` / `г.`): lowercase-exact (Q3).
        return src[start..].starts_with(lexeme);
    }
    let end = start + lexeme.len();
    if end > src.len() || !src.is_char_boundary(end) {
        return false;
    }
    let mut src_chars = src[start..end].chars();
    for lex_ch in lexeme.chars() {
        match src_chars.next() {
            Some(src_ch) if fold_eq(src_ch, lex_ch) => {}
            _ => return false,
        }
    }
    src_chars.next().is_none()
}

/// Allocation-free single-char Unicode lowercase equality (Cyrillic folds
/// here; ASCII-only helpers would not).
fn fold_eq(a: char, b: char) -> bool {
    let mut a = a.to_lowercase();
    let mut b = b.to_lowercase();
    loop {
        match (a.next(), b.next()) {
            (None, None) => return true,
            (Some(x), Some(y)) if x == y => continue,
            _ => return false,
        }
    }
}

/// Recognizes `dd.mm.yyyy` (2-2-4 widths) with day 1..=31 and month 1..=12.
fn scan_date(src: &str, start: usize) -> Option<usize> {
    let bytes = src.as_bytes();
    let end = start + 10;
    if end > bytes.len() {
        return None;
    }
    let digit = |offset: usize| bytes[start + offset].is_ascii_digit();
    if !(digit(0)
        && digit(1)
        && bytes[start + 2] == b'.'
        && digit(3)
        && digit(4)
        && bytes[start + 5] == b'.'
        && digit(6)
        && digit(7)
        && digit(8)
        && digit(9))
    {
        return None;
    }
    let day = u32::from(bytes[start] - b'0') * 10 + u32::from(bytes[start + 1] - b'0');
    let month = u32::from(bytes[start + 3] - b'0') * 10 + u32::from(bytes[start + 4] - b'0');
    if (1..=31).contains(&day) && (1..=12).contains(&month) {
        Some(end)
    } else {
        None
    }
}

/// Recognizes the longest `digits(.digits)+` run; returns `None` when the
/// digits are undotted (`1.` is Word + Punct, never a hier-number).
fn scan_hier_num(src: &str, start: usize) -> Option<usize> {
    let bytes = src.as_bytes();
    let mut pos = start;
    while pos < bytes.len() && bytes[pos].is_ascii_digit() {
        pos += 1;
    }
    if pos == start {
        return None;
    }
    let mut end = None;
    loop {
        if pos >= bytes.len() || bytes[pos] != b'.' {
            break;
        }
        match bytes.get(pos + 1) {
            Some(next) if next.is_ascii_digit() => pos += 2,
            _ => break,
        }
        while pos < bytes.len() && bytes[pos].is_ascii_digit() {
            pos += 1;
        }
        end = Some(pos);
    }
    end
}

/// Recognizes `digits-ФЗ` / `digits-ФКЗ` as one DocNo token (D330 rule 10):
/// the hyphen stays inside the token and the suffix must be the whole
/// following alphabetic run, so a Latin `N` in `N 44-ФЗ` stays a Word and
/// `44-ФЗх` never mints a DocNo.
fn scan_doc_no(src: &str, start: usize) -> Option<usize> {
    let bytes = src.as_bytes();
    let mut pos = start;
    while pos < bytes.len() && bytes[pos].is_ascii_digit() {
        pos += 1;
    }
    if pos == start || bytes.get(pos) != Some(&b'-') {
        return None;
    }
    let after_hyphen = pos + 1;
    for suffix in ["ФЗ", "ФКЗ"] {
        let end = after_hyphen + suffix.len();
        if src[after_hyphen..].starts_with(suffix)
            && !src[end..].chars().next().is_some_and(char::is_alphabetic)
        {
            return Some(end);
        }
    }
    None
}

/// Start-of-input digit marker (`1.`, `1)`, `10)`, `11)`; D330 rule 6): the
/// marker kind is local to byte 0, so the digits of a heading `Глава 1.` —
/// sitting at pos > 0 — stay a Word, and `1.` is still never a hier-number.
fn scan_enum_marker_digits(src: &str, start: usize) -> Option<usize> {
    if start != 0 {
        return None;
    }
    let bytes = src.as_bytes();
    let mut pos = start;
    while pos < bytes.len() && bytes[pos].is_ascii_digit() {
        pos += 1;
    }
    if pos == start {
        return None;
    }
    match bytes.get(pos) {
        Some(b'.' | b')') => Some(pos + 1),
        _ => None,
    }
}

/// Start-of-input single lowercase cyrillic marker (`а)`; D330 rule 6).
fn scan_enum_marker_letter(src: &str, start: usize) -> Option<usize> {
    if start != 0 {
        return None;
    }
    let letter = src.chars().next()?;
    if !is_lower_cyrillic(letter) {
        return None;
    }
    let after_letter = start + letter.len_utf8();
    (src.as_bytes().get(after_letter) == Some(&b')')).then_some(after_letter + 1)
}

/// `LawCode` is exact equality on the whole alphabetic run (D330 rule 10):
/// `Федеральный` is a Word, never a LawCode prefix match; lowercase `фз` and
/// `ФЗЫ` stay Words too.
fn is_law_code(run: &str) -> bool {
    run == "ФЗ" || run == "ФКЗ"
}

/// Lowercase cyrillic letters of the Russian alphabet (inclusive of `ё`).
fn is_lower_cyrillic(ch: char) -> bool {
    ('а'..='я').contains(&ch) || ch == 'ё'
}

/// End of the single lowercase cyrillic letter opening a quoted subpoint
/// label (`п "а"` = Punct + EnumMarker + Punct; D330 rule 6): `src` must
/// carry `"` + letter at `start` with a closing `"` after exactly one
/// letter. The closing quote stays for the (greedy) Punct scan, so `а").`
/// ends in one three-byte Punct token.
fn quoted_enum_letter_end(src: &str, start: usize) -> Option<usize> {
    if src.as_bytes().get(start) != Some(&b'"') {
        return None;
    }
    let letter = src[start + 1..].chars().next()?;
    if !is_lower_cyrillic(letter) {
        return None;
    }
    let after_letter = start + 1 + letter.len_utf8();
    (src.as_bytes().get(after_letter) == Some(&b'"')).then_some(after_letter)
}
