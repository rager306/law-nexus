//! Frozen C2/C3 corpus manifests: a dependency-free, fail-closed boundary.
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::Path,
};
pub const SCHEMA: &str = "law-nexus-npa-corpus-manifest/v1";
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Admission {
    BoundedReviewed,
    HoldoutSealed,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ManifestEntry {
    pub entry_id: String,
    pub document_relative_path: String,
    pub content_hash: String,
    pub evidence_anchor: String,
    pub admission: Admission,
    pub provider: String,
    pub year: String,
    pub document_type: String,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorpusManifest {
    pub schema_version: String,
    pub manifest_id: String,
    pub stratum: String,
    pub parser_revision: String,
    pub corpus_snapshot_hash: String,
    pub provider_strata: BTreeMap<String, usize>,
    pub environment: BTreeMap<String, String>,
    pub entries: Vec<ManifestEntry>,
    pub lifecycle: String,
    pub sealed: bool,
    pub manifest_digest: Option<String>,
    pub draw_seed: u64,
    pub nesting_rule: String,
}
#[derive(Debug, Clone)]
enum J {
    S(String),
    N(String),
    B(bool),
    A(Vec<J>),
    O(BTreeMap<String, J>),
    Null,
}
struct P<'a> {
    b: &'a [u8],
    i: usize,
}
impl<'a> P<'a> {
    fn new(s: &'a str) -> Self {
        Self {
            b: s.as_bytes(),
            i: 0,
        }
    }
    fn ws(&mut self) {
        while self.b.get(self.i).is_some_and(|b| b.is_ascii_whitespace()) {
            self.i += 1
        }
    }
    fn err<T>(&self, m: &str) -> Result<T, String> {
        Err(format!("JSON at byte {}: {m}", self.i))
    }
    fn val(&mut self) -> Result<J, String> {
        self.ws();
        match self.b.get(self.i) {
            Some(b'"') => Ok(J::S(self.string()?)),
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b't') => {
                self.literal("true")?;
                Ok(J::B(true))
            }
            Some(b'f') => {
                self.literal("false")?;
                Ok(J::B(false))
            }
            Some(b'n') => {
                self.literal("null")?;
                Ok(J::Null)
            }
            Some(b'-' | b'0'..=b'9') => self.number(),
            _ => self.err("unexpected value"),
        }
    }
    fn literal(&mut self, s: &str) -> Result<(), String> {
        if self.b[self.i..].starts_with(s.as_bytes()) {
            self.i += s.len();
            Ok(())
        } else {
            self.err("invalid literal")
        }
    }
    fn string(&mut self) -> Result<String, String> {
        self.i += 1;
        let mut s = String::new();
        loop {
            let Some(&b) = self.b.get(self.i) else {
                return self.err("unterminated string");
            };
            self.i += 1;
            match b {
                b'"' => return Ok(s),
                b'\\' => {
                    let Some(&e) = self.b.get(self.i) else {
                        return self.err("bad escape");
                    };
                    self.i += 1;
                    match e {
                        b'"' => s.push('"'),
                        b'\\' => s.push('\\'),
                        b'/' => s.push('/'),
                        b'n' => s.push('\n'),
                        b'r' => s.push('\r'),
                        b't' => s.push('\t'),
                        b'u' => {
                            let mut code = 0u32;
                            for _ in 0..4 {
                                let Some(&h) = self.b.get(self.i) else {
                                    return self.err("short unicode escape");
                                };
                                self.i += 1;
                                let digit = match h {
                                    b'0'..=b'9' => (h - b'0') as u32,
                                    b'a'..=b'f' => (h - b'a' + 10) as u32,
                                    b'A'..=b'F' => (h - b'A' + 10) as u32,
                                    _ => return self.err("invalid unicode escape"),
                                };
                                code = code * 16 + digit;
                            }
                            let Some(ch) = char::from_u32(code) else {
                                return self.err("invalid unicode codepoint");
                            };
                            s.push(ch);
                        }
                        _ => return self.err("unsupported escape"),
                    }
                }
                0..=31 => return self.err("control in string"),
                _ => s.push(b as char),
            }
        }
    }
    fn number(&mut self) -> Result<J, String> {
        let a = self.i;
        if self.b.get(self.i) == Some(&b'-') {
            self.i += 1
        }
        while self.b.get(self.i).is_some_and(|b| b.is_ascii_digit()) {
            self.i += 1
        }
        if a == self.i {
            return self.err("invalid number");
        };
        Ok(J::N(String::from_utf8_lossy(&self.b[a..self.i]).into()))
    }
    fn object(&mut self) -> Result<J, String> {
        self.i += 1;
        let mut m = BTreeMap::new();
        self.ws();
        if self.b.get(self.i) == Some(&b'}') {
            self.i += 1;
            return Ok(J::O(m));
        }
        loop {
            self.ws();
            if self.b.get(self.i) != Some(&b'"') {
                return self.err("object key");
            };
            let k = self.string()?;
            self.ws();
            if self.b.get(self.i) != Some(&b':') {
                return self.err("colon");
            };
            self.i += 1;
            let v = self.val()?;
            if m.insert(k, v).is_some() {
                return self.err("duplicate key");
            };
            self.ws();
            match self.b.get(self.i) {
                Some(b',') => self.i += 1,
                Some(b'}') => {
                    self.i += 1;
                    return Ok(J::O(m));
                }
                _ => return self.err("object separator"),
            }
        }
    }
    fn array(&mut self) -> Result<J, String> {
        self.i += 1;
        let mut a = Vec::new();
        self.ws();
        if self.b.get(self.i) == Some(&b']') {
            self.i += 1;
            return Ok(J::A(a));
        }
        loop {
            a.push(self.val()?);
            self.ws();
            match self.b.get(self.i) {
                Some(b',') => self.i += 1,
                Some(b']') => {
                    self.i += 1;
                    return Ok(J::A(a));
                }
                _ => return self.err("array separator"),
            }
        }
    }
}
fn map(j: J) -> Result<BTreeMap<String, J>, String> {
    match j {
        J::O(m) => Ok(m),
        _ => Err("expected object".into()),
    }
}
fn s(m: &BTreeMap<String, J>, k: &str) -> Result<String, String> {
    match m.get(k) {
        Some(J::S(v)) if !v.trim().is_empty() => Ok(v.clone()),
        Some(_) => Err(format!("{k}: expected non-empty string")),
        None => Err(format!("missing key {k}")),
    }
}
fn a<'x>(m: &'x BTreeMap<String, J>, k: &str) -> Result<&'x [J], String> {
    match m.get(k) {
        Some(J::A(v)) => Ok(v),
        _ => Err(format!("{k}: expected array")),
    }
}
fn closed(m: &BTreeMap<String, J>, allow: &[&str], ctx: &str) -> Result<(), String> {
    if let Some(k) = m.keys().find(|k| !allow.contains(&k.as_str())) {
        Err(format!("{ctx}: unexpected key {k}"))
    } else {
        Ok(())
    }
}
fn sha(data: &[u8]) -> String {
    use std::process::Command;
    let mut c = Command::new("sha256sum");
    c.arg("-");
    use std::process::Stdio;
    let o = c
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .and_then(|mut p| {
            use std::io::Write;
            p.stdin.as_mut().unwrap().write_all(data)?;
            p.wait_with_output()
        });
    match o {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout)
            .split_whitespace()
            .next()
            .unwrap_or_default()
            .into(),
        _ => panic!("sha256sum is required for frozen manifest verification"),
    }
}
pub fn load(path: &Path) -> Result<CorpusManifest, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut p = P::new(&text);
    let root = map(p.val()?)?;
    p.ws();
    if p.i != p.b.len() {
        return Err(format!("JSON at byte {}: trailing JSON", p.i));
    }
    closed(
        &root,
        &[
            "schema_version",
            "manifest_id",
            "stratum",
            "parser_revision",
            "corpus_snapshot_hash",
            "provider_strata",
            "environment",
            "entries",
            "lifecycle",
            "sealed",
            "manifest_digest",
            "draw_seed",
            "nesting_rule",
        ],
        "manifest",
    )?;
    let schema = s(&root, "schema_version")?;
    if schema != SCHEMA {
        return Err(format!("schema_version must be {SCHEMA}"));
    }
    let id = s(&root, "manifest_id")?;
    if !id.starts_with("NPA-MAN-")
        || id
            .chars()
            .any(|c| !(c.is_ascii_uppercase() || c.is_ascii_digit() || c == '-'))
    {
        return Err("manifest_id must match NPA-MAN pattern".into());
    }
    let stratum = s(&root, "stratum")?;
    if stratum != "C2" && stratum != "C3" {
        return Err("stratum must be C2 or C3".into());
    }
    let snap = s(&root, "corpus_snapshot_hash")?;
    if !snap.starts_with("sha256:") {
        return Err("corpus_snapshot_hash must start sha256:".into());
    }
    let life = s(&root, "lifecycle")?;
    if life != "[bounded]" && life != "[diagnostic]" {
        return Err("invalid lifecycle".into());
    }
    let sealed = matches!(root.get("sealed"), Some(J::B(true)));
    let digest = match root.get("manifest_digest") {
        Some(J::S(v)) if v.starts_with("sha256:") => Some(v.clone()),
        Some(_) => return Err("manifest_digest must start sha256:".into()),
        None => None,
    };
    if stratum == "C3" && (!sealed || digest.is_none()) {
        return Err("C3 requires sealed and manifest_digest".into());
    }
    let em = map(root
        .get("environment")
        .cloned()
        .ok_or("missing environment")?)?;
    closed(
        &em,
        &["platform", "rust_toolchain", "command"],
        "environment",
    )?;
    let mut env = BTreeMap::new();
    for k in ["platform", "rust_toolchain", "command"] {
        env.insert(k.into(), s(&em, k)?);
    }
    let mut ps = BTreeMap::new();
    for x in a(&root, "provider_strata")? {
        let m = map(x.clone())?;
        closed(
            &m,
            &[
                "provider",
                "year",
                "document_type",
                "quota",
                "availability_cap",
            ],
            "provider_strata",
        )?;
        let q = match m.get("quota") {
            Some(J::N(v)) => v.parse::<usize>().map_err(|_| "quota must be integer")?,
            _ => return Err("quota must be integer".into()),
        };
        if q == 0 {
            return Err("quota must be positive".into());
        }
        ps.insert(s(&m, "provider")?, q);
    }
    let mut entries = Vec::new();
    let mut ids = BTreeSet::new();
    let mut hashes = BTreeSet::new();
    for x in a(&root, "entries")? {
        let m = map(x.clone())?;
        closed(
            &m,
            &[
                "entry_id",
                "document_relative_path",
                "content_hash",
                "evidence_anchor",
                "admission",
                "provider",
                "year",
                "document_type",
            ],
            "entry",
        )?;
        let eid = s(&m, "entry_id")?;
        if !ids.insert(eid.clone()) {
            return Err("duplicate entry_id".into());
        }
        let rel = s(&m, "document_relative_path")?;
        if rel.starts_with('/') || rel.contains("..") {
            return Err("document_relative_path must be relative and without ..".into());
        }
        let hash = s(&m, "content_hash")?;
        if hash.len() != 71
            || !hash.starts_with("sha256:")
            || !hash[7..].chars().all(|c| c.is_ascii_hexdigit())
        {
            return Err(format!("{eid}: invalid content_hash"));
        }
        if !hashes.insert(hash.clone()) {
            return Err(format!("duplicate content_hash at {eid}"));
        }
        let admission = match s(&m, "admission")?.as_str() {
            "bounded_reviewed" => Admission::BoundedReviewed,
            "holdout_sealed" => Admission::HoldoutSealed,
            _ => return Err("invalid admission".into()),
        };
        let anchor = s(&m, "evidence_anchor")?;
        if anchor.contains("raw") || anchor.contains("text") {
            return Err("evidence_anchor cannot contain raw-text-like fields".into());
        }
        entries.push(ManifestEntry {
            entry_id: eid,
            document_relative_path: rel,
            content_hash: hash,
            evidence_anchor: anchor,
            admission,
            provider: s(&m, "provider")?,
            year: s(&m, "year")?,
            document_type: s(&m, "document_type")?,
        })
    }
    if entries.is_empty() {
        return Err("entries must not be empty".into());
    }
    let seed = match root.get("draw_seed") {
        Some(J::N(v)) => v.parse().map_err(|_| "draw_seed must be integer")?,
        _ => return Err("draw_seed must be integer".into()),
    };
    let nesting = s(&root, "nesting_rule")?;
    let out = CorpusManifest {
        schema_version: schema,
        manifest_id: id,
        stratum: stratum.clone(),
        parser_revision: s(&root, "parser_revision")?,
        corpus_snapshot_hash: snap,
        provider_strata: ps,
        environment: env,
        entries,
        lifecycle: life,
        sealed,
        manifest_digest: digest.clone(),
        draw_seed: seed,
        nesting_rule: nesting,
    };
    if stratum == "C3" {
        let marker = "\"manifest_digest\": \"";
        let start = text.find(marker).ok_or("missing manifest_digest")? + marker.len();
        let end = text[start..].find('"').ok_or("bad manifest_digest")? + start;
        let mut blank = text.clone();
        blank.replace_range(start..end, "");
        let expected = format!("sha256:{}", sha(blank.as_bytes()));
        if digest.as_deref() != Some(expected.as_str()) {
            return Err("manifest_digest does not bind manifest bytes".into());
        }
    }
    Ok(out)
}
pub fn disjoint(a: &CorpusManifest, b: &CorpusManifest) -> bool {
    let x: BTreeSet<_> = a.entries.iter().map(|e| e.content_hash.as_str()).collect();
    b.entries
        .iter()
        .all(|e| !x.contains(e.content_hash.as_str()))
}
