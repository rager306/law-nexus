//! Thin `reader-nav` counts-only census binary (M223-d2q075 S06/T04).
//!
//! One invocation processes one XML file through the frozen reader pipeline —
//! `capture` → `build_projection` → `ReadingOrderIndex::build` →
//! `CleanView::build` → `build_navigation` — and prints **exactly one** JSON
//! counts document to stdout (or `--out`). The document carries counts only:
//! views / segments / references, per-kind tallies, resolved / unresolved-by-
//! reason tallies, max depth / path length, subtree character counts and a
//! document count. Raw decoded text never reaches stdout, stderr or the
//! document. No pagination field is emitted.
//!
//! The binary re-parses no XML for structure, order, provenance or reference
//! endpoints: it consumes the already-materialized projection, the S04 reading
//! order, the S05 clean view and the substrate records, exactly as
//! `build_navigation` documents. `build_navigation` itself does not re-parse.
//!
//! Non-claims: not R1000 closure, not a semantic or legal interpretation, not
//! normalization, not authenticity, not physical pagination, not temporal
//! structure. A non-zero exit is fail-closed: no partial document is printed.
//! Stdlib only: no clap, no serde.

use std::collections::BTreeMap;
use std::io::Write as _;
use std::path::PathBuf;
use std::process::ExitCode;

use ln_decode::reader_clean_view::CleanView;
use ln_decode::reader_gate::gate_reader;
use ln_decode::reader_navigation::{
    NavLinkKind, NavNodeBody, NavNodeKind, NavigationIndex, NodeAddress, build_navigation,
};
use ln_decode::reader_projection::build_projection;
use ln_decode::reader_reading_order::ReadingOrderIndex;
use ln_decode::source_package::{Limits, capture};

const EXIT_USAGE: u8 = 2;
const EXIT_OUT_UNWRITABLE: u8 = 3;
const EXIT_INPUT_UNREADABLE: u8 = 4;
const EXIT_SOURCE_REFUSED: u8 = 5;
const EXIT_BUILD_FAILED: u8 = 6;
const EXIT_INVARIANT_VIOLATION: u8 = 7;

const COUNTS_SCHEMA: &str = "m223-s06-navigation-counts/v1";

const USAGE: &str = "\
reader-nav — counts-only navigation census over one Consultant WordML file

USAGE:
    reader-nav --from-xml <path> [--out <path>]

FLAGS:
    --from-xml <path>  A Consultant WordML XML file. It is captured, projected,
                       ordered, cleaned and navigated; only counts are printed.
    --out <path>       Write the single JSON counts document to <path> instead
                       of stdout.
    -h, --help         Print this usage and exit 0.

OUTPUT (stdout, exactly one JSON document, no raw decoded text):
    schema, views, segments, references, views_by_kind, segments_by_kind,
    segments_by_origin, references_by_type, links_by_kind, resolved,
    unresolved, unresolved_by_reason, max_depth, max_path_len, subtree_chars,
    docs, path_terminal, cycles

EXIT CODES:
    0  the single counts document was written
    2  usage error
    3  --out could not be opened for writing
    4  --from-xml could not be read
    5  the source is not admissible supported WordML (capture / gate refusal)
    6  the projection, reading order, clean view or navigation build refused
    7  an index invariant was violated (reference accounting, cycle, non-terminal path)

Invariants enforced before printing: resolved + unresolved == references;
path_to_root is terminal (root-first, ends at the queried view); no parent
cycle; no pagination field. This is bounded counts evidence, not R1000 closure
and not a semantic or authenticity claim.
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

/// The counts of one document. Every field is a count, a boolean fact or a
/// closed-vocabulary token tally — never text.
#[derive(Debug, Default)]
struct Counts {
    views: u64,
    segments: u64,
    references: u64,
    views_by_kind: BTreeMap<String, u64>,
    segments_by_kind: BTreeMap<String, u64>,
    segments_by_origin: BTreeMap<String, u64>,
    references_by_type: BTreeMap<String, u64>,
    links_by_kind: BTreeMap<String, u64>,
    resolved: u64,
    unresolved: u64,
    unresolved_by_reason: BTreeMap<String, u64>,
    max_depth: u64,
    max_path_len: u64,
    subtree_primary: u64,
    subtree_service: u64,
    docs: u64,
    path_terminal: bool,
}

/// Closed tally failure classes. Each maps to [`EXIT_INVARIANT_VIOLATION`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TallyError {
    /// `resolved + unresolved != references`.
    ReferenceAccounting,
    /// A view's `parent_view` chain is cyclic or unbounded.
    ParentCycle,
    /// `path_to_root` did not end at a root view (non-terminal).
    NonTerminalPath,
}

impl TallyError {
    const fn as_str(self) -> &'static str {
        match self {
            TallyError::ReferenceAccounting => "reference_accounting",
            TallyError::ParentCycle => "parent_cycle",
            TallyError::NonTerminalPath => "non_terminal_path",
        }
    }
}

fn bump(map: &mut BTreeMap<String, u64>, token: &str) {
    *map.entry(token.to_string()).or_insert(0) += 1;
}

/// Tallies one built navigation index. Pure: it only reads the index and the
/// clean view.
fn tally(index: &NavigationIndex, clean: &CleanView) -> Result<Counts, TallyError> {
    let mut counts = Counts {
        docs: 1,
        ..Counts::default()
    };

    for node in index.nodes_by_address.values() {
        match node.kind {
            NavNodeKind::View => {
                counts.views += 1;
                if let NavNodeBody::View { view_kind, .. } = &node.body {
                    bump(&mut counts.views_by_kind, view_kind.as_str());
                }
            }
            NavNodeKind::Segment => {
                counts.segments += 1;
                if let NavNodeBody::Segment {
                    segment_kind,
                    origin,
                    ..
                } = &node.body
                {
                    bump(&mut counts.segments_by_kind, segment_kind.as_str());
                    bump(&mut counts.segments_by_origin, origin.as_str());
                }
            }
            NavNodeKind::Reference => {
                counts.references += 1;
                if let NavNodeBody::Reference { reference_type, .. } = &node.body {
                    bump(&mut counts.references_by_type, reference_type.as_str());
                }
            }
        }
    }

    for link in &index.links {
        bump(&mut counts.links_by_kind, link.kind.as_str());
        if link.kind == NavLinkKind::ResolvesTo {
            counts.resolved += 1;
        }
    }
    counts.unresolved = index.resolve_reasons.len() as u64;
    for reason in index.resolve_reasons.values() {
        bump(&mut counts.unresolved_by_reason, reason.as_str());
    }

    // Reference accounting: every reference node has exactly one of a
    // `ResolvesTo` link or a closed `NavResolveReason`.
    if counts.resolved + counts.unresolved != counts.references {
        return Err(TallyError::ReferenceAccounting);
    }

    // Structure / path: `path_to_root` must be root-first, terminal and
    // cycle-free for every view.
    counts.path_terminal = true;
    for node in index.nodes_by_address.values() {
        let NavNodeBody::View { .. } = &node.body else {
            continue;
        };
        let view = match &node.address {
            NodeAddress::View(view) => view,
            _ => continue,
        };
        let chain = match index.path_to_root(view) {
            Ok(chain) => chain,
            Err(_) => return Err(TallyError::ParentCycle),
        };
        if chain.last() != Some(view) {
            return Err(TallyError::NonTerminalPath);
        }
        let Some(root) = chain.first() else {
            return Err(TallyError::NonTerminalPath);
        };
        if index.parent(root).is_some() {
            return Err(TallyError::NonTerminalPath);
        }
        let path_len = chain.len() as u64;
        let depth = path_len - 1;
        counts.max_path_len = counts.max_path_len.max(path_len);
        counts.max_depth = counts.max_depth.max(depth);
    }

    // Subtree text: the document's root-subtree text length, taken from the S05
    // `CleanView` totals. The root views partition every view, so the sum of
    // their subtrees equals the whole clean view; navigation views carry no
    // text and are absent from the clean view. This is O(1), never a per-root
    // rescan of the reading order.
    counts.subtree_primary = clean.primary_text().chars().count() as u64;
    counts.subtree_service = clean.service_text().chars().count() as u64;

    Ok(counts)
}

// ------------------------------------------------------------------ render #

/// A minimal JSON value for the fixed counts document: a number, a boolean or a
/// tally object with safe token keys.
enum JVal<'a> {
    Num(u64),
    Bool(bool),
    Str(&'static str),
    Obj(&'a BTreeMap<String, u64>),
}

/// Writes a JSON object with the given ordered entries. Keys are known safe
/// tokens (identifiers and closed vocabulary tokens), so no escaping is needed.
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
            ("views", JVal::Num(counts.views)),
            ("segments", JVal::Num(counts.segments)),
            ("references", JVal::Num(counts.references)),
            ("views_by_kind", JVal::Obj(&counts.views_by_kind)),
            ("segments_by_kind", JVal::Obj(&counts.segments_by_kind)),
            ("segments_by_origin", JVal::Obj(&counts.segments_by_origin)),
            ("references_by_type", JVal::Obj(&counts.references_by_type)),
            ("links_by_kind", JVal::Obj(&counts.links_by_kind)),
            ("resolved", JVal::Num(counts.resolved)),
            ("unresolved", JVal::Num(counts.unresolved)),
            (
                "unresolved_by_reason",
                JVal::Obj(&counts.unresolved_by_reason),
            ),
            ("max_depth", JVal::Num(counts.max_depth)),
            ("max_path_len", JVal::Num(counts.max_path_len)),
            ("subtree_chars_primary", JVal::Num(counts.subtree_primary)),
            ("subtree_chars_service", JVal::Num(counts.subtree_service)),
            ("docs", JVal::Num(counts.docs)),
            ("path_terminal", JVal::Bool(counts.path_terminal)),
            ("cycles", JVal::Num(0)),
        ],
    );
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
            eprintln!("reader-nav: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(EXIT_USAGE);
        }
    };

    let bytes = match std::fs::read(&cli.from_xml) {
        Ok(bytes) => bytes,
        Err(_) => {
            eprintln!("reader-nav: input unreadable");
            return ExitCode::from(EXIT_INPUT_UNREADABLE);
        }
    };
    let package = match capture(&bytes, &Limits::default()) {
        Ok(package) => package,
        Err(_) => {
            eprintln!("reader-nav: capture refused");
            return ExitCode::from(EXIT_SOURCE_REFUSED);
        }
    };
    if gate_reader(package.records()).is_err() {
        eprintln!("reader-nav: source not admissible wordml");
        return ExitCode::from(EXIT_SOURCE_REFUSED);
    }
    let records = package.records();

    let projection = match build_projection(records) {
        Ok(projection) => projection,
        Err(_) => {
            eprintln!("reader-nav: projection refused");
            return ExitCode::from(EXIT_BUILD_FAILED);
        }
    };
    let order = match ReadingOrderIndex::build(&projection, records) {
        Ok(order) => order,
        Err(_) => {
            eprintln!("reader-nav: reading order refused");
            return ExitCode::from(EXIT_BUILD_FAILED);
        }
    };
    let clean = match CleanView::build(&projection, &order, records) {
        Ok(clean) => clean,
        Err(_) => {
            eprintln!("reader-nav: clean view refused");
            return ExitCode::from(EXIT_BUILD_FAILED);
        }
    };
    let index = match build_navigation(&projection, &order, records) {
        Ok(index) => index,
        Err(_) => {
            eprintln!("reader-nav: navigation refused");
            return ExitCode::from(EXIT_BUILD_FAILED);
        }
    };
    let counts = match tally(&index, &clean) {
        Ok(counts) => counts,
        Err(error) => {
            eprintln!("reader-nav: invariant violation: {}", error.as_str());
            return ExitCode::from(EXIT_INVARIANT_VIOLATION);
        }
    };

    let document = render(&counts);
    match &cli.out {
        Some(path) => match std::fs::write(path, document.as_bytes()) {
            Ok(()) => ExitCode::SUCCESS,
            Err(_) => {
                eprintln!("reader-nav: output unwritable");
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
            views: 2,
            segments: 3,
            references: 1,
            resolved: 1,
            docs: 1,
            path_terminal: true,
            ..Counts::default()
        };
        counts.views_by_kind.insert("paragraph".into(), 2);
        counts.links_by_kind.insert("owns".into(), 3);
        let first = render(&counts);
        let second = render(&counts);
        assert_eq!(first, second);
        assert!(first.contains("\"schema\":\"m223-s06-navigation-counts/v1\""));
        assert!(first.contains("\"views_by_kind\":{\"paragraph\":2}"));
        assert!(first.contains("\"path_terminal\":true"));
    }

    #[test]
    fn parse_args_requires_from_xml() {
        assert!(parse_args(&[]).is_err());
        assert!(parse_args(&["--out".into(), "x.json".into()]).is_err());
        let cli = parse_args(&["--from-xml".into(), "in.xml".into()]).expect("parses");
        assert_eq!(cli.from_xml, PathBuf::from("in.xml"));
        assert!(cli.out.is_none());
    }
}
