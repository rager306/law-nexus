"""Command-line surface for the repository control-plane harness."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "status":
        raise AssertionError(f"unhandled command: {args.command}")

    result = run_rust_binary(
        args.binary,
        ["status"],
        timeout_seconds=args.timeout,
        max_output_bytes=args.max_output_bytes,
    )
    sys.stdout.write(result.to_json())
    return 0 if result.status == "ok" else 1
