//! Thin `cleaned-project` binary: argv parsing and output wiring only.
//! Every behavior — argument parsing, the three commands, atomic publication,
//! counts-only summaries and the exit-code contract — lives in
//! `ln_decode::cleaned_cli`, so contract tests exercise library functions
//! instead of shelling out. Stderr carries closed codes and counts only: raw
//! decoded text never reaches a diagnostic. Stdlib only.

use std::process::ExitCode;

use ln_decode::cleaned_cli::{parse_cleaned_args, run_cleaned, USAGE};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let cli = match parse_cleaned_args(args) {
        Ok(cli) => cli,
        Err(code) => {
            eprintln!("cleaned-project: usage error");
            eprint!("{USAGE}");
            return ExitCode::from(code);
        }
    };
    ExitCode::from(run_cleaned(&cli))
}
