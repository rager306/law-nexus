from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

from law_nexus.adapters.retrieval.proof_helpers import (
    BOUNDED_DIAGNOSTIC_FIELDS,
    MAX_SAFE_FIELD_LENGTH,
    bounded_path,
    diagnostic_codes,
    diagnostic_payloads,
    error_summary,
    safe_payload_errors,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "prd/retrieval/fixtures/retrieval_output_validator_cases.json"
VALIDATOR_PATH = ROOT / "scripts/retrieval_output_validator.py"
SUMMARY_SCHEMA_VERSION = "retrieval-output-validator-proof/v1"
_MAX_SAFE_FIELD_LENGTH = MAX_SAFE_FIELD_LENGTH


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retrieval_output_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import validator from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bounded_path(path: Path) -> str:
    return bounded_path(path, root=ROOT)


def _error_summary(
    *, fixtures: Path, phase: str, code: str, detail: str | None = None
) -> dict[str, Any]:
    return error_summary(
        fixtures=fixtures,
        root=ROOT,
        schema_version=SUMMARY_SCHEMA_VERSION,
        phase=phase,
        code=code,
        detail=detail,
    )


def _diagnostic_codes(result: Any) -> list[str]:
    return diagnostic_codes(result)


def _diagnostic_payloads(result: Any) -> list[Mapping[str, Any]]:
    return diagnostic_payloads(result)


def _safe_payload_errors(
    *,
    case_id: str,
    result: Any,
    safe_fields: set[str],
    known_codes: set[str],
) -> list[dict[str, Any]]:
    return safe_payload_errors(
        case_id=case_id,
        result=result,
        safe_fields=safe_fields,
        known_codes=known_codes,
        bounded_fields=BOUNDED_DIAGNOSTIC_FIELDS,
        max_length=MAX_SAFE_FIELD_LENGTH,
    )


def _case_mismatch(
    *,
    case_id: str,
    expected_result: Any,
    actual_result: str,
    expected_codes: Any,
    actual_codes: list[str],
) -> dict[str, Any]:
    return {
        "phase": "case_expectation",
        "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
        "code": "expectation_mismatch",
        "expected_result": str(expected_result)[:_MAX_SAFE_FIELD_LENGTH],
        "actual_result": actual_result,
        "expected_codes": expected_codes if isinstance(expected_codes, list) else [],
        "actual_codes": actual_codes,
    }


def run_proof(fixtures: Path) -> tuple[int, dict[str, Any]]:
    validator = _load_validator()
    try:
        fixture = validator.load_fixture_file(fixtures)
    except FileNotFoundError as exc:
        return 2, _error_summary(
            fixtures=fixtures, phase="fixture_load", code="fixture_not_found", detail=str(exc)
        )
    except json.JSONDecodeError as exc:
        return 2, _error_summary(
            fixtures=fixtures, phase="fixture_load", code="malformed_fixture_json", detail=exc.msg
        )
    except ValueError as exc:
        return 2, _error_summary(
            fixtures=fixtures, phase="fixture_load", code="malformed_output_shape", detail=str(exc)
        )
    except OSError as exc:
        return 2, _error_summary(
            fixtures=fixtures, phase="fixture_load", code="fixture_load_error", detail=str(exc)
        )

    data = fixture.data
    cases = data.get("cases")
    if not isinstance(cases, list):
        return 2, _error_summary(
            fixtures=fixtures,
            phase="fixture_shape",
            code="malformed_output_shape",
            detail="cases must be a list",
        )

    safe_fields = set(validator.SAFE_DIAGNOSTIC_FIELDS)
    known_codes = set(validator.KNOWN_DIAGNOSTIC_CODES)
    result_counts: Counter[str] = Counter()
    diagnostic_inventory: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            mismatches.append(
                {
                    "phase": "fixture_shape",
                    "case_id": f"<index:{index}>",
                    "code": "malformed_output_shape",
                    "field_path": f"cases[{index}]",
                }
            )
            continue
        raw_case_id = case.get("case_id")
        case_id = raw_case_id if isinstance(raw_case_id, str) else f"<index:{index}>"
        result = validator.validate_case(case, fixture)
        actual_codes = _diagnostic_codes(result)
        result_counts[result.result] += 1
        diagnostic_inventory.update(actual_codes)

        expected_result = case.get("expected_result")
        expected_codes = case.get("expected_diagnostic_codes")
        if result.result != expected_result or actual_codes != expected_codes:
            mismatches.append(
                _case_mismatch(
                    case_id=case_id,
                    expected_result=expected_result,
                    actual_result=result.result,
                    expected_codes=expected_codes,
                    actual_codes=actual_codes,
                )
            )
        mismatches.extend(
            _safe_payload_errors(
                case_id=case_id,
                result=result,
                safe_fields=safe_fields,
                known_codes=known_codes,
            )
        )

    accepted_count = result_counts["accepted"] + result_counts["accepted_scoped_no_answer"]
    rejected_count = result_counts["rejected"]
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixtures),
        "total_cases": len(cases),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "mismatch_count": len(mismatches),
        "diagnostic_code_inventory": sorted(diagnostic_inventory),
    }
    if mismatches:
        summary["mismatches"] = mismatches
    return (0 if not mismatches else 1), summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the retrieval output validator proof against tracked fixtures."
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Path to retrieval output validator fixture JSON.",
    )
    args = parser.parse_args(argv)
    exit_code, summary = run_proof(args.fixtures)
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
