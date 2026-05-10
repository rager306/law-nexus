#!/usr/bin/env python3
"""Produce the M003/S04 validation-gated read-only execution proof artifact.

T02 intentionally stops at deterministic validation. It consumes the durable S03
reasoning-safe candidate handoff, fails closed when no accepted clean candidate is
available, and records only categorical validation diagnostics. Graph execution is
left as an explicit not-attempted state for the later execution task.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_S03_ARTIFACT = ROOT / ".gsd/milestones/M003/slices/S03/S03-REASONING-SAFE-CANDIDATE.json"
DEFAULT_SCHEMA_CONTRACT = ROOT / "tests/fixtures/m002_legalgraph_schema_contract.json"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S04"
ARTIFACT_NAME = "S04-VALIDATION-READONLY-EXECUTION.json"
SCHEMA_VERSION = "m003-s04-validation-readonly-execution/v1"
S03_SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v2"
M002_SCHEMA_VERSION = "m002-legalgraph-cypher-safety-contract/v1"

_REQUIRED_S03_CLEAN_FLAGS = (
    "has_think_tag",
    "has_markdown_fence",
    "has_prose_prefix",
    "has_prose_suffix",
    "has_comment",
    "has_multi_statement",
    "raw_provider_body_persisted",
)
_REQUIRED_EVIDENCE_RETURNS = ["Article.id", "EvidenceSpan.id", "SourceBlock.id"]
_BOUNDARY_NON_CLAIMS = [
    "provider generation quality",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "ODT parsing",
    "retrieval quality",
    "production graph schema fitness",
    "live legal graph execution",
]


def _load_m002_validator() -> ModuleType:
    path = ROOT / "scripts/verify-m002-cypher-safety-contract.py"
    spec = importlib.util.spec_from_file_location("verify_m002_cypher_safety_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load M002 validator module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_M002 = _load_m002_validator()
load_schema_contract = _M002.load_schema_contract
validate_candidate = _M002.validate_candidate


def _load_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def _redaction() -> dict[str, bool]:
    return {
        "raw_provider_body_persisted": False,
        "credential_persisted": False,
        "auth_header_persisted": False,
        "prompt_text_persisted": False,
        "raw_reasoning_text_persisted": False,
        "raw_legal_text_persisted": False,
        "raw_graph_rows_persisted": False,
        "secret_like_values_persisted": False,
    }


def _execution_skipped() -> dict[str, Any]:
    return {
        "attempted": False,
        "status": "not-attempted",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "row_shape_summary": {
            "row_count_category": "not-run",
            "column_categories": [],
            "raw_rows_persisted": False,
        },
        "synthetic_identifier_categories": [],
    }


def _boundaries(proves: list[str]) -> dict[str, list[str]]:
    return {
        "proves": proves,
        "does_not_prove": _BOUNDARY_NON_CLAIMS,
    }


def _s03_source(payload: dict[str, Any] | None, *, fallback_reason: str | None = None) -> dict[str, Any]:
    if payload is None:
        return {
            "schema_version": S03_SCHEMA_VERSION,
            "status": "failed-runtime",
            "root_cause": fallback_reason or "s03-artifact-unavailable",
            "phase": "artifact-read",
            "provider_attempts": 0,
            "candidate_accepted": False,
        }
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    return {
        "schema_version": str(payload.get("schema_version", S03_SCHEMA_VERSION)),
        "status": str(payload.get("status", "failed-runtime")),
        "root_cause": str(payload.get("root_cause", "unknown")),
        "phase": str(payload.get("phase", "unknown")),
        "provider_attempts": int(payload.get("provider_attempts", 0)) if isinstance(payload.get("provider_attempts", 0), int) else 0,
        "candidate_accepted": bool(cast("dict[str, Any]", candidate).get("accepted", False)),
    }


def _candidate_unavailable_artifact(s03_payload: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "skipped",
        "root_cause": "candidate-unavailable",
        "phase": "s03-handoff",
        "s03_source": _s03_source(s03_payload, fallback_reason=reason),
        "validation": {
            "attempted": False,
            "accepted": False,
            "schema_version": M002_SCHEMA_VERSION,
            "query_shape_category": "candidate-unavailable",
            "rejection_codes": ["E_CANDIDATE_UNAVAILABLE"],
            "required_evidence_returns": [],
            "safe_parameter_categories": {},
            "candidate_availability_reason": reason,
        },
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 candidate handoff was inspected and no accepted candidate was available"]),
    }


def _schema_unavailable_artifact(s03_payload: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked-environment",
        "root_cause": "blocked-environment",
        "phase": "validation",
        "s03_source": _s03_source(s03_payload),
        "validation": {
            "attempted": True,
            "accepted": False,
            "schema_version": M002_SCHEMA_VERSION,
            "query_shape_category": "schema-unavailable",
            "rejection_codes": ["E_CONTRACT_MALFORMED"],
            "required_evidence_returns": [],
            "safe_parameter_categories": {},
            "candidate_availability_reason": "available",
            "failure_class": "contract-readback",
            "schema_load_error_category": reason,
        },
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 accepted candidate was not executed because schema contract loading failed closed"]),
    }


def _clean_candidate_text(payload: dict[str, Any]) -> tuple[str | None, str]:
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        return None, "candidate-object-missing"
    if payload.get("schema_version") != S03_SCHEMA_VERSION:
        return None, "s03-schema-mismatch"
    if payload.get("status") != "confirmed-runtime" or payload.get("root_cause") != "none":
        return None, "s03-not-confirmed-runtime"
    if candidate.get("accepted") is not True:
        return None, "candidate-not-accepted"
    if any(candidate.get(flag) is not False for flag in _REQUIRED_S03_CLEAN_FLAGS):
        return None, "candidate-diagnostics-not-clean"
    if candidate.get("categories") not in ([], None):
        return None, "candidate-diagnostics-not-clean"
    text = candidate.get("normalized_text")
    if not isinstance(text, str) or not text.strip():
        return None, "candidate-text-missing"
    return text, "available"


def _parameter_categories(query: str) -> dict[str, str]:
    categories: dict[str, str] = {}
    for key in sorted(set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", query))):
        if key == "as_of" or key.endswith("_date"):
            categories[key] = "temporal"
        elif key in {"search_terms", "q", "query"}:
            categories[key] = "search-terms"
        elif key.endswith("_id") or key == "id":
            categories[key] = "identifier"
        else:
            categories[key] = "scalar"
    return categories


def _query_shape_category(report: Any) -> str:
    if not report.accepted:
        return "rejected"
    required = set(_REQUIRED_EVIDENCE_RETURNS)
    if required.issubset(set(report.required_evidence_returns)):
        return "evidence-return-readonly"
    return "readonly"


def _validation_artifact(s03_payload: dict[str, Any], candidate_text: str, schema_contract: Path) -> dict[str, Any]:
    try:
        contract = load_schema_contract(schema_contract)
    except ValueError as exc:
        return _schema_unavailable_artifact(s03_payload, str(exc).split(":", maxsplit=1)[0])
    report = validate_candidate(candidate_text, contract, query_case="s03_reasoning_safe_candidate")
    report_dict = asdict(report)
    validation = {
        "attempted": True,
        "accepted": report.accepted,
        "schema_version": report.schema_version,
        "query_shape_category": _query_shape_category(report),
        "rejection_codes": list(report.rejection_codes),
        "required_evidence_returns": list(report.required_evidence_returns),
        "safe_parameter_categories": _parameter_categories(candidate_text) if report.accepted else {},
        "candidate_availability_reason": "available",
    }
    if not report.accepted:
        validation["failure_class"] = report_dict["diagnostics"][0]["failure_class"] if report_dict["diagnostics"] else "validation"
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "validation-rejected",
            "root_cause": "validation-rejected",
            "phase": "validation",
            "s03_source": _s03_source(s03_payload),
            "validation": validation,
            "execution": _execution_skipped(),
            "redaction": _redaction(),
            "boundaries": _boundaries(["S03 accepted candidate was rejected by deterministic M002 validation before execution"]),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "validation-accepted",
        "root_cause": "none",
        "phase": "validation",
        "s03_source": _s03_source(s03_payload),
        "validation": validation,
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 accepted candidate passed deterministic M002 validation; graph execution is explicitly skipped in T02"]),
    }


def build_artifact(s03_artifact: Path, schema_contract: Path = DEFAULT_SCHEMA_CONTRACT) -> dict[str, Any]:
    try:
        s03_payload = _load_json(s03_artifact)
    except FileNotFoundError:
        return _candidate_unavailable_artifact(None, "s03-artifact-missing")
    except json.JSONDecodeError:
        return _candidate_unavailable_artifact(None, "s03-artifact-malformed")
    except OSError:
        return _candidate_unavailable_artifact(None, "s03-artifact-read-failed")

    candidate_text, reason = _clean_candidate_text(s03_payload)
    if candidate_text is None:
        return _candidate_unavailable_artifact(s03_payload, reason)
    return _validation_artifact(s03_payload, candidate_text, schema_contract)


def write_artifact(artifact_dir: Path, payload: dict[str, Any]) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / ARTIFACT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s03-artifact", type=Path, default=DEFAULT_S03_ARTIFACT)
    parser.add_argument("--schema-contract", type=Path, default=DEFAULT_SCHEMA_CONTRACT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--no-write-artifacts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_artifact(args.s03_artifact, args.schema_contract)
    if not args.no_write_artifacts:
        artifact_path = write_artifact(args.artifact_dir, payload)
    else:
        artifact_path = None
    result = {
        "verdict": "pass" if payload["status"] in {"skipped", "validation-rejected", "validation-accepted"} else "fail",
        "status": payload["status"],
        "root_cause": payload["root_cause"],
        "phase": payload["phase"],
        "s03_status": payload["s03_source"]["status"],
        "validation_attempted": payload["validation"]["attempted"],
        "validation_accepted": payload["validation"]["accepted"],
        "validation_rejection_codes": payload["validation"]["rejection_codes"],
        "execution_attempted": payload["execution"]["attempted"],
        "artifact": str(artifact_path) if artifact_path is not None else None,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
