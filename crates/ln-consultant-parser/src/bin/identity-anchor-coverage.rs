//! Thin argv/output shell for the M224/S02 corpus identity-anchor coverage
//! run (`anchor_coverage` owns behavior; this file only wires argv and stdio).
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!(
            "identity-anchor-coverage --manifest <path> --catalog <path> --coverage-out <path> --envelope-out <path> [--check]"
        );
        return ExitCode::SUCCESS;
    }
    let cli = match ln_consultant_parser::anchor_coverage::parse_coverage_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("identity-anchor-coverage: {error}");
            return ExitCode::from(ln_consultant_parser::anchor_coverage::EXIT_USAGE);
        }
    };
    let (code, message) = ln_consultant_parser::anchor_coverage::run_coverage(&cli);
    if !message.is_empty() {
        eprintln!("identity-anchor-coverage: {message}");
    }
    ExitCode::from(code)
}
