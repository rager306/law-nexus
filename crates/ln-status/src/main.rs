use std::env;
use std::io::{self, Write};
use std::process::ExitCode;
use std::thread;
use std::time::Duration;

const STATUS_SCHEMA_VERSION: &str = "law-nexus-rust-status/v1";
const VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug, PartialEq, Eq)]
enum Command {
    Status,
    Fail,
    SleepMs(u64),
    VerboseBytes(usize),
    Help,
}

fn status_json() -> String {
    format!(
        "{{\"binary\":\"ln-status\",\"mode\":\"repository-tracer\",\"schema_version\":\"{STATUS_SCHEMA_VERSION}\",\"status\":\"ok\",\"version\":\"{VERSION}\"}}"
    )
}

fn parse_command(args: &[String]) -> Result<Command, String> {
    match args {
        [] => Ok(Command::Status),
        [command] if command == "status" => Ok(Command::Status),
        [command] if command == "--fail" => Ok(Command::Fail),
        [command] if command == "--help" || command == "-h" => Ok(Command::Help),
        [command, value] if command == "--sleep-ms" => value
            .parse::<u64>()
            .map(Command::SleepMs)
            .map_err(|_| format!("invalid milliseconds: {value}")),
        [command, value] if command == "--verbose-bytes" => value
            .parse::<usize>()
            .map(Command::VerboseBytes)
            .map_err(|_| format!("invalid byte count: {value}")),
        _ => Err(format!("unknown arguments: {}", args.join(" "))),
    }
}

fn usage() -> &'static str {
    "Usage: ln-status [status|--fail|--sleep-ms N|--verbose-bytes N|--help]"
}

fn run(command: Command) -> io::Result<ExitCode> {
    match command {
        Command::Status => {
            println!("{}", status_json());
            Ok(ExitCode::SUCCESS)
        }
        Command::Fail => {
            println!(
                "{{\"binary\":\"ln-status\",\"schema_version\":\"{STATUS_SCHEMA_VERSION}\",\"status\":\"forced_failure\"}}"
            );
            eprintln!("forced failure for repository harness verification");
            Ok(ExitCode::from(2))
        }
        Command::SleepMs(milliseconds) => {
            thread::sleep(Duration::from_millis(milliseconds));
            println!("{}", status_json());
            Ok(ExitCode::SUCCESS)
        }
        Command::VerboseBytes(count) => {
            let mut stdout = io::stdout().lock();
            let chunk = vec![b'x'; count];
            stdout.write_all(&chunk)?;
            stdout.write_all(b"\n")?;
            Ok(ExitCode::SUCCESS)
        }
        Command::Help => {
            println!("{}", usage());
            Ok(ExitCode::SUCCESS)
        }
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let command = match parse_command(&args) {
        Ok(command) => command,
        Err(message) => {
            eprintln!("{message}");
            eprintln!("{}", usage());
            return ExitCode::from(2);
        }
    };

    match run(command) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("ln-status I/O failure: {error}");
            ExitCode::from(1)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    #[test]
    fn status_payload_is_deterministic() {
        assert_eq!(
            status_json(),
            "{\"binary\":\"ln-status\",\"mode\":\"repository-tracer\",\"schema_version\":\"law-nexus-rust-status/v1\",\"status\":\"ok\",\"version\":\"0.1.0\"}"
        );
    }

    #[test]
    fn parses_supported_commands() {
        assert_eq!(parse_command(&[]), Ok(Command::Status));
        assert_eq!(parse_command(&args(&["status"])), Ok(Command::Status));
        assert_eq!(parse_command(&args(&["--fail"])), Ok(Command::Fail));
        assert_eq!(
            parse_command(&args(&["--sleep-ms", "25"])),
            Ok(Command::SleepMs(25))
        );
        assert_eq!(
            parse_command(&args(&["--verbose-bytes", "4096"])),
            Ok(Command::VerboseBytes(4096))
        );
    }

    #[test]
    fn rejects_unknown_or_invalid_arguments() {
        assert!(parse_command(&args(&["unknown"])).is_err());
        assert!(parse_command(&args(&["--sleep-ms", "not-a-number"])).is_err());
        assert!(parse_command(&args(&["--verbose-bytes"])).is_err());
    }
}
