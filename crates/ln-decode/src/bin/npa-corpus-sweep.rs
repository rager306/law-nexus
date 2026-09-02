//! Thin `npa-corpus-sweep` binary: argv parsing and output wiring only
//! (M198-das7v8 S01 T02). Every behavior — root resolution with
//! empty-as-unset env semantics, the deterministic XML walk, per-file
//! decode+ingest, the closed-schema aggregate render, and the exit-code
//! contract — lives in `ln_decode::npa_sweep`, so contract tests exercise
//! library functions instead of shelling out. Stderr carries counts only;
//! payload bytes and block text never reach stdout/stderr (Q3). Stdlib
//! only: no clap, no walkdir, no serde.

use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_sweep;

const USAGE: &str = "\
npa-corpus-sweep — read-only C1 sweep over the Consultant XML export

USAGE:
    npa-corpus-sweep [--root <dir>] [--out <path>] [--limit <n>] [--cycle <label>]

FLAGS:
    --root <dir>     Sweep root: an existing tree of *.xml files. Default is
                     the resolved Consultant export
                     (<CONSULTANT_EXPORT_DIR>/consru_export/exports, empty
                     env value counts as unset); an absent default root is
                     skip-mode: exit 0 with a zeroed aggregate.
    --out <path>     Write the JSONL aggregate to <path> instead of stdout.
    --limit <n>      Process at most <n> XML files after the deterministic
                     sort; 0 is a valid empty walk.
    --cycle <label>  Cycle label for the header record (default: C1).
    -h, --help       Print this usage and exit 0.

EXIT CODES:
    0  walk completed (per-file decode failures are counted, not fatal)
    2  usage error
    3  --out could not be opened for writing
    4  explicit --root does not exist or is not a directory
    5  filesystem walk failure
";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match npa_sweep::parse_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-corpus-sweep: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_sweep::EXIT_USAGE);
        }
    };
    let run = npa_sweep::run_sweep(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-corpus-sweep: {}", run.stderr);
    }
    if let (Some(jsonl), true) = (&run.jsonl, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(jsonl.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
