//! Thin argv/output shell for `npa-integration-runner` (M211 S04 T05).
//!
//! All logic lives in `ln_decode::npa_report`; this binary only parses argv,
//! prints usage, writes the canonical report to stdout or `--out`, and maps
//! the library exit code to the process exit code.

use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_report;
use ln_decode::npa_sweep;

const USAGE: &str = "npa-integration-runner — end-to-end NPA classification report (npa-integration-report/v1)\n\nUSAGE:\n    npa-integration-runner [--root <dir>] [--out <path>] [--limit <n>] [--label <label>]\n\nEXIT CODES:\n    0 complete, or explicit skip when the default corpus root is absent\n    2 usage error\n    3 --out failure\n    4 explicit --root missing\n    5 fixture source missing or walk failure\n\nThe report is [proposed]/derived, differential against the tracked Python\nreference, and carries no completeness claim from counts or hashes (INV-22).\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match npa_report::parse_integration_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-integration-runner: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_report::EXIT_USAGE);
        }
    };
    let run = npa_report::run_integration_report(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-integration-runner: {}", run.stderr);
    }
    if let (Some(json), true) = (&run.json, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(json.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
