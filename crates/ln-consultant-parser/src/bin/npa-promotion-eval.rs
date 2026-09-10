//! Evaluate and check revision-bound NPA promotion receipts.
use ln_consultant_parser::promotion_gate;
use std::{path::PathBuf, process::ExitCode};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "-h" || a == "--help") {
        println!("npa-promotion-eval --eval|--check [--root <dir>] [--out <path>]");
        return ExitCode::SUCCESS;
    }
    let root = args.windows(2).find(|w| w[0] == "--root").map_or_else(
        || PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."),
        |w| PathBuf::from(&w[1]),
    );
    let default_out = root.join("prd/migration/rust-evidence/m203-s09-promotion-receipts.jsonl");
    let out = args
        .windows(2)
        .find(|w| w[0] == "--out")
        .map_or(default_out, |w| PathBuf::from(&w[1]));
    let result = if args.iter().any(|a| a == "--eval") {
        promotion_gate::eval(&root, &out)
            .map(|blocked| format!("wrote {} receipts ({blocked} blocked)\n", 24))
    } else if args.iter().any(|a| a == "--check") {
        promotion_gate::check(&root, &out).map(|()| "promotion receipts: clean\n".to_string())
    } else {
        Err("expected --eval or --check".to_string())
    };
    match result {
        Ok(message) => {
            print!("{message}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("npa-promotion-eval: {error}");
            ExitCode::from(1)
        }
    }
}
