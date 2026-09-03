//! Shared Layer-2 gold-sample manifest loader (`npa-lawref-sample/v1`; M199 S01).
//!
//! Hand-rolled JSON (D328 pattern: stdlib only, closed schema, fail-closed),
//! structurally copied from `tests/npa_support/mod.rs`. This is deliberately a
//! SEPARATE module: it is NOT a `#[path]` include of `npa_support` (different
//! schema — the Layer-2 sample is span/slot evidence, not a TokenKind oracle)
//! and it must never compile `npa_golden_fixtures.rs` twice (D335).
//!
//! T01 pinned the schema only: closed constants + `validate_sample_set` + the
//! on-disk `load_sample_manifest` helper. T02 landed the 40-document
//! stratified fill under `tests/fixtures/npa-lawref/` (canonical manifest in
//! `prd/migration/rust-evidence/`, never a fixtures-side copy — one source of
//! truth) plus the `#[ignore]` harvest runner in the contract test.
//! `lawref_seed` spans are T03.
//!
//! Q3 hygiene: errors name keys, offsets, and file names — never fragment or
//! block payload text.
//!
//! Protocol authority: `prd/migration/rust-evidence/m199-s01-annotation-protocol.md`.
#![allow(dead_code)]

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

// ---------------------------------------------------------------------------
// Closed schema constants (`npa-lawref-sample/v1`).
// ---------------------------------------------------------------------------

pub(crate) const SAMPLE_SCHEMA: &str = "npa-lawref-sample/v1";
pub(crate) const SAMPLE_SCHEMA_VERSION: usize = 1;
pub(crate) const SAMPLE_LIFECYCLE: &str = "[bounded]";
pub(crate) const SAMPLE_DECODER: &str = "ConsultantWordMlBlockDecoder";

/// Closed family vocab (= `npa_sweep::family_from_path` non-`other` set).
pub(crate) const SAMPLE_FAMILIES: [&str; 4] = ["npa", "courts", "fas", "xml"];

/// Closed fragment `note_kind` vocab. `hostile-control` rows sit outside the
/// D367 quotas (T03 negative pins); `provider_note` is a fragment provenance
/// role from Consultant notes — it never mints a lexer kind.
pub(crate) const SAMPLE_NOTE_KINDS: [&str; 4] = [
    "enacting",
    "provider_note",
    "hostile-control",
    "pattern-boost",
];

/// Closed fragment `status` vocab: the seed is not gold (protocol §10).
pub(crate) const SAMPLE_FRAGMENT_STATUSES: [&str; 1] = ["seed"];

/// Closed C2 TokenKind vocab (same nine kinds as the S01 oracle). `Editorial`
/// is a wave-2 kind and fails closed by name; `LawRef` is a product type, not
/// a TokenKind, and is rejected explicitly wherever a span kind is read.
pub(crate) const SAMPLE_TOKEN_KINDS: [&str; 9] = [
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

/// Honesty substrings every document's non_claims must carry
/// (R070 stays open; the sample is not the N2 gate).
pub(crate) const SAMPLE_REQUIRED_NON_CLAIMS: [&str; 5] = [
    "official-publication",
    "R070",
    "LawRef",
    "N2-gate",
    "legal interpretation",
];

/// D367 frozen quota table `(family, doc_type, quota)` — 9 strata, 40
/// documents, npa oversampled as the primary family; the 118 44-ФЗ editions
/// are one Work sampled as one cluster cell (R081), not 118 strata.
pub(crate) const D367_QUOTA_TABLE: [(&str, &str, usize); 9] = [
    ("npa", "law", 8),
    ("npa", "law-44fz", 4),
    ("npa", "order", 6),
    ("npa", "resolution", 4),
    ("npa", "directive", 3),
    ("npa", "decree-document", 1),
    ("courts", "courts-unspecified", 5),
    ("fas", "fas-unspecified", 5),
    ("xml", "xml-unspecified", 4),
];

pub(crate) const D367_TOTAL_DOCS: usize = 40;

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

    fn as_u64(&self) -> Result<u64, String> {
        match self {
            Json::Num(raw) => raw
                .parse::<u64>()
                .map_err(|_| format!("expected non-negative integer, found '{raw}'")),
            other => Err(format!("expected integer, found {other:?}")),
        }
    }
}

// ---------------------------------------------------------------------------
// Loaded types.
// ---------------------------------------------------------------------------

/// Optional rule-seed span on a fragment (T03 fills these; the loader already
/// pins the coordinate contract now).
#[derive(Debug)]
pub(crate) struct SeedSpan {
    pub(crate) kind: &'static str,
    pub(crate) start: usize,
    pub(crate) end: usize,
}

#[derive(Debug)]
pub(crate) struct SampleDocument {
    pub(crate) doc_id: String,
    pub(crate) source_path: String,
    pub(crate) source_sha256: String,
    pub(crate) byte_count: u64,
    pub(crate) family: String,
    pub(crate) doc_type: String,
    pub(crate) fragment_ids: Vec<String>,
}

#[derive(Debug)]
pub(crate) struct SampleFragment {
    pub(crate) id: String,
    pub(crate) file: String,
    pub(crate) doc_id: String,
    pub(crate) source_block_index: usize,
    pub(crate) note_kind: String,
    pub(crate) byte_len: usize,
    pub(crate) status: String,
    pub(crate) seed_span: Option<SeedSpan>,
}

#[derive(Debug)]
pub(crate) struct SampleManifest {
    pub(crate) draw_seed: u64,
    pub(crate) strata: Vec<(String, String, usize)>,
    pub(crate) documents: Vec<SampleDocument>,
    pub(crate) fragments: Vec<SampleFragment>,
}

// ---------------------------------------------------------------------------
// Fail-closed loaders.
// ---------------------------------------------------------------------------

/// Reads the manifest JSON plus every sibling `*.txt` fragment and validates
/// the whole set. `manifest_path` may be the fixtures-side copy or the tracked
/// evidence copy (`prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`);
/// `fragments_dir` is the `tests/fixtures/npa-lawref/` tree (T02).
pub(crate) fn load_sample_manifest(
    manifest_path: &Path,
    fragments_dir: &Path,
) -> Result<SampleManifest, String> {
    let manifest_text = fs::read_to_string(manifest_path)
        .map_err(|err| format!("read {}: {err}", manifest_path.display()))?;
    let mut files = BTreeMap::new();
    let entries = fs::read_dir(fragments_dir)
        .map_err(|err| format!("read fragments dir {}: {err}", fragments_dir.display()))?;
    for entry in entries {
        let path = entry
            .map_err(|err| format!("fragments dir entry: {err}"))?
            .path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("txt") {
            let name = path
                .file_name()
                .ok_or_else(|| format!("fragment path without file name: {}", path.display()))?
                .to_string_lossy()
                .into_owned();
            let content = fs::read_to_string(&path)
                .map_err(|err| format!("read fragment '{name}': {err}"))?;
            files.insert(name, content);
        }
    }
    validate_sample_set(&manifest_text, &files)
}

/// Core validator: closed keys everywhere, closed vocabularies, exact D367
/// strata table, per-document sha256/non_claims, bijection
/// `fragment.file ↔ *.txt`, byte-length honesty, and (when present) the
/// seed-span coordinate contract. No covering/token-concat check: Layer-2
/// fragments are plain decoded text, not a TokenKind sidecar.
pub(crate) fn validate_sample_set(
    manifest_text: &str,
    files: &BTreeMap<String, String>,
) -> Result<SampleManifest, String> {
    let root = JsonParser::new(manifest_text).parse_document()?;
    root.require_keys(
        &[
            "schema",
            "schema_version",
            "lifecycle",
            "draw_seed",
            "strata",
            "documents",
            "fragments",
        ],
        "manifest",
    )?;

    let schema = root.get("schema")?.as_str()?;
    if schema != SAMPLE_SCHEMA {
        return Err(format!("manifest schema '{schema}' != '{SAMPLE_SCHEMA}'"));
    }
    let schema_version = root.get("schema_version")?.as_usize()?;
    if schema_version != SAMPLE_SCHEMA_VERSION {
        return Err(format!(
            "manifest schema_version {schema_version} != {SAMPLE_SCHEMA_VERSION}"
        ));
    }
    let lifecycle = root.get("lifecycle")?.as_str()?;
    if lifecycle != SAMPLE_LIFECYCLE {
        return Err(format!(
            "manifest lifecycle '{lifecycle}' != '{SAMPLE_LIFECYCLE}'"
        ));
    }
    let draw_seed = root.get("draw_seed")?.as_u64()?;

    // --- strata: closed rows, exact frozen D367 table ----------------------
    let strata_entries = root.get("strata")?.as_arr()?;
    if strata_entries.is_empty() {
        return Err("manifest strata must not be empty".to_string());
    }
    let mut strata: Vec<(String, String, usize)> = Vec::with_capacity(strata_entries.len());
    for (position, entry) in strata_entries.iter().enumerate() {
        let context = format!("strata[{position}]");
        entry.require_keys(&["family", "doc_type", "quota"], &context)?;
        let family = entry.get("family")?.as_str()?.to_owned();
        if !SAMPLE_FAMILIES.contains(&family.as_str()) {
            return Err(format!("{context}: unknown family '{family}'"));
        }
        let doc_type = entry.get("doc_type")?.as_str()?.to_owned();
        if doc_type.is_empty() {
            return Err(format!("{context}: empty doc_type"));
        }
        let quota = entry.get("quota")?.as_usize()?;
        if quota == 0 {
            return Err(format!("{context}: quota must be >= 1"));
        }
        strata.push((family, doc_type, quota));
    }
    let mut actual = strata.clone();
    actual.sort();
    let mut expected: Vec<(String, String, usize)> = D367_QUOTA_TABLE
        .iter()
        .map(|(family, doc_type, quota)| ((*family).to_owned(), (*doc_type).to_owned(), *quota))
        .collect();
    expected.sort();
    if actual != expected {
        return Err(format!(
            "manifest strata must equal the frozen D367 quota table (9 rows, {D367_TOTAL_DOCS} documents); got {} row(s) that drifted from D367",
            strata.len()
        ));
    }

    // --- documents ----------------------------------------------------------
    let document_entries = root.get("documents")?.as_arr()?;
    if document_entries.is_empty() {
        return Err("manifest must declare at least one document".to_string());
    }
    let mut documents = Vec::with_capacity(document_entries.len());
    let mut seen_doc_ids = BTreeSet::new();
    for (position, entry) in document_entries.iter().enumerate() {
        let document = validate_document(entry, position, &strata)?;
        if !seen_doc_ids.insert(document.doc_id.clone()) {
            return Err(format!("duplicate document id '{}'", document.doc_id));
        }
        documents.push(document);
    }

    // --- fragments ----------------------------------------------------------
    let fragment_entries = root.get("fragments")?.as_arr()?;
    if fragment_entries.is_empty() {
        return Err("manifest must declare at least one fragment".to_string());
    }
    let mut fragments = Vec::with_capacity(fragment_entries.len());
    let mut seen_fragment_ids = BTreeSet::new();
    let mut seen_files = BTreeSet::new();
    for (position, entry) in fragment_entries.iter().enumerate() {
        let fragment = validate_fragment(entry, position, files)?;
        if !seen_fragment_ids.insert(fragment.id.clone()) {
            return Err(format!("duplicate fragment id '{}'", fragment.id));
        }
        if !seen_files.insert(fragment.file.clone()) {
            return Err(format!("duplicate fragment file '{}'", fragment.file));
        }
        fragments.push(fragment);
    }

    // --- document <-> fragment reference consistency ------------------------
    for fragment in &fragments {
        if !documents.iter().any(|doc| doc.doc_id == fragment.doc_id) {
            return Err(format!(
                "fragment '{}': unknown document id '{}'",
                fragment.id, fragment.doc_id
            ));
        }
    }
    for document in &documents {
        for fragment_id in &document.fragment_ids {
            let Some(fragment) = fragments
                .iter()
                .find(|fragment| &fragment.id == fragment_id)
            else {
                return Err(format!(
                    "document '{}': fragment_ids entry '{fragment_id}' has no matching fragment",
                    document.doc_id
                ));
            };
            if fragment.doc_id != document.doc_id {
                return Err(format!(
                    "document '{}' lists fragment '{}' which declares doc_id '{}'",
                    document.doc_id, fragment.id, fragment.doc_id
                ));
            }
        }
    }

    // --- bijection fragment.file <-> *.txt ----------------------------------
    for name in files.keys() {
        if !seen_files.contains(name) {
            return Err(format!(
                "extra fragment file '{name}' has no manifest entry"
            ));
        }
    }

    Ok(SampleManifest {
        draw_seed,
        strata,
        documents,
        fragments,
    })
}

fn validate_document(
    entry: &Json,
    position: usize,
    strata: &[(String, String, usize)],
) -> Result<SampleDocument, String> {
    let context = format!("documents[{position}]");
    entry.require_keys(
        &[
            "doc_id",
            "source_path",
            "source_sha256",
            "byte_count",
            "family",
            "doc_type",
            "decoder",
            "fragment_ids",
            "non_claims",
        ],
        &context,
    )?;
    let doc_id = entry.get("doc_id")?.as_str()?.to_owned();
    let context = format!("{context} (doc_id '{doc_id}')");
    if doc_id.is_empty() {
        return Err(format!("{context}: empty document id"));
    }
    let source_path = entry.get("source_path")?.as_str()?.to_owned();
    if source_path.is_empty() {
        return Err(format!("{context}: empty source_path"));
    }
    if source_path.starts_with('/') {
        return Err(format!(
            "{context}: source_path must be repo- or export-relative, got '{source_path}'"
        ));
    }
    let source_sha256 = entry.get("source_sha256")?.as_str()?.to_owned();
    if source_sha256.len() != 64 || !source_sha256.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!(
            "{context}: source_sha256 must be a 64-char hex digest"
        ));
    }
    let byte_count = entry.get("byte_count")?.as_u64()?;
    if byte_count == 0 {
        return Err(format!("{context}: byte_count must be >= 1"));
    }
    let family = entry.get("family")?.as_str()?.to_owned();
    if !SAMPLE_FAMILIES.contains(&family.as_str()) {
        return Err(format!("{context}: unknown family '{family}'"));
    }
    let doc_type = entry.get("doc_type")?.as_str()?.to_owned();
    if doc_type.is_empty() {
        return Err(format!("{context}: empty doc_type"));
    }
    let decoder = entry.get("decoder")?.as_str()?.to_owned();
    if decoder != SAMPLE_DECODER {
        return Err(format!(
            "{context}: decoder '{decoder}' != '{SAMPLE_DECODER}' (Consultant only; Garant ODT is out of scope for the npa-lawref sample)"
        ));
    }
    if !strata.iter().any(|(stratum_family, stratum_type, _)| {
        *stratum_family == family && *stratum_type == doc_type
    }) {
        return Err(format!(
            "{context}: (family, doc_type) ('{family}', '{doc_type}') is outside the declared D367 strata"
        ));
    }
    let fragment_ids_json = entry.get("fragment_ids")?.as_arr()?;
    if fragment_ids_json.is_empty() {
        return Err(format!("{context}: fragment_ids must not be empty"));
    }
    let mut fragment_ids = Vec::with_capacity(fragment_ids_json.len());
    let mut seen_ids = BTreeSet::new();
    for item in fragment_ids_json {
        let fragment_id = item.as_str()?.to_owned();
        if fragment_id.is_empty() {
            return Err(format!("{context}: empty fragment_ids entry"));
        }
        if !seen_ids.insert(fragment_id.clone()) {
            return Err(format!(
                "{context}: duplicate fragment_ids entry '{fragment_id}'"
            ));
        }
        fragment_ids.push(fragment_id);
    }
    let non_claims_json = entry.get("non_claims")?.as_arr()?;
    if non_claims_json.is_empty() {
        return Err(format!("{context}: non_claims must not be empty"));
    }
    for claim in non_claims_json {
        claim.as_str()?;
    }
    for required in SAMPLE_REQUIRED_NON_CLAIMS {
        if !non_claims_json
            .iter()
            .filter_map(|claim| claim.as_str().ok())
            .any(|claim| claim.contains(required))
        {
            return Err(format!("{context}: non_claims is missing '{required}'"));
        }
    }
    Ok(SampleDocument {
        doc_id,
        source_path,
        source_sha256,
        byte_count,
        family,
        doc_type,
        fragment_ids,
    })
}

fn validate_fragment(
    entry: &Json,
    position: usize,
    files: &BTreeMap<String, String>,
) -> Result<SampleFragment, String> {
    let context = format!("fragments[{position}]");
    entry.require_keys(
        &[
            "id",
            "file",
            "doc_id",
            "source_block_index",
            "note_kind",
            "byte_len",
            "status",
            "seed_span",
        ],
        &context,
    )?;
    let id = entry.get("id")?.as_str()?.to_owned();
    let context = format!("{context} (id '{id}')");
    if id.is_empty() {
        return Err(format!("{context}: empty fragment id"));
    }
    let file = entry.get("file")?.as_str()?.to_owned();
    if !is_safe_sample_file_name(&file) {
        return Err(format!("{context}: unsafe sample file name '{file}'"));
    }
    let doc_id = entry.get("doc_id")?.as_str()?.to_owned();
    if doc_id.is_empty() {
        return Err(format!("{context}: empty doc_id"));
    }
    let source_block_index = entry.get("source_block_index")?.as_usize()?;
    let note_kind = entry.get("note_kind")?.as_str()?.to_owned();
    if !SAMPLE_NOTE_KINDS.contains(&note_kind.as_str()) {
        return Err(format!(
            "{context}: unknown note_kind '{note_kind}' (Editorial is not in the S01 vocab)"
        ));
    }
    let status = entry.get("status")?.as_str()?.to_owned();
    if !SAMPLE_FRAGMENT_STATUSES.contains(&status.as_str()) {
        return Err(format!(
            "{context}: unknown fragment status '{status}' (seed is the only S01 status; the seed is not gold)"
        ));
    }
    let byte_len = entry.get("byte_len")?.as_usize()?;
    let text = files
        .get(&file)
        .ok_or_else(|| format!("{context}: manifest file '{file}' has no .txt fragment on disk"))?;
    if text.is_empty() {
        return Err(format!("{context} ({file}): fragment text is empty"));
    }
    if text.starts_with('\u{feff}') {
        return Err(format!(
            "{context} ({file}): fragment text carries a UTF-8 BOM"
        ));
    }
    if text.contains('\r') {
        return Err(format!(
            "{context} ({file}): fragment text carries CR (LF only)"
        ));
    }
    if byte_len != text.len() {
        return Err(format!(
            "{context} ({file}): byte_len {byte_len} does not equal the fragment file byte length {}",
            text.len()
        ));
    }
    let seed_span = match entry.get_opt("seed_span")? {
        None | Some(Json::Null) => None,
        Some(span_entry) => Some(validate_seed_span(span_entry, &context, &file, text)?),
    };
    Ok(SampleFragment {
        id,
        file,
        doc_id,
        source_block_index,
        note_kind,
        byte_len,
        status,
        seed_span,
    })
}

fn validate_seed_span(
    entry: &Json,
    context: &str,
    file: &str,
    text: &str,
) -> Result<SeedSpan, String> {
    let span_context = format!("{context} ({file}).seed_span");
    entry.require_keys(&["kind", "start", "end"], &span_context)?;
    let kind = validate_token_kind_name(entry.get("kind")?.as_str()?, &span_context)?;
    let start = entry.get("start")?.as_usize()?;
    let end = entry.get("end")?.as_usize()?;
    if start >= end {
        return Err(format!(
            "{span_context}: start {start} >= end {end} — the span must be non-empty [start,end)"
        ));
    }
    if end > text.len() {
        return Err(format!(
            "{span_context}: [{start},{end}) end {end} exceeds fragment text length {}",
            text.len()
        ));
    }
    if !text.is_char_boundary(start) || !text.is_char_boundary(end) {
        return Err(format!(
            "{span_context}: [{start},{end}) is not on char boundaries"
        ));
    }
    Ok(SeedSpan { kind, start, end })
}

/// Closed TokenKind name check for seed-span fields: `Editorial` fails by
/// name (wave-2 kind, absent from C2 by design) and `LawRef` fails
/// explicitly — it is a product type, not a TokenKind, and must not leak
/// into Layer-2 span fields (no LawRef type exists in src/ during S01).
fn validate_token_kind_name(kind: &str, context: &str) -> Result<&'static str, String> {
    if kind == "Editorial" {
        return Err(format!(
            "{context}: token kind 'Editorial' is not in the closed S01 TokenKind set"
        ));
    }
    if kind == "LawRef" {
        return Err(format!(
            "{context}: 'LawRef' is a product type, not a TokenKind — Layer-2 seed spans are TokenKind-based and no LawRef type may exist in src/ (S01 boundary)"
        ));
    }
    SAMPLE_TOKEN_KINDS
        .iter()
        .find(|candidate| **candidate == kind)
        .copied()
        .ok_or_else(|| format!("{context}: unknown token kind '{kind}'"))
}

pub(crate) fn is_safe_sample_file_name(name: &str) -> bool {
    name.len() > 4
        && name.ends_with(".txt")
        && !name.contains('/')
        && !name.contains('\\')
        && !name.contains("..")
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
}
