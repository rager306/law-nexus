//! Shared NPA golden-fixture loader (extracted from
//! `tests/npa_golden_fixtures.rs` in M197 S02).
//!
//! S02 carries two integration tests that must compare against the same S01
//! oracle, and a Cargo `tests/` subdirectory is not auto-discovered as a test
//! target: this module is included by both `npa_golden_fixtures.rs` and
//! `npa_lexer_contract.rs` via `mod npa_support;` (no `#[path]` games, no
//! third test target, no duplicated loader).
//!
//! Owned here: the hand-rolled JSON parser (D328: stdlib only, closed
//! schema, fail-closed), the closed S01 vocab/constants, the fail-closed
//! fixture loader and validators, and the D330 lexeme shape helpers. The
//! tracked `tests/fixtures/npa/` files stay the span coordinate system;
//! nothing here decodes the 5.2 MB source XML (only `fs::metadata`
//! provenance pinning).

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::domain::TextSpan;

pub(crate) const SOURCE_RELATIVE_PATH: &str = "law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml";
pub(crate) const SOURCE_SHA256: &str =
    "c111119c6c3001b5b4fde0e35bffbe382bcb877df2bba9cd54ab0290c92c1b14";
pub(crate) const SOURCE_BYTES: u64 = 5_262_136;
pub(crate) const SOURCE_DECODER: &str = "ConsultantWordMlBlockDecoder";
pub(crate) const TOKENS_MANIFEST: &str = "fz44_npa_tokens.json";
pub(crate) const MANIFEST_SCHEMA_VERSION: usize = 1;
pub(crate) const MANIFEST_LIFECYCLE: &str = "[bounded]";

/// Closed TokenKind vocab (ADR-0028 step-1 list). `Editorial` is a wave-2
/// kind and must fail the loader closed in S01.
pub(crate) const TOKEN_KINDS: [&str; 9] = [
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
pub(crate) const ABBREV_IDS: [&str; 17] = [
    "st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd", "pril", "prim", "red", "izm",
    "utv", "sm", "sr", "g",
];

/// D329-nine: a corpus-goldens rule, not a corpus empiric. Tracked 44-ФЗ
/// goldens (`note_kind != synthetic`) must never mint tokens under these
/// ids, so goldens are never calibrated on them (operative KEEP, M198-das7v8
/// S02/T01: the list itself is frozen — never narrow it, never extend it).
/// This is NOT a claim that the nine never occur in the full Consultant
/// export: the C1 sweep (43 785 XML) refuted "nine never occur" (utv 3464,
/// podp 1352, gl 1195, abz 1574, razd 163, prim 35, pril 33, sr 16; stst is
/// the only global zero).
pub(crate) const CORPUS_FORBIDDEN_ABBREV_IDS: [&str; 9] = [
    "gl", "razd", "podp", "abz", "pril", "prim", "stst", "utv", "sr",
];

/// Canonical Abbrev lexemes: an Abbrev token consumes its trailing dot, so
/// `id: st` must slice exactly `ст.` (this rejects a split `пп.`).
pub(crate) const ABBREV_CANONICAL_LEXEMES: [(&str, &str); 17] = [
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
pub(crate) const CORPUS_BUCKETS: [&str; 8] = [
    "abbrev-hier",
    "date-docno",
    "enum-list",
    "heading",
    "fullword-ref",
    "lawcode",
    "dense-note",
    "misc-punct",
];

/// The only bucket a `synthetic` fragment may claim; corpus fragments must
/// never claim it (otherwise they could escape the >= 40 corpus quota).
pub(crate) const SYNTHETIC_BUCKET: &str = "synthetic-collision";

/// note_kind vocab for S01; `synthetic` marks the T03 constructed collision
/// pair (never counted as corpus, never eligible for bucket quotas).
pub(crate) const NOTE_KINDS: [&str; 3] = ["enacting", "provider_note", "synthetic"];

/// Honesty substrings every manifest must carry (R070 stays open).
pub(crate) const REQUIRED_NON_CLAIMS: [&str; 3] =
    ["official-publication", "LawRef", "legal interpretation"];

pub(crate) fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

pub(crate) fn fixtures_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa")
}

// ---------------------------------------------------------------------------
// Hand-rolled JSON (D328: stdlib only, closed schema, fail-closed).
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub(crate) enum Json {
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
pub(crate) struct RawToken {
    pub(crate) kind: &'static str,
    pub(crate) id: Option<String>,
    pub(crate) start: usize,
    pub(crate) end: usize,
}

#[derive(Debug)]
pub(crate) struct LoadedFragment {
    pub(crate) id: String,
    pub(crate) file: String,
    pub(crate) source_block_index: usize,
    pub(crate) bucket: String,
    pub(crate) note_kind: String,
    pub(crate) text: String,
    pub(crate) spans: Vec<TextSpan>,
    pub(crate) kinds: Vec<&'static str>,
    pub(crate) abbrev_ids: Vec<Option<String>>,
    pub(crate) lexemes: Vec<String>,
}

pub(crate) fn count_corpus_fragments(fragments: &[LoadedFragment]) -> usize {
    fragments
        .iter()
        .filter(|fragment| fragment.note_kind != "synthetic")
        .count()
}

pub(crate) fn load_golden_fixtures(
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

pub(crate) fn validate_fixture_set(
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

pub(crate) fn validate_fragment(
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
    if !NOTE_KINDS.contains(&note_kind.as_str()) {
        return Err(format!("{context}: unknown note_kind '{note_kind}'"));
    }
    if note_kind == "synthetic" {
        if bucket != SYNTHETIC_BUCKET {
            return Err(format!(
                "{context}: synthetic fragment must use bucket '{SYNTHETIC_BUCKET}', got '{bucket}'"
            ));
        }
    } else if bucket == SYNTHETIC_BUCKET {
        return Err(format!(
            "{context}: corpus fragment must not claim the synthetic bucket '{SYNTHETIC_BUCKET}'"
        ));
    } else if !CORPUS_BUCKETS.contains(&bucket.as_str()) {
        return Err(format!("{context}: unknown bucket '{bucket}'"));
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

pub(crate) fn validate_raw_token(
    entry: &Json,
    context: &str,
    index: usize,
) -> Result<RawToken, String> {
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

pub(crate) fn validate_lexeme_shape(
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

pub(crate) fn is_word_lexeme(lexeme: &str) -> bool {
    !lexeme.is_empty()
        && (lexeme.chars().all(|ch| ch.is_alphabetic())
            || lexeme.bytes().all(|byte| byte.is_ascii_digit()))
}

pub(crate) fn is_hier_num_lexeme(lexeme: &str) -> bool {
    lexeme.contains('.')
        && lexeme
            .split('.')
            .all(|group| !group.is_empty() && group.bytes().all(|byte| byte.is_ascii_digit()))
}

pub(crate) fn is_date_lexeme(lexeme: &str) -> bool {
    let bytes = lexeme.as_bytes();
    bytes.len() == 10
        && bytes[2] == b'.'
        && bytes[5] == b'.'
        && (0..10).all(|index| index == 2 || index == 5 || bytes[index].is_ascii_digit())
        && (1..=31).contains(&lexeme[..2].parse::<u32>().unwrap_or(0))
        && (1..=12).contains(&lexeme[3..5].parse::<u32>().unwrap_or(0))
}

pub(crate) fn is_doc_no_lexeme(lexeme: &str) -> bool {
    match lexeme.split_once('-') {
        Some((digits, suffix)) => {
            !digits.is_empty()
                && digits.bytes().all(|byte| byte.is_ascii_digit())
                && (suffix == "ФЗ" || suffix == "ФКЗ")
        }
        None => false,
    }
}

pub(crate) fn is_enum_marker_lexeme(lexeme: &str) -> bool {
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

pub(crate) fn is_lower_cyrillic(ch: char) -> bool {
    ('а'..='я').contains(&ch) || ch == 'ё'
}

pub(crate) fn is_safe_fixture_file_name(name: &str) -> bool {
    name.len() > 4
        && name.ends_with(".txt")
        && !name.contains('/')
        && !name.contains('\\')
        && !name.contains("..")
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
}
