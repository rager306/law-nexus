//! Thin CLI over the closed hierarchy candidate artifact boundary
//! (M202-9qf3ta S02).
//!
//! Writes (`--write --out <path>`), checks (`--check --out <expected>`) or
//! prints (no mode flags) the `law-nexus-hierarchy-candidate-artifact/v1`
//! document for an explicit `--source` XML file. No implicit corpus walk, no
//! registry YAML access, no admission (D185 / D417 / D418). stderr carries
//! the count-only heartbeat (`extracted=N unique=N drift=0`) or a typed
//! `drift=<class>` / `error=<class>` line with the pinned exit code.

use std::process::ExitCode;

use ln_decode::hierarchy_artifact::{
    parse_artifact_args, run_hierarchy_candidate_artifact, ArtifactError,
};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cli = match parse_artifact_args(args) {
        Ok(cli) => cli,
        Err(error) => return fail(&error),
    };
    match run_hierarchy_candidate_artifact(&cli) {
        Ok(outcome) => {
            eprintln!("{}", outcome.heartbeat);
            if let Some(artifact) = outcome.stdout {
                print!("{artifact}");
            }
            ExitCode::SUCCESS
        }
        Err(error) => fail(&error),
    }
}

fn fail(error: &ArtifactError) -> ExitCode {
    eprintln!("{}", error.cli_line());
    ExitCode::from(u8::try_from(error.exit_code()).unwrap_or(1))
}
