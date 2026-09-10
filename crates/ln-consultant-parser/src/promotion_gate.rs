//! Fail-closed, revision-bound NPA promotion receipts.
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    path::Path,
    process::{Command, Stdio},
};

pub const SCHEMA: &str = "npa-promotion-receipts/v1";
const CAPS: [&str; 4] = ["parsing", "semantic", "identity", "temporal"];
const SCOPES: [&str; 6] = [
    "C2-bounded",
    "C3-holdout",
    "C4-full-diagnostics",
    "C5-100",
    "C5-400",
    "C5-800",
];
const INPUTS: [&str; 7] = [
    "prd/architecture/npa-metric-baselines.yaml",
    "prd/architecture/npa-promotion-gates.json",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-100.json",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-400.json",
    "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-800.json",
    "prd/migration/rust-evidence/m203-s08-ledger-events.jsonl",
    "prd/migration/rust-evidence/m203-s08-quality-receipts.jsonl",
];

#[derive(Debug, Clone, PartialEq)]
enum V {
    Obj(BTreeMap<String, V>),
    Arr(Vec<V>),
    Str(String),
    Num(u64),
    Bool(bool),
    Null,
}
impl V {
    fn obj(&self, key: &str) -> Option<&V> {
        match self {
            V::Obj(map) => map.get(key),
            _ => None,
        }
    }
    fn str(&self, key: &str) -> Option<&str> {
        match self.obj(key) {
            Some(V::Str(value)) => Some(value),
            _ => None,
        }
    }
}

struct Json<'a> {
    bytes: &'a [u8],
    pos: usize,
}
impl<'a> Json<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            bytes: input.as_bytes(),
            pos: 0,
        }
    }
    fn whitespace(&mut self) {
        while self.pos < self.bytes.len() && self.bytes[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }
    fn value(&mut self) -> Result<V, String> {
        self.whitespace();
        match self.bytes.get(self.pos) {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => self.string().map(V::Str),
            Some(b'n') => {
                self.literal(b"null")?;
                Ok(V::Null)
            }
            Some(b't') => {
                self.literal(b"true")?;
                Ok(V::Bool(true))
            }
            Some(b'f') => {
                self.literal(b"false")?;
                Ok(V::Bool(false))
            }
            Some(b'0'..=b'9') => self.number(),
            Some(_) => Err("invalid JSON token".into()),
            None => Err("unexpected end of JSON".into()),
        }
    }
    fn literal(&mut self, expected: &[u8]) -> Result<(), String> {
        if self.bytes.get(self.pos..self.pos + expected.len()) == Some(expected) {
            self.pos += expected.len();
            Ok(())
        } else {
            Err("invalid JSON literal".into())
        }
    }
    fn string(&mut self) -> Result<String, String> {
        self.pos += 1;
        let mut out = String::new();
        while let Some(byte) = self.bytes.get(self.pos) {
            match byte {
                b'"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.pos += 1;
                    let escaped = match self.bytes.get(self.pos) {
                        Some(b'"') => '"',
                        Some(b'\\') => '\\',
                        Some(b'n') => '\n',
                        Some(b'r') => '\r',
                        Some(b't') => '\t',
                        _ => return Err("unsupported JSON escape".into()),
                    };
                    out.push(escaped);
                    self.pos += 1;
                }
                byte => {
                    out.push(*byte as char);
                    self.pos += 1;
                }
            }
        }
        Err("unterminated JSON string".into())
    }
    fn number(&mut self) -> Result<V, String> {
        let start = self.pos;
        while self.bytes.get(self.pos).is_some_and(u8::is_ascii_digit) {
            self.pos += 1;
        }
        let n = std::str::from_utf8(&self.bytes[start..self.pos])
            .unwrap()
            .parse()
            .map_err(|_| "bad number")?;
        Ok(V::Num(n))
    }
    fn object(&mut self) -> Result<V, String> {
        self.pos += 1;
        let mut map = BTreeMap::new();
        loop {
            self.whitespace();
            if self.bytes.get(self.pos) == Some(&b'}') {
                self.pos += 1;
                return Ok(V::Obj(map));
            }
            let key = self.string()?;
            self.whitespace();
            if self.bytes.get(self.pos) != Some(&b':') {
                return Err("expected colon".into());
            }
            self.pos += 1;
            map.insert(key, self.value()?);
            self.whitespace();
            match self.bytes.get(self.pos) {
                Some(b',') => self.pos += 1,
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(V::Obj(map));
                }
                _ => return Err("expected object delimiter".into()),
            }
        }
    }
    fn array(&mut self) -> Result<V, String> {
        self.pos += 1;
        let mut values = Vec::new();
        loop {
            self.whitespace();
            if self.bytes.get(self.pos) == Some(&b']') {
                self.pos += 1;
                return Ok(V::Arr(values));
            }
            values.push(self.value()?);
            self.whitespace();
            match self.bytes.get(self.pos) {
                Some(b',') => self.pos += 1,
                Some(b']') => {
                    self.pos += 1;
                    return Ok(V::Arr(values));
                }
                _ => return Err("expected array delimiter".into()),
            }
        }
    }
}
fn parse(input: &str) -> Result<V, String> {
    let mut parser = Json::new(input);
    let value = parser.value()?;
    parser.whitespace();
    if parser.pos == parser.bytes.len() {
        Ok(value)
    } else {
        Err("trailing JSON data".into())
    }
}
fn esc(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}
fn gate_exists(gates: &V, capability: &str, scope: &str) -> bool {
    gates
        .obj("promotion_gates")
        .and_then(|v| match v {
            V::Arr(items) => Some(items),
            _ => None,
        })
        .is_some_and(|items| {
            items.iter().any(|gate| {
                gate.str("capability") == Some(capability)
                    && gate.str("corpus_scope") == Some(scope)
            })
        })
}
fn object_numbers(value: Option<&V>) -> String {
    match value {
        Some(V::Obj(map)) => format!(
            "{{{}}}",
            map.iter()
                .filter_map(|(key, value)| match value {
                    V::Num(number) => Some(format!("\"{}\":{number}", esc(key))),
                    _ => None,
                })
                .collect::<Vec<_>>()
                .join(",")
        ),
        _ => "{}".into(),
    }
}

pub fn binding_for_paths(root: &Path, paths: &[&str]) -> Result<String, String> {
    let mut hashes = Vec::new();
    for path in paths {
        let output = Command::new("sha256sum")
            .arg(root.join(path))
            .output()
            .map_err(|e| format!("sha256sum {path}: {e}"))?;
        if !output.status.success() {
            return Err(format!("cannot hash binding input: {path}"));
        }
        let hash = String::from_utf8_lossy(&output.stdout)
            .split_whitespace()
            .next()
            .ok_or("empty sha256sum")?
            .to_string();
        hashes.push((path, hash));
    }
    hashes.sort_by(|a, b| a.0.cmp(b.0));
    let mut input = Vec::new();
    for (_, hash) in hashes {
        input.extend_from_slice(hash.as_bytes());
        input.push(b'\n');
    }
    let mut command = Command::new("sha256sum");
    command
        .arg("-")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped());
    let mut child = command.spawn().map_err(|e| e.to_string())?;
    child
        .stdin
        .as_mut()
        .ok_or("sha256sum stdin unavailable")?
        .write_all(&input)
        .map_err(|e| e.to_string())?;
    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    let hash = String::from_utf8_lossy(&output.stdout)
        .split_whitespace()
        .next()
        .ok_or("empty binding hash")?
        .to_string();
    Ok(format!("sha256:{hash}"))
}
pub fn current_binding(root: &Path) -> Result<String, String> {
    binding_for_paths(root, &INPUTS)
}

pub fn eval(root: &Path, output: &Path) -> Result<usize, String> {
    let gates = parse(&fs::read_to_string(root.join(INPUTS[1])).map_err(|e| e.to_string())?)?;
    let binding = current_binding(root)?;
    let quality = fs::read_to_string(root.join(INPUTS[6])).map_err(|e| e.to_string())?;
    let receipts = quality
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(parse)
        .collect::<Result<Vec<_>, _>>()?;
    let mut text = String::new();
    let mut blocked = 0;
    for capability in CAPS {
        for scope in SCOPES {
            let matching = receipts.iter().find(|receipt| {
                receipt
                    .str("evidence_id")
                    .is_some_and(|id| id.eq_ignore_ascii_case(scope))
            });
            let outcome = if !gate_exists(&gates, capability, scope) {
                "blocked-scope"
            } else if matching.is_none() {
                "blocked-threshold"
            } else {
                "blocked-human-gate"
            };
            blocked += 1;
            let (zero, layers) = matching.map_or(("{}".into(), "{}".into()), |r| {
                (
                    object_numbers(r.obj("zero_tolerance")),
                    object_numbers(r.obj("layers")),
                )
            });
            text.push_str(&format!("{{\"schema\":\"{SCHEMA}\",\"capability\":\"{capability}\",\"corpus_scope\":\"{scope}\",\"from_state\":\"S4\",\"to_state\":\"S5\",\"thresholds_checked\":{{\"zero_tolerance\":{zero},\"per_layer\":{layers}}},\"human_acceptance\":null,\"outcome\":\"{outcome}\",\"revision_binding\":\"{binding}\",\"parser_revision\":\"m203-s08-c5-ladder-v1\",\"requirement_debt\":[\"R035\",\"R070\"],\"rollback_ref\":\"prd/architecture/npa-metric-baselines.yaml#/rollback_criteria\",\"non_claims\":[\"promotions do not create product readiness\",\"promotions do not close R035 or R070\"]}}\n"));
        }
    }
    fs::write(output, text).map_err(|e| e.to_string())?;
    Ok(blocked)
}

pub fn check(root: &Path, receipt_path: &Path) -> Result<(), String> {
    let binding = current_binding(root)?;
    let gates = parse(&fs::read_to_string(root.join(INPUTS[1])).map_err(|e| e.to_string())?)?;
    let text = fs::read_to_string(receipt_path).map_err(|e| e.to_string())?;
    let mut seen = std::collections::BTreeSet::new();
    for line in text.lines().filter(|line| !line.trim().is_empty()) {
        let receipt = parse(line)?;
        if receipt.str("schema") != Some(SCHEMA) {
            return Err("invalid receipt schema".into());
        }
        let capability = receipt.str("capability").ok_or("missing capability")?;
        let scope = receipt.str("corpus_scope").ok_or("missing corpus_scope")?;
        if !gate_exists(&gates, capability, scope) {
            return Err("unknown capability or scope".into());
        }
        if !seen.insert((capability.to_string(), scope.to_string())) {
            return Err("duplicate capability/scope receipt".into());
        }
        if receipt.str("revision_binding") != Some(binding.as_str()) {
            return Err("stale revision binding".into());
        }
        if receipt.str("outcome") == Some("promoted") {
            return Err("promoted receipt is forbidden without human evidence".into());
        }
    }
    if seen.len() != 24 {
        return Err("receipt matrix is incomplete".into());
    }
    let ledger = fs::read_to_string(root.join(INPUTS[5])).map_err(|e| e.to_string())?;
    crate::drift_baseline::validate_ledger(&ledger)
}
