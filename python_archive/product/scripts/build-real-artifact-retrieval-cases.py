#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from law_nexus.application.real_artifact_retrieval_cases import (
    RealArtifactRetrievalCaseBuilder,
    stable_real_artifact_retrieval_json,
)
from law_nexus.application.real_artifact_retrieval_cases import (
    select_records as _select_records,
)
from law_nexus.ports.real_artifact_retrieval_cases import (
    RealArtifactRetrievalCaseBuildRequest,
    RealArtifactSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]
HIERARCHY_JSON_PATH = ROOT / "prd/parser/consultant_hierarchy_corpus_records.json"
HIERARCHY_JSONL_PATH = ROOT / "prd/parser/consultant_hierarchy_corpus_records.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
MAPPING_PATH = ROOT / "prd/retrieval/real_artifact_evidence_mapping.md"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"

SCHEMA_VERSION = "real-artifact-retrieval-cases/v1"

SOURCE_ARTIFACT_PATHS = [
    HIERARCHY_JSON_PATH,
    HIERARCHY_JSONL_PATH,
    STAGING_GRAPH_PATH,
    MAPPING_PATH,
]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def select_records(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    return _select_records(records)


def source_artifacts() -> list[RealArtifactSourceArtifact]:
    return [
        RealArtifactSourceArtifact(path=relative(path), sha256=sha256_path(path))
        for path in SOURCE_ARTIFACT_PATHS
    ]


def build_payload() -> dict[str, Any]:
    request = RealArtifactRetrievalCaseBuildRequest(
        hierarchy_summary=load_json(HIERARCHY_JSON_PATH),
        staging_graph=load_json(STAGING_GRAPH_PATH),
        hierarchy_records=load_jsonl(HIERARCHY_JSONL_PATH),
        source_artifacts=tuple(source_artifacts()),
    )
    return RealArtifactRetrievalCaseBuilder().build_payload(request)


def render_payload(payload: dict[str, Any]) -> str:
    return stable_real_artifact_retrieval_json(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build M013 real-artifact retrieval case corpus.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check generated corpus freshness instead of writing it.",
    )
    args = parser.parse_args(argv)

    payload = build_payload()
    rendered = render_payload(payload)
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        status = "pass" if current == rendered else "fail"
        print(
            json.dumps(
                {
                    "status": status,
                    "artifact": relative(OUTPUT_PATH),
                    "case_count": len(payload["cases"]),
                    "schema_version": SCHEMA_VERSION,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0 if status == "pass" else 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "written",
                "artifact": relative(OUTPUT_PATH),
                "case_count": len(payload["cases"]),
                "schema_version": SCHEMA_VERSION,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
