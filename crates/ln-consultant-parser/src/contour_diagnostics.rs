//! Count-only C4 contour diagnostics. No source text, tokens, or spans are retained.
use std::{
    collections::BTreeMap,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
};

use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, ParsedBlock},
    lawref, lexer, local_grammar, morphology,
    npa_sweep::{payload_ref_for_path, walk_and_observe, FileTerminal, SweepObserver},
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
        }
    }
}
pub fn parse_args<I: IntoIterator<Item = String>>(args: I) -> Result<Cli, String> {
    let mut c = Cli::default();
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
        self.inv("year", &year(path));
        self.inv("act_type", &act_type(path));
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
    pub fn render(&self, label: &str, root: &Path) -> String {
        let mut o = String::new();
        let _=writeln!(o,"{{\"record_kind\":\"header\",\"schema\":\"{SCHEMA}\",\"schema_version\":1,\"label\":{},\"lifecycle\":\"diagnostic\",\"parser_revision\":\"ln-consultant-parser\",\"corpus_snapshot_hash\":\"sha256:diagnostic-path-fingerprint\",\"non_claims\":[\"C4 does not advance C2/C3/C5\",\"not gold\",\"not R035/R070\"],\"provider_roots\":[\"consultant\",\"garant\"]}}",q(label));
        let _=writeln!(o,"{{\"record_kind\":\"aggregate\",\"provider\":{},\"files\":{},\"decoded\":{},\"failed\":{},\"stages\":{}}}",q(&self.provider),self.files,self.decoded,self.failed,map(&self.stages));
        let _ = writeln!(
            o,
            "{{\"record_kind\":\"inventory\",\"provider\":{},\"dimensions\":{}}}",
            q(&self.provider),
            map(&self.inventory)
        );
        let _=writeln!(o,"{{\"record_kind\":\"run_manifest\",\"bounds\":{{\"raw_text\":false,\"source_spans\":false}},\"root\":{},\"observed_file_count\":{},\"run_status\":\"complete\"}}",q(&root.to_string_lossy()),self.files);
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
fn year(p: &Path) -> String {
    p.to_string_lossy()
        .split(|c: char| !c.is_ascii_digit())
        .find(|s| s.len() == 4)
        .unwrap_or("unknown")
        .into()
}
fn act_type(p: &Path) -> String {
    let s = p.to_string_lossy().to_lowercase();
    if s.contains("ukaz") {
        "decree".into()
    } else if s.contains("postan") {
        "resolution".into()
    } else if s.contains("fz") || s.contains("federal") || s.contains("law") {
        "law".into()
    } else {
        "unknown".into()
    }
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
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
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
                Some(Acc::default().render(&cli.label, &root)),
                "default root absent; skipped".into(),
            )
        };
    }
    let mut a = Acc {
        provider: "consultant".into(),
        ..Default::default()
    };
    let n = {
        let mut ob = Observer { acc: &mut a };
        match walk_and_observe(&root, cli.limit, &mut ob) {
            Ok(n) => n,
            Err(e) => return (EXIT_WALK_FAILED, None, e.to_string()),
        }
    };
    if cli.profile == "contour" {
        let g = root.parent().unwrap_or(&root).join("law-source/garant");
        if g.is_dir() {
            let mut ga = Acc {
                provider: "garant".into(),
                ..Default::default()
            };
            for p in odts(&g)
                .into_iter()
                .take(cli.limit.unwrap_or(u64::MAX) as usize)
            {
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
                        ga.measure(&b)
                    }
                    None => ga.failed += 1,
                }
            }
            a.files += ga.files;
            a.decoded += ga.decoded;
            a.failed += ga.failed;
            for (k, v) in ga.stages {
                for (x, n) in v {
                    *a.stages.entry(k.clone()).or_default().entry(x).or_default() += n;
                }
            }
        }
    }
    let body = a.render(&cli.label, &root);
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
