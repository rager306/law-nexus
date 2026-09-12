#!/usr/bin/env python3
"""Closed, additive requirement-evidence classifier for M204/S15.

The classifier reads only the three historical requirement-evidence JSON files,
S14 acceptance and its frozen manifest.  It never reads GSD/DB/projections,
walks the corpus, or changes requirement lifecycle state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s15-requirement-class/v1"
S14 = ROOT / "prd/migration/rust-evidence/m204-s14-c4-acceptance.json"
S14_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s14-frozen-hashes.json"
OUT = ROOT / "prd/migration/rust-evidence/m204-s15-requirement-class.json"
EXPECTED_IDS = ["R038", "R063", "R064", "R081", "R035", "R070", "R066", "R073", "R000", "R999"]
SOURCES = {
    "s06": ROOT / "prd/migration/rust-evidence/m204-s06-requirement-evidence.json",
    "s07": ROOT / "prd/migration/rust-evidence/m204-s07-requirement-evidence.json",
    "s10": ROOT / "prd/migration/rust-evidence/m204-s10-requirement-evidence.json",
}
S14_EXPECTED = {
    "c4_acceptance": "non-pass",
    "classification": "supporting-only",
    "status_effect": "unchanged",
}
ROW_EXPECTED = {
    "R038": ("supporting-only", "source-bound-criterion-plus-c4-gsd-attempt"),
    "R063": ("supporting-only", "process-provenance-without-product-change"),
    "R064": ("supporting-only", "thin-harness-operability-retest"),
    "R081": ("supporting-only", "documentation-residue-no-new-work"),
    "R035": ("hold", "ontology-gate-absent"),
    "R070": ("hold", "edition-provenance-absent"),
    "R066": ("out-of-class", "anti-feature-unrelated-to-c4"),
    "R073": ("out-of-class", "governor-check-specs-unexpanded"),
    "R000": ("reserved-stub", "reserved-stub"),
    "R999": ("reserved-stub", "reserved-stub"),
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


ALLOWED_SURFACES = {rel(path) for path in (*SOURCES.values(), S14, S14_MANIFEST)}


def safe_source(value: str) -> Path:
    path = Path(value)
    banned = {".git", ".gsd", ".planning", ".audits"}
    if (
        path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or any(p in banned for p in path.parts)
    ):
        raise ValueError(f"unsafe source path: {value}")
    candidate = ROOT / path
    if any(part.is_symlink() for part in [ROOT, *candidate.parents, candidate] if part.exists()):
        raise ValueError(f"symlink source path: {value}")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate or not resolved.is_file():
        raise ValueError(f"source is not a regular repository file: {value}")
    return resolved


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def obj(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected object")
    return value


def verify_s15_manifest() -> None:
    manifest = obj(
        load(ROOT / "prd/migration/rust-evidence/m204-s15-frozen-hashes.json"),
        "S15 frozen manifest",
    )
    if (
        manifest.get("schema") != "law-nexus/m204-s15-frozen-hashes/v1"
        or manifest.get("scope")
        != "S15 additive classifier; frozen tracked evidence only; no corpus walk"
    ):
        raise ValueError("S15 manifest schema or scope mismatch")
    rows = manifest.get("files")
    expected = {rel(path) for path in (*SOURCES.values(), S14, S14_MANIFEST)}
    if (
        not isinstance(rows, list)
        or {obj(row, "S15 manifest row").get("path") for row in rows} != expected
    ):
        raise ValueError("S15 manifest pin set mismatch")
    for row in rows:
        row = obj(row, "S15 manifest row")
        source = safe_source(row["path"])
        if row.get("sha256") != digest(source) or row.get("size_bytes") != source.stat().st_size:
            raise ValueError(f"S15 frozen source drift: {row.get('path')}")


def verify_s14() -> dict[str, Any]:
    value = obj(load(S14), "S14 acceptance")
    for key, expected in S14_EXPECTED.items():
        if value.get(key) != expected:
            raise ValueError(f"S14 {key} is not {expected}")
    if value.get("s14_called_validate_milestone") is not False:
        raise ValueError("S14 lifecycle claim is not false")
    manifest = obj(load(S14_MANIFEST), "S14 frozen manifest")
    if manifest.get("schema") != "law-nexus/m204-s14-frozen-hashes/v1":
        raise ValueError("S14 manifest schema mismatch")
    for row in manifest.get("files", []):
        row = obj(row, "S14 manifest row")
        source = safe_source(row["path"])
        if row.get("sha256") != digest(source) or row.get("size_bytes") != source.stat().st_size:
            raise ValueError(f"S14 frozen source drift: {row.get('path')}")
    command = ["uv", "run", "python", "scripts/m204_s14_polarity.py", "classify"]
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("S14 classify timed out") from exc
    if completed.returncode != 0:
        raise ValueError(f"S14 classify failed: {completed.stderr.strip()}")
    if completed.stderr or not completed.stdout.strip():
        raise ValueError("S14 classify was not strict JSON output")
    result = obj(json.loads(completed.stdout), "S14 classify output")
    if result != {
        "integrity": "pass",
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
    }:
        raise ValueError("S14 classify polarity mismatch")
    return value


def source_surface(path: Path) -> dict[str, str]:
    return {"path": rel(path), "sha256": digest(path)}


def find_row(doc: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    rows = doc.get("requirements") if "requirements" in doc else doc.get("rows")
    if not isinstance(rows, list):
        raise ValueError("historical requirement rows missing")
    found = [
        obj(row, "requirement row")
        for row in rows
        if row.get("requirement_id", row.get("requirement")) == requirement_id
    ]
    if len(found) != 1:
        raise ValueError(f"{requirement_id}: expected exactly one historical row")
    return found[0]


def historical() -> dict[str, dict[str, Any]]:
    docs = {name: obj(load(path), name) for name, path in SOURCES.items()}
    s06_ids = [find_row(docs["s06"], rid) for rid in EXPECTED_IDS[:4]]
    s07_ids = [find_row(docs["s07"], rid) for rid in EXPECTED_IDS[:4]]
    s10_ids = [find_row(docs["s10"], rid) for rid in EXPECTED_IDS[:4]]
    if docs["s07"].get("predecessor", {}).get("path") != rel(SOURCES["s06"]):
        raise ValueError("S07 predecessor path does not pin S06")
    if docs["s07"]["predecessor"].get("sha256") != digest(SOURCES["s06"]):
        raise ValueError("S07 predecessor hash does not pin S06")
    for rows in (s06_ids, s07_ids):
        if any(row.get("disposition") != "supporting-only" for row in rows):
            raise ValueError("historical evidence is not supporting-only")
    if any(
        not isinstance(row.get("disposition"), str)
        or not row["disposition"].startswith("supporting-only")
        for row in s10_ids
    ):
        raise ValueError("S10 historical evidence is not supporting-only")
    if any(row.get("status_effect", "").startswith("unchanged") is False for row in s06_ids):
        raise ValueError("S06 status effect drift")
    if any(row.get("status_effect") != "unchanged" for row in s07_ids):
        raise ValueError("S07 status effect drift")
    if any("status_effect" in row for row in s10_ids):
        raise ValueError("S10 unexpectedly invents status_effect")
    if docs["s10"].get("hold_requirements") != ["R035", "R070"]:
        raise ValueError("S10 hold requirements drift")
    return docs


def classify() -> dict[str, Any]:
    verify_s15_manifest()
    s14 = verify_s14()
    docs = historical()
    surfaces = [source_surface(path) for path in (*SOURCES.values(), S14, S14_MANIFEST)]
    limits = {
        "R038": "supports criterion and attempted run only; no operational pass",
        "R063": "supports process provenance only; not product composition proof",
        "R064": "supports thin-harness operability retest only; no engine repair",
        "R081": "documentation residue only; not Work identity proof",
        "R035": "HOLD and no ontology-gate evidence",
        "R070": "HOLD and no edition-provenance evidence",
        "R066": "unrelated anti-feature evidence; no C4 class match",
        "R073": "governor-check specs remain unexpanded",
        "R000": "reserved stub; not a real requirement",
        "R999": "reserved stub; not a real requirement",
    }
    classes = {
        "R038": ("supporting-only", "source-bound-criterion-plus-c4-gsd-attempt"),
        "R063": ("supporting-only", "process-provenance-without-product-change"),
        "R064": ("supporting-only", "thin-harness-operability-retest"),
        "R081": ("supporting-only", "documentation-residue-no-new-work"),
        "R035": ("hold", "ontology-gate-absent"),
        "R070": ("hold", "edition-provenance-absent"),
        "R066": ("out-of-class", "anti-feature-unrelated-to-c4"),
        "R073": ("out-of-class", "governor-check-specs-unexpanded"),
        "R000": ("reserved-stub", "reserved-stub"),
        "R999": ("reserved-stub", "reserved-stub"),
    }
    rows = []
    for rid in EXPECTED_IDS:
        kind, evidence_class = classes[rid]
        rows.append(
            {
                "requirement_id": rid,
                "coverage_kind": kind,
                "evidence_class": evidence_class,
                "class_matched": False,
                "status_effect": "unchanged",
                "source_surfaces": surfaces,
                "limitations": [limits[rid]],
            }
        )
    result = {
        "schema": SCHEMA,
        "c4_acceptance": s14["c4_acceptance"],
        "classification": s14["classification"],
        "status_effect": "unchanged",
        "class_matched_ids": [],
        "s15_called_validate_milestone": False,
        "s15_called_requirement_update": False,
        "engine_status": {
            "engine_fix": docs["s10"]["engine_status"]["engine_fix"],
            "upstream_issue": docs["s10"]["engine_status"]["upstream_issue"],
        },
        "open_findings": docs["s10"]["open_findings"],
        "predecessor_pins": {"path": rel(SOURCES["s06"]), "sha256": digest(SOURCES["s06"])},
        "rows": rows,
    }
    validate(result)
    return result


def _check_claim_text(text: Any, label: str) -> None:
    if not isinstance(text, str):
        raise ValueError(f"{label} must be a string")
    lowered = text.lower()
    forbidden = (
        "validated r035",
        "r038 validated",
        "r070 validates",
        "f19 closure",
        "rc28-f19 closure",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise ValueError(f"forbidden affirmative claim in {label}")


def validate(value: Any) -> None:
    value = obj(value, "S15 artifact")
    required = {
        "schema",
        "c4_acceptance",
        "classification",
        "status_effect",
        "class_matched_ids",
        "s15_called_validate_milestone",
        "s15_called_requirement_update",
        "engine_status",
        "open_findings",
        "predecessor_pins",
        "rows",
    }
    if (
        set(value) != required
        or value["schema"] != SCHEMA
        or value["c4_acceptance"] != "non-pass"
        or value["classification"] != "supporting-only"
        or value["status_effect"] != "unchanged"
        or value["class_matched_ids"] != []
    ):
        raise ValueError("closed S15 top-level schema or polarity mismatch")
    if (
        value["s15_called_validate_milestone"] is not False
        or value["s15_called_requirement_update"] is not False
        or type(value["open_findings"]) is not int
        or value["open_findings"] != 19
    ):
        raise ValueError("S15 lifecycle or finding claim is not fail-closed")
    if value["engine_status"] != {"engine_fix": "not_fixed", "upstream_issue": "not_filed"}:
        raise ValueError("engine status drift")
    if value["predecessor_pins"] != {"path": rel(SOURCES["s06"]), "sha256": digest(SOURCES["s06"])}:
        raise ValueError("predecessor pin mismatch")
    rows = value["rows"]
    if (
        not isinstance(rows, list)
        or len(rows) != len(EXPECTED_IDS)
        or [obj(row, "S15 row")["requirement_id"] for row in rows] != EXPECTED_IDS
    ):
        raise ValueError("rows must be complete and in canonical order")
    for row in rows:
        expected_kind, expected_class = ROW_EXPECTED[row["requirement_id"]]
        if (
            set(row)
            != {
                "requirement_id",
                "coverage_kind",
                "evidence_class",
                "class_matched",
                "status_effect",
                "source_surfaces",
                "limitations",
            }
            or row["coverage_kind"] != expected_kind
            or row["evidence_class"] != expected_class
            or row["class_matched"] is not False
            or row["status_effect"] != "unchanged"
            or not isinstance(row["limitations"], list)
            or not row["limitations"]
        ):
            raise ValueError(f"closed row mismatch: {row.get('requirement_id')}")
        for index, limitation in enumerate(row["limitations"]):
            _check_claim_text(limitation, f"{row['requirement_id']} limitation {index}")
        if not isinstance(row["source_surfaces"], list) or not row["source_surfaces"]:
            raise ValueError("source surfaces must be a non-empty list")
        for surface in row["source_surfaces"]:
            if not isinstance(surface, dict) or set(surface) != {"path", "sha256"}:
                raise ValueError("closed source surface mismatch")
            if not isinstance(surface["path"], str) or not isinstance(surface["sha256"], str):
                raise ValueError("source surface fields must be strings")
            if surface["path"] not in ALLOWED_SURFACES:
                raise ValueError(f"unapproved source surface: {surface['path']}")
            source = safe_source(surface["path"])
            if surface["sha256"] != digest(source):
                raise ValueError(f"source hash mismatch: {surface['path']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check", "classify"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    try:
        if args.command == "compose":
            value = classify()
            encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            if args.out.exists() and args.out.read_text(encoding="utf-8") != encoded:
                raise ValueError(f"refusing to overwrite existing artifact: {args.out}")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if not args.out.exists():
                args.out.write_text(encoded, encoding="utf-8")
            print("S15_REQUIREMENT_CLASS_COMPOSED")
        elif args.command == "check":
            validate(load(args.out))
            print("S15_REQUIREMENT_CLASS_CHECK_OK")
        else:
            value = classify()
            print(
                json.dumps(
                    {
                        key: value[key]
                        for key in (
                            "c4_acceptance",
                            "classification",
                            "class_matched_ids",
                            "status_effect",
                        )
                    },
                    separators=(",", ":"),
                )
            )
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s15_requirement_class: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
