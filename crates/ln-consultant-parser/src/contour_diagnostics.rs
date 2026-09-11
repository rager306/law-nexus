//! Count-only C4 contour diagnostics. No source text, tokens, or spans are retained.
use std::{
    collections::BTreeMap,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
    thread,
};

use crate::corpus_sample::{classify_path, SourceRootKind};

use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, ParsedBlock},
    lawref, lexer, local_grammar, morphology,
    npa_sweep::{
        payload_ref_for_path, walk_and_observe, walk_xml_files, FileTerminal, SweepObserver,
    },
    ports::BlockDecoderPort,
};

pub const SCHEMA: &str = "npa-contour-diagnostics/v1";
pub const EXIT_OK: u8 = 0;
pub const EXIT_USAGE: u8 = 2;
pub const EXIT_OUT_UNWRITABLE: u8 = 3;
pub const EXIT_ROOT_MISSING: u8 = 4;
pub const EXIT_WALK_FAILED: u8 = 5;
const STAGES: [&str; 7] = [
    "decode",
    "lexer_coverage",
    "grammar_frames",
    "document_context",
    "semantic_scope",
    "identity_claims",
    "temporal",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Cli {
    pub root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
    pub profile: String,
    pub check: bool,
    pub label: String,
    /// Worker count for consultant XML observe. `0` = all cores. Tests keep `1`
    /// (sequential `walk_and_observe`). The CLI parser defaults to `0`.
    pub jobs: usize,
}
impl Default for Cli {
    fn default() -> Self {
        Self {
            root: None,
            out: None,
            limit: None,
            profile: "contour".into(),
            check: false,
            label: "fixture-gate".into(),
            jobs: 1,
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
    let mut c = Cli {
        jobs: 0,
        ..Cli::default()
    };
    let mut it = args.into_iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--root" => c.root = Some(next(&mut it, &a)?),
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
            "--jobs" => {
                c.jobs = next(&mut it, &a)?.parse().map_err(|_| {
                    "--jobs expects a non-negative integer (0 = all cores)".to_string()
                })?;
            }
            x => return Err(format!("unexpected argument '{x}'")),
        }
    }
    Ok(c)
}
fn next(it: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    it.next().ok_or_else(|| format!("missing value for {flag}"))
}

#[derive(Debug, Default)]
pub struct Acc {
    files: u64,
    decoded: u64,
    failed: u64,
    stages: BTreeMap<String, BTreeMap<String, u64>>,
    inventory: BTreeMap<String, BTreeMap<String, u64>>,
    provider: String,
    source_root: Option<PathBuf>,
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
                .inventory
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
            identity += caps.captures().iter().filter(|_| true).count();
            temporal += morphology::find_legal_markers(t).len();
        }
        for (s, n) in [
            ("lexer_coverage", lexed),
            ("grammar_frames", frames),
            ("document_context", contexts),
            ("semantic_scope", semantic),
            ("identity_claims", identity),
            ("temporal", temporal),
        ] {
            self.hit(s, if n > 0 { "observed" } else { "none" });
        }
    }
    pub fn merge(&mut self, other: Acc) {
        self.files += other.files;
        self.decoded += other.decoded;
        self.failed += other.failed;
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
        for (dimension, values) in other.inventory {
            for (value, count) in values {
                *self
                    .inventory
                    .entry(dimension.clone())
                    .or_default()
                    .entry(value)
                    .or_default() += count;
            }
        }
    }

    pub fn render(&self, label: &str, root: &Path, limit: Option<u64>, profile: &str) -> String {
        let mut o = String::new();
        let _=writeln!(o,"{{\"record_kind\":\"header\",\"schema\":\"{SCHEMA}\",\"schema_version\":1,\"label\":{},\"lifecycle\":\"diagnostic\",\"parser_revision\":\"ln-consultant-parser\",\"corpus_snapshot_hash\":\"sha256:diagnostic-path-fingerprint\",\"non_claims\":[\"C4 does not advance C2/C3/C5\",\"not gold\",\"not R035/R070\"],\"provider_roots\":[\"consultant\",\"garant\"]}}",q(label));
        let _=writeln!(o,"{{\"record_kind\":\"aggregate\",\"provider\":{},\"files\":{},\"decoded\":{},\"failed\":{},\"stages\":{}}}",q("all-contours"),self.files,self.decoded,self.failed,map(&self.stages));
        let _ = writeln!(
            o,
            "{{\"record_kind\":\"inventory\",\"provider\":{},\"dimensions\":{}}}",
            q("all-contours"),
            map(&self.inventory)
        );
        let _=writeln!(o,"{{\"record_kind\":\"run_manifest\",\"bounds\":{{\"raw_text\":false,\"source_spans\":false,\"limit\":{},\"profile\":{}}},\"root\":{},\"observed_file_count\":{},\"run_status\":\"complete\"}}",limit.map_or_else(|| "null".into(), |n| n.to_string()),q(profile),q(&root.to_string_lossy()),self.files);
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
struct Observer<'a> {
    acc: &'a mut Acc,
}
impl SweepObserver for Observer<'_> {
    fn observe_file(&mut self, p: &Path, t: FileTerminal, b: &[ParsedBlock]) {
        self.acc.observe(p, t, b)
    }
}
fn write(path: &Path, body: &str) -> Result<(), String> {
    let nonce = std::process::id();
    let tmp = PathBuf::from(format!("{}.tmp-{nonce}", path.display()));
    fs::write(&tmp, body)
        .and_then(|_| fs::rename(&tmp, path))
        .map_err(|e| e.to_string())
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
                Some(Acc::default().render(&cli.label, &root, cli.limit, &cli.profile)),
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
    if cli.profile == "contour" {
        let g = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .join("law-source/garant");
        if g.is_dir() {
            let mut ga = Acc {
                provider: "garant".into(),
                source_root: Some(g.clone()),
                ..Default::default()
            };
            for p in odts(&g)
                .into_iter()
                .take(cli.limit.unwrap_or(u64::MAX) as usize)
            {
                ga.inv("provider", "garant");
                if let Ok(meta) = classify_path(&p, &g, SourceRootKind::Garant) {
                    ga.inv(
                        "year",
                        &meta
                            .year
                            .map_or_else(|| "unknown".into(), |y| y.to_string()),
                    );
                    ga.inv("act_type", &meta.document_type);
                }
                ga.files += 1;
                match fs::read(&p).ok().and_then(|bytes| {
                    let r = DecodeRequest::new(
                        payload_ref_for_path(&p),
                        FamilyFormat::parse("family:garant-odt").ok()?,
                        &bytes,
                    );
                    GarantOdtBlockDecoder.decode_blocks(&r).ok()
                }) {
                    Some(b) => {
                        ga.decoded += 1;
                        ga.measure(&b);
                        ga.hit("decode", "ok");
                    }
                    None => {
                        ga.failed += 1;
                        for s in STAGES {
                            ga.hit(s, "failed");
                        }
                    }
                }
            }
            a.merge(ga);
        }
    }
    let body = a.render(&cli.label, &root, cli.limit, &cli.profile);
    if cli.check {
        match cli.out.as_ref().and_then(|p| fs::read_to_string(p).ok()) {
            Some(old) if old == body => (EXIT_OK, None, format!("observed={n}; check=ok")),
            _ => (EXIT_WALK_FAILED, None, "--check mismatch".into()),
        }
    } else if let Some(out) = &cli.out {
        match write(Path::new(out), &body) {
            Ok(()) => (EXIT_OK, None, format!("observed={n}")),
            Err(e) => (EXIT_OUT_UNWRITABLE, None, e),
        }
    } else {
        (EXIT_OK, Some(body), format!("observed={n}"))
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
    let request = DecodeRequest::new(
        payload_ref_for_path(path),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        &bytes,
    );
    match ConsultantWordMlBlockDecoder.decode_blocks(&request) {
        Ok(blocks) => acc.observe(path, FileTerminal::Decoded, &blocks),
        Err(_) => acc.observe(path, FileTerminal::Failed, &[]),
    }
}

fn observe_consultant_files(
    root: &Path,
    limit: Option<u64>,
    jobs: usize,
    acc: &mut Acc,
) -> Result<usize, String> {
    if jobs <= 1 {
        let mut ob = Observer { acc };
        return walk_and_observe(root, limit, &mut ob).map_err(|e| e.to_string());
    }
    let files = walk_xml_files(root, limit).map_err(|e| e.to_string())?;
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
