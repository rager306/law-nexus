//! Thin `consumer-run` counts-only consumer binary (M223-d2q075 S07/T04).
//!
//! One invocation processes one Consultant WordML file through the **two S07
//! consumer surfaces** — the tokenizer (`reader_tokenizer`, T02) and the graph
//! projection (`npa_graph_projection`, T03) — and prints **exactly one** JSON
//! counts document to stdout (or `--out`), schema
//! `m223-s07-consumer-counts/v1`. The document carries counts, closed tokens
//! and hashes only: no raw decoded text ever reaches stdout, stderr or the
//! document.
//!
//! Both consumers read the **materialized JSONL layers**, never the source XML:
//!
//! * the tokenizer reads the rendered **cleaned wire JSONL** (`render_cleaned_projection`
//!   → `read_cleaned_wire` → `tokenize_from_wire`), copying provenance from the
//!   frozen reader projection segments;
//! * the graph projection reads the rendered **`npa-analysis` JSONL**
//!   (`render_npa_analysis` → `NpaGraph::import`), keying every node and edge by
//!   the composite `SourceIdentity ⊕ DocumentVersionRef`.
//!
//! The binary captures the source **once** as the producer step (exactly like
//! `reader-nav`); neither consumer module re-opens the XML — the T02/T03 source
//! scans assert that. The binary emits counts only, so the whole-corpus harness
//! can bind each entry to exactly one terminal consumer outcome.
//!
//! Repeat import is exercised in-process: the same analysis envelope is imported
//! twice into one graph and the second import must be an idempotent no-op
//! (`already_present`, `added_nodes == 0`, `added_edges == 0`, identical counts).
//!
//! Non-claims: not R1000 closure, not a semantic or legal interpretation, not
//! normalization, not authenticity, not physical pagination, not a cross-document
//! relation claim. Stdlib only: no clap, no serde.

use std::collections::BTreeMap;
use std::io::Write as _;
use std::path::PathBuf;
use std::process::ExitCode;

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::cleaned_wire::{
    WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::analyze_document;
use ln_decode::npa_analysis_wire::{
    AnalysisEnvelopeRequest, AnalysisLimits, AnalysisScope, render_npa_analysis,
};
use ln_decode::npa_graph_projection::{GraphCounts, NpaGraph};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::build_projection;
use ln_decode::reader_tokenizer::{
    DocumentIdentity, READER_TOKENIZER_PROFILE, ReaderToken, tokenize_from_wire,
};
use ln_decode::source_package::{Limits, MODEL, PROFILE, Package, capture};

const EXIT_USAGE: u8 = 2;
const EXIT_OUT_UNWRITABLE: u8 = 3;
const EXIT_INPUT_UNREADABLE: u8 = 4;
const EXIT_SOURCE_REFUSED: u8 = 5;
const EXIT_CONSUMER_REFUSED: u8 = 6;
const EXIT_INVARIANT_VIOLATION: u8 = 7;

const COUNTS_SCHEMA: &str = "m223-s07-consumer-counts/v1";

/// Stable `document_version_ref` label for the S07 consumer run. The triple is
/// completed by the per-document `source_revision` (= the source sha256) and the
/// frozen decoder profile, so every document version is distinct and repeatable.
const VERSION_REF: &str = "m223-s07-corpus/v1";

const USAGE: &str = "\
consumer-run — counts-only tokenizer + graph-projection consumer over one Consultant WordML file

USAGE:
    consumer-run --from-xml <path> [--out <path>]

FLAGS:
    --from-xml <path>  A Consultant WordML XML file. It is captured, projected,
                       materialized into the cleaned wire JSONL and the
                       npa-analysis JSONL, and both S07 consumers are run over
                       those saved layers; only counts are printed.
    --out <path>       Write the single JSON counts document to <path> instead
                       of stdout.
    -h, --help         Print this usage and exit 0.

OUTPUT (stdout, exactly one JSON document, no raw decoded text):
    schema, docs, tokens{total,source,derived,composite,by_class,derived_by_kind},
    graph{nodes,fragments,members,classifications,relations},
    repeat_import{already_present,added_nodes,added_edges,counts_identical},
    identity{source_sha256,source_bytes,parent_schema,document_version_ref,
             source_revision,decoder_profile},
    profiles{tokenizer,graph}

EXIT CODES:
    0  the single counts document was written
    2  usage error
    3  --out could not be opened for writing
    4  --from-xml could not be read
    5  the source is not admissible supported WordML (capture / gate refusal)
    6  a consumer refused (projection / cleaned wire / tokenizer / analysis / graph)
    7  a consumer accounting invariant was violated

Invariants enforced before printing: tokens.total == source + derived + composite;
the source by-class and derived by-kind tallies sum to their totals;
graph.nodes == fragments + members + classifications; the repeat import is an
idempotent no-op with byte-identical counts. This is bounded counts evidence, not
R1000 closure and not a semantic or authenticity claim.
";

/// One invocation's arguments.
struct Cli {
    from_xml: PathBuf,
    out: Option<PathBuf>,
}

fn parse_args(args: &[String]) -> Result<Cli, &'static str> {
    let mut from_xml: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--from-xml" => {
                index += 1;
                let value = args.get(index).ok_or("--from-xml needs a value")?;
                from_xml = Some(PathBuf::from(value));
            }
            "--out" => {
                index += 1;
                let value = args.get(index).ok_or("--out needs a value")?;
                out = Some(PathBuf::from(value));
            }
            _ => return Err("unknown argument"),
        }
        index += 1;
    }
    let from_xml = from_xml.ok_or("--from-xml is required")?;
    Ok(Cli { from_xml, out })
}

/// The counts of one document. Every field is a count, a boolean fact, a
/// closed-vocabulary token tally or a hash — never text.
#[derive(Debug, Default)]
struct Counts {
    docs: u64,
    tokens_total: u64,
    tokens_source: u64,
    tokens_derived: u64,
    tokens_composite: u64,
    tokens_by_class: BTreeMap<String, u64>,
    derived_by_kind: BTreeMap<String, u64>,
    graph: GraphCounts,
    repeat_already_present: bool,
    repeat_added_nodes: u64,
    repeat_added_edges: u64,
    repeat_counts_identical: bool,
    source_sha256: String,
    source_bytes: u64,
    parent_schema: String,
    document_version_ref: String,
    source_revision: String,
    decoder_profile: String,
}

/// Closed tally failure classes. Each maps to [`EXIT_INVARIANT_VIOLATION`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TallyError {
    /// `tokens.total != source + derived + composite`.
    TokenAccounting,
    /// A source by-class tally does not sum to the source token count.
    ClassAccounting,
    /// A derived by-kind tally does not sum to the derived token count.
    DerivedAccounting,
    /// `graph.nodes != fragments + members + classifications`.
    NodeAccounting,
    /// The repeat import was not an idempotent no-op with identical counts.
    RepeatImportNotIdempotent,
}

impl TallyError {
    const fn as_str(self) -> &'static str {
        match self {
            TallyError::TokenAccounting => "token_accounting",
            TallyError::ClassAccounting => "class_accounting",
            TallyError::DerivedAccounting => "derived_accounting",
            TallyError::NodeAccounting => "node_accounting",
            TallyError::RepeatImportNotIdempotent => "repeat_import_not_idempotent",
        }
    }
}

fn bump(map: &mut BTreeMap<String, u64>, token: &str) {
    *map.entry(token.to_string()).or_insert(0) += 1;
}

/// The materialized consumer layers for one document, plus its identity.
struct Consumed {
    tokens: Vec<ReaderToken>,
    graph: NpaGraph,
    identity: DocumentIdentity,
    repeat: (bool, usize, usize),
}

/// Runs the producer (capture + materialize) and both consumers over one file.
///
/// Returns the exit code and a closed stderr message (no decoded text) on
/// refusal, or the consumed layers.
///
/// When `M223_S07_TIMING` is set, a per-stage wall-time diagnostic is written
/// to stderr (counts and stage names only, never decoded text).
#[allow(unused_assignments)]
fn consume(bytes: &[u8]) -> Result<Consumed, (u8, String)> {
    let timing = std::env::var_os("M223_S07_TIMING").is_some();
    let start = std::time::Instant::now();
    #[allow(unused_mut)]
    let mut last = start;
    macro_rules! mark {
        ($label:expr) => {
            if timing {
                let now = std::time::Instant::now();
                eprintln!(
                    "timing {}: {}ms total {}ms",
                    $label,
                    (now - last).as_millis(),
                    (now - start).as_millis()
                );
                last = now;
            }
        };
    }
    let package: Package = capture(bytes, &Limits::default())
        .map_err(|error| (EXIT_SOURCE_REFUSED, format!("capture failed: {error}")))?;
    mark!("capture");
    match gate_reader(package.records()) {
        Ok(ReaderSourceClass::SupportedWordml) => {}
        Ok(other) => {
            return Err((
                EXIT_SOURCE_REFUSED,
                format!("source refused: {}", other.as_str()),
            ));
        }
        Err(_) => {
            return Err((
                EXIT_SOURCE_REFUSED,
                "source refused: source_not_wordml".to_string(),
            ));
        }
    }

    let records = package.records();
    let projection = build_projection(records)
        .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("projection_refused")))?;
    let index = ReaderRecordIndex::new(records)
        .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("record_index_refused")))?;

    // Producer step: materialize the cleaned wire JSONL. The tokenizer then
    // reads that saved layer, never the XML.
    let wire = render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    mark!("render_wire");
    let cleaned = read_cleaned_wire(&wire)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    mark!("read_wire");

    // Producer step: materialize the npa-analysis JSONL from the same captured
    // package. The graph projection reads that saved layer.
    let source_identity = SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        MODEL.to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("analysis_identity_refused")))?;
    let version = DocumentVersionRef::try_new(
        VERSION_REF.to_string(),
        package.manifest().source.sha256.clone(),
        PROFILE.to_string(),
    )
    .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("analysis_version_refused")))?;
    let mut mapping = SourceMapping::new(source_identity.clone(), version.clone());
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &source_identity,
            )
            .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("analysis_mapping_refused")))?;
    }
    let analysis = analyze_document(&projection, &index, &mapping)
        .map_err(|_| (EXIT_CONSUMER_REFUSED, refused("analysis_refused")))?;
    mark!("analyze");
    let request = AnalysisEnvelopeRequest {
        analysis: &analysis,
        projection: &projection,
        index: &index,
        mapping: &mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    };
    let envelope = render_npa_analysis(&request)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    mark!("render_analysis");

    // Tokenizer consumer: reads the saved cleaned wire + the already-captured
    // substrate package; copies provenance verbatim, never fabricates.
    let token_identity = DocumentIdentity::from_cleaned(&cleaned, version)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    let stream = tokenize_from_wire(&wire, &package, &token_identity)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    mark!("tokenize");

    // Graph consumer: reads the saved analysis JSONL. Repeat import must be an
    // idempotent no-op with byte-identical counts.
    let mut graph = NpaGraph::new();
    graph
        .import(&envelope)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    let first = graph.counts();
    mark!("import1");
    let second = graph
        .import(&envelope)
        .map_err(|error| (EXIT_CONSUMER_REFUSED, refused(error.kind().as_str())))?;
    mark!("import2");
    let repeat = (
        second.already_present,
        second.added_nodes,
        second.added_edges,
    );
    if second.counts != first {
        return Err((EXIT_CONSUMER_REFUSED, refused("repeat_import_counts_drift")));
    }

    Ok(Consumed {
        tokens: stream.tokens,
        graph,
        identity: token_identity,
        repeat,
    })
}

/// The closed stderr message for a consumer refusal.
fn refused(token: &str) -> String {
    format!("consumer failed: {token}")
}

/// Tallies one consumed document into the fixed counts document shape.
fn tally(consumed: &Consumed) -> Result<Counts, TallyError> {
    let mut counts = Counts {
        docs: 1,
        graph: consumed.graph.counts(),
        repeat_already_present: consumed.repeat.0,
        repeat_added_nodes: consumed.repeat.1 as u64,
        repeat_added_edges: consumed.repeat.2 as u64,
        repeat_counts_identical: true,
        source_sha256: consumed.identity.source.source_sha256.clone(),
        source_bytes: consumed.identity.source.source_bytes,
        parent_schema: consumed.identity.source.parent_schema.clone(),
        document_version_ref: consumed.identity.version.document_version_ref().to_string(),
        source_revision: consumed.identity.version.source_revision().to_string(),
        decoder_profile: consumed.identity.version.decoder_profile().to_string(),
        ..Counts::default()
    };

    for token in &consumed.tokens {
        match token {
            ReaderToken::Source { class, .. } => {
                counts.tokens_source += 1;
                bump(&mut counts.tokens_by_class, class.as_str());
            }
            ReaderToken::DerivedControl { derived_kind, .. } => {
                counts.tokens_derived += 1;
                bump(&mut counts.derived_by_kind, derived_kind.as_str());
            }
            ReaderToken::Composite { .. } => counts.tokens_composite += 1,
        }
    }
    counts.tokens_total = counts.tokens_source + counts.tokens_derived + counts.tokens_composite;

    // Invariants: closed accounting before printing.
    if counts.tokens_total != counts.tokens_source + counts.tokens_derived + counts.tokens_composite
    {
        return Err(TallyError::TokenAccounting);
    }
    let class_sum: u64 = counts.tokens_by_class.values().sum();
    if class_sum != counts.tokens_source {
        return Err(TallyError::ClassAccounting);
    }
    let derived_sum: u64 = counts.derived_by_kind.values().sum();
    if derived_sum != counts.tokens_derived {
        return Err(TallyError::DerivedAccounting);
    }
    if counts.graph.nodes() as u64
        != (counts.graph.fragments + counts.graph.members + counts.graph.classifications) as u64
    {
        return Err(TallyError::NodeAccounting);
    }
    if !counts.repeat_already_present
        || counts.repeat_added_nodes != 0
        || counts.repeat_added_edges != 0
        || !counts.repeat_counts_identical
    {
        return Err(TallyError::RepeatImportNotIdempotent);
    }
    Ok(counts)
}

// ------------------------------------------------------------------ render #

/// A minimal JSON value for the fixed counts document.
enum JVal<'a> {
    Num(u64),
    Bool(bool),
    Str(&'a str),
    Obj(&'a BTreeMap<String, u64>),
}

/// Writes a JSON object with the given ordered entries. Keys and string values
/// are known safe tokens (identifiers, closed vocabulary tokens and hashes), so
/// no escaping is needed.
fn write_object(out: &mut String, entries: &[(&str, JVal<'_>)]) {
    out.push('{');
    for (position, (key, value)) in entries.iter().enumerate() {
        if position > 0 {
            out.push(',');
        }
        out.push('"');
        out.push_str(key);
        out.push_str("\":");
        match value {
            JVal::Num(number) => out.push_str(&number.to_string()),
            JVal::Bool(flag) => out.push_str(if *flag { "true" } else { "false" }),
            JVal::Str(text) => {
                out.push('"');
                out.push_str(text);
                out.push('"');
            }
            JVal::Obj(map) => {
                out.push('{');
                for (inner, (token, count)) in map.iter().enumerate() {
                    if inner > 0 {
                        out.push(',');
                    }
                    out.push('"');
                    out.push_str(token);
                    out.push_str("\":");
                    out.push_str(&count.to_string());
                }
                out.push('}');
            }
        }
    }
    out.push('}');
}

/// Renders the single counts document. Deterministic: the tally maps are
/// `BTreeMap`s, so the key order is stable.
fn render(counts: &Counts) -> String {
    let mut out = String::new();
    write_object(
        &mut out,
        &[
            ("schema", JVal::Str(COUNTS_SCHEMA)),
            ("docs", JVal::Num(counts.docs)),
            ("tokens_total", JVal::Num(counts.tokens_total)),
            ("tokens_source", JVal::Num(counts.tokens_source)),
            ("tokens_derived", JVal::Num(counts.tokens_derived)),
            ("tokens_composite", JVal::Num(counts.tokens_composite)),
            ("tokens_by_class", JVal::Obj(&counts.tokens_by_class)),
            ("derived_by_kind", JVal::Obj(&counts.derived_by_kind)),
        ],
    );
    // graph + repeat_import + identity + profiles appended as nested objects.
    out.pop(); // drop the trailing '}' of the first object
    out.push(',');
    out.push_str("\"graph\":");
    write_object(
        &mut out,
        &[
            ("nodes", JVal::Num(counts.graph.nodes() as u64)),
            ("fragments", JVal::Num(counts.graph.fragments as u64)),
            ("members", JVal::Num(counts.graph.members as u64)),
            (
                "classifications",
                JVal::Num(counts.graph.classifications as u64),
            ),
            ("relations", JVal::Num(counts.graph.relations as u64)),
        ],
    );
    out.push(',');
    out.push_str("\"repeat_import\":");
    write_object(
        &mut out,
        &[
            ("already_present", JVal::Bool(counts.repeat_already_present)),
            ("added_nodes", JVal::Num(counts.repeat_added_nodes)),
            ("added_edges", JVal::Num(counts.repeat_added_edges)),
            (
                "counts_identical",
                JVal::Bool(counts.repeat_counts_identical),
            ),
        ],
    );
    out.push(',');
    out.push_str("\"identity\":");
    write_object(
        &mut out,
        &[
            ("source_sha256", JVal::Str(&counts.source_sha256)),
            ("source_bytes", JVal::Num(counts.source_bytes)),
            ("parent_schema", JVal::Str(&counts.parent_schema)),
            (
                "document_version_ref",
                JVal::Str(&counts.document_version_ref),
            ),
            ("source_revision", JVal::Str(&counts.source_revision)),
            ("decoder_profile", JVal::Str(&counts.decoder_profile)),
        ],
    );
    out.push(',');
    out.push_str("\"profiles\":");
    write_object(
        &mut out,
        &[
            ("tokenizer", JVal::Str(READER_TOKENIZER_PROFILE)),
            (
                "graph",
                JVal::Str(ln_decode::npa_graph_projection::NPA_GRAPH_PROJECTION_PROFILE),
            ),
        ],
    );
    out.push('}');
    out
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match parse_args(&args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("consumer-run: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(EXIT_USAGE);
        }
    };

    let bytes = match std::fs::read(&cli.from_xml) {
        Ok(bytes) => bytes,
        Err(_) => {
            eprintln!("consumer-run: cannot read --from-xml");
            return ExitCode::from(EXIT_INPUT_UNREADABLE);
        }
    };

    let consumed = match consume(&bytes) {
        Ok(consumed) => consumed,
        Err((code, message)) => {
            eprintln!("consumer-run: {message}");
            return ExitCode::from(code);
        }
    };

    let counts = match tally(&consumed) {
        Ok(counts) => counts,
        Err(error) => {
            eprintln!("consumer-run: invariant violation: {}", error.as_str());
            return ExitCode::from(EXIT_INVARIANT_VIOLATION);
        }
    };

    let document = render(&counts);
    match &cli.out {
        Some(path) => match std::fs::write(path, document.as_bytes()) {
            Ok(()) => ExitCode::SUCCESS,
            Err(_) => {
                eprintln!("consumer-run: output unwritable");
                ExitCode::from(EXIT_OUT_UNWRITABLE)
            }
        },
        None => {
            let mut stdout = std::io::stdout().lock();
            if stdout.write_all(document.as_bytes()).is_err() {
                return ExitCode::from(EXIT_OUT_UNWRITABLE);
            }
            let _ = stdout.write_all(b"\n");
            let _ = stdout.flush();
            ExitCode::SUCCESS
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_is_deterministic_and_carries_the_schema() {
        let mut counts = Counts {
            docs: 1,
            tokens_total: 3,
            tokens_source: 2,
            tokens_derived: 1,
            repeat_already_present: true,
            repeat_counts_identical: true,
            source_sha256: "a".repeat(64),
            source_bytes: 12,
            parent_schema: "law-nexus/cleaned-projection/v1".to_string(),
            document_version_ref: VERSION_REF.to_string(),
            source_revision: "b".repeat(64),
            decoder_profile: "source_package_decoded_text/v1".to_string(),
            ..Counts::default()
        };
        counts.tokens_by_class.insert("word".into(), 2);
        counts.derived_by_kind.insert("tab".into(), 1);
        counts.graph.fragments = 2;
        counts.graph.members = 1;
        let first = render(&counts);
        let second = render(&counts);
        assert_eq!(first, second);
        assert!(first.contains("\"schema\":\"m223-s07-consumer-counts/v1\""));
        assert!(first.contains("\"tokens_by_class\":{\"word\":2}"));
        assert!(first.contains("\"repeat_import\":{\"already_present\":true"));
        assert!(first.contains("\"graph\":{\"nodes\":3"));
    }

    #[test]
    fn parse_args_requires_from_xml() {
        assert!(parse_args(&[]).is_err());
        assert!(parse_args(&["--out".into(), "x.json".into()]).is_err());
        let cli = parse_args(&["--from-xml".into(), "in.xml".into()]).expect("parses");
        assert_eq!(cli.from_xml, PathBuf::from("in.xml"));
        assert!(cli.out.is_none());
    }

    #[test]
    fn tally_rejects_broken_accounting() {
        let identity = DocumentIdentity::new(
            SourceIdentity::try_new(
                "a".repeat(64),
                1,
                ln_decode::cleaned_wire::CLEANED_PROJECTION_SCHEMA.to_string(),
                None,
                None,
            )
            .expect("identity"),
            DocumentVersionRef::try_new(
                VERSION_REF.to_string(),
                "rev".to_string(),
                "profile".to_string(),
            )
            .expect("version"),
        );
        let consumed = Consumed {
            tokens: vec![],
            graph: NpaGraph::new(),
            identity,
            repeat: (false, 0, 0),
        };
        // The empty graph's repeat import was not observed as already-present.
        assert_eq!(
            tally(&consumed).err(),
            Some(TallyError::RepeatImportNotIdempotent)
        );
    }
}
