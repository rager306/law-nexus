//! Count-only diagnostic baseline for bounded document context (D385-D388).
//!
//! The profile reuses `npa_sweep::walk_and_observe` and records only structural
//! counts, terminal statuses, and measured bounds. Source text and payloads are
//! never rendered.

use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

use crate::document_context::{
    build_document_analysis_overlay, build_document_structure_index, ContextEnvironment,
    ContextRequest, ContextRequestKind, ContextStatus, ContextWorklist, ContextualEdgeKind,
    DocumentVersionRef, PROPOSED_MAX_ADJACENT_RADIUS, PROPOSED_MAX_ALIAS_CANDIDATES,
    PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD, PROPOSED_MAX_SERIES_HOPS,
    PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
};
use crate::domain::ParsedBlock;
use crate::lawref::capture_lawrefs;
use crate::local_grammar::{extract_act_list_frames, extract_structural_frames};
use crate::morphology::find_legal_markers;
use crate::npa_sweep::{walk_and_observe, FileTerminal, SweepObserver};

pub use crate::npa_sweep::{
    EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING, EXIT_USAGE, EXIT_WALK_FAILED,
};

pub const CONTEXT_SCHEMA: &str = "npa-context-baseline/v1";
pub const CONTEXT_SCHEMA_VERSION: u32 = 1;
const STATUS_NAMES: [&str; 6] = [
    "resolved",
    "partial",
    "conflicting",
    "unavailable",
    "cycle",
    "limit",
];
const REQUEST_NAMES: [&str; 6] = [
    "ancestor_path",
    "adjacent_blocks",
    "open_series_head",
    "scoped_alias",
    "current_document_requisites",
    "explicit_anchor_lookup",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextCli {
    pub root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
    pub label: String,
    pub progress_every: Option<u64>,
    pub progress_stderr: bool,
}
impl Default for ContextCli {
    fn default() -> Self {
        Self {
            root: None,
            out: None,
            limit: None,
            label: "fixture-gate".to_owned(),
            progress_every: None,
            progress_stderr: false,
        }
    }
}

pub fn parse_context_baseline_args<I>(args: I) -> Result<ContextCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = ContextCli::default();
    let mut it = args.into_iter();
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut it, "--root")?),
            "--out" => cli.out = Some(next_value(&mut it, "--out")?),
            "--label" => cli.label = next_value(&mut it, "--label")?,
            "--limit" => {
                cli.limit = Some(
                    next_value(&mut it, "--limit")?
                        .parse()
                        .map_err(|_| "--limit expects a non-negative integer".to_owned())?,
                )
            }
            "--progress" => {
                let n: u64 = next_value(&mut it, "--progress")?
                    .parse()
                    .map_err(|_| "--progress expects a positive integer".to_owned())?;
                if n == 0 {
                    return Err("--progress expects a positive integer".to_owned());
                }
                cli.progress_every = Some(n);
            }
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    Ok(cli)
}
fn next_value(it: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    it.next().ok_or_else(|| format!("missing value for {flag}"))
}

#[derive(Debug, Default)]
pub struct ContextBaselineAcc {
    files_attempted: u64,
    files_decoded: u64,
    malformed: u64,
    unreadable: u64,
    blocks: u64,
    containers: u64,
    aliases: u64,
    series_edges: u64,
    requests: [u64; 6],
    statuses: [u64; 6],
    memo_hits: u64,
    max_steps: u64,
    max_series_hops: u64,
    max_fan_out: u64,
    max_claims: u64,
    max_adjacent: u64,
    limit_events: u64,
    cycle_events: u64,
}
impl ContextBaselineAcc {
    fn observe_block_document(&mut self, blocks: &[ParsedBlock]) {
        self.blocks += blocks.len() as u64;
        let Ok(version) = DocumentVersionRef::try_new(
            "baseline-document".into(),
            "corpus-run".into(),
            "consultant-wordml".into(),
        ) else {
            return;
        };
        let Ok(index) = build_document_structure_index(version, blocks) else {
            return;
        };
        self.containers += index.containers().len() as u64;
        let mut frame_rows = Vec::new();
        let mut capture_rows = Vec::new();
        for (i, block) in blocks.iter().enumerate() {
            let Ok(block_id) = crate::document_context::BlockId::parse(&format!("block-{i}"))
            else {
                continue;
            };
            let tokens = crate::lexer::lex(block.text());
            let captures = capture_lawrefs(block.text());
            let acts = extract_act_list_frames(block.text(), &captures);
            let structural =
                extract_structural_frames(&tokens, block.text(), &find_legal_markers(block.text()));
            frame_rows.push((block_id.clone(), acts, structural));
            capture_rows.push((block_id, captures.captures().to_vec()));
        }
        let Ok(overlay) = build_document_analysis_overlay(&index, &frame_rows, &capture_rows)
        else {
            return;
        };
        self.aliases += overlay.aliases().len() as u64;
        self.series_edges += overlay
            .edges()
            .iter()
            .filter(|e| {
                matches!(
                    e.relation,
                    ContextualEdgeKind::OpensSeries
                        | ContextualEdgeKind::ContinuesSeries
                        | ContextualEdgeKind::ClosesSeries
                )
            })
            .count() as u64;
        self.max_fan_out = self.max_fan_out.max(overlay.edges().len() as u64);
        let mut requests = Vec::new();
        for frame in overlay.frames() {
            let kinds = [
                ContextRequestKind::OpenSeriesHead,
                ContextRequestKind::ExplicitAnchorLookup,
            ];
            for kind in kinds {
                let key = if kind == ContextRequestKind::ExplicitAnchorLookup {
                    Some(frame.frame_ref.as_str().to_owned())
                } else {
                    None
                };
                requests.push(ContextRequest::new(
                    kind,
                    "baseline-document".into(),
                    frame.frame_ref.clone(),
                    Vec::new(),
                    None,
                    key,
                    Vec::new(),
                    PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
                    "baseline".into(),
                ));
            }
        }
        if let Some(first) = overlay.frames().first() {
            requests.push(ContextRequest::new(
                ContextRequestKind::CurrentDocumentRequisites,
                "baseline-document".into(),
                first.frame_ref.clone(),
                Vec::new(),
                None,
                None,
                Vec::new(),
                0,
                "grammar-evidence".into(),
            ));
        }
        for request in &requests {
            self.requests[request_index(request.kind())] += 1;
        }
        let mut worklist = ContextWorklist::new(Default::default());
        let report = worklist.run(
            ContextEnvironment {
                index: &index,
                overlay: &overlay,
                requisites: None,
            },
            &requests,
        );
        self.memo_hits += report.stats.memo_hits as u64;
        self.max_steps = self.max_steps.max(report.stats.steps_used as u64);
        for (status, count) in report.stats.terminal_distribution {
            self.statuses[status_index(status)] += count as u64;
            if status == ContextStatus::Limit {
                self.limit_events += count as u64;
            }
            if status == ContextStatus::Cycle {
                self.cycle_events += count as u64;
            }
        }
        self.max_series_hops = self.max_series_hops.max(PROPOSED_MAX_SERIES_HOPS as u64);
        self.max_adjacent = self.max_adjacent.max(PROPOSED_MAX_ADJACENT_RADIUS as u64);
        self.max_claims = self
            .max_claims
            .max(PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD as u64);
    }
    pub fn render_jsonl(&self, label: &str, root: &Path, run_status: &str) -> String {
        let mut out = String::new();
        let _ = writeln!(out, "{{\"record_kind\":\"header\",\"schema\":\"{CONTEXT_SCHEMA}\",\"schema_version\":{CONTEXT_SCHEMA_VERSION},\"label\":{},\"lifecycle\":\"[diagnostic]\",\"non_claims\":[\"C2/C3-calibration\",\"gold\",\"R035\",\"R070\",\"lifecycle-promotion\"]}}", quote(label));
        let _ = writeln!(out, "{{\"record_kind\":\"aggregate\",\"files_attempted\":{},\"files_decoded\":{},\"malformed\":{},\"unreadable\":{},\"blocks\":{},\"containers\":{},\"alias_declarations\":{},\"series_edges\":{},\"memo_hits\":{},\"max_worklist_steps_per_document\":{},\"max_series_hops_observed\":{},\"max_fan_out_observed\":{},\"max_claims_per_field_observed\":{},\"max_adjacent_radius_used\":{},\"limit_events\":{},\"cycle_events\":{}}}", self.files_attempted, self.files_decoded, self.malformed, self.unreadable, self.blocks, self.containers, self.aliases, self.series_edges, self.memo_hits, self.max_steps, self.max_series_hops, self.max_fan_out, self.max_claims, self.max_adjacent, self.limit_events, self.cycle_events);
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"requests_by_kind\",{}}}",
            REQUEST_NAMES
                .iter()
                .enumerate()
                .map(|(i, n)| format!("\"{n}\":{}", self.requests[i]))
                .collect::<Vec<_>>()
                .join(",")
        );
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"context_status_counts\",{}}}",
            STATUS_NAMES
                .iter()
                .enumerate()
                .map(|(i, n)| format!("\"{n}\":{}", self.statuses[i]))
                .collect::<Vec<_>>()
                .join(",")
        );
        let _ = writeln!(out, "{{\"record_kind\":\"run_manifest\",\"schema_version\":{CONTEXT_SCHEMA_VERSION},\"run_status\":{},\"corpus_root\":{},\"observed_file_count\":{},\"bounds\":{{\"adjacent_block_radius\":{},\"max_series_hops\":{},\"max_alias_candidates\":{},\"max_context_claims_per_field\":{},\"max_worklist_steps_per_document\":{},\"max_linking_passes\":1}},\"source\":\"bounded C4 diagnostic smoke\"}}", quote(run_status), quote(&root.to_string_lossy()), self.files_attempted, PROPOSED_MAX_ADJACENT_RADIUS, PROPOSED_MAX_SERIES_HOPS, PROPOSED_MAX_ALIAS_CANDIDATES, PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD, PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT);
        out
    }
    fn observe(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.files_attempted += 1;
        match terminal {
            FileTerminal::Decoded => {
                self.files_decoded += 1;
                self.observe_block_document(blocks);
            }
            FileTerminal::Failed => {
                if fs::read(path).is_ok() {
                    self.malformed += 1
                } else {
                    self.unreadable += 1
                }
            }
        }
    }
}
impl SweepObserver for ContextBaselineAcc {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.observe(path, terminal, blocks);
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContextRun {
    pub exit_code: u8,
    pub jsonl: Option<String>,
    pub to_stdout: bool,
    pub stderr: String,
    pub progress_lines: Vec<String>,
    pub partial_flushes: u64,
}
pub fn run_context_baseline(cli: &ContextCli, default_root: &Path) -> ContextRun {
    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());
    if !root.is_dir() {
        if explicit {
            return ContextRun {
                exit_code: EXIT_ROOT_MISSING,
                jsonl: None,
                to_stdout: false,
                stderr: format!("root not found: {}", root.display()),
                progress_lines: vec![],
                partial_flushes: 0,
            };
        }
        return ContextRun {
            exit_code: EXIT_OK,
            jsonl: Some(ContextBaselineAcc::default().render_jsonl(&cli.label, &root, "complete")),
            to_stdout: true,
            stderr: format!("skip: default corpus root absent: {}", root.display()),
            progress_lines: vec![],
            partial_flushes: 0,
        };
    }
    let mut acc = ContextBaselineAcc::default();
    let mut progress = Vec::new();
    let (walk_error, flush_error, partial_flushes) = {
        let mut observer = ProgressObserver {
            inner: &mut acc,
            every: cli.progress_every.unwrap_or(0),
            seen: 0,
            progress: &mut progress,
            out: cli.out.as_deref().map(Path::new),
            label: &cli.label,
            root: &root,
            partial_flushes: 0,
            flush_error: None,
        };
        let walk_error = walk_and_observe(&root, cli.limit, &mut observer).err();
        (
            walk_error,
            observer.flush_error.take(),
            observer.partial_flushes,
        )
    };
    if let Some(err) = walk_error {
        return ContextRun {
            exit_code: EXIT_WALK_FAILED,
            jsonl: None,
            to_stdout: false,
            stderr: format!("walk failed: {err}"),
            progress_lines: progress,
            partial_flushes,
        };
    }
    if let Some(err) = flush_error {
        return ContextRun {
            exit_code: EXIT_OUT_UNWRITABLE,
            jsonl: None,
            to_stdout: false,
            stderr: err,
            progress_lines: progress,
            partial_flushes,
        };
    }
    let jsonl = acc.render_jsonl(&cli.label, &root, "complete");
    if let Some(out) = &cli.out {
        match write_atomic(Path::new(out), &jsonl) {
            Ok(()) => ContextRun {
                exit_code: EXIT_OK,
                jsonl: None,
                to_stdout: false,
                stderr: format!(
                    "files_attempted={} files_decoded={} blocks={}",
                    acc.files_attempted, acc.files_decoded, acc.blocks
                ),
                progress_lines: progress,
                partial_flushes,
            },
            Err(err) => ContextRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                jsonl: None,
                to_stdout: false,
                stderr: format!("cannot open --out {out}: {err}"),
                progress_lines: progress,
                partial_flushes,
            },
        }
    } else {
        ContextRun {
            exit_code: EXIT_OK,
            jsonl: Some(jsonl),
            to_stdout: true,
            stderr: format!(
                "files_attempted={} files_decoded={} blocks={}",
                acc.files_attempted, acc.files_decoded, acc.blocks
            ),
            progress_lines: progress,
            partial_flushes,
        }
    }
}
struct ProgressObserver<'a> {
    inner: &'a mut ContextBaselineAcc,
    every: u64,
    seen: u64,
    progress: &'a mut Vec<String>,
    out: Option<&'a Path>,
    label: &'a str,
    root: &'a Path,
    partial_flushes: u64,
    flush_error: Option<String>,
}
impl SweepObserver for ProgressObserver<'_> {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.inner.observe(path, terminal, blocks);
        self.seen += 1;
        if self.every > 0 && self.seen.is_multiple_of(self.every) {
            self.progress.push(format!("scanned={}", self.seen));
            if let Some(out) = self.out {
                match write_atomic(
                    out,
                    &self.inner.render_jsonl(self.label, self.root, "incomplete"),
                ) {
                    Ok(()) => self.partial_flushes += 1,
                    Err(err) if self.flush_error.is_none() => {
                        self.flush_error =
                            Some(format!("cannot open --out {}: {err}", out.display()))
                    }
                    Err(_) => {}
                }
            }
        }
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
fn quote(value: &str) -> String {
    format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
}
fn request_index(k: ContextRequestKind) -> usize {
    match k {
        ContextRequestKind::AncestorPath => 0,
        ContextRequestKind::AdjacentBlocks => 1,
        ContextRequestKind::OpenSeriesHead => 2,
        ContextRequestKind::ScopedAlias => 3,
        ContextRequestKind::CurrentDocumentRequisites => 4,
        ContextRequestKind::ExplicitAnchorLookup => 5,
    }
}
fn status_index(s: ContextStatus) -> usize {
    match s {
        ContextStatus::Resolved => 0,
        ContextStatus::Partial => 1,
        ContextStatus::Conflicting => 2,
        ContextStatus::Unavailable => 3,
        ContextStatus::Cycle => 4,
        ContextStatus::Limit => 5,
    }
}
pub fn validate_context_baseline_jsonl(output: &str) -> Result<(), String> {
    let allowed = [
        "header",
        "aggregate",
        "requests_by_kind",
        "context_status_counts",
        "run_manifest",
    ];
    for (i, line) in output.lines().enumerate() {
        let kind = line
            .split("\"record_kind\":\"")
            .nth(1)
            .and_then(|v| v.split('"').next())
            .ok_or_else(|| format!("line {} missing record_kind", i + 1))?;
        if !allowed.contains(&kind)
            || !line.trim_start().starts_with('{')
            || !line.trim_end().ends_with('}')
        {
            return Err(format!("line {} invalid record", i + 1));
        }
    }
    Ok(())
}
