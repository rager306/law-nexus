#!/usr/bin/env python3
"""Export a derived recovery view from minimal ACP fixture records.

The export is read-only relative to ACP source records. It is a derived view for
agent recovery, not an authority over architecture status.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/minimal-chain"
DEFAULT_OUTPUT = ROOT / "prd/architecture/acp/derived/recovery-view.json"
VERIFY_SCRIPT = ROOT / "scripts/verify-acp-records.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("verify_acp_records", VERIFY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator from {VERIFY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def record_summary(record: Any) -> dict[str, Any]:
    data = record.frontmatter
    return {
        "id": data.get("id"),
        "record_kind": data.get("record_kind"),
        "title": data.get("title"),
        "status": data.get("status"),
        "path": display_path(record.path),
        "source_refs": data.get("source_refs", []),
        "safety": data.get("safety", {}),
    }


def build_edges(records: list[Any]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    ids = {record.record_id for record in records}
    for record in records:
        data = record.frontmatter
        source = record.record_id
        links = {
            "producedProposal": data.get("produced_proposal"),
            "originPromptRecord": data.get("origin_prompt_record"),
            "originProposal": data.get("origin_proposal"),
            "requiresProof": data.get("requires_proof_gate"),
        }
        for rel, target in links.items():
            if isinstance(target, str) and target in ids:
                if rel.startswith("origin"):
                    edges.append({"source": target, "target": source, "relationship": rel})
                else:
                    edges.append({"source": source, "target": target, "relationship": rel})
        for target in data.get("decision_candidates", []) if isinstance(data.get("decision_candidates"), list) else []:
            if target in ids:
                edges.append({"source": source, "target": target, "relationship": "suggestedDecision"})
        for target in data.get("affected_records", []) if isinstance(data.get("affected_records"), list) else []:
            if target in ids:
                edges.append({"source": source, "target": target, "relationship": "affects"})
    return edges


def collect_blocked_actions(records: list[Any]) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for record in records:
        data = record.frontmatter
        actions: list[str] = []
        if isinstance(data.get("blocks"), list):
            actions.extend(str(item) for item in data["blocks"])
        if isinstance(data.get("blocked_actions"), list):
            actions.extend(str(item) for item in data["blocked_actions"])
        for action in actions:
            blocked.append(
                {
                    "action": action,
                    "blocked_by": record.record_id,
                    "record_kind": record.record_kind,
                    "reason": data.get("failure_mode") or data.get("finding") or "blocked by ACP record",
                }
            )
    return blocked


def allowed_next_actions(records: list[Any]) -> list[str]:
    ids = {record.record_id for record in records}
    actions = [
        "Run deterministic ACP validator before promoting any decision candidate.",
        "Generate or check the derived recovery view from source records.",
        "Keep runtime dashboard and registry integration blocked until proof gate evidence exists.",
    ]
    if "DC-0001" in ids and "PG-0001" in ids:
        actions.append("Implement S02 validator/exporter evidence for PG-0001.")
    return actions


def build_recovery_view(fixture_dir: Path) -> dict[str, Any]:
    validator = load_validator()
    validation = validator.run(fixture_dir)
    if validation["status"] != "ok":
        raise ValueError("ACP fixtures failed validation; refusing to export recovery view")
    records, parse_diagnostics = validator.load_records(fixture_dir)
    if parse_diagnostics:
        raise ValueError("ACP fixtures had parse diagnostics after validation")
    return {
        "kind": "acp_recovery_view",
        "version": "0.1.0",
        "boundary": "Derived recovery view only; ACP source records remain authoritative.",
        "source_fixture_dir": display_path(fixture_dir),
        "records": [record_summary(record) for record in records],
        "edges": build_edges(records),
        "blocked_actions": collect_blocked_actions(records),
        "allowed_next_actions": allowed_next_actions(records),
        "validation": {
            "status": validation["status"],
            "record_count": validation["record_count"],
            "diagnostic_count": validation["diagnostic_count"],
        },
    }


def write_output(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_output(output_path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    expected = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not output_path.exists():
        return False, "output file does not exist"
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, "output file is stale"
    return True, "output file is current"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail if derived output is missing or stale.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_recovery_view(args.fixture_dir)
        if args.check:
            ok, message = check_output(args.output, payload)
            result = {"status": "ok" if ok else "failed", "message": message, "output": display_path(args.output)}
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if ok else 1
        write_output(args.output, payload)
        result = {
            "status": "ok",
            "output": display_path(args.output),
            "record_count": len(payload["records"]),
            "blocked_action_count": len(payload["blocked_actions"]),
            "boundary": payload["boundary"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except ValueError as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
