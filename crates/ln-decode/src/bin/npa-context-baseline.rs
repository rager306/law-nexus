//! Thin argv/output shell for `npa-context-baseline`.

use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_context_baseline;
use ln_decode::npa_sweep;

const USAGE: &str = "npa-context-baseline — bounded count-only document-context baseline\n\nUSAGE:\n    npa-context-baseline [--root <dir>] [--out <path>] [--limit <n>] [--label <label>] [--progress <n>]\n\nEXIT CODES:\n    0 complete or absent default-root skip\n    2 usage error\n    3 --out failure\n    4 explicit root missing\n    5 walk failure\n\nThe report is [diagnostic]/[proposed] and contains no payload text.\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let mut cli = match npa_context_baseline::parse_context_baseline_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-context-baseline: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_context_baseline::EXIT_USAGE);
        }
    };
    cli.progress_stderr = true;
    let run = npa_context_baseline::run_context_baseline(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-context-baseline: {}", run.stderr);
    }
    if let (Some(jsonl), true) = (&run.jsonl, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(jsonl.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}
