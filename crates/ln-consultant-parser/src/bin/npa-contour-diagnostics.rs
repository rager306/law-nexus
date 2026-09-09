//! Thin argv/output shell for the C4 contour diagnostics profile.
use std::{io::Write as _, process::ExitCode};

use ln_consultant_parser::contour_diagnostics;
use ln_decode::npa_sweep;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "-h" || a == "--help") {
        println!("npa-contour-diagnostics [--root <dir>] [--out <path>] [--limit <n>] [--profile decode|contour] [--check] [--label <label>] [--jobs <n>]");
        return ExitCode::SUCCESS;
    }
    let cli = match contour_diagnostics::parse_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("npa-contour-diagnostics: {error}");
            return ExitCode::from(contour_diagnostics::EXIT_USAGE);
        }
    };
    let (code, output, message) = contour_diagnostics::run(&cli, &npa_sweep::default_sweep_root());
    if !message.is_empty() {
        eprintln!("npa-contour-diagnostics: {message}");
    }
    if let Some(output) = output {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(output.as_bytes());
    }
    ExitCode::from(code)
}
