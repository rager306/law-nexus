#!/usr/bin/env python3
"""Build normalized non-authoritative Consultant prior-art expectations.

The command summarizes law-parser prior-art structure/articles outputs and
validation YAML files into a compact expectation artifact. It preserves source
hashes and freshness diagnostics, but does not treat prior-art output as legal
truth, parser completeness evidence, or authoritative legal interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path("prd/parser/consultant_prior_art_inventory.json")
JSON_PATH = Path("prd/parser/consultant_prior_art_expectations.json")
REPORT_PATH = Path("prd/parser/consultant_prior_art_expectations.md")
STRUCTURE_PATH = Path("/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json")
ARTICLES_PATH = Path("/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl")
VALIDATION_DIR = Path("/root/law-parser/prompt_domain_44fz/validation")
MAX_DIAGNOSTICS = 100
NON_CLAIMS = [
    "Prior-art expectations are deterministic comparison safeguards only.",
    "Prior-art expectations do not claim legal correctness or authoritative legal interpretation.",
    "Prior-art expectations do not claim parser completeness.",
    "Prior-art expectations do not make LLM output authoritative.",
]
COMPARABLE_STRUCTURAL_RULES = {
    "STRUCT-001",
    "STRUCT-002",
    "STRUCT-003",
    "STRUCT-004",
    "STRUCT-005",
    "STRUCT-006",
}
ADVISORY_SEMANTIC_RULES = {
    "SEM-001",
    "SEM-002",
    "SEM-003",
    "SEM-004",
    "SEM-005",
    "SEM-006",
    "SEM-007",
    "SEM-008",
    "SEM-009",
}
SKIPPED_FIELDS = [
    {
        "field": "article.title/text and part/clause/subclause text",
        "reason": "text copied from prior-art output is source/provider-specific and not a compact structure expectation",
    },
    {
        "field": "semantic legal meaning and internal-reference validity",
        "reason": "requires citation-safe deterministic evidence beyond context-free count comparison",
    },
    {
        "field": "amendment/invalidation legal effect",
        "reason": "prior-art markers are advisory until temporal/legal evidence rules are verified separately",
    },
]


@dataclass(frozen=True)
class BuildResult:
    """Generated artifacts and diagnostics."""

    summary_json: str
    report_md: str
    diagnostics: dict[str, Any]


def stable_json(data: Any) -> str:
    """Return deterministic pretty JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(path: Path) -> str:
    """Return SHA-256 of a source file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    """Return SHA-256 of text encoded as UTF-8."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def truncate(text: Any, limit: int = 220) -> str:
    """Return a bounded diagnostic string."""

    rendered = str(text)
    return rendered if len(rendered) <= limit else rendered[: limit - 1].rstrip() + "…"


def compact_error(kind: str, message: Any, **extra: Any) -> dict[str, Any]:
    """Return a bounded deterministic diagnostic error."""

    payload = {"kind": kind, "message": truncate(message)}
    payload.update(extra)
    return payload


def load_json(path: Path) -> tuple[Any | None, dict[str, Any] | None]:
    """Load JSON and return a compact error instead of raising."""

    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, compact_error("missing_json", f"missing JSON file: {path}", path=str(path))
    except json.JSONDecodeError as exc:
        return None, compact_error("malformed_json", exc, path=str(path))


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Load JSONL article records and return compact parse diagnostics."""

    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [], compact_error("missing_jsonl", f"missing JSONL file: {path}", path=str(path))

    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            return records, compact_error("malformed_jsonl", exc, path=str(path), line_no=line_no)
        if not isinstance(value, dict):
            return records, compact_error("non_object_jsonl_record", "JSONL record is not an object", path=str(path), line_no=line_no)
        records.append(value)
    return records, None


def load_yaml(path: Path) -> tuple[Any | None, dict[str, Any] | None]:
    """Load YAML and return a compact error instead of raising."""

    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, compact_error("missing_yaml", f"missing YAML file: {path}", path=str(path))
    except yaml.YAMLError as exc:
        return None, compact_error("malformed_yaml", exc, path=str(path))


def source_entry(path: Path, inventory_assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return source hash and inventory freshness metadata for one prior-art file."""

    exists = path.exists()
    actual_sha = sha256_bytes(path) if exists else None
    asset = inventory_assets.get(str(path)) or inventory_assets.get(path.name) or {}
    expected_sha = asset.get("expected_sha256") or asset.get("sha256")
    return {
        "asset_id": asset.get("asset_id"),
        "classification": asset.get("classification"),
        "comparable_boundary": asset.get("reuse_boundary"),
        "exists": exists,
        "expected_sha256": expected_sha,
        "hash_matches_expected": actual_sha == expected_sha if actual_sha and expected_sha else False,
        "path": str(path),
        "sha256": actual_sha,
        "size_bytes": path.stat().st_size if exists else None,
    }


def load_inventory_assets() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Load prior-art inventory assets keyed by source path."""

    payload, error = load_json(ROOT / INVENTORY_PATH)
    if error is not None:
        return {}, [error]
    assets: dict[str, dict[str, Any]] = {}
    for asset in payload.get("assets", []) if isinstance(payload, dict) else []:
        if isinstance(asset, dict) and asset.get("source_path"):
            assets[str(asset["source_path"])] = asset
            assets[Path(str(asset["source_path"])).name] = asset
    return assets, []


def structure_expectations(structure: dict[str, Any]) -> dict[str, Any]:
    """Summarize comparable structure-json counts."""

    chapters = structure.get("chapters") or []
    chapter_article_counts = [len(chapter.get("articles") or []) for chapter in chapters if isinstance(chapter, dict)]
    chapter_paragraph_counts = [len(chapter.get("paragraphs") or []) for chapter in chapters if isinstance(chapter, dict)]
    metadata = structure.get("metadata") or {}
    return {
        "expectation_id": "EXP-CPA-STRUCTURE-COUNTS",
        "classification": "comparable",
        "counts": {
            "chapter_count": len(chapters),
            "chapter_article_refs_total": sum(chapter_article_counts),
            "chapter_paragraphs_total": sum(chapter_paragraph_counts),
            "chapters_with_article_refs": sum(1 for value in chapter_article_counts if value),
            "chapters_with_paragraphs": sum(1 for value in chapter_paragraph_counts if value),
            "metadata_field_count": len(metadata) if isinstance(metadata, dict) else 0,
            "all_references_count": len(structure.get("all_references") or []),
            "external_laws_count": len(structure.get("external_laws") or []),
            "key_dates_count": len(structure.get("key_dates") or {}),
            "definitions_count": len(structure.get("definitions") or {}),
        },
        "chapter_summaries": [
            {
                "chapter": chapter.get("number"),
                "article_refs": len(chapter.get("articles") or []),
                "paragraphs": len(chapter.get("paragraphs") or []),
                "title_excerpt": truncate(chapter.get("title", ""), 120),
            }
            for chapter in chapters
            if isinstance(chapter, dict)
        ],
        "skipped_fields": ["metadata legal dates as semantics", "article/reference text payloads"],
    }


def articles_expectations(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize comparable article-jsonl record counts."""

    invalid_counts = Counter(str(bool(record.get("invalid"))).lower() for record in records)
    parts_total = 0
    clauses_total = 0
    subclauses_total = 0
    invalid_parts = 0
    invalid_clauses = 0
    invalid_subclauses = 0
    part_references = 0
    clause_references = 0
    part_amendments = 0
    clause_amendments = 0
    article_numbers: list[str] = []
    chapter_counts: Counter[str] = Counter()

    for record in records:
        article_numbers.append(str(record.get("article")))
        chapter_counts[str(record.get("chapter"))] += 1
        for part in record.get("parts") or []:
            if not isinstance(part, dict):
                continue
            parts_total += 1
            invalid_parts += int(bool(part.get("invalid")))
            part_references += len(part.get("references") or [])
            part_amendments += len(part.get("amendments") or [])
            for clause in part.get("clauses") or []:
                if not isinstance(clause, dict):
                    continue
                clauses_total += 1
                invalid_clauses += int(bool(clause.get("invalid")))
                clause_references += len(clause.get("references") or [])
                clause_amendments += len(clause.get("amendments") or [])
                for subclause in clause.get("subclauses") or []:
                    if isinstance(subclause, dict):
                        subclauses_total += 1
                        invalid_subclauses += int(bool(subclause.get("invalid")))
                    else:
                        subclauses_total += 1

    return {
        "expectation_id": "EXP-CPA-ARTICLE-COUNTS",
        "classification": "comparable",
        "counts": {
            "article_record_count": len(records),
            "article_invalid_false_count": invalid_counts.get("false", 0),
            "article_invalid_true_count": invalid_counts.get("true", 0),
            "articles_without_parts": sum(1 for record in records if not record.get("parts")),
            "part_count": parts_total,
            "part_invalid_true_count": invalid_parts,
            "clause_count": clauses_total,
            "clause_invalid_true_count": invalid_clauses,
            "subclause_count": subclauses_total,
            "subclause_invalid_true_count": invalid_subclauses,
            "part_references_count": part_references,
            "clause_references_count": clause_references,
            "part_amendments_count": part_amendments,
            "clause_amendments_count": clause_amendments,
        },
        "chapter_article_counts": dict(sorted(chapter_counts.items(), key=lambda item: item[0])),
        "first_article_ids": article_numbers[:5],
        "last_article_ids": article_numbers[-5:],
        "skipped_fields": ["title", "text", "amendment legal effect", "reference legal validity"],
    }


def rule_classification(rule_id: str, rule_file: str) -> str:
    """Classify a validation YAML rule for comparison use."""

    if rule_id in COMPARABLE_STRUCTURAL_RULES:
        return "comparable"
    if rule_id in ADVISORY_SEMANTIC_RULES or rule_file == "semantic_rules.yaml":
        return "advisory"
    return "advisory"


def validation_rule_expectations(paths: list[Path]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize validation YAML rules with comparable/advisory classes."""

    errors: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    counts = Counter()

    for path in paths:
        payload, error = load_yaml(path)
        if error is not None:
            errors.append(error)
            continue
        file_rules = payload.get("rules", []) if isinstance(payload, dict) else []
        file_entry = {
            "path": str(path),
            "sha256": sha256_bytes(path),
            "rule_count": len(file_rules),
            "version": payload.get("version") if isinstance(payload, dict) else None,
        }
        files.append(file_entry)
        for index, rule in enumerate(file_rules, 1):
            if not isinstance(rule, dict):
                rule_id = f"{path.stem}:{index:02d}"
                classification = "advisory"
                rule_entry = {
                    "rule_id": rule_id,
                    "classification": classification,
                    "file": path.name,
                    "source_excerpt": truncate(rule),
                }
            else:
                rule_id = str(rule.get("id") or f"{path.stem}:{index:02d}")
                classification = rule_classification(rule_id, path.name)
                rule_entry = {
                    "rule_id": rule_id,
                    "classification": classification,
                    "file": path.name,
                    "name": rule.get("name"),
                    "severity": rule.get("severity"),
                    "target": rule.get("target"),
                    "check": rule.get("check"),
                    "source_excerpt": truncate(rule.get("description") or rule.get("name") or rule_id),
                }
            counts[classification] += 1
            rules.append(rule_entry)

    return {
        "expectation_id": "EXP-CPA-VALIDATION-RULES",
        "classification": "mixed",
        "counts": {
            "validation_file_count": len(files),
            "validation_rule_count": len(rules),
            "comparable_rule_count": counts.get("comparable", 0),
            "advisory_rule_count": counts.get("advisory", 0),
        },
        "files": files,
        "rules": rules,
        "skipped_fields": ["rule implementation semantics", "LLM prompt behavior", "legal interpretation"],
    }, errors


def freshness_map(expected: dict[Path, str]) -> dict[str, bool]:
    """Return whether generated artifact content matches files on disk."""

    result: dict[str, bool] = {}
    for relative_path, content in expected.items():
        path = ROOT / relative_path
        result[str(relative_path)] = path.exists() and path.read_text(encoding="utf-8") == content
    return result


def render_report(summary: dict[str, Any]) -> str:
    """Render compact deterministic Markdown for human review."""

    comparable_counts = summary["expectations"]["comparable_counts"]
    validation = summary["expectations"]["validation_rules"]
    lines = [
        "# Consultant prior-art expectations",
        "",
        "This artifact normalizes law-parser prior-art outputs into deterministic comparison safeguards. It is non-authoritative and does not claim legal correctness, parser completeness, or authoritative legal interpretation.",
        "",
        "## Source freshness",
        "",
    ]
    for source in summary["sources"]:
        lines.append(
            f"- `{source['path']}` asset=`{source.get('asset_id')}` sha256=`{source.get('sha256')}` expected=`{source.get('expected_sha256')}` match=`{str(source.get('hash_matches_expected')).lower()}` class=`{source.get('classification')}`"
        )
    lines.extend(
        [
            "",
            "## Comparable counts",
            "",
            "### Structure JSON",
            "",
        ]
    )
    for key, value in comparable_counts["structure"]["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "### Articles JSONL", ""])
    for key, value in comparable_counts["articles"]["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Validation rules", ""])
    for key, value in validation["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "### Comparable rules", ""])
    for rule in validation["rules"]:
        if rule["classification"] == "comparable":
            lines.append(f"- `{rule['rule_id']}` `{rule.get('severity')}` target=`{rule.get('target')}` check=`{rule.get('check')}` — {rule.get('source_excerpt')}")
    lines.extend(["", "### Advisory rules", ""])
    for rule in validation["rules"]:
        if rule["classification"] == "advisory":
            lines.append(f"- `{rule['rule_id']}` `{rule.get('severity')}` target=`{rule.get('target')}` check=`{rule.get('check')}` — {rule.get('source_excerpt')}")
    lines.extend(["", "## Skipped/advisory fields", ""])
    for item in summary["expectations"]["skipped_fields"]:
        lines.append(f"- `{item['field']}` — {item['reason']}")
    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            f"- Fatal errors: `{summary['fatal_error_count']}`",
            f"- Hash drift count: `{summary['hash_drift_count']}`",
            f"- Artifact freshness: `{json.dumps(summary.get('artifact_freshness'), ensure_ascii=False, sort_keys=True)}`",
            "",
        ]
    )
    return "\n".join(lines)


def build() -> BuildResult:
    """Build the normalized prior-art expectations and diagnostics."""

    inventory_assets, fatal_errors = load_inventory_assets()
    validation_paths = sorted(VALIDATION_DIR.glob("*.yaml")) if VALIDATION_DIR.exists() else [VALIDATION_DIR / "semantic_rules.yaml", VALIDATION_DIR / "structural_rules.yaml"]
    source_paths = [STRUCTURE_PATH, ARTICLES_PATH, *validation_paths]
    sources = [source_entry(path, inventory_assets) for path in source_paths]

    structure_payload, structure_error = load_json(STRUCTURE_PATH)
    articles_records, articles_error = load_jsonl(ARTICLES_PATH)
    if structure_error is not None:
        fatal_errors.append(structure_error)
    if articles_error is not None:
        fatal_errors.append(articles_error)

    validation_rules, validation_errors = validation_rule_expectations(validation_paths)
    fatal_errors.extend(validation_errors)

    structure_counts = structure_expectations(structure_payload if isinstance(structure_payload, dict) else {})
    article_counts = articles_expectations(articles_records)
    hash_drifts = [
        compact_error("hash_drift", f"source hash does not match inventory for {source['path']}", path=source["path"], asset_id=source.get("asset_id"))
        for source in sources
        if source.get("exists") and source.get("expected_sha256") and not source.get("hash_matches_expected")
    ]
    missing_sources = [
        compact_error("missing_source", f"source is missing: {source['path']}", path=source["path"], asset_id=source.get("asset_id"))
        for source in sources
        if not source.get("exists")
    ]
    fatal_errors.extend(missing_sources)

    summary = {
        "artifact_paths": {"json": str(JSON_PATH), "report": str(REPORT_PATH)},
        "artifact_freshness": None,
        "diagnostics_bounded": True,
        "expectations": {
            "comparable_counts": {"articles": article_counts, "structure": structure_counts},
            "skipped_fields": SKIPPED_FIELDS,
            "validation_rules": validation_rules,
        },
        "fatal_error_count": len(fatal_errors),
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "hash_drift_count": len(hash_drifts),
        "hash_drifts": hash_drifts[:MAX_DIAGNOSTICS],
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
        "phase": "consultant_prior_art_expectations_build",
        "sources": sources,
    }
    summary_json = stable_json(summary)
    report_md = render_report(summary)
    return BuildResult(summary_json=summary_json, report_md=report_md, diagnostics=summary)


def write_artifacts(result: BuildResult) -> None:
    """Write generated artifacts deterministically."""

    for relative_path, content in {JSON_PATH: result.summary_json, REPORT_PATH: result.report_md}.items():
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_artifacts(result: BuildResult) -> bool:
    """Return True when generated artifacts are fresh."""

    expected = {JSON_PATH: result.summary_json, REPORT_PATH: result.report_md}
    return all((ROOT / path).exists() and (ROOT / path).read_text(encoding="utf-8") == content for path, content in expected.items())


def cli_payload(result: BuildResult, status: str) -> dict[str, Any]:
    """Return CLI diagnostics with artifact freshness populated."""

    output = dict(result.diagnostics)
    output["artifact_freshness"] = freshness_map({JSON_PATH: result.summary_json, REPORT_PATH: result.report_md})
    output["status"] = status
    return output


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifacts are fresh without writing")
    args = parser.parse_args(argv)

    result = build()
    if result.diagnostics.get("fatal_error_count", 0) or result.diagnostics.get("hash_drift_count", 0):
        print(stable_json(cli_payload(result, "fail")), end="")
        return 1

    if args.check:
        fresh = check_artifacts(result)
        print(stable_json(cli_payload(result, "pass" if fresh else "fail")), end="")
        return 0 if fresh else 1

    write_artifacts(result)
    print(stable_json(cli_payload(result, "pass")), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
