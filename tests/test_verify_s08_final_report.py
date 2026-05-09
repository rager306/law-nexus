from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/verify-s08-final-report.py"
REQUIRED_IDS = ("G-005", "G-008", "G-011", "G-015")
REQUIRED_REQUIREMENTS = ("R001", "R009", "R010")


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s08_final_report", VERIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_supporting_artifacts(root: Path) -> dict[str, str]:
    paths = {
        "s07_review_findings": root / "prd/04_review_findings.md",
        "s04_falkordb_smoke": root / "evidence/s04.json",
        "s05_odt_parser_findings": root / "evidence/s05.md",
        "s09_local_embedding_evaluation": root / "evidence/s09.json",
        "s10_embedding_runtime_proof": root / "evidence/s10.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture evidence\n", encoding="utf-8")
    return {key: path.relative_to(root).as_posix() for key, path in paths.items()}


def schema_payload() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "generated_at", "source_artifacts", "findings"],
        "properties": {
            "schema_version": {"const": "s08-final-architecture-findings/v1"},
            "findings": {"type": "array"},
        },
        "$defs": {
            "finding": {
                "required": [
                    "id",
                    "title",
                    "source",
                    "claim_class",
                    "status",
                    "severity",
                    "evidence",
                    "impact",
                    "recommendation",
                    "owner",
                    "resolution_path",
                    "verification_criteria",
                    "roadmap_effect",
                    "requirement_links",
                ],
                "properties": {
                    "claim_class": {
                        "enum": [
                            "prd-fixed",
                            "deferred-proof-gate",
                            "confirmed-runtime-bounded",
                            "parser-smoke-bounded",
                            "prior-art-bounded",
                            "embedding-boundary",
                            "out-of-scope-guardrail",
                        ]
                    },
                    "status": {
                        "enum": [
                            "fixed",
                            "deferred",
                            "confirmed-runtime",
                            "blocked-environment",
                            "bounded",
                            "excluded",
                        ]
                    },
                    "severity": {"enum": ["BLOCKER", "MAJOR", "MINOR", "INFO"]},
                },
            }
        },
    }


def finding(root: Path, finding_id: str, claim_class: str, status: str, severity: str) -> dict[str, Any]:
    artifact = root / f"evidence/{finding_id}.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(f"evidence for {finding_id}\n", encoding="utf-8")
    return {
        "id": finding_id,
        "title": f"{finding_id} bounded architecture finding",
        "source": [artifact.relative_to(root).as_posix()],
        "claim_class": claim_class,
        "status": status,
        "severity": severity,
        "evidence": [
            {
                "artifact": artifact.relative_to(root).as_posix(),
                "status": status,
                "summary": f"Bounded evidence summary for {finding_id}.",
            }
        ],
        "impact": f"Impact for {finding_id} remains bounded.",
        "recommendation": f"Recommendation for {finding_id} preserves architecture-only scope.",
        "owner": f"Owner for {finding_id}",
        "resolution_path": f"Resolution path for {finding_id}",
        "verification_criteria": f"Verification criteria for {finding_id}",
        "roadmap_effect": f"Roadmap effect for {finding_id}",
        "requirement_links": list(REQUIRED_REQUIREMENTS),
        "non_goals": ["No product ETL or production legal retrieval quality claim."],
    }


def findings_payload(root: Path) -> dict[str, Any]:
    source_artifacts = write_supporting_artifacts(root)
    rows = [
        finding(root, "S07-FIXED-PRD-CONSISTENCY", "prd-fixed", "fixed", "INFO"),
        finding(root, "G-005", "deferred-proof-gate", "deferred", "MAJOR"),
        finding(root, "G-008", "deferred-proof-gate", "deferred", "MAJOR"),
        finding(root, "G-011", "embedding-boundary", "confirmed-runtime", "MINOR"),
        finding(root, "G-015", "deferred-proof-gate", "deferred", "MINOR"),
        finding(root, "S04-FALKORDB-RUNTIME-BOUNDED", "confirmed-runtime-bounded", "confirmed-runtime", "INFO"),
        finding(root, "S05-PARSER-ODT-BOUNDARY", "parser-smoke-bounded", "bounded", "MAJOR"),
        finding(root, "S05-OLD-PROJECT-PRIOR-ART", "prior-art-bounded", "bounded", "MAJOR"),
        finding(root, "M001-ARCHITECTURE-ONLY-GUARDRAIL", "out-of-scope-guardrail", "excluded", "BLOCKER"),
    ]
    return {
        "schema_version": "s08-final-architecture-findings/v1",
        "generated_at": "2026-05-09T00:00:00Z",
        "source_artifacts": source_artifacts,
        "findings": rows,
    }


def report_markdown(payload: dict[str, Any]) -> str:
    rows = payload["findings"]
    matrix = "\n".join(
        f"| `{row['id']}` | {row['severity']} / {row['status']} | {row['claim_class']} evidence | {row['impact']} | {row['recommendation']} | {row['owner']} | {row['verification_criteria']} | {row['roadmap_effect']} |"
        for row in rows
    )
    ids = ", ".join(row["id"] for row in rows)
    return f"""
# 5. Final Architecture Review: M001 Closure

> Source of truth: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, validated against `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`.
> M001 is architecture-only and does not ship product ETL or production runtime behavior.

## 1. Executive verdict
The handoff gates are {ids}. Owner, resolution, verification, and roadmap fields remain machine-readable.

## 2. Evidence inventory
S04 is bounded runtime evidence, S05 is parser-smoke-bounded evidence, S09/S10 preserve local/open-weight embedding evidence, and S07 is prd-fixed evidence.

## 3. Findings matrix
| ID | Severity / status | Evidence | Impact | Recommendation | Owner | Verification | Roadmap effect |
|---|---|---|---|---|---|---|---|
{matrix}

## 4. Roadmap corrections for M002-M007
M002-M007 must preserve G-005, G-008, G-011, and G-015 proof gates.

## 5. Machine-readable findings path and schema proposal
Current row artifact: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`
Current schema artifact: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`
Proposed durable future path: `prd/findings/architecture-findings.v1.json`
Proposed durable future schema path: `prd/findings/architecture-findings.v1.schema.json`
Required row fields include owner, resolution_path, verification_criteria, roadmap_effect, and requirement_links.

## 6. Non-goals and overclaim guardrails
No product ETL has been implemented. No final ODT parser readiness is claimed. No production retrieval quality is claimed. No direct LegalGraph GraphBLAS control-surface proof is claimed. No managed embedding API fallback is allowed.

## 7. Cold-reader action checklist
A planner checks owner, resolution, verification, roadmap, machine-readable evidence, and bounded claim class before closing a row.
"""


def write_fixture(root: Path, payload: dict[str, Any] | None = None) -> tuple[Path, Path, Path, dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    selected = findings_payload(root) if payload is None else payload
    report = root / "report.md"
    findings = root / "findings.json"
    schema = root / "schema.json"
    report.write_text(report_markdown(selected), encoding="utf-8")
    findings.write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")
    schema.write_text(json.dumps(schema_payload(), ensure_ascii=False), encoding="utf-8")
    return report, findings, schema, selected


def test_accepts_complete_report_findings_and_schema(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, _ = write_fixture(tmp_path)

    result = verifier.verify(report, findings, schema)

    assert result.ok is True
    assert result.errors == []


def test_cli_accepts_complete_fixture(tmp_path: Path) -> None:
    report, findings, schema, _ = write_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_PATH),
            "--report",
            str(report),
            "--findings",
            str(findings),
            "--schema",
            str(schema),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "S08 final architecture report verification passed" in result.stdout


def test_rejects_missing_required_row_field(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, payload = write_fixture(tmp_path)
    del payload["findings"][0]["owner"]
    findings.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("missing required field: owner" in error for error in result.errors)


def test_rejects_missing_required_gate_id(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, payload = write_fixture(tmp_path)
    payload["findings"] = [row for row in payload["findings"] if row["id"] != "G-008"]
    findings.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    report.write_text(report_markdown(payload), encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("missing required finding ID: G-008" in error for error in result.errors)


def test_rejects_missing_requirement_coverage(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, payload = write_fixture(tmp_path)
    payload["findings"][1]["requirement_links"] = ["R001", "R009"]
    findings.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("G-005 missing required requirement link: R010" in error for error in result.errors)


def test_rejects_nonexistent_artifact_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, payload = write_fixture(tmp_path)
    payload["source_artifacts"]["s04_falkordb_smoke"] = "evidence/missing-s04.json"
    findings.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("source_artifacts.s04_falkordb_smoke path does not exist" in error for error in result.errors)


def test_rejects_malformed_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, _ = write_fixture(tmp_path)
    findings.write_text("{not json", encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("findings JSON invalid JSON" in error for error in result.errors)


def test_rejects_missing_report_section(tmp_path: Path) -> None:
    verifier = load_verifier()
    report, findings, schema, _ = write_fixture(tmp_path)
    report.write_text(report.read_text(encoding="utf-8").replace("## 5. Machine-readable findings path and schema proposal", "## 5. Other"), encoding="utf-8")

    result = verifier.verify(report, findings, schema)

    assert result.ok is False
    assert any("report missing section: ## 5. Machine-readable findings path and schema proposal" in error for error in result.errors)


def test_rejects_overclaim_phrases_even_when_rows_are_otherwise_valid(tmp_path: Path) -> None:
    verifier = load_verifier()
    overclaims = [
        "Product ETL is ready for production import.",
        "The final ODT parser is ready for product extraction.",
        "Production retrieval quality is proven for legal answers.",
        "Direct LegalGraph GraphBLAS control-surface proof is confirmed.",
        "Managed embedding API fallback is promoted for M002.",
    ]
    for phrase in overclaims:
        report, findings, schema, payload = write_fixture(tmp_path / phrase.split()[0].lower(), deepcopy(findings_payload(tmp_path / phrase.split()[0].lower())))
        report.write_text(report_markdown(payload) + f"\n{phrase}\n", encoding="utf-8")

        result = verifier.verify(report, findings, schema)

        assert result.ok is False, phrase
        assert any("overclaim" in error.lower() for error in result.errors), result.errors
