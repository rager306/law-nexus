from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/verify-s05-odt-parser.py"

REQUIRED_OLD_PROJECT_PATHS = [
    "Old_project/structures/44fz.yaml",
    "Old_project/parsing_prompt.yaml",
    "Old_project/validation/structural_rules.yaml",
    "Old_project/validation/semantic_rules.yaml",
    "Old_project/contracts/api.yaml",
    "Old_project/contracts/extractor-api.md",
    "Old_project/sources/consultant_word2003xml.yaml",
]


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s05_odt_parser", VERIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_required_old_project_files(root: Path) -> None:
    for relative_path in REQUIRED_OLD_PROJECT_PATHS:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("prior art fixture only\n", encoding="utf-8")


def probe_payload(*, odfpy_status: str = "loaded-temp-clean-manifest", alternative_status: str = "loaded-unmodified") -> dict[str, Any]:
    return {
        "schema_version": "s05-raw-odt-baseline/v1",
        "probe_log_path": ".gsd/milestones/M001/slices/S05/probe-log.json",
        "probe_count": 3,
        "statuses": {
            "raw-baseline": "verified-source-evidence",
            "odfpy": odfpy_status,
            "odfdo": alternative_status,
        },
        "probes": [
            {
                "parser": "raw-baseline",
                "status": "verified-source-evidence",
                "evidence_class": "verified-source-evidence",
                "issue_ids": ["S05-raw-odt-baseline"],
                "source": {
                    "path": "law-source/garant/44-fz.odt",
                    "sha256": "a" * 64,
                    "size_bytes": 123,
                    "is_default_real_source": True,
                },
                "required_real_source": "law-source/garant/44-fz.odt",
                "raw_odt_observations": {"ordered_block_count": 10},
                "parser_direction_claims_authoritative": False,
            },
            {
                "parser": "odfpy",
                "status": odfpy_status,
                "evidence_class": "parser-comparison-evidence",
                "issue_ids": [f"S05-optional-odfpy-{odfpy_status}"],
                "phases": {"unmodified": {"status": "failed-unmodified-load"}},
                "parser_direction_claims_authoritative": False,
            },
            {
                "parser": "odfdo",
                "status": alternative_status,
                "evidence_class": "parser-comparison-evidence",
                "issue_ids": [f"S05-optional-odfdo-{alternative_status}"],
                "parser_direction_claims_authoritative": False,
            },
        ],
    }


def findings_markdown(*, old_project_table: bool = True, issue_owner: str = "S05", alternative_blocked: bool = False) -> str:
    comparison_note = (
        "Alternative parser comparison is BLOCKED because odfdo is not installed; resolution path: "
        "S05 owner installs odfdo or records an explicit parser alternative before S06."
        if alternative_blocked
        else "Alternative parser comparison is complete for smoke-only parser-comparison evidence."
    )
    legacy_rows = "\n".join(
        f"| {path} | adapt/defer | S01 | Re-check against S05 probe log before reuse | Verify in S06/S07 before product ETL |"
        for path in REQUIRED_OLD_PROJECT_PATHS
    )
    legacy_table = (
        "| Candidate | Classification | Owner | Resolution path | Verification criterion |\n"
        "|---|---|---|---|---|\n"
        f"{legacy_rows}\n"
        if old_project_table
        else ""
    )
    return f"""
# S05 ODT Parser Findings

## Parser direction
Raw content.xml remains the ordering oracle. odfpy is not accepted as the sole parser because the unmodified-load phase failed on the real manifest; it is controlled comparison evidence only. {comparison_note}

## Real ODT evidence
The probe log records real source path `law-source/garant/44-fz.odt`, SHA-256, source size, raw verified-source-evidence, odfpy status, alternative parser status, issue IDs, and normalized `.gsd/milestones/M001/slices/S05/probe-log.json` artifact path.

## Old_project reuse classification
Old_project is prior art only; no product ETL claims are made.

{legacy_table}
## Issues
| Issue ID | Owner | Resolution path | Verification criterion |
|---|---|---|---|
| S05-raw-odt-baseline | S05 | Preserve raw source probe log | Probe verifier passes against real source metadata |
| S05-optional-odfpy-loaded-temp-clean-manifest | {issue_owner} | Keep odfpy as controlled comparison; do not select as sole parser until unmodified load is resolved | Verifier rejects sole-parser acceptance and records manifest issue |
| S05-optional-odfdo-loaded-unmodified | S05 | Carry odfdo/alternative status into parser decision | S06/S07 cite this verifier output before parser direction |
| S05-optional-odfdo-not-installed | S05 | Install odfdo or record another explicit alternative before parser selection | Verifier permits not-installed only with an explicit comparison hold and resolution path |

## Owners
Every parser issue and reusable legacy candidate has an owner in the tables above.

## Resolution paths
Every issue and candidate has a resolution path in the tables above.

## Verification criteria
Every issue and candidate has a verification criterion in the tables above.
"""


def write_probe(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_accepts_complete_probe_and_findings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_required_old_project_files(tmp_path)
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, probe_payload())
    findings.write_text(findings_markdown(), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is True
    assert result.errors == []


def test_rejects_invalid_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    probe.write_text("{not json", encoding="utf-8")
    findings.write_text(findings_markdown(), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("Probe JSON log is invalid" in error for error in result.errors)


def test_rejects_missing_real_source_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = probe_payload()
    payload["probes"][0]["source"]["path"] = "tmp/fixture.odt"  # type: ignore[index]
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, payload)
    findings.write_text(findings_markdown(), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("real source path law-source/garant/44-fz.odt" in error for error in result.errors)


def test_rejects_missing_odfpy_or_alternative_status(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = probe_payload()
    del payload["statuses"]["odfpy"]  # type: ignore[index]
    payload["probes"] = [payload["probes"][0], payload["probes"][2]]  # type: ignore[index]
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, payload)
    findings.write_text(findings_markdown(), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("odfpy" in error and "missing" in error for error in result.errors)


def test_rejects_missing_old_project_table(tmp_path: Path) -> None:
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, probe_payload())
    findings.write_text(findings_markdown(old_project_table=False), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("Old_project" in error and "table" in error for error in result.errors)


def test_rejects_issue_rows_without_owner_resolution_or_verifier(tmp_path: Path) -> None:
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, probe_payload())
    findings.write_text(findings_markdown(issue_owner=""), encoding="utf-8")

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("issue S05-optional-odfpy-loaded-temp-clean-manifest" in error for error in result.errors)


def test_rejects_odfpy_as_sole_parser_after_unmodified_failure(tmp_path: Path) -> None:
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, probe_payload())
    findings.write_text(
        findings_markdown().replace(
            "odfpy is not accepted as the sole parser",
            "odfpy is accepted as the sole parser",
        ),
        encoding="utf-8",
    )

    result = verifier.verify(findings, probe)

    assert result.ok is False
    assert any("odfpy" in error and "sole parser" in error for error in result.errors)


def test_allows_not_installed_alternative_only_with_blocked_resolution(tmp_path: Path) -> None:
    verifier = load_verifier()
    probe = tmp_path / "probe.json"
    findings = tmp_path / "findings.md"
    write_probe(probe, probe_payload(alternative_status="not-installed"))
    findings.write_text(findings_markdown(alternative_blocked=False), encoding="utf-8")

    missing_blocked = verifier.verify(findings, probe)

    findings.write_text(findings_markdown(alternative_blocked=True), encoding="utf-8")
    blocked_with_resolution = verifier.verify(findings, probe)

    assert any("alternative parser is not-installed" in error for error in missing_blocked.errors)
    assert blocked_with_resolution.ok is True
