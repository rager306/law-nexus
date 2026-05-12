#!/usr/bin/env python3
"""Generate a derived, non-authoritative architecture closure roadmap.

The closure roadmap summarizes M007/R04 architecture-governance closure state
from the S02 remediation matrix and S03 major track split. It is not product
readiness evidence and does not retire open proof gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_JSON_PATH = ROOT / "prd/architecture/remediation_matrix.json"
DEFAULT_TRACK_JSON_PATH = ROOT / "prd/architecture/major_track_split.json"
DEFAULT_CLOSURE_JSON_PATH = ROOT / "prd/architecture/closure_roadmap.json"
DEFAULT_CLOSURE_MD_PATH = ROOT / "prd/architecture/closure_roadmap.md"

EXPECTED_RECOMMENDATION_COUNT = 18
EXPECTED_TRACK_COUNT = 6
EXPECTED_ASSIGNED_GATE_COUNT = 7

FINAL_STATUS_BUCKETS = {
    "implemented-s01": "completed-in-m007",
    "implemented-s01-open-gates": "completed-in-m007-with-open-gates",
    "partially-implemented-s01": "partial-follow-up",
    "downstream-s03": "future-proof-track",
    "defer-s04": "deferred-minor",
}


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc


def validate_inputs(matrix: dict[str, Any], track_split: dict[str, Any]) -> None:
    recommendation_count = len(matrix.get("recommendation_rows", []))
    track_count = len(track_split.get("tracks", []))
    assigned_gate_count = track_split.get("summary", {}).get("assigned_gate_count")
    errors: list[str] = []
    if recommendation_count != EXPECTED_RECOMMENDATION_COUNT:
        errors.append(f"expected {EXPECTED_RECOMMENDATION_COUNT} recommendations, found {recommendation_count}")
    if track_count != EXPECTED_TRACK_COUNT:
        errors.append(f"expected {EXPECTED_TRACK_COUNT} tracks, found {track_count}")
    if assigned_gate_count != EXPECTED_ASSIGNED_GATE_COUNT:
        errors.append(f"expected {EXPECTED_ASSIGNED_GATE_COUNT} assigned gates, found {assigned_gate_count}")
    unknown_statuses = sorted({row.get("status") for row in matrix.get("recommendation_rows", [])} - set(FINAL_STATUS_BUCKETS))
    if unknown_statuses:
        errors.append(f"unknown recommendation statuses: {', '.join(str(status) for status in unknown_statuses)}")
    if errors:
        raise RuntimeError("; ".join(errors))


def build_closure(matrix: dict[str, Any], track_split: dict[str, Any]) -> dict[str, Any]:
    validate_inputs(matrix, track_split)
    recommendations = matrix["recommendation_rows"]
    tracks = track_split["tracks"]
    recommendation_rows: list[dict[str, Any]] = []
    for row in recommendations:
        recommendation_rows.append(
            {
                "id": row["id"],
                "title": row["title"],
                "priority": row["priority"],
                "m007_status": row["status"],
                "final_bucket": FINAL_STATUS_BUCKETS[row["status"]],
                "next": row["next"],
                "non_claims": row.get("non_claims", []),
            }
        )
    status_counts = dict(sorted(Counter(row["m007_status"] for row in recommendation_rows).items()))
    bucket_counts = dict(sorted(Counter(row["final_bucket"] for row in recommendation_rows).items()))
    return {
        "schema_version": "legalgraph-architecture-closure-roadmap/v1",
        "record_kind": "derived-architecture-closure-roadmap",
        "review_id": "R04",
        "milestone_id": "M007",
        "non_authoritative": True,
        "source_inputs": [
            "prd/architecture/remediation_matrix.json",
            "prd/architecture/major_track_split.json",
        ],
        "summary": {
            "recommendation_count": len(recommendation_rows),
            "track_count": len(tracks),
            "assigned_gate_count": track_split["summary"]["assigned_gate_count"],
            "status_counts": status_counts,
            "bucket_counts": bucket_counts,
        },
        "recommendation_rows": recommendation_rows,
        "future_tracks": [
            {
                "track_id": track["track_id"],
                "title": track["title"],
                "track_status": track["track_status"],
                "gate_ids": track["gate_ids"],
                "proof_artifact": track["proof_artifact"],
                "recommended_next_unit": track["recommended_next_unit"],
                "non_claims": track["non_claims"],
            }
            for track in tracks
        ],
        "m007_closure_statement": "M007 closes R04 architecture governance triage, coverage, matrix, and track-split planning; it does not close product/runtime proof gates.",
        "non_claims": [
            "M007 closure does not prove product readiness.",
            "M007 closure does not retire generated-Cypher, access-control, parser/retrieval, temporal, embedding, or runtime migration proof gates.",
            "M007 closure does not prove legal-answer correctness, parser completeness, retrieval quality, FalkorDB production behavior, or LLM legal authority.",
            "Future tracks are planning destinations, not completed implementation slices.",
        ],
    }


def render_markdown(closure: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Architecture Closure Roadmap",
        "",
        "> **Scope:** Derived, non-authoritative M007/R04 closure artifact. It records architecture-governance closure and future proof destinations; it does not prove product readiness.",
        "",
        "## Closure Statement",
        "",
        closure["m007_closure_statement"],
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| R04 recommendations | {closure['summary']['recommendation_count']} |",
        f"| Future proof tracks | {closure['summary']['track_count']} |",
        f"| Assigned open gates | {closure['summary']['assigned_gate_count']} |",
        "",
        "### Recommendation Buckets",
        "",
        "| Bucket | Count |",
        "| --- | ---: |",
    ]
    for bucket, count in closure["summary"]["bucket_counts"].items():
        lines.append(f"| {escape_md(bucket)} | {count} |")

    lines.extend([
        "",
        "## R04 Recommendation Final Disposition",
        "",
        "| Recommendation | Priority | M007 Status | Final Bucket | Next |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in closure["recommendation_rows"]:
        lines.append(
            f"| `{escape_md(row['id'])}` — {escape_md(row['title'])} | "
            f"{escape_md(row['priority'])} | {escape_md(row['m007_status'])} | "
            f"{escape_md(row['final_bucket'])} | {escape_md(row['next'])} |"
        )

    lines.extend([
        "",
        "## Future Proof Tracks",
        "",
        "| Track | Status | Gates | Proof Artifact | Next Unit |",
        "| --- | --- | --- | --- | --- |",
    ])
    for track in closure["future_tracks"]:
        lines.append(
            f"| `{escape_md(track['track_id'])}` — {escape_md(track['title'])} | "
            f"{escape_md(track['track_status'])} | {escape_md(', '.join(track['gate_ids']))} | "
            f"{escape_md(track['proof_artifact'])} | {escape_md(track['recommended_next_unit'])} |"
        )

    lines.extend([
        "",
        "## Non-Claims",
        "",
    ])
    for claim in closure["non_claims"]:
        lines.append(f"- {escape_md(claim)}")

    lines.extend([
        "",
        "---",
        "",
        "*Generated from `prd/architecture/remediation_matrix.json` and `prd/architecture/major_track_split.json`. Source evidence remains authoritative.*",
    ])
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_output(path: Path, expected: str, label: str) -> bool:
    if not path.exists():
        print(f"missing {label}: {path}; regenerate with `uv run python scripts/generate-architecture-closure-roadmap.py`", file=sys.stderr)
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"stale {label}: {path}; regenerate with `uv run python scripts/generate-architecture-closure-roadmap.py`", file=sys.stderr)
        return False
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/check the derived architecture closure roadmap.")
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON_PATH)
    parser.add_argument("--track-json", type=Path, default=DEFAULT_TRACK_JSON_PATH)
    parser.add_argument("--closure-json", type=Path, default=DEFAULT_CLOSURE_JSON_PATH)
    parser.add_argument("--closure-md", type=Path, default=DEFAULT_CLOSURE_MD_PATH)
    parser.add_argument("--check", action="store_true", help="Compare expected outputs without rewriting.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        matrix = load_json(args.matrix_json)
        track_split = load_json(args.track_json)
        closure = build_closure(matrix, track_split)
    except RuntimeError as exc:
        print(f"closure roadmap error: {exc}", file=sys.stderr)
        return 1

    expected_json = json.dumps(closure, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(closure)

    if args.check:
        if not check_output(args.closure_json, expected_json, "closure roadmap JSON"):
            return 1
        if not check_output(args.closure_md, expected_md, "closure roadmap Markdown"):
            return 1
    else:
        write_atomic(args.closure_json, expected_json)
        write_atomic(args.closure_md, expected_md)

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "write",
        "closure_json": str(args.closure_json),
        "closure_md": str(args.closure_md),
        "recommendation_count": closure["summary"]["recommendation_count"],
        "track_count": closure["summary"]["track_count"],
        "assigned_gate_count": closure["summary"]["assigned_gate_count"],
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
