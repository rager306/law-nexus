#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from law_nexus.application.offline_retrieval_cases import (
    OfflineRetrievalCaseBuilder,
    stable_retrieval_case_json,
)
from law_nexus.ports.offline_retrieval_cases import (
    OfflineRetrievalCaseBuildRequest,
    OfflineRetrievalSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/offline_citation_retrieval_contract.md"
REAL_CASES_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
HIERARCHY_JSON_PATH = ROOT / "prd/parser/consultant_hierarchy_records.json"
HIERARCHY_JSONL_PATH = ROOT / "prd/parser/consultant_hierarchy_records.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"

SOURCE_ARTIFACT_PATHS = [
    CONTRACT_PATH,
    REAL_CASES_PATH,
    HIERARCHY_JSON_PATH,
    HIERARCHY_JSONL_PATH,
    STAGING_GRAPH_PATH,
]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_artifacts() -> list[OfflineRetrievalSourceArtifact]:
    return [
        OfflineRetrievalSourceArtifact(path=relative(path), sha256=sha256_path(path))
        for path in SOURCE_ARTIFACT_PATHS
    ]


def build_payload() -> dict[str, Any]:
    request = OfflineRetrievalCaseBuildRequest(
        real_cases=load_json(REAL_CASES_PATH),
        hierarchy_records=load_jsonl(HIERARCHY_JSONL_PATH),
        source_artifacts=tuple(source_artifacts()),
    )
    return OfflineRetrievalCaseBuilder().build_payload(request)


def stable_json(data: dict[str, Any]) -> str:
    return stable_retrieval_case_json(data)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic M014 offline citation retrieval seed cases.")
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in fixture is stale.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Fixture output path.")
    args = parser.parse_args(argv)

    payload = build_payload()
    rendered = stable_json(payload)
    output_path = args.output
    if args.check:
        try:
            current = output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(json.dumps({"status": "fail", "reason": "missing_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        if current != rendered:
            print(json.dumps({"status": "fail", "reason": "stale_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        print(json.dumps({"status": "pass", "case_count": len(payload["cases"]), "path": relative(output_path)}, sort_keys=True))
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "written", "case_count": len(payload["cases"]), "path": relative(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
