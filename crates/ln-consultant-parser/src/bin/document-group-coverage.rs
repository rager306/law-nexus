//! Thin argv/output shell for the M224/S04 corpus `document_groups` coverage
//! run (`document_group_coverage` owns behavior; this file only wires argv and
//! stdio).
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!("document-group-coverage --manifest <path> --out <path> [--check]");
        return ExitCode::SUCCESS;
    }
    let cli =
        match ln_consultant_parser::document_group_coverage::parse_document_group_coverage_args(
            args,
        ) {
            Ok(cli) => cli,
            Err(error) => {
                eprintln!("document-group-coverage: {error}");
                return ExitCode::from(ln_consultant_parser::document_group_coverage::EXIT_USAGE);
            }
        };
    let (code, message) =
        ln_consultant_parser::document_group_coverage::run_document_group_coverage(&cli);
    if !message.is_empty() {
        eprintln!("document-group-coverage: {message}");
    }
    ExitCode::from(code)
}
