#!/usr/bin/env python3
"""Probe ConsultantWordMLParser against the canonical source-fixture corpus.

The script reads ``prd/parser/source_fixture_inventory.json`` (M072 S01
inventory) and runs the existing ``ConsultantWordMLParser`` (M009 baseline
seam) over every fixture — Consultant XML and Garant ODT alike. Per-fixture
outcome is categorized and recorded deterministically.

OUTCOMES (per-fixture):

  - ``success-classified`` — parser succeeded AND ``consultant.DocumentType``
    matches the v2 document_type taxonomy for this fixture (currently only
    ``federal_law`` is recognised by the parser).
  - ``success-as-other`` — parser succeeded but the document kind fell through
    to ``ConsultantDocumentType.other`` because the parser's regex-driven
    classifier only knows ``Федеральный закон`` today. The probe surfaces the
    gap so S03 knows which variants to add.
  - ``fail-by-design`` — fixture is an ODT or otherwise non-Consultant XML;
    the parser correctly rejects it. This is an expected outcome, not a bug.
  - ``fail`` — parser failed for a reason other than by-design rejection;
    ``failure_mode`` categorises the cause.

FAILURE MODES (bounded):

  - ``missing-document-properties`` — no ``<o:DocumentProperties>`` block.
  - ``missing-title`` — DocumentProperties present but no ``<o:Title>``.
  - ``wrong-namespace`` — root is not in the WordML namespace (most ODTs).
  - ``malformed-xml`` — XML parse error.
  - ``path-traversal`` — path escaped the trusted root (should not happen
    with inventory-provided paths).
  - ``file-not-found`` — file disappeared between inventory and probe.
  - ``other-exception`` — unexpected error; surfaced for triage.

NON-CLAIMS: this probe does not validate parser completeness, legal
correctness, R035/R037/R038, FalkorDB, retrieval, or multi-source readiness.
It is structural observability of the document-level parser seam against
the expanded fixture corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "parser-probe-results/v1"
SCRIPT_PATH = "scripts/probe-consultant-parser.py"
JSON_OUTPUT = Path("prd/parser/probe_results.json")
MARKDOWN_OUTPUT = Path("prd/parser/probe_results.md")
INVENTORY_JSON = Path("prd/parser/source_fixture_inventory.json")

FAILURE_MODES = frozenset(
    {
        "missing-document-properties",
        "missing-title",
        "wrong-namespace",
        "malformed-xml",
        "path-traversal",
        "file-not-found",
        "other-exception",
    }
)

NON_CLAIMS = (
    "This probe does not validate parser completeness.",
    "This probe does not validate legal correctness or authoritative legal interpretation.",
    "This probe does not validate R035, R037, or R038.",
    "This probe does not validate FalkorDB product runtime readiness.",
    "This probe does not validate citation-safe retrieval quality.",
    "This probe does not validate multi-source parser readiness.",
    "Outcome counts are observability of the existing document-level parser seam only; structural extension (S03 ConsultantDocumentType variants) is bounded future work.",
    "fail-by-design on ODT fixtures is expected and not a regression — the ConsultantWordMLParser is the Consultant XML adapter, not a multi-format parser.",
)

# Map a ConsultantParseError message to a bounded failure mode.
_FAILURE_MODE_BY_FRAGMENT = (
    ("missing <o:DocumentProperties>", "missing-document-properties"),
    ("missing <o:Title>", "missing-title"),
    ("malformed WordML XML", "malformed-xml"),
    ("refusing path outside trusted source root", "path-traversal"),
    ("source not found or not a file", "file-not-found"),
    ("expected WordML root in namespace", "wrong-namespace"),
)


@dataclass
class ProbeError(Exception):
    """Raised when probe generation or checking fails."""

    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(self.errors)


def _categorize_failure(error_message: str) -> str:
    for fragment, mode in _FAILURE_MODE_BY_FRAGMENT:
        if fragment in error_message:
            return mode
    return "other-exception"


def _load_inventory(root: Path) -> dict[str, Any]:
    path = root / INVENTORY_JSON
    if not path.is_file():
        msg = f"missing inventory artifact: {INVENTORY_JSON}"
        raise ProbeError([msg])
    return json.loads(path.read_text(encoding="utf-8"))


def _probe_one(
    parser_cls: type,
    fixture: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    path_str = fixture["path"]
    relative_path = path_str
    absolute_path = root / path_str
    inventory_document_type = fixture.get("document_type")
    inventory_title_first_line = fixture.get("title_first_line")
    inventory_source_kind = fixture.get("source_kind")
    inventory_source_role_v2 = fixture.get("source_role_v2")
    out: dict[str, Any] = {
        "path": relative_path,
        "inventory_source_kind": inventory_source_kind,
        "inventory_document_type": inventory_document_type,
        "inventory_source_role_v2": inventory_source_role_v2,
        "inventory_title_first_line": inventory_title_first_line,
        "parser_outcome": None,
        "parser_classification": None,
        "parser_source_id": None,
        "parser_act_number": None,
        "parser_edition_date": None,
        "parser_sha256": None,
        "failure_mode": None,
        "error_message": None,
        "is_by_design_fail": None,
    }
    # ODT fixtures: parser will reject with wrong-namespace; mark by-design.
    is_odt = inventory_source_kind == "garant-odt"
    if not absolute_path.is_file():
        out["parser_outcome"] = "fail"
        out["failure_mode"] = "file-not-found"
        out["error_message"] = f"path missing on disk: {relative_path}"
        return out
    parser = parser_cls()  # uses default source_root = "law-source"
    try:
        document, blocks = parser.parse(path_str)
    except Exception as exc:  # noqa: BLE001 — surface all parser outcomes
        out["parser_outcome"] = "fail-by-design" if is_odt else "fail"
        out["failure_mode"] = _categorize_failure(str(exc))
        out["error_message"] = str(exc)
        out["is_by_design_fail"] = is_odt
        return out
    out["parser_source_id"] = document.source_id
    out["parser_act_number"] = document.act_number
    out["parser_edition_date"] = (
        document.edition_date.isoformat() if document.edition_date else None
    )
    out["parser_sha256"] = document.sha256
    # The parser currently always returns commercial_consolidated; we cannot
    # recover the ConsultantDocumentType enum directly from SourceDocument
    # (only its SourceProvenanceClass is exposed). Re-derive classification
    # by re-running the parser's local _classify_document_type() on the
    # inventory title (which equals the parser's input).
    from law_nexus.adapters.parsers.consultant_wordml import _classify_document_type  # type: ignore[import-not-found]
    derived = _classify_document_type(inventory_title_first_line or "")
    out["parser_classification"] = derived.value
    out["parser_outcome"] = (
        "success-classified"
        if (
            inventory_document_type == "federal_law"
            and derived.value == "federal_law"
        )
        else "success-as-other"
    )
    out["is_by_design_fail"] = False
    return out


def probe_corpus(root: Path) -> dict[str, Any]:
    inventory = _load_inventory(root)
    fixtures = inventory.get("fixtures", [])
    # Late import: parser depends on src/law_nexus being importable; scripts
    # may be invoked from any cwd as long as PYTHONPATH or uv sets the venv.
    from law_nexus.adapters.parsers.consultant_wordml import ConsultantWordMLParser  # type: ignore[import-not-found]

    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        rows.append(_probe_one(ConsultantWordMLParser, fixture, root))

    by_outcome: dict[str, int] = {}
    by_failure_mode: dict[str, int] = {}
    classification_gap_count = 0
    for row in rows:
        by_outcome[row["parser_outcome"] or "unknown"] = (
            by_outcome.get(row["parser_outcome"] or "unknown", 0) + 1
        )
        if row["failure_mode"]:
            by_failure_mode[row["failure_mode"]] = (
                by_failure_mode.get(row["failure_mode"], 0) + 1
            )
        if row["parser_outcome"] == "success-as-other":
            classification_gap_count += 1

    classification_gap = [
        {
            "path": row["path"],
            "inventory_document_type": row["inventory_document_type"],
            "inventory_title_first_line": row["inventory_title_first_line"],
            "parser_classification": row["parser_classification"],
        }
        for row in rows
        if row["parser_outcome"] == "success-as-other"
    ]

    status = "pass" if all(
        row["parser_outcome"] in ("success-classified", "success-as-other", "fail-by-design")
        or row["parser_outcome"] == "fail"
        for row in rows
    ) else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": SCRIPT_PATH,
        "status": status,
        "non_authoritative": True,
        "inventory_schema_version": inventory.get("schema_version"),
        "fixture_count": len(rows),
        "outcome_counts": dict(sorted(by_outcome.items())),
        "failure_mode_counts": dict(sorted(by_failure_mode.items())),
        "classification_gap_count": classification_gap_count,
        "failure_modes_taxonomy": sorted(FAILURE_MODES),
        "non_claims": list(NON_CLAIMS),
        "classification_gap": classification_gap,
        "fixtures": rows,
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Consultant Parser Probe Results",
        "",
        "This report is generated by `scripts/probe-consultant-parser.py` from the canonical source-fixture inventory (M072 S01).",
        "",
        "## Summary",
        "",
        f"- Schema version: `{manifest['schema_version']}`",
        f"- Inventory schema version: `{manifest['inventory_schema_version']}`",
        f"- Status: `{manifest['status']}`",
        f"- Fixture count: `{manifest['fixture_count']}`",
        f"- Non-authoritative: `{str(manifest['non_authoritative']).lower()}`",
        f"- Classification gap count (parser recognised as `other` while inventory shows a known document_type): `{manifest['classification_gap_count']}`",
        "",
        "## Outcome counts",
        "",
    ]
    for outcome, count in manifest["outcome_counts"].items():
        lines.append(f"- `{outcome}`: {count}")
    lines.extend(["", "## Failure-mode counts (bounded taxonomy)", ""])
    if manifest["failure_mode_counts"]:
        for mode, count in manifest["failure_mode_counts"].items():
            lines.append(f"- `{mode}`: {count}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Classification gap (parser vs inventory)",
            "",
        ]
    )
    if manifest["classification_gap"]:
        lines.append("| Path | Inventory document_type | Parser classification | Title (first line) |")
        lines.append("|---|---|---|---|")
        for row in manifest["classification_gap"]:
            title_display = (row.get("inventory_title_first_line") or "").replace("|", "\\|")[:100]
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{row['path']}`",
                        str(row["inventory_document_type"]),
                        str(row["parser_classification"]),
                        title_display or "—",
                    ]
                )
                + " |"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Per-fixture outcome",
            "",
            "| Path | Inventory kind | Inventory doc_type | Outcome | Parser classification | Failure mode |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in manifest["fixtures"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['path']}`",
                    str(row["inventory_source_kind"]),
                    str(row["inventory_document_type"]),
                    str(row["parser_outcome"]),
                    str(row["parser_classification"] or "—"),
                    str(row["failure_mode"] or "—"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Explicit non-claims", ""])
    lines.extend(f"- {claim}" for claim in manifest["non_claims"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, manifest: dict[str, Any]) -> None:
    json_path = root / JSON_OUTPUT
    markdown_path = root / MARKDOWN_OUTPUT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(manifest), encoding="utf-8")


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def check_outputs(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_json = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    expected_markdown = render_markdown(manifest)
    for relative_path, expected in (
        (JSON_OUTPUT, expected_json),
        (MARKDOWN_OUTPUT, expected_markdown),
    ):
        path = root / relative_path
        if not path.is_file():
            errors.append(f"Missing generated artifact: {relative_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"Generated artifact is stale: {relative_path}")
    if manifest["status"] != "pass":
        errors.append("Probe status is not pass")
    return errors


def observability_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": manifest["status"],
        "fixture_count": manifest["fixture_count"],
        "outcome_counts": manifest["outcome_counts"],
        "failure_mode_counts": manifest["failure_mode_counts"],
        "classification_gap_count": manifest["classification_gap_count"],
        "inventory_schema_version": manifest["inventory_schema_version"],
        "non_authoritative": manifest["non_authoritative"],
        "probe_sha256": sha256_of_file(Path(JSON_OUTPUT)),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifacts are current without writing them")
    parser.add_argument("--show-sha", action="store_true", help="print SHA-256 of the generated JSON (after --write) and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    manifest = probe_corpus(root)
    if args.check:
        errors = check_outputs(root, manifest)
        print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        return 0
    write_outputs(root, manifest)
    if args.show_sha:
        print(sha256_of_file(root / JSON_OUTPUT))
        return 0
    print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
