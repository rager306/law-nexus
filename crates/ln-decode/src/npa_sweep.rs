//! Read-only corpus-sweep accumulator for the C1 NPA engine
//! (M198-das7v8 S01, ADR-0028 step 2).
//!
//! T01 domain contract only: an in-memory [`SweepAcc`] that ingests
//! already-decoded block text through the covering M197 lexer
//! (`ln_decode::lexer::lex`) and the morphology marker finder, and renders a
//! hand-rolled, closed-schema JSONL aggregate
//! (`npa-corpus-sweep/v1`, D328/D353 — stdlib only, no serde).
//!
//! T02 adds the measurement plumbing around the same accumulator: the
//! deterministic `std::fs` XML walker ([`walk_xml_files`]), bounded per-file
//! payload identity ([`payload_ref_for_path`]), per-file decode+ingest
//! ([`ingest_file`]), and the library-level runner ([`run_sweep`]) that the
//! thin `src/bin/npa-corpus-sweep.rs` shell (argv + printing only) wires up.
//! The tracked full-corpus evidence artifact stays downstream (T03).
//! `lexer.rs`, the YAML lexicon, and `morphology.rs` are read-only; the
//! 17-id table is a compile-time alias of the single `lexer::NPA_ABBREV_IDS`
//! canon, and the 9-id D329 table stays a hand-frozen copy of the goldens
//! rule pinned exactly by contract tests (M200-8s4kwq S01/T01). R070 stays
//! open and ADR-0028 stays `[proposed]`.

use std::collections::{BTreeMap, HashMap};
use std::fmt::Write as _;
use std::fs;
use std::path::{Component, Path, PathBuf};

use crate::adapters::ConsultantWordMlBlockDecoder;
use crate::domain::{
    fingerprint_bytes, DecodeRequest, FamilyFormat, ParagraphStyle, ParsedBlock, PayloadRef,
};
use crate::lexer::{self, TokenKind};
use crate::morphology;
use crate::ports::BlockDecoderPort;

/// Closed allowlist of canonical legal-drafting abbreviation ids — a
/// compile-time alias of the single read-only canon source
/// [`crate::lexer::NPA_ABBREV_IDS`] (M200-8s4kwq S01/T01; narrows the D354
/// "no lexer export" clause to lexeme data). The public sweep name stays
/// stable, and any canon length or content drift fails this build instead of
/// silently diverging. Lexemes stay YAML data.
pub const SWEEP_ABBREV_IDS: [&str; 17] = lexer::NPA_ABBREV_IDS;

/// The D329-nine: abbreviation ids that never occur in the tracked 44-ФЗ
/// corpus — a hand-frozen copy of the goldens rule owner
/// (`tests/npa_support::CORPUS_FORBIDDEN_ABBREV_IDS`): a `tests/` module
/// cannot be aliased from `src`, so the exact match is enforced by the
/// `t01_drift_pin_*` contract tests (M200-8s4kwq S01/T01). The list stays
/// frozen: never narrow it, never extend it. `№` is not an Abbrev id and
/// never appears here.
pub const D329_NINE_IDS: [&str; 9] = [
    "gl", "razd", "podp", "abz", "pril", "prim", "stst", "utv", "sr",
];

/// Closed schema tag and version of the aggregate JSONL (D353).
pub const SWEEP_SCHEMA: &str = "npa-corpus-sweep/v1";
pub const SWEEP_SCHEMA_VERSION: u32 = 1;

/// Ranked unknown-tail rows kept in the rendered aggregate (D352).
const UNKNOWN_TAIL_CAP: usize = 50;

/// Fixed serialization order of the nine closed token kinds.
const KIND_ORDER: [TokenKind; 9] = [
    TokenKind::Word,
    TokenKind::Abbrev,
    TokenKind::HierNum,
    TokenKind::Date,
    TokenKind::DocNo,
    TokenKind::EnumMarker,
    TokenKind::LawCode,
    TokenKind::Punct,
    TokenKind::Space,
];

/// One ranked unknown-tail / abbrev-candidate row (the same table serves both
/// views — the census is an alias, never a second ranking).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownTailEntry {
    /// Human view: the short original lexeme (a draft fact, not a paragraph).
    pub lexeme: String,
    pub count: u64,
    /// Machine id: `domain::fingerprint_bytes` (FNV-1a) of the original lexeme.
    pub id: String,
}

/// Shape census counters over the structural token kinds, plus the DocNo
/// suffix split and the HierNum segment-depth split.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
struct ShapeCounts {
    hier_num: u64,
    date: u64,
    doc_no: u64,
    enum_marker: u64,
    law_code: u64,
    doc_no_fz: u64,
    doc_no_fkz: u64,
    hier_seg2: u64,
    hier_seg3plus: u64,
}

/// Per-family file accounting fed by [`SweepAcc::note_file`].
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
struct FamilyCounts {
    seen: u64,
    decoded: u64,
    failed: u64,
}

/// Measurement accumulator over decoded block text.
///
/// All counting goes through the single covering lexer; nothing here decodes
/// WordML or touches the filesystem. A zero count for any of the 17 abbrev
/// ids or 9 D329 keys is still a finding, so both tables are always present
/// in the rendered aggregate.
#[derive(Debug, Default)]
pub struct SweepAcc {
    cycle: String,
    kind_hist: [u64; 9],
    abbrev_hits: BTreeMap<&'static str, u64>,
    d329_hits: BTreeMap<&'static str, u64>,
    shapes: ShapeCounts,
    files_seen: u64,
    files_decoded: u64,
    files_failed: u64,
    word_tokens: u64,
    marker_hits: u64,
    /// Original short lexeme -> hit count; ranked only at render time.
    unknown_tail: HashMap<String, u64>,
    family_split: BTreeMap<String, FamilyCounts>,
}

impl SweepAcc {
    /// New accumulator for one sweep `cycle` label (verbatim header field).
    pub fn new(cycle: impl Into<String>) -> Self {
        Self {
            cycle: cycle.into(),
            abbrev_hits: SWEEP_ABBREV_IDS.iter().map(|id| (*id, 0)).collect(),
            d329_hits: D329_NINE_IDS.iter().map(|id| (*id, 0)).collect(),
            ..Self::default()
        }
    }

    /// Ingest one free-standing text: no paragraph style, so the unknown
    /// tail applies (`ingest_text` is never a ProviderComment path).
    pub fn ingest_text(&mut self, text: &str) {
        self.ingest_lexed(text, true);
    }

    /// Ingest decoded blocks; ProviderComment blocks still feed kind /
    /// abbrev / D329 / shape / marker counting but never mint unknown-tail
    /// candidates (the `rank_unknown_forms` suppression pattern).
    /// `family_split` is file accounting (`note_file`); per-family block
    /// routing belongs to the T02 walker.
    pub fn ingest_blocks(&mut self, family: &str, blocks: &[ParsedBlock]) {
        let _ = family;
        for block in blocks {
            let allow_unknown_tail = block.style() != ParagraphStyle::ProviderComment;
            self.ingest_lexed(block.text(), allow_unknown_tail);
        }
    }

    /// File accounting for the walker: decoded/failed split per family.
    /// T01 tests call this directly; the T02 walker is its only producer.
    pub fn note_file(&mut self, family: &str, decoded: bool) {
        self.files_seen += 1;
        let counts = self.family_split.entry(family.to_owned()).or_default();
        counts.seen += 1;
        if decoded {
            self.files_decoded += 1;
            counts.decoded += 1;
        } else {
            self.files_failed += 1;
            counts.failed += 1;
        }
    }

    /// Render the closed-schema aggregate: exactly eight JSON objects, one
    /// per line, in fixed `record_kind` order. Hand-rolled (D328/D353), no
    /// raw sentence survives as a string value (Q3).
    pub fn render_jsonl(&self) -> String {
        let mut out = String::with_capacity(4096);
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"header\",\"schema\":{},\"schema_version\":{},",
                "\"cycle\":{},\"lifecycle\":\"[bounded]\",",
                "\"decoder\":\"ConsultantWordMlBlockDecoder\",",
                "\"lexer\":\"ln_decode::lexer::lex\",\"crate\":\"ln-decode\",",
                "\"family_format\":\"consultant-wordml-xml\",",
                "\"non_claims\":[\"official-publication\",\"R070\",\"LawRef\",\"N2-gate\"]}}"
            ),
            quote(SWEEP_SCHEMA),
            SWEEP_SCHEMA_VERSION,
            quote(&self.cycle),
        );
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"totals\",\"files_seen\":{},\"files_decoded\":{},",
                "\"files_failed\":{},\"word_tokens\":{},\"marker_hits\":{},",
                "\"marker_coverage_ppm\":{}}}"
            ),
            self.files_seen,
            self.files_decoded,
            self.files_failed,
            self.word_tokens,
            self.marker_hits,
            self.marker_coverage_ppm(),
        );
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"kind_hist\",{}}}",
            id_pairs(KIND_ORDER.iter().map(|kind| kind.as_str()), |name| {
                self.kind_count(
                    KIND_ORDER
                        .iter()
                        .copied()
                        .find(|kind| kind.as_str() == name)
                        .expect("closed TokenKind set"),
                )
            }),
        );
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"abbrev_hits\",{}}}",
            id_pairs(SWEEP_ABBREV_IDS, |id| self.abbrev_hit(id)),
        );
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"d329\",{}}}",
            id_pairs(D329_NINE_IDS, |id| self.d329_hit(id)),
        );
        let shapes = self.shapes;
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"shapes\",\"hier_num\":{},\"date\":{},\"doc_no\":{},",
                "\"enum_marker\":{},\"law_code\":{},\"doc_no_fz\":{},\"doc_no_fkz\":{},",
                "\"hier_seg2\":{},\"hier_seg3plus\":{}}}"
            ),
            shapes.hier_num,
            shapes.date,
            shapes.doc_no,
            shapes.enum_marker,
            shapes.law_code,
            shapes.doc_no_fz,
            shapes.doc_no_fkz,
            shapes.hier_seg2,
            shapes.hier_seg3plus,
        );
        let table: String = self
            .unknown_tail_ranked()
            .iter()
            .take(UNKNOWN_TAIL_CAP)
            .map(|entry| {
                format!(
                    "{{\"id\":{},\"lexeme\":{},\"count\":{}}}",
                    quote(&entry.id),
                    quote(&entry.lexeme),
                    entry.count
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        // One table, two views: `abbrev_candidate_census` is an alias of the
        // same ranked rows, never a second ranking (D352/D354).
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"unknown_tail\",\"cap\":{},",
                "\"entries\":[{}],\"abbrev_candidate_census\":[{}]}}"
            ),
            UNKNOWN_TAIL_CAP, table, table,
        );
        let mut families = String::new();
        for (family, counts) in &self.family_split {
            let _ = write!(
                families,
                ",{}:{{\"seen\":{},\"decoded\":{},\"failed\":{}}}",
                quote(family),
                counts.seen,
                counts.decoded,
                counts.failed
            );
        }
        let _ = writeln!(out, "{{\"record_kind\":\"family_split\"{families}}}");
        out
    }

    /// Closed-key reader over rendered output: every line must parse as one
    /// JSON object, carry a known `record_kind`, and stay inside that
    /// record's key allowlist (family names are corpus data, not schema).
    /// Any unexpected key fails closed.
    pub fn validate_jsonl(output: &str) -> Result<(), String> {
        for (index, line) in output.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let parsed = scan_jsonl_line(line)
                .map_err(|err| format!("npa-corpus-sweep line {}: {err}", index + 1))?;
            let Some(record_kind) = parsed.record_kind.as_deref() else {
                return Err(format!(
                    "npa-corpus-sweep line {}: missing record_kind",
                    index + 1
                ));
            };
            for key in &parsed.keys {
                let allowed = match record_kind {
                    "header" => HEADER_KEYS.contains(&key.as_str()),
                    "totals" => TOTALS_KEYS.contains(&key.as_str()),
                    "kind_hist" => {
                        key == "record_kind" || KIND_ORDER.iter().any(|kind| kind.as_str() == key)
                    }
                    "abbrev_hits" => {
                        key == "record_kind" || SWEEP_ABBREV_IDS.contains(&key.as_str())
                    }
                    "d329" => key == "record_kind" || D329_NINE_IDS.contains(&key.as_str()),
                    "shapes" => SHAPE_KEYS.contains(&key.as_str()),
                    "unknown_tail" => UNKNOWN_TAIL_KEYS.contains(&key.as_str()),
                    // Family keys are corpus data, not schema: any key is
                    // allowed, but the line still had to parse as JSON above.
                    "family_split" => true,
                    other => {
                        return Err(format!(
                            "npa-corpus-sweep line {}: unknown record_kind '{other}'",
                            index + 1
                        ))
                    }
                };
                if !allowed {
                    return Err(format!(
                        "npa-corpus-sweep line {}: unexpected key '{key}' for record_kind '{record_kind}'",
                        index + 1
                    ));
                }
            }
        }
        Ok(())
    }

    pub fn kind_count(&self, kind: TokenKind) -> u64 {
        self.kind_hist[kind_index(kind)]
    }

    pub fn abbrev_hit(&self, id: &str) -> u64 {
        self.abbrev_hits.get(id).copied().unwrap_or(0)
    }

    pub fn d329_hit(&self, id: &str) -> u64 {
        self.d329_hits.get(id).copied().unwrap_or(0)
    }

    /// Full ranked unknown-tail table (count desc, original lexeme asc);
    /// rendering caps it at [`UNKNOWN_TAIL_CAP`].
    pub fn unknown_tail_ranked(&self) -> Vec<UnknownTailEntry> {
        let mut entries: Vec<UnknownTailEntry> = self
            .unknown_tail
            .iter()
            .map(|(lexeme, count)| UnknownTailEntry {
                id: fingerprint_bytes(lexeme.as_bytes()),
                lexeme: lexeme.clone(),
                count: *count,
            })
            .collect();
        entries.sort_by(|a, b| b.count.cmp(&a.count).then_with(|| a.lexeme.cmp(&b.lexeme)));
        entries
    }

    pub fn files_seen(&self) -> u64 {
        self.files_seen
    }

    pub fn files_decoded(&self) -> u64 {
        self.files_decoded
    }

    pub fn files_failed(&self) -> u64 {
        self.files_failed
    }

    pub fn word_tokens(&self) -> u64 {
        self.word_tokens
    }

    pub fn marker_hits(&self) -> u64 {
        self.marker_hits
    }

    /// Integer-only coverage (D353): marker hits per million Word tokens,
    /// denominator floored at 1 so empty sweeps stay divide-free.
    pub fn marker_coverage_ppm(&self) -> u64 {
        1_000_000_u64.saturating_mul(self.marker_hits) / self.word_tokens.max(1)
    }

    /// Single counting path over one text: lex + markers + all censuses.
    fn ingest_lexed(&mut self, text: &str, allow_unknown_tail: bool) {
        let tokens = lexer::lex(text);
        self.marker_hits += morphology::find_legal_markers(text).len() as u64;
        for (index, token) in tokens.iter().enumerate() {
            self.kind_hist[kind_index(token.kind)] += 1;
            let lexeme = token.lexeme(text);
            match token.kind {
                TokenKind::Word => {
                    self.word_tokens += 1;
                    if allow_unknown_tail
                        && is_short_cyrillic(lexeme)
                        && tokens.get(index + 1).is_some_and(|next| {
                            next.kind == TokenKind::Punct && next.lexeme(text).starts_with('.')
                        })
                    {
                        *self.unknown_tail.entry(lexeme.to_owned()).or_insert(0) += 1;
                    }
                }
                TokenKind::Abbrev => {
                    if let Some(id) = token.abbrev_id {
                        if let Some(count) = self.abbrev_hits.get_mut(id.as_str()) {
                            *count += 1;
                        }
                        if D329_NINE_IDS.contains(&id.as_str()) {
                            let count = self
                                .d329_hits
                                .get_mut(id.as_str())
                                .expect("D329 table is seeded with the nine ids");
                            *count += 1;
                        }
                    }
                }
                TokenKind::HierNum => {
                    self.shapes.hier_num += 1;
                    match hier_segment_count(lexeme) {
                        2 => self.shapes.hier_seg2 += 1,
                        3.. => self.shapes.hier_seg3plus += 1,
                        _ => {}
                    }
                }
                TokenKind::Date => self.shapes.date += 1,
                TokenKind::DocNo => {
                    self.shapes.doc_no += 1;
                    if lexeme.ends_with("ФЗ") {
                        self.shapes.doc_no_fz += 1;
                    }
                    if lexeme.ends_with("ФКЗ") {
                        self.shapes.doc_no_fkz += 1;
                    }
                }
                TokenKind::EnumMarker => self.shapes.enum_marker += 1,
                TokenKind::LawCode => self.shapes.law_code += 1,
                TokenKind::Punct | TokenKind::Space => {}
            }
        }
    }
}

/// Module-level alias over the closed-key reader: contract tests render via
/// `SweepAcc::render_jsonl` and validate without naming the accumulator type.
pub fn validate_jsonl(output: &str) -> Result<(), String> {
    SweepAcc::validate_jsonl(output)
}

/// Pure family router: the first path component under `exports/` decides the
/// family (`npa` / `xml` / `courts` / `fas`), anything else — including a
/// missing `exports/` segment — is `other`. No filesystem access.
pub fn family_from_path(path: &Path) -> &'static str {
    let mut under_exports = false;
    for component in path.components() {
        let Component::Normal(name) = component else {
            continue;
        };
        let name = name.to_string_lossy();
        if under_exports {
            return match name.as_ref() {
                "npa" => "npa",
                "xml" => "xml",
                "courts" => "courts",
                "fas" => "fas",
                _ => "other",
            };
        }
        if name == "exports" {
            under_exports = true;
        }
    }
    "other"
}

/// Fixed reader allowlists (closed schemas, D353).
const HEADER_KEYS: [&str; 10] = [
    "record_kind",
    "schema",
    "schema_version",
    "cycle",
    "lifecycle",
    "decoder",
    "lexer",
    "crate",
    "family_format",
    "non_claims",
];
const TOTALS_KEYS: [&str; 7] = [
    "record_kind",
    "files_seen",
    "files_decoded",
    "files_failed",
    "word_tokens",
    "marker_hits",
    "marker_coverage_ppm",
];
const SHAPE_KEYS: [&str; 10] = [
    "record_kind",
    "hier_num",
    "date",
    "doc_no",
    "enum_marker",
    "law_code",
    "doc_no_fz",
    "doc_no_fkz",
    "hier_seg2",
    "hier_seg3plus",
];
const UNKNOWN_TAIL_KEYS: [&str; 4] = ["record_kind", "cap", "entries", "abbrev_candidate_census"];

fn kind_index(kind: TokenKind) -> usize {
    KIND_ORDER
        .iter()
        .position(|candidate| *candidate == kind)
        .expect("closed TokenKind set")
}

fn id_pairs(ids: impl IntoIterator<Item = &'static str>, count_of: impl Fn(&str) -> u64) -> String {
    ids.into_iter()
        .map(|id| format!("\"{}\":{}", id, count_of(id)))
        .collect::<Vec<_>>()
        .join(",")
}

/// D352 predicate: 1..=6 Cyrillic letters (either case), nothing else.
fn is_short_cyrillic(lexeme: &str) -> bool {
    let mut letters = 0usize;
    for ch in lexeme.chars() {
        if !matches!(ch, 'а'..='я' | 'А'..='Я' | 'Ё' | 'ё') {
            return false;
        }
        letters += 1;
        if letters > 6 {
            return false;
        }
    }
    letters > 0
}

/// ASCII-digit runs separated by `.`: `15.1` is 2 segments, `1.1.1` is 3+.
fn hier_segment_count(lexeme: &str) -> usize {
    lexeme
        .split('.')
        .filter(|segment| !segment.is_empty())
        .count()
}

/// Minimal JSON string escaper for the hand-rolled writer: quotes, backslash
/// and control characters only; legal UTF-8 passes through verbatim.
fn quote(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", ch as u32);
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

/// Top-level keys of one JSON object line, plus its `record_kind` if present.
struct LineKeys {
    keys: Vec<String>,
    record_kind: Option<String>,
}

/// Char cursor for the closed-key reader (stdlib only, D328 pattern).
struct Cursor<'a> {
    src: std::str::Chars<'a>,
}

impl Cursor<'_> {
    fn peek(&mut self) -> Option<char> {
        self.src.clone().next()
    }

    fn bump(&mut self) -> Option<char> {
        self.src.next()
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(' ') | Some('\t') | Some('\r')) {
            self.bump();
        }
    }

    fn expect(&mut self, want: char) -> Result<(), String> {
        match self.bump() {
            Some(ch) if ch == want => Ok(()),
            other => Err(format!("expected '{want}', found {other:?}")),
        }
    }

    fn read_string(&mut self) -> Result<String, String> {
        self.expect('"')?;
        let mut value = String::new();
        loop {
            match self.bump() {
                None => return Err("unterminated JSON string".to_owned()),
                Some('"') => return Ok(value),
                Some('\\') => match self.bump() {
                    Some('n') => value.push('\n'),
                    Some('t') => value.push('\t'),
                    Some('r') => value.push('\r'),
                    Some('b') => value.push('\u{8}'),
                    Some('f') => value.push('\u{c}'),
                    Some('/') | Some('\\') | Some('"') => {}
                    Some('u') => {
                        for _ in 0..4 {
                            self.bump();
                        }
                    }
                    other => return Err(format!("bad JSON escape {other:?}")),
                },
                Some(ch) => value.push(ch),
            }
        }
    }

    fn read_word(&mut self) -> Result<String, String> {
        let mut word = String::new();
        while matches!(self.peek(), Some(ch) if ch.is_ascii_alphabetic()) {
            word.push(self.bump().expect("peeked char"));
        }
        if word.is_empty() {
            return Err("expected a JSON literal".to_owned());
        }
        Ok(word)
    }

    fn expect_literal(&mut self, want: &str) -> Result<(), String> {
        let word = self.read_word()?;
        if word == want {
            Ok(())
        } else {
            Err(format!("bad JSON literal '{word}'"))
        }
    }

    fn skip_value(&mut self) -> Result<(), String> {
        self.skip_ws();
        match self.peek() {
            Some('"') => self.read_string().map(|_| ()),
            Some('{') => {
                self.bump();
                self.skip_container('}', true)
            }
            Some('[') => {
                self.bump();
                self.skip_container(']', false)
            }
            Some('-') | Some('0'..='9') => {
                while matches!(self.peek(), Some(ch) if ch.is_ascii_digit() || matches!(ch, '-' | '+' | '.' | 'e' | 'E'))
                {
                    self.bump();
                }
                Ok(())
            }
            Some('t') => self.expect_literal("true"),
            Some('f') => self.expect_literal("false"),
            Some('n') => self.expect_literal("null"),
            other => Err(format!("unexpected JSON value start {other:?}")),
        }
    }

    fn skip_container(&mut self, close: char, is_object: bool) -> Result<(), String> {
        self.skip_ws();
        if self.peek() == Some(close) {
            self.bump();
            return Ok(());
        }
        loop {
            self.skip_ws();
            if is_object {
                self.read_string()?;
                self.skip_ws();
                self.expect(':')?;
                self.skip_value()?;
            } else if self.peek() == Some(close) {
                self.bump();
                return Ok(());
            } else {
                self.skip_value()?;
            }
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some(ch) if ch == close => return Ok(()),
                other => return Err(format!("expected ',' or '{close}', found {other:?}")),
            }
        }
    }
}

fn scan_jsonl_line(line: &str) -> Result<LineKeys, String> {
    let mut cursor = Cursor { src: line.chars() };
    cursor.skip_ws();
    cursor.expect('{')?;
    let mut keys = Vec::new();
    let mut record_kind = None;
    cursor.skip_ws();
    if cursor.peek() == Some('}') {
        cursor.bump();
        if cursor.bump().is_some() {
            return Err("trailing content after object".to_owned());
        }
        return Ok(LineKeys { keys, record_kind });
    }
    loop {
        cursor.skip_ws();
        let key = cursor.read_string()?;
        keys.push(key.clone());
        cursor.skip_ws();
        cursor.expect(':')?;
        if key == "record_kind" {
            cursor.skip_ws();
            let value = cursor
                .read_string()
                .map_err(|_| "record_kind must be a string".to_owned())?;
            record_kind = Some(value);
        } else {
            cursor.skip_value()?;
        }
        cursor.skip_ws();
        match cursor.bump() {
            Some(',') => continue,
            Some('}') => break,
            other => return Err(format!("expected ',' or '}}', found {other:?}")),
        }
    }
    if cursor.bump().is_some() {
        return Err("trailing content after object".to_owned());
    }
    Ok(LineKeys { keys, record_kind })
}

// ---------------------------------------------------------------------------
// T02: measurement plumbing around the accumulator — deterministic `std::fs`
// XML walk, bounded per-file payload identity, per-file decode+ingest, and
// the library-level runner the thin `npa-corpus-sweep` binary wires up.
// Stdlib only: no walkdir, no rayon, no clap, no serde. The binary itself is
// argv + printing; everything observable lives here so contract tests
// exercise library functions instead of shelling out as their only contour.
// ---------------------------------------------------------------------------

/// Exit code: walk completed. Per-file read/decode failures are counted in
/// `files_failed`, never fatal; the default-root-absent skip-mode also
/// finishes with this code and a zeroed aggregate.
pub const EXIT_OK: u8 = 0;
/// Exit code: usage error — unknown flag, positional argument, missing or
/// garbled flag value.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: `--out` could not be opened for writing.
pub const EXIT_OUT_UNWRITABLE: u8 = 3;
/// Exit code: an explicit `--root` was given but does not exist or is not a
/// directory (the skip-mode default root never takes this path).
pub const EXIT_ROOT_MISSING: u8 = 4;
/// Exit code: the walk itself failed on the filesystem (e.g. an unreadable
/// directory). Per-file failures never take this path.
pub const EXIT_WALK_FAILED: u8 = 5;

/// Parsed argv of the `npa-corpus-sweep` binary — stdlib only, no clap.
/// Lives in the domain module (not the bin) so the CLI contract is testable
/// as a library function.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SweepCli {
    /// Explicit sweep root (an existing tree of `*.xml`). `None` resolves
    /// the default export root, where absence is skip-mode.
    pub root: Option<String>,
    /// Aggregate output path; `None` sends the JSONL to stdout.
    pub out: Option<String>,
    /// Cap on XML files, applied after the deterministic sort; `0` is a
    /// valid empty walk.
    pub limit: Option<u64>,
    /// Verbatim header cycle label; defaults to `C1`.
    pub cycle: String,
}

impl Default for SweepCli {
    fn default() -> Self {
        Self {
            root: None,
            out: None,
            limit: None,
            cycle: "C1".to_owned(),
        }
    }
}

/// Strict stdlib argv parser: `--root`, `--out`, `--limit`, `--cycle`, each
/// with a following value; later occurrences override earlier ones. Unknown
/// flags, positionals, missing values, and non-numeric limits are usage
/// errors.
pub fn parse_args<I>(args: I) -> Result<SweepCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = SweepCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--cycle" => cli.cycle = next_value(&mut iter, "--cycle")?,
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                let parsed = raw
                    .parse::<u64>()
                    .map_err(|_| format!("--limit expects a non-negative integer, got '{raw}'"))?;
                cli.limit = Some(parsed);
            }
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// `CONSULTANT_EXPORT_DIR` with empty-as-unset semantics (M185 S03):
/// unset, empty, or whitespace-only falls back to `consru_export`. Pure over
/// the env value so contract tests pin it without touching process env.
pub fn resolve_export_dir(env_value: Option<&str>) -> String {
    match env_value {
        Some(value) if !value.trim().is_empty() => value.to_owned(),
        _ => "consru_export".to_owned(),
    }
}

/// Default sweep universe for the binary: `<repo>/<export-dir>/consru_export/
/// exports` (nested MEM1319 layout), resolved from the compile-time crate
/// dir — the same `CARGO_MANIFEST_DIR/../..` join the tracked corpus tests
/// use. Never `law-source/consultant/`.
pub fn default_sweep_root() -> PathBuf {
    let env_value = std::env::var("CONSULTANT_EXPORT_DIR").ok();
    let export_dir = resolve_export_dir(env_value.as_deref());
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join(export_dir)
        .join("consru_export")
        .join("exports")
}

/// Deterministic XML walk over `root`: recursive `std::fs::read_dir` with
/// entries sorted at every level, only `*.xml` kept (case-insensitive
/// extension), everything else skipped. `limit` truncates AFTER the final
/// full-path sort, so the cut is independent of tree shape. Directory
/// read/stat errors propagate (`EXIT_WALK_FAILED` at the runner); per-file
/// read/decode failures are the accumulator's accounting, not the walker's.
pub fn walk_xml_files(root: &Path, limit: Option<u64>) -> std::io::Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    collect_xml_files(root, &mut files)?;
    files.sort();
    if let Some(limit) = limit {
        let keep = usize::try_from(limit)
            .unwrap_or(usize::MAX)
            .min(files.len());
        files.truncate(keep);
    }
    Ok(files)
}

fn collect_xml_files(dir: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    let mut entries: Vec<PathBuf> = Vec::new();
    for entry in fs::read_dir(dir)? {
        entries.push(entry?.path());
    }
    entries.sort();
    for path in entries {
        // symlink_metadata keeps symlinks leaves, so a cyclic link cannot
        // make the walk recurse forever.
        if fs::symlink_metadata(&path)?.is_dir() {
            collect_xml_files(&path, files)?;
        } else if is_xml_path(&path) {
            files.push(path);
        }
    }
    Ok(())
}

/// Case-insensitive `*.xml` gate; `.txt`/`.odt` (Garant) and everything
/// else is skipped.
fn is_xml_path(path: &Path) -> bool {
    path.extension()
        .and_then(|ext| ext.to_str())
        .is_some_and(|ext| ext.eq_ignore_ascii_case("xml"))
}

/// Bounded payload identity for one corpus file (Q3): a stem of at most 56
/// ASCII `[-_:.0-9A-Za-z]` bytes keeps its `payload:<stem>` ref (the
/// `payload:` prefix must still fit `PayloadRef::parse`'s 64-char cap);
/// anything else — long corpus stems, non-ASCII, empty — falls back to
/// `sw:` plus the hex tail of the FNV-1a fingerprint over the path bytes
/// (19 chars, always inside the cap, never raw path text).
pub fn payload_ref_for_path(path: &Path) -> PayloadRef {
    if let Some(stem) = path.file_stem().and_then(|stem| stem.to_str()) {
        if !stem.is_empty() && stem.bytes().all(is_ref_stem_byte) {
            if let Ok(id) = PayloadRef::parse(&format!("payload:{stem}")) {
                return id;
            }
        }
    }
    let fingerprint = fingerprint_bytes(path.as_os_str().as_encoded_bytes());
    let hex_tail = fingerprint.strip_prefix("fnv1a64:").unwrap_or(&fingerprint);
    PayloadRef::parse(&format!("sw:{hex_tail}")).expect("sw ref fits the 64-char cap")
}

fn is_ref_stem_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b':' | b'.')
}

/// Decode one corpus file and feed the accumulator. A read failure and a
/// decode failure are the same accounting — `note_file(family, false)` —
/// and the walk continues: one broken file never aborts the corpus and
/// never puts payload bytes or block text into the aggregate or stderr
/// (Q3/Q7). Garant ODT is outside the sweep universe by construction: the
/// walker only takes `*.xml`, and the decoder is pinned to
/// `family:consultant-wordml`, so a wrong family never reaches
/// [`ConsultantWordMlBlockDecoder`].
pub fn ingest_file(acc: &mut SweepAcc, path: &Path) {
    let family = family_from_path(path);
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(_) => {
            acc.note_file(family, false);
            return;
        }
    };
    let request = DecodeRequest::new(
        payload_ref_for_path(path),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        &bytes,
    );
    match ConsultantWordMlBlockDecoder.decode_blocks(&request) {
        Ok(blocks) => {
            acc.note_file(family, true);
            acc.ingest_blocks(family, &blocks);
        }
        Err(_) => acc.note_file(family, false),
    }
}

/// Everything the thin binary prints and exits with after one run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SweepRun {
    pub exit_code: u8,
    /// Rendered aggregate; `None` on fatal error paths (nothing to print).
    pub jsonl: Option<String>,
    /// `true` when `jsonl` belongs on stdout (no usable `--out`).
    pub to_stdout: bool,
    /// Counts line or failure note for stderr — counts and paths only,
    /// never payload bytes or block text (Q3).
    pub stderr: String,
}

/// Library-level sweep runner: exactly what the binary does after argv
/// parsing. `default_root` is injected so tests never touch the live
/// `consru_export` corpus; the binary passes [`default_sweep_root`].
pub fn run_sweep(cli: &SweepCli, default_root: &Path) -> SweepRun {
    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());

    if !root.is_dir() {
        if explicit {
            return SweepRun {
                exit_code: EXIT_ROOT_MISSING,
                jsonl: None,
                to_stdout: false,
                stderr: format!("root not found: {}", root.display()),
            };
        }
        // Skip-mode: a checkout without the export still completes with a
        // closed-schema zeroed aggregate (the corpus_role skip pattern).
        return SweepRun {
            exit_code: EXIT_OK,
            jsonl: Some(SweepAcc::new(cli.cycle.as_str()).render_jsonl()),
            to_stdout: true,
            stderr: format!("skip: default corpus root absent: {}", root.display()),
        };
    }

    let files = match walk_xml_files(&root, cli.limit) {
        Ok(files) => files,
        Err(err) => {
            return SweepRun {
                exit_code: EXIT_WALK_FAILED,
                jsonl: None,
                to_stdout: false,
                stderr: format!("walk failed: {err}"),
            };
        }
    };

    let mut acc = SweepAcc::new(cli.cycle.as_str());
    for path in &files {
        ingest_file(&mut acc, path);
    }
    let stderr = format!(
        "files_seen={} files_decoded={} files_failed={} word_tokens={} marker_hits={}",
        acc.files_seen(),
        acc.files_decoded(),
        acc.files_failed(),
        acc.word_tokens(),
        acc.marker_hits(),
    );
    match &cli.out {
        None => SweepRun {
            exit_code: EXIT_OK,
            jsonl: Some(acc.render_jsonl()),
            to_stdout: true,
            stderr,
        },
        Some(out_path) => match fs::write(out_path, acc.render_jsonl()) {
            Ok(()) => SweepRun {
                exit_code: EXIT_OK,
                jsonl: None,
                to_stdout: false,
                stderr,
            },
            Err(err) => SweepRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                jsonl: None,
                to_stdout: false,
                stderr: format!("cannot open --out {}: {err}", out_path),
            },
        },
    }
}
