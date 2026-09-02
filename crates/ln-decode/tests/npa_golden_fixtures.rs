//! Load test for NPA golden reference fixtures (M197 S01).
//!
//! The fixture set under `tests/fixtures/npa/` carries decoded reference
//! fragments from the tracked Consultant 44-ФЗ WordML (`ConsultantWordMlBlockDecoder`
//! harvest; never a naive `w:t` join). The sidecar `fz44_npa_tokens.json` pins
//! the expected `TokenKind` + UTF-8 byte span markup; the `.txt` files are the
//! span coordinate system (lexemes are reconstructed as `text[start..end]`,
//! never duplicated into the JSON).
//!
//! This is fixture infrastructure only (S01 is a data slice):
//! - it never calls the private `tokenizer` module (typed lexer is S02);
//! - it never decodes the 5.2 MB source XML (provenance is pinned by path +
//!   sha256 + byte length checked against `fs::metadata` only);
//! - stdlib only — hand-rolled JSON parser (D328; no serde in the workspace).
//!
//! D330 marking rules, frozen here so two executors cannot mark `15.1` or
//! `пп.` differently:
//! 1. `Abbrev` consumes its trailing dot: `ст.` is one token (`id: st`);
//!    `пп.` is ONE token (`id: pp`), never two `п` tokens.
//! 2. `HierNum` is the longest `\d+(\.\d+)+` run (`15.1`, `2.3.1`) — one token.
//! 3. `Date` is `dd.mm.yyyy` with plausible day/month and beats `HierNum` on
//!    that shape (`01.01.2028` is never HierNum).
//! 4. Undotted digit runs (`16`, `2028`) are `Word`, not HierNum.
//! 5. Headings `Глава 1.` / `Статья 16.` are `Word + Space + Word + Punct`
//!    (not HierNum, not EnumMarker).
//! 6. `EnumMarker` is the list marker as typed, without surrounding quotes
//!    (`1)`, `1.`, `а)`; a quoted subpoint label `п "а"` = Punct + EnumMarker
//!    + Punct).
//! 7. `Space` is contiguous Unicode whitespace (NBSP included when the
//!    decoder emits it).
//! 8. `Punct` is everything else non-alphanumeric.
//! 9. `Word` is an alphabetic run (plus undotted digit runs); no lowercasing
//!    in fixtures.
//! 10. Latin `N` in `N 44-ФЗ` is Word, `44-ФЗ` is DocNo, lone `ФЗ`/`ФКЗ` is
//!     LawCode.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::domain::TextSpan;

const SOURCE_RELATIVE_PATH: &str = "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml";
const SOURCE_SHA256: &str = "c111119c6c3001b5b4fde0e35bffbe382bcb877df2bba9cd54ab0290c92c1b14";
const SOURCE_BYTES: u64 = 5_262_136;
const SOURCE_DECODER: &str = "ConsultantWordMlBlockDecoder";
const TOKENS_MANIFEST: &str = "fz44_npa_tokens.json";
const MANIFEST_SCHEMA_VERSION: usize = 1;
const MANIFEST_LIFECYCLE: &str = "[bounded]";

/// Closed TokenKind vocab (ADR-0028 step-1 list). `Editorial` is a wave-2
/// kind and must fail the loader closed in S01.
const TOKEN_KINDS: [&str; 9] = [
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

/// Closed Abbrev id vocab (ADR-0028 lexicon). The table may carry ids with
/// zero corpus hits (S02 keeps them as synthetic unit-test cases), but corpus
/// fragments (`note_kind != synthetic`) must never use the D329 subset below.
const ABBREV_IDS: [&str; 17] = [
    "st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd", "pril", "prim", "red", "izm",
    "utv", "sm", "sr", "g",
];

/// D329: zero hits in the tracked 44-ФЗ — corpus goldens must not mint them.
const CORPUS_FORBIDDEN_ABBREV_IDS: [&str; 9] = [
    "gl", "razd", "podp", "abz", "pril", "prim", "stst", "utv", "sr",
];

/// Canonical Abbrev lexemes: an Abbrev token consumes its trailing dot, so
/// `id: st` must slice exactly `ст.` (this rejects a split `пп.`).
const ABBREV_CANONICAL_LEXEMES: [(&str, &str); 17] = [
    ("st", "ст."),
    ("stst", "ст.ст."),
    ("ch", "ч."),
    ("p", "п."),
    ("pp", "пп."),
    ("podp", "подп."),
    ("abz", "абз."),
    ("gl", "гл."),
    ("razd", "разд."),
    ("pril", "прил."),
    ("prim", "прим."),
    ("red", "ред."),
    ("izm", "изм."),
    ("utv", "утв."),
    ("sm", "см."),
    ("sr", "ср."),
    ("g", "г."),
];

/// Corpus bucket vocab. Quota minimums arrive as load-test assertions in
/// T02/T03; T01 only fails closed on unknown buckets.
const CORPUS_BUCKETS: [&str; 8] = [
    "abbrev-hier",
    "date-docno",
    "enum-list",
    "heading",
    "fullword-ref",
    "lawcode",
    "dense-note",
    "misc-punct",
];

/// note_kind vocab for S01; `synthetic` arrives with the T03 collision pair.
const NOTE_KINDS: [&str; 2] = ["enacting", "provider_note"];

/// Honesty substrings every manifest must carry (R070 stays open).
const REQUIRED_NON_CLAIMS: [&str; 3] = ["official-publication", "LawRef", "legal interpretation"];

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn fixtures_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa")
}

// ---------------------------------------------------------------------------
// Hand-rolled JSON (D328: stdlib only, closed schema, fail-closed).
// ---------------------------------------------------------------------------

#[derive(Debug)]
enum Json {
    Null,
    Bool,
    Num(String),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

struct JsonParser<'a> {
    src: &'a str,
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(src: &'a str) -> Self {
        Self { src, pos: 0 }
    }

    fn err<T>(&self, message: impl std::fmt::Display) -> Result<T, String> {
        Err(format!("JSON parse error at byte {}: {message}", self.pos))
    }

    fn peek(&self) -> Option<char> {
        self.src[self.pos..].chars().next()
    }

    fn bump(&mut self) -> Option<char> {
        let ch = self.peek()?;
        self.pos += ch.len_utf8();
        Some(ch)
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(' ' | '\t' | '\n' | '\r')) {
            self.pos += 1;
        }
    }

    fn expect_char(&mut self, expected: char) -> Result<(), String> {
        self.skip_ws();
        match self.peek() {
            Some(ch) if ch == expected => {
                self.pos += ch.len_utf8();
                Ok(())
            }
            other => self.err(format!("expected '{expected}', found {other:?}")),
        }
    }

    fn parse_document(mut self) -> Result<Json, String> {
        let value = self.parse_value()?;
        self.skip_ws();
        if self.pos != self.src.len() {
            return self.err("trailing characters after JSON document");
        }
        Ok(value)
    }

    fn parse_value(&mut self) -> Result<Json, String> {
        self.skip_ws();
        match self.peek() {
            Some('{') => self.parse_object(),
            Some('[') => self.parse_array(),
            Some('"') => Ok(Json::Str(self.parse_string()?)),
            Some('t') => self.parse_literal("true", Json::Bool),
            Some('f') => self.parse_literal("false", Json::Bool),
            Some('n') => self.parse_literal("null", Json::Null),
            Some(ch) if ch == '-' || ch.is_ascii_digit() => self.parse_number(),
            other => self.err(format!("unexpected character {other:?}")),
        }
    }

    fn parse_literal(&mut self, literal: &str, value: Json) -> Result<Json, String> {
        if self.src[self.pos..].starts_with(literal) {
            self.pos += literal.len();
            Ok(value)
        } else {
            self.err(format!("invalid literal, expected {literal}"))
        }
    }

    fn parse_number(&mut self) -> Result<Json, String> {
        let start = self.pos;
        if self.peek() == Some('-') {
            self.pos += 1;
        }
        let mut digits = false;
        while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
            self.pos += 1;
            digits = true;
        }
        if !digits {
            return self.err("number without digits");
        }
        if self.peek() == Some('.') {
            self.pos += 1;
            let mut fraction = false;
            while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
                self.pos += 1;
                fraction = true;
            }
            if !fraction {
                return self.err("dangling decimal point");
            }
        }
        if matches!(self.peek(), Some('e' | 'E')) {
            self.pos += 1;
            if matches!(self.peek(), Some('+' | '-')) {
                self.pos += 1;
            }
            let mut exponent = false;
            while matches!(self.peek(), Some(ch) if ch.is_ascii_digit()) {
                self.pos += 1;
                exponent = true;
            }
            if !exponent {
                return self.err("dangling exponent");
            }
        }
        Ok(Json::Num(self.src[start..self.pos].to_owned()))
    }

    fn parse_string(&mut self) -> Result<String, String> {
        self.expect_char('"')?;
        let mut out = String::new();
        loop {
            match self.bump() {
                None => return self.err("unterminated string"),
                Some('"') => return Ok(out),
                Some('\\') => match self.bump() {
                    Some('"') => out.push('"'),
                    Some('\\') => out.push('\\'),
                    Some('/') => out.push('/'),
                    Some('b') => out.push('\u{0008}'),
                    Some('f') => out.push('\u{000C}'),
                    Some('n') => out.push('\n'),
                    Some('r') => out.push('\r'),
                    Some('t') => out.push('\t'),
                    Some('u') => {
                        let high = self.parse_hex4()?;
                        let code = if (0xD800..0xDC00).contains(&high) {
                            if self.peek() == Some('\\') {
                                self.pos += 1;
                                if self.peek() != Some('u') {
                                    return self.err("low surrogate missing");
                                }
                                self.pos += 1;
                                let low = self.parse_hex4()?;
                                if !(0xDC00..0xE000).contains(&low) {
                                    return self.err("invalid low surrogate");
                                }
                                0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)
                            } else {
                                return self.err("lone high surrogate");
                            }
                        } else if (0xDC00..0xE000).contains(&high) {
                            return self.err("lone low surrogate");
                        } else {
                            high
                        };
                        match char::from_u32(code) {
                            Some(decoded) => out.push(decoded),
                            None => return self.err("invalid unicode codepoint"),
                        }
                    }
                    other => return self.err(format!("invalid escape {other:?}")),
                },
                Some(ch) if (ch as u32) < 0x20 => {
                    return self.err("raw control character in string");
                }
                Some(ch) => out.push(ch),
            }
        }
    }

    fn parse_hex4(&mut self) -> Result<u32, String> {
        let mut value: u32 = 0;
        for _ in 0..4 {
            let digit = match self.bump() {
                Some(ch @ '0'..='9') => ch as u32 - '0' as u32,
                Some(ch @ 'a'..='f') => ch as u32 - 'a' as u32 + 10,
                Some(ch @ 'A'..='F') => ch as u32 - 'A' as u32 + 10,
                other => return self.err(format!("invalid \\u escape digit {other:?}")),
            };
            value = value * 16 + digit;
        }
        Ok(value)
    }

    fn parse_object(&mut self) -> Result<Json, String> {
        self.expect_char('{')?;
        let mut pairs: Vec<(String, Json)> = Vec::new();
        self.skip_ws();
        if self.peek() == Some('}') {
            self.pos += 1;
            return Ok(Json::Obj(pairs));
        }
        loop {
            self.skip_ws();
            if self.peek() != Some('"') {
                return self.err("object key must be a string");
            }
            let key = self.parse_string()?;
            self.expect_char(':')?;
            let value = self.parse_value()?;
            if pairs.iter().any(|(existing, _)| existing == &key) {
                return Err(format!("duplicate JSON object key '{key}'"));
            }
            pairs.push((key, value));
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some('}') => return Ok(Json::Obj(pairs)),
                other => return self.err(format!("expected ',' or '}}', found {other:?}")),
            }
        }
    }

    fn parse_array(&mut self) -> Result<Json, String> {
        self.expect_char('[')?;
        let mut items = Vec::new();
        self.skip_ws();
        if self.peek() == Some(']') {
            self.pos += 1;
            return Ok(Json::Arr(items));
        }
        loop {
            items.push(self.parse_value()?);
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some(']') => return Ok(Json::Arr(items)),
                other => return self.err(format!("expected ',' or ']', found {other:?}")),
            }
        }
    }
}

impl Json {
    fn obj(&self) -> Result<&[(String, Json)], String> {
        match self {
            Json::Obj(pairs) => Ok(pairs),
            other => Err(format!("expected JSON object, found {other:?}")),
        }
    }

    fn get(&self, key: &str) -> Result<&Json, String> {
        self.obj()?
            .iter()
            .find(|(existing, _)| existing == key)
            .map(|(_, value)| value)
            .ok_or_else(|| format!("missing JSON field '{key}'"))
    }

    fn get_opt(&self, key: &str) -> Result<Option<&Json>, String> {
        Ok(self
            .obj()?
            .iter()
            .find(|(existing, _)| existing == key)
            .map(|(_, value)| value))
    }

    fn require_keys(&self, allowed: &[&str], context: &str) -> Result<(), String> {
        for (key, _) in self.obj()? {
            if !allowed.contains(&key.as_str()) {
                return Err(format!("{context}: unexpected JSON key '{key}'"));
            }
        }
        Ok(())
    }

    fn as_str(&self) -> Result<&str, String> {
        match self {
            Json::Str(value) => Ok(value),
            other => Err(format!("expected JSON string, found {other:?}")),
        }
    }

    fn as_arr(&self) -> Result<&[Json], String> {
        match self {
            Json::Arr(items) => Ok(items),
            other => Err(format!("expected JSON array, found {other:?}")),
        }
    }

    fn as_usize(&self) -> Result<usize, String> {
        match self {
            Json::Num(raw) => raw
                .parse::<usize>()
                .map_err(|_| format!("expected non-negative integer, found '{raw}'")),
            other => Err(format!("expected integer, found {other:?}")),
        }
    }
}

// ---------------------------------------------------------------------------
// Fixture loader (fail-closed on schema, vocab, spans, covering, bijection).
// ---------------------------------------------------------------------------

#[derive(Debug)]
struct RawToken {
    kind: &'static str,
    id: Option<String>,
    start: usize,
    end: usize,
}

#[derive(Debug)]
struct LoadedFragment {
    id: String,
    file: String,
    source_block_index: usize,
    bucket: String,
    note_kind: String,
    text: String,
    spans: Vec<TextSpan>,
    kinds: Vec<&'static str>,
    abbrev_ids: Vec<Option<String>>,
    lexemes: Vec<String>,
}

fn count_corpus_fragments(fragments: &[LoadedFragment]) -> usize {
    fragments
        .iter()
        .filter(|fragment| fragment.note_kind != "synthetic")
        .count()
}

fn load_golden_fixtures(
    fixtures_dir: &Path,
    provenance_base: &Path,
) -> Result<Vec<LoadedFragment>, String> {
    let manifest_path = fixtures_dir.join(TOKENS_MANIFEST);
    let manifest_text = fs::read_to_string(&manifest_path)
        .map_err(|err| format!("read {}: {err}", manifest_path.display()))?;
    let mut files = BTreeMap::new();
    let entries = fs::read_dir(fixtures_dir)
        .map_err(|err| format!("read fixtures dir {}: {err}", fixtures_dir.display()))?;
    for entry in entries {
        let path = entry
            .map_err(|err| format!("fixtures dir entry: {err}"))?
            .path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("txt") {
            let name = path
                .file_name()
                .ok_or_else(|| format!("fixture path without file name: {}", path.display()))?
                .to_string_lossy()
                .into_owned();
            let content =
                fs::read_to_string(&path).map_err(|err| format!("read fixture '{name}': {err}"))?;
            files.insert(name, content);
        }
    }
    validate_fixture_set(&manifest_text, &files, Some(provenance_base))
}

fn validate_fixture_set(
    manifest_text: &str,
    files: &BTreeMap<String, String>,
    provenance_base: Option<&Path>,
) -> Result<Vec<LoadedFragment>, String> {
    let root = JsonParser::new(manifest_text).parse_document()?;
    root.require_keys(
        &["schema_version", "lifecycle", "source", "fragments"],
        "manifest",
    )?;

    let schema_version = root.get("schema_version")?.as_usize()?;
    if schema_version != MANIFEST_SCHEMA_VERSION {
        return Err(format!(
            "manifest schema_version {schema_version} != {MANIFEST_SCHEMA_VERSION}"
        ));
    }
    let lifecycle = root.get("lifecycle")?.as_str()?;
    if lifecycle != MANIFEST_LIFECYCLE {
        return Err(format!(
            "manifest lifecycle '{lifecycle}' != '{MANIFEST_LIFECYCLE}'"
        ));
    }

    let source = root.get("source")?;
    source.require_keys(&["path", "sha256", "decoder", "non_claims"], "source")?;
    let source_path = source.get("path")?.as_str()?;
    if source_path != SOURCE_RELATIVE_PATH {
        return Err(format!(
            "source.path '{source_path}' != pinned corpus path '{SOURCE_RELATIVE_PATH}'"
        ));
    }
    let source_sha256 = source.get("sha256")?.as_str()?;
    if source_sha256 != SOURCE_SHA256 {
        return Err("source.sha256 does not match the pinned corpus digest".to_string());
    }
    let decoder = source.get("decoder")?.as_str()?;
    if decoder != SOURCE_DECODER {
        return Err(format!("source.decoder '{decoder}' != '{SOURCE_DECODER}'"));
    }
    let non_claims = source.get("non_claims")?.as_arr()?;
    if non_claims.len() < REQUIRED_NON_CLAIMS.len() {
        return Err("source.non_claims must carry at least the three honesty claims".to_string());
    }
    for required in REQUIRED_NON_CLAIMS {
        if !non_claims
            .iter()
            .filter_map(|claim| claim.as_str().ok())
            .any(|claim| claim.contains(required))
        {
            return Err(format!("source.non_claims is missing '{required}'"));
        }
    }

    if let Some(base) = provenance_base {
        if source_sha256.len() != 64 || !source_sha256.bytes().all(|byte| byte.is_ascii_hexdigit())
        {
            return Err("source.sha256 must be a 64-char hex digest".to_string());
        }
        let xml = base.join(SOURCE_RELATIVE_PATH);
        let metadata = fs::metadata(&xml).map_err(|err| {
            format!("pinned corpus XML missing at '{SOURCE_RELATIVE_PATH}': {err}")
        })?;
        let actual = metadata.len();
        if actual != SOURCE_BYTES {
            return Err(format!(
                "pinned corpus XML is {actual} bytes, manifest pins {SOURCE_BYTES}"
            ));
        }
    }

    let fragment_entries = root.get("fragments")?.as_arr()?;
    if fragment_entries.is_empty() {
        return Err("manifest must declare at least one fragment".to_string());
    }

    let mut fragments = Vec::with_capacity(fragment_entries.len());
    let mut seen_ids = BTreeSet::new();
    let mut seen_files = BTreeSet::new();
    for (position, entry) in fragment_entries.iter().enumerate() {
        let fragment = validate_fragment(entry, position, files)?;
        if !seen_ids.insert(fragment.id.clone()) {
            return Err(format!("duplicate fragment id '{}'", fragment.id));
        }
        if !seen_files.insert(fragment.file.clone()) {
            return Err(format!("duplicate fragment file '{}'", fragment.file));
        }
        fragments.push(fragment);
    }

    for name in files.keys() {
        if !seen_files.contains(name) {
            return Err(format!("extra fixture file '{name}' has no manifest entry"));
        }
    }
    for file in &seen_files {
        if !files.contains_key(file) {
            return Err(format!(
                "manifest file '{file}' has no .txt fixture on disk"
            ));
        }
    }

    Ok(fragments)
}

fn validate_fragment(
    entry: &Json,
    position: usize,
    files: &BTreeMap<String, String>,
) -> Result<LoadedFragment, String> {
    let context = format!("fragments[{position}]");
    entry.require_keys(
        &[
            "id",
            "file",
            "source_block_index",
            "bucket",
            "note_kind",
            "tokens",
        ],
        &context,
    )?;
    let id = entry.get("id")?.as_str()?.to_owned();
    let file = entry.get("file")?.as_str()?.to_owned();
    let source_block_index = entry.get("source_block_index")?.as_usize()?;
    let bucket = entry.get("bucket")?.as_str()?.to_owned();
    let note_kind = entry.get("note_kind")?.as_str()?.to_owned();

    let context = format!("{context} (id '{id}')");
    if id.is_empty() {
        return Err(format!("{context}: empty fragment id"));
    }
    if !is_safe_fixture_file_name(&file) {
        return Err(format!("{context}: unsafe fixture file name '{file}'"));
    }
    if !CORPUS_BUCKETS.contains(&bucket.as_str()) {
        return Err(format!("{context}: unknown bucket '{bucket}'"));
    }
    if !NOTE_KINDS.contains(&note_kind.as_str()) {
        return Err(format!("{context}: unknown note_kind '{note_kind}'"));
    }

    let text = files
        .get(&file)
        .ok_or_else(|| format!("{context}: manifest file '{file}' has no .txt fixture on disk"))?;

    if text.is_empty() {
        return Err(format!("{context} ({file}): fixture text is empty"));
    }
    if text.starts_with('\u{feff}') {
        return Err(format!(
            "{context} ({file}): fixture text carries a UTF-8 BOM"
        ));
    }
    if text.contains('\r') {
        return Err(format!(
            "{context} ({file}): fixture text carries CR (LF only)"
        ));
    }

    let token_entries = entry.get("tokens")?.as_arr()?;
    if token_entries.is_empty() {
        return Err(format!("{context} ({file}): fragment has no tokens"));
    }

    let mut raw_tokens = Vec::with_capacity(token_entries.len());
    for (index, token_entry) in token_entries.iter().enumerate() {
        raw_tokens.push(validate_raw_token(token_entry, &context, index)?);
    }

    if note_kind != "synthetic" {
        for token in &raw_tokens {
            if let Some(abbrev_id) = &token.id {
                if CORPUS_FORBIDDEN_ABBREV_IDS.contains(&abbrev_id.as_str()) {
                    return Err(format!(
                        "{context} ({file}): corpus fragment uses D329-forbidden abbrev id '{abbrev_id}'"
                    ));
                }
            }
        }
    }

    let mut order: Vec<usize> = (0..raw_tokens.len()).collect();
    order.sort_by_key(|&index| (raw_tokens[index].start, index));

    let mut spans = Vec::with_capacity(raw_tokens.len());
    let mut kinds = Vec::with_capacity(raw_tokens.len());
    let mut abbrev_ids = Vec::with_capacity(raw_tokens.len());
    let mut lexemes = Vec::with_capacity(raw_tokens.len());
    for &index in &order {
        let token = &raw_tokens[index];
        if token.end > text.len() {
            return Err(format!(
                "{context} ({file}): token[{index}] end {} exceeds text length {}",
                token.end,
                text.len()
            ));
        }
        if !text.is_char_boundary(token.start) || !text.is_char_boundary(token.end) {
            return Err(format!(
                "{context} ({file}): token[{index}] span [{},{}) is not on char boundaries",
                token.start, token.end
            ));
        }
        let span = TextSpan::try_new(token.start, token.end)
            .map_err(|err| format!("{context} ({file}): token[{index}] invalid span: {err:?}"))?;
        let lexeme = &text[token.start..token.end];
        validate_lexeme_shape(&context, index, token, lexeme)?;
        spans.push(span);
        kinds.push(token.kind);
        abbrev_ids.push(token.id.clone());
        lexemes.push(lexeme.to_owned());
    }

    let first = &raw_tokens[order[0]];
    if first.start != 0 {
        return Err(format!(
            "{context} ({file}): covering gap — first token starts at byte {} instead of 0",
            first.start
        ));
    }
    for window in order.windows(2) {
        let (previous_index, next_index) = (window[0], window[1]);
        let previous = &raw_tokens[previous_index];
        let next = &raw_tokens[next_index];
        if next.start < previous.end {
            return Err(format!(
                "{context} ({file}): overlap — tokens [{},{}) and [{},{}) share bytes",
                previous.start, previous.end, next.start, next.end
            ));
        }
        if next.start > previous.end {
            return Err(format!(
                "{context} ({file}): covering gap — byte range [{},{}) is unclaimed",
                previous.end, next.start
            ));
        }
    }
    let last = &raw_tokens[*order.last().expect("tokens non-empty")];
    if last.end != text.len() {
        return Err(format!(
            "{context} ({file}): covering gap — last token ends at byte {} but text is {} bytes",
            last.end,
            text.len()
        ));
    }

    Ok(LoadedFragment {
        id,
        file,
        source_block_index,
        bucket,
        note_kind,
        text: text.clone(),
        spans,
        kinds,
        abbrev_ids,
        lexemes,
    })
}

fn validate_raw_token(entry: &Json, context: &str, index: usize) -> Result<RawToken, String> {
    let token_context = format!("{context}.tokens[{index}]");
    entry.require_keys(&["kind", "id", "start", "end"], &token_context)?;
    let kind_raw = entry.get("kind")?.as_str()?;
    let kind = TOKEN_KINDS
        .iter()
        .find(|candidate| **candidate == kind_raw)
        .copied()
        .ok_or_else(|| {
            format!("{token_context}: unknown token kind '{kind_raw}' (Editorial is not in the S01 vocab)")
        })?;
    let id_json = entry.get_opt("id")?;
    let id: Option<&str> = match id_json {
        None | Some(Json::Null) => None,
        Some(Json::Str(value)) => Some(value.as_str()),
        Some(other) => {
            return Err(format!(
                "{token_context}: id must be a string or null, found {other:?}"
            ));
        }
    };
    match (kind, id) {
        ("Abbrev", Some(abbrev_id)) => {
            if !ABBREV_IDS.contains(&abbrev_id) {
                return Err(format!("{token_context}: unknown abbrev id '{abbrev_id}'"));
            }
        }
        ("Abbrev", None) => return Err(format!("{token_context}: Abbrev token requires an id")),
        (_, Some(abbrev_id)) => {
            return Err(format!(
                "{token_context}: non-Abbrev token carries id '{abbrev_id}'"
            ));
        }
        (_, None) => {}
    }
    let start = entry.get("start")?.as_usize()?;
    let end = entry.get("end")?.as_usize()?;
    if start >= end {
        return Err(format!("{token_context}: start {start} >= end {end}"));
    }
    Ok(RawToken {
        kind,
        id: id.map(str::to_owned),
        start,
        end,
    })
}

fn validate_lexeme_shape(
    context: &str,
    index: usize,
    token: &RawToken,
    lexeme: &str,
) -> Result<(), String> {
    let token_context = format!("{context}.tokens[{index}] lexeme '{lexeme}'");
    match token.kind {
        "Abbrev" => {
            let id = token.id.as_deref().expect("Abbrev id validated earlier");
            let canonical = ABBREV_CANONICAL_LEXEMES
                .iter()
                .find(|(candidate, _)| *candidate == id)
                .map(|(_, lexeme)| *lexeme)
                .expect("abbrev id validated against the closed vocab");
            if lexeme != canonical {
                return Err(format!(
                    "{token_context}: Abbrev id '{id}' must slice canonical '{canonical}' (Abbrev consumes its dot; `пп.` is one token)"
                ));
            }
        }
        "HierNum" => {
            if !is_hier_num_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: HierNum must match \\d+(\\.\\d+)+ (one token)"
                ));
            }
            if is_date_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: dd.mm.yyyy with plausible day/month is a Date, never HierNum (D330 rule 3)"
                ));
            }
        }
        "Date" => {
            if !is_date_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: Date must be dd.mm.yyyy with plausible day/month"
                ));
            }
        }
        "DocNo" => {
            if !is_doc_no_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: DocNo must be digits + '-' + ФЗ/ФКЗ (e.g. '44-ФЗ')"
                ));
            }
        }
        "LawCode" => {
            if lexeme != "ФЗ" && lexeme != "ФКЗ" {
                return Err(format!(
                    "{token_context}: LawCode must be a lone 'ФЗ' or 'ФКЗ'"
                ));
            }
        }
        "EnumMarker" => {
            if !is_enum_marker_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: EnumMarker must be '1)' / '1.' / 'а)' as typed (quotes stay Punct)"
                ));
            }
        }
        "Space" => {
            if !lexeme.chars().all(char::is_whitespace) {
                return Err(format!(
                    "{token_context}: Space must be contiguous whitespace"
                ));
            }
        }
        "Word" => {
            if !is_word_lexeme(lexeme) {
                return Err(format!(
                    "{token_context}: Word must be an alphabetic run or an undotted digit run"
                ));
            }
        }
        "Punct" => {
            if lexeme.chars().any(char::is_alphanumeric) || lexeme.chars().all(char::is_whitespace)
            {
                return Err(format!(
                    "{token_context}: Punct must be non-alphanumeric symbols (letters/digits are Word/HierNum/Date/DocNo)"
                ));
            }
        }
        other => {
            let _ = other; // vocab is closed at parse time; unreachable
        }
    }
    Ok(())
}

fn is_word_lexeme(lexeme: &str) -> bool {
    !lexeme.is_empty()
        && (lexeme.chars().all(|ch| ch.is_alphabetic())
            || lexeme.bytes().all(|byte| byte.is_ascii_digit()))
}

fn is_hier_num_lexeme(lexeme: &str) -> bool {
    lexeme.contains('.')
        && lexeme
            .split('.')
            .all(|group| !group.is_empty() && group.bytes().all(|byte| byte.is_ascii_digit()))
}

fn is_date_lexeme(lexeme: &str) -> bool {
    let bytes = lexeme.as_bytes();
    bytes.len() == 10
        && bytes[2] == b'.'
        && bytes[5] == b'.'
        && (0..10).all(|index| index == 2 || index == 5 || bytes[index].is_ascii_digit())
        && (1..=31).contains(&lexeme[..2].parse::<u32>().unwrap_or(0))
        && (1..=12).contains(&lexeme[3..5].parse::<u32>().unwrap_or(0))
}

fn is_doc_no_lexeme(lexeme: &str) -> bool {
    match lexeme.split_once('-') {
        Some((digits, suffix)) => {
            !digits.is_empty()
                && digits.bytes().all(|byte| byte.is_ascii_digit())
                && (suffix == "ФЗ" || suffix == "ФКЗ")
        }
        None => false,
    }
}

fn is_enum_marker_lexeme(lexeme: &str) -> bool {
    let mut chars = lexeme.chars();
    let first = chars.next();
    if chars.next().is_none() {
        // Bare single lowercase cyrillic letter: a quoted subpoint label
        // (`п "а"` = Punct + EnumMarker + Punct), quotes stay Punct.
        return first.map(is_lower_cyrillic).unwrap_or(false);
    }
    let marker = lexeme.chars().next_back().unwrap_or(' ');
    if marker != ')' && marker != '.' {
        return false;
    }
    let body = &lexeme[..lexeme.len() - marker.len_utf8()];
    if body.is_empty() {
        return false;
    }
    body.bytes().all(|byte| byte.is_ascii_digit())
        || (body.chars().count() == 1
            && body.chars().next().map(is_lower_cyrillic).unwrap_or(false))
}

fn is_lower_cyrillic(ch: char) -> bool {
    ('а'..='я').contains(&ch) || ch == 'ё'
}

fn is_safe_fixture_file_name(name: &str) -> bool {
    name.len() > 4
        && name.ends_with(".txt")
        && !name.contains('/')
        && !name.contains('\\')
        && !name.contains("..")
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
}

// ---------------------------------------------------------------------------
// Green path.
// ---------------------------------------------------------------------------

#[test]
fn golden_fixtures_load_with_covering_span_invariants() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");
    assert!(fragments.len() >= 2, "the two seed goldens must be present");

    let fz44_001 = fragments
        .iter()
        .find(|fragment| fragment.id == "fz44-001")
        .expect("seed golden fz44-001");
    assert_eq!(fz44_001.source_block_index, 877, "fz44-001 block pin");
    assert_eq!(fz44_001.bucket, "abbrev-hier");
    assert_eq!(fz44_001.note_kind, "enacting");
    assert!(
        fz44_001
            .abbrev_ids
            .iter()
            .any(|id| id.as_deref() == Some("st")),
        "fz44-001 must pin an Abbrev st lexeme"
    );
    assert!(
        fz44_001.kinds.contains(&"HierNum"),
        "fz44-001 must pin a dotted HierNum token"
    );

    let fz44_002 = fragments
        .iter()
        .find(|fragment| fragment.id == "fz44-002")
        .expect("seed golden fz44-002");
    assert_eq!(fz44_002.source_block_index, 31, "fz44-002 block pin");
    assert_eq!(fz44_002.bucket, "date-docno");
    assert_eq!(fz44_002.note_kind, "enacting");
    assert!(fz44_002.kinds.contains(&"Date"), "fz44-002 must pin a Date");
    assert!(
        fz44_002.kinds.contains(&"DocNo"),
        "fz44-002 must pin a DocNo"
    );

    // TextSpan slices must reconstruct every pinned lexeme byte-exactly.
    for fragment in &fragments {
        assert_eq!(
            fragment.spans.len(),
            fragment.lexemes.len(),
            "span/lexeme parallel arrays must stay aligned"
        );
        for (span, lexeme) in fragment.spans.iter().zip(&fragment.lexemes) {
            assert_eq!(
                &fragment.text[span.start()..span.end()],
                lexeme,
                "fragment {} span {}..{} must slice its lexeme",
                fragment.id,
                span.start(),
                span.end()
            );
        }
    }

    assert!(
        count_corpus_fragments(&fragments) >= 2,
        "seed goldens are corpus fragments (T02 raises the quota to >= 40)"
    );
}

// ---------------------------------------------------------------------------
// T02: corpus harvest quotas and named collision locks (fixtures only; the
// 5.2 MB XML stays undecoded in CI — provenance is the pinned metadata).
// ---------------------------------------------------------------------------

/// Full-form reference words that must appear as Word tokens in the
/// fullword-ref bucket (running text, not headings; T02 quota table).
const FULLWORD_FORMS: [&str; 14] = [
    "статья",
    "статьи",
    "статье",
    "статью",
    "статьей",
    "статей", //
    "часть",
    "части",
    "частью",
    "частями",
    "частей", //
    "пункта",
    "пунктом",
    "подпунктом",
];

/// Punct lexemes that satisfy the misc-punct bucket (quotes / list separators).
const MISC_PUNCT_LEXEMES: [&str; 5] = ["\"", ";", ":", "«", "»"];

#[test]
fn t02_corpus_goldens_hold_quota_and_collision_locks() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");

    let corpus: Vec<&LoadedFragment> = fragments
        .iter()
        .filter(|fragment| fragment.note_kind != "synthetic")
        .collect();
    assert!(
        corpus.len() >= 40,
        "T02 quota: >= 40 corpus goldens (got {})",
        corpus.len()
    );

    let bucket = |name: &str| -> Vec<&LoadedFragment> {
        corpus
            .iter()
            .copied()
            .filter(|fragment| fragment.bucket == name)
            .collect()
    };
    let has_abbrev = |fragment: &LoadedFragment, id: &str| {
        fragment
            .abbrev_ids
            .iter()
            .any(|candidate| candidate.as_deref() == Some(id))
    };

    // abbrev-hier >= 8: an Abbrev from {st,ch,p,pp} AND a HierNum per fragment.
    let abbrev_hier = bucket("abbrev-hier");
    assert!(
        abbrev_hier.len() >= 8,
        "abbrev-hier quota: >= 8 (got {})",
        abbrev_hier.len()
    );
    for fragment in &abbrev_hier {
        assert!(
            fragment
                .abbrev_ids
                .iter()
                .any(|id| matches!(id.as_deref(), Some("st" | "ch" | "p" | "pp"))),
            "{} must carry a reference Abbrev",
            fragment.id
        );
        assert!(
            fragment.kinds.contains(&"HierNum"),
            "{} must pair the Abbrev with a HierNum",
            fragment.id
        );
    }

    // date-docno >= 6: Date AND DocNo per fragment.
    let date_docno = bucket("date-docno");
    assert!(
        date_docno.len() >= 6,
        "date-docno quota: >= 6 (got {})",
        date_docno.len()
    );
    for fragment in &date_docno {
        assert!(
            fragment.kinds.contains(&"Date") && fragment.kinds.contains(&"DocNo"),
            "{} must carry both Date and DocNo",
            fragment.id
        );
    }

    // enum-list >= 4: EnumMarker per fragment.
    let enum_list = bucket("enum-list");
    assert!(
        enum_list.len() >= 4,
        "enum-list quota: >= 4 (got {})",
        enum_list.len()
    );
    for fragment in &enum_list {
        assert!(
            fragment.kinds.contains(&"EnumMarker"),
            "{} must carry an EnumMarker",
            fragment.id
        );
    }

    // heading >= 4: `Глава/Статья N.` = Word + Space + Word(digits) + Punct(".");
    // both heading words must occur across the bucket.
    let heading = bucket("heading");
    assert!(
        heading.len() >= 4,
        "heading quota: >= 4 (got {})",
        heading.len()
    );
    let mut have_glava = false;
    let mut have_statya = false;
    for fragment in &heading {
        assert!(
            fragment.kinds.len() >= 4,
            "{} too short for a heading",
            fragment.id
        );
        assert_eq!(
            fragment.kinds[0], "Word",
            "{} heading must open with a Word",
            fragment.id
        );
        let is_glava = fragment.lexemes[0] == "Глава";
        let is_statya = fragment.lexemes[0] == "Статья";
        assert!(
            is_glava || is_statya,
            "{} must open with Глава/Статья, got {}",
            fragment.id,
            fragment.lexemes[0]
        );
        have_glava |= is_glava;
        have_statya |= is_statya;
        assert_eq!(fragment.kinds[1], "Space");
        assert_eq!(
            fragment.kinds[2], "Word",
            "{} heading number is an undotted-digit Word, never HierNum",
            fragment.id
        );
        assert!(
            fragment.lexemes[2].chars().all(|ch| ch.is_ascii_digit()),
            "{} heading number must be digits",
            fragment.id
        );
        assert_eq!(fragment.kinds[3], "Punct");
        assert_eq!(
            fragment.lexemes[3], ".",
            "{} heading dot stays Punct",
            fragment.id
        );
    }
    assert!(
        have_glava && have_statya,
        "heading bucket needs both Глава and Статья"
    );

    // fullword-ref >= 6: >= 1 full-form Word token per fragment.
    let fullword = bucket("fullword-ref");
    assert!(
        fullword.len() >= 6,
        "fullword-ref quota: >= 6 (got {})",
        fullword.len()
    );
    for fragment in &fullword {
        assert!(
            fragment
                .lexemes
                .iter()
                .zip(&fragment.kinds)
                .any(|(lexeme, kind)| *kind == "Word" && FULLWORD_FORMS.contains(&lexeme.as_str())),
            "{} must carry a full-form reference word",
            fragment.id
        );
    }

    // lawcode >= 2: lone ФЗ and lone ФКЗ across the bucket.
    let lawcode = bucket("lawcode");
    assert!(
        lawcode.len() >= 2,
        "lawcode quota: >= 2 (got {})",
        lawcode.len()
    );
    assert!(
        lawcode
            .iter()
            .any(|f| f.lexemes.iter().any(|lexeme| lexeme == "ФЗ")),
        "lawcode bucket must pin a lone ФЗ"
    );
    assert!(
        lawcode
            .iter()
            .any(|f| f.lexemes.iter().any(|lexeme| lexeme == "ФКЗ")),
        "lawcode bucket must pin a lone ФКЗ"
    );

    // dense-note: >= 3 and <= 5, each pinning `ред.` as Abbrev id=red.
    let dense_note = bucket("dense-note");
    assert!(
        dense_note.len() >= 3,
        "dense-note quota: >= 3 (got {})",
        dense_note.len()
    );
    assert!(
        dense_note.len() <= 5,
        "dense-note quota: <= 5 (got {})",
        dense_note.len()
    );
    for fragment in &dense_note {
        assert!(
            has_abbrev(fragment, "red"),
            "{} must pin `ред.` as Abbrev id=red",
            fragment.id
        );
    }

    // misc-punct >= 3: quotes / `;` / `:` Punct lexemes per fragment.
    let misc_punct = bucket("misc-punct");
    assert!(
        misc_punct.len() >= 3,
        "misc-punct quota: >= 3 (got {})",
        misc_punct.len()
    );
    for fragment in &misc_punct {
        assert!(
            fragment
                .lexemes
                .iter()
                .zip(&fragment.kinds)
                .any(|(lexeme, kind)| *kind == "Punct"
                    && MISC_PUNCT_LEXEMES.contains(&lexeme.as_str())),
            "{} must carry a quote/semicolon/colon Punct",
            fragment.id
        );
    }

    // Every kind from the closed vocab occurs at least once in the corpus.
    for kind in TOKEN_KINDS {
        assert!(
            corpus.iter().any(|fragment| fragment.kinds.contains(&kind)),
            "kind {kind} must occur at least once in the corpus"
        );
    }
    // The four reference abbrevs each occur (пп. is one token id=pp).
    for id in ["st", "ch", "p", "pp"] {
        assert!(
            corpus.iter().any(|fragment| has_abbrev(fragment, id)),
            "corpus must pin Abbrev id={id}"
        );
    }
    // Corpus Abbrev ids never come from the D329 forbidden zero set.
    for fragment in &corpus {
        for id in &fragment.abbrev_ids {
            if let Some(id) = id.as_deref() {
                assert!(
                    !CORPUS_FORBIDDEN_ABBREV_IDS.contains(&id),
                    "{}: forbidden corpus Abbrev id {id}",
                    fragment.id
                );
            }
        }
    }

    // Lexeme-shape locks T01 deliberately left to the load layer:
    // >= 1 Abbrev with trailing dot, >= 1 two-part HierNum, >= 1 dd.mm.yyyy
    // Date, >= 1 -ФЗ/-ФКЗ DocNo, and no date-shaped HierNum anywhere.
    let mut saw_abbrev_dot = false;
    let mut saw_two_part_hier = false;
    let mut saw_date = false;
    let mut saw_docno = false;
    for fragment in &corpus {
        for (kind, lexeme) in fragment.kinds.iter().zip(&fragment.lexemes) {
            match *kind {
                "Abbrev" => saw_abbrev_dot |= lexeme.ends_with('.'),
                "HierNum" => {
                    saw_two_part_hier |=
                        is_hier_num_lexeme(lexeme) && lexeme.matches('.').count() == 1;
                    assert!(
                        !is_date_lexeme(lexeme),
                        "{}: date-shaped HierNum lexeme {lexeme} is forbidden",
                        fragment.id
                    );
                }
                "Date" => saw_date |= is_date_lexeme(lexeme),
                "DocNo" => saw_docno |= lexeme.contains("-ФЗ") || lexeme.contains("-ФКЗ"),
                _ => {}
            }
        }
    }
    assert!(saw_abbrev_dot, "corpus must pin a dotted Abbrev lexeme");
    assert!(saw_two_part_hier, "corpus must pin a \\d+\\.\\d+ HierNum");
    assert!(saw_date, "corpus must pin a dd.mm.yyyy Date");
    assert!(saw_docno, "corpus must pin a -ФЗ/-ФКЗ DocNo");

    // Named corpus collisions (T02 plan item 7):
    // 1. `п. 9.1` = Abbrev + Space + HierNum (fz44-003).
    let fz44_003 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-003")
        .expect("fz44-003 must exist");
    assert!(
        fz44_003
            .kinds
            .windows(3)
            .any(|window| window == ["Abbrev", "Space", "HierNum"]),
        "fz44-003 must pin Abbrev+Space+HierNum (п. 9.1)"
    );

    // 2. dotted HierNum directly after an Abbrev (fz44-010: ст. 111.4).
    let fz44_010 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-010")
        .expect("fz44-010 must exist");
    assert!(
        has_abbrev(fz44_010, "st") && fz44_010.lexemes.iter().any(|lexeme| lexeme == "111.4"),
        "fz44-010 must pin Abbrev(st) before the dotted HierNum 111.4"
    );

    // 3. `пп. "а"` = Abbrev(pp) + Space + Punct + EnumMarker + Punct.
    let quoted_label = corpus.iter().any(|fragment| {
        (0..fragment.kinds.len().saturating_sub(4)).any(|index| {
            fragment.kinds[index] == "Abbrev"
                && fragment.abbrev_ids[index].as_deref() == Some("pp")
                && fragment.kinds[index + 1] == "Space"
                && fragment.kinds[index + 2] == "Punct"
                && fragment.kinds[index + 3] == "EnumMarker"
                && fragment.kinds[index + 4] == "Punct"
        })
    });
    assert!(
        quoted_label,
        "corpus must pin the quoted subpoint label collision"
    );

    // 4. `N 44-ФЗ` = Word("N") + Space + DocNo.
    let n_docno = corpus.iter().any(|fragment| {
        (0..fragment.kinds.len().saturating_sub(2)).any(|index| {
            fragment.kinds[index] == "Word"
                && fragment.lexemes[index] == "N"
                && fragment.kinds[index + 1] == "Space"
                && fragment.kinds[index + 2] == "DocNo"
        })
    });
    assert!(n_docno, "corpus must pin Word(N)+Space+DocNo");

    // 5. `01.01.2028` stays Date, never HierNum (fz44-037).
    let fz44_037 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-037")
        .expect("fz44-037 must exist");
    assert!(
        fz44_037
            .lexemes
            .iter()
            .zip(&fz44_037.kinds)
            .any(|(lexeme, kind)| lexeme == "01.01.2028" && *kind == "Date"),
        "fz44-037 must pin 01.01.2028 as Date"
    );

    // Frequency caps from the T02 marking contract.
    let amendment_lists = corpus
        .iter()
        .filter(|fragment| {
            (0..fragment.kinds.len().saturating_sub(1)).any(|index| {
                fragment.kinds[index] == "DocNo"
                    && fragment.kinds[index + 1] == "Punct"
                    && fragment.lexemes[index + 1] == ","
            })
        })
        .count();
    assert!(
        amendment_lists <= 5,
        "amendment-list fragments must stay <= 5 (got {amendment_lists})"
    );
    let provider_notes = fragments
        .iter()
        .filter(|fragment| fragment.note_kind == "provider_note")
        .count();
    assert!(
        provider_notes <= 5,
        "provider_note fragments must stay <= 5 (got {provider_notes})"
    );
}

// ---------------------------------------------------------------------------
// Hostile: in-memory manifests must fail the loader closed (goldens untouched).
// ---------------------------------------------------------------------------

const HOSTILE_FILE: &str = "hostile-001.txt";

fn hostile_source_block() -> String {
    format!(
        r#""source": {{
    "path": "{SOURCE_RELATIVE_PATH}",
    "sha256": "{SOURCE_SHA256}",
    "decoder": "{SOURCE_DECODER}",
    "non_claims": [
      "not official-publication provenance (R070 open)",
      "not LawRef / act-tree / clause segmentation",
      "not legal interpretation"
    ]
  }}"#
    )
}

fn hostile_manifest(fragments_json: &str) -> String {
    format!(
        r#"{{
  "schema_version": 1,
  "lifecycle": "[bounded]",
  {source_block},
  "fragments": {fragments_json}
}}"#,
        source_block = hostile_source_block(),
    )
}

fn hostile_fragment_json(tokens_json: &str) -> String {
    format!(
        r#"[{{"id": "hostile-001", "file": "{HOSTILE_FILE}", "source_block_index": 0, "bucket": "abbrev-hier", "note_kind": "enacting", "tokens": [{tokens_json}]}}]"#
    )
}

fn run_hostile_loader(tokens_json: &str, text: &str) -> String {
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), text.to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(tokens_json));
    validate_fixture_set(&manifest, &files, None)
        .expect_err("hostile manifest must fail the loader closed")
}

#[test]
fn hostile_overlap_spans_fail_closed() {
    // text = "абв" (6 bytes); the second token starts inside the first one.
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 4},
           {"kind": "Word", "start": 2, "end": 6}"#,
        "абв",
    );
    assert!(
        error.contains("overlap"),
        "expected overlap error, got: {error}"
    );

    // Exact duplicate spans collide the same way.
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 2},
           {"kind": "Word", "start": 0, "end": 2}"#,
        "аб",
    );
    assert!(
        error.contains("overlap"),
        "expected overlap error, got: {error}"
    );
}

#[test]
fn hostile_covering_gap_fails_closed() {
    // text = "ст. 15.1" (10 bytes); the Space at bytes 5..6 is unclaimed.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "HierNum", "start": 6, "end": 10}"#,
        "ст. 15.1",
    );
    assert!(
        error.contains("gap"),
        "expected covering-gap error, got: {error}"
    );
}

#[test]
fn hostile_unknown_editorial_kind_fails_closed() {
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "Editorial", "start": 6, "end": 10}"#,
        "ст. 15.1",
    );
    assert!(
        error.contains("unknown token kind 'Editorial'"),
        "expected Editorial rejection, got: {error}"
    );
}

#[test]
fn hostile_pp_split_into_two_abbrevs_fails_closed() {
    // text = "пп." (5 bytes): `пп.` must be ONE Abbrev id=pp (D330 rule 1);
    // two `п` tokens leave `п` without its canonical trailing dot.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "p", "start": 0, "end": 2},
           {"kind": "Abbrev", "id": "p", "start": 2, "end": 5}"#,
        "пп.",
    );
    assert!(
        error.contains("canonical"),
        "expected canonical-lexeme rejection for the split `пп.`, got: {error}"
    );
}

#[test]
fn hostile_empty_span_fails_closed() {
    let error = run_hostile_loader(r#"{"kind": "Punct", "start": 0, "end": 0}"#, ".");
    assert!(
        error.contains(">= end"),
        "expected empty-span rejection, got: {error}"
    );
}

#[test]
fn hostile_date_shaped_hier_num_fails_closed() {
    // D330 rule 3: Date beats HierNum on `dd.mm.yyyy` ("01.01.2028").
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 4},
           {"kind": "Space", "start": 4, "end": 5},
           {"kind": "HierNum", "start": 5, "end": 15},
           {"kind": "Space", "start": 15, "end": 16},
           {"kind": "Word", "start": 16, "end": 34}"#,
        "До 01.01.2028 действует",
    );
    assert!(
        error.contains("Date"),
        "expected Date-beats-HierNum rejection, got: {error}"
    );
}

#[test]
fn hostile_corpus_forbidden_abbrev_id_fails_closed() {
    // D329: `гл.` has zero hits in the tracked 44-ФЗ — never mint it as corpus.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "gl", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "Word", "start": 6, "end": 7}"#,
        "гл. 2",
    );
    assert!(
        error.contains("D329-forbidden"),
        "expected forbidden-abbrev rejection, got: {error}"
    );
}

#[test]
fn hostile_malformed_manifest_json_fails_closed() {
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), "ст. 15.1".to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},,,"#,
    ));
    let error = validate_fixture_set(&manifest, &files, None)
        .expect_err("malformed manifest JSON must fail closed");
    assert!(
        error.contains("JSON parse error"),
        "expected JSON parse rejection, got: {error}"
    );
}

#[test]
fn hostile_bijection_violations_fail_closed() {
    // Extra .txt on disk without a manifest entry.
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), "ст. 15.1".to_string());
    files.insert("orphan-001.txt".to_string(), "лишний".to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "HierNum", "start": 6, "end": 10}"#,
    ));
    let error = validate_fixture_set(&manifest, &files, None)
        .expect_err("extra txt without a manifest entry must fail closed");
    assert!(
        error.contains("extra fixture file"),
        "expected extra-file rejection, got: {error}"
    );

    // Manifest entry whose .txt is missing.
    let empty_files: BTreeMap<String, String> = BTreeMap::new();
    let error = validate_fixture_set(&manifest, &empty_files, None)
        .expect_err("manifest entry without its txt must fail closed");
    assert!(
        error.contains("no .txt fixture"),
        "expected missing-file rejection, got: {error}"
    );
}
