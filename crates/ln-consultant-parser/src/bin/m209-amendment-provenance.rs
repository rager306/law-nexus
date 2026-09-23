//! Thin CLI over the M209/S03 amendment-provenance evidence boundary (D554).
//!
//! Modes arrive one per S03 task. T01 ships `families`, which re-derives the
//! count-only family denominator for the named `cc:44-fz` chain from the live,
//! untracked provider export. T02 adds `amends-provisions`, which re-derives the
//! amending-act and affected-provision leg: the explicit `amends` edges of the
//! catalog relation run rooted at `cp:LAW:508812`, joined to the layer1 manifest
//! and to the act exports under `exports/npa`, with statya level candidate
//! provision targets resolved against the chain needle of the frozen hierarchy
//! registry. T03 adds `commencement`, which re-derives the commencement and
//! transitional leg: one slot per layer1 record of the T02 amending-act
//! denominator, carrying a closed-vocabulary evidence class, slot verdict,
//! reason code and transitional value, and failing closed on any Legislative
//! upgrade attempt, any minted M208 vocabulary and any date or file name read as
//! a commencement source. T04 adds `edition-chain`, which walks the one
//! multi-edition chain of the corpus with the unmodified admitted `multi_edition`
//! runtime, reconciles the declared edition inventory against the live directory
//! listing and the frozen T01 declaration, and declares the consecutive
//! link-topology delta windows plus a per-edition and chain determinism digest.
//! T05 adds `ledger`, which aggregates the four tracked S03 leg artifacts and
//! the frozen M201 R070 proof gate into the scoped coverage ledger S04 accepts
//! or holds scope by scope, promoting no leg and mutating no requirement. Every
//! mode either writes the artifact (`--write`) or byte-compares it against the
//! tracked file without writing (`--check`, D424).
//!
//! stderr carries a count-only heartbeat (`families=N manifests=N chains=1
//! editions=N drift=0`, `amends=N resolved=N unresolved=N layer1=N rows=N
//! drift=0`, `commencement=N named=N amending=N filled=N absent=N
//! class_matched=N drift=0`, `edition-chain=N processed=N unreadable=N
//! unparsed=N windows=N drift=0`, or `ledger=4 bounded=N
//! slot-filled-not-proven=N gates-promoted=0 drift=0`) or a typed
//! `drift=<code>` / `error=<class>` line
//! with the pinned exit code: usage or path drift 2, input absent 3, output
//! unwritable 4, schema, hash or ascii drift 6. No XML bytes, no article text and
//! no raw relation tooltips are ever read into an artifact.

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
