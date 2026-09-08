//! Count-only diagnostic baseline for the two D384 local-grammar frame families.
//!
//! This profile deliberately reuses `npa_sweep::walk_and_observe`: the
//! deterministic XML walk and Consultant decoder are not copied here. It
//! retains only counts, maxima, status tallies, and limit events; decoded
//! text, frame payloads, and member values never enter the report (Q3).

use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

use crate::domain::ParsedBlock;
use crate::local_grammar::{extract_act_list_frames, extract_structural_frames, FrameStatus};
use crate::morphology::find_legal_markers;
use crate::npa_sweep::{walk_and_observe, FileTerminal, SweepObserver};

pub use crate::npa_sweep::{
    EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING, EXIT_USAGE, EXIT_WALK_FAILED,
};

pub const FRAMES_SCHEMA: &str = "npa-frames-baseline/v1";
pub const FRAMES_SCHEMA_VERSION: u32 = 1;

const STATUS_NAMES: [&str; 3] = ["proposed", "ambiguous", "rejected"];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FramesCli {
    pub root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
    pub label: String,
    pub progress_every: Option<u64>,
    pub progress_stderr: bool,
}

impl Default for FramesCli {
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

pub fn parse_frames_baseline_args<I>(args: I) -> Result<FramesCli, String>
where
    I: IntoIterator<Item = String>,
{
    let args: Vec<String> = args.into_iter().collect();
    let mut cli = FramesCli::default();
    let mut iter = args.iter().cloned();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--label" => cli.label = next_value(&mut iter, "--label")?,
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                cli.limit =
                    Some(raw.parse().map_err(|_| {
                        format!("--limit expects a non-negative integer, got '{raw}'")
                    })?);
            }
            "--progress" => {
                let raw = next_value(&mut iter, "--progress")?;
                let value: u64 = raw
                    .parse()
                    .map_err(|_| format!("--progress expects a positive integer, got '{raw}'"))?;
                if value == 0 {
                    return Err("--progress expects a positive integer".to_owned());
                }
                cli.progress_every = Some(value);
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

#[derive(Debug, Default)]
pub struct FramesBaselineAcc {
    blocks: u64,
    files_attempted: u64,
    files_decoded: u64,
    malformed: u64,
    unreadable: u64,
    frame_blocks: u64,
    frames: u64,
    frame_sum_per_block: u64,
    max_frames_per_block: u64,
    max_act_members: u64,
    max_structural_values: u64,
    status_counts: [u64; 3],
    limit_events: u64,
}

impl FramesBaselineAcc {
    pub fn frames_total(&self) -> u64 {
        self.frames
    }
    pub fn max_act_members(&self) -> u64 {
        self.max_act_members
    }
    pub fn max_structural_values(&self) -> u64 {
        self.max_structural_values
    }
    pub fn max_frames_per_block(&self) -> u64 {
        self.max_frames_per_block
    }
    pub fn status_count(&self, status: FrameStatus) -> u64 {
        self.status_counts[match status {
            FrameStatus::Proposed => 0,
            FrameStatus::Ambiguous => 1,
            FrameStatus::Rejected => 2,
        }]
    }

    fn observe_block(&mut self, block: &ParsedBlock) {
        let text = block.text();
        let tokens = crate::lexer::lex(text);
        let batch = crate::lawref::capture_lawrefs(text);
        let acts = extract_act_list_frames(text, &batch);
        let structural = extract_structural_frames(&tokens, text, &find_legal_markers(text));
        let count = acts.len() as u64 + structural.len() as u64;
        self.blocks += 1;
        self.frames += count;
        self.frame_sum_per_block += count;
        self.max_frames_per_block = self.max_frames_per_block.max(count);
        if count > 0 {
            self.frame_blocks += 1;
        }
        for frame in acts {
            self.max_act_members = self.max_act_members.max(frame.members.len() as u64);
            self.note_status(
                frame.status,
                frame
                    .diagnostic
                    .is_some_and(|d| d.as_str() == "frame_member_limit_reached"),
            );
        }
        for frame in structural {
            self.max_structural_values = self.max_structural_values.max(frame.values.len() as u64);
            self.note_status(
                frame.status,
                frame
                    .diagnostic
                    .is_some_and(|d| d.as_str() == "frame_member_limit_reached"),
            );
        }
    }

    fn note_status(&mut self, status: FrameStatus, limited: bool) {
        let index = match status {
            FrameStatus::Proposed => 0,
            FrameStatus::Ambiguous => 1,
            FrameStatus::Rejected => 2,
        };
        self.status_counts[index] += 1;
        if limited {
            self.limit_events += 1;
        }
    }

    pub fn render_jsonl(&self, label: &str, root: &Path, run_status: &str) -> String {
        let mean_scaled = self
            .frame_sum_per_block
            .saturating_mul(1_000_000)
            .checked_div(self.blocks)
            .unwrap_or(0);
        let mut out = String::new();
        let _ = writeln!(out, "{{\"record_kind\":\"header\",\"schema\":\"{FRAMES_SCHEMA}\",\"schema_version\":{FRAMES_SCHEMA_VERSION},\"label\":{},\"lifecycle\":\"[diagnostic]\",\"decoder\":\"ConsultantWordMlBlockDecoder\",\"lexer\":\"ln_decode::lexer::lex\",\"frames\":\"ln_decode::local_grammar::frame_extractors\",\"non_claims\":[\"C2/C3-calibration\",\"gold\",\"R035\",\"R070\",\"lifecycle-promotion\"]}}", quote(label));
        let _ = writeln!(out, "{{\"record_kind\":\"aggregate\",\"files_attempted\":{},\"files_decoded\":{},\"malformed\":{},\"unreadable\":{},\"blocks\":{},\"frame_blocks\":{},\"frames\":{},\"frames_per_block_max\":{},\"frames_per_block_mean_ppm\":{},\"act_members_max\":{},\"structural_values_max\":{},\"limit_events\":{}}}", self.files_attempted, self.files_decoded, self.malformed, self.unreadable, self.blocks, self.frame_blocks, self.frames, self.max_frames_per_block, mean_scaled, self.max_act_members, self.max_structural_values, self.limit_events);
        let statuses = STATUS_NAMES
            .iter()
            .enumerate()
            .map(|(i, name)| format!("\"{name}\":{}", self.status_counts[i]))
            .collect::<Vec<_>>()
            .join(",");
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"frame_status_counts\",{statuses}}}"
        );
        let _ = writeln!(out, "{{\"record_kind\":\"run_manifest\",\"schema_version\":{FRAMES_SCHEMA_VERSION},\"run_status\":{},\"corpus_root\":{},\"observed_file_count\":{},\"source\":\"bounded C4 diagnostic smoke\",\"bounds\":{{\"G06_max_members\":{},\"G07_max_expanded_candidates\":{}}},\"limitations\":[\"PARSE-P2D remains proposed\",\"endpoint expansion is resolve-side and not measured here\"]}}", quote(run_status), quote(&root.to_string_lossy()), self.files_attempted, crate::local_grammar::PROPOSED_MAX_FRAME_MEMBERS, crate::local_grammar::PROPOSED_MAX_EXPANDED_CANDIDATES);
        out
    }
}

impl SweepObserver for FramesBaselineAcc {
    fn observe_file(&mut self, _path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.files_attempted += 1;
        match terminal {
            FileTerminal::Decoded => {
                self.files_decoded += 1;
                for block in blocks {
                    self.observe_block(block);
                }
            }
            FileTerminal::Failed => {
                // The shared seam combines read/decode failures. A bounded
                // second read distinguishes malformed XML from unreadable
                // input without retaining payload bytes.
                if fs::read(_path).is_ok() {
                    self.malformed += 1;
                } else {
                    self.unreadable += 1;
                }
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FramesRun {
    pub exit_code: u8,
    pub jsonl: Option<String>,
    pub to_stdout: bool,
    pub stderr: String,
    pub progress_lines: Vec<String>,
    pub partial_flushes: u64,
}

pub fn run_frames_baseline(cli: &FramesCli, default_root: &Path) -> FramesRun {
    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());
    if !root.is_dir() {
        if explicit {
            return FramesRun {
                exit_code: EXIT_ROOT_MISSING,
                jsonl: None,
                to_stdout: false,
                stderr: format!("root not found: {}", root.display()),
                progress_lines: vec![],
                partial_flushes: 0,
            };
        }
        let acc = FramesBaselineAcc::default();
        return FramesRun {
            exit_code: EXIT_OK,
            jsonl: Some(acc.render_jsonl(&cli.label, &root, "complete")),
            to_stdout: true,
            stderr: format!("skip: default corpus root absent: {}", root.display()),
            progress_lines: vec![],
            partial_flushes: 0,
        };
    }
    let mut acc = FramesBaselineAcc::default();
    let mut progress = Vec::new();
    let mut progress_observer = ProgressObserver {
        inner: &mut acc,
        every: cli.progress_every.unwrap_or(0),
        seen: 0,
        progress: &mut progress,
        out_path: cli.out.as_deref().map(Path::new),
        label: &cli.label,
        root: &root,
        flush_error: None,
        partial_flushes: 0,
    };
    let result = walk_and_observe(&root, cli.limit, &mut progress_observer);
    let flush_error = progress_observer.flush_error.take();
    let partial_flushes = progress_observer.partial_flushes;
    if let Err(err) = result {
        return FramesRun {
            exit_code: EXIT_WALK_FAILED,
            jsonl: None,
            to_stdout: false,
            stderr: format!("walk failed: {err}"),
            progress_lines: progress,
            partial_flushes,
        };
    }
    if let Some(message) = flush_error {
        return FramesRun {
            exit_code: EXIT_OUT_UNWRITABLE,
            jsonl: None,
            to_stdout: false,
            stderr: message,
            progress_lines: progress,
            partial_flushes,
        };
    }
    let jsonl = acc.render_jsonl(&cli.label, &root, "complete");
    if let Some(out) = &cli.out {
        if let Err(err) = write_out_atomic(Path::new(out), &jsonl) {
            return FramesRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                jsonl: None,
                to_stdout: false,
                stderr: format!("cannot open --out {out}: {err}"),
                progress_lines: progress,
                partial_flushes,
            };
        }
        FramesRun {
            exit_code: EXIT_OK,
            jsonl: None,
            to_stdout: false,
            stderr: format!(
                "files_attempted={} files_decoded={} blocks={} frames={}",
                acc.files_attempted, acc.files_decoded, acc.blocks, acc.frames
            ),
            progress_lines: progress,
            partial_flushes,
        }
    } else {
        FramesRun {
            exit_code: EXIT_OK,
            jsonl: Some(jsonl),
            to_stdout: true,
            stderr: format!(
                "files_attempted={} files_decoded={} blocks={} frames={}",
                acc.files_attempted, acc.files_decoded, acc.blocks, acc.frames
            ),
            progress_lines: progress,
            partial_flushes,
        }
    }
}

struct ProgressObserver<'a> {
    inner: &'a mut FramesBaselineAcc,
    every: u64,
    seen: u64,
    progress: &'a mut Vec<String>,
    out_path: Option<&'a Path>,
    label: &'a str,
    root: &'a Path,
    flush_error: Option<String>,
    partial_flushes: u64,
}

impl SweepObserver for ProgressObserver<'_> {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.inner.observe_file(path, terminal, blocks);
        self.seen += 1;
        if self.every > 0 && self.seen.is_multiple_of(self.every) {
            self.progress.push(format!("scanned={}", self.seen));
            if let Some(out) = self.out_path {
                match write_out_atomic(
                    out,
                    &self.inner.render_jsonl(self.label, self.root, "incomplete"),
                ) {
                    Ok(()) => self.partial_flushes += 1,
                    Err(err) if self.flush_error.is_none() => {
                        self.flush_error =
                            Some(format!("cannot open --out {}: {err}", out.display()));
                    }
                    Err(_) => {}
                }
            }
        }
    }
}

fn write_out_atomic(out_path: &Path, payload: &str) -> std::io::Result<()> {
    let tmp = PathBuf::from(format!("{}.tmp", out_path.display()));
    let result = fs::write(&tmp, payload).and_then(|()| fs::rename(&tmp, out_path));
    if result.is_err() {
        let _ = fs::remove_file(tmp);
    }
    result
}

fn quote(value: &str) -> String {
    format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
}

pub fn validate_frames_baseline_jsonl(output: &str) -> Result<(), String> {
    let kinds = ["header", "aggregate", "frame_status_counts", "run_manifest"];
    for (line, raw) in output.lines().enumerate() {
        let kind = raw
            .split("\"record_kind\":\"")
            .nth(1)
            .and_then(|v| v.split('"').next())
            .ok_or_else(|| format!("line {} missing record_kind", line + 1))?;
        if !kinds.contains(&kind) {
            return Err(format!("line {} unknown record_kind", line + 1));
        }
        if !raw.trim_start().starts_with('{') || !raw.trim_end().ends_with('}') {
            return Err(format!("line {} is not an object", line + 1));
        }
    }
    Ok(())
}
