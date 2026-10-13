//! Thin argv/output shell for the M224/S03 corpus pageindex run
//! (`corpus_pageindex` owns behavior; this file only wires argv and stdio).
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!(
            "corpus-pageindex --envelope <path> --catalog <path> --coverage-out <path> --index-out <path> [--check]"
        );
        return ExitCode::SUCCESS;
    }
    let cli = match ln_consultant_parser::corpus_pageindex::parse_pageindex_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("corpus-pageindex: {error}");
            return ExitCode::from(ln_consultant_parser::corpus_pageindex::EXIT_USAGE);
        }
    };
    let (code, message) = ln_consultant_parser::corpus_pageindex::run_pageindex(&cli);
    if !message.is_empty() {
        eprintln!("corpus-pageindex: {message}");
    }
    ExitCode::from(code)
}
