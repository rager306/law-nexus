//! Thin CLI shell for the pinned S04 corpus sample (M214-es3jvw S04/T02).
//!
//! All sampling, hashing and schema logic lives in
//! `ln_consultant_parser::npa_corpus_acceptance`; this binary only parses
//! argv, prints help, calls `build_sample` and writes the manifest. It never
//! reads corpus bytes itself and never fabricates an entry.
//!
//! Exit codes: `0` success, `2` usage error, `1` runtime refusal (absent
//! declared root, inventory smaller than the declared sample size, non-ASCII
//! path, etc.).

use std::path::PathBuf;
use std::process::ExitCode;

use ln_consultant_parser::artifact_output::{
    output_identity, preflight_publish_target, publish_text_artifact,
};
use ln_consultant_parser::npa_corpus_acceptance::{
    CONSULTANT_ROOT_RELATIVE, GARANT_ROOT_RELATIVE, build_sample, declared_sample_roots,
};

const DEFAULT_OUT: &str = "prd/migration/rust-evidence/m214-s04-corpus-sample.json";

fn usage() -> String {
    format!(
        "npa-corpus-sample: write the pinned S04 provider/work-family stratified sample\n\
         \n\
         USAGE:\n  npa-corpus-sample [--consultant-root <dir>] [--garant-root <dir>] [--out <file>] [--force]\n\
         \n\
         The declared roots stay {CONSULTANT_ROOT_RELATIVE} and {GARANT_ROOT_RELATIVE};\n\
         the disk overrides exist only for synthetic runs.\n\
         \n\
         OPTIONS:\n\
           --consultant-root <dir>  walk this directory (default {CONSULTANT_ROOT_RELATIVE})\n\
           --garant-root <dir>      walk this directory (default {GARANT_ROOT_RELATIVE})\n\
           --out <file>             manifest path (default {DEFAULT_OUT})\n\
           --force                  replace an existing regular manifest (default: refuse)\n\
           -h, --help               print this help\n\
         \n\
         Exit codes: 0 ok, 1 refusal, 2 usage."
    )
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

fn has_flag(args: &[String], flag: &str) -> bool {
    args.iter().any(|arg| arg == flag)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{}", usage());
        return ExitCode::SUCCESS;
    }
    let consultant = match option_value(&args, "--consultant-root") {
        Ok(value) => value.map_or_else(|| PathBuf::from(CONSULTANT_ROOT_RELATIVE), PathBuf::from),
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(2);
        }
    };
    let garant = match option_value(&args, "--garant-root") {
        Ok(value) => value.map_or_else(|| PathBuf::from(GARANT_ROOT_RELATIVE), PathBuf::from),
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(2);
        }
    };
    let out = match option_value(&args, "--out") {
        Ok(value) => value.map_or_else(|| PathBuf::from(DEFAULT_OUT), PathBuf::from),
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(2);
        }
    };
    let roots = match declared_sample_roots(consultant, garant) {
        Ok(roots) => roots,
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(2);
        }
    };
    let force = has_flag(&args, "--force");

    // Fail-closed output safety before the (expensive) corpus walk: the
    // manifest must not resolve onto a declared root, and the target must be
    // publishable under the caller's replacement policy.
    let out_identity = match output_identity(&out) {
        Ok(identity) => identity,
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(1);
        }
    };
    for root in &roots {
        let root_identity = match output_identity(&root.path) {
            Ok(identity) => identity,
            Err(error) => {
                eprintln!("npa-corpus-sample: {error}");
                return ExitCode::from(1);
            }
        };
        if root_identity == out_identity {
            eprintln!(
                "npa-corpus-sample: refusing --out {}: resolves to declared root {}; pass a distinct manifest path",
                out.display(),
                root.relative_path
            );
            return ExitCode::from(1);
        }
    }
    if let Err(error) = preflight_publish_target(&out, force) {
        eprintln!("npa-corpus-sample: --out {}: {error}", out.display());
        return ExitCode::from(1);
    }

    let manifest = match build_sample(&roots) {
        Ok(manifest) => manifest,
        Err(error) => {
            eprintln!("npa-corpus-sample: {error}");
            return ExitCode::from(1);
        }
    };
    let text = match manifest.to_json_string() {
        Ok(text) => text,
        Err(error) => {
            eprintln!("npa-corpus-sample: render: {error}");
            return ExitCode::from(1);
        }
    };
    if let Err(error) = publish_text_artifact(&out, &text, force) {
        eprintln!("npa-corpus-sample: --out {}: {error}", out.display());
        return ExitCode::from(1);
    }
    println!(
        "npa-corpus-sample: wrote {} pinned entries (snapshot {}) to {}",
        manifest.entries.len(),
        manifest.corpus_snapshot_sha256,
        out.display()
    );
    ExitCode::SUCCESS
}
