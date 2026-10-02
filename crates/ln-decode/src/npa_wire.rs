//! M207 hybrid records wire emitter (M211 S02, ADR-0029).
//!
//! Hand-rolled canonical JSON writer for `m207-hybrid-records/v1`
//! (`prd/annotation/m207-hybrid-records-contract.md`). No external JSON or
//! serialization crate is used: the emitted bytes reproduce
//! `json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"`,
//! so the frozen Python validator
//! (`scripts/m207_hybrid_eval_experiment.py --validate-records`) accepts the
//! output.
//!
//! The envelope is source-local and fail-closed: every fragment always
//! carries `source_utf8`, so `source_validation` is `bytes-present`, and
//! every anchor is a half-open UTF-8 byte span inside its fragment
//! (`npa_anchor::check_span` rules). `kind` stays a working label
//! (`act-requisites` construction), never adopted legal TYPE vocabulary.

use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

use crate::domain::ParsedBlock;
use crate::npa_anchor::LocalSpan;
use crate::npa_sweep::{
    walk_and_observe, FileTerminal, SweepObserver, EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING,
    EXIT_WALK_FAILED,
};

/// Closed schema tag of the records wire (contract §Version).
pub const RECORDS_SCHEMA: &str = "m207-hybrid-records/v1";
/// Integer schema version of [`RECORDS_SCHEMA`].
pub const RECORDS_SCHEMA_VERSION: u32 = 1;
/// Provenance origin reserved for bytes emitted by a Rust runtime exporter.
pub const RECORDS_ORIGIN_RUST: &str = "rust-runtime";
/// Working construction label (not adopted legal TYPE vocabulary).
pub const CONSTRUCTION_ACT_REQUISITES: &str = "act-requisites";
/// Derived source-validation value when every fragment carries bytes.
pub const SOURCE_VALIDATION_BYTES_PRESENT: &str = "bytes-present";
/// Alignment policy fixed by the contract.
pub const ALIGNMENT_POLICY: &str = "local-anchor-identity-v1";
/// `unresolved_reason` value when no TYPE hypothesis survived.
pub const REASON_TYPE_UNRESOLVED: &str = "type_unresolved";

/// One source fragment (a decoded paragraph block) with its typed
/// occurrences. `byte_length` is the UTF-8 byte length of `source_utf8`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireFragment {
    pub fragment_id: String,
    pub source_utf8: String,
    pub byte_length: usize,
    pub occurrences: Vec<WireOccurrence>,
}

/// One typed occurrence inside a fragment.
///
/// The plan's sketch lists `id, date, number, type_name, type_evidence,
/// unresolved`; `span` is carried as well because the occurrence's own
/// `anchors` and the `date`/`number` field sources are exactly this local
/// byte span (`LocalSpan.block` maps to the enclosing fragment id).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireOccurrence {
    pub id: String,
    pub date: String,
    pub number: String,
    pub type_name: String,
    pub span: LocalSpan,
    pub type_evidence: Option<LocalSpan>,
    pub unresolved: bool,
}

/// One document: an ordered list of fragments plus a derived bundle.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireDocument {
    pub document_id: String,
    pub fragments: Vec<WireFragment>,
}

/// Build a wire document from decoded block texts (fragment = block text).
///
/// Returns `None` when there are no blocks, so callers never emit an
/// invalid document with an empty `fragments` array. Typed members come
/// from the canonical `npa_typed::scan_typed` producer; `LocalSpan.block`
/// is the block index, which is also the fragment index.
pub fn wire_document_from_blocks(document_id: &str, blocks: &[String]) -> Option<WireDocument> {
    if blocks.is_empty() {
        return None;
    }
    let members = crate::npa_typed::scan_typed(blocks);
    let mut fragments = Vec::with_capacity(blocks.len());
    for (frag_index, text) in blocks.iter().enumerate() {
        let mut occurrences = Vec::new();
        for (occ_index, member) in members
            .iter()
            .filter(|m| m.span.block == frag_index)
            .enumerate()
        {
            occurrences.push(WireOccurrence {
                id: format!("occ-{frag_index}-{occ_index}"),
                date: member.date.clone(),
                number: member.number.clone(),
                type_name: member.type_name.clone(),
                span: member.span,
                type_evidence: member.type_evidence,
                unresolved: member.unresolved,
            });
        }
        fragments.push(WireFragment {
            fragment_id: format!("{document_id}#{frag_index}"),
            source_utf8: text.clone(),
            byte_length: text.len(),
            occurrences,
        });
    }
    Some(WireDocument {
        document_id: document_id.to_owned(),
        fragments,
    })
}

/// Render the closed-schema records envelope for `docs`.
///
/// `origin` is emitted verbatim as `provenance_origin`; the Rust CLI always
/// passes [`RECORDS_ORIGIN_RUST`]. The returned string is the canonical
/// UTF-8 bytes (no BOM) required by the contract.
pub fn render_records(docs: &[WireDocument], origin: &str) -> String {
    let documents: Vec<Json> = docs.iter().map(render_document).collect();
    let bundles: Vec<Json> = docs.iter().map(render_bundle).collect();
    let envelope = Json::obj(vec![
        ("schema", Json::Str(RECORDS_SCHEMA.to_owned())),
        ("schema_version", Json::Int(RECORDS_SCHEMA_VERSION as i64)),
        ("provenance_origin", Json::Str(origin.to_owned())),
        ("documents", Json::Arr(documents)),
        ("bundles", Json::Arr(bundles)),
        (
            "lifecycle",
            Json::Arr(vec![Json::Str("proposed".to_owned())]),
        ),
        ("authoritative", Json::Bool(false)),
        ("is_gold", Json::Bool(false)),
        ("not_human", Json::Bool(true)),
        ("not_s03_metrics", Json::Bool(true)),
        (
            "source_validation",
            Json::Str(SOURCE_VALIDATION_BYTES_PRESENT.to_owned()),
        ),
        ("alignment_policy", Json::Str(ALIGNMENT_POLICY.to_owned())),
        ("limits", Json::Arr(limit_rows())),
        ("non_claims", Json::Arr(non_claim_rows())),
    ]);
    let mut out = String::new();
    render_json(&envelope, 0, &mut out);
    out.push('\n');
    out
}

fn limit_rows() -> Vec<Json> {
    vec![
        Json::Str("rust-runtime export".to_owned()),
        Json::Str("not human, not gold, not S03 metrics".to_owned()),
        Json::Str("hand-rolled JSON wire".to_owned()),
    ]
}

fn non_claim_rows() -> Vec<Json> {
    vec![
        Json::Str("Does not measure legal correctness".to_owned()),
        Json::Str("Does not adopt TYPE vocabulary".to_owned()),
        Json::Str("Does not rewrite frozen S01-S04 stores".to_owned()),
    ]
}

fn render_document(doc: &WireDocument) -> Json {
    let fragments: Vec<Json> = doc
        .fragments
        .iter()
        .map(|f| {
            debug_assert_eq!(
                f.byte_length,
                f.source_utf8.len(),
                "byte_length must equal the source_utf8 UTF-8 byte length"
            );
            Json::obj(vec![
                ("fragment_id", Json::Str(f.fragment_id.clone())),
                ("byte_length", Json::Int(f.byte_length as i64)),
                ("source_utf8", Json::Str(f.source_utf8.clone())),
            ])
        })
        .collect();
    Json::obj(vec![
        ("document_id", Json::Str(doc.document_id.clone())),
        ("fragments", Json::Arr(fragments)),
    ])
}

fn render_bundle(doc: &WireDocument) -> Json {
    let declared_region: Vec<Json> = doc
        .fragments
        .iter()
        .map(|f| Json::Str(f.fragment_id.clone()))
        .collect();
    let mut occurrences = Vec::new();
    let mut first_id: Option<String> = None;
    for (frag_index, frag) in doc.fragments.iter().enumerate() {
        for occ in &frag.occurrences {
            if first_id.is_none() {
                first_id = Some(occ.id.clone());
            }
            occurrences.push(render_occurrence(doc, frag_index, frag, occ));
        }
    }
    let focus_id = first_id.unwrap_or_else(|| format!("{}#0", doc.document_id));
    Json::obj(vec![
        ("bundle_id", Json::Str(doc.document_id.clone())),
        (
            "construction",
            Json::Str(CONSTRUCTION_ACT_REQUISITES.to_owned()),
        ),
        ("focus_id", Json::Str(focus_id)),
        ("context_status", Json::Str("available".to_owned())),
        ("declared_region", Json::Arr(declared_region)),
        ("context_only", Json::Arr(Vec::new())),
        ("occurrences", Json::Arr(occurrences)),
        ("relations", Json::Arr(Vec::new())),
    ])
}

fn render_occurrence(
    doc: &WireDocument,
    frag_index: usize,
    frag: &WireFragment,
    occ: &WireOccurrence,
) -> Json {
    let anchor_fragment = if occ.span.block == frag_index {
        frag.fragment_id.clone()
    } else {
        fragment_id_for_block(doc, occ.span.block).unwrap_or_else(|| frag.fragment_id.clone())
    };
    let occurrence_anchor = anchor_json(&anchor_fragment, occ.span.start, occ.span.end);
    let kind_source = occ.type_evidence.map(|evidence| {
        let evidence_fragment =
            fragment_id_for_block(doc, evidence.block).unwrap_or_else(|| anchor_fragment.clone());
        anchor_json(&evidence_fragment, evidence.start, evidence.end)
    });
    let kind = Json::obj(vec![
        ("value", Json::Str(occ.type_name.clone())),
        ("source", kind_source.unwrap_or(Json::Null)),
    ]);
    let date = Json::obj(vec![
        ("value", Json::Str(occ.date.clone())),
        ("source", occurrence_anchor.clone()),
    ]);
    let number = Json::obj(vec![
        ("value", Json::Str(occ.number.clone())),
        ("source", occurrence_anchor.clone()),
    ]);
    let fields = Json::obj(vec![("kind", kind), ("date", date), ("number", number)]);
    let unresolved_reason = if occ.unresolved {
        Json::Str(REASON_TYPE_UNRESOLVED.to_owned())
    } else {
        Json::Null
    };
    Json::obj(vec![
        ("id", Json::Str(occ.id.clone())),
        ("anchors", Json::Arr(vec![occurrence_anchor])),
        ("unresolved", Json::Bool(occ.unresolved)),
        ("unresolved_reason", unresolved_reason),
        ("fields", fields),
    ])
}

fn fragment_id_for_block(doc: &WireDocument, block: usize) -> Option<String> {
    doc.fragments.get(block).map(|f| f.fragment_id.clone())
}

fn anchor_json(fragment_id: &str, start: usize, end: usize) -> Json {
    Json::obj(vec![
        ("fragment_id", Json::Str(fragment_id.to_owned())),
        ("start", Json::Int(start as i64)),
        ("end", Json::Int(end as i64)),
    ])
}

/// Minimal JSON value tree. Private: the module owns the closed wire shape.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Json {
    Null,
    Bool(bool),
    Int(i64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    fn obj(pairs: Vec<(&str, Json)>) -> Json {
        Json::Obj(pairs.into_iter().map(|(k, v)| (k.to_owned(), v)).collect())
    }
}

fn push_indent(out: &mut String, depth: usize) {
    for _ in 0..depth {
        out.push_str("  ");
    }
}

/// Canonical renderer matching `json.dumps(..., indent=2, sort_keys=True)`:
/// object keys are emitted in ascending order at every level, empty
/// containers stay inline, and non-empty containers are one entry per line.
fn render_json(value: &Json, depth: usize, out: &mut String) {
    match value {
        Json::Null => out.push_str("null"),
        Json::Bool(flag) => out.push_str(if *flag { "true" } else { "false" }),
        Json::Int(number) => {
            let _ = write!(out, "{number}");
        }
        Json::Str(text) => write_json_string(text, out),
        Json::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                push_indent(out, depth + 1);
                render_json(item, depth + 1, out);
            }
            out.push('\n');
            push_indent(out, depth);
            out.push(']');
        }
        Json::Obj(entries) => {
            let mut ordered: Vec<&(String, Json)> = entries.iter().collect();
            ordered.sort_by(|a, b| a.0.cmp(&b.0));
            if ordered.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (index, (key, val)) in ordered.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                push_indent(out, depth + 1);
                write_json_string(key, out);
                out.push_str(": ");
                render_json(val, depth + 1, out);
            }
            out.push('\n');
            push_indent(out, depth);
            out.push('}');
        }
    }
}

/// Python-compatible string escaping: quote, backslash, the short control
/// escapes, and `\u00xx` for the remaining C0 controls; legal UTF-8 passes
/// through verbatim (`ensure_ascii=False`).
fn write_json_string(text: &str, out: &mut String) {
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

// ---------------------------------------------------------------------------
// CLI runner (thin binary delegates here so contract tests exercise the
// library, not the shell). Mirrors the frames-baseline profile: strict argv,
// `--root` / `--out` / `--limit`, `npa_sweep::EXIT_*` codes.
// ---------------------------------------------------------------------------

/// Parsed argv of the `npa-hybrid-records` binary.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RecordsCli {
    pub root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
}

/// Strict stdlib argv parser: `--root`, `--out`, `--limit`. Unknown flags,
/// positionals, missing values, and non-numeric limits are usage errors.
pub fn parse_records_args<I>(args: I) -> Result<RecordsCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = RecordsCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                cli.limit =
                    Some(raw.parse().map_err(|_| {
                        format!("--limit expects a non-negative integer, got '{raw}'")
                    })?);
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

/// Everything the thin binary prints and exits with after one run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecordsRun {
    pub exit_code: u8,
    /// Rendered records; `None` on fatal paths (nothing valid to print).
    pub json: Option<String>,
    pub to_stdout: bool,
    pub stderr: String,
}

/// Collects one wire document per decoded corpus file, skipping files with
/// no decoded blocks (they would produce an empty `fragments` array).
struct RecordsObserver {
    documents: Vec<WireDocument>,
}

impl SweepObserver for RecordsObserver {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        if terminal != FileTerminal::Decoded {
            return;
        }
        let texts: Vec<String> = blocks.iter().map(|b| b.text().to_owned()).collect();
        if texts.is_empty() {
            return;
        }
        let document_id = path.to_string_lossy().into_owned();
        if let Some(doc) = wire_document_from_blocks(&document_id, &texts) {
            self.documents.push(doc);
        }
    }
}

/// Library-level runner: what the binary does after argv parsing. Walks the
/// corpus through the shared `npa_sweep` seam and renders one
/// `m207-hybrid-records/v1` file. Never emits an empty `documents` array:
/// a corpus with no decodable document is a non-zero exit, not invalid
/// output (Q5/Q7).
pub fn run_records(cli: &RecordsCli, default_root: &Path) -> RecordsRun {
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());
    if !root.is_dir() {
        return RecordsRun {
            exit_code: EXIT_ROOT_MISSING,
            json: None,
            to_stdout: false,
            stderr: format!("root not found: {}", root.display()),
        };
    }
    let mut observer = RecordsObserver {
        documents: Vec::new(),
    };
    if let Err(err) = walk_and_observe(&root, cli.limit, &mut observer) {
        return RecordsRun {
            exit_code: EXIT_WALK_FAILED,
            json: None,
            to_stdout: false,
            stderr: format!("walk failed: {err}"),
        };
    }
    if observer.documents.is_empty() {
        return RecordsRun {
            exit_code: EXIT_WALK_FAILED,
            json: None,
            to_stdout: false,
            stderr: "no documents produced (empty corpus or undecodable files)".to_owned(),
        };
    }
    let body = render_records(&observer.documents, RECORDS_ORIGIN_RUST);
    let stderr = format!(
        "documents={} fragments={}",
        observer.documents.len(),
        observer
            .documents
            .iter()
            .map(|d| d.fragments.len())
            .sum::<usize>()
    );
    match &cli.out {
        None => RecordsRun {
            exit_code: EXIT_OK,
            json: Some(body),
            to_stdout: true,
            stderr,
        },
        Some(out) => match write_atomic(Path::new(out), &body) {
            Ok(()) => RecordsRun {
                exit_code: EXIT_OK,
                json: None,
                to_stdout: false,
                stderr,
            },
            Err(err) => RecordsRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                json: None,
                to_stdout: false,
                stderr: format!("cannot open --out {out}: {err}"),
            },
        },
    }
}

fn write_atomic(path: &Path, body: &str) -> std::io::Result<()> {
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
    let result = fs::write(&tmp, body).and_then(|()| fs::rename(&tmp, path));
    if result.is_err() {
        let _ = fs::remove_file(tmp);
    }
    result
}

/// `EXIT_USAGE` re-export so the thin binary need not reach into `npa_sweep`
/// for the argv-error path.
pub use crate::npa_sweep::EXIT_USAGE as RECORDS_EXIT_USAGE;

#[cfg(test)]
mod internal_checks {
    use super::*;

    #[test]
    fn canonical_renderer_matches_python_shape() {
        let value = Json::obj(vec![
            ("b", Json::Arr(vec![Json::Int(1), Json::Int(2)])),
            ("a", Json::Bool(true)),
        ]);
        let mut out = String::new();
        render_json(&value, 0, &mut out);
        assert_eq!(out, "{\n  \"a\": true,\n  \"b\": [\n    1,\n    2\n  ]\n}");
    }

    #[test]
    fn empty_containers_stay_inline() {
        let value = Json::obj(vec![("a", Json::Arr(vec![])), ("b", Json::Null)]);
        let mut out = String::new();
        render_json(&value, 0, &mut out);
        assert_eq!(out, "{\n  \"a\": [],\n  \"b\": null\n}");
    }

    #[test]
    fn cyrillic_serializes_verbatim() {
        let mut out = String::new();
        write_json_string("контракт", &mut out);
        assert_eq!(out, "\"контракт\"");
    }
}
