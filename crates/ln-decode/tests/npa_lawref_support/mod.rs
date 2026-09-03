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

/// Optional rule-seed span on a manifest fragment (projection
/// {kind, start, end}; the scanner's richer `SeedSpan` lives in the T03
/// section below).
#[derive(Debug)]
pub(crate) struct ManifestSeedSpan {
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
    pub(crate) seed_span: Option<ManifestSeedSpan>,
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
) -> Result<ManifestSeedSpan, String> {
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
    Ok(ManifestSeedSpan { kind, start, end })
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

/// Fragment texts by file name, for the T03 scanner and artifact parsers.
pub(crate) fn load_sample_files(fragments_dir: &Path) -> Result<BTreeMap<String, String>, String> {
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
    Ok(files)
}

// ---------------------------------------------------------------------------
// T03: test-only rule-seed scanner over the frozen C2 lexer.
//
// Distant-supervision seed (protocol §10): deterministic, linear, patterns
// carried as DATA (the closed `pattern_id` table below) — never as src/
// types. The scanner observes what `lex()` already decided (C2 frozen):
// fullword tails stay Word (never retagged to Abbrev), hostile 1-letter
// initials and currency stay unpromoted, ranges and anaphora are recorded
// as unresolved candidates, never expanded or resolved (S03 work). No regex
// over raw text, no `references.rs` reuse, no product type.
// ---------------------------------------------------------------------------

use ln_decode::lexer::{lex, NpaToken, TokenKind};

pub(crate) const SEED_SCHEMA: &str = "npa-lawref-seed/v1";
pub(crate) const SEED_PROVENANCE: &str = "rule-seed";

/// Closed pattern-id table (plan T03 do 1: patterns are data, not src types).
pub(crate) const SEED_PATTERN_IDS: [&str; 7] = [
    "abbrev-hier-chain",
    "abbrev-amendment-window",
    "date-docno-window",
    "fullword-ref",
    "quoted-enum",
    "range_candidate",
    "anaphora_candidate",
];

/// Protocol §5 closed span-slot set (exactly eight; `not_a_reference` is a
/// fragment-level code, not a span slot).
const SLOT_KEYS: [&str; 8] = [
    "marker_chain",
    "hier_nums",
    "date",
    "doc_no",
    "law_code",
    "anaphora",
    "range",
    "quoted_enum",
];

/// Chain-forming abbrev ids (plan (a)): compact combined chains.
const CHAIN_ABBREV_IDS: [&str; 9] = ["st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd"];
/// Amendment markers (plan (b)): `ред.` / `изм.` windows.
const AMENDMENT_ABBREV_IDS: [&str; 2] = ["red", "izm"];
/// Markers allowed before a quoted enum label (plan (e)).
const QUOTED_MARKER_ABBREV_IDS: [&str; 2] = ["p", "pp"];
/// Fullword reference tails (plan (d)): genitive fullwords the C2 lexer
/// keeps as Word — the seed observes that, never retags to Abbrev.
const FULLWORD_TAILS: [&str; 4] = ["статьи", "пункта", "закона", "года"];
/// Anaphora heads (plan (g)): unresolved marker class (protocol §6).
const ANAPHORA_HEADS: [&str; 4] = ["настоящей", "настоящего", "настоящая", "того"];

/// Slot guesses for one candidate span. Every value is a short lexeme or a
/// canonical id reconstructed by slicing the fragment text — never a raw
/// sentence (Q3 hygiene: seed JSONL carries no payload sentences).
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct SeedSlots {
    pub(crate) marker_chain: Vec<String>,
    pub(crate) hier_nums: Vec<String>,
    pub(crate) date: Option<String>,
    pub(crate) doc_no: Option<String>,
    pub(crate) law_code: Option<String>,
    pub(crate) anaphora: Option<String>,
    pub(crate) range: Option<(String, String)>,
    pub(crate) quoted_enum: Option<String>,
}

impl SeedSlots {
    fn empty() -> Self {
        Self {
            marker_chain: Vec::new(),
            hier_nums: Vec::new(),
            date: None,
            doc_no: None,
            law_code: None,
            anaphora: None,
            range: None,
            quoted_enum: None,
        }
    }

    fn render(&self) -> String {
        let chain = self
            .marker_chain
            .iter()
            .map(|id| format!("\"{id}\""))
            .collect::<Vec<_>>()
            .join(",");
        let nums = self
            .hier_nums
            .iter()
            .map(|num| format!("\"{}\"", json_escape(num)))
            .collect::<Vec<_>>()
            .join(",");
        let opt = |value: &Option<String>| match value {
            Some(value) => format!("\"{}\"", json_escape(value)),
            None => "null".to_string(),
        };
        let range = match &self.range {
            Some((from, to)) => format!(
                "{{\"from\":\"{}\",\"to\":\"{}\"}}",
                json_escape(from),
                json_escape(to)
            ),
            None => "null".to_string(),
        };
        format!(
            "{{\"marker_chain\":[{chain}],\"hier_nums\":[{nums}],\"date\":{},\"doc_no\":{},\"law_code\":{},\"anaphora\":{},\"range\":{},\"quoted_enum\":{}}}",
            opt(&self.date),
            opt(&self.doc_no),
            opt(&self.law_code),
            opt(&self.anaphora),
            range,
            opt(&self.quoted_enum),
        )
    }
}

/// One rule-seed candidate span on the fragment text: `[start, end)` byte
/// range, the TokenKind of the first covered token as the span kind, the
/// closed pattern id, the covered TokenKind sequence, and slot guesses.
#[derive(Debug, Clone)]
pub(crate) struct SeedSpan {
    pub(crate) start: usize,
    pub(crate) end: usize,
    pub(crate) kind: &'static str,
    pub(crate) pattern_id: &'static str,
    pub(crate) token_kind_seq: String,
    pub(crate) slots: SeedSlots,
}

/// One seed record: candidate span bound to its fragment.
#[derive(Debug)]
pub(crate) struct SeedRecord {
    pub(crate) fragment_id: String,
    pub(crate) span: SeedSpan,
}

fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => out.push(ch),
        }
    }
    out
}

fn seq_of(tokens: &[NpaToken], first: usize, last: usize) -> String {
    tokens[first..=last]
        .iter()
        .map(|token| token.kind.as_str())
        .collect::<Vec<_>>()
        .join(",")
}

fn abbrev_id_of(token: &NpaToken, ids: &[&str]) -> Option<&'static str> {
    if token.kind != TokenKind::Abbrev {
        return None;
    }
    let id = token.abbrev_id?.as_str();
    ids.contains(&id).then_some(id)
}

/// Number slot: a dotted HierNum or a bare digit Word. C2 lexes bare part
/// numbers (`ч. 2`) as digit Words, and the chain observes both shapes.
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

/// Containment (strict on at least one side) used for duplicate suppression.
fn contained_in(span: &SeedSpan, other: &SeedSpan) -> bool {
    (other.start < span.start && span.end <= other.end)
        || (other.start <= span.start && span.end < other.end)
}

/// Plan (a): `Abbrev(chain) (Space Abbrev Space number)* Space number` —
/// compact combined chains like `ст. 15.1`, `ч. 2 ст. 15`, `пп. 2 п. 1`.
fn match_chain(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    let first_id = abbrev_id_of(&tokens[index], &CHAIN_ABBREV_IDS)?;
    if index + 2 >= tokens.len() {
        return None;
    }
    if tokens[index + 1].kind != TokenKind::Space || !is_number_token(&tokens[index + 2], src) {
        return None;
    }
    let mut marker_chain = vec![first_id.to_owned()];
    let mut hier_nums = vec![tokens[index + 2].lexeme(src).to_owned()];
    let mut last = index + 2;
    while last + 3 < tokens.len() {
        if tokens[last + 1].kind != TokenKind::Space {
            break;
        }
        let Some(next_id) = abbrev_id_of(&tokens[last + 2], &CHAIN_ABBREV_IDS) else {
            break;
        };
        if tokens[last + 3].kind != TokenKind::Space {
            break;
        }
        if last + 4 >= tokens.len() || !is_number_token(&tokens[last + 4], src) {
            break;
        }
        marker_chain.push(next_id.to_owned());
        hier_nums.push(tokens[last + 4].lexeme(src).to_owned());
        last += 4;
    }
    Some(SeedSpan {
        start: tokens[index].span.start(),
        end: tokens[last].span.end(),
        kind: tokens[index].kind.as_str(),
        pattern_id: "abbrev-hier-chain",
        token_kind_seq: seq_of(tokens, index, last),
        slots: SeedSlots {
            marker_chain,
            hier_nums,
            ..SeedSlots::empty()
        },
    })
}

/// Plan (b): `Abbrev(red|izm) … Date … DocNo` — amendment requisite windows
/// with bounded Space/Word/Punct filler between the anchors.
fn match_amendment(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    abbrev_id_of(&tokens[index], &AMENDMENT_ABBREV_IDS)?;
    let mut cursor = index + 1;
    let mut gap = 0usize;
    let date_index = loop {
        let token = tokens.get(cursor)?;
        match token.kind {
            TokenKind::Date => break cursor,
            TokenKind::Space | TokenKind::Word | TokenKind::Punct if gap < 16 => {
                cursor += 1;
                gap += 1;
            }
            _ => return None,
        }
    };
    let mut cursor = date_index + 1;
    let mut gap = 0usize;
    loop {
        let token = tokens.get(cursor)?;
        match token.kind {
            TokenKind::DocNo => {
                return Some(SeedSpan {
                    start: tokens[index].span.start(),
                    end: token.span.end(),
                    kind: tokens[index].kind.as_str(),
                    pattern_id: "abbrev-amendment-window",
                    token_kind_seq: seq_of(tokens, index, cursor),
                    slots: SeedSlots {
                        date: Some(tokens[date_index].lexeme(src).to_owned()),
                        doc_no: Some(token.lexeme(src).to_owned()),
                        ..SeedSlots::empty()
                    },
                });
            }
            TokenKind::Space | TokenKind::Word | TokenKind::Punct if gap < 4 => {
                cursor += 1;
                gap += 1;
            }
            _ => return None,
        }
    }
}

/// Plan (c): `Date … (DocNo|LawCode)` requisite windows (a lone Date is too
/// weak to seed a reference; the window needs a document anchor).
fn match_date_window(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    if tokens[index].kind != TokenKind::Date {
        return None;
    }
    let last = (index + 4).min(tokens.len().saturating_sub(1));
    for cursor in index + 1..=last {
        match tokens[cursor].kind {
            TokenKind::DocNo | TokenKind::LawCode => {
                let mut slots = SeedSlots::empty();
                slots.date = Some(tokens[index].lexeme(src).to_owned());
                if tokens[cursor].kind == TokenKind::DocNo {
                    slots.doc_no = Some(tokens[cursor].lexeme(src).to_owned());
                } else {
                    slots.law_code = Some(tokens[cursor].lexeme(src).to_owned());
                }
                return Some(SeedSpan {
                    start: tokens[index].span.start(),
                    end: tokens[cursor].span.end(),
                    kind: tokens[index].kind.as_str(),
                    pattern_id: "date-docno-window",
                    token_kind_seq: seq_of(tokens, index, cursor),
                    slots,
                });
            }
            TokenKind::Space | TokenKind::Word | TokenKind::Punct => continue,
            _ => return None,
        }
    }
    None
}

/// Plan (d): fullword tails (`статьи`/`пункта`/`закона`/`года`) adjacent to
/// a HierNum/DocNo. Coded `fullword-ref` with `marker_chain = []` — the tail
/// stays a Word exactly as the C2 lexer classified it (never retagged).
fn match_fullword(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    if tokens[index].kind != TokenKind::Word || !FULLWORD_TAILS.contains(&tokens[index].lexeme(src))
    {
        return None;
    }
    if index + 2 >= tokens.len() || tokens[index + 1].kind != TokenKind::Space {
        return None;
    }
    let anchor = &tokens[index + 2];
    let mut slots = SeedSlots::empty();
    if anchor.kind == TokenKind::DocNo {
        slots.doc_no = Some(anchor.lexeme(src).to_owned());
    } else if is_number_token(anchor, src) {
        // Dotted HierNum or bare digit Word — same number slot as the chain.
        slots.hier_nums = vec![anchor.lexeme(src).to_owned()];
    } else {
        return None;
    }
    Some(SeedSpan {
        start: tokens[index].span.start(),
        end: tokens[index + 2].span.end(),
        kind: tokens[index].kind.as_str(),
        pattern_id: "fullword-ref",
        token_kind_seq: seq_of(tokens, index, index + 2),
        slots,
    })
}

/// Plan (e): quoted EnumMarker `Punct(") EnumMarker Punct(")` preceded by a
/// `пп.`/`п.` marker or a `подпункт*` fullword — span covers marker + label.
fn match_quoted_enum(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    if tokens[index].kind != TokenKind::EnumMarker || index < 3 {
        return None;
    }
    if tokens[index - 1].kind != TokenKind::Punct || tokens[index - 1].lexeme(src) != "\"" {
        return None;
    }
    let closing = tokens.get(index + 1)?;
    if closing.kind != TokenKind::Punct || !closing.lexeme(src).starts_with('"') {
        return None;
    }
    if tokens[index - 2].kind != TokenKind::Space {
        return None;
    }
    let marker = &tokens[index - 3];
    let (marker_chain, marker_ok) = match abbrev_id_of(marker, &QUOTED_MARKER_ABBREV_IDS) {
        Some(id) => (vec![id.to_owned()], true),
        None => (
            Vec::new(),
            marker.kind == TokenKind::Word && marker.lexeme(src).starts_with("подпункт"),
        ),
    };
    if !marker_ok {
        return None;
    }
    Some(SeedSpan {
        start: marker.span.start(),
        end: closing.span.end(),
        kind: marker.kind.as_str(),
        pattern_id: "quoted-enum",
        token_kind_seq: seq_of(tokens, index - 3, index + 1),
        slots: SeedSlots {
            marker_chain,
            quoted_enum: Some(tokens[index].lexeme(src).to_owned()),
            ..SeedSlots::empty()
        },
    })
}

/// Plan (f): `HierNum Space Punct(-) Space HierNum` → `range_candidate`.
/// Endpoints are recorded as written; the range is never expanded (S03).
fn match_range(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    if index + 4 >= tokens.len() || tokens[index].kind != TokenKind::HierNum {
        return None;
    }
    if tokens[index + 1].kind != TokenKind::Space
        || tokens[index + 2].kind != TokenKind::Punct
        || tokens[index + 2].lexeme(src) != "-"
        || tokens[index + 3].kind != TokenKind::Space
        || tokens[index + 4].kind != TokenKind::HierNum
    {
        return None;
    }
    Some(SeedSpan {
        start: tokens[index].span.start(),
        end: tokens[index + 4].span.end(),
        kind: tokens[index].kind.as_str(),
        pattern_id: "range_candidate",
        token_kind_seq: seq_of(tokens, index, index + 4),
        slots: SeedSlots {
            range: Some((
                tokens[index].lexeme(src).to_owned(),
                tokens[index + 4].lexeme(src).to_owned(),
            )),
            ..SeedSlots::empty()
        },
    })
}

/// Plan (g): `настоящей`/`того же` + article/section word →
/// `anaphora_candidate`. Recorded as written, never resolved (S03).
fn match_anaphora(tokens: &[NpaToken], index: usize, src: &str) -> Option<SeedSpan> {
    if tokens[index].kind != TokenKind::Word || !ANAPHORA_HEADS.contains(&tokens[index].lexeme(src))
    {
        return None;
    }
    let mut cursor = index + 1;
    if tokens.get(cursor)?.kind != TokenKind::Space {
        return None;
    }
    cursor += 1;
    let mut marker_words = vec![tokens[index].lexeme(src).to_owned()];
    if tokens
        .get(cursor)
        .is_some_and(|token| token.kind == TokenKind::Word && token.lexeme(src) == "же")
    {
        marker_words.push("же".to_owned());
        cursor += 1;
        if tokens.get(cursor)?.kind != TokenKind::Space {
            return None;
        }
        cursor += 1;
    }
    if tokens.get(cursor)?.kind != TokenKind::Word {
        return None;
    }
    Some(SeedSpan {
        start: tokens[index].span.start(),
        end: tokens[cursor].span.end(),
        kind: tokens[index].kind.as_str(),
        pattern_id: "anaphora_candidate",
        token_kind_seq: seq_of(tokens, index, cursor),
        slots: SeedSlots {
            anaphora: Some(marker_words.join(" ")),
            ..SeedSlots::empty()
        },
    })
}

/// Scans one decoded fragment text into deterministic rule-seed candidate
/// spans (sorted by start/end/pattern). Linear over `lex()` tokens; no raw
/// regex, no references.rs, no product type.
pub(crate) fn seed_spans(text: &str) -> Vec<SeedSpan> {
    if text.is_empty() {
        return Vec::new();
    }
    let tokens = lex(text);
    let mut spans = Vec::new();
    for index in 0..tokens.len() {
        if let Some(span) = match_amendment(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_chain(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_date_window(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_fullword(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_quoted_enum(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_range(&tokens, index, text) {
            spans.push(span);
        }
        if let Some(span) = match_anaphora(&tokens, index, text) {
            spans.push(span);
        }
    }
    // Duplicate suppression, deterministic by construction:
    // (1) a date window fully inside an amendment window is the same
    //     requisite counted twice;
    // (2) a candidate fully inside a same-pattern candidate that starts
    //     earlier is a double fire (chain-in-chain).
    let drop: Vec<bool> = spans
        .iter()
        .map(|span| {
            (span.pattern_id == "date-docno-window"
                && spans.iter().any(|other| {
                    other.pattern_id == "abbrev-amendment-window" && contained_in(span, other)
                }))
                || spans
                    .iter()
                    .any(|other| other.pattern_id == span.pattern_id && contained_in(span, other))
        })
        .collect();
    let mut kept = Vec::with_capacity(spans.len());
    for (index, span) in spans.into_iter().enumerate() {
        if !drop[index] {
            kept.push(span);
        }
    }
    kept.sort_by_key(|span| (span.start, span.end, span.pattern_id));
    kept
}

impl SeedSpan {
    fn render_record(&self, fragment_id: &str) -> String {
        format!(
            "{{\"fragment_id\":\"{}\",\"start\":{},\"end\":{},\"kind\":\"{}\",\"pattern_id\":\"{}\",\"token_kind_seq\":\"{}\",\"slots\":{},\"provenance\":\"{}\"}}",
            json_escape(fragment_id),
            self.start,
            self.end,
            self.kind,
            self.pattern_id,
            json_escape(&self.token_kind_seq),
            self.slots.render(),
            SEED_PROVENANCE,
        )
    }
}

/// Scans every manifest fragment (sorted by id) into the deterministic seed
/// record list.
pub(crate) fn scan_tracked_fragments(
    manifest: &SampleManifest,
    files: &BTreeMap<String, String>,
) -> Vec<SeedRecord> {
    let mut fragments: Vec<(&str, &str)> = manifest
        .fragments
        .iter()
        .filter_map(|fragment| {
            files
                .get(&fragment.file)
                .map(|text| (fragment.id.as_str(), text.as_str()))
        })
        .collect();
    fragments.sort_unstable();
    let mut records = Vec::new();
    for (id, text) in fragments {
        for span in seed_spans(text) {
            records.push(SeedRecord {
                fragment_id: id.to_owned(),
                span,
            });
        }
    }
    records
}

/// Renders the tracked JSONL: one line per candidate span, records sorted by
/// (fragment_id, start, end, pattern_id). Byte-identical across re-runs.
pub(crate) fn render_seed_jsonl(records: &[SeedRecord]) -> String {
    let mut out = String::new();
    for record in records {
        out.push_str(&record.span.render_record(&record.fragment_id));
        out.push('\n');
    }
    out
}

/// Renders the fixtures-side seed sidecar with the same span records.
pub(crate) fn render_lawref_seed_json(records: &[SeedRecord]) -> String {
    let mut out = String::from(
        "{\n  \"schema\": \"npa-lawref-seed/v1\",\n  \"provenance\": \"rule-seed\",\n  \"spans\": [\n",
    );
    for (index, record) in records.iter().enumerate() {
        out.push_str("    ");
        out.push_str(&record.span.render_record(&record.fragment_id));
        if index + 1 != records.len() {
            out.push(',');
        }
        out.push('\n');
    }
    out.push_str("  ]\n}\n");
    out
}

fn parse_slots(entry: &Json, context: &str) -> Result<SeedSlots, String> {
    entry.require_keys(&SLOT_KEYS, context)?;
    let mut marker_chain = Vec::new();
    for item in entry.get("marker_chain")?.as_arr()? {
        let id = item.as_str()?;
        if id.is_empty()
            || !id
                .bytes()
                .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
        {
            return Err(format!(
                "{context}: marker_chain id '{id}' is not a closed abbrev id"
            ));
        }
        marker_chain.push(id.to_owned());
    }
    let mut hier_nums = Vec::new();
    for item in entry.get("hier_nums")?.as_arr()? {
        let num = item.as_str()?;
        if num.is_empty()
            || !num
                .bytes()
                .all(|byte| byte.is_ascii_digit() || byte == b'.')
        {
            return Err(format!(
                "{context}: hier_nums entry '{num}' is not a dotted number"
            ));
        }
        hier_nums.push(num.to_owned());
    }
    let opt_string = |key: &str| -> Result<Option<String>, String> {
        match entry.get(key)? {
            Json::Null => Ok(None),
            Json::Str(value) => Ok(Some(value.clone())),
            other => Err(format!(
                "{context}: slot '{key}' must be a string or null, found {other:?}"
            )),
        }
    };
    let date = opt_string("date")?;
    if let Some(date) = &date {
        let bytes = date.as_bytes();
        let digit = |offset: usize| bytes.get(offset).is_some_and(|byte| byte.is_ascii_digit());
        let shaped = bytes.len() == 10
            && digit(0)
            && digit(1)
            && bytes[2] == b'.'
            && digit(3)
            && digit(4)
            && bytes[5] == b'.'
            && (6..10).all(digit);
        if !shaped {
            return Err(format!("{context}: date slot '{date}' is not dd.mm.yyyy"));
        }
    }
    let doc_no = opt_string("doc_no")?;
    let law_code = opt_string("law_code")?;
    if let Some(code) = &law_code {
        if code != "ФЗ" && code != "ФКЗ" {
            return Err(format!(
                "{context}: law_code slot '{code}' is outside the closed ФЗ/ФКЗ set"
            ));
        }
    }
    let anaphora = opt_string("anaphora")?;
    let quoted_enum = opt_string("quoted_enum")?;
    let range = match entry.get("range")? {
        Json::Null => None,
        range_entry @ Json::Obj(_) => {
            range_entry.require_keys(&["from", "to"], &format!("{context}.range"))?;
            let from = range_entry.get("from")?.as_str()?;
            let to = range_entry.get("to")?.as_str()?;
            for endpoint in [from, to] {
                if endpoint.is_empty()
                    || !endpoint
                        .bytes()
                        .all(|byte| byte.is_ascii_digit() || byte == b'.')
                {
                    return Err(format!(
                        "{context}: range endpoint '{endpoint}' is not a dotted number"
                    ));
                }
            }
            Some((from.to_owned(), to.to_owned()))
        }
        other => {
            return Err(format!(
                "{context}: range slot must be null or an object, found {other:?}"
            ))
        }
    };
    Ok(SeedSlots {
        marker_chain,
        hier_nums,
        date,
        doc_no,
        law_code,
        anaphora,
        range,
        quoted_enum,
    })
}

fn parse_seed_object(
    value: &Json,
    context: &str,
    manifest: &SampleManifest,
    files: &BTreeMap<String, String>,
) -> Result<SeedRecord, String> {
    value.require_keys(
        &[
            "fragment_id",
            "start",
            "end",
            "kind",
            "pattern_id",
            "token_kind_seq",
            "slots",
            "provenance",
        ],
        context,
    )?;
    let fragment_id = value.get("fragment_id")?.as_str()?.to_owned();
    let start = value.get("start")?.as_usize()?;
    let end = value.get("end")?.as_usize()?;
    let kind = validate_token_kind_name(value.get("kind")?.as_str()?, context)?;
    let pattern_id_raw = value.get("pattern_id")?.as_str()?;
    let pattern_id = SEED_PATTERN_IDS
        .iter()
        .find(|id| **id == pattern_id_raw)
        .copied()
        .ok_or_else(|| format!("{context}: unknown pattern_id '{pattern_id_raw}'"))?;
    let token_kind_seq = value.get("token_kind_seq")?.as_str()?;
    for part in token_kind_seq.split(',') {
        if !SAMPLE_TOKEN_KINDS.contains(&part) {
            return Err(format!(
                "{context}: token_kind_seq part '{part}' is outside the closed C2 kind set"
            ));
        }
    }
    let provenance = value.get("provenance")?.as_str()?;
    if provenance != SEED_PROVENANCE {
        return Err(format!(
            "{context}: provenance '{provenance}' != '{SEED_PROVENANCE}'"
        ));
    }
    let slots = parse_slots(value.get("slots")?, context)?;
    let text = fragment_text(&fragment_id, manifest, files)
        .ok_or_else(|| format!("{context}: unknown fragment '{fragment_id}'"))?;
    if start >= end {
        return Err(format!("{context}: [{start},{end}) is empty"));
    }
    if end > text.len() {
        return Err(format!(
            "{context}: [{start},{end}) exceeds fragment length {}",
            text.len()
        ));
    }
    if !text.is_char_boundary(start) || !text.is_char_boundary(end) {
        return Err(format!(
            "{context}: [{start},{end}) is not on char boundaries"
        ));
    }
    Ok(SeedRecord {
        fragment_id,
        span: SeedSpan {
            start,
            end,
            kind,
            pattern_id,
            token_kind_seq: token_kind_seq.to_owned(),
            slots,
        },
    })
}

/// Fail-closed JSONL reader: closed record keys, closed vocabularies,
/// coordinate contract against the fragment text, and the determinism shape
/// (strictly ascending (fragment_id, start, end, pattern_id)).
/// Resolves a fragment id to its text via the manifest (id -> file -> text).
fn fragment_text<'a>(
    fragment_id: &str,
    manifest: &SampleManifest,
    files: &'a BTreeMap<String, String>,
) -> Option<&'a str> {
    let fragment = manifest.fragments.iter().find(|f| f.id == fragment_id)?;
    files.get(&fragment.file).map(|text| text.as_str())
}

pub(crate) fn parse_seed_jsonl(
    text: &str,
    manifest: &SampleManifest,
    files: &BTreeMap<String, String>,
) -> Result<Vec<SeedRecord>, String> {
    let mut records = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let value = JsonParser::new(line)
            .parse_document()
            .map_err(|err| format!("seed record line {}: {err}", index + 1))?;
        records.push(parse_seed_object(
            &value,
            &format!("seed record line {}", index + 1),
            manifest,
            files,
        )?);
    }
    for pair in records.windows(2) {
        let a = (
            &pair[0].fragment_id,
            pair[0].span.start,
            pair[0].span.end,
            pair[0].span.pattern_id,
        );
        let b = (
            &pair[1].fragment_id,
            pair[1].span.start,
            pair[1].span.end,
            pair[1].span.pattern_id,
        );
        if a >= b {
            return Err(format!(
                "seed JSONL records must be strictly ascending by (fragment_id, start, end, pattern_id); found {a:?} followed by {b:?}"
            ));
        }
    }
    Ok(records)
}

/// Fail-closed reader for the fixtures-side seed sidecar.
pub(crate) fn parse_lawref_seed_json(
    text: &str,
    manifest: &SampleManifest,
    files: &BTreeMap<String, String>,
) -> Result<Vec<SeedRecord>, String> {
    let root = JsonParser::new(text)
        .parse_document()
        .map_err(|err| format!("lawref_seed.json: {err}"))?;
    root.require_keys(&["schema", "provenance", "spans"], "lawref_seed.json")?;
    let schema = root.get("schema")?.as_str()?;
    if schema != SEED_SCHEMA {
        return Err(format!(
            "lawref_seed.json schema '{schema}' != '{SEED_SCHEMA}'"
        ));
    }
    let provenance = root.get("provenance")?.as_str()?;
    if provenance != SEED_PROVENANCE {
        return Err(format!(
            "lawref_seed.json provenance '{provenance}' != '{SEED_PROVENANCE}'"
        ));
    }
    let mut records = Vec::new();
    for (index, entry) in root.get("spans")?.as_arr()?.iter().enumerate() {
        records.push(parse_seed_object(
            entry,
            &format!("lawref_seed.json spans[{index}]"),
            manifest,
            files,
        )?);
    }
    Ok(records)
}

/// Deterministic DS-noise nested subsample (plan T03 do 4): 20 fragments,
/// at least 2 per primary family, allocated by largest remainder over family
/// fragment counts, then a midpoint stride within each family's sorted ids.
/// The rule sees only sorted ids, never content: no cherry-picking.
pub(crate) fn ds_noise_subsample(manifest: &SampleManifest) -> Vec<(String, String)> {
    const TOTAL: usize = 20;
    let total_fragments = manifest.fragments.len();
    assert!(
        total_fragments >= TOTAL,
        "the sample must hold at least {TOTAL} fragments for the DS-noise subsample"
    );
    let doc_family: BTreeMap<&str, &str> = manifest
        .documents
        .iter()
        .map(|doc| (doc.doc_id.as_str(), doc.family.as_str()))
        .collect();
    let mut by_family: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for fragment in &manifest.fragments {
        if let Some(family) = doc_family.get(fragment.doc_id.as_str()) {
            by_family
                .entry((*family).to_owned())
                .or_default()
                .push(fragment.id.clone());
        }
    }
    let mut families: Vec<(String, Vec<String>)> = by_family.into_iter().collect();
    for (_, ids) in &mut families {
        ids.sort();
    }
    // Base allocation: max(2, floor(TOTAL * family_frags / total_frags));
    // top-up to exactly TOTAL by largest remainder (tie: family name asc).
    let mut allocs: Vec<(String, usize, u64, usize)> = families
        .iter()
        .map(|(family, ids)| {
            let product = TOTAL as u64 * ids.len() as u64;
            let base = ((product / total_fragments as u64) as usize).max(2);
            (
                family.clone(),
                base,
                product % total_fragments as u64,
                ids.len(),
            )
        })
        .collect();
    let mut allocated: usize = allocs.iter().map(|alloc| alloc.1).sum();
    assert!(
        allocated <= TOTAL,
        "base DS-noise allocation must not exceed the {TOTAL}-fragment budget"
    );
    while allocated < TOTAL {
        let pick = allocs
            .iter_mut()
            .filter(|alloc| alloc.1 < alloc.3)
            .min_by(|a, b| b.2.cmp(&a.2).then_with(|| b.0.cmp(&a.0)))
            .expect("families must cover the DS-noise budget");
        pick.1 += 1;
        allocated += 1;
    }
    let mut out = Vec::new();
    for (index, (family, ids)) in families.iter().enumerate() {
        let selected = allocs[index].1;
        for i in 0..selected {
            let position = ((2 * i + 1) * ids.len()) / (2 * selected);
            out.push((family.clone(), ids[position].clone()));
        }
    }
    out.sort();
    out
}
