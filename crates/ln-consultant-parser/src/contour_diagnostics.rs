//! Count-only C4 contour diagnostics. No source text, tokens, or spans are retained.
use std::{
    collections::BTreeMap,
    fmt::Write as _,
    fs,
    io::Write as _,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    thread,
    time::Instant,
};

use crate::{
    acceptance_retry_contract::AcceptanceContract,
    corpus_sample::{classify_path, SourceRootKind},
};

use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, ParsedBlock},
    lawref, lexer, local_grammar, morphology,
    npa_sweep::{payload_ref_for_path, walk_xml_files, FileTerminal},
    ports::BlockDecoderPort,
};

pub const SCHEMA: &str = "npa-contour-diagnostics/v2";
pub const PARSER_REVISION: &str = "m204-s04-c4-contour-v1";
pub const EXIT_OK: u8 = 0;
pub const EXIT_DRIFT: u8 = 6;
pub const EXIT_INCOMPARABLE: u8 = 7;
pub const EXIT_MISSING: u8 = 8;
pub const EXIT_USAGE: u8 = 2;
pub const EXIT_OUT_UNWRITABLE: u8 = 3;
pub const EXIT_ROOT_MISSING: u8 = 4;
pub const EXIT_WALK_FAILED: u8 = 5;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Comparison {
    Match,
    OperationalOnly,
    SemanticDrift,
    IncomparableInput,
    MissingBaseline,
}

const STAGES: [&str; 7] = [
    "decode",
    "lexer_coverage",
    "grammar_frames",
    "block_presence",
    "lawref_capture_presence",
    "identity_binding_not_measured",
    "legal_marker_presence",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Cli {
    pub root: Option<String>,
    pub garant_root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
    pub profile: String,
    pub check: bool,
    pub label: String,
    /// Worker count for consultant XML observe. `0` = all cores. Tests keep `1`
    /// (sequential `walk_and_observe`). The CLI parser defaults to `0`.
    pub jobs: usize,
    /// Explicit caller pin for acceptance runs; never inferred from GSD or git.
    pub source_revision: Option<String>,
    pub acceptance_contract: Option<String>,
    pub acceptance_mode: Option<String>,
    /// Actual argv captured by the thin binary shell.
    pub argv: Vec<String>,
}
impl Default for Cli {
    fn default() -> Self {
        Self {
            root: None,
            garant_root: None,
            out: None,
            limit: None,
            profile: "contour".into(),
            check: false,
            label: "fixture-gate".into(),
            jobs: 1,
            source_revision: None,
            acceptance_contract: None,
            acceptance_mode: None,
            argv: Vec::new(),
        }
    }
}
fn resolve_jobs(jobs: usize) -> usize {
    if jobs == 0 {
        thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(1)
    } else {
        jobs
    }
}

pub fn parse_args<I: IntoIterator<Item = String>>(args: I) -> Result<Cli, String> {
    let argv: Vec<String> = args.into_iter().collect();
    let mut c = Cli {
        jobs: 0,
        argv: argv.clone(),
        ..Cli::default()
    };
    let mut it = argv.into_iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--root" => c.root = Some(next(&mut it, &a)?),
            "--garant-root" => c.garant_root = Some(next(&mut it, &a)?),
            "--out" => c.out = Some(next(&mut it, &a)?),
            "--label" => c.label = next(&mut it, &a)?,
            "--profile" => {
                c.profile = next(&mut it, &a)?;
                if c.profile != "decode" && c.profile != "contour" {
                    return Err("--profile expects decode or contour".into());
                }
            }
            "--limit" => {
                c.limit = Some(
                    next(&mut it, &a)?
                        .parse()
                        .map_err(|_| "--limit expects a non-negative integer".to_string())?,
                )
            }
            "--check" => c.check = true,
            "--source-revision" => c.source_revision = Some(next(&mut it, &a)?),
            "--acceptance-contract" => c.acceptance_contract = Some(next(&mut it, &a)?),
            "--acceptance-mode" => {
                let mode = next(&mut it, &a)?;
                if mode != "runtime" && mode != "artifact" {
                    return Err("--acceptance-mode expects runtime or artifact".into());
                }
                c.acceptance_mode = Some(mode);
            }
            "--jobs" => {
                c.jobs = next(&mut it, &a)?.parse().map_err(|_| {
                    "--jobs expects a non-negative integer (0 = all cores)".to_string()
                })?;
            }
            x => return Err(format!("unexpected argument '{x}'")),
        }
    }
    if c.acceptance_contract.is_some() && c.source_revision.is_none() {
        return Err("--acceptance-contract requires --source-revision caller pin".into());
    }
    if c.acceptance_mode.is_some() && c.acceptance_contract.is_none() {
        return Err("--acceptance-mode requires --acceptance-contract".into());
    }
    Ok(c)
}
fn next(it: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    it.next().ok_or_else(|| format!("missing value for {flag}"))
}

#[derive(Debug, Clone, Copy)]
pub struct RenderOpts<'a> {
    pub label: &'a str,
    pub limit: Option<u64>,
    pub profile: &'a str,
    pub source_revision: Option<&'a str>,
    pub acceptance_contract: Option<&'a str>,
    pub acceptance_check_id: Option<&'a str>,
    pub acceptance_mode: Option<&'a str>,
    pub acceptance_command_template: Option<&'a str>,
    pub argv: &'a [String],
    pub duration_ms: u128,
}

#[derive(Debug, Default)]
pub struct Acc {
    files: u64,
    decoded: u64,
    failed: u64,
    stages: BTreeMap<String, BTreeMap<String, u64>>,
    dimensions: BTreeMap<String, BTreeMap<String, u64>>,
    provider: String,
    source_root: Option<PathBuf>,
    inventory: Vec<String>,
}
impl Acc {
    fn hit(&mut self, stage: &str, outcome: &str) {
        *self
            .stages
            .entry(stage.into())
            .or_default()
            .entry(outcome.into())
            .or_default() += 1;
    }
    fn inv(&mut self, dim: &str, value: &str) {
        let safe = value
            .chars()
            .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
            .collect::<String>();
        if !safe.is_empty() {
            *self
                .dimensions
                .entry(dim.into())
                .or_default()
                .entry(safe)
                .or_default() += 1;
        }
    }
    fn observe(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.files += 1;
        let provider = self.provider.clone();
        self.inv("provider", &provider);
        if let Some(root) = &self.source_root {
            if let Ok(meta) = classify_path(
                path,
                root,
                if self.provider == "garant" {
                    SourceRootKind::Garant
                } else {
                    SourceRootKind::ConsultantExport
                },
            ) {
                self.inv(
                    "year",
                    &meta
                        .year
                        .map_or_else(|| "unknown".into(), |y| y.to_string()),
                );
                self.inv("act_type", &meta.document_type);
            }
        }
        match terminal {
            FileTerminal::Failed => {
                self.failed += 1;
                for s in STAGES {
                    self.hit(s, "failed");
                }
            }
            FileTerminal::Decoded => {
                self.decoded += 1;
                self.hit("decode", "ok");
                self.measure(blocks);
            }
        }
    }
    fn measure(&mut self, blocks: &[ParsedBlock]) {
        if blocks.is_empty() {
            for s in &STAGES[1..] {
                self.hit(s, "empty");
            }
            return;
        }
        let mut lexed = 0;
        let mut frames = 0;
        let mut contexts = 0;
        let mut semantic = 0;
        let mut identity = 0;
        let mut temporal = 0;
        for b in blocks {
            let t = b.text();
            let tokens = lexer::lex(t);
            lexed += tokens.len();
            let caps = lawref::capture_lawrefs(t);
            let fs = local_grammar::extract_structural_frames(
                &tokens,
                t,
                &morphology::find_legal_markers(t),
            );
            frames += fs.len();
            contexts += 1;
            semantic += caps.captures().len();
            // C4 deliberately does not execute or infer product identity binding.
            identity = 0;
            temporal += morphology::find_legal_markers(t).len();
        }
        for (s, n) in [
            ("lexer_coverage", lexed),
            ("grammar_frames", frames),
            ("block_presence", contexts),
            ("lawref_capture_presence", semantic),
            ("identity_binding_not_measured", identity),
            ("legal_marker_presence", temporal),
        ] {
            self.hit(s, if n > 0 { "observed" } else { "none" });
        }
    }
    pub fn merge(&mut self, other: Acc) {
        self.files += other.files;
        self.decoded += other.decoded;
        self.failed += other.failed;
        self.inventory.extend(other.inventory);
        for (stage, outcomes) in other.stages {
            for (outcome, count) in outcomes {
                *self
                    .stages
                    .entry(stage.clone())
                    .or_default()
                    .entry(outcome)
                    .or_default() += count;
            }
        }
        for (dimension, values) in other.dimensions {
            for (value, count) in values {
                *self
                    .dimensions
                    .entry(dimension.clone())
                    .or_default()
                    .entry(value)
                    .or_default() += count;
            }
        }
    }

    pub fn render(&self, _root: &Path, opts: &RenderOpts<'_>) -> String {
        let RenderOpts {
            label,
            limit,
            profile,
            source_revision,
            acceptance_contract,
            acceptance_check_id,
            acceptance_mode,
            acceptance_command_template,
            argv,
            duration_ms,
        } = *opts;
        let mut o = String::new();
        let mut tuples = self.inventory.clone();
        tuples.sort();
        let inventory_digest = digest_bytes(tuples.join("\n").as_bytes())
            .unwrap_or_else(|_| "sha256:unavailable".into());
        let semantic = format!(
            "files={};decoded={};failed={};stages={};inventory={}",
            self.files,
            self.decoded,
            self.failed,
            map(&self.stages),
            map(&self.dimensions)
        );
        let semantic_digest =
            digest_bytes(semantic.as_bytes()).unwrap_or_else(|_| "sha256:unavailable".into());
        let _=writeln!(o,"{{\"record_kind\":\"header\",\"schema\":\"{SCHEMA}\",\"schema_version\":2,\"label\":{},\"lifecycle\":\"diagnostic\",\"parser_revision\":\"{PARSER_REVISION}\",\"inventory_digest\":{},\"profile\":{},\"limit\":{},\"non_claims\":[\"C4 does not advance C2/C3/C5\",\"not gold\",\"not R035/R070\",\"product document_context/semantic_scope/identity_binding are not executed\",\"ln-temporal runtime is not used\"],\"provider_roots\":[\"consultant\",\"garant\"]}}",q(label),q(&inventory_digest),q(profile),limit.map_or_else(|| "null".into(), |n| n.to_string()));
        let _=writeln!(o,"{{\"record_kind\":\"aggregate\",\"provider\":{},\"files\":{},\"decoded\":{},\"failed\":{},\"stages\":{}}}",q("all-contours"),self.files,self.decoded,self.failed,map(&self.stages));
        let _ = writeln!(
            o,
            "{{\"record_kind\":\"inventory\",\"provider\":{},\"dimensions\":{}}}",
            q("all-contours"),
            map(&self.dimensions)
        );
        let _=writeln!(o,"{{\"record_kind\":\"canonical_payload\",\"schema\":\"{SCHEMA}\",\"parser_revision\":\"{PARSER_REVISION}\",\"inventory_digest\":{},\"semantic_digest\":{},\"profile\":{},\"limit\":{},\"source_revision\":{},\"acceptance_contract_version\":{},\"acceptance_check_id\":{},\"acceptance_mode\":{},\"acceptance_command_template\":{},\"files\":{},\"decoded\":{},\"failed\":{},\"stages\":{},\"inventory\":{}}}",q(&inventory_digest),q(&semantic_digest),q(profile),limit.map_or_else(|| "null".into(), |n| n.to_string()),q(source_revision.unwrap_or("unavailable")),q(acceptance_contract.unwrap_or("unavailable")),q(acceptance_check_id.unwrap_or("unavailable")),q(acceptance_mode.unwrap_or("unavailable")),q(acceptance_command_template.unwrap_or("unavailable")),self.files,self.decoded,self.failed,map(&self.stages),map(&self.dimensions));
        let toolchain = observed_toolchain();
        let argv_json = format!(
            "[{}]",
            argv.iter().map(|a| q(a)).collect::<Vec<_>>().join(",")
        );
        let source = source_revision.unwrap_or("unavailable");
        let contract = acceptance_contract.unwrap_or("unavailable");
        let _=writeln!(o,"{{\"record_kind\":\"operational_envelope\",\"label\":{},\"observed_file_count\":{},\"run_status\":\"complete\",\"acceptance_contract_version\":{},\"source_revision\":{},\"argv\":{},\"observed_rustc_version\":{},\"duration_ms\":{}}}",q(label),self.files,q(contract),q(source),argv_json,q(&toolchain),duration_ms);
        o
    }
}
fn map(m: &BTreeMap<String, BTreeMap<String, u64>>) -> String {
    let entries = m
        .iter()
        .map(|(k, v)| {
            let inner = v
                .iter()
                .map(|(a, n)| format!("{}:{}", q(a), n))
                .collect::<Vec<_>>()
                .join(",");
            format!("{}:{{{inner}}}", q(k))
        })
        .collect::<Vec<_>>()
        .join(",");
    format!("{{{entries}}}")
}
fn q(s: &str) -> String {
    format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\""))
}
fn write(path: &Path, body: &str) -> Result<(), String> {
    let nonce = std::process::id();
    let tmp = PathBuf::from(format!("{}.tmp-{nonce}", path.display()));
    fs::write(&tmp, body)
        .and_then(|_| fs::rename(&tmp, path))
        .map_err(|e| e.to_string())
}
fn acceptance_identity(
    cli: &Cli,
) -> (
    Option<String>,
    Option<String>,
    Option<String>,
    Option<String>,
) {
    let Some(path) = cli.acceptance_contract.as_deref() else {
        return (None, None, None, None);
    };
    let Ok(contract) = AcceptanceContract::parse_file(path) else {
        return (None, None, None, None);
    };
    let mode = cli.acceptance_mode.as_deref().unwrap_or("runtime");
    let check = contract.checks.iter().find(|check| {
        matches!(
            (&check.mode, mode),
            (
                crate::acceptance_retry_contract::CheckMode::Runtime,
                "runtime"
            ) | (
                crate::acceptance_retry_contract::CheckMode::Artifact,
                "artifact"
            )
        )
    });
    check.map_or(
        (
            Some(contract.contract_version.clone()),
            None,
            Some(mode.to_string()),
            None,
        ),
        |check| {
            (
                Some(contract.contract_version.clone()),
                Some(check.check_id.clone()),
                Some(mode.to_string()),
                Some(check.command_template.clone()),
            )
        },
    )
}

fn observed_toolchain() -> String {
    Command::new("rustc")
        .arg("--version")
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "unavailable".into())
}

fn digest_bytes(bytes: &[u8]) -> Result<String, String> {
    let mut child = Command::new("sha256sum")
        .arg("-")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("sha256sum unavailable: {e}"))?;
    child
        .stdin
        .take()
        .ok_or("sha256sum stdin unavailable")?
        .write_all(bytes)
        .map_err(|e| format!("sha256sum write failed: {e}"))?;
    let output = child
        .wait_with_output()
        .map_err(|e| format!("sha256sum failed: {e}"))?;
    if !output.status.success() {
        return Err("sha256sum returned failure".into());
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let hex = stdout.split_whitespace().next().unwrap_or("");
    if hex.len() != 64 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("invalid sha256sum output".into());
    }
    Ok(format!("sha256:{hex}"))
}

pub fn validate_jsonl(s: &str) -> Result<(), String> {
    for (i, l) in s.lines().enumerate() {
        if !l.starts_with('{') || !l.ends_with('}') || !l.contains("\"record_kind\"") {
            return Err(format!("line {} invalid", i + 1));
        }
    }
    Ok(())
}

pub fn run(cli: &Cli, default_root: &Path) -> (u8, Option<String>, String) {
    if let Some(path) = &cli.acceptance_contract {
        if let Err(error) = AcceptanceContract::parse_file(path) {
            return (
                EXIT_USAGE,
                None,
                format!("acceptance contract invalid: {error}"),
            );
        }
        if cli.source_revision.as_deref().is_none_or(str::is_empty) {
            return (
                EXIT_USAGE,
                None,
                "acceptance path requires source revision caller pin".into(),
            );
        }
    }
    let started = Instant::now();
    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.into());
    if !root.is_dir() {
        return if explicit {
            (
                EXIT_ROOT_MISSING,
                None,
                format!("root not found: {}", root.display()),
            )
        } else {
            (
                EXIT_OK,
                Some({
                    let (version, check_id, mode, command) = acceptance_identity(cli);
                    Acc::default().render(
                        &root,
                        &RenderOpts {
                            label: &cli.label,
                            limit: cli.limit,
                            profile: &cli.profile,
                            source_revision: cli.source_revision.as_deref(),
                            acceptance_contract: version.as_deref(),
                            acceptance_check_id: check_id.as_deref(),
                            acceptance_mode: mode.as_deref(),
                            acceptance_command_template: command.as_deref(),
                            argv: &cli.argv,
                            duration_ms: started.elapsed().as_millis(),
                        },
                    )
                }),
                "default root absent; skipped".into(),
            )
        };
    }
    let mut a = Acc {
        provider: "consultant".into(),
        source_root: Some(root.clone()),
        ..Default::default()
    };
    let n = match observe_consultant_files(&root, cli.limit, resolve_jobs(cli.jobs), &mut a) {
        Ok(n) => n,
        Err(e) => return (EXIT_WALK_FAILED, None, e),
    };
    if let Some(g) = cli.garant_root.as_ref() {
        let garant = PathBuf::from(g);
        if !garant.is_dir() {
            return (
                EXIT_ROOT_MISSING,
                None,
                format!("garant root not found: {}", garant.display()),
            );
        }
        let mut ga = Acc {
            provider: "garant".into(),
            source_root: Some(garant.clone()),
            ..Default::default()
        };
        for path in odts(&garant)
            .into_iter()
            .take(cli.limit.unwrap_or(u64::MAX) as usize)
        {
            observe_garant_file(&mut ga, &path);
        }
        a.merge(ga);
    }
    let (version, check_id, mode, command) = acceptance_identity(cli);
    let body = a.render(
        &root,
        &RenderOpts {
            label: &cli.label,
            limit: cli.limit,
            profile: &cli.profile,
            source_revision: cli.source_revision.as_deref(),
            acceptance_contract: version.as_deref(),
            acceptance_check_id: check_id.as_deref(),
            acceptance_mode: mode.as_deref(),
            acceptance_command_template: command.as_deref(),
            argv: &cli.argv,
            duration_ms: started.elapsed().as_millis(),
        },
    );
    if cli.check {
        let Some(path) = cli.out.as_ref() else {
            return (EXIT_USAGE, None, "--check requires --out baseline".into());
        };
        let Some(old) = fs::read_to_string(path).ok() else {
            return (EXIT_MISSING, None, "baseline receipt missing".into());
        };
        match compare_reports(&body, Some(&old)) {
            Comparison::Match | Comparison::OperationalOnly => {
                (EXIT_OK, None, format!("observed={n}; check=ok"))
            }
            Comparison::SemanticDrift => (EXIT_DRIFT, None, "--check semantic drift".into()),
            Comparison::IncomparableInput => (
                EXIT_INCOMPARABLE,
                None,
                "--check incomparable baseline".into(),
            ),
            Comparison::MissingBaseline => (EXIT_MISSING, None, "baseline receipt missing".into()),
        }
    } else if let Some(out) = &cli.out {
        let path = Path::new(out);
        if let Ok(old) = fs::read_to_string(path) {
            match compare_reports(&body, Some(&old)) {
                Comparison::Match | Comparison::OperationalOnly => {
                    return (EXIT_OK, None, format!("observed={n}; receipt=reused"));
                }
                Comparison::SemanticDrift
                | Comparison::IncomparableInput
                | Comparison::MissingBaseline => {}
            }
        }
        match write(path, &body) {
            Ok(()) => (EXIT_OK, None, format!("observed={n}")),
            Err(e) => (EXIT_OUT_UNWRITABLE, None, e),
        }
    } else {
        (EXIT_OK, Some(body), format!("observed={n}"))
    }
}
/// Compare only the canonical payload. Operational metadata (label, receipt
/// destination, timestamps and durations) is intentionally excluded.
pub fn compare_reports(current: &str, baseline: Option<&str>) -> Comparison {
    let Some(baseline) = baseline else {
        return Comparison::MissingBaseline;
    };
    let current_payload = canonical_payload(current);
    let baseline_payload = canonical_payload(baseline);
    let (Some(current_payload), Some(baseline_payload)) = (current_payload, baseline_payload)
    else {
        return Comparison::IncomparableInput;
    };
    if current_payload.schema != baseline_payload.schema
        || current_payload.revision != baseline_payload.revision
        || current_payload.profile != baseline_payload.profile
        || current_payload.limit != baseline_payload.limit
        || current_payload.inventory_digest != baseline_payload.inventory_digest
        || current_payload.source_revision != baseline_payload.source_revision
        || current_payload.acceptance_contract_version
            != baseline_payload.acceptance_contract_version
        || current_payload.acceptance_check_id != baseline_payload.acceptance_check_id
        || current_payload.acceptance_mode != baseline_payload.acceptance_mode
        || current_payload.acceptance_command_template
            != baseline_payload.acceptance_command_template
    {
        return Comparison::IncomparableInput;
    }
    if current_payload.semantic != baseline_payload.semantic {
        return Comparison::SemanticDrift;
    }
    if current_payload.operational != baseline_payload.operational {
        Comparison::OperationalOnly
    } else {
        Comparison::Match
    }
}

#[derive(Debug, PartialEq, Eq)]
struct CanonicalPayload {
    schema: String,
    revision: String,
    profile: String,
    limit: String,
    inventory_digest: String,
    source_revision: String,
    acceptance_contract_version: String,
    acceptance_check_id: String,
    acceptance_mode: String,
    acceptance_command_template: String,
    semantic_digest: String,
    semantic: String,
    operational: String,
}

fn json_field(line: &str, key: &str) -> Option<String> {
    let marker = format!("\"{key}\":");
    let start = line.find(&marker)? + marker.len();
    let rest = &line[start..];
    let bytes = rest.as_bytes();
    if bytes.first() == Some(&b'\"') {
        let mut escaped = false;
        for (i, byte) in bytes.iter().enumerate().skip(1) {
            if escaped {
                escaped = false;
            } else if *byte == b'\\' {
                escaped = true;
            } else if *byte == b'\"' {
                return Some(rest[1..i].to_owned());
            }
        }
        return None;
    }
    if matches!(bytes.first(), Some(b'{') | Some(b'[')) {
        let open = bytes[0];
        let close = if open == b'{' { b'}' } else { b']' };
        let mut depth = 0usize;
        let mut in_string = false;
        let mut escaped = false;
        for (i, byte) in bytes.iter().enumerate() {
            if in_string {
                if escaped {
                    escaped = false;
                } else if *byte == b'\\' {
                    escaped = true;
                } else if *byte == b'\"' {
                    in_string = false;
                }
            } else if *byte == b'\"' {
                in_string = true;
            } else if *byte == open {
                depth += 1;
            } else if *byte == close {
                depth = depth.checked_sub(1)?;
                if depth == 0 {
                    return Some(rest[..=i].to_owned());
                }
            }
        }
        return None;
    }
    let end = rest
        .find(',')
        .or_else(|| rest.find('}'))
        .unwrap_or(rest.len());
    Some(rest[..end].trim().to_owned())
}

fn canonical_payload(report: &str) -> Option<CanonicalPayload> {
    let lines: Vec<&str> = report.lines().collect();
    if lines.len() < 5 || validate_jsonl(report).is_err() {
        return None;
    }
    let header = lines
        .iter()
        .find(|line| line.contains("\"record_kind\":\"header\""))?;
    let payload = lines
        .iter()
        .find(|line| line.contains("\"record_kind\":\"canonical_payload\""))?;
    let operational = lines
        .iter()
        .find(|line| line.contains("\"record_kind\":\"operational_envelope\""))?;
    let semantic = ["files", "decoded", "failed", "stages", "inventory"]
        .iter()
        .map(|key| json_field(payload, key))
        .collect::<Option<Vec<_>>>()?
        .join("|");
    let _stored_semantic_digest = json_field(payload, "semantic_digest")?;
    // The stored digest is an observability field, not a trust boundary. The
    // comparator recomputes the binding from typed semantic fields, so a stale
    // or forged semantic_digest cannot masquerade as a valid baseline.
    let semantic_digest = digest_bytes(
        format!(
            "files={};decoded={};failed={};stages={};inventory={}",
            json_field(payload, "files")?,
            json_field(payload, "decoded")?,
            json_field(payload, "failed")?,
            json_field(payload, "stages")?,
            json_field(payload, "inventory")?,
        )
        .as_bytes(),
    )
    .ok()?;
    Some(CanonicalPayload {
        schema: json_field(header, "schema")?,
        revision: json_field(header, "parser_revision")?,
        profile: json_field(payload, "profile")?,
        limit: json_field(payload, "limit")?,
        inventory_digest: json_field(payload, "inventory_digest")?,
        source_revision: json_field(payload, "source_revision")
            .unwrap_or_else(|| "unavailable".into()),
        acceptance_contract_version: json_field(payload, "acceptance_contract_version")
            .unwrap_or_else(|| "unavailable".into()),
        acceptance_check_id: json_field(payload, "acceptance_check_id")
            .unwrap_or_else(|| "unavailable".into()),
        acceptance_mode: json_field(payload, "acceptance_mode")
            .unwrap_or_else(|| "unavailable".into()),
        acceptance_command_template: json_field(payload, "acceptance_command_template")
            .unwrap_or_else(|| "unavailable".into()),
        semantic_digest,
        semantic,
        operational: ["label", "observed_file_count", "run_status"]
            .iter()
            .map(|key| json_field(operational, key))
            .collect::<Option<Vec<_>>>()?
            .join("|"),
    })
}

fn observe_garant_file(acc: &mut Acc, path: &Path) {
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(_) => {
            acc.observe(path, FileTerminal::Failed, &[]);
            return;
        }
    };
    let digest = match digest_bytes(&bytes) {
        Ok(d) => d,
        Err(_) => {
            acc.observe(path, FileTerminal::Failed, &[]);
            return;
        }
    };
    let relative = acc
        .source_root
        .as_ref()
        .and_then(|root| path.strip_prefix(root).ok())
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .unwrap_or_default();
    acc.inventory
        .push(format!("{}|{}|{}", acc.provider, relative, digest));
    let decoded = fs::read(path)
        .ok()
        .and_then(|current| {
            (digest_bytes(&current).ok().as_deref() == Some(digest.as_str())).then_some(current)
        })
        .and_then(|current| {
            let request = DecodeRequest::new(
                payload_ref_for_path(path),
                FamilyFormat::parse("family:garant-odt").ok()?,
                &current,
            );
            GarantOdtBlockDecoder.decode_blocks(&request).ok()
        });
    match decoded {
        Some(blocks) => acc.observe(path, FileTerminal::Decoded, &blocks),
        None => acc.observe(path, FileTerminal::Failed, &[]),
    }
}

fn observe_consultant_file(acc: &mut Acc, path: &Path) {
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(_) => {
            acc.observe(path, FileTerminal::Failed, &[]);
            return;
        }
    };
    let digest = match digest_bytes(&bytes) {
        Ok(digest) => digest,
        Err(_) => {
            acc.observe(path, FileTerminal::Failed, &[]);
            return;
        }
    };
    let relative = acc
        .source_root
        .as_ref()
        .and_then(|root| path.strip_prefix(root).ok())
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .unwrap_or_else(|| {
            path.file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned()
        });
    acc.inventory
        .push(format!("{}|{}|{}", acc.provider, relative, digest));
    let request = DecodeRequest::new(
        payload_ref_for_path(path),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        &bytes,
    );
    match ConsultantWordMlBlockDecoder.decode_blocks(&request) {
        Ok(blocks) => {
            if fs::read(path)
                .ok()
                .and_then(|now| digest_bytes(&now).ok())
                .as_deref()
                != Some(digest.as_str())
            {
                acc.observe(path, FileTerminal::Failed, &[]);
            } else {
                acc.observe(path, FileTerminal::Decoded, &blocks);
            }
        }
        Err(_) => acc.observe(path, FileTerminal::Failed, &[]),
    }
}

fn observe_consultant_files(
    root: &Path,
    limit: Option<u64>,
    jobs: usize,
    acc: &mut Acc,
) -> Result<usize, String> {
    let files = walk_xml_files(root, limit).map_err(|e| e.to_string())?;
    if jobs <= 1 {
        for path in &files {
            observe_consultant_file(acc, path);
        }
        return Ok(files.len());
    }
    let n = files.len();
    if n == 0 {
        return Ok(0);
    }
    let jobs = jobs.min(n);
    let chunk = n.div_ceil(jobs);
    let provider = acc.provider.clone();
    let source_root = root.to_path_buf();
    let mut handles = Vec::with_capacity(jobs);
    for shard in files.chunks(chunk) {
        let shard: Vec<PathBuf> = shard.to_vec();
        let provider = provider.clone();
        let worker_root = source_root.clone();
        handles.push(thread::spawn(move || {
            let mut local = Acc {
                provider,
                source_root: Some(worker_root),
                ..Default::default()
            };
            for path in &shard {
                observe_consultant_file(&mut local, path);
            }
            local
        }));
    }
    for handle in handles {
        acc.merge(
            handle
                .join()
                .map_err(|_| "consultant observe worker panicked".to_string())?,
        );
    }
    Ok(n)
}

fn odts(root: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    fn rec(p: &Path, o: &mut Vec<PathBuf>) {
        if let Ok(rd) = fs::read_dir(p) {
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    rec(&p, o)
                } else if p.extension().is_some_and(|x| x == "odt") {
                    o.push(p)
                }
            }
        }
    }
    rec(root, &mut out);
    out.sort();
    out
}
