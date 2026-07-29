#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from law_nexus.adapters.cli.runtime import (
    CliRuntimeError,
    load_json_object,
    repo_relative_path,
    stable_json_text,
)
from law_nexus.adapters.cli.runtime import (
    sha256_bytes as cli_sha256_bytes,
)
from law_nexus.adapters.cli.runtime import (
    sha256_path as cli_sha256_path,
)
from law_nexus.adapters.cli.runtime import (
    sha256_text as cli_sha256_text,
)
from law_nexus.application.representative_corpus_manifest import (
    CORPUS_ID,
    DIAGNOSTIC_CODE_INVENTORY,
    FIXTURE_ARTIFACT,
    GATE,
    GENERATED_BY,
    REPORT_ARTIFACT,
    REQUIREMENT,
    SCHEMA_VERSION,
    ManifestError,
    RepresentativeCorpusManifestBuilder,
    candidate_references,
    coverage_classes,
    diagnostic,
    query_labels,
    redaction,
    runtime_handoff,
    validate_payload,
)
from law_nexus.ports.representative_corpus_manifest import (
    REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS,
    RepresentativeCorpusManifestBuildRequest,
    RepresentativeCorpusSourceArtifact,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/representative_retrieval_corpus_contract.md"
LOCAL_BENCHMARK_PATH = ROOT / "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
OFFLINE_CASES_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
REAL_ARTIFACT_CASES_PATH = ROOT / "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
SOURCE_FIXTURE_INVENTORY_PATH = ROOT / "prd/parser/source_fixture_inventory.json"
OUTPUT_PATH = ROOT / FIXTURE_ARTIFACT
REPORT_PATH = ROOT / REPORT_ARTIFACT
REQUIRED_SOURCE_PATHS = [
    CONTRACT_PATH,
    LOCAL_BENCHMARK_PATH,
    OFFLINE_CASES_PATH,
    REAL_ARTIFACT_CASES_PATH,
    SOURCE_FIXTURE_INVENTORY_PATH,
]

# Backward-compatible script constants used by existing tests and ad hoc imports.
NON_CLAIMS = REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS
LEGACY_EXPORTS = (
    SCHEMA_VERSION,
    CORPUS_ID,
    GENERATED_BY,
    GATE,
    REQUIREMENT,
    DIAGNOSTIC_CODE_INVENTORY,
    candidate_references,
    coverage_classes,
    query_labels,
    redaction,
    runtime_handoff,
    validate_payload,
)


def relative(path: Path) -> str:
    return repo_relative_path(path, root=ROOT, outside_project=path.as_posix())


def sha256_bytes(payload: bytes) -> str:
    return cli_sha256_bytes(payload)


def sha256_text(payload: str) -> str:
    return cli_sha256_text(payload)


def sha256_path(path: Path) -> str:
    return cli_sha256_path(path)


def stable_json(payload: dict[str, Any]) -> str:
    return stable_json_text(payload)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_object(path, path_display=relative)
    except CliRuntimeError as exc:
        if exc.failure_class == "missing_source_artifact":
            raise ManifestError(
                diagnostic(
                    "missing_source_artifact", severity="error", artifact_path=relative(path)
                )
            ) from exc
        raise ManifestError(
            diagnostic(
                "manifest_schema_mismatch",
                severity="error",
                artifact_path=relative(path),
                field_path="$",
            )
        ) from exc


def require_source_paths() -> None:
    for path in REQUIRED_SOURCE_PATHS:
        if not path.exists():
            raise ManifestError(
                diagnostic(
                    "missing_source_artifact", severity="error", artifact_path=relative(path)
                )
            )
        if not relative(path).startswith("prd/"):
            raise ManifestError(
                diagnostic(
                    "manifest_schema_mismatch",
                    severity="error",
                    artifact_path=relative(path),
                    field_path="source_artifacts",
                )
            )


def source_artifacts() -> list[dict[str, str]]:
    return [
        {"path": relative(path), "sha256": sha256_path(path)}
        for path in sorted(REQUIRED_SOURCE_PATHS, key=relative)
    ]


def build_request() -> RepresentativeCorpusManifestBuildRequest:
    require_source_paths()
    return RepresentativeCorpusManifestBuildRequest(
        source_fixture_inventory=load_json(SOURCE_FIXTURE_INVENTORY_PATH),
        local_retrieval_quality_benchmark=load_json(LOCAL_BENCHMARK_PATH),
        offline_citation_retrieval_cases=load_json(OFFLINE_CASES_PATH),
        real_artifact_retrieval_cases=load_json(REAL_ARTIFACT_CASES_PATH),
        source_artifacts=tuple(
            RepresentativeCorpusSourceArtifact(**artifact) for artifact in source_artifacts()
        ),
    )


def build_payload() -> dict[str, Any]:
    return RepresentativeCorpusManifestBuilder().build_payload(build_request())


def render_report(payload: dict[str, Any]) -> str:
    class_names = ", ".join(item["class_name"] for item in payload["coverage_classes"])
    return (
        "# Representative Retrieval Corpus Manifest\n\n"
        f"- Schema version: `{payload['schema_version']}`\n"
        f"- Corpus ID: `{payload['corpus_id']}`\n"
        f"- Manifest artifact: `{payload['fixture_artifact']}`\n"
        f"- Source artifact count: {len(payload['source_artifacts'])}\n"
        f"- Query label count: {len(payload['query_labels'])}\n"
        f"- Candidate reference count: {len(payload['candidate_references'])}\n"
        f"- Coverage class count: {len(payload['coverage_classes'])}\n"
        f"- Coverage classes: {class_names}\n"
        "- Boundary: redacted static manifest only; no raw legal text, raw prompts, vectors, provider payloads, raw FalkorDB rows, generated legal advice, or closed-gate claim.\n"
        "- Garant boundary: ODT fixture metadata only; no Garant parsed-content or retrieval-quality claim.\n"
    )


def success_json(payload: dict[str, Any], status: str) -> str:
    return json.dumps(
        {
            "status": status,
            "schema_version": payload["schema_version"],
            "corpus_id": payload["corpus_id"],
            "source_artifact_count": len(payload["source_artifacts"]),
            "query_label_count": len(payload["query_labels"]),
            "candidate_reference_count": len(payload["candidate_references"]),
            "coverage_class_count": len(payload["coverage_classes"]),
            "diagnostic_codes": payload["diagnostic_code_inventory"],
            "artifact": payload["fixture_artifact"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic M016 representative retrieval corpus manifest."
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail if checked-in manifest/report are stale."
    )
    args = parser.parse_args(argv)

    try:
        payload = build_payload()
        rendered = stable_json(payload)
        report = render_report(payload)
        if args.check:
            if not OUTPUT_PATH.exists():
                raise ManifestError(
                    diagnostic(
                        "missing_source_artifact",
                        severity="error",
                        artifact_path=relative(OUTPUT_PATH),
                    )
                )
            if OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
                raise ManifestError(
                    diagnostic(
                        "manifest_schema_mismatch",
                        severity="error",
                        artifact_path=relative(OUTPUT_PATH),
                        field_path="manifest_bytes",
                    )
                )
            if not REPORT_PATH.exists() or REPORT_PATH.read_text(encoding="utf-8") != report:
                raise ManifestError(
                    diagnostic(
                        "manifest_schema_mismatch",
                        severity="error",
                        artifact_path=relative(REPORT_PATH),
                        field_path="report_bytes",
                    )
                )
            print(success_json(payload, "pass"))
            return 0

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(success_json(payload, "written"))
        return 0
    except ManifestError as exc:
        print(
            json.dumps(
                {"status": "fail", "diagnostic": exc.diagnostic}, ensure_ascii=False, sort_keys=True
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
