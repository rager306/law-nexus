#!/usr/bin/env python3
"""Command boundary for deterministic ConsultantPlus source lifecycle work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from source_lifecycle import (
    SourceLifecycleError,
    build_external_review_pack,
    build_review_pack,
    classify_batch,
    discover_with_minimax,
    lifecycle_status,
    process_batch,
    register_batch,
    run_batch_with_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = ROOT / "law-source" / "consultant"


def build_parser() -> argparse.ArgumentParser:
    """Build the source lifecycle CLI argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Deterministic no-LLM ConsultantPlus source lifecycle CLI. "
            "S03 starts with manifest-driven inventory helpers and safe output foundations."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="ConsultantPlus lifecycle workspace root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register a batch manifest.")
    register.add_argument("manifest", type=Path, help="Path to batch.manifest.json.")
    register.set_defaults(handler=run_register)

    classify = subparsers.add_parser("classify", help="Classify registered or provided XML artifacts.")
    classify.add_argument("manifest", type=Path, help="Path to batch.manifest.json.")
    classify.set_defaults(handler=run_classify)

    process = subparsers.add_parser("process", help="Emit safe inventory-only processed outputs.")
    process.add_argument("manifest", type=Path, help="Path to batch.manifest.json.")
    process.set_defaults(handler=run_process)

    status = subparsers.add_parser("status", help="Summarize lifecycle state.")
    status.set_defaults(handler=run_status)

    run_batch = subparsers.add_parser("run-batch", help="Run register, classify, and process.")
    run_batch.add_argument("manifest", type=Path, help="Path to batch.manifest.json.")
    run_batch.set_defaults(handler=run_batch_command)

    review_pack = subparsers.add_parser("review-pack", help="Write a safe review pack for a run.")
    review_pack.add_argument("run_id", nargs="?", help="Run id; defaults to latest run.")
    review_pack.set_defaults(handler=run_review_pack)

    discover = subparsers.add_parser("discover", help="Run a non-authoritative MiniMax discovery attempt.")
    discover.add_argument("--run-id", help="Optional safe RUN- id for this discovery attempt.")
    discover.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Workspace source, processed, or registry ref to include in the discovery context.",
    )
    discover.add_argument(
        "--prompt-summary",
        default="Discover source structures useful for graph context.",
        help="Bounded prompt summary or open-source context for structural discovery.",
    )
    discover.add_argument("--model", default="MiniMax-M2.7-highspeed", help="MiniMax model name.")
    discover.add_argument(
        "--endpoint",
        default="https://api.minimax.io/v1/chat/completions",
        help="MiniMax OpenAI-compatible chat-completions endpoint.",
    )
    discover.add_argument("--api-key-env", default="MINIMAX_API_KEY", help="Environment variable containing the MiniMax API key.")
    discover.add_argument("--mock-response", type=Path, help="JSON file with response_summary/content/message for tests.")
    discover.add_argument(
        "--verify-candidates",
        action="store_true",
        help="Run deterministic verifier over normalized discovery candidates.",
    )
    discover.set_defaults(handler=run_discover)

    external_review = subparsers.add_parser(
        "external-review-pack",
        help="Write an external GPT-5.5 review pack for a discovery run.",
    )
    external_review.add_argument("run_id", help="Safe RUN- id to package for external review.")
    external_review.set_defaults(handler=run_external_review_pack)
    return parser


def run_register(args: argparse.Namespace) -> int:
    """Register a batch manifest into safe lifecycle registry files."""

    result = register_batch(args.manifest, args.workspace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_classify(args: argparse.Namespace) -> int:
    """Classify manifest artifacts into safe route metadata."""

    result = classify_batch(args.manifest, args.workspace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_process(args: argparse.Namespace) -> int:
    """Emit safe inventory-only processed outputs."""

    result = process_batch(args.manifest, args.workspace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_status(args: argparse.Namespace) -> int:
    """Print bounded workspace lifecycle status."""

    result = lifecycle_status(args.workspace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_batch_command(args: argparse.Namespace) -> int:
    """Run register, classify, and inventory-only process with a run envelope."""

    result = run_batch_with_envelope(args.manifest, args.workspace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "completed" else 2


def run_review_pack(args: argparse.Namespace) -> int:
    """Write a safe review pack for a run."""

    result = build_review_pack(args.workspace, args.run_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run_discover(args: argparse.Namespace) -> int:
    """Run a non-authoritative MiniMax-assisted discovery attempt."""

    result = discover_with_minimax(
        args.workspace,
        run_id=args.run_id,
        source_refs=args.source_ref,
        prompt_summary=args.prompt_summary,
        model=args.model,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        mock_response_path=args.mock_response,
        verify_candidates=args.verify_candidates,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "completed" else 2


def run_external_review_pack(args: argparse.Namespace) -> int:
    """Write an external GPT-5.5 review pack for a discovery run."""

    result = build_external_review_pack(args.workspace, args.run_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the source lifecycle CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except SourceLifecycleError as exc:
        print(f"source lifecycle error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
