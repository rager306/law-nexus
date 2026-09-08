//! Thin argv/output shell for the count-only npa-frames-baseline diagnostic.
use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_frames_baseline;
use ln_decode::npa_sweep;

const USAGE: &str = "npa-frames-baseline [--root <dir>] [--out <path>] [--limit <n>] [--label <label>] [--progress <n>]\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match npa_frames_baseline::parse_frames_baseline_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-frames-baseline: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_frames_baseline::EXIT_USAGE);
        }
    };
    let run = npa_frames_baseline::run_frames_baseline(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-frames-baseline: {}", run.stderr);
    }
    if let (Some(jsonl), true) = (&run.jsonl, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(jsonl.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
