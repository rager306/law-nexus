//! Thin CLI shell for the S04 corpus acceptance run (M214-es3jvw S04/T03).
//!
//! All pipeline, limit, resource and tamper-probe logic lives in
//! `ln_consultant_parser::npa_corpus_acceptance`; this binary only parses
//! argv, loads the pinned manifest, computes the manifest file hash, calls
//! `run_acceptance_with` and writes the separated report, the text-free
//! adjudication packet and the per-entry JSONL. It never reads corpus bytes
//! itself and never fabricates an outcome.
//!
//! Exit codes: `0` success, `2` usage error, `1` runtime refusal (absent
//! declared root, unreadable sample, non-canonical manifest hash, report
//! validation failure).

use std::path::PathBuf;
use std::process::ExitCode;

use ln_consultant_parser::artifact_output::{
    output_identity, preflight_publish_target, publish_text_artifact,
};
use ln_consultant_parser::npa_corpus_acceptance::{
    AcceptanceOptions, CONSULTANT_ROOT_RELATIVE, CorpusSampleManifest, GARANT_ROOT_RELATIVE,
    declared_sample_roots, run_acceptance_with,
};
use sha2::{Digest, Sha256};

const DEFAULT_SAMPLE: &str = "prd/migration/rust-evidence/m214-s04-corpus-sample.json";
const DEFAULT_OUT: &str = "prd/migration/rust-evidence/m214-s04-corpus-acceptance.json";
const DEFAULT_PACKET: &str = "prd/migration/rust-evidence/m214-s04-adjudication-packet.json";
const DEFAULT_ENTRIES: &str = "prd/migration/rust-evidence/m214-s04-corpus-acceptance.jsonl";

fn usage() -> String {
    let mut out = String::new();
    out.push_str(
        "npa-corpus-acceptance: run the pinned S04 sample through the S01-S03 pipeline\n\n",
    );
    out.push_str("USAGE:\n");
    out.push_str("  npa-corpus-acceptance [--sample <file>] [--consultant-root <dir>]\n");
    out.push_str(
        "                        [--garant-root <dir>] [--out <file>] [--packet <file>]\n",
    );
    out.push_str("                        [--entries <file>] [--force]\n\n");
    out.push_str(&format!(
        "The declared roots stay {CONSULTANT_ROOT_RELATIVE} and {GARANT_ROOT_RELATIVE};\n"
    ));
    out.push_str("the disk overrides exist only for synthetic runs.\n\n");
    out.push_str("OPTIONS:\n");
    out.push_str(&format!(
        "  --sample <file>          pinned sample manifest (default {DEFAULT_SAMPLE})\n"
    ));
    out.push_str(&format!(
        "  --consultant-root <dir>  walk this directory (default {CONSULTANT_ROOT_RELATIVE})\n"
    ));
    out.push_str(&format!(
        "  --garant-root <dir>      walk this directory (default {GARANT_ROOT_RELATIVE})\n"
    ));
    out.push_str(&format!(
        "  --out <file>             report path (default {DEFAULT_OUT})\n"
    ));
    out.push_str(&format!(
        "  --packet <file>          adjudication packet path (default {DEFAULT_PACKET})\n"
    ));
    out.push_str(&format!(
        "  --entries <file>         per-entry JSONL path (default {DEFAULT_ENTRIES})\n"
    ));
    out.push_str(
        "  --force                  replace an existing regular output file (default: refuse)\n",
    );
    out.push_str("  -h, --help               print this help\n\n");
    out.push_str("Exit codes: 0 ok, 1 refusal, 2 usage.");
    out
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

fn path_option(args: &[String], flag: &str, default: &str) -> Result<PathBuf, String> {
    Ok(option_value(args, flag)?.map_or_else(|| PathBuf::from(default), PathBuf::from))
}

fn has_flag(args: &[String], flag: &str) -> bool {
    args.iter().any(|arg| arg == flag)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

/// Refuse any output path that resolves onto the sample or onto a sibling
/// output, then preflight each output before the (expensive) pipeline runs.
fn check_output_paths(
    sample_path: &std::path::Path,
    outputs: [(&str, &PathBuf); 3],
    force: bool,
) -> Result<(), String> {
    let sample_identity = output_identity(sample_path).map_err(|error| error.to_string())?;
    let mut seen: Vec<(&str, PathBuf)> = Vec::with_capacity(outputs.len());
    for (label, path) in outputs {
        let identity = output_identity(path).map_err(|error| error.to_string())?;
        if identity == sample_identity {
            return Err(format!(
                "refusing {label} {}: resolves to the sample manifest {}; pass a distinct output path",
                path.display(),
                sample_path.display()
            ));
        }
        if let Some((other, _)) = seen
            .iter()
            .find(|(_, seen_identity)| seen_identity == &identity)
        {
            return Err(format!(
                "refusing {label} {}: collides with {other} at {}; pass distinct output paths",
                path.display(),
                identity.display()
            ));
        }
        seen.push((label, identity));
    }
    for (label, path) in outputs {
        preflight_publish_target(path, force)
            .map_err(|error| format!("{label} {}: {error}", path.display()))?;
    }
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{}", usage());
        return ExitCode::SUCCESS;
    }
    let sample_path = match path_option(&args, "--sample", DEFAULT_SAMPLE) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let consultant = match path_option(&args, "--consultant-root", CONSULTANT_ROOT_RELATIVE) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let garant = match path_option(&args, "--garant-root", GARANT_ROOT_RELATIVE) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let out = match path_option(&args, "--out", DEFAULT_OUT) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let packet_path = match path_option(&args, "--packet", DEFAULT_PACKET) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let entries_path = match path_option(&args, "--entries", DEFAULT_ENTRIES) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(2);
        }
    };
    let force = has_flag(&args, "--force");
    let outputs: [(&str, &PathBuf); 3] = [
        ("--out", &out),
        ("--packet", &packet_path),
        ("--entries", &entries_path),
    ];
    if let Err(error) = check_output_paths(&sample_path, outputs, force) {
        eprintln!("npa-corpus-acceptance: {error}");
        return ExitCode::from(1);
    }

    let sample_text = match std::fs::read(&sample_path) {
        Ok(bytes) => bytes,
        Err(error) => {
            eprintln!(
                "npa-corpus-acceptance: read sample {}: {error}",
                sample_path.display()
            );
            return ExitCode::from(1);
        }
    };
    let sample_manifest_sha256 = format!("sha256:{}", sha256_hex(&sample_text));
    let sample =
        match CorpusSampleManifest::load(std::str::from_utf8(&sample_text).unwrap_or_default()) {
            Ok(sample) => sample,
            Err(error) => {
                eprintln!("npa-corpus-acceptance: sample manifest: {error}");
                return ExitCode::from(1);
            }
        };
    let roots = match declared_sample_roots(consultant, garant) {
        Ok(roots) => roots,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(1);
        }
    };
    let run = match run_acceptance_with(
        &sample,
        &sample_manifest_sha256,
        &roots,
        &AcceptanceOptions::default(),
    ) {
        Ok(run) => run,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: {error}");
            return ExitCode::from(1);
        }
    };
    let report_text = match run.report.to_json_string() {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: render report: {error}");
            return ExitCode::from(1);
        }
    };
    let packet_text = match run.packet.to_json_string() {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: render packet: {error}");
            return ExitCode::from(1);
        }
    };
    let entries_text = match run.entries_jsonl() {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-acceptance: render entries: {error}");
            return ExitCode::from(1);
        }
    };
    for (label, path, text) in [
        ("--out", out.as_path(), report_text.as_str()),
        ("--packet", packet_path.as_path(), packet_text.as_str()),
        ("--entries", entries_path.as_path(), entries_text.as_str()),
    ] {
        if let Err(error) = publish_text_artifact(path, text, force) {
            eprintln!("npa-corpus-acceptance: {label} {}: {error}", path.display());
            return ExitCode::from(1);
        }
    }
    let structural = &run.report.structural_integrity;
    println!(
        "npa-corpus-acceptance: verdict={} entries={} verified_ok={} structural_failures={} limit_events={} tamper={}/{} report={}",
        run.report.verdict.as_str(),
        structural.entries_total,
        structural.verified_ok,
        structural.structural_failures,
        run.report.limits.limit_events_total,
        structural.tamper_probe_detected,
        structural.tamper_probe_entries,
        out.display(),
    );
    ExitCode::SUCCESS
}
