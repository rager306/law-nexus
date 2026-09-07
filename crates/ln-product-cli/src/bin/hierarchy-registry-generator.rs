//! Thin `hierarchy-registry-generator` binary (M202-9qf3ta S03 T04, D427).
//!
//! Explicit `--candidate-artifact` / `--admissions` / `--out` with mutually
//! exclusive `--write` / `--check`, orchestrated through
//! `ln_product_cli::hierarchy_registry_generation`. Exit codes are pinned:
//! 0 success, 2 usage/path refusal, 4 missing input, 6 drift/conflict/stale.

use std::process;

use ln_product_cli::hierarchy_registry_generation::{parse_generator_args, run_generator};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cli = match parse_generator_args(args) {
        Ok(cli) => cli,
        Err(error) => {
            eprintln!("{}", error.stderr_line());
            process::exit(error.exit_code());
        }
    };
    match run_generator(&cli) {
        Ok(()) => process::exit(0),
        Err(error) => {
            eprintln!("{}", error.stderr_line());
            process::exit(error.exit_code());
        }
    }
}
