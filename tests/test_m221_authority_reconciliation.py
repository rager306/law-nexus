"""Guard for the M221/S05 design-only documentation reconciliation pin.

The pin at ``prd/architecture/m221-s05-docs-reconciliation.yaml`` is the
machine-checkable spine of the F06 closure: it records that the four cold
authority surfaces are reconciled with the *bounded* M211 Rust runtime without
any lifecycle promotion, requirement closure, or corpus-wide/semantic claim.

Invariants enforced here:

* the pin stays non-authoritative and human-adoption-pending;
* the pinned ADR owner and consumed schema are stable;
* every ``source_bindings`` entry resolves to a local tracked file whose
  sha256 still matches, and none of those entries pins a surface this slice
  edits (a pinned mutable surface would break on the very next edit);
* the contract is fail-closed: corrupting a hash, flipping ``authoritative``
  to true, or promoting ``human_adoption`` to adopted is a failure.

The test reads only local tracked files in ``prd/architecture`` and
``prd/migration/rust-evidence``; there is no network access.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = REPO_ROOT / "prd" / "architecture" / "m221-s05-docs-reconciliation.yaml"

SCHEMA = "law-nexus/m221-s05-docs-reconciliation/v1"

# Surfaces this slice edits (T02/T04). The pin MUST NOT hash any of these:
# a sha256 over a surface edited in the same slice is guaranteed to drift.
EDITABLE_SURFACES = frozenset(
    {
        "prd/ARCHITECTURE.md",
        "doc/adr/0029-requisites-anchored-member-assembly-fsm.md",
        "doc/adr/README.md",
        "README.md",
        "doc/adr-architecture-cross-matrix.md",
        "assessment/34-rust-npa-foundation-readiness-audit.md",
    }
)

# The four cold authority surfaces reconciled in T02. Each must drop the
# stale "no Rust engine code" claim and acknowledge the bounded M211 runtime.
AUTHORITY_SURFACES: dict[str, str] = {
    "adr": "doc/adr/0029-requisites-anchored-member-assembly-fsm.md",
    "architecture": "prd/ARCHITECTURE.md",
    "adr_readme": "doc/adr/README.md",
    "root_readme": "README.md",
}

CROSS_MATRIX = "doc/adr-architecture-cross-matrix.md"

# M173 S02 one-pager budget; a documentation reconciliation may not grow it.
ARCHITECTURE_LINE_BUDGET = 325


class PinContractError(AssertionError):
    """Raised when the reconciliation pin violates its contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PinContractError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _surface_text(relative: str) -> str:
    path = REPO_ROOT / relative
    _require(path.is_file(), f"missing surface: {relative}")
    return path.read_text(encoding="utf-8")


def _load_pin() -> dict[str, Any]:
    loaded = yaml.safe_load(PIN_PATH.read_text(encoding="utf-8"))
    _require(isinstance(loaded, dict), "pin must load as a mapping")
    return loaded


def validate_pin(pin: dict[str, Any]) -> None:
    """Validate the pin contract in memory (raises PinContractError)."""
    _require(pin.get("schema") == SCHEMA, "unexpected pin schema")
    _require(pin.get("lifecycle") == ["proposed"], "lifecycle must stay [proposed]")
    _require(pin.get("authoritative") is False, "authoritative must stay false")
    _require(
        pin.get("human_adoption") == "pending",
        "human_adoption must stay pending",
    )
    _require(pin.get("owner_adr") == "0029", "owner_adr must be 0029")
    _require(pin.get("runtime_stop_active") is True, "runtime_stop_active must be true")
    _require(
        pin.get("consumes") == ["law-nexus/npa-analysis-corpus-acceptance/v2"],
        "pin must consume the v2 corpus-acceptance schema",
    )

    finding = pin.get("finding") or {}
    _require(finding.get("id") == "F06", "finding id must be F06")
    _require(finding.get("class") == "MEDIUM", "finding class must be MEDIUM")
    _require(
        finding.get("disposition") == "closed-bounded-under-S05",
        "finding disposition must be closed-bounded-under-S05",
    )

    _require(bool(pin.get("non_claims")), "non_claims must be non-empty")

    surfaces = pin.get("surfaces") or {}
    for name, spec in surfaces.items():
        _require(isinstance(spec, dict), f"surface {name} must be a mapping")
        _require(
            spec.get("edit") in {"append", "in-place", "none"},
            f"surface {name} has an invalid edit kind",
        )

    for artifact in pin.get("planned_artifacts") or []:
        _require(isinstance(artifact, dict), "planned_artifacts entries must be mappings")
        _require("sha256" not in artifact, "planned artifacts must not carry a hash yet")
        _require(bool(artifact.get("path")), "planned artifacts need a path")


def test_pin_shape_and_contract() -> None:
    validate_pin(_load_pin())


def test_source_bindings_resolve_and_match_disk() -> None:
    pin = _load_pin()
    bindings = pin.get("source_bindings") or []
    _require(bool(bindings), "pin must bind at least one source artifact")
    for binding in bindings:
        rel = binding["path"]
        _require(not rel.startswith("/"), f"absolute path in binding: {rel}")
        _require(".." not in Path(rel).parts, f"parent traversal in binding: {rel}")
        target = REPO_ROOT / rel
        _require(target.is_file(), f"missing source binding: {rel}")
        _require(
            binding["sha256"] == _sha256(target),
            f"sha256 drift for source binding: {rel}",
        )


def test_source_bindings_never_pin_editable_surfaces() -> None:
    pin = _load_pin()
    pinned = {binding["path"] for binding in pin.get("source_bindings") or []}
    overlap = pinned.intersection(EDITABLE_SURFACES)
    _require(not overlap, f"pin hashes editable surface(s): {sorted(overlap)}")


def test_surface_paths_are_local_and_present() -> None:
    pin = _load_pin()
    for name, spec in (pin.get("surfaces") or {}).items():
        rel = spec["path"]
        _require(not rel.startswith("/"), f"absolute surface path: {name}")
        _require(".." not in Path(rel).parts, f"parent traversal in surface: {name}")
        _require((REPO_ROOT / rel).is_file(), f"missing surface: {rel}")


# --- hostile / fail-closed coverage -----------------------------------------


def test_corrupted_source_binding_hash_is_rejected() -> None:
    pin = _load_pin()
    pin["source_bindings"][0]["sha256"] = "0" * 64
    with pytest.raises(PinContractError, match="sha256 drift"):
        # the on-disk recompute is performed by the binding test
        for binding in pin["source_bindings"]:
            target = REPO_ROOT / binding["path"]
            _require(
                binding["sha256"] == _sha256(target),
                f"sha256 drift for source binding: {binding['path']}",
            )


def test_authoritative_true_is_rejected() -> None:
    pin = _load_pin()
    pin["authoritative"] = True
    with pytest.raises(PinContractError, match="authoritative"):
        validate_pin(pin)


def test_human_adoption_adopted_is_rejected() -> None:
    pin = _load_pin()
    pin["human_adoption"] = "adopted"
    with pytest.raises(PinContractError, match="human_adoption"):
        validate_pin(pin)


def test_lifecycle_promotion_is_rejected() -> None:
    pin = _load_pin()
    pin["lifecycle"] = ["adopted"]
    with pytest.raises(PinContractError, match="lifecycle"):
        validate_pin(pin)


def test_pinning_an_editable_surface_is_rejected() -> None:
    pin = _load_pin()
    pin["source_bindings"].append({"path": "prd/ARCHITECTURE.md", "sha256": "0" * 64})
    with pytest.raises(PinContractError, match="editable surface"):
        pinned = {binding["path"] for binding in pin["source_bindings"]}
        overlap = pinned.intersection(EDITABLE_SURFACES)
        _require(not overlap, f"pin hashes editable surface(s): {sorted(overlap)}")


# --- surface reconciliation (T02) -------------------------------------------


def test_no_authority_surface_keeps_stale_no_rust_claim() -> None:
    for name, relative in AUTHORITY_SURFACES.items():
        text = _surface_text(relative)
        _require(
            "no Rust engine code" not in text,
            f"{name} still carries the stale 'no Rust engine code' claim",
        )


def test_adr_0029_status_names_bounded_m211_runtime() -> None:
    normalized = " ".join(_surface_text(AUTHORITY_SURFACES["adr"]).split())
    _require("M211" in normalized, "ADR-0029 Status must cite M211")
    _require("bounded" in normalized.lower(), "ADR-0029 Status must mark the runtime bounded")
    for token in ("npa_anchor", "npa-integration-runner"):
        _require(token in normalized, f"ADR-0029 Status must name {token}")


def test_index_and_root_readme_mention_m211_bounded_runtime() -> None:
    index = " ".join(_surface_text(AUTHORITY_SURFACES["adr_readme"]).split())
    root = " ".join(_surface_text(AUTHORITY_SURFACES["root_readme"]).split())
    for name, text in (("doc/adr/README.md", index), ("README.md", root)):
        _require("M211" in text, f"{name} must mention M211")
        _require("bounded" in text.lower(), f"{name} must mark the runtime bounded")


def test_architecture_page_budget_holds() -> None:
    line_count = len(_surface_text(AUTHORITY_SURFACES["architecture"]).splitlines())
    _require(
        line_count <= ARCHITECTURE_LINE_BUDGET,
        f"prd/ARCHITECTURE.md grew to {line_count} lines (budget {ARCHITECTURE_LINE_BUDGET})",
    )


def test_cross_matrix_companion_points_at_pin() -> None:
    text = _surface_text(CROSS_MATRIX)
    _require(
        "m221-s05-docs-reconciliation.yaml" in text,
        "cross-matrix companion must point at the S05 reconciliation pin",
    )
    _require("M221/S05" in text, "cross-matrix companion must be labelled M221/S05")


def test_adr_matrix_keeps_adr_0029_proposed() -> None:
    from law_nexus_harness.adr_matrix import build_adr_matrix

    rows = {row["adr_id"]: row for row in build_adr_matrix(REPO_ROOT)["rows"]}
    _require("ADR-0029" in rows, "ADR matrix must include ADR-0029")
    row = rows["ADR-0029"]
    _require(row["status_lifecycle"] == "proposed", "ADR-0029 status lifecycle must stay proposed")
    _require(row["oracle_lifecycle"] == "proposed", "ADR-0029 oracle lifecycle must stay proposed")
    _require(row["index_lifecycle"] == "proposed", "ADR-0029 index lifecycle must stay proposed")
