//! Reference knowledge layer (ADR-0031): XML → JSONL digest-timeline + JSON-LD
//! projection, ported 1:1 from the Python reference
//! `scripts/m217_reference_jsonld.py` (commit `81b74482+`).
//!
//! Parity oracle: the committed artifacts
//! `prd/migration/rust-evidence/m217-reference-*.json[l]` — the Rust derivation
//! must byte-match them. Any semantics change happens in the Python reference
//! first, then here.
//!
//! Non-authoritative reference projection; digest identity is not text CTV
//! resolution; no requirement/ADR/lifecycle promotion.
//!
//! The WordML scanner is hand-rolled (no new dependencies): it replicates the
//! Python `ElementTree.iterparse` semantics used by the reference — every
//! `w:p` end event (including `<w:p/>` and paragraphs inside tables), text =
//! concatenation of all descendant `w:t` character data with XML entities
//! decoded — and it scans BEFORE entity decoding, so escaped `</w:p>` inside
//! text cannot break paragraph boundaries (same as the XML parser).

use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

pub const CORPUS_DIR: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz";
pub const CATALOG: &str = "consru_export/consru_export/catalog.sqlite";
pub const TIMELINE_SCHEMA_V2: &str = "m217-reference-timeline/v2";
pub const DIGESTS_SCHEMA: &str = "m217-reference-digests/v1";
pub const NAMED_GRAPHS_SCHEMA: &str = "m217-reference-named-graphs/v1";
pub const AMEND_SCHEMA: &str = "m217-reference-amend-provenance/v1";
pub const NORM_PROFILE_ID: &str = "m217-norm/v1";

/// ed-50-scoped measurement edition (D782): the D4 references measurement is
/// derivable only from a corpus that carries edition 50, so both the write and
/// the `--check` branch share one applicability predicate.
pub const MEASUREMENT_EDITION: u32 = 50;
pub const REFS_SCHEMA: &str = "m217-reference-references/v1";
pub const PAGEINDEX_SCHEMA: &str = "m217-reference-pageindex/v1";

/// The measurement's own non-claims, appended to `NON_AUTHORITY` (Python
/// `REFS_NON_CLAIMS`). Kept verbatim: the artifact is byte-compared.
const REFS_NON_CLAIMS: [&str; 4] = [
    "Deep-link mechanics are proven by non-empty candidates; a resolved deep link needs the target act's corpus and the edition in force at the citing act's applied day (ADR-0031 D4, never the enacting-date edition alone), which is outside this measurement's scope — the zero deep_links is a derived honest zero, not a silent skip",
    "Amendment-fact sentences and own-edition markers resolve to amendment provenance (D3), never to deep links (ADR-0031 D4)",
    "Requisite resolution identifies the citing act's changing act; it does not interpret amendment semantics",
    "Reference and requisite scope is the article body text; the article heading line is structural metadata (its digest already carries the H: prefix), so a requisite appearing only on a heading line is not counted",
];

/// The D5 ladder's own non-claims, appended to `NON_AUTHORITY` (Python
/// `PAGEINDEX_NON_CLAIMS`). Kept verbatim: the artifact is byte-compared.
const PAGEINDEX_NON_CLAIMS: [&str; 4] = [
    "The ladder is a structural contents projection of one edition: a node is a recognized heading paragraph and every remaining non-empty paragraph is a level-7 paragraph-block (D783, corpus-wide — preamble and appendix paragraphs included); the ladder is not a text CTV or a semantic segmentation",
    "A node owns exactly one paragraph, so chars is that paragraph's character count and the nodes partition the non-empty paragraphs; char conservation is over all nodes, not over leaves",
    "max_depth is the deepest ladder level present (the ladder defines seven levels: section, chapter/paragraph(§), article, part, punkt, subpoint, paragraph-block), not the longest ancestor chain",
    "Numbering keeps its dotted form in the label (§ 3. vs § 3.1.) so path ids stay unique; empty paragraphs stay out of the ladder and add no chars",
];

pub const EXIT_OK: i32 = 0;
pub const EXIT_ARGV: i32 = 2;
pub const EXIT_INPUT: i32 = 3;
pub const EXIT_DRIFT: i32 = 6;

pub const SAMPLE_ARTICLE: &str = "statya-44";

/// WordML 2003 namespace the reference scanner is defined over. The Python
/// reference matches `w:p` in this namespace only; the Rust scanner is prefix
/// agnostic, so it verifies the namespace up front and refuses anything else
/// instead of silently deriving a different paragraph set.
pub const WORDML_NAMESPACE: &str = "http://schemas.microsoft.com/office/word/2003/wordml";

/// Unreadable or underivable input. ADR-0031 D6 maps this to exit 3, and the
/// port must never panic its way out of a bad input: a panic is not an exit
/// code, and the Python reference returns 3 for the same inputs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RefError {
    reason: String,
}

impl RefError {
    pub fn new(reason: impl Into<String>) -> Self {
        Self {
            reason: reason.into(),
        }
    }

    pub fn reason(&self) -> &str {
        &self.reason
    }

    pub fn exit_code(&self) -> i32 {
        EXIT_INPUT
    }
}

impl std::fmt::Display for RefError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.reason)
    }
}

impl std::error::Error for RefError {}

/// The corpus must declare the WordML 2003 namespace the contract is written
/// over; the declarations sit on the root element. Bounded to the preamble.
fn declares_wordml_namespace(bytes: &[u8]) -> bool {
    let head = &bytes[..bytes.len().min(64 * 1024)];
    head.windows(WORDML_NAMESPACE.len())
        .any(|w| w == WORDML_NAMESPACE.as_bytes())
}

const NON_AUTHORITY: [&str; 4] = [
    "Non-authoritative reference projection",
    "Does not validate M224 pins or promote requirements",
    "Does not close review findings or lifecycle state",
    "Digest identity is not text CTV resolution",
];

const PROFILE_RULES: [&str; 5] = [
    "nbsp_to_space",
    "strip_paragraph_text",
    "skip_empty_paragraphs",
    "article_digest_progressive_sha12_pipe",
    "join_parts_newline",
];

// ---------- canonical JSON (Python: ensure_ascii=False, sort_keys=True) ----------

/// Python-style JSON value with deterministic ordering (BTreeMap = sort_keys).
#[derive(Clone, Debug, PartialEq)]
pub enum J {
    Null,
    Bool(bool),
    Int(i64),
    /// Preformatted numeric literal (e.g. "522.57") to control float rendering.
    Num(String),
    Str(String),
    Arr(Vec<J>),
    Obj(Vec<(String, J)>),
}

fn jstr_escape(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

fn j_compact(v: &J, out: &mut String) {
    match v {
        J::Null => out.push_str("null"),
        J::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        J::Int(i) => out.push_str(&i.to_string()),
        J::Num(n) => out.push_str(n),
        J::Str(s) => jstr_escape(s, out),
        J::Arr(items) => {
            out.push('[');
            for (i, x) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                j_compact(x, out);
            }
            out.push(']');
        }
        J::Obj(entries) => {
            out.push('{');
            for (i, (k, x)) in entries.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                jstr_escape(k, out);
                out.push(':');
                j_compact(x, out);
            }
            out.push('}');
        }
    }
}

fn j_pretty(v: &J, ind: usize, out: &mut String) {
    match v {
        J::Arr(items) if !items.is_empty() => {
            out.push_str("[\n");
            for (i, x) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&" ".repeat(ind + 1));
                j_pretty(x, ind + 1, out);
            }
            out.push('\n');
            out.push_str(&" ".repeat(ind));
            out.push(']');
        }
        J::Obj(entries) if !entries.is_empty() => {
            out.push_str("{\n");
            for (i, (k, x)) in entries.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&" ".repeat(ind + 1));
                jstr_escape(k, out);
                out.push_str(": ");
                j_pretty(x, ind + 1, out);
            }
            out.push('\n');
            out.push_str(&" ".repeat(ind));
            out.push('}');
        }
        other => j_compact(other, out),
    }
}

fn j_pretty_str(v: &J) -> String {
    let mut s = String::new();
    j_pretty(v, 0, &mut s);
    s + "\n"
}

fn j_compact_str(v: &J) -> String {
    let mut s = String::new();
    j_compact(v, &mut s);
    s
}

fn obj(entries: Vec<(&str, J)>) -> J {
    // sort_keys=True: BTree ordering by key bytes
    let mut v: Vec<(String, J)> = entries
        .into_iter()
        .map(|(k, x)| (k.to_string(), x))
        .collect();
    v.sort_by(|a, b| a.0.cmp(&b.0));
    J::Obj(v)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    let d = h.finalize();
    let mut s = String::with_capacity(64);
    for b in d {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

fn sha12(text: &str) -> String {
    let mut h = Sha256::new();
    h.update(text.as_bytes());
    let d = h.finalize();
    let mut s = String::with_capacity(12);
    for b in &d[..6] {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

// ---------- WordML paragraph scanner (ElementTree parity) ----------

fn decode_entities(raw: &str) -> Result<String, RefError> {
    if !raw.contains('&') {
        return Ok(raw.to_string());
    }
    let mut out = String::with_capacity(raw.len());
    let bytes = raw.as_bytes();
    let mut i = 0usize;
    while i < bytes.len() {
        if bytes[i] == b'&' {
            // ElementTree refuses an undeclared entity or a bare `&`; a byte
            // scanner would silently keep `&nbsp;` as literal text, so the
            // Rust port must fail closed on the same input.
            let semi = raw[i + 1..]
                .find(';')
                .map(|k| i + 1 + k)
                .filter(|semi| semi - i <= 12)
                .ok_or_else(|| {
                    RefError::new(format!(
                        "invalid XML: '&' without a terminating entity reference near {:?}",
                        &raw[i..raw.len().min(i + 16)]
                    ))
                })?;
            let ent = &raw[i + 1..semi];
            let decoded = match ent {
                "amp" => Some('&'),
                "lt" => Some('<'),
                "gt" => Some('>'),
                "quot" => Some('"'),
                "apos" => Some('\''),
                _ => {
                    if let Some(hex) = ent.strip_prefix("#x").or(ent.strip_prefix("#X")) {
                        u32::from_str_radix(hex, 16).ok().and_then(char::from_u32)
                    } else if let Some(dec) = ent.strip_prefix('#') {
                        dec.parse::<u32>().ok().and_then(char::from_u32)
                    } else {
                        None
                    }
                }
            };
            let c = decoded.ok_or_else(|| {
                RefError::new(format!("invalid XML: undeclared entity '&{ent};'"))
            })?;
            out.push(c);
            i = semi + 1;
            continue;
        }
        let ch = raw[i..].chars().next().unwrap_or('\u{fffd}');
        out.push(ch);
        i += ch.len_utf8();
    }
    Ok(out)
}

fn find_sub(hay: &[u8], from: usize, needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || hay.len() < needle.len() {
        return None;
    }
    (from..=hay.len() - needle.len()).find(|&k| &hay[k..k + needle.len()] == needle)
}

/// Text of one `w:p` inner byte range: concat of all `w:t` data, entities decoded.
fn paragraph_text(inner: &[u8]) -> Result<String, RefError> {
    let mut out = String::new();
    let mut i = 0usize;
    while i < inner.len() {
        if inner[i] == b'<' && inner[i..].starts_with(b"<w:t") {
            let after = inner.get(i + 4).copied();
            let (gt, selfc) = match after {
                Some(b'>') => (i + 4, false),
                Some(b'/') => {
                    let g = i
                        + 4
                        + inner[i + 4..]
                            .iter()
                            .position(|&b| b == b'>')
                            .ok_or_else(|| RefError::new("<w:t/> without '>'"))?;
                    (g, true)
                }
                Some(b' ') => {
                    let g = i
                        + 4
                        + inner[i + 4..]
                            .iter()
                            .position(|&b| b == b'>')
                            .ok_or_else(|| RefError::new("<w:t ...> without '>'"))?;
                    (g, inner[g - 1] == b'/')
                }
                _ => {
                    i += 4;
                    continue;
                }
            };
            if selfc {
                i = gt + 1;
                continue;
            }
            let close = find_sub(inner, gt + 1, b"</w:t>")
                .ok_or_else(|| RefError::new("<w:t> without closing </w:t>"))?;
            out.push_str(&decode_entities(
                std::str::from_utf8(&inner[gt + 1..close]).unwrap_or(""),
            )?);
            i = close + 6;
        } else {
            // Advance exactly one UTF-8 character: `inner[i]` is a leading
            // byte (ASCII or multi-byte start), so skip it plus its
            // continuation bytes. (A `position(|b| b & 0xC0 != 0x80)` search
            // from `i` matches the leading byte itself and yields 0 — an
            // infinite loop on every paragraph containing a non-`w:t` tag.)
            let mut j = i + 1;
            while j < inner.len() && inner[j] & 0xC0 == 0x80 {
                j += 1;
            }
            i = j;
        }
    }
    Ok(out.replace('\u{a0}', " ").trim().to_string())
}

/// Scan WordML bytes: one entry per `w:p` element (document order, including
/// self-closing and paragraphs inside tables), Python-parity text extraction.
pub fn scan_wordml_paragraphs(bytes: &[u8]) -> Result<Vec<String>, RefError> {
    let mut paras = Vec::new();
    let mut i = 0usize;
    while i < bytes.len() {
        if bytes[i] == b'<' && bytes[i..].starts_with(b"<w:p") {
            let after = bytes.get(i + 4).copied();
            match after {
                Some(b'>') | Some(b' ') => {
                    let gt = i
                        + 4
                        + bytes[i + 4..]
                            .iter()
                            .position(|&b| b == b'>')
                            .ok_or_else(|| RefError::new("<w:p ...> without '>'"))?;
                    if bytes[gt - 1] == b'/' {
                        paras.push(String::new()); // <w:p ... />
                        i = gt + 1;
                        continue;
                    }
                    let close = find_sub(bytes, gt + 1, b"</w:p>")
                        .ok_or_else(|| RefError::new("<w:p> without closing </w:p>"))?;
                    let inner = &bytes[gt + 1..close];
                    paras.push(paragraph_text(inner)?);
                    i = close + 6;
                }
                Some(b'/') => {
                    paras.push(String::new()); // <w:p/>
                    let gt = i
                        + 4
                        + bytes[i + 4..]
                            .iter()
                            .position(|&b| b == b'>')
                            .ok_or_else(|| RefError::new("<w:p/> without '>'"))?;
                    i = gt + 1;
                }
                _ => {
                    // <w:pict / <w:pgSz / <w:proofErr ...: not a paragraph
                    i += 4;
                }
            }
        } else {
            i += 1;
        }
    }
    Ok(paras)
}

// ---------- hand parsers (regex-free, Python-regex parity) ----------

/// Python: ^Статья (\d+(?:\.\d+)?)\.?\s*(.*)
fn article_heading(text: &str) -> Option<(String, String)> {
    let rest = text.strip_prefix("Статья ")?;
    let b = rest.as_bytes();
    let mut k = 0;
    while k < b.len() && b[k].is_ascii_digit() {
        k += 1;
    }
    if k == 0 {
        return None;
    }
    let mut no = rest[..k].to_string();
    let mut j = k;
    if b.get(j) == Some(&b'.') && b.get(j + 1).is_some_and(|c| c.is_ascii_digit()) {
        j += 1;
        while j < b.len() && b[j].is_ascii_digit() {
            j += 1;
        }
        no = rest[..j].to_string();
    }
    let mut j2 = j;
    if b.get(j2) == Some(&b'.') {
        j2 += 1;
    }
    let tail = &rest[j2..];
    let heading_start = tail.len() - tail.trim_start().len();
    Some((no, tail[heading_start..].trim_end().to_string()))
}

/// Python: ^(\d+)\.\s
fn part_marker(text: &str) -> bool {
    let b = text.as_bytes();
    let mut k = 0;
    while k < b.len() && b[k].is_ascii_digit() {
        k += 1;
    }
    k > 0 && b.get(k) == Some(&b'.') && b.get(k + 1).is_some_and(|c| c.is_ascii_whitespace())
}

/// Python: \(в ред\.[^)]*?от\s+date\s+N\s*token
fn amend_marker_of(text: &str) -> Option<(String, String)> {
    // Python: / \(в ред\.[^)]*?от\s+(\d{2}\.\d{2}\.\d{4})\s+N\s*([^\s)]+) /
    // "от" is 4 bytes in UTF-8, not 2 — the earlier 2-byte slice compare could
    // never match, so the scan always ran into the closing ')' and returned
    // `None` for every marker in the corpus.
    const STEM: &str = "(в ред.";
    const OT: &str = "от";
    let after = &text[text.find(STEM)? + STEM.len()..];
    let mut tail: Option<&str> = None;
    for (i, c) in after.char_indices() {
        if c == ')' {
            return None;
        }
        if let Some(rest) = after[i..].strip_prefix(OT)
            && rest.starts_with(char::is_whitespace)
        {
            tail = Some(rest);
            break;
        }
    }
    let rest = tail?.trim_start();
    let date = rest.get(..10)?;
    let shape_ok = date.as_bytes().iter().enumerate().all(|(k, c)| {
        if k == 2 || k == 5 {
            *c == b'.'
        } else {
            c.is_ascii_digit()
        }
    });
    if !shape_ok {
        return None;
    }
    let rest = rest[10..].trim_start().strip_prefix('N')?.trim_start();
    let tok: String = rest
        .chars()
        .take_while(|c| !c.is_whitespace() && *c != ')')
        .collect();
    if tok.is_empty() {
        return None;
    }
    let iso = format!("{}-{}-{}", &date[6..10], &date[3..5], &date[0..2]);
    let num = tok.trim_end_matches([')', '.', ',']).to_string();
    Some((iso, num))
}

/// Python: стать(?:ё|е|ей|и|ю|я)?\s+(\d{1,3}) case-insensitive, first match.
/// Python: `re.finditer(r"стать(?:ё|е|ей|и|ю|я)?\s+(\d{1,3})", sent, re.I)` —
/// every match, ending alternatives tried in regex order (with backtracking),
/// at most three digits. Returning only the first match of the sentence
/// halved the qualified-edge count against the reference.
pub fn refs_in_sentence(sentence: &str) -> Vec<String> {
    const STEM: &str = "стать";
    const ENDINGS: [&str; 7] = ["ё", "е", "ей", "и", "ю", "я", ""];
    let low = sentence.to_lowercase();
    let mut out = Vec::new();
    let mut from = 0usize;
    while let Some(rel) = low[from..].find(STEM) {
        let stem_end = from + rel + STEM.len();
        let mut next = stem_end;
        let after = &low[stem_end..];
        for cand in ENDINGS {
            // The ending must actually be present: consuming `cand.len()` bytes
            // blindly let "ей" (4 bytes) eat the unrelated "ях" of "статьях",
            // inventing a reference the reference implementation rejects.
            let Some(rest) = after.strip_prefix(cand) else {
                continue;
            };
            let ws: usize = rest
                .chars()
                .take_while(|c| c.is_whitespace())
                .map(char::len_utf8)
                .sum();
            if ws == 0 {
                continue;
            }
            let digits: String = rest[ws..]
                .chars()
                .take_while(|c| c.is_ascii_digit())
                .take(3)
                .collect();
            if !digits.is_empty() {
                next = stem_end + cand.len() + ws + digits.len();
                out.push(digits);
                break;
            }
        }
        from = next;
    }
    out
}

/// Python: `re.search(r"Федерального закона|закона|Кодекса|ТК РФ|ГК РФ|законе", sent, re.I)`.
fn contains_external_marker_ci(sent: &str) -> bool {
    let low = sent.to_lowercase();
    [
        "федерального закона",
        "закона",
        "кодекса",
        "тк рф",
        "гк рф",
        "законе",
    ]
    .iter()
    .any(|n| low.contains(n))
}

/// Python: re.split(r"(?<=[.;])\s+", chunk)
pub fn split_sentences(chunk: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut seg = String::new();
    let mut prev_is_delim = false;
    for c in chunk.chars() {
        if prev_is_delim && c.is_whitespace() {
            out.push(std::mem::take(&mut seg));
            continue;
        }
        prev_is_delim = c == '.' || c == ';';
        seg.push(c);
    }
    if !seg.is_empty() {
        out.push(seg);
    }
    out
}

fn article_sort_key(a: &str) -> Vec<u64> {
    a.split('-')
        .nth(1)
        .unwrap_or("0")
        .split('.')
        .map(|p| p.parse::<u64>().unwrap_or(0))
        .collect()
}

// ---------- scanned edition ----------

#[derive(Clone, Debug)]
pub struct ArticleSpan {
    pub p_start: usize,
    pub p_end: usize,
}

#[derive(Clone, Debug)]
pub struct EditionDigest {
    pub source_sha256: String,
    pub edition_no: u32,
    pub raw_day: String,
    pub applied_day: String,
    pub clamped: bool,
    pub article_count: usize,
    pub raw_headings: usize,
    pub parse_loss: usize,
    pub break_from_previous: bool,
    pub removed_from_previous: usize,
    pub part_count: usize,
    pub edge_count: usize,
}

pub struct ScannedEdition {
    pub edition_no: u32,
    pub digests: BTreeMap<String, String>,
    pub spans: BTreeMap<String, ArticleSpan>,
    pub edges: Vec<(String, String)>,
    pub raw_headings: usize,
    pub part_count: usize,
    pub amend: Vec<(String, String, String)>, // (article, iso-date, number)
    pub source_sha256: String,
}

pub fn scan_edition(path: &Path) -> Result<ScannedEdition, RefError> {
    let file_name = path.file_name().and_then(|n| n.to_str()).ok_or_else(|| {
        RefError::new(format!("unreadable edition file name: {}", path.display()))
    })?;
    let edition_no = edition_no_of(file_name).ok_or_else(|| {
        RefError::new(format!(
            "edition file name has no numeric edition number: {file_name}"
        ))
    })?;
    let bytes = std::fs::read(path)
        .map_err(|e| RefError::new(format!("unreadable edition file {}: {e}", path.display())))?;
    if !declares_wordml_namespace(&bytes) {
        return Err(RefError::new(format!(
            "edition file {} does not declare the WordML 2003 namespace {WORDML_NAMESPACE}",
            path.display()
        )));
    }
    let source_sha256 = sha256_hex(&bytes);
    let paras = scan_wordml_paragraphs(&bytes)?;
    let mut digests: BTreeMap<String, String> = BTreeMap::new();
    let mut spans: BTreeMap<String, ArticleSpan> = BTreeMap::new();
    let mut full_text: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut amend: Vec<(String, String, String)> = Vec::new();
    let mut raw_headings = 0usize;
    let mut cur: Option<String> = None;
    for (idx, text) in paras.iter().enumerate() {
        if let Some((iso, num)) = amend_marker_of(text) {
            let art = cur.clone().unwrap_or_else(|| "act".into());
            if !amend
                .iter()
                .any(|(a, d, n)| a == &art && d == &iso && n == &num)
            {
                amend.push((art, iso, num));
            }
        }
        if let Some((no, body)) = article_heading(text) {
            raw_headings += 1;
            cur = Some(format!("statya-{no}"));
            let aid = cur.clone().unwrap_or_default();
            digests.insert(aid.clone(), sha12(&format!("H:{body}")));
            spans.insert(
                aid.clone(),
                ArticleSpan {
                    p_start: idx,
                    p_end: idx,
                },
            );
            if !body.is_empty() {
                full_text.entry(aid).or_default().push(body);
            }
            continue;
        }
        if let (Some(aid), false) = (cur.clone(), text.is_empty()) {
            // every non-empty paragraph after the heading is a chunk
            full_text.entry(aid.clone()).or_default().push(text.clone());
            let d = digests.get(&aid).cloned().unwrap_or_default();
            digests.insert(aid.clone(), sha12(&format!("{d}|{text}")));
            let sp = spans.get(&aid).cloned().unwrap_or(ArticleSpan {
                p_start: idx,
                p_end: idx,
            });
            spans.insert(
                aid.clone(),
                ArticleSpan {
                    p_start: sp.p_start,
                    p_end: idx,
                },
            );
        }
    }
    // qualified internal edges: sentence-scoped, external markers excluded
    let mut edges: BTreeMap<String, std::collections::BTreeSet<String>> = BTreeMap::new();
    for (aid, chunks) in &full_text {
        for chunk in chunks {
            for sent in split_sentences(chunk) {
                if contains_external_marker_ci(&sent)
                    && !sent.contains("настоящего")
                    && !sent.contains("прежнему")
                {
                    continue;
                }
                for num in refs_in_sentence(&sent) {
                    let ref_id = format!("statya-{num}");
                    if ref_id != *aid && digests.contains_key(&ref_id) {
                        edges.entry(aid.clone()).or_default().insert(ref_id);
                    }
                }
            }
        }
    }
    let part_count = full_text.values().map(Vec::len).sum();
    let edge_list: Vec<(String, String)> = edges
        .iter()
        .flat_map(|(a, set)| set.iter().map(move |b| (a.clone(), b.clone())))
        .collect();
    Ok(ScannedEdition {
        edition_no,
        digests,
        spans,
        edges: edge_list,
        raw_headings,
        part_count,
        amend,
        source_sha256,
    })
}

// ---------- catalog ----------

/// Act directory (last path segment) whose catalog rows this derivation may
/// read. The Python reference used to hardcode `law_2013-04-05_44-fz`; the
/// reference layer must be able to serve any act directory, so the filter is
/// derived from the corpus dir the caller passed.
pub fn act_dir_name(corpus_dir: &Path) -> Result<String, RefError> {
    corpus_dir
        .file_name()
        .and_then(|n| n.to_str())
        .map(str::to_string)
        .ok_or_else(|| RefError::new(format!("corpus dir has no name: {}", corpus_dir.display())))
}

fn open_catalog(catalog: &Path) -> Result<rusqlite::Connection, RefError> {
    if !catalog.is_file() {
        return Err(RefError::new(format!(
            "unreadable catalog: {}",
            catalog.display()
        )));
    }
    rusqlite::Connection::open_with_flags(catalog, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
        .map_err(|e| RefError::new(format!("unreadable catalog {}: {e}", catalog.display())))
}

fn cat_days_map(catalog: &Path, act_dir: &str) -> Result<BTreeMap<String, String>, RefError> {
    let con = open_catalog(catalog)?;
    let mut stmt = con
        .prepare(
            "select relative_path, document_date from editions \
             where relative_path like ?",
        )
        .map_err(|e| RefError::new(format!("catalog query failed: {e}")))?;
    let pattern = format!("%/npa/{act_dir}/%");
    let mut map = BTreeMap::new();
    let mut rows = stmt
        .query([pattern])
        .map_err(|e| RefError::new(format!("catalog query failed: {e}")))?;
    while let Some(row) = rows
        .next()
        .map_err(|e| RefError::new(format!("catalog row failed: {e}")))?
    {
        let rel: String = row.get(0).unwrap_or_default();
        let day: String = row.get(1).unwrap_or_default();
        map.insert(rel, day);
    }
    Ok(map)
}

fn corpus_editions_count(catalog: &Path) -> Result<i64, RefError> {
    let con = open_catalog(catalog)?;
    con.query_row("select count(*) from editions", [], |r| r.get::<_, i64>(0))
        .map_err(|e| RefError::new(format!("catalog count failed: {e}")))
}

/// Prefix prepended to catalog relative paths to form the reported
/// `resolved_path`: the corpus root relative to the repository root
/// (`consru_export/consru_export` for the shipped corpus). Taken from the
/// corpus dir actually in use, so the reference layer is not bound to one act.
fn corpus_prefix(corpus_dir: &Path) -> String {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..");
    let canon_dir = std::fs::canonicalize(corpus_dir).unwrap_or_else(|_| corpus_dir.to_path_buf());
    let canon_root = std::fs::canonicalize(&root).unwrap_or(root);
    let rel = canon_dir
        .strip_prefix(&canon_root)
        .map(Path::to_path_buf)
        .unwrap_or(canon_dir);
    let s = rel
        .to_string_lossy()
        .replace(std::path::MAIN_SEPARATOR, "/");
    match s.find("/exports/") {
        Some(k) => s[..k].to_string(),
        None => String::new(),
    }
}

fn resolve_amend(
    con: &rusqlite::Connection,
    iso_date: &str,
    number: &str,
    prefix: &str,
) -> Result<(String, Option<String>), RefError> {
    let pattern = format!("%{number}%");
    let mut stmt = con
        .prepare("select relative_path, document_date from editions where number like ? limit 60")
        .map_err(|e| RefError::new(format!("amend query failed: {e}")))?;
    let rows: Vec<(String, String)> = stmt
        .query_map([pattern], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
        })
        .map_err(|e| RefError::new(format!("amend query failed: {e}")))?
        .filter_map(Result::ok)
        .collect();
    let exact: Vec<&(String, String)> = rows.iter().filter(|(_, d)| d == iso_date).collect();
    // An empty prefix (corpus outside the repository root) must not leave a
    // leading slash: the Python reference reports the bare catalog path.
    let joined = |rel: &str| {
        if prefix.is_empty() {
            rel.to_string()
        } else {
            format!("{prefix}/{rel}")
        }
    };
    if let Some((rel, _)) = exact.first() {
        return Ok(("resolved_enacting_date".into(), Some(joined(rel))));
    }
    if let Some((rel, _)) = rows.first() {
        return Ok(("resolved_number_only".into(), Some(joined(rel))));
    }
    Ok(("unresolved".into(), None))
}

// ---------- derivation ----------

pub struct DeriveOptions {
    pub limit_editions: Option<u32>,
    pub corpus_dir: PathBuf,
    pub catalog: PathBuf,
}

pub struct Reference {
    pub timeline: String,
    pub digests: String,
    pub named_graphs: String,
    pub amend: String,
}

fn effective_day(name: &str, cat_days: &BTreeMap<String, String>, act_dir: &str) -> String {
    if let Some(day) = filename_day(name) {
        return day;
    }
    let rel = format!("exports/npa/{act_dir}/{name}");
    cat_days
        .get(&rel)
        .cloned()
        .unwrap_or_else(|| "9999-12-31".into())
}

/// `from-YYYY-MM-DD`, else `rev-YYYY-MM-DD`, from a corpus filename — mirrors
/// the Python reference `RE_FROM`/`RE_REV` (strict ISO shape, `from-unknown`
/// and `rev-initial` do not match).
pub fn filename_day(name: &str) -> Option<String> {
    extract_after(name, "from-").or_else(|| extract_after(name, "rev-"))
}

fn is_date10(s: &str) -> bool {
    let b = s.as_bytes();
    b.len() >= 10
        && b[..10].iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == b'-'
            } else {
                c.is_ascii_digit()
            }
        })
}

fn extract_after(name: &str, marker: &str) -> Option<String> {
    let i = name.find(marker)? + marker.len();
    let s = name.get(i..)?;
    if is_date10(s) {
        Some(s[..10].to_string())
    } else {
        None
    }
}

fn edition_no_of(name: &str) -> Option<u32> {
    let rest = name.strip_prefix("edition-")?;
    let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
    digits.parse().ok()
}

pub fn derive(opts: &DeriveOptions) -> Reference {
    try_derive(opts).unwrap_or_else(|e| panic!("reference-layer derivation failed: {e}"))
}

/// Fallible derivation. Every unreadable or underivable input returns
/// `RefError` (ADR-0031 D6 exit 3) instead of panicking, which is what the
/// Python reference does and what the CLI contract requires.
pub fn try_derive(opts: &DeriveOptions) -> Result<Reference, RefError> {
    if !opts.corpus_dir.is_dir() {
        return Err(RefError::new(format!(
            "unreadable corpus dir: {}",
            opts.corpus_dir.display()
        )));
    }
    let act_dir = act_dir_name(&opts.corpus_dir)?;
    let mut files: Vec<(u32, PathBuf)> = Vec::new();
    let read = std::fs::read_dir(&opts.corpus_dir)
        .map_err(|e| RefError::new(format!("unreadable corpus dir: {e}")))?;
    for entry in read {
        let path = entry
            .map_err(|e| RefError::new(format!("unreadable corpus entry: {e}")))?
            .path();
        let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
            continue;
        };
        if !(name.starts_with("edition-") && name.ends_with(".xml")) {
            continue;
        }
        let no = edition_no_of(name).ok_or_else(|| {
            RefError::new(format!(
                "edition file name has no numeric edition number: {name}"
            ))
        })?;
        files.push((no, path));
    }
    if files.is_empty() {
        return Err(RefError::new(format!(
            "no edition files under corpus dir {}",
            opts.corpus_dir.display()
        )));
    }
    files.sort_by_key(|(no, _)| *no);
    for pair in files.windows(2) {
        if pair[0].0 == pair[1].0 {
            return Err(RefError::new(format!(
                "duplicate edition number {} in corpus dir {}",
                pair[0].0,
                opts.corpus_dir.display()
            )));
        }
    }
    if let Some(max) = opts.limit_editions {
        files.retain(|(no, _)| *no <= max);
    }

    let cat_days = cat_days_map(&opts.catalog, &act_dir)?;
    let con = open_catalog(&opts.catalog)?;
    let amend_prefix = corpus_prefix(&opts.corpus_dir);
    let mut editions: Vec<EditionDigest> = Vec::new();
    let mut digests_by_ed: BTreeMap<u32, BTreeMap<String, String>> = BTreeMap::new();
    let mut spans_by_ed: BTreeMap<u32, BTreeMap<String, ArticleSpan>> = BTreeMap::new();
    let mut shas_by_ed: BTreeMap<u32, String> = BTreeMap::new();
    let mut amend_rows: Vec<J> = Vec::new();
    let mut amend_cache: BTreeMap<(String, String), (String, Option<String>)> = BTreeMap::new();
    let mut prev_day: Option<String> = None;
    let mut prev_digests: Option<BTreeMap<String, String>> = None;

    for (ed_no, path) in &files {
        let ed_no = *ed_no;
        let name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or_default()
            .to_string();
        let raw_day = effective_day(&name, &cat_days, &act_dir);
        let scanned = scan_edition(path)?;
        let applied_day;
        let clamped;
        if let Some(prev) = &prev_day
            && raw_day.as_str() < prev.as_str()
        {
            applied_day = prev.clone();
            clamped = true;
        } else {
            applied_day = raw_day.clone();
            clamped = false;
        }
        prev_day = Some(applied_day.clone());
        let (break_from_previous, removed_count) = match &prev_digests {
            Some(prev) => {
                let removed = prev
                    .keys()
                    .filter(|k| !scanned.digests.contains_key(*k))
                    .count();
                (removed > 0, removed)
            }
            None => (false, 0),
        };
        editions.push(EditionDigest {
            source_sha256: scanned.source_sha256.clone(),
            edition_no: ed_no,
            raw_day: raw_day.clone(),
            applied_day: applied_day.clone(),
            clamped,
            article_count: scanned.digests.len(),
            raw_headings: scanned.raw_headings,
            parse_loss: scanned.raw_headings.saturating_sub(scanned.digests.len()),
            break_from_previous,
            removed_from_previous: removed_count,
            part_count: scanned.part_count,
            edge_count: scanned.edges.len(),
        });
        digests_by_ed.insert(ed_no, scanned.digests.clone());
        spans_by_ed.insert(ed_no, scanned.spans.clone());
        shas_by_ed.insert(ed_no, scanned.source_sha256.clone());
        for (art, iso, num) in &scanned.amend {
            let key = (iso.clone(), num.clone());
            let (tier, rel) = match amend_cache.get(&key) {
                Some(v) => v.clone(),
                None => {
                    let v = resolve_amend(&con, iso, num, &amend_prefix)?;
                    amend_cache.insert(key.clone(), v.clone());
                    v
                }
            };
            let mut entries: Vec<(&str, J)> = vec![
                ("edition_no", J::Int(ed_no as i64)),
                ("article", J::Str(art.clone())),
                ("date", J::Str(iso.clone())),
                ("number", J::Str(num.clone())),
                ("tier", J::Str(tier)),
            ];
            if let Some(rel) = rel {
                entries.push(("resolved_path", J::Str(rel)));
            }
            // `obj` sorts keys like the Python reference's `sort_keys=True`;
            // a raw `J::Obj` emitted insertion order and drifted every
            // corpus-wide marker record.
            amend_rows.push(obj(entries));
        }
        prev_digests = Some(scanned.digests);
    }

    // CTV events
    let mut ctv: Vec<(String, u32, &'static str)> = Vec::new();
    let mut prev: Option<&BTreeMap<String, String>> = None;
    for ed_no in digests_by_ed.keys().copied().collect::<Vec<_>>() {
        let cur = &digests_by_ed[&ed_no];
        if let Some(prev_d) = prev {
            let mut union: Vec<String> = prev_d.keys().chain(cur.keys()).cloned().collect();
            union.sort_by_key(|aid| article_sort_key(aid));
            union.dedup();
            for aid in &union {
                match (prev_d.get(aid), cur.get(aid)) {
                    (None, Some(_)) => ctv.push((aid.clone(), ed_no, "created")),
                    (Some(_), None) => ctv.push((aid.clone(), ed_no, "removed")),
                    (Some(a), Some(b)) if a != b => ctv.push((aid.clone(), ed_no, "amended")),
                    _ => {}
                }
            }
        }
        prev = Some(cur);
    }

    // Named graphs sample
    let mut graphs: Vec<J> = Vec::new();
    for e in &editions {
        let digests = &digests_by_ed[&e.edition_no];
        let Some(digest) = digests.get(SAMPLE_ARTICLE) else {
            continue;
        };
        graphs.push(obj(vec![
            (
                "@id",
                J::Str(format!(
                    "eli:expression/44-fz/ed-{:04}#{SAMPLE_ARTICLE}",
                    e.edition_no
                )),
            ),
            ("digest", J::Str(digest.clone())),
            ("applied_day", J::Str(e.applied_day.clone())),
        ]));
    }
    let named = vec![
        obj(vec![
            ("@id", J::Str("eli:work/44-fz".into())),
            ("sample_article", J::Str(SAMPLE_ARTICLE.into())),
        ]),
        obj(vec![
            ("@id", J::Str(format!("cc:44-fz:{SAMPLE_ARTICLE}"))),
            ("graphs", J::Arr(graphs)),
        ]),
    ];

    // G-layer volume (measured on the densest edition)
    let measured = editions
        .iter()
        .max_by_key(|e| (e.part_count, e.edition_no))
        .cloned()
        .ok_or_else(|| RefError::new("no editions derived"))?;
    if measured.part_count == 0 {
        // Python divides by `part_count` here and raises ZeroDivisionError; the
        // port must not emit `NaN` as a JSON number (invalid JSON that no one
        // validates), so the same input fails closed with exit 3.
        return Err(RefError::new(
            "no article parts under corpus dir: G-layer volume is not measurable",
        ));
    }
    let measured_path = files
        .iter()
        .find(|(no, _)| *no == measured.edition_no)
        .map(|(_, p)| p.clone())
        .ok_or_else(|| RefError::new("measured edition file not found"))?;
    let day = measured.applied_day.clone();
    let blob = edition_layer_document(&measured_path, measured.edition_no, &day)?;
    let per_part = blob.len() as f64 / measured.part_count as f64;
    let act_parts: usize = editions.iter().map(|e| e.part_count).sum();
    let corpus_editions = corpus_editions_count(&opts.catalog)?;
    let act_projection = py_round(act_parts as f64 * per_part + editions.len() as f64 * 400.0);
    let corpus_projection =
        py_round(act_projection as f64 / editions.len() as f64 * corpus_editions as f64);

    let digests_body = render_digests(&editions, &digests_by_ed, &spans_by_ed, &shas_by_ed);
    let g_volume = obj(vec![
        ("methodology", J::Str("bytes measured on the densest edition, scaled linearly by part counts; corpus projection is coarse (one-act average over all catalog editions)".into())),
        ("measured_edition_no", J::Int(measured.edition_no as i64)),
        ("measured_jsonld_bytes", J::Int(blob.len() as i64)),
        ("measured_parts", J::Int(measured.part_count as i64)),
        ("bytes_per_part", J::Num(py_round2(per_part))),
        ("act_text_inline_projection_bytes", J::Int(act_projection)),
        ("corpus_editions_in_catalog", J::Int(corpus_editions)),
        ("corpus_text_inline_projection_bytes", J::Int(corpus_projection)),
        ("digest_timeline_bytes_alternative", J::Int(digests_body.len() as i64)),
    ]);

    let mut timeline_editions: Vec<J> = Vec::new();
    for e in &editions {
        timeline_editions.push(obj(vec![
            ("edition_no", J::Int(e.edition_no as i64)),
            ("source_sha256", J::Str(e.source_sha256.clone())),
            ("raw_day", J::Str(e.raw_day.clone())),
            ("applied_day", J::Str(e.applied_day.clone())),
            ("clamped", J::Bool(e.clamped)),
            ("article_count", J::Int(e.article_count as i64)),
            ("raw_headings", J::Int(e.raw_headings as i64)),
            ("parse_loss", J::Int(e.parse_loss as i64)),
            ("break_from_previous", J::Bool(e.break_from_previous)),
            (
                "removed_from_previous",
                J::Int(e.removed_from_previous as i64),
            ),
            ("part_count", J::Int(e.part_count as i64)),
            ("edge_count", J::Int(e.edge_count as i64)),
        ]));
    }
    let mut ctv_values: Vec<J> = Vec::new();
    for (aid, no, op) in &ctv {
        ctv_values.push(obj(vec![
            ("article", J::Str(aid.clone())),
            ("edition_no", J::Int(*no as i64)),
            ("op", J::Str(op.to_string())),
        ]));
    }
    let mut nonmono: Vec<J> = Vec::new();
    for e in editions.iter().filter(|e| e.clamped) {
        nonmono.push(obj(vec![
            ("from_edition_no", J::Int((e.edition_no - 1) as i64)),
            ("raw_day", J::Str(e.raw_day.clone())),
            ("applied_day", J::Str(e.applied_day.clone())),
        ]));
    }
    // Declaration order, not sorted: the Python reference publishes
    // `NORMALIZATION_PROFILE["rules"]` as written.
    let profile_rules: Vec<J> = PROFILE_RULES
        .iter()
        .map(|s| J::Str(s.to_string()))
        .collect();
    let timeline = j_pretty_str(&obj(vec![
        ("schema_version", J::Str(TIMELINE_SCHEMA_V2.into())),
        ("authoritative", J::Bool(false)),
        (
            "normalization_profile",
            obj(vec![
                ("id", J::Str(NORM_PROFILE_ID.into())),
                ("rules", J::Arr(profile_rules)),
            ]),
        ),
        (
            "non_claims",
            J::Arr(
                NON_AUTHORITY
                    .iter()
                    .map(|s| J::Str(s.to_string()))
                    .chain(std::iter::once(J::Str("Article-count variance across editions reflects documented law history (476-FZ purge band from edition 81), not parsing defect".into())))
                    .collect(),
            ),
        ),
        (
            "counts",
            obj(vec![
                ("editions", J::Int(editions.len() as i64)),
                ("ctv_events", J::Int(ctv.len() as i64)),
                ("non_monotonic", J::Int(nonmono.len() as i64)),
            ]),
        ),
        ("g_layer_volume", g_volume),
        ("editions", J::Arr(timeline_editions)),
        ("ctv_events", J::Arr(ctv_values)),
        ("non_monotonic", J::Arr(nonmono)),
    ]));

    let named_graphs = j_pretty_str(&obj(vec![
        ("schema_version", J::Str(NAMED_GRAPHS_SCHEMA.into())),
        ("authoritative", J::Bool(false)),
        (
            "non_claims",
            J::Arr(
                NON_AUTHORITY
                    .iter()
                    .map(|s| J::Str(s.to_string()))
                    .collect(),
            ),
        ),
        ("graphs", J::Arr(named)),
    ]));

    // amend artifact
    let mut tier_counts: BTreeMap<String, usize> = BTreeMap::new();
    // Python appends markers in (edition, paragraph) derivation order and never
    // re-sorts them; the previous `cmp_obj_rows` comparator ordered
    // `edition_no` as a *string* ("10" < "2"), which scrambled the whole
    // corpus-wide marker list.
    let amend_sorted = amend_rows.clone();
    for r in &amend_sorted {
        if let J::Obj(rows) = r {
            for (k, v) in rows {
                if k == "tier"
                    && let J::Str(t) = v
                {
                    *tier_counts.entry(t.clone()).or_default() += 1;
                }
            }
        }
    }
    let laws: std::collections::BTreeSet<(String, String)> = amend_sorted
        .iter()
        .filter_map(|r| {
            if let J::Obj(rows) = r {
                let is_act = rows
                    .iter()
                    .any(|(k, v)| k == "article" && v == &J::Str("act".into()));
                if is_act {
                    return None;
                }
                let date = rows
                    .iter()
                    .find_map(|(k, v)| (k == "date").then(|| v.clone()));
                let num = rows
                    .iter()
                    .find_map(|(k, v)| (k == "number").then(|| v.clone()));
                match (date, num) {
                    (Some(J::Str(d)), Some(J::Str(n))) => Some((d, n)),
                    _ => None,
                }
            } else {
                None
            }
        })
        .collect();
    let eds_with: std::collections::BTreeSet<u32> = amend_sorted
        .iter()
        .filter_map(|r| {
            if let J::Obj(rows) = r {
                rows.iter().find_map(|(k, v)| {
                    if k == "edition_no" {
                        Some(match v {
                            J::Int(i) => *i as u32,
                            _ => 0,
                        })
                    } else {
                        None
                    }
                })
            } else {
                None
            }
        })
        .collect();
    let mut tiers_j: Vec<(String, J)> = tier_counts
        .into_iter()
        .map(|(k, v)| (k, J::Int(v as i64)))
        .collect();
    tiers_j.sort_by(|a, b| a.0.cmp(&b.0));
    let amend_artifact = j_pretty_str(&obj(vec![
        ("schema_version", J::Str(AMEND_SCHEMA.into())),
        ("authoritative", J::Bool(false)),
        (
            "non_claims",
            J::Arr(
                NON_AUTHORITY
                    .iter()
                    .map(|s| J::Str(s.to_string()))
                    .chain(std::iter::once(J::Str("Amendment provenance identifies the changing act; it does not interpret amendment semantics (M208 territory)".into())))
                    .collect(),
            ),
        ),
        (
            "counts",
            obj(vec![
                ("editions_with_markers", J::Int(eds_with.len() as i64)),
                ("markers", J::Int(amend_sorted.len() as i64)),
                ("unique_amending_laws", J::Int(laws.len() as i64)),
            ]),
        ),
        ("resolution_tiers", J::Obj(tiers_j)),
        ("markers", J::Arr(amend_sorted)),
    ]));

    Ok(Reference {
        timeline,
        digests: digests_body,
        named_graphs,
        amend: amend_artifact,
    })
}

/// Python round(x) half-to-even on the decimal digit (used for integer results).
fn py_round(x: f64) -> i64 {
    format!("{x:.0}").parse().unwrap_or(0)
}

/// Python `round(x, 2)` rendered the way `json.dumps` renders it: the shortest
/// round-trip repr of the rounded double (`698.0`, `403.5`, `522.57`).
///
/// `format!("{x:.2}")` is not enough: it keeps the padding (`698.00`) and the
/// 44-FZ corpus hides that because its value happens to have two decimals.
fn py_round2(x: f64) -> String {
    if !x.is_finite() {
        // Unreachable: a corpus with no article parts fails closed before the
        // G-layer volume is computed. Kept explicit so NaN can never reach the
        // JSON writer as a bare `NaN` token (invalid JSON).
        return format!("{x}");
    }
    let rounded: f64 = format!("{x:.2}").parse().unwrap_or(x);
    let mut s = format!("{rounded}");
    if !s.contains('.') && !s.contains('e') && !s.contains('E') {
        s.push_str(".0");
    }
    s
}

fn render_digests(
    editions: &[EditionDigest],
    digests_by_ed: &BTreeMap<u32, BTreeMap<String, String>>,
    spans_by_ed: &BTreeMap<u32, BTreeMap<String, ArticleSpan>>,
    shas_by_ed: &BTreeMap<u32, String>,
) -> String {
    let mut out: Vec<String> = Vec::new();
    out.push(j_compact_str(&obj(vec![
        ("record_kind", J::Str("header".into())),
        ("schema_version", J::Str(DIGESTS_SCHEMA.into())),
        (
            "normalization_profile",
            obj(vec![
                ("id", J::Str(NORM_PROFILE_ID.into())),
                (
                    "rules",
                    J::Arr(
                        PROFILE_RULES
                            .iter()
                            .map(|s| J::Str(s.to_string()))
                            .collect(),
                    ),
                ),
            ]),
        ),
        (
            "non_claims",
            J::Arr(
                NON_AUTHORITY
                    .iter()
                    .map(|s| J::Str(s.to_string()))
                    .collect(),
            ),
        ),
    ])));
    for e in editions {
        let digests = &digests_by_ed[&e.edition_no];
        let mut aids: Vec<&String> = digests.keys().collect();
        aids.sort_by_key(|aid| article_sort_key(aid));
        for aid in aids {
            let span = &spans_by_ed[&e.edition_no][aid];
            out.push(j_compact_str(&obj(vec![
                ("record_kind", J::Str("art_digest".into())),
                ("schema_version", J::Str(DIGESTS_SCHEMA.into())),
                ("edition_no", J::Int(e.edition_no as i64)),
                ("article", J::Str(aid.clone())),
                ("digest", J::Str(digests[aid].clone())),
                (
                    "source",
                    obj(vec![
                        ("sha256", J::Str(shas_by_ed[&e.edition_no].clone())),
                        ("p_start", J::Int(span.p_start as i64)),
                        ("p_end", J::Int(span.p_end as i64)),
                    ]),
                ),
            ])));
        }
    }
    out.join("\n") + "\n"
}

// ---------- D4 measurement (ADR-0031 D4, ed-50 scoped per D782) ----------
//
// Ported 1:1 from the Python reference (`classify_references`,
// `measure_requisites`, `measure_deep_links`, `references_document`). The two
// requisite patterns are hand-rolled because ADR-0031 D8 forbids new crate
// dependencies; the matchers reproduce the Python regexes' leftmost,
// greedy-quantifier semantics for the shapes that actually occur (and the
// general shape otherwise).

/// Python `\w`: Unicode alphanumeric plus underscore.
fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// Case-insensitive literal prefix match at `pos` (Python `re.I`);
/// `needle_lower` must already be lowercase. Returns the end byte offset.
fn ci_literal_end(s: &str, pos: usize, needle_lower: &str) -> Option<usize> {
    let mut consumed = 0usize;
    let mut it = s[pos..].chars();
    for nc in needle_lower.chars() {
        let hc = it.next()?;
        if !hc.to_lowercase().eq(std::iter::once(nc)) {
            return None;
        }
        consumed += hc.len_utf8();
    }
    Some(pos + consumed)
}

/// End of the maximal `\w` run starting at `pos` (Python greedy `\w+`/`\w*`:
/// a shorter run could only be followed by another word char, never by the
/// literal/`\s` the patterns require next).
fn word_run_end(s: &str, pos: usize) -> usize {
    let mut end = pos;
    for (i, c) in s[pos..].char_indices() {
        if is_word_char(c) {
            end = pos + i + c.len_utf8();
        } else {
            break;
        }
    }
    end
}

/// End of the maximal whitespace run starting at `pos` (Python greedy `\s+`).
fn ws_run_end(s: &str, pos: usize) -> usize {
    let mut end = pos;
    for (i, c) in s[pos..].char_indices() {
        if c.is_whitespace() {
            end = pos + i + c.len_utf8();
        } else {
            break;
        }
    }
    end
}

fn next_char_boundary(s: &str, pos: usize) -> usize {
    match s[pos..].chars().next() {
        Some(c) => pos + c.len_utf8(),
        None => pos + 1,
    }
}

/// All char-boundary offsets in `[a, b]`, ascending (both are boundaries).
fn boundaries_between(s: &str, a: usize, b: usize) -> Vec<usize> {
    let mut out = vec![a];
    let mut i = a;
    while i < b {
        i = next_char_boundary(s, i);
        out.push(i);
    }
    out
}

/// Python `(\d{2})\.(\d{2})\.(\d{4})` at `pos`; returns (end, ISO date).
fn dated_at(s: &str, pos: usize) -> Option<(usize, String)> {
    let window = s.as_bytes().get(pos..pos + 10)?;
    let shape_ok = window.iter().enumerate().all(|(i, c)| {
        if i == 2 || i == 5 {
            *c == b'.'
        } else {
            c.is_ascii_digit()
        }
    });
    if !shape_ok {
        return None;
    }
    let iso = format!(
        "{}-{}-{}",
        &s[pos + 6..pos + 10],
        &s[pos + 3..pos + 5],
        &s[pos..pos + 2]
    );
    Some((pos + 10, iso))
}

/// Python `[^\s,;)]+` at `pos`; returns the end offset, `None` when empty.
fn number_run_end(s: &str, pos: usize) -> Option<usize> {
    let mut end = pos;
    for (i, c) in s[pos..].char_indices() {
        if c.is_whitespace() || c == ',' || c == ';' || c == ')' {
            break;
        }
        end = pos + i + c.len_utf8();
    }
    if end == pos { None } else { Some(end) }
}

/// The `от\s+date\s+N\s*number` tail with the literal `от` already positioned
/// at `pos` (the `\s*`/`\s+` that precedes it is handled by the callers).
fn requisite_tail_at(s: &str, pos: usize) -> Option<(usize, String, String)> {
    let ot_end = ci_literal_end(s, pos, "от")?;
    let ws = ws_run_end(s, ot_end);
    if ws == ot_end {
        return None;
    }
    let (date_end, iso) = dated_at(s, ws)?;
    let ws2 = ws_run_end(s, date_end);
    if ws2 == date_end {
        return None;
    }
    let n_end = ci_literal_end(s, ws2, "n")?;
    let ns = ws_run_end(s, n_end);
    let num_end = number_run_end(s, ns)?;
    let number = s[ns..num_end].trim_end_matches('.').to_string();
    Some((num_end, iso, number))
}

/// Python `\s*от\s+date\s+N\s*number` starting at `pos` (group 2 is
/// followed by `\s*`, not `\s+`, before `от`).
fn optional_space_requisite_tail_at(s: &str, pos: usize) -> Option<(usize, String, String)> {
    let ws = ws_run_end(s, pos);
    requisite_tail_at(s, ws)
}

/// Python `\s+от\s+date\s+N\s*number` starting at `pos`.
fn spaced_requisite_tail_at(s: &str, pos: usize) -> Option<(usize, String, String)> {
    let ws = ws_run_end(s, pos);
    if ws == pos {
        return None;
    }
    requisite_tail_at(s, ws)
}

/// Python `RE_REQ_LAW` at `pos`:
/// `(?:Федеральн\w+ закон\w+|закон\w*)\s+от\s+date\s+N\s*number`.
fn law_at(s: &str, pos: usize) -> Option<(usize, String, String)> {
    if let Some(after_stem) = ci_literal_end(s, pos, "федеральн") {
        let r1 = word_run_end(s, after_stem);
        // Branch A carries a single *literal* space between the two words
        // (not `\s`); only the maximal `\w` run can be followed by it.
        if r1 > after_stem && s.as_bytes().get(r1) == Some(&b' ') {
            let zakon = r1 + 1;
            if let Some(z_end) = ci_literal_end(s, zakon, "закон") {
                let r2 = word_run_end(s, z_end);
                if r2 > z_end
                    && let Some(hit) = spaced_requisite_tail_at(s, r2)
                {
                    return Some(hit);
                }
            }
        }
    }
    let z_end = ci_literal_end(s, pos, "закон")?;
    let r = word_run_end(s, z_end);
    spaced_requisite_tail_at(s, r)
}

/// One body alternative of the Python `RE_REQ_PPA` group 2, in alternation
/// order: 0 `Правительств\w+ РФ`, 1 `Минфина России`, 2 `ФНС России`.
fn ppa_body_end(s: &str, pos: usize, kind: usize) -> Option<usize> {
    match kind {
        0 => {
            let after = ci_literal_end(s, pos, "правительств")?;
            let r = word_run_end(s, after);
            if r == after {
                return None;
            }
            ci_literal_end(s, r, " рф")
        }
        1 => ci_literal_end(s, pos, "минфина россии"),
        2 => ci_literal_end(s, pos, "фнс россии"),
        _ => None,
    }
}

/// Python `(group2)?\s*от\s+date\s+N\s*number` from the `\s+` run that starts
/// at `p` and ends at `w`. The `\s+` is greedy, so it backtracks from `w`
/// downwards; `group2`'s lazy `[^)]{0,60}?` tries the shortest prefix first.
fn ppa_group2_or_absent(s: &str, p: usize, w: usize) -> Option<(usize, String, String)> {
    let starts = boundaries_between(s, p + 1, w);
    for (idx, &start) in starts.iter().enumerate().rev() {
        for kind in 0..3 {
            let mut b = start;
            let mut count = 0usize;
            loop {
                if let Some(hit) = ppa_body_end(s, b, kind)
                    .and_then(|body_end| optional_space_requisite_tail_at(s, body_end))
                {
                    return Some(hit);
                }
                if count >= 60 {
                    break;
                }
                let Some(c) = s[b..].chars().next() else {
                    break;
                };
                // `[^)]` stops at the first closing paren.
                if c == ')' {
                    break;
                }
                b += c.len_utf8();
                count += 1;
            }
        }
        // group 2 absent: `\s*` soaks up the rest of the whitespace run, so
        // `от` must sit at `w`. Constant across `s`, hence checked once.
        if idx == starts.len() - 1
            && let Some(hit) = requisite_tail_at(s, w)
        {
            return Some(hit);
        }
    }
    None
}

/// Python `RE_REQ_PPA` at `pos`. Returns (end, lowercased type word, ISO
/// date, number).
fn ppa_at(s: &str, pos: usize) -> Option<(usize, String, String, String)> {
    // (stem, minimum `\w` tail length) in the Python alternation order.
    const FORMS: [(&str, usize); 4] = [
        ("постановлени", 1),
        ("приказ", 0),
        ("распоряжени", 1),
        ("письмо", 0),
    ];
    for (stem, min_tail) in FORMS {
        let Some(after) = ci_literal_end(s, pos, stem) else {
            continue;
        };
        let r = word_run_end(s, after);
        if r < after + min_tail {
            continue;
        }
        let w = ws_run_end(s, r);
        if w == r {
            continue;
        }
        if let Some((end, iso, number)) = ppa_group2_or_absent(s, r, w) {
            return Some((end, s[pos..r].to_lowercase(), iso, number));
        }
    }
    None
}

/// Python `find_requisites`: external requisite occurrences over one sentence,
/// from two independent scans (law first, then sub-legislative acts).
fn find_requisites(sent: &str) -> Vec<(String, String, String)> {
    let mut found: Vec<(String, String, String)> = Vec::new();
    let mut pos = 0usize;
    while pos < sent.len() {
        if let Some((end, iso, number)) = law_at(sent, pos) {
            found.push(("law".into(), iso, number));
            pos = end;
        } else {
            pos = next_char_boundary(sent, pos);
        }
    }
    pos = 0;
    while pos < sent.len() {
        if let Some((end, typ, iso, number)) = ppa_at(sent, pos) {
            found.push((typ, iso, number));
            pos = end;
        } else {
            pos = next_char_boundary(sent, pos);
        }
    }
    found
}

/// Python `article_chunks` (digests + per-article chunks). `scan_edition` keeps
/// its own inline copy for the four byte-pinned artifacts; this one feeds the
/// D4 measurement only.
fn article_chunks(paras: &[String]) -> (BTreeMap<String, String>, BTreeMap<String, Vec<String>>) {
    let mut digests: BTreeMap<String, String> = BTreeMap::new();
    let mut full_text: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut cur: Option<String> = None;
    for text in paras {
        if let Some((no, body)) = article_heading(text) {
            let aid = format!("statya-{no}");
            digests.insert(aid.clone(), sha12(&format!("H:{body}")));
            if !body.is_empty() {
                full_text.entry(aid.clone()).or_default().push(body);
            }
            cur = Some(aid);
            continue;
        }
        if let (Some(aid), false) = (cur.as_deref(), text.is_empty()) {
            let aid = aid.to_string();
            full_text.entry(aid.clone()).or_default().push(text.clone());
            let d = digests.get(&aid).cloned().unwrap_or_default();
            digests.insert(aid, sha12(&format!("{d}|{text}")));
        }
    }
    (digests, full_text)
}

/// Python `article_body`: the article chunks after the heading line — the D4
/// measurement scope. The heading line is structural metadata (its text is
/// already carried as the `H:` digest prefix), so including it would add three
/// ed-50 heading-only requisite mentions and drift from the 611/609 oracle.
fn article_body(full_text: &BTreeMap<String, Vec<String>>) -> BTreeMap<String, Vec<String>> {
    full_text
        .iter()
        .map(|(aid, chunks)| {
            let rest = if chunks.len() > 1 {
                chunks[1..].to_vec()
            } else {
                Vec::new()
            };
            (aid.clone(), rest)
        })
        .collect()
}

/// Candidate (citing article, target article) pair.
type RefPair = (String, String);

/// Python `classify_references` (ADR-0031 D4): sentence-scoped reference
/// qualification into candidates / internal / external-sentence.
fn classified_references(
    digests: &BTreeMap<String, String>,
    body: &BTreeMap<String, Vec<String>>,
) -> (Vec<RefPair>, Vec<RefPair>, Vec<RefPair>) {
    use std::collections::BTreeSet;
    let mut candidates: BTreeSet<RefPair> = BTreeSet::new();
    let mut internal: BTreeSet<RefPair> = BTreeSet::new();
    let mut external: BTreeSet<RefPair> = BTreeSet::new();
    for (aid, chunks) in body {
        for chunk in chunks {
            for sent in split_sentences(chunk) {
                let external_marker = contains_external_marker_ci(&sent)
                    && !sent.contains("настоящего")
                    && !sent.contains("прежнему");
                for num in refs_in_sentence(&sent) {
                    let target = format!("statya-{num}");
                    if target != *aid && digests.contains_key(&target) {
                        let pair = (aid.clone(), target);
                        if external_marker {
                            external.insert(pair.clone());
                        } else {
                            internal.insert(pair.clone());
                        }
                        candidates.insert(pair);
                    }
                }
            }
        }
    }
    (
        candidates.into_iter().collect(),
        internal.into_iter().collect(),
        external.into_iter().collect(),
    )
}

/// D4 requisite measurement (occurrence totals + sorted unique rows).
struct RequisiteMeasurement {
    total: usize,
    exact_date: usize,
    unique: usize,
    /// Sorted by `(type, ISO date, number)` — the Python `sorted(resolved)`.
    rows: Vec<(String, String, String, String, Option<String>)>,
}

/// Python `measure_requisites`: requisites resolved through `resolve_amend`.
fn measure_requisites(
    body: &BTreeMap<String, Vec<String>>,
    con: &rusqlite::Connection,
    prefix: &str,
) -> Result<RequisiteMeasurement, RefError> {
    let mut occurrences: Vec<(String, String, String)> = Vec::new();
    for chunks in body.values() {
        for chunk in chunks {
            for sent in split_sentences(chunk) {
                occurrences.extend(find_requisites(&sent));
            }
        }
    }
    let mut resolved: BTreeMap<(String, String, String), (String, Option<String>)> =
        BTreeMap::new();
    let mut exact_date = 0usize;
    for key in &occurrences {
        let entry = match resolved.get(key) {
            Some(v) => v.clone(),
            None => {
                let v = resolve_amend(con, &key.1, &key.2, prefix)?;
                resolved.insert(key.clone(), v.clone());
                v
            }
        };
        if entry.0 == "resolved_enacting_date" {
            exact_date += 1;
        }
    }
    let rows = resolved
        .iter()
        .map(|((typ, iso, num), (tier, rel))| {
            (
                typ.clone(),
                iso.clone(),
                num.clone(),
                tier.clone(),
                rel.clone(),
            )
        })
        .collect();
    Ok(RequisiteMeasurement {
        total: occurrences.len(),
        exact_date,
        unique: resolved.len(),
        rows,
    })
}

/// Python `measure_deep_links`: (candidates, resolved). Resolution needs the
/// target act's corpus and the edition in force at the citing act's applied
/// day, neither of which is in this measurement's scope, so `resolved` is
/// empty by construction — an honest derived zero, not a silent skip.
fn measure_deep_links(body: &BTreeMap<String, Vec<String>>) -> (Vec<RefPair>, Vec<RefPair>) {
    use std::collections::BTreeSet;
    let mut candidates: BTreeSet<RefPair> = BTreeSet::new();
    for (aid, chunks) in body {
        for chunk in chunks {
            for sent in split_sentences(chunk) {
                if find_requisites(&sent).is_empty() {
                    continue;
                }
                for num in refs_in_sentence(&sent) {
                    let target = format!("statya-{num}");
                    if target != *aid {
                        candidates.insert((aid.clone(), target));
                    }
                }
            }
        }
    }
    (candidates.into_iter().collect(), Vec::new())
}

/// Python `measurement_edition_path`: the corpus file carrying `edition_no`.
fn measurement_edition_path(corpus_dir: &Path, edition_no: u32) -> Option<PathBuf> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(corpus_dir)
        .ok()?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.starts_with("edition-") && n.ends_with(".xml"))
        })
        .collect();
    files.sort();
    files.into_iter().find(|p| {
        p.file_name()
            .and_then(|n| n.to_str())
            .and_then(edition_no_of)
            == Some(edition_no)
    })
}

/// The ed-50 measurement applies only where the corpus carries edition 50
/// (D782). Fixture corpora without it must stay exit 0, never exit 3.
pub fn measurement_applicable(corpus_dir: &Path) -> bool {
    measurement_edition_path(corpus_dir, MEASUREMENT_EDITION).is_some()
}

/// Python `render_references(build_references_measurement(..))`: the D4
/// measurement document (sorted keys, one-space indent, trailing newline).
pub fn references_document(
    corpus_dir: &Path,
    catalog: &Path,
    edition_no: u32,
) -> Result<String, RefError> {
    let path = measurement_edition_path(corpus_dir, edition_no)
        .ok_or_else(|| RefError::new(format!("corpus has no edition {edition_no}")))?;
    let bytes = std::fs::read(&path)
        .map_err(|e| RefError::new(format!("unreadable edition file {}: {e}", path.display())))?;
    if !declares_wordml_namespace(&bytes) {
        return Err(RefError::new(format!(
            "edition file {} does not declare the WordML 2003 namespace {WORDML_NAMESPACE}",
            path.display()
        )));
    }
    let paras = scan_wordml_paragraphs(&bytes)?;
    let (digests, full_text) = article_chunks(&paras);
    let body = article_body(&full_text);
    let (candidates, internal, external) = classified_references(&digests, &body);
    let con = open_catalog(catalog)?;
    let prefix = corpus_prefix(corpus_dir);
    let requisites = measure_requisites(&body, &con, &prefix)?;
    let (deep_candidates, deep_links) = measure_deep_links(&body);
    let act_dir = act_dir_name(corpus_dir)?;
    let non_claims: Vec<J> = NON_AUTHORITY
        .iter()
        .chain(REFS_NON_CLAIMS.iter())
        .map(|s| J::Str(s.to_string()))
        .collect();
    let edge_array = |pairs: &[RefPair]| {
        J::Arr(
            pairs
                .iter()
                .map(|(a, b)| J::Arr(vec![J::Str(a.clone()), J::Str(b.clone())]))
                .collect(),
        )
    };
    let rows: Vec<J> = requisites
        .rows
        .iter()
        .map(|(typ, iso, num, tier, rel)| {
            let mut entries: Vec<(&str, J)> = vec![
                ("type", J::Str(typ.clone())),
                ("date", J::Str(iso.clone())),
                ("number", J::Str(num.clone())),
                ("tier", J::Str(tier.clone())),
            ];
            if let Some(rel) = rel {
                entries.push(("resolved_path", J::Str(rel.clone())));
            }
            obj(entries)
        })
        .collect();
    let document = obj(vec![
        ("schema_version", J::Str(REFS_SCHEMA.into())),
        ("authoritative", J::Bool(false)),
        (
            "scope",
            obj(vec![
                ("act_dir", J::Str(act_dir)),
                ("edition_no", J::Int(edition_no as i64)),
            ]),
        ),
        ("non_claims", J::Arr(non_claims)),
        (
            "counts",
            obj(vec![
                ("candidates", J::Int(candidates.len() as i64)),
                ("internal", J::Int(internal.len() as i64)),
                ("external_sentence", J::Int(external.len() as i64)),
                ("deep_link_candidates", J::Int(deep_candidates.len() as i64)),
                ("deep_links", J::Int(deep_links.len() as i64)),
                ("requisites", J::Int(requisites.total as i64)),
                (
                    "requisites_exact_date",
                    J::Int(requisites.exact_date as i64),
                ),
                ("requisites_unique", J::Int(requisites.unique as i64)),
            ]),
        ),
        ("edges_internal", edge_array(&internal)),
        ("edges_external_sentence", edge_array(&external)),
        ("requisites", J::Arr(rows)),
    ]);
    Ok(j_pretty_str(&document))
}

// ---------- D5 pageindex ladder (ADR-0031 D5) ----------

/// Ladder level of a paragraph block (D783): any non-empty paragraph the six
/// heading levels above do not recognize — preamble and appendix included.
const PAGEINDEX_BLOCK_LEVEL: u8 = 7;

/// One ladder node. A node owns exactly one paragraph (`p_start == p_end`), so
/// `chars` is that paragraph's character count and the nodes partition the
/// non-empty paragraphs of the edition.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PageIndexNode {
    pub id: String,
    pub level: u8,
    pub kind: String,
    pub label: String,
    pub parent: Option<String>,
    pub p_start: usize,
    pub p_end: usize,
    pub chars: usize,
    pub char_start: usize,
    pub char_end: usize,
}

/// Byte length of the leading whitespace run (Python `\s` over a `str`).
/// Paragraph text is already stripped, so this only ever sees interior runs.
fn ws_len(s: &str) -> usize {
    let mut k = 0;
    for c in s.chars() {
        if !c.is_whitespace() {
            break;
        }
        k += c.len_utf8();
    }
    k
}

/// Byte length of the leading ASCII digit run (Python `\d`; the corpus is
/// ASCII-numbered, same choice the T04 requisite port took).
fn digit_run(s: &str) -> usize {
    s.bytes().take_while(|b| b.is_ascii_digit()).count()
}

/// Python `\d+(?:\d+)*`: the maximal dotted-number label and its byte length.
/// Greedy with nothing required after it, so the longest prefix always wins.
fn dotted_label(s: &str) -> Option<(String, usize)> {
    let d = digit_run(s);
    if d == 0 {
        return None;
    }
    let mut end = d;
    while s[end..].starts_with('.') {
        let d2 = digit_run(&s[end + 1..]);
        if d2 == 0 {
            break;
        }
        end += 1 + d2;
    }
    Some((s[..end].to_string(), end))
}

/// Python `RE_SECTION = ^Раздел\s*([IVXLCXХ\d]+)?` — the label group is
/// optional, so any paragraph starting with "Раздел" matches; a missing or
/// unrecognized label is "unnumbered".
fn section_of(text: &str) -> Option<String> {
    let rest = text.strip_prefix("Раздел")?;
    let rest = &rest[ws_len(rest)..];
    let mut k = 0usize;
    for c in rest.chars() {
        if c.is_ascii_digit() || matches!(c, 'I' | 'V' | 'X' | 'L' | 'C' | 'Х') {
            k += c.len_utf8();
        } else {
            break;
        }
    }
    Some(if k == 0 {
        "unnumbered".to_string()
    } else {
        rest[..k].to_string()
    })
}

/// Python `RE_CH = ^Глава (\d+(?:\.\d+)?)\.?\s+(.+)`. `\s+` then `.+` means a
/// match needs whitespace plus at least one further character, or two
/// whitespace characters `.+` can consume after backtracking.
fn chapter_of(text: &str) -> Option<String> {
    let rest = text.strip_prefix("Глава ")?;
    let d = digit_run(rest);
    if d == 0 {
        return None;
    }
    let num = &rest[..d];
    let after = &rest[d..];
    let mut candidates: Vec<&str> = Vec::new();
    if let Some(tail) = after.strip_prefix('.') {
        let d2 = digit_run(tail);
        if d2 > 0 {
            candidates.push(&tail[d2..]);
        }
    }
    candidates.push(after);
    for cand in candidates {
        for tail in [cand.strip_prefix('.'), Some(cand)] {
            let Some(tail) = tail else { continue };
            let w = ws_len(tail);
            if w >= 1 && (!tail[w..].is_empty() || w >= 2) {
                return Some(num.to_string());
            }
        }
    }
    None
}

/// Python `RE_PARA = ^§\s*(\d+(?:\.\d+)*)`.
fn paragraph_of(text: &str) -> Option<String> {
    let rest = text.strip_prefix('§')?;
    let rest = &rest[ws_len(rest)..];
    dotted_label(rest).map(|(label, _)| label)
}

/// Python `RE_PART_DOTTED = ^(\d+(?:\.\d+)*)\.\s`.
fn part_of(text: &str) -> Option<String> {
    let (label, end) = dotted_label(text)?;
    let rest = text[end..].strip_prefix('.')?;
    (ws_len(rest) >= 1).then_some(label)
}

/// Python `RE_PUNKT = ^(\d+)\)\s`.
fn punkt_of(text: &str) -> Option<String> {
    let d = digit_run(text);
    if d == 0 {
        return None;
    }
    let rest = text[d..].strip_prefix(')')?;
    (ws_len(rest) >= 1).then(|| text[..d].to_string())
}

/// Python class `[а-яё]`.
fn is_subpunkt_letter(c: char) -> bool {
    ('а'..='я').contains(&c) || c == 'ё'
}

/// Python `RE_SUBPUNKT = ^([а-яё])\)\s`.
fn subpunkt_of(text: &str) -> Option<String> {
    let c = text.chars().next()?;
    if !is_subpunkt_letter(c) {
        return None;
    }
    let rest = text[c.len_utf8()..].strip_prefix(')')?;
    (ws_len(rest) >= 1).then(|| c.to_string())
}

/// Python `pageindex_level`: `(level, kind, label)` of a recognized heading
/// paragraph, else `None` (a level-7 block). Precedence is ADR-0031 D5:
/// section, chapter/§ (one level-2 slot, `kind` discriminates), article, part,
/// punkt, subpunkt.
fn pageindex_level(text: &str) -> Option<(u8, &'static str, String)> {
    if let Some(label) = section_of(text) {
        return Some((1, "section", label));
    }
    if let Some(label) = chapter_of(text) {
        return Some((2, "chapter", label));
    }
    if let Some(label) = paragraph_of(text) {
        return Some((2, "paragraph", label));
    }
    if let Some((no, _)) = article_heading(text) {
        return Some((3, "statya", no));
    }
    if let Some(label) = part_of(text) {
        return Some((4, "part", label));
    }
    if let Some(label) = punkt_of(text) {
        return Some((5, "punkt", label));
    }
    if let Some(label) = subpunkt_of(text) {
        return Some((6, "subpunkt", label));
    }
    None
}

/// Python `check_pageindex_invariants`: the four ADR-0031 D5 invariants,
/// executed on the derived ladder. A violation is a `RefError` (ADR-0031 D6
/// exit 3, fail-closed): the ladder is never published half-derived.
fn check_pageindex_invariants(
    paras: &[String],
    digests: &BTreeMap<String, String>,
    nodes: &[PageIndexNode],
) -> Result<(), RefError> {
    use std::collections::BTreeSet;
    // (b) single assignment: every non-empty paragraph is in exactly one node.
    let owned: Vec<usize> = nodes.iter().map(|n| n.p_start).collect();
    let expected: Vec<usize> = paras
        .iter()
        .enumerate()
        .filter(|(_, text)| !text.is_empty())
        .map(|(idx, _)| idx)
        .collect();
    if owned != expected || nodes.iter().any(|n| n.p_start != n.p_end) {
        return Err(RefError::new(
            "pageindex invariant violated: every non-empty paragraph must belong to exactly one node",
        ));
    }
    // (a) char conservation.
    let node_chars: usize = nodes.iter().map(|n| n.chars).sum();
    let para_chars: usize = paras
        .iter()
        .filter(|text| !text.is_empty())
        .map(|text| text.chars().count())
        .sum();
    if node_chars != para_chars {
        return Err(RefError::new(
            "pageindex invariant violated: char conservation",
        ));
    }
    // (c) no article outside the ladder: the ladder's statya ids are the digest
    // spine (articles are the last path segment of the node id).
    let ladder: BTreeSet<&str> = nodes
        .iter()
        .filter(|n| n.kind == "statya")
        .filter_map(|n| n.id.rsplit('/').next())
        .collect();
    let spine: BTreeSet<&str> = digests.keys().map(|k| k.as_str()).collect();
    if ladder != spine {
        return Err(RefError::new(format!(
            "pageindex invariant violated: the ladder must carry exactly the {} articles of the digest spine",
            digests.len()
        )));
    }
    // (d) id uniqueness.
    let ids: BTreeSet<&str> = nodes.iter().map(|n| n.id.as_str()).collect();
    if ids.len() != nodes.len() {
        return Err(RefError::new(
            "pageindex invariant violated: duplicate path id",
        ));
    }
    Ok(())
}

/// Python `build_pageindex`: the ADR-0031 D5 contents ladder over one edition's
/// paragraphs. A new node of level L closes every open node of level >= L (the
/// level-2 slot is shared by chapter and §), so the path ids
/// (`chapter-1/statya-44/part-2/punkt-3/subpunkt-а/block-2718`) cannot collide
/// across articles. Every non-empty paragraph is exactly one node: a recognized
/// heading at its own level, or a level-7 block (D783). Empty paragraphs stay
/// out of the ladder and add no chars. All four D5 invariants are executed
/// before the ladder is returned.
///
/// `char_start`/`char_end` are character offsets into `"\n".join(paras)`
/// (Python `len(str)` counts code points, so this counts `chars()` too).
pub fn build_pageindex(paras: &[String]) -> Result<Vec<PageIndexNode>, RefError> {
    let mut offsets: Vec<usize> = Vec::with_capacity(paras.len());
    let mut offset = 0usize;
    for text in paras {
        offsets.push(offset);
        offset += text.chars().count() + 1;
    }
    // The digest spine of the same paragraphs drives invariant (c).
    let (digests, _full_text) = article_chunks(paras);
    let mut nodes: Vec<PageIndexNode> = Vec::new();
    let mut stack: Vec<(u8, String)> = Vec::new();
    for (idx, text) in paras.iter().enumerate() {
        if text.is_empty() {
            continue;
        }
        let (level, kind, label) = match pageindex_level(text) {
            Some((level, kind, label)) => (level, kind.to_string(), label),
            None => (PAGEINDEX_BLOCK_LEVEL, "block".to_string(), idx.to_string()),
        };
        while stack.last().is_some_and(|(open, _)| *open >= level) {
            stack.pop();
        }
        let parent = stack.last().map(|(_, id)| id.clone());
        let id = match &parent {
            Some(p) => format!("{p}/{kind}-{label}"),
            None => format!("{kind}-{label}"),
        };
        let chars = text.chars().count();
        nodes.push(PageIndexNode {
            id: id.clone(),
            level,
            kind,
            label,
            parent,
            p_start: idx,
            p_end: idx,
            chars,
            char_start: offsets[idx],
            char_end: offsets[idx] + chars,
        });
        stack.push((level, id));
    }
    check_pageindex_invariants(paras, &digests, &nodes)?;
    Ok(nodes)
}

/// Python `render_pageindex(build_pageindex_measurement(..))`: the D5 contents
/// ladder document (sorted keys, one-space indent, trailing newline).
pub fn pageindex_document(corpus_dir: &Path, edition_no: u32) -> Result<String, RefError> {
    let path = measurement_edition_path(corpus_dir, edition_no)
        .ok_or_else(|| RefError::new(format!("corpus has no edition {edition_no}")))?;
    let bytes = std::fs::read(&path)
        .map_err(|e| RefError::new(format!("unreadable edition file {}: {e}", path.display())))?;
    if !declares_wordml_namespace(&bytes) {
        return Err(RefError::new(format!(
            "edition file {} does not declare the WordML 2003 namespace {WORDML_NAMESPACE}",
            path.display()
        )));
    }
    let paras = scan_wordml_paragraphs(&bytes)?;
    let nodes = build_pageindex(&paras)?;
    let act_dir = act_dir_name(corpus_dir)?;
    // section chapter paragraph statya part punkt subpunkt block
    let mut counts = [0usize; 8];
    for node in &nodes {
        let slot = match node.kind.as_str() {
            "section" => 0,
            "chapter" => 1,
            "paragraph" => 2,
            "statya" => 3,
            "part" => 4,
            "punkt" => 5,
            "subpunkt" => 6,
            "block" => 7,
            _ => continue,
        };
        counts[slot] += 1;
    }
    let max_depth = nodes.iter().map(|n| n.level).max().unwrap_or(0);
    let chars: usize = nodes.iter().map(|n| n.chars).sum();
    let non_claims: Vec<J> = NON_AUTHORITY
        .iter()
        .chain(PAGEINDEX_NON_CLAIMS.iter())
        .map(|s| J::Str(s.to_string()))
        .collect();
    let node_json = |n: &PageIndexNode| {
        obj(vec![
            ("id", J::Str(n.id.clone())),
            ("level", J::Int(n.level as i64)),
            ("kind", J::Str(n.kind.clone())),
            ("label", J::Str(n.label.clone())),
            ("parent", n.parent.clone().map(J::Str).unwrap_or(J::Null)),
            ("p_start", J::Int(n.p_start as i64)),
            ("p_end", J::Int(n.p_end as i64)),
            ("chars", J::Int(n.chars as i64)),
            ("char_start", J::Int(n.char_start as i64)),
            ("char_end", J::Int(n.char_end as i64)),
        ])
    };
    let document = obj(vec![
        ("schema_version", J::Str(PAGEINDEX_SCHEMA.into())),
        ("authoritative", J::Bool(false)),
        (
            "scope",
            obj(vec![
                ("act_dir", J::Str(act_dir)),
                ("edition_no", J::Int(edition_no as i64)),
            ]),
        ),
        ("non_claims", J::Arr(non_claims)),
        (
            "counts",
            obj(vec![
                ("total_nodes", J::Int(nodes.len() as i64)),
                ("sections", J::Int(counts[0] as i64)),
                ("chapters", J::Int(counts[1] as i64)),
                ("paragraphs", J::Int(counts[2] as i64)),
                ("articles", J::Int(counts[3] as i64)),
                ("parts", J::Int(counts[4] as i64)),
                ("punkts", J::Int(counts[5] as i64)),
                ("subpoints", J::Int(counts[6] as i64)),
                ("blocks", J::Int(counts[7] as i64)),
                ("max_depth", J::Int(max_depth as i64)),
                ("chars", J::Int(chars as i64)),
            ]),
        ),
        ("nodes", J::Arr(nodes.iter().map(node_json).collect())),
    ]);
    Ok(j_pretty_str(&document))
}

// ---------- CLI support ----------

/// Full-text JSON-LD layer for one edition (on-demand projection; not
/// committed as an artifact). Python parity: `edition_layer_document` in
/// `scripts/m217_reference_jsonld.py`.
pub fn edition_layer_document(
    path: &Path,
    edition_no: u32,
    day: &str,
) -> Result<Vec<u8>, RefError> {
    let bytes = std::fs::read(path)
        .map_err(|e| RefError::new(format!("unreadable edition file {}: {e}", path.display())))?;
    if !declares_wordml_namespace(&bytes) {
        return Err(RefError::new(format!(
            "edition file {} does not declare the WordML 2003 namespace {WORDML_NAMESPACE}",
            path.display()
        )));
    }
    let paras = scan_wordml_paragraphs(&bytes)?;
    let mut nodes: Vec<J> = Vec::new();
    let mut index: BTreeMap<String, usize> = BTreeMap::new();
    let mut cur: Option<String> = None;
    for text in &paras {
        // `article_heading` already strips the "Статья " prefix; stripping it
        // here as well made every heading miss and left `@graph` empty.
        if let Some((no, body)) = article_heading(text) {
            let id = format!("cc:44-fz:statya-{no}");
            if !index.contains_key(&id) {
                index.insert(id.clone(), nodes.len());
                nodes.push(obj(vec![
                    ("@id", J::Str(id.clone())),
                    ("@type", J::Str("cc:ComponentConcept".into())),
                    ("heading", J::Str(body)),
                    ("has_part", J::Arr(vec![])),
                    ("refs", J::Arr(vec![])),
                ]));
            }
            cur = Some(id);
            continue;
        }
        if let (Some(id), false) = (cur.as_deref(), text.is_empty())
            && let Some(pos) = index.get(id)
            && let J::Obj(entries) = &mut nodes[*pos]
        {
            // Python: the part id suffix is the part number, else "c";
            // `part_no` stays "cont" in both cases.
            let part =
                part_marker(text).then(|| text.split('.').next().unwrap_or("cont").to_string());
            let suffix = part.clone().unwrap_or_else(|| "c".into());
            let part_no = part.unwrap_or_else(|| "cont".into());
            for (k, v) in entries.iter_mut() {
                if k == "has_part"
                    && let J::Arr(items) = v
                {
                    items.push(obj(vec![
                        ("@id", J::Str(format!("ex:p/{edition_no}/{id}/{suffix}"))),
                        ("part_no", J::Str(part_no.clone())),
                        ("text", J::Str(text.clone())),
                    ]));
                }
            }
        }
    }
    let doc = obj(vec![
        (
            "@context",
            obj(vec![
                ("cc", J::Str("https://law-nexus.local/vocab/cc#".into())),
                ("eli", J::Str("http://data.europa.eu/eli/".into())),
                ("ex", J::Str("https://law-nexus.local/vocab/ex#".into())),
                ("heading", J::Str("ex:heading".into())),
                ("text", J::Str("ex:text".into())),
                ("part_no", J::Str("ex:partNo".into())),
                (
                    "effect_day",
                    obj(vec![
                        ("@id", J::Str("ex:effectDay".into())),
                        ("@type", J::Str("xsd:date".into())),
                    ]),
                ),
                (
                    "has_part",
                    obj(vec![
                        ("@id", J::Str("ex:hasPart".into())),
                        ("@type", J::Str("@id".into())),
                    ]),
                ),
                (
                    "refs",
                    obj(vec![
                        ("@id", J::Str("ex:refs".into())),
                        ("@type", J::Str("@id".into())),
                        ("@container", J::Str("@set".into())),
                    ]),
                ),
                ("xsd", J::Str("http://www.w3.org/2001/XMLSchema#".into())),
            ]),
        ),
        (
            "@id",
            J::Str(format!("eli:expression/44-fz/ed-{edition_no:04}")),
        ),
        ("effect_day", J::Str(day.to_string())),
        ("@graph", J::Arr(nodes)),
    ]);
    let mut s = String::new();
    j_pretty(&doc, 0, &mut s);
    Ok(s.into_bytes())
}

pub fn artifacts_dir(manifest_dir: &Path) -> PathBuf {
    manifest_dir
        .join("..")
        .join("..")
        .join("prd")
        .join("migration")
        .join("rust-evidence")
}

pub fn corpus_dir(manifest_dir: &Path) -> PathBuf {
    manifest_dir
        .join("..")
        .join("..")
        .join(CORPUS_DIR.replace('/', std::path::MAIN_SEPARATOR_STR))
}

pub fn catalog_path(manifest_dir: &Path) -> PathBuf {
    manifest_dir
        .join("..")
        .join("..")
        .join(CATALOG.replace('/', std::path::MAIN_SEPARATOR_STR))
}

pub fn artifact_paths(out_dir: &Path) -> [PathBuf; 4] {
    [
        out_dir.join("m217-reference-timeline.json"),
        out_dir.join("m217-reference-digests.jsonl"),
        out_dir.join("m217-reference-named-graphs.json"),
        out_dir.join("m217-reference-amend-provenance.json"),
    ]
}

/// ed-50-scoped measurement artifacts (ADR-0031 D782), kept separate from the
/// four full-corpus artifacts in `artifact_paths()`. In this order: the D4
/// references document and the D5 contents ladder.
pub fn measurement_artifact_paths(out_dir: &Path) -> Vec<PathBuf> {
    vec![
        out_dir.join("m217-reference-references.json"),
        out_dir.join("m217-reference-pageindex.json"),
    ]
}

/// Append a drift entry when `path` is missing or byte-differs from `body`.
fn note_drift(drift: &mut Vec<String>, path: &Path, body: &str) {
    match std::fs::read_to_string(path) {
        Ok(existing) => {
            if existing != *body {
                drift.push(format!("{}: byte drift", path.display()));
            }
        }
        Err(_) => drift.push(format!("{}: missing artifact", path.display())),
    }
}

pub fn run_check(corpus: &Path, catalog: &Path, out_dir: &Path) -> i32 {
    let opts = DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus.to_path_buf(),
        catalog: catalog.to_path_buf(),
    };
    let reference = match try_derive(&opts) {
        Ok(reference) => reference,
        Err(err) => {
            eprintln!("unreadable inputs: {err}");
            return err.exit_code();
        }
    };
    let bodies = [
        reference.timeline,
        reference.digests,
        reference.named_graphs,
        reference.amend,
    ];
    let paths = artifact_paths(out_dir);
    let mut drift = Vec::new();
    for (path, body) in paths.iter().zip(bodies.iter()) {
        note_drift(&mut drift, path, body);
    }
    // D782 applicability: the ed-50 measurements are compared only where the
    // corpus carries edition 50; elsewhere they are explicitly not applicable
    // and never count as drift (fixture corpora keep their exit 0). Both
    // measurement documents are derived, then compared against their own path
    // in `measurement_artifact_paths` order.
    if measurement_applicable(corpus) {
        let bodies = [
            references_document(corpus, catalog, MEASUREMENT_EDITION),
            pageindex_document(corpus, MEASUREMENT_EDITION),
        ];
        for (path, body) in measurement_artifact_paths(out_dir).iter().zip(bodies) {
            match body {
                Ok(body) => note_drift(&mut drift, path, &body),
                Err(err) => {
                    eprintln!("unreadable inputs: {err}");
                    return err.exit_code();
                }
            }
        }
    } else {
        println!("measurement not applicable: corpus has no edition {MEASUREMENT_EDITION}");
    }
    if !drift.is_empty() {
        for d in drift {
            eprintln!("drift: {d}");
        }
        return EXIT_DRIFT;
    }
    println!("check=ok artifacts byte-identical");
    EXIT_OK
}
