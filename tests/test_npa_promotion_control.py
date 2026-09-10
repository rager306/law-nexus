from __future__ import annotations

import hashlib
import json
from pathlib import Path

from law_nexus_harness.governor import (
    _npa_promotion_binding,
    check_npa_promotion_control,
)


def _write_contract(root: Path) -> dict[str, object]:
    gates = {
        "revision_binding": {"binding_inputs": ["inputs.txt"]},
        "forbidden_promotions": [
            {"scope": "system"},
            {"scope": "all"},
            {"without_human_gate": True},
        ],
        "requirement_transitions": {
            "debt": [
                {"requirement": "R035", "remaining": "open gate items"},
                {"requirement": "R070", "remaining": "uncovered editions"},
            ]
        },
    }
    (root / "prd/architecture").mkdir(parents=True)
    (root / "prd/architecture/npa-promotion-gates.json").write_text(
        json.dumps(gates), encoding="utf-8"
    )
    (root / "inputs.txt").write_text("binding fixture\n", encoding="utf-8")
    return gates


def _write_receipt(root: Path, receipt: dict[str, object]) -> None:
    path = root / "prd/migration/rust-evidence/m203-s09-promotion-receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")


def test_missing_receipts_passes_and_reports_explicit_debt(tmp_path: Path) -> None:
    _write_contract(tmp_path)

    finding = check_npa_promotion_control(tmp_path)[0]

    assert finding.status == "pass"
    assert "R035: open gate items" in finding.observed
    assert "R070: uncovered editions" in finding.observed


def test_blocked_receipt_is_not_a_promotion_claim(tmp_path: Path) -> None:
    _write_contract(tmp_path)
    _write_receipt(tmp_path, {"outcome": "blocked-stale"})

    finding = check_npa_promotion_control(tmp_path)[0]

    assert finding.status == "pass"
    assert "remaining_debt=R035" in finding.observed


def test_stale_revision_binding_fails_closed(tmp_path: Path) -> None:
    _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        {
            "outcome": "promoted",
            "capability": "parsing",
            "corpus_scope": "C2-bounded",
            "revision_binding": "0" * 64,
            "human_acceptance": {"evidence_anchor": "board#1"},
        },
    )

    finding = check_npa_promotion_control(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "error"
    assert "stale-revision-binding" in finding.observed


def test_promoted_without_anchored_human_gate_fails_closed(tmp_path: Path) -> None:
    _write_contract(tmp_path)
    binding = _npa_promotion_binding(tmp_path, ["inputs.txt"])
    _write_receipt(
        tmp_path,
        {
            "outcome": "promoted",
            "capability": "parsing",
            "corpus_scope": "C2-bounded",
            "revision_binding": binding,
            "human_acceptance": None,
        },
    )

    finding = check_npa_promotion_control(tmp_path)[0]

    assert finding.status == "fail"
    assert "promoted-without-human-gate" in finding.observed


def test_system_and_empty_scope_are_scope_smoothed(tmp_path: Path) -> None:
    _write_contract(tmp_path)
    binding = _npa_promotion_binding(tmp_path, ["inputs.txt"])
    for scope, capability in [("C2-bounded", "system"), ("", "parsing")]:
        _write_receipt(
            tmp_path,
            {
                "outcome": "promoted",
                "capability": capability,
                "corpus_scope": scope,
                "revision_binding": binding,
                "human_acceptance": {"evidence_anchor": "board#1"},
            },
        )
        finding = check_npa_promotion_control(tmp_path)[0]
        assert finding.status == "fail"
        assert "scope-smoothed" in finding.observed


def test_sha256_over_sha256_lines_vector() -> None:
    root = Path(".")
    digests = [
        hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in sorted(["README.md", "pyproject.toml"])
    ]
    expected = hashlib.sha256("".join(f"{digest}\n" for digest in digests).encode()).hexdigest()

    assert _npa_promotion_binding(root, ["README.md", "pyproject.toml"]) == expected
