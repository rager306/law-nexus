//! Thin argv/output shell for the M224/S05 per-document hierarchy-lift census
//! consumer. Behavior lives in
//! [`ln_consultant_parser::hierarchy_lift_census`]; this file only wires argv
//! and stdio. It reads the materialized cleaned-wire JSONL layer and never the
//! source XML/ODT artifact.
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!(
            "hierarchy-lift-census --cleaned-wire <jsonl> --corpus-path <relative_path> \
[--source-format wordml|odt] [--out <path>]"
        );
        return ExitCode::SUCCESS;
    }
    let cli =
        match ln_consultant_parser::hierarchy_lift_census::parse_hierarchy_lift_census_args(args) {
            Ok(cli) => cli,
            Err(error) => {
                eprintln!("hierarchy-lift-census: {error}");
                return ExitCode::from(ln_consultant_parser::hierarchy_lift_census::EXIT_USAGE);
            }
        };
    let (code, message) =
        ln_consultant_parser::hierarchy_lift_census::run_hierarchy_lift_census(&cli);
    if code == ln_consultant_parser::hierarchy_lift_census::EXIT_OK && cli.out.is_none() {
        // No `--out`: the payload is the output.
        println!("{message}");
    } else if !message.is_empty() {
        eprintln!("hierarchy-lift-census: {message}");
    }
    ExitCode::from(code)
}
