//! Thin `corpus-inventory` binary: argv parsing and output wiring only
//! (M223-d2q075 S02/T01). Every behavior — root resolution, the deterministic
//! XML walk, per-file streaming sha256, the closed-schema JSONL manifest, pin
//! drift reporting, and the exit-code contract — lives in
//! `ln_decode::corpus_inventory`, so contract tests exercise library functions
//! instead of shelling out. Stderr carries counts/pins/hashes only; raw
//! decoded text never reaches stdout/stderr (Q3). Stdlib only: no clap, no
//! walkdir, no serde.

use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::corpus_inventory;
use ln_decode::npa_sweep;

const USAGE: &str = "\
corpus-inventory — authoritative per-file hash manifest of the pinned Consultant XML corpus

USAGE:
    corpus-inventory [--root <dir>] [--out <path>] [--limit <n>]

FLAGS:
    --root <dir>   Inventory root: an existing tree of *.xml files. Default is
                   the resolved Consultant export
                   (<CONSULTANT_EXPORT_DIR>/consru_export/exports, empty env
                   value counts as unset). An absent root is fail-closed:
                   no zeroed manifest is published.
    --out <path>   Write the JSONL manifest to <path> instead of stdout.
    --limit <n>    Process at most <n> XML files after the deterministic sort;
                   0 is a valid empty walk (and a pin drift by construction).
    -h, --help     Print this usage and exit 0.

EXIT CODES:
    0  manifest completed; §8.3 pin match/drift is recorded in the header
    2  usage error
    3  --out could not be opened for writing
    4  root does not exist or is not a directory
    5  filesystem walk failure
    6  a discovered XML file could not be read (fail-closed: no manifest)

The manifest is integrity evidence only: source.sha256 and the seals are
recomputable by any party controlling the bytes, and this is not a corpus
acceptance or semantic verdict.
";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match corpus_inventory::parse_inventory_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("corpus-inventory: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(corpus_inventory::EXIT_USAGE);
        }
    };
    let run = corpus_inventory::run_inventory(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("corpus-inventory: {}", run.stderr);
    }
    if let (Some(jsonl), true) = (&run.jsonl, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(jsonl.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
