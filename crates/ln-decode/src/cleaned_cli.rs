//! Deterministic stdlib-only CLI for the cleaned-projection artifact.
//!
//! This module owns all CLI behavior — argument parsing, the three commands,
//! exit codes and output shaping — so the thin
//! `src/bin/cleaned-project.rs` binary is argv plus printing only and contract
//! tests exercise library functions instead of shelling out.
//!
//! Output is deterministic by construction: no clock, locale or environment
//! value enters stdout/stderr, the writer emits records in a fixed order, and
//! no `HashMap` iteration reaches the output. A repeated run is byte-identical.
//! Stderr carries closed codes and counts only: raw decoded text never reaches
//! a diagnostic. Standard library only — no clap, no serde, no walkdir.

use std::fs;
use std::io::{Cursor, Write};
use std::path::PathBuf;

use crate::cleaned_completion::{ScopeDeclaration, classify_completion};
use crate::cleaned_publish::write_cleaned_projection_atomic;
use crate::cleaned_verifier::verify_cleaned_wire;
use crate::cleaned_wire::{WireLimits, export_cleaned_projection, read_cleaned_wire};
use crate::reader_gate::{classify_source, gate_reader};
use crate::reader_projection::build_projection;
use crate::source_package::{Limits, Package, capture, read_package};

// ------------------------------------------------------------- exit codes #

/// Success.
pub const EXIT_OK: u8 = 0;
/// Usage error (unknown command/flag, missing value, invalid shape).
pub const EXIT_USAGE: u8 = 2;
/// The `--out` target could not be published.
pub const EXIT_OUT_UNWRITABLE: u8 = 3;
/// The artifact was unreadable or verification found defects.
pub const EXIT_VERIFY_FAILED: u8 = 4;
/// The input XML/package was unreadable, refused, or not projectable.
pub const EXIT_INPUT_UNREADABLE: u8 = 5;

/// Command-line usage text; also printed by the thin binary for `-h`/`--help`.
pub const USAGE: &str = "\
cleaned-project — export, read back and verify a cleaned-projection artifact

USAGE:
    cleaned-project export --from-xml <path> | --package <path> [--completion <token>] [--out <path>]
    cleaned-project read   --artifact <path>
    cleaned-project verify --artifact <path> --package <path>

COMMANDS:
    export   Render a cleaned-projection artifact from XML or a frozen source
             package. Without --out the artifact is written to stdout.
    read     Print a counts-only summary of an artifact (never decoded text).
    verify   Independently verify an artifact against its frozen source package.

FLAGS:
    --from-xml <path>     Capture a WordML XML document into a source package
                          (gated: only supported WordML is accepted).
    --package <path>      Read a frozen source-package JSONL.
    --artifact <path>     Read a cleaned-projection artifact.
    --completion <token>  Producer scope declaration:
                          complete | hold | text_only | caller_scope |
                          unsupported_source (default: complete).
    --out <path>          Publish the artifact atomically at <path>; without it
                          the artifact goes to stdout.
    -h, --help            Print this usage and exit 0.

EXIT CODES:
    0  success
    2  usage error
    3  --out could not be published
    4  artifact unreadable or verification failed
    5  input XML/package unreadable or refused

Stdlib only: no clock, locale or environment enters the output, so repeated
runs are byte-identical.
";

// ---------------------------------------------------------------- parsing #

/// Closed command vocabulary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CleanedCommand {
    /// Render a cleaned-projection artifact.
    Export,
    /// Print a counts-only summary of an artifact.
    Read,
    /// Independently verify an artifact against its source package.
    Verify,
}

/// Parsed `cleaned-project` invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanedCli {
    /// Selected command.
    pub command: CleanedCommand,
    /// XML input for `export`.
    pub from_xml: Option<PathBuf>,
    /// Frozen source-package JSONL input for `export` / `verify`.
    pub package: Option<PathBuf>,
    /// Cleaned-projection artifact input for `read` / `verify`.
    pub artifact: Option<PathBuf>,
    /// Atomic publication target for `export`; `None` means stdout.
    pub out: Option<PathBuf>,
    /// Producer scope declaration (defaults to `complete`).
    pub completion: ScopeDeclaration,
}

/// Parses the argument vector (excluding the program name) into a
/// [`CleanedCli`].
///
/// Returns [`EXIT_USAGE`] for an unknown command, an unknown flag, a missing
/// flag value, an unknown `--completion` token, or a command whose required
/// inputs are absent or contradictory.
pub fn parse_cleaned_args(argv: Vec<String>) -> Result<CleanedCli, u8> {
    let mut iter = argv.iter();
    let command = match iter.next().map(String::as_str) {
        Some("export") => CleanedCommand::Export,
        Some("read") => CleanedCommand::Read,
        Some("verify") => CleanedCommand::Verify,
        _ => return Err(EXIT_USAGE),
    };
    let mut cli = CleanedCli {
        command,
        from_xml: None,
        package: None,
        artifact: None,
        out: None,
        completion: ScopeDeclaration::WholeProjection,
    };
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--from-xml" => cli.from_xml = Some(PathBuf::from(next_value(&mut iter)?)),
            "--package" => cli.package = Some(PathBuf::from(next_value(&mut iter)?)),
            "--artifact" => cli.artifact = Some(PathBuf::from(next_value(&mut iter)?)),
            "--out" => cli.out = Some(PathBuf::from(next_value(&mut iter)?)),
            "--completion" => {
                let token = next_value(&mut iter)?;
                cli.completion = ScopeDeclaration::from_token(&token).map_err(|_| EXIT_USAGE)?;
            }
            _ => return Err(EXIT_USAGE),
        }
    }
    validate_shape(&cli)?;
    Ok(cli)
}

fn next_value<'a>(iter: &mut impl Iterator<Item = &'a String>) -> Result<String, u8> {
    iter.next().cloned().ok_or(EXIT_USAGE)
}

/// Command-specific required/forbidden flag shape. Fail-closed: a flag that
/// cannot mean anything for the selected command is a usage error.
fn validate_shape(cli: &CleanedCli) -> Result<(), u8> {
    match cli.command {
        CleanedCommand::Export => {
            if cli.artifact.is_some() {
                return Err(EXIT_USAGE);
            }
            match (cli.from_xml.is_some(), cli.package.is_some()) {
                (true, false) | (false, true) => Ok(()),
                _ => Err(EXIT_USAGE),
            }
        }
        CleanedCommand::Read => {
            if cli.artifact.is_none() || cli.from_xml.is_some() || cli.package.is_some() {
                return Err(EXIT_USAGE);
            }
            Ok(())
        }
        CleanedCommand::Verify => {
            if cli.artifact.is_none() || cli.package.is_none() || cli.from_xml.is_some() {
                return Err(EXIT_USAGE);
            }
            Ok(())
        }
    }
}

// ----------------------------------------------------------------- runner #

/// Runs a parsed invocation against the real stdout/stderr.
pub fn run_cleaned(cli: &CleanedCli) -> u8 {
    let stdout = std::io::stdout();
    let stderr = std::io::stderr();
    let mut out = stdout.lock();
    let mut err = stderr.lock();
    run_cleaned_with(cli, &mut out, &mut err)
}

/// Runs a parsed invocation against caller-supplied writers.
///
/// This is the testability seam: [`run_cleaned`] delegates here with the
/// process stdout/stderr, and contract tests pass `Vec<u8>` buffers to inspect
/// deterministic output without spawning a subprocess.
pub fn run_cleaned_with<W: Write, E: Write>(cli: &CleanedCli, out: &mut W, err: &mut E) -> u8 {
    match cli.command {
        CleanedCommand::Export => run_export(cli, out, err),
        CleanedCommand::Read => run_read(cli, out, err),
        CleanedCommand::Verify => run_verify(cli, out, err),
    }
}

fn run_export<W: Write, E: Write>(cli: &CleanedCli, out: &mut W, err: &mut E) -> u8 {
    let Some(package) = load_package(cli, err) else {
        return EXIT_INPUT_UNREADABLE;
    };

    // `--from-xml` is gated: only supported WordML may be captured. The
    // `--package` path instead classifies freely, so an out-of-profile package
    // still exports as an honest `Incomplete{UnsupportedSource}`.
    let source_class = if cli.from_xml.is_some() {
        match gate_reader(package.records()) {
            Ok(class) => class,
            Err(refusal) => {
                let _ = writeln!(
                    err,
                    "cleaned-project: source refused: {}",
                    refusal.kind().as_str()
                );
                return EXIT_INPUT_UNREADABLE;
            }
        }
    } else {
        classify_source(package.records())
    };
    let completion = classify_completion(source_class, cli.completion);

    let projection = match build_projection(package.records()) {
        Ok(projection) => projection,
        Err(error) => {
            let _ = writeln!(
                err,
                "cleaned-project: projection failed: {}",
                error.kind().as_str()
            );
            return EXIT_INPUT_UNREADABLE;
        }
    };
    let artifact =
        match export_cleaned_projection(&package, &projection, &completion, &WireLimits::default())
        {
            Ok(artifact) => artifact,
            Err(error) => {
                let _ = writeln!(
                    err,
                    "cleaned-project: export failed: {}",
                    error.kind().as_str()
                );
                return EXIT_INPUT_UNREADABLE;
            }
        };

    match &cli.out {
        Some(path) => match write_cleaned_projection_atomic(path, &artifact) {
            Ok(()) => EXIT_OK,
            Err(error) => {
                let _ = writeln!(
                    err,
                    "cleaned-project: publish failed: {}",
                    error.kind().as_str()
                );
                EXIT_OUT_UNWRITABLE
            }
        },
        None => match out.write_all(artifact.as_bytes()) {
            Ok(()) => EXIT_OK,
            Err(_) => EXIT_OUT_UNWRITABLE,
        },
    }
}

fn load_package<E: Write>(cli: &CleanedCli, err: &mut E) -> Option<Package> {
    if let Some(path) = &cli.from_xml {
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(error) => {
                let _ = writeln!(
                    err,
                    "cleaned-project: cannot read --from-xml: {}",
                    io_error_token(&error)
                );
                return None;
            }
        };
        match capture(&bytes, &Limits::default()) {
            Ok(package) => Some(package),
            Err(error) => {
                let _ = writeln!(err, "cleaned-project: capture failed: {error}");
                None
            }
        }
    } else if let Some(path) = &cli.package {
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(error) => {
                let _ = writeln!(
                    err,
                    "cleaned-project: cannot read --package: {}",
                    io_error_token(&error)
                );
                return None;
            }
        };
        match read_package(Cursor::new(bytes), &Limits::default()) {
            Ok(package) => Some(package),
            Err(error) => {
                let _ = writeln!(err, "cleaned-project: package unreadable: {error}");
                None
            }
        }
    } else {
        None
    }
}

fn run_read<W: Write, E: Write>(cli: &CleanedCli, out: &mut W, err: &mut E) -> u8 {
    let Some(path) = &cli.artifact else {
        return EXIT_USAGE;
    };
    let text = match fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) => {
            let _ = writeln!(
                err,
                "cleaned-project: cannot read --artifact: {}",
                io_error_token(&error)
            );
            return EXIT_VERIFY_FAILED;
        }
    };
    let readback = match read_cleaned_wire(&text) {
        Ok(readback) => readback,
        Err(error) => {
            let _ = writeln!(
                err,
                "cleaned-project: artifact unreadable: {}",
                error.kind().as_str()
            );
            return EXIT_VERIFY_FAILED;
        }
    };

    // Counts-only summary. The summed inline channels are recomputed from the
    // reconstructed `inline_texts`; the declared footer counts are printed as
    // declared. No decoded text ever reaches a writer.
    let inline_chars: u64 = readback
        .inline_texts
        .iter()
        .map(|segment| segment.text.chars().count() as u64)
        .sum();
    let inline_bytes: u64 = readback
        .inline_texts
        .iter()
        .map(|segment| segment.text.len() as u64)
        .sum();
    let counts = &readback.counts;
    let _ = writeln!(out, "contract_version={}", readback.contract_version);
    let _ = writeln!(out, "completion={}", readback.completion.as_str());
    let _ = writeln!(out, "completion_basis={}", readback.completion.basis_str());
    let _ = writeln!(
        out,
        "incomplete_reasons={}",
        readback.completion.reason_strs().join(",")
    );
    let _ = writeln!(out, "views={}", counts.views);
    let _ = writeln!(out, "segments={}", counts.segments);
    let _ = writeln!(out, "references={}", counts.references);
    let _ = writeln!(out, "source_segments={}", counts.source_segments);
    let _ = writeln!(out, "derived_segments={}", counts.derived_segments);
    let _ = writeln!(out, "records={}", counts.records);
    let _ = writeln!(out, "text_chars={}", counts.text_chars);
    let _ = writeln!(out, "text_bytes={}", counts.text_bytes);
    let _ = writeln!(out, "inline_chars={inline_chars}");
    let _ = writeln!(out, "inline_bytes={inline_bytes}");
    EXIT_OK
}

fn run_verify<W: Write, E: Write>(cli: &CleanedCli, out: &mut W, err: &mut E) -> u8 {
    let (Some(artifact_path), Some(package_path)) = (&cli.artifact, &cli.package) else {
        return EXIT_USAGE;
    };
    let text = match fs::read_to_string(artifact_path) {
        Ok(text) => text,
        Err(error) => {
            let _ = writeln!(
                err,
                "cleaned-project: cannot read --artifact: {}",
                io_error_token(&error)
            );
            return EXIT_VERIFY_FAILED;
        }
    };
    let bytes = match fs::read(package_path) {
        Ok(bytes) => bytes,
        Err(error) => {
            let _ = writeln!(
                err,
                "cleaned-project: cannot read --package: {}",
                io_error_token(&error)
            );
            return EXIT_INPUT_UNREADABLE;
        }
    };
    let package = match read_package(Cursor::new(bytes), &Limits::default()) {
        Ok(package) => package,
        Err(error) => {
            let _ = writeln!(err, "cleaned-project: package unreadable: {error}");
            return EXIT_INPUT_UNREADABLE;
        }
    };
    match verify_cleaned_wire(&text, &package) {
        Ok(()) => EXIT_OK,
        Err(findings) => {
            let _ = writeln!(out, "findings={}", findings.len());
            for finding in &findings {
                let _ = writeln!(out, "code={}", finding.code.as_str());
            }
            EXIT_VERIFY_FAILED
        }
    }
}

/// Closed token for an I/O error kind; never carries a path or payload.
fn io_error_token(error: &std::io::Error) -> &'static str {
    match error.kind() {
        std::io::ErrorKind::NotFound => "not_found",
        std::io::ErrorKind::PermissionDenied => "permission_denied",
        std::io::ErrorKind::InvalidData => "invalid_data",
        _ => "io_error",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_defaults_completion_to_complete() {
        let cli = parse_cleaned_args(vec!["export".into(), "--from-xml".into(), "in.xml".into()])
            .expect("export from xml parses");
        assert_eq!(cli.command, CleanedCommand::Export);
        assert_eq!(cli.from_xml, Some(PathBuf::from("in.xml")));
        assert_eq!(cli.completion, ScopeDeclaration::WholeProjection);
        assert_eq!(cli.out, None);
    }

    #[test]
    fn unknown_command_and_flag_are_usage_errors() {
        assert_eq!(parse_cleaned_args(Vec::new()).unwrap_err(), EXIT_USAGE);
        assert_eq!(
            parse_cleaned_args(vec!["frobnicate".into()]).unwrap_err(),
            EXIT_USAGE
        );
        assert_eq!(
            parse_cleaned_args(vec![
                "export".into(),
                "--from-xml".into(),
                "x".into(),
                "--bogus".into()
            ])
            .unwrap_err(),
            EXIT_USAGE
        );
    }

    #[test]
    fn io_error_token_is_closed() {
        let not_found = std::io::Error::from(std::io::ErrorKind::NotFound);
        assert_eq!(io_error_token(&not_found), "not_found");
        let other = std::io::Error::from(std::io::ErrorKind::Other);
        assert_eq!(io_error_token(&other), "io_error");
    }
}
