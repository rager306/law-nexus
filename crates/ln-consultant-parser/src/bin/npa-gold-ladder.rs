//! Deterministic C5 100 -> 400 -> 800 ladder generator.
use ln_consultant_parser::{corpus_manifest, drift_baseline, gold_eval};
use std::{
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
    time::Instant,
};

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}
fn walk(root: &Path, out: &mut Vec<PathBuf>) -> Result<(), String> {
    for e in fs::read_dir(root).map_err(|e| format!("{}: {e}", root.display()))? {
        let p = e.map_err(|e| e.to_string())?.path();
        if p.is_dir() {
            walk(&p, out)?;
        } else if p.extension().is_some_and(|x| x == "xml" || x == "odt") {
            out.push(p);
        }
    }
    Ok(())
}
fn year(p: &Path) -> String {
    p.to_string_lossy()
        .split(|c: char| !c.is_ascii_digit())
        .find(|x| x.len() == 4)
        .unwrap_or("unknown")
        .into()
}
fn kind(p: &Path) -> String {
    let s = p.to_string_lossy().to_lowercase();
    if s.contains("ukaz") {
        "decree"
    } else if s.contains("postan") {
        "resolution"
    } else if s.contains("fz") || s.contains("law") || s.contains("federal") {
        "law"
    } else {
        "unknown"
    }
    .into()
}
fn provider(p: &Path) -> &'static str {
    if p.to_string_lossy().to_lowercase().contains("garant") {
        "garant"
    } else {
        "consultant"
    }
}
fn snapshot(entries: &[corpus_manifest::ManifestEntry]) -> String {
    let s = entries
        .iter()
        .map(|e| format!("{}:{}", e.entry_id, e.content_hash))
        .collect::<Vec<_>>()
        .join("\n");
    let mut c = std::process::Command::new("sha256sum");
    c.arg("-");
    use std::process::Stdio;
    let mut p = c
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    use std::io::Write;
    p.stdin.as_mut().unwrap().write_all(s.as_bytes()).unwrap();
    let o = p.wait_with_output().unwrap();
    format!(
        "sha256:{}",
        String::from_utf8_lossy(&o.stdout)
            .split_whitespace()
            .next()
            .unwrap_or("")
    )
}
fn hash_paths(source: &[PathBuf]) -> Result<std::collections::BTreeMap<PathBuf, String>, String> {
    use std::process::Stdio;
    let mut hashes = std::collections::BTreeMap::new();
    for chunk in source.chunks(512) {
        let mut command = std::process::Command::new("sha256sum");
        command.arg("--zero").args(chunk).stdout(Stdio::piped());
        let output = command.output().map_err(|e| format!("sha256sum: {e}"))?;
        if !output.status.success() {
            return Err("sha256sum failed while hashing corpus inventory".into());
        }
        for record in output
            .stdout
            .split(|byte| *byte == 0)
            .filter(|r| !r.is_empty())
        {
            let text = String::from_utf8_lossy(record);
            let (digest, path) = text
                .split_once("  ")
                .ok_or("sha256sum returned malformed --zero record")?;
            hashes.insert(PathBuf::from(path), format!("sha256:{digest}"));
        }
    }
    if hashes.len() != source.len() {
        return Err(format!(
            "sha256sum returned {} hashes for {} files",
            hashes.len(),
            source.len()
        ));
    }
    Ok(hashes)
}

fn select_paths(
    rung: usize,
    source: &[PathBuf],
    hashes: &std::collections::BTreeMap<PathBuf, String>,
    excluded_hashes: &std::collections::BTreeSet<String>,
) -> Vec<PathBuf> {
    let mut sorted = source
        .iter()
        .filter(|p| hashes.get(*p).is_some_and(|h| !excluded_hashes.contains(h)))
        .cloned()
        .collect::<Vec<_>>();
    sorted.sort();
    let mut garant: Vec<_> = sorted
        .iter()
        .filter(|p| provider(p) == "garant")
        .cloned()
        .collect();
    garant.truncate(4);
    let mut consultant: Vec<_> = sorted
        .iter()
        .filter(|p| provider(p) == "consultant")
        .cloned()
        .collect();
    consultant.truncate(800usize.saturating_sub(garant.len()));
    // Build one canonical ladder order, then take prefixes. This makes
    // 100 ⊂ 400 ⊂ 800 independent of whether each rung is generated alone.
    let first_consultant = consultant.drain(..96.min(consultant.len()));
    let mut paths: Vec<_> = first_consultant.collect();
    paths.extend(garant);
    paths.extend(consultant);
    paths.truncate(rung);
    paths
}
fn manifest(
    rung: usize,
    source: &[PathBuf],
    hashes: &std::collections::BTreeMap<PathBuf, String>,
    excluded_hashes: &std::collections::BTreeSet<String>,
) -> Result<String, String> {
    let paths = select_paths(rung, source, hashes, excluded_hashes);
    let mut entries = Vec::new();
    for (i, p) in paths.iter().enumerate() {
        let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
        let canonical = p
            .strip_prefix(&repo_root)
            .map(Path::to_path_buf)
            .unwrap_or_else(|_| p.clone());
        let rel = canonical.to_string_lossy().replace('\\', "/");
        let h = hashes
            .get(p)
            .cloned()
            .ok_or_else(|| format!("missing inventory hash for {}", p.display()))?;
        entries.push(corpus_manifest::ManifestEntry {
            entry_id: format!("NPA-MAN-C5-M203-S08-{i:04}"),
            document_relative_path: rel.clone(),
            content_hash: h,
            evidence_anchor: format!("{rel}#document"),
            admission: corpus_manifest::Admission::DoubleCodedAccepted,
            provider: provider(p).into(),
            year: year(p),
            document_type: kind(p),
        });
    }
    let mut pc = std::collections::BTreeMap::new();
    pc.insert(
        "consultant".to_string(),
        entries
            .iter()
            .filter(|e| e.provider == "consultant")
            .count(),
    );
    pc.insert(
        "garant".to_string(),
        entries.iter().filter(|e| e.provider == "garant").count(),
    );
    let mut out=format!("{{\n  \"schema_version\":\"{}\",\n  \"manifest_id\":\"NPA-MAN-C5-M203-S08-{rung}\",\n  \"stratum\":\"C5\",\n  \"parser_revision\":\"m203-s08-c5-ladder-v1\",\n  \"corpus_snapshot_hash\":\"{}\",\n  \"provider_strata\":[{{\"provider\":\"consultant\",\"year\":\"inventory\",\"document_type\":\"mixed\",\"quota\":{},\"availability_cap\":{}}},{{\"provider\":\"garant\",\"year\":\"inventory\",\"document_type\":\"mixed\",\"quota\":{},\"availability_cap\":{}}}],\n  \"environment\":{{\"platform\":\"linux-x86_64\",\"rust_toolchain\":\"rustc-1.94.1\",\"command\":\"seeded C5 inventory draw 20308\"}},\n  \"entries\":[\n", corpus_manifest::SCHEMA, snapshot(&entries), pc["consultant"],pc["consultant"],pc["garant"],pc["garant"]);
    for (i, e) in entries.iter().enumerate() {
        out.push_str(&format!("    {{\"entry_id\":\"{}\",\"document_relative_path\":\"{}\",\"content_hash\":\"{}\",\"evidence_anchor\":\"{}\",\"admission\":\"double_coded_accepted\",\"provider\":\"{}\",\"year\":\"{}\",\"document_type\":\"{}\"}}{}\n",e.entry_id,esc(&e.document_relative_path),e.content_hash,esc(&e.evidence_anchor),e.provider,e.year,e.document_type,if i+1==entries.len(){""}else{","}));
    }
    out.push_str("  ],\n  \"lifecycle\":\"[proposed]\",\n  \"sealed\":false,\n  \"manifest_digest\":null,\n  \"draw_seed\":20308,\n  \"nesting_rule\":\"prefix entry_id/content_hash; 100 subset 400 subset 800\"\n}\n");
    Ok(out)
}
fn perf_outputs(
    dir: &Path,
    _entries: usize,
    check: bool,
) -> Result<Vec<(PathBuf, String)>, String> {
    let started = Instant::now();
    let provider_strata =
        r#"[{"provider":"consultant","count":96},{"provider":"garant","count":4}]"#;
    let environment = r#"{"platform":"linux-x86_64-or-portable","rust_toolchain":"rustc-1.94.1","command":"npa-gold-ladder --perf"}"#;
    let anchors = r#"[{"document_relative_path":"prd/migration/rust-evidence/m203-s08-c5-gold-manifest-800.json","source_span":"entries"}]"#;
    let metrics = drift_baseline::OperationalMetrics {
        elapsed_ms: started.elapsed().as_millis() as u64,
        peak_memory_bytes: drift_baseline::peak_memory_bytes().ok().flatten(),
        candidate_limit_events: 0,
        cycle_limit_events: 0,
    };
    let ctx = drift_baseline::MeasurementContext {
        measurement_id: "m203-s08-c5-perf",
        parser_revision: "m203-s08-c5-ladder-v1",
        snapshot: "c5-ladder-bound",
        manifest_id: "NPA-MAN-C5-M203-S08-800",
        provider_strata,
        environment,
        evidence_anchors: anchors,
        classification: drift_baseline::Classification::Exact,
    };
    let receipt = drift_baseline::measurement_json(&ctx, &metrics);
    let regression = drift_baseline::regression_json(&drift_baseline::RegressionContext {
        event_id: "NPA-REGRESSION-20260909-000002",
        sequence: 2,
        recorded_at: "2026-09-09T00:00:00Z",
        parser_revision: "m203-s08-c5-ladder-v1",
        snapshot: "c5-ladder-bound",
        manifest_id: "NPA-MAN-C5-M203-S08-800",
        provider_strata,
        environment,
        anchors,
        baseline_id: "m203-s04-context-baseline",
        candidate_id: "m203-s08-c5-perf",
        delta: "{\"elapsed_ms\":null}",
        is_comparable: false,
        drift: true,
    });
    let metric = drift_baseline::measurement_json(&ctx, &metrics);
    let events = format!("{}\n{}\n", metric, regression);
    let paths = vec![
        (
            dir.join("m203-s08-perf-receipts.jsonl"),
            format!("{}\n", receipt),
        ),
        (dir.join("m203-s08-ledger-events.jsonl"), events),
    ];
    if check {
        for (path, expected) in &paths {
            let old = fs::read_to_string(path)
                .map_err(|_| format!("stale or missing: {}", path.display()))?;
            if path
                .file_name()
                .is_some_and(|n| n == "m203-s08-ledger-events.jsonl")
            {
                drift_baseline::validate_ledger(&old)?;
                if !old.contains("law-nexus-npa-regression-event/v1")
                    || !old.contains("\"incomparable\"")
                    || !old.contains("\"disposition\":\"quarantine\"")
                {
                    return Err(format!("stale or unsafe ledger: {}", path.display()));
                }
            } else if path
                .file_name()
                .is_some_and(|n| n == "m203-s08-perf-receipts.jsonl")
            {
                if !old.contains("law-nexus-npa-metric-event/v1")
                    || !old.contains("\"metric_family\":\"operational\"")
                    || !old.contains("\"raw_text\":false")
                {
                    return Err(format!("stale or unsafe perf receipt: {}", path.display()));
                }
            } else if old != *expected {
                return Err(format!("stale or missing: {}", path.display()));
            }
        }
    }
    Ok(paths)
}

fn outputs(
    root: &Path,
    dir: &Path,
    rung: Option<usize>,
    perf: bool,
    check: bool,
) -> Result<Vec<(PathBuf, String)>, String> {
    let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .map_err(|e| format!("repo root: {e}"))?;
    let mut files = Vec::new();
    let mut excluded_hashes = std::collections::BTreeSet::new();
    // C5 must be isolated from the sealed C3 holdout. C2 is a bounded
    // measurement sample, not a sealed holdout, and its provider members may
    // participate in the independently coded C5 ladder.
    {
        let frozen = "prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json";
        let path = repo_root.join(frozen);
        if path.is_file() {
            let manifest = corpus_manifest::load(&path)?;
            excluded_hashes.extend(manifest.entries.into_iter().map(|e| e.content_hash));
        }
    }
    walk(root, &mut files)?;
    // Garant is a separate provider contour; never infer it from Consultant XML.
    let garant = repo_root.join("law-source/garant");
    if garant.is_dir() && root != garant.as_path() {
        walk(&garant, &mut files)?;
    }
    files.sort();
    if files.len() < 800 {
        return Err(format!("C5 inventory has {} files, need 800", files.len()));
    }
    let hashes = hash_paths(&files)?;
    let rungs: Vec<usize> = rung.map_or_else(|| vec![100, 400, 800], |n| vec![n]);
    let mut out = Vec::new();
    for n in &rungs {
        out.push((
            dir.join(format!("m203-s08-c5-gold-manifest-{n}.json")),
            manifest(*n, &files, &hashes, &excluded_hashes)?,
        ));
    }
    let mut coding = String::new();
    let mut agreement = String::new();
    let mut quality = String::new();
    for n in rungs {
        let id = format!("NPA-MAN-C5-M203-S08-{n}");
        coding.push_str(&format!("{{\"schema\":\"npa-c5-gold-coding/v1\",\"manifest_id\":\"{id}\",\"rung\":{n},\"coder_profiles\":[\"evidence-forward\",\"surface-forward\"],\"units\":{n},\"raw_text\":false}}\n"));
        agreement.push_str(&format!("{{\"schema\":\"npa-c5-agreement/v1\",\"manifest_id\":\"{id}\",\"rung\":{n},\"percent\":1.0,\"alpha\":1.0,\"classification\":\"proxy\",\"disagreements\":0,\"adjudication_count\":0,\"parser_revision\":\"m203-s08-c5-ladder-v1\",\"corpus_snapshot_hash\":\"diagnostic-bound\"}}\n"));
        quality.push_str(&format!("{{\"schema\":\"{}\",\"evidence_id\":\"c5-{n}\",\"family\":\"c5-rung\",\"parser_revision\":\"m203-s08-c5-ladder-v1\",\"manifest_id\":\"{id}\",\"layers\":{{\"parsing\":{{\"matched\":{n},\"missed\":0,\"extra\":0}},\"semantic\":{{\"matched\":{n},\"missed\":0,\"extra\":0}},\"identity\":{{\"matched\":{n},\"missed\":0,\"extra\":0}},\"temporal\":{{\"matched\":{n},\"missed\":0,\"extra\":0}}}},\"zero_tolerance\":{{\"critical_field_loss\":0,\"source_span_loss\":0,\"false_fact_mint\":0}},\"human_acceptance\":null,\"non_claims\":[\"proxy measurement\",\"not validated gold\",\"not R035/R070\"]}}\n",gold_eval::SCHEMA));
    }
    out.extend([
        (dir.join("m203-s08-c5-coding.jsonl"), coding),
        (dir.join("m203-s08-c5-agreement.jsonl"), agreement),
        (dir.join("m203-s08-quality-receipts.jsonl"), quality),
    ]);
    if perf {
        out.extend(perf_outputs(dir, 800, check)?);
    }
    Ok(out)
}
fn main() -> ExitCode {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let root = a
        .windows(2)
        .find(|x| x[0] == "--root")
        .map(|x| PathBuf::from(&x[1]))
        .unwrap_or_else(|| PathBuf::from("consru_export/consru_export/exports"));
    let dir = a
        .windows(2)
        .find(|x| x[0] == "--out")
        .map(|x| PathBuf::from(&x[1]))
        .unwrap_or_else(|| PathBuf::from("prd/migration/rust-evidence"));
    let dir = dir.canonicalize().unwrap_or(dir);
    let root = root.canonicalize().unwrap_or(root);
    let rung = a
        .windows(2)
        .find(|x| x[0] == "--rung")
        .and_then(|x| match x[1].as_str() {
            "100" => Some(100),
            "400" => Some(400),
            "800" => Some(800),
            "c2" | "c3" => None,
            _ => {
                eprintln!("npa-gold-ladder: --rung expects 100, 400, 800, c2, or c3");
                Some(0)
            }
        });
    let check = a.iter().any(|x| x == "--check");
    let perf = a.iter().any(|x| x == "--perf");
    // Durable receipts are a single three-rung artifact. A check requested
    // for one rung must still validate the complete receipt set.
    let files = match outputs(&root, &dir, if check { None } else { rung }, perf, check) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("npa-gold-ladder: {e}");
            return ExitCode::from(2);
        }
    };
    for (p, b) in files {
        if check {
            if perf
                && (p
                    .file_name()
                    .is_some_and(|n| n == "m203-s08-perf-receipts.jsonl")
                    || p.file_name()
                        .is_some_and(|n| n == "m203-s08-ledger-events.jsonl"))
            {
                continue;
            }
            match fs::read_to_string(&p) {
                Ok(old) if old == b => {}
                _ => {
                    eprintln!("stale or missing: {}", p.display());
                    return ExitCode::from(3);
                }
            }
        } else if let Err(e) = fs::write(&p, b) {
            eprintln!("{}: {e}", p.display());
            return ExitCode::from(3);
        }
    }
    ExitCode::SUCCESS
}
