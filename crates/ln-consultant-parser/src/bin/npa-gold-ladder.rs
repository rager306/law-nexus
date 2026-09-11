//! Deterministic C5 100 -> 400 -> 800 ladder generator.
use ln_consultant_parser::{
    corpus_manifest, corpus_sample, drift_baseline, gold_coding, gold_eval,
};
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

fn manifest(rung: usize, plan: &corpus_sample::DrawPlan) -> Result<String, String> {
    let mut entries = Vec::new();
    for (i, candidate) in plan.candidates.iter().enumerate() {
        let rel = candidate.relative_path.clone();
        let provider = match candidate.meta.provider {
            corpus_sample::SourceRootKind::ConsultantExport => "consultant",
            corpus_sample::SourceRootKind::Garant => "garant",
        };
        entries.push(corpus_manifest::ManifestEntry {
            entry_id: format!("NPA-MAN-C5-M204-S02-{i:04}"),
            document_relative_path: rel.clone(),
            content_hash: candidate.content_hash.clone(),
            evidence_anchor: format!("{rel}#document"),
            admission: corpus_manifest::Admission::BoundedReviewed,
            provider: provider.into(),
            year: candidate
                .meta
                .year
                .map_or_else(|| "unknown".into(), |y| y.to_string()),
            document_type: candidate.meta.document_type.clone(),
        });
    }
    let consultant = entries
        .iter()
        .filter(|e| e.provider == "consultant")
        .count();
    let garant = entries.iter().filter(|e| e.provider == "garant").count();
    let mut out = format!(
        "{{\n  \"schema_version\":\"{}\",\n  \"manifest_id\":\"NPA-MAN-C5-M204-S02-{rung}\",\n  \"stratum\":\"C5\",\n  \"parser_revision\":\"m204-s03-c5-ladder-v3\",\n  \"corpus_snapshot_hash\":\"{}\",\n  \"provider_strata\":[{{\"provider\":\"consultant\",\"year\":\"inventory\",\"document_type\":\"mixed\",\"quota\":{consultant},\"availability_cap\":{consultant}}},{{\"provider\":\"garant\",\"year\":\"inventory\",\"document_type\":\"mixed\",\"quota\":{garant},\"availability_cap\":4}}],\n  \"environment\":{{\"platform\":\"linux-x86_64\",\"rust_toolchain\":\"rustc-1.94.1\",\"command\":\"npa-gold-ladder --seed {}\"}},\n  \"entries\":[\n",
        corpus_manifest::SCHEMA,
        snapshot(&entries),
        plan.seed,
    );
    for (i, e) in entries.iter().enumerate() {
        out.push_str(&format!("    {{\"entry_id\":\"{}\",\"document_relative_path\":\"{}\",\"content_hash\":\"{}\",\"evidence_anchor\":\"{}\",\"admission\":\"bounded_reviewed\",\"provider\":\"{}\",\"year\":\"{}\",\"document_type\":\"{}\"}}{}\n", e.entry_id, esc(&e.document_relative_path), e.content_hash, esc(&e.evidence_anchor), e.provider, e.year, e.document_type, if i + 1 == entries.len() { "" } else { "," }));
    }
    out.push_str(&format!("  ],\n  \"lifecycle\":\"[proposed]\",\n  \"sealed\":false,\n  \"manifest_digest\":null,\n  \"draw_seed\":{},\n  \"nesting_rule\":\"prefix entry_id/content_hash; 100 subset 400 subset 800\"\n}}\n", plan.seed));
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
    garant_root: &Path,
    dir: &Path,
    rung: Option<usize>,
    seed: u64,
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
        if !path.is_file() {
            return Err(format!(
                "required frozen C3 manifest is missing: {}",
                path.display()
            ));
        }
        let manifest = corpus_manifest::load(&path)?;
        excluded_hashes.extend(manifest.entries.into_iter().map(|e| e.content_hash));
    }
    walk(root, &mut files)?;
    // Garant is a separate provider contour; never infer it from Consultant XML.
    if garant_root.is_dir() && root != garant_root {
        walk(garant_root, &mut files)?;
    }
    files.sort();
    if files.len() < 800 {
        return Err(format!("C5 inventory has {} files, need 800", files.len()));
    }
    let hashes = hash_paths(&files)?;
    let consultant_source = corpus_sample::CorpusRoot::new(
        root.to_path_buf(),
        corpus_sample::SourceRootKind::ConsultantExport,
    )?;
    let garant_source = corpus_sample::CorpusRoot::new(
        garant_root.to_path_buf(),
        corpus_sample::SourceRootKind::Garant,
    )?;
    let inventory = files
        .iter()
        .map(|path| {
            let meta = consultant_source
                .classify(path)
                .or_else(|_| garant_source.classify(path))?;
            Ok(corpus_sample::SampleCandidate {
                relative_path: meta.relative_path.clone(),
                content_hash: hashes
                    .get(path)
                    .cloned()
                    .ok_or_else(|| format!("missing inventory hash for {}", path.display()))?,
                meta,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    let rungs: Vec<usize> = rung.map_or_else(|| vec![100, 400, 800], |n| vec![n]);
    let mut out = Vec::new();
    let mut coding = String::new();
    let mut agreement = String::new();
    let mut quality = String::new();
    let mut leakage_rows = Vec::new();
    let status = gold_coding::MeasurementStatus::NotMeasured.as_str();
    for n in rungs {
        let plan = corpus_sample::draw(inventory.clone(), &excluded_hashes, n, seed)?;
        let leakage = &plan.leakage;
        leakage_rows.push(format!(
            "{{\"rung\":{n},\"requested\":{},\"selected\":{},\"input_candidates\":{},\"exact_duplicate_hashes\":{},\"excluded_c3_hashes\":{},\"collapsed_editions\":{},\"collapsed_families\":{},\"c3_family_overlap\":{},\"garant_cap\":{},\"garant_selected\":{},\"consultant_selected\":{},\"not_year_type_stratified\":{}}}",
            plan.requested,
            plan.candidates.len(),
            leakage.input_candidates,
            leakage.exact_duplicate_hashes,
            leakage.excluded_c3_hashes,
            leakage.collapsed_editions,
            leakage.collapsed_families,
            leakage.c3_family_overlap,
            leakage.garant_cap,
            leakage.garant_selected,
            leakage.consultant_selected,
            leakage.not_year_type_stratified,
        ));
        let rendered = manifest(n, &plan)?;
        let marker = "\"corpus_snapshot_hash\":\"";
        let start = rendered
            .find(marker)
            .ok_or("manifest missing snapshot binding")?
            + marker.len();
        let end = rendered[start..]
            .find('\"')
            .ok_or("manifest has malformed snapshot binding")?
            + start;
        let snapshot = rendered[start..end].to_owned();
        out.push((
            dir.join(format!("m204-s02-c5-gold-manifest-{n}.json")),
            rendered,
        ));
        let id = format!("NPA-MAN-C5-M204-S02-{n}");
        coding.push_str(&format!("{{\"schema\":\"npa-c5-gold-coding/v2\",\"manifest_id\":\"{id}\",\"rung\":{n},\"measurement_status\":\"{status}\",\"coder_profiles\":[],\"units\":0,\"raw_text\":false,\"corpus_snapshot_hash\":\"{snapshot}\"}}\n"));
        agreement.push_str(&format!("{{\"schema\":\"npa-c5-agreement/v2\",\"manifest_id\":\"{id}\",\"rung\":{n},\"measurement_status\":\"{status}\",\"percent\":null,\"alpha\":null,\"classification\":null,\"disagreements\":null,\"adjudication_count\":0,\"parser_revision\":\"m204-s03-c5-ladder-v3\",\"corpus_snapshot_hash\":\"{snapshot}\"}}\n"));
        quality.push_str(&format!("{{\"schema\":\"{}\",\"evidence_id\":\"c5-{n}\",\"family\":\"c5-rung\",\"parser_revision\":\"m204-s03-c5-ladder-v3\",\"manifest_id\":\"{id}\",\"measurement_status\":\"{status}\",\"corpus_snapshot_hash\":\"{snapshot}\",\"layers\":{{}},\"zero_tolerance\":{{}},\"human_acceptance\":null,\"non_claims\":[\"not measured\",\"not accepted gold\",\"not R035/R070\"]}}\n",gold_eval::SCHEMA));
    }
    out.extend([
        (dir.join("m204-s02-c5-coding.jsonl"), coding),
        (dir.join("m204-s02-c5-agreement.jsonl"), agreement),
        (dir.join("m204-s02-c5-quality-receipts.jsonl"), quality),
        (dir.join("m204-s03-sample-leakage.json"), format!("{{\"schema\":\"m204-s03-sample-leakage/v1\",\"seed\":{},\"non_claims\":[\"no raw text\",\"not a Work-family holdout\",\"C2 reuse is not independent evaluation\"],\"rungs\":[{}]}}\n", seed, leakage_rows.join(","))),
    ]);
    if perf {
        out.extend(perf_outputs(dir, 800, check)?);
    }
    Ok(out)
}
fn option_value(args: &[String], flag: &str) -> Result<Option<String>, String> {
    let Some(index) = args.iter().position(|arg| arg == flag) else {
        return Ok(None);
    };
    let value = args
        .get(index + 1)
        .ok_or_else(|| format!("{flag} requires a value"))?;
    if value.starts_with("--") {
        return Err(format!("{flag} requires a value"));
    }
    Ok(Some(value.clone()))
}

fn main() -> ExitCode {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let seed_arg = match option_value(&a, "--seed") {
        Ok(value) => value,
        Err(error) => {
            eprintln!("npa-gold-ladder: {error}");
            return ExitCode::from(2);
        }
    };
    let seed = match seed_arg {
        Some(value) => match value.parse::<u64>() {
            Ok(value) => value,
            Err(_) => {
                eprintln!("npa-gold-ladder: --seed expects an unsigned integer");
                return ExitCode::from(2);
            }
        },
        None => corpus_sample::DEFAULT_DRAW_SEED,
    };
    let root = match option_value(&a, "--root") {
        Ok(Some(value)) => PathBuf::from(value),
        Ok(None) => PathBuf::from("consru_export/consru_export/exports"),
        Err(error) => {
            eprintln!("npa-gold-ladder: {error}");
            return ExitCode::from(2);
        }
    };
    let dir = match option_value(&a, "--out") {
        Ok(Some(value)) => PathBuf::from(value),
        Ok(None) => PathBuf::from("prd/migration/rust-evidence"),
        Err(error) => {
            eprintln!("npa-gold-ladder: {error}");
            return ExitCode::from(2);
        }
    };
    let dir = dir.canonicalize().unwrap_or(dir);
    let root = root.canonicalize().unwrap_or(root);
    let rung_arg = match option_value(&a, "--rung") {
        Ok(value) => value,
        Err(error) => {
            eprintln!("npa-gold-ladder: {error}");
            return ExitCode::from(2);
        }
    };
    let rung = match rung_arg {
        None => None,
        Some(value) => match value.as_str() {
            "100" => Some(100),
            "400" => Some(400),
            "800" => Some(800),
            "c2" | "c3" => {
                eprintln!("npa-gold-ladder: frozen {value} cannot be regenerated");
                return ExitCode::from(2);
            }
            _ => {
                eprintln!("npa-gold-ladder: --rung expects 100, 400, 800, c2, or c3");
                return ExitCode::from(2);
            }
        },
    };
    let check = a.iter().any(|x| x == "--check");
    let perf = a.iter().any(|x| x == "--perf");
    let garant_root = match option_value(&a, "--garant-root") {
        Ok(Some(value)) => PathBuf::from(value),
        Ok(None) => PathBuf::from("law-source/garant"),
        Err(error) => {
            eprintln!("npa-gold-ladder: {error}");
            return ExitCode::from(2);
        }
    };
    let garant_root = garant_root.canonicalize().unwrap_or(garant_root);
    // Durable receipts are a single three-rung artifact. A check requested
    // for one rung must still validate the complete receipt set.
    let files = match outputs(
        &root,
        &garant_root,
        &dir,
        if check { None } else { rung },
        seed,
        perf,
        check,
    ) {
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
