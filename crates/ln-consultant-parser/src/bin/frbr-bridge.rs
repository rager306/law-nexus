//! Thin argv/output shell for the M224/S07 corpus FRBR-bridge mapping-artifact
//! consumer. Behavior lives in [`ln_consultant_parser::frbr_bridge`]; this file
//! only wires argv and stdio. The payload (mapping artifact) is ASCII by
//! construction and never carries decoded text.
use std::process::ExitCode;

use ln_consultant_parser::frbr_bridge::{EXIT_USAGE, parse_bridge_args, run_bridge};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!(
            "frbr-bridge [--envelope <path>] [--receipts <path>] [--catalog <path>] \
             [--timeline <path>] [--ontology <path>] [--registry <path>] [--binary <path>] \
             [--out <path>] [--check]"
        );
        return ExitCode::SUCCESS;
    }
    let cli = match parse_bridge_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("frbr-bridge: {error}");
            return ExitCode::from(EXIT_USAGE);
        }
    };
    let (code, message) = run_bridge(&cli);
    if code == 0 {
        println!("{message}");
    } else {
        eprintln!("frbr-bridge: {message}");
    }
    ExitCode::from(code)
}
