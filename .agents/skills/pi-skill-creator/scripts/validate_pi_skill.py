#!/usr/bin/env python3
"""Validate PI/GSD skill structure and optional eval schema.

This is a PI/GSD adaptation of the useful parts of Anthropic's skill-creator
quick validation: frontmatter checks, directory/reference checks, and eval file
shape validation without Claude Code-specific `.claude/commands` assumptions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
REQUIRED_TAGS = ["success_criteria"]
OPTIONAL_ROUTER_TAGS = ["essential_principles", "quick_reference", "routing", "reference_index", "workflows_index"]


class ValidationError(Exception):
    pass


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValidationError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValidationError("SKILL.md frontmatter is not closed")
    frontmatter_text = text[4:end]
    body = text[end + len("\n---\n") :]
    data: dict[str, str] = {}
    current_key: str | None = None
    current_block: list[str] = []

    def flush_block() -> None:
        nonlocal current_key, current_block
        if current_key is not None:
            data[current_key] = "\n".join(current_block).strip()
            current_key = None
            current_block = []

    for raw_line in frontmatter_text.splitlines():
        if not raw_line.strip():
            continue
        if current_key is not None and (raw_line.startswith(" ") or raw_line.startswith("\t")):
            current_block.append(raw_line.strip())
            continue
        flush_block()
        if ":" not in raw_line:
            raise ValidationError(f"Invalid frontmatter line: {raw_line!r}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {"|", ">"}:
            current_key = key
            current_block = []
        else:
            data[key] = value.strip('"').strip("'")
    flush_block()
    return data, body


def validate_frontmatter(skill_dir: Path, frontmatter: dict[str, str]) -> None:
    unexpected = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
    if unexpected:
        raise ValidationError(f"Unexpected frontmatter keys: {', '.join(sorted(unexpected))}")
    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if not name:
        raise ValidationError("Missing frontmatter name")
    if name != skill_dir.name:
        raise ValidationError(f"Frontmatter name {name!r} must match directory {skill_dir.name!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValidationError("Skill name must be lowercase kebab-case")
    if len(name) > 64:
        raise ValidationError("Skill name exceeds 64 characters")
    if not description:
        raise ValidationError("Missing frontmatter description")
    if len(description) > 1024:
        raise ValidationError("Description exceeds 1024 characters")
    if "<" in description or ">" in description:
        raise ValidationError("Description must not contain XML/angle brackets")
    if "use" not in description.lower() and "when" not in description.lower():
        raise ValidationError("Description should state when to use the skill")


def validate_body(body: str) -> None:
    if len(body.splitlines()) > 500:
        raise ValidationError("SKILL.md body exceeds 500 lines; use references/workflows")
    for tag in REQUIRED_TAGS:
        if f"<{tag}>" not in body or f"</{tag}>" not in body:
            raise ValidationError(f"Missing required XML tag pair: {tag}")
    router_tags_present = sum(1 for tag in OPTIONAL_ROUTER_TAGS if f"<{tag}>" in body and f"</{tag}>" in body)
    if len(body.splitlines()) > 120 and router_tags_present < 2:
        raise ValidationError("Large SKILL.md should use router/progressive-disclosure XML sections")


def referenced_files(body: str) -> set[str]:
    return set(re.findall(r"`((?:workflows|references|templates|scripts)/[^`]+)`", body))


def validate_references(skill_dir: Path, body: str) -> None:
    for rel in sorted(referenced_files(body)):
        if not (skill_dir / rel).exists():
            raise ValidationError(f"SKILL.md references missing file: {rel}")
    for workflow in (skill_dir / "workflows").glob("*.md") if (skill_dir / "workflows").exists() else []:
        text = workflow.read_text(encoding="utf-8")
        for tag in ["required_reading", "process", "success_criteria"]:
            if f"<{tag}>" not in text or f"</{tag}>" not in text:
                raise ValidationError(f"Workflow {workflow.relative_to(skill_dir)} missing {tag} tag pair")


def validate_evals(evals_path: Path, skill_name: str) -> None:
    data: Any = json.loads(evals_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("evals/evals.json must be an object")
    if data.get("skill_name") != skill_name:
        raise ValidationError("evals/evals.json skill_name must match skill frontmatter name")
    evals = data.get("evals")
    if not isinstance(evals, list):
        raise ValidationError("evals/evals.json evals must be a list")
    seen_ids: set[int] = set()
    for index, item in enumerate(evals):
        if not isinstance(item, dict):
            raise ValidationError(f"evals[{index}] must be an object")
        eval_id = item.get("id")
        if not isinstance(eval_id, int):
            raise ValidationError(f"evals[{index}].id must be an integer")
        if eval_id in seen_ids:
            raise ValidationError(f"duplicate eval id: {eval_id}")
        seen_ids.add(eval_id)
        for key in ["prompt", "expected_output"]:
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValidationError(f"evals[{index}].{key} must be a non-empty string")
        files = item.get("files", [])
        if not isinstance(files, list) or not all(isinstance(v, str) for v in files):
            raise ValidationError(f"evals[{index}].files must be a list of strings")
        expectations = item.get("expectations", [])
        if not isinstance(expectations, list) or not expectations or not all(isinstance(v, str) and v.strip() for v in expectations):
            raise ValidationError(f"evals[{index}].expectations must be a non-empty list of strings")


def validate_skill(skill_dir: Path, require_evals: bool) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise ValidationError(f"Missing SKILL.md in {skill_dir}")
    frontmatter, body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    validate_frontmatter(skill_dir, frontmatter)
    validate_body(body)
    validate_references(skill_dir, body)

    warnings: list[str] = []
    evals_path = skill_dir / "evals" / "evals.json"
    if evals_path.exists():
        validate_evals(evals_path, frontmatter["name"])
    elif require_evals:
        raise ValidationError("Missing evals/evals.json")
    else:
        warnings.append("No evals/evals.json found; structure is valid but quality is not eval-validated")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PI/GSD skill structure")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--require-evals", action="store_true")
    args = parser.parse_args()
    try:
        warnings = validate_skill(args.skill_dir, args.require_evals)
    except (ValidationError, json.JSONDecodeError) as exc:
        print(f"PI skill validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"PI skill validation passed: {args.skill_dir}")
    for warning in warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
