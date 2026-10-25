//! Thin argv/output shell for the M224/S06 corpus edition-timeline assembly
//! consumer. Behavior lives in
//! [`ln_consultant_parser::edition_timeline`]; this file only wires argv and
//! stdio. It reads the materialized cleaned-wire JSONL layer and never the
//! source XML/ODT artifact.
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!(
            "edition-timeline --editions <tsv> [--mode assembly|chain|timeline] [--ctv] [--out <path>]"
        );
        return ExitCode::SUCCESS;
    }
    let cli = match ln_consultant_parser::edition_timeline::parse_edition_timeline_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("edition-timeline: {error}");
            return ExitCode::from(ln_consultant_parser::edition_timeline::EXIT_USAGE);
        }
    };
    let (code, message) = ln_consultant_parser::edition_timeline::run_edition_timeline(&cli);
    if code == ln_consultant_parser::edition_timeline::EXIT_OK && cli.out.is_none() {
        // No `--out`: the payload is the output.
        println!("{message}");
    } else if !message.is_empty() {
        eprintln!("edition-timeline: {message}");
    }
    ExitCode::from(code)
}
