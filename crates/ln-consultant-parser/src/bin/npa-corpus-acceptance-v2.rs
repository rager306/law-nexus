//! Thin CLI shell for the M221-wbslul S04 bounded split-acceptance run (T05).
//!
//! All pipeline, coverage and completion logic lives in
//! `ln_consultant_parser::npa_corpus_acceptance` (bounded surface) and
//! `ln_consultant_parser::npa_corpus_acceptance_v2` (the split report). This
//! binary only parses argv, walks the declared roots bounded (no frozen v1
//! sample-size pin; D677), threads the runner's tamper-probe counts into the v2
//! report, and publishes the count/hash-only `.../v2` report plus its per-entry
//! JSONL companion. It never reads corpus bytes itself and never fabricates an
//! outcome.
//!
//! Exit codes: `0` success, `2` usage error, `1` runtime refusal (absent
//! declared root, empty inventory, non-canonical report, refused output path).

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use ln_consultant_parser::artifact_output::{
    output_identity, preflight_publish_target, publish_text_artifact,
};
use ln_consultant_parser::npa_corpus_acceptance::{
    build_bounded_inventory, declared_sample_roots, run_acceptance_entries, AcceptanceOptions,
    SampleRoot, CONSULTANT_ROOT_RELATIVE, GARANT_ROOT_RELATIVE,
};
use ln_consultant_parser::npa_corpus_acceptance_v2::{
    build_report_v2, entries_jsonl, V2Thresholds,
};

const DEFAULT_OUT: &str = "prd/migration/rust-evidence/m221-s04-acceptance.json";
const DEFAULT_ENTRIES: &str = "prd/migration/rust-evidence/m221-s04-acceptance.jsonl";

fn usage() -> String {
    let mut out = String::new();
    out.push_str("npa-corpus-acceptance-v2: bounded split-acceptance run (M221-wbslul S04)\n\n");
    out.push_str("USAGE:\n");
    out.push_str("  npa-corpus-acceptance-v2 [--consultant-root <dir>] [--garant-root <dir>]\n");
    out.push_str("                           [--out <file>] [--entries <file>] [--force]\n\n");
    out.push_str(&format!(
        "The declared roots stay {CONSULTANT_ROOT_RELATIVE} and {GARANT_ROOT_RELATIVE};\n"
    ));
    out.push_str("the disk overrides exist only for bounded/synthetic runs. No v1\n");
    out.push_str("sample-size pin is applied and no aggregate verdict is produced.\n\n");
    out.push_str("OPTIONS:\n");
    out.push_str(&format!(
        "  --consultant-root <dir>  walk this directory (default {CONSULTANT_ROOT_RELATIVE})\n"
    ));
    out.push_str(&format!(
        "  --garant-root <dir>      walk this directory (default {GARANT_ROOT_RELATIVE})\n"
    ));
    out.push_str(&format!(
        "  --out <file>             v2 report path (default {DEFAULT_OUT})\n"
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

/// Absolute lexical form of a path (without resolving symlinks).
fn absolute(path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()
            .map(|cwd| cwd.join(path))
            .unwrap_or_else(|_| path.to_path_buf())
    }
}

/// Canonical directory when it exists, else the absolute lexical path. The
/// declared root is not created here; `build_bounded_inventory` owns the
/// fail-closed absent-root refusal.
fn resolve_dir(path: &Path) -> PathBuf {
    std::fs::canonicalize(path).unwrap_or_else(|_| absolute(path))
}

/// Refuse any output path that resolves onto a sibling output or inside a
/// declared source root, then preflight each output before the (expensive)
/// pipeline runs. A symlinked or existing target is refused by
/// `preflight_publish_target` unless `--force` is set.
fn check_output_paths(
    out: &Path,
    entries: &Path,
    roots: &[SampleRoot],
    force: bool,
) -> Result<(), String> {
    let out_identity = output_identity(out).map_err(|error| error.to_string())?;
    let entries_identity = output_identity(entries).map_err(|error| error.to_string())?;
    if out_identity == entries_identity {
        return Err(format!(
            "refusing --entries {}: collides with --out at {}; pass distinct output paths",
            entries.display(),
            out_identity.display()
        ));
    }
    for root in roots {
        let dir = resolve_dir(&root.path);
        if out_identity.starts_with(&dir) {
            return Err(format!(
                "refusing --out {}: resolves inside declared root {}; pass a distinct output path",
                out.display(),
                root.relative_path
            ));
        }
        if entries_identity.starts_with(&dir) {
            return Err(format!(
                "refusing --entries {}: resolves inside declared root {}; pass a distinct output path",
                entries.display(),
                root.relative_path
            ));
        }
    }
    for (label, path) in [("--out", out), ("--entries", entries)] {
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
    let consultant = match path_option(&args, "--consultant-root", CONSULTANT_ROOT_RELATIVE) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(2);
        }
    };
    let garant = match path_option(&args, "--garant-root", GARANT_ROOT_RELATIVE) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(2);
        }
    };
    let out = match path_option(&args, "--out", DEFAULT_OUT) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(2);
        }
    };
    let entries_path = match path_option(&args, "--entries", DEFAULT_ENTRIES) {
        Ok(path) => path,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(2);
        }
    };
    let force = has_flag(&args, "--force");

    let roots = match declared_sample_roots(consultant, garant) {
        Ok(roots) => roots,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(1);
        }
    };
    if let Err(error) = check_output_paths(&out, &entries_path, &roots, force) {
        eprintln!("npa-corpus-acceptance-v2: {error}");
        return ExitCode::from(1);
    }

    let inventory = match build_bounded_inventory(&roots) {
        Ok(inventory) => inventory,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(1);
        }
    };
    let run =
        match run_acceptance_entries(&inventory.entries, &roots, &AcceptanceOptions::default()) {
            Ok(run) => run,
            Err(error) => {
                eprintln!("npa-corpus-acceptance-v2: {error}");
                return ExitCode::from(1);
            }
        };
    let report = match build_report_v2(
        &run.entries,
        &inventory.declared_roots,
        &inventory.provider_candidate_counts,
        run.tamper_probe_counts(),
        &V2Thresholds::declared(),
    ) {
        Ok(report) => report,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: {error}");
            return ExitCode::from(1);
        }
    };
    let report_text = match report.to_json_string() {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: render report: {error}");
            return ExitCode::from(1);
        }
    };
    let entries_text = match entries_jsonl(&run.entries) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-acceptance-v2: render entries: {error}");
            return ExitCode::from(1);
        }
    };
    for (label, path, text) in [
        ("--out", out.as_path(), report_text.as_str()),
        ("--entries", entries_path.as_path(), entries_text.as_str()),
    ] {
        if let Err(error) = publish_text_artifact(path, text, force) {
            eprintln!(
                "npa-corpus-acceptance-v2: {label} {}: {error}",
                path.display()
            );
            return ExitCode::from(1);
        }
    }
    println!(
        "npa-corpus-acceptance-v2: transport={} completion={} semantic={} entries={} verified_ok={} uncovered={} report={}",
        report.verdicts.transport_integrity.as_str(),
        report.verdicts.analysis_completion.as_str(),
        report.verdicts.semantic_acceptance.as_str(),
        report.structural_integrity.entries_total,
        report.structural_integrity.verified_ok,
        report.provider_coverage.uncovered.len(),
        out.display(),
    );
    ExitCode::SUCCESS
}
