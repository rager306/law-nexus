"""Command-line surface for the repository control-plane harness."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from law_nexus_harness.governor import run_governor
from law_nexus_harness.preflight import run_preflight
from law_nexus_harness.subprocess_runner import (
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    run_rust_binary,
)

DEFAULT_STATUS_BINARY = Path("target/debug/ln-status")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="law-nexus-harness", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    status = subcommands.add_parser("status", help="Run the Rust repository status tracer.")
    status.add_argument("--binary", type=Path, default=DEFAULT_STATUS_BINARY)
    status.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    status.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    governor = subcommands.add_parser(
        "governor",
        help=(
            "Run trajectory anti-drift checks for roadmap freshness, hostile proof "
            "chain coherence, and residual GSD debt."
        ),
    )
    governor.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    preflight = subcommands.add_parser(
        "preflight",
        help="Run early non-mutating repository preflight checks before completion/commit.",
    )
    preflight.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        result = run_rust_binary(
            args.binary,
            ["status"],
            timeout_seconds=args.timeout,
            max_output_bytes=args.max_output_bytes,
        )
        sys.stdout.write(result.to_json())
        return 0 if result.status == "ok" else 1
    if args.command == "governor":
        report = run_governor(args.root)
        sys.stdout.write(report.to_json())
        return 0 if report.status == "ok" else 1
    if args.command == "preflight":
        report = run_preflight(args.root)
        sys.stdout.write(report.to_json())
        return 0 if report.status == "ok" else 1
    raise AssertionError(f"unhandled command: {args.command}")
