//! Thin argv/output shell for the m207-hybrid-records/v1 Rust emitter.
//!
//! All behavior lives in `ln_decode::npa_wire` so contract tests exercise
//! the library instead of shelling out; this binary is argv + printing only.
use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_sweep;
use ln_decode::npa_wire;

const USAGE: &str = "npa-hybrid-records [--root <dir>] [--out <path>] [--limit <n>]\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match npa_wire::parse_records_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-hybrid-records: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_wire::RECORDS_EXIT_USAGE);
        }
    };
    let run = npa_wire::run_records(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-hybrid-records: {}", run.stderr);
    }
    if let (Some(json), true) = (&run.json, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(json.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
