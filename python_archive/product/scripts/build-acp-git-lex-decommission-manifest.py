#!/usr/bin/env python3
"""Build the deterministic ACP/git-lex decommission inventory (M108/D0)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "prd/migration/decommission/acp-git-lex-manifest.json"
MD_OUT = ROOT / "prd/migration/decommission/acp-git-lex-manifest.md"
SCHEMA = "law-nexus/acp-git-lex-decommission-manifest/v1"
EXCLUDED = {
    "scripts/build-acp-git-lex-decommission-manifest.py",
    "tests/test_acp_git_lex_decommission_manifest.py",
    "tests/test_repository_quality_gate.py",
    "prd/migration/decommission/acp-git-lex-manifest.json",
    "prd/migration/decommission/acp-git-lex-manifest.md",
}
PRODUCT_DENY_PREFIXES = (
    "src/law_nexus/",
    "law-source/",
    "prd/parser/",
    "prd/retrieval/",
)


def tracked_paths(root: Path = ROOT) -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=root, text=True)
    return sorted(line for line in output.splitlines() if line)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def explicit_class(path: str) -> tuple[str, str | None] | None:
    mappings = (
        (".lex/", "derived_lex_state", "python_archive/acp_git_lex/lex-state/"),
        (
            "prd/architecture/acp/",
            "historical_architecture",
            "python_archive/acp_git_lex/architecture/",
        ),
        (".agents/skills/acp/", "active_skill", "python_archive/acp_git_lex/skills/acp/"),
        (".agents/skills/git-lex/", "active_skill", "python_archive/acp_git_lex/skills/git-lex/"),
        (
            "git-lex-kit-acp/",
            "project_local_kit",
            "python_archive/acp_git_lex/kits/git-lex-kit-acp/",
        ),
        (
            "git-lex-kit-law-nexus/",
            "project_local_kit",
            "python_archive/acp_git_lex/kits/git-lex-kit-law-nexus/",
        ),
    )
    for prefix, category, target in mappings:
        if path.startswith(prefix):
            return category, target + path[len(prefix) :]
    lower = path.lower()
    if path.startswith("scripts/") and ("acp" in lower or "git_lex" in lower or "git-lex" in lower):
        return "active_script", "python_archive/acp_git_lex/scripts/" + path.removeprefix(
            "scripts/"
        )
    if path.startswith("tests/") and ("acp" in lower or "git_lex" in lower or "git-lex" in lower):
        return "active_test", "python_archive/acp_git_lex/tests/" + path.removeprefix("tests/")
    if path == ".github/workflows/compliance-gate.yml":
        return "rewrite_quality_gate", None
    return None


def contains_signal(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    value = text.lower()
    return any(token in value for token in ("acp", "git-lex", "git_lex", ".lex/", "git lex"))


def build_manifest(root: Path = ROOT) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for rel in tracked_paths(root):
        if rel in EXCLUDED or rel.startswith("python_archive/acp_git_lex/"):
            continue
        classified = explicit_class(rel)
        if classified is None and not contains_signal(root / rel):
            continue
        category, target = classified or ("manual_review_reference", None)
        entries.append(
            {
                "source_path": rel,
                "source_sha256": sha256_file(root / rel),
                "classification": category,
                "archive_path": target,
                "action": "archive" if target else "review_or_rewrite",
            }
        )
    entries.sort(key=lambda item: str(item["source_path"]))
    archive_targets = [str(e["archive_path"]) for e in entries if e["archive_path"]]
    denied = [
        str(e["source_path"])
        for e in entries
        if e["archive_path"] and str(e["source_path"]).startswith(PRODUCT_DENY_PREFIXES)
    ]
    duplicates = sorted(path for path, count in Counter(archive_targets).items() if count > 1)
    counts = Counter(str(e["classification"]) for e in entries)
    return {
        "schema_version": SCHEMA,
        "decision": "D104",
        "requirement": "R066",
        "external_repository_mutation_allowed": False,
        "external_repository": "/root/git-lex-kit-acp/",
        "entry_count": len(entries),
        "archive_candidate_count": len(archive_targets),
        "manual_review_count": counts.get("manual_review_reference", 0),
        "counts_by_classification": dict(sorted(counts.items())),
        "duplicate_archive_targets": duplicates,
        "product_denylist_violations": denied,
        "entries": entries,
    }


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_markdown(payload: dict[str, object]) -> str:
    counts = payload["counts_by_classification"]
    lines = [
        "# ACP/git-lex decommission manifest",
        "",
        f"- Entries: **{payload['entry_count']}**",
        f"- Archive candidates: **{payload['archive_candidate_count']}**",
        f"- Manual review: **{payload['manual_review_count']}**",
        f"- Duplicate targets: **{len(payload['duplicate_archive_targets'])}**",
        f"- Product denylist violations: **{len(payload['product_denylist_violations'])}**",
        "- External `/root/git-lex-kit-acp/`: **must not be modified**",
        "",
        "## Counts",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| `{key}` | {value} |" for key, value in counts.items())
    lines += [
        "",
        "## Boundary",
        "",
        "Archive candidates are moved only by later reviewed waves. Manual-review references are rewritten or explicitly preserved; this manifest performs no move.",
        "",
    ]
    return "\n".join(lines)


def validate(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if payload["duplicate_archive_targets"]:
        errors.append("duplicate_archive_targets")
    if payload["product_denylist_violations"]:
        errors.append("product_denylist_violations")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_manifest()
    errors = validate(payload)
    expected = {JSON_OUT: render_json(payload), MD_OUT: render_markdown(payload)}
    if args.check:
        for path, content in expected.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                errors.append(f"stale:{path.relative_to(ROOT)}")
    else:
        for path, content in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "pass" if not errors else "fail",
                "entry_count": payload["entry_count"],
                "archive_candidate_count": payload["archive_candidate_count"],
                "manual_review_count": payload["manual_review_count"],
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
