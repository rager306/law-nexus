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

/// T01 static mirror of the S01 canonical abbreviation table
/// (`ABBREV_CANONICAL_LEXEMES` in `tests/npa_golden_fixtures.rs`), ordered
/// longest-first so `пп.` wins over `п.` and `ст.ст.` over `ст.`. The YAML
/// lexicon (`npa_abbrev_lexicon`, T03) becomes the source of truth later; the
/// T03 catalog pin guards this mirror against drift.
const ABBREV_LEXEMES: &[(AbbrevId, &str)] = &[
    (AbbrevId("stst"), "ст.ст."),
    (AbbrevId("podp"), "подп."),
    (AbbrevId("pril"), "прил."),
    (AbbrevId("prim"), "прим."),
    (AbbrevId("razd"), "разд."),
    (AbbrevId("abz"), "абз."),
    (AbbrevId("izm"), "изм."),
    (AbbrevId("red"), "ред."),
    (AbbrevId("utv"), "утв."),
    (AbbrevId("gl"), "гл."),
    (AbbrevId("pp"), "пп."),
    (AbbrevId("sm"), "см."),
    (AbbrevId("sr"), "ср."),
    (AbbrevId("st"), "ст."),
    (AbbrevId("g"), "г."),
    (AbbrevId("p"), "п."),
    (AbbrevId("ch"), "ч."),
];

/// Lex `src` into covering tokens (infallible, single left-to-right pass).
///
/// * empty input → no tokens;
/// * whitespace-only input → a single [`TokenKind::Space`];
/// * dates (`dd.mm.yyyy`, day 1..=31, month 1..=12) win over hier-numbers;
/// * a hier-number needs inner digits on both sides of at least one dot, so
///   `1.` is never one;
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
        let (kind, abbrev_id, end) = if ch.is_whitespace() {
            (
                TokenKind::Space,
                None,
                scan_while(src, pos, |c| c.is_whitespace()),
            )
        } else if ch.is_alphabetic() {
            match scan_abbrev(src, pos) {
                Some((end, id)) => (TokenKind::Abbrev, Some(id), end),
                None => (
                    TokenKind::Word,
                    None,
                    scan_while(src, pos, |c| c.is_alphabetic()),
                ),
            }
        } else if ch.is_ascii_digit() {
            if let Some(end) = scan_date(src, pos) {
                (TokenKind::Date, None, end)
            } else if let Some(end) = scan_hier_num(src, pos) {
                (TokenKind::HierNum, None, end)
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

/// Matches an exact lowercase canonical abbrev lexeme (dot included),
/// longest-first, only at a word boundary (no preceding alphabetic char), so
/// capitalized `Ч.` / `П.` and in-word tails fall through to Word + Punct.
fn scan_abbrev(src: &str, start: usize) -> Option<(usize, AbbrevId)> {
    let at_word_start = src[..start]
        .chars()
        .next_back()
        .is_none_or(|prev| !prev.is_alphabetic());
    if !at_word_start {
        return None;
    }
    ABBREV_LEXEMES.iter().find_map(|(id, lexeme)| {
        src[start..]
            .starts_with(lexeme)
            .then(|| (start + lexeme.len(), *id))
    })
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
