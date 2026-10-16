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
        match std::fs::read_to_string(path) {
            Ok(existing) => {
                if existing != *body {
                    drift.push(format!("{}: byte drift", path.display()));
                }
            }
            Err(_) => drift.push(format!("{}: missing artifact", path.display())),
        }
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
