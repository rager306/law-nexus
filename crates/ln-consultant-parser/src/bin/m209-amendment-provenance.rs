//! Thin CLI over the M209/S03 amendment-provenance evidence boundary (D554).
//!
//! Modes arrive one per S03 task; T01 ships `families`, which re-derives the
//! count-only family denominator for the named `cc:44-fz` chain from the live,
//! untracked provider export and either writes it (`--write`) or byte-compares
//! it against the tracked artifact without writing (`--check`, D424).
//!
//! stderr carries a count-only heartbeat (`families=N manifests=N chains=1
//! editions=N drift=0`) or a typed `drift=<code>` / `error=<class>` line with
//! the pinned exit code: usage or path drift 2, input absent 3, output
//! unwritable 4, schema, hash or ascii drift 6. No XML bytes, no article text
//! and no raw relation tooltips are ever read into an artifact.

use std::path::PathBuf;
use std::process::ExitCode;

use ln_consultant_parser::amendment_provenance::{
    parse_provenance_args, run_provenance, AmendmentProvenanceError,
};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cli = match parse_provenance_args(args) {
        Ok(cli) => cli,
        Err(error) => return fail(&error),
    };
    let root = repo_root();
    match run_provenance(&cli, &root) {
        Ok(outcome) => {
            eprintln!("{}", outcome.heartbeat);
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

/// Repository root, resolved from the compile-time crate manifest directory so
/// the binary works from any working directory (subprocess or interactive).
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn fail(error: &AmendmentProvenanceError) -> ExitCode {
    eprintln!("{}", error.cli_line());
    ExitCode::from(u8::try_from(error.exit_code()).unwrap_or(1))
}
