//! Thin `npa-bounds-scan` binary: argv parsing and output wiring only
//! (M200-8s4kwq S01/T03). Every behavior — root resolution with
//! empty-as-unset env semantics, the deterministic walk through the T02
//! observation seam, the production Consultant decode path, the
//! `npa-bounds-scan/v1` accumulator, the closed-schema render, and the
//! exit-code contract — lives in `ln_decode::npa_bounds`, so contract
//! tests exercise library functions instead of shelling out. Stderr
//! carries counts only; payload bytes and block text never reach
//! stdout/stderr (Q3). Stdlib only: no clap, no walkdir, no serde.

use std::io::Write as _;
use std::process::ExitCode;

use ln_decode::npa_bounds;
use ln_decode::npa_sweep;

const USAGE: &str = "\
npa-bounds-scan — read-only npa-bounds-scan/v1 measurement profile over the Consultant XML export

USAGE:
    npa-bounds-scan [--root <dir>] [--out <path>] [--limit <n>] [--label <label>]
                    [--source-revision <value>] [--rust-toolchain <value>]

FLAGS:
    --root <dir>           Scan root: an existing tree of *.xml files. Default
                           is the resolved Consultant export
                           (<CONSULTANT_EXPORT_DIR>/consru_export/exports,
                           empty env value counts as unset); an absent default
                           root is skip-mode: exit 0 with a zeroed aggregate.
    --out <path>           Write the JSONL aggregate to <path> instead of
                           stdout.
    --limit <n>            Process at most <n> XML files after the
                           deterministic sort; 0 is a valid empty scan.
    --label <label>        Run label for the header record (default:
                           fixture-gate).
    --source-revision <v>  Source revision recorded in the terminal run
                           manifest.
    --rust-toolchain <v>   Rust toolchain recorded in the terminal run
                           manifest.
    -h, --help             Print this usage and exit 0.

EXIT CODES:
    0  scan completed (per-file failures are classified malformed or
       unreadable, never fatal)
    2  usage error
    3  --out could not be opened for writing
    4  explicit --root does not exist or is not a directory
    5  filesystem walk failure

The run lifecycle stays [diagnostic]: numeric bounds decisions are
deferred-undefined (D388 runtime_stop), and lexical proxies are never
semantic frames.
";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        print!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let mut cli = match npa_bounds::parse_bounds_args(args) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("npa-bounds-scan: {message}");
            eprint!("{USAGE}");
            return ExitCode::from(npa_bounds::EXIT_USAGE);
        }
    };
    // The manifest records the CLI invocation window captured immediately
    // before the scan call (a manifest limitation states this explicitly).
    cli.started_at = Some(rfc3339_now());
    cli.ended_at = Some(rfc3339_now());
    let run = npa_bounds::run_bounds_scan(&cli, &npa_sweep::default_sweep_root());
    if !run.stderr.is_empty() {
        eprintln!("npa-bounds-scan: {}", run.stderr);
    }
    if let (Some(jsonl), true) = (&run.jsonl, run.to_stdout) {
        let mut stdout = std::io::stdout().lock();
        let _ = stdout.write_all(jsonl.as_bytes());
        let _ = stdout.flush();
    }
    ExitCode::from(run.exit_code)
}

/// RFC3339 UTC timestamp from the system clock, stdlib only.
fn rfc3339_now() -> String {
    let elapsed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = elapsed.as_secs();
    let (days, rest) = (secs / 86_400, secs % 86_400);
    let (year, month, day) = civil_from_days(days as i64);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}Z",
        rest / 3_600,
        (rest % 3_600) / 60,
        rest % 60
    )
}

/// Days-since-epoch to civil date (Howard Hinnant's algorithm; stdlib only).
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let shifted = days + 719_468;
    let era = if shifted >= 0 {
        shifted
    } else {
        shifted - 146_096
    } / 146_097;
    let day_of_era = (shifted - era * 146_097) as u64;
    let year_of_era =
        (day_of_era - day_of_era / 1_460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let year = year_of_era as i64 + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let mp = (5 * day_of_year + 2) / 153;
    let day = (day_of_year - (153 * mp + 2) / 5 + 1) as u32;
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if month <= 2 { year + 1 } else { year }, month, day)
}
