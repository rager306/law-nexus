#!/usr/bin/env python3
"""Compare Consultant hierarchy records against prior-art expectations.

The comparison is a deterministic safeguard only. It does not claim legal
correctness, parser completeness, amendment effect, or authoritative legal
interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from parser_records import ConsultantHierarchyRecord, load_jsonl_records

ROOT = Path(__file__).resolve().parents[1]
HIERARCHY_JSONL_PATH = Path("prd/parser/consultant_hierarchy_records.jsonl")
EXPECTATIONS_PATH = Path("prd/parser/consultant_prior_art_expectations.json")
JSON_PATH = Path("prd/parser/consultant_hierarchy_prior_art_comparison.json")
REPORT_PATH = Path("prd/parser/consultant_hierarchy_prior_art_comparison.md")
MAX_DIAGNOSTICS = 100
NON_CLAIMS = [
    "Consultant hierarchy prior-art comparison is a deterministic safeguard only.",
    "Comparison results do not claim legal correctness or authoritative legal interpretation.",
    "Comparison results do not claim parser completeness.",
    "Prior-art mismatches are evidence anchors for review, not legal conclusions.",
]
INVALIDITY_TERMS = ("утратил", "утратила", "утратило", "утратили", "не применяется")
MAJOR_LEVELS = {"chapter", "article"}
GRANULAR_LEVELS = {"part", "clause", "subclause", "section"}


@dataclass(frozen=True)
class BuildResult:
    """Generated comparison artifacts and diagnostics."""

    summary_json: str
    report_md: str
    diagnostics: dict[str, Any]


def stable_json(data: Any) -> str:
    """Return deterministic pretty JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(path: Path) -> str | None:
    """Return SHA-256 for an existing file, otherwise None."""

    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truncate(value: Any, limit: int = 220) -> str:
    """Return a bounded diagnostic string."""

    rendered = str(value)
    return rendered if len(rendered) <= limit else rendered[: limit - 1].rstrip() + "…"


def compact_error(kind: str, message: Any, **extra: Any) -> dict[str, Any]:
    """Return a compact deterministic diagnostic error."""

    payload = {"kind": kind, "message": truncate(message)}
    payload.update(extra)
    return payload


def load_json(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load a JSON object with bounded diagnostics."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, compact_error("missing_json", f"missing JSON file: {path}", path=str(path))
    except json.JSONDecodeError as exc:
        return None, compact_error("malformed_json", exc, path=str(path))
    if not isinstance(payload, dict):
        return None, compact_error("non_object_json", "JSON file must contain an object", path=str(path))
    return payload, None


def marker_number(record: ConsultantHierarchyRecord) -> str | None:
    """Extract the comparable numeric/letter marker from a hierarchy record."""

    if record.marker is None:
        return None
    normalized = record.marker.normalized
    match = re.search(r"\d+(?:\.\d+)?", normalized)
    if match:
        return match.group(0)
    return normalized.strip().strip(".") or None


def record_anchor(record: ConsultantHierarchyRecord) -> dict[str, Any]:
    """Return a bounded evidence anchor for one hierarchy record."""

    return {
        "record_id": record.id,
        "level": record.level,
        "marker": marker_number(record),
        "order_index": record.order_index,
        "parent_id": record.parent_id,
        "source_path": record.source_path,
        "source_sha256": record.source_sha256,
        "excerpt_sha256": record.excerpt_sha256,
        "excerpt": truncate(record.excerpt, 180),
    }


def first_anchor(records: Iterable[ConsultantHierarchyRecord]) -> dict[str, Any] | None:
    """Return the first bounded anchor in an iterable."""

    for record in records:
        return record_anchor(record)
    return None


def hierarchy_records(path: Path) -> tuple[list[ConsultantHierarchyRecord], list[dict[str, Any]]]:
    """Load only Consultant hierarchy records from JSONL."""

    parsed, diagnostics = load_jsonl_records(path)
    records = [record for record in parsed if isinstance(record, ConsultantHierarchyRecord)]
    skipped = [record for record in parsed if not isinstance(record, ConsultantHierarchyRecord)]
    if skipped:
        diagnostics.append(compact_error("non_hierarchy_record", "comparison input contained non-hierarchy records", count=len(skipped)))
    return records, diagnostics


def ancestor_level(record: ConsultantHierarchyRecord, by_id: dict[str, ConsultantHierarchyRecord], level: str) -> ConsultantHierarchyRecord | None:
    """Return the nearest ancestor at the requested level."""

    seen: set[str] = set()
    current = record
    while current.parent_id:
        if current.parent_id in seen:
            return None
        seen.add(current.parent_id)
        parent = by_id.get(current.parent_id)
        if parent is None:
            return None
        if parent.level == level:
            return parent
        current = parent
    return None


def observed_summary(records: list[ConsultantHierarchyRecord]) -> dict[str, Any]:
    """Summarize observed hierarchy counts, order, parents, and source anchors."""

    by_id = {record.id: record for record in records}
    counts = Counter(record.level for record in records)
    first_by_level: dict[str, ConsultantHierarchyRecord] = {}
    last_by_level: dict[str, ConsultantHierarchyRecord] = {}
    duplicate_ids = [record_id for record_id, count in Counter(record.id for record in records).items() if count > 1]
    missing_parents = [record for record in records if record.parent_id and record.parent_id not in by_id]
    non_monotonic = []
    previous = -1
    for record in records:
        first_by_level.setdefault(record.level, record)
        last_by_level[record.level] = record
        if record.order_index <= previous:
            non_monotonic.append(record)
        previous = record.order_index

    chapter_article_counts: dict[str, int] = defaultdict(int)
    article_markers: list[str] = []
    for record in records:
        if record.level != "article":
            continue
        marker = marker_number(record)
        if marker is not None:
            article_markers.append(marker)
        chapter = ancestor_level(record, by_id, "chapter")
        if chapter is not None:
            chapter_marker = marker_number(chapter)
            if chapter_marker is not None:
                chapter_article_counts[chapter_marker] += 1

    invalidity_records = [
        record
        for record in records
        if any(term in f"{record.title} {record.excerpt}".lower() for term in INVALIDITY_TERMS)
    ]
    invalidity_by_level = Counter(record.level for record in invalidity_records)

    return {
        "counts_by_level": dict(sorted(counts.items())),
        "duplicate_ids": duplicate_ids[:MAX_DIAGNOSTICS],
        "first_by_level": {level: record_anchor(record) for level, record in sorted(first_by_level.items())},
        "last_by_level": {level: record_anchor(record) for level, record in sorted(last_by_level.items())},
        "missing_parent_count": len(missing_parents),
        "missing_parent_samples": [record_anchor(record) for record in missing_parents[:MAX_DIAGNOSTICS]],
        "non_monotonic_order_count": len(non_monotonic),
        "non_monotonic_order_samples": [record_anchor(record) for record in non_monotonic[:MAX_DIAGNOSTICS]],
        "article_markers_first": article_markers[:5],
        "article_markers_last": article_markers[-5:],
        "chapter_article_counts": dict(sorted(chapter_article_counts.items(), key=lambda item: float(item[0]))),
        "invalidity_marker_counts_by_level": dict(sorted(invalidity_by_level.items())),
        "invalidity_marker_samples": [record_anchor(record) for record in invalidity_records[:MAX_DIAGNOSTICS]],
        "source_hashes": sorted({record.source_sha256 for record in records}),
        "record_count": len(records),
    }


def comparison_entry(
    *,
    check_id: str,
    rule_ids: list[str],
    classification: str,
    expected: Any,
    observed: Any,
    status: str,
    rationale: str,
    anchors: list[dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Return one deterministic comparison check."""

    return {
        "check_id": check_id,
        "classification": classification,
        "expected": expected,
        "observed": observed,
        "rationale": rationale,
        "rule_ids": rule_ids,
        "status": status,
        "evidence_anchors": [anchor for anchor in (anchors or []) if anchor is not None][:MAX_DIAGNOSTICS],
    }


def expected_counts(expectations: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Extract the comparable prior-art count expectations and structural rule IDs."""

    comparable = expectations.get("expectations", {}).get("comparable_counts", {})
    article_exp = comparable.get("articles", {})
    structure_exp = comparable.get("structure", {})
    rules = expectations.get("expectations", {}).get("validation_rules", {}).get("rules", [])
    comparable_rule_ids = [rule.get("rule_id") for rule in rules if rule.get("classification") == "comparable" and rule.get("rule_id")]
    return article_exp, structure_exp, sorted(comparable_rule_ids)


def compare(expectations: dict[str, Any], records: list[ConsultantHierarchyRecord], parse_diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare observed hierarchy records to prior-art expectations."""

    observed = observed_summary(records)
    article_exp, structure_exp, comparable_rule_ids = expected_counts(expectations)
    article_counts = article_exp.get("counts", {})
    structure_counts = structure_exp.get("counts", {})
    checks: list[dict[str, Any]] = []

    first_article_anchor = observed["first_by_level"].get("article")
    last_article_anchor = observed["last_by_level"].get("article")
    first_chapter_anchor = observed["first_by_level"].get("chapter")
    last_chapter_anchor = observed["last_by_level"].get("chapter")

    for level, expected_key in (("chapter", "chapter_count"), ("article", "article_record_count")):
        expected = structure_counts.get(expected_key) if level == "chapter" else article_counts.get(expected_key)
        observed_count = observed["counts_by_level"].get(level, 0)
        status = "pass" if expected == observed_count else "blocked"
        checks.append(
            comparison_entry(
                check_id=f"COUNT-{level.upper()}",
                rule_ids=["STRUCT-006"] if level == "article" else ["STRUCT-002"],
                classification="major-count",
                expected=expected,
                observed=observed_count,
                status=status,
                rationale="Major chapter/article counts must match prior-art structure safeguards exactly.",
                anchors=[first_chapter_anchor if level == "chapter" else first_article_anchor, last_chapter_anchor if level == "chapter" else last_article_anchor],
            )
        )

    for level, expected_key in (("part", "part_count"), ("clause", "clause_count"), ("subclause", "subclause_count"), ("section", None)):
        expected = article_counts.get(expected_key) if expected_key else 0
        observed_count = observed["counts_by_level"].get(level, 0)
        if expected == observed_count:
            status = "pass"
            rationale = "Granular count matches prior-art output."
        elif observed_count >= expected:
            status = "accepted"
            rationale = "Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL."
        else:
            status = "needs-review"
            rationale = "Granular count is below prior-art evidence and needs parser-boundary review."
        checks.append(
            comparison_entry(
                check_id=f"COUNT-{level.upper()}",
                rule_ids=["STRUCT-004" if level in {"part", "clause", "subclause"} else "STRUCT-005"],
                classification="granular-count",
                expected=expected,
                observed=observed_count,
                status=status,
                rationale=rationale,
                anchors=[observed["first_by_level"].get(level), observed["last_by_level"].get(level)],
            )
        )

    expected_chapter_counts = {str(key): value for key, value in (article_exp.get("chapter_article_counts") or {}).items()}
    checks.append(
        comparison_entry(
            check_id="ORDER-CHAPTER-ARTICLE-COUNTS",
            rule_ids=["STRUCT-003", "STRUCT-006"],
            classification="order-and-parentage",
            expected=expected_chapter_counts,
            observed=observed["chapter_article_counts"],
            status="pass" if expected_chapter_counts == observed["chapter_article_counts"] else "blocked",
            rationale="Articles must map to the same chapter-count distribution even when sections are present.",
            anchors=[first_article_anchor, last_article_anchor],
        )
    )

    checks.append(
        comparison_entry(
            check_id="ORDER-FIRST-LAST-ARTICLES",
            rule_ids=["STRUCT-001", "STRUCT-003"],
            classification="order-and-boundary-samples",
            expected={"first": article_exp.get("first_article_ids"), "last": article_exp.get("last_article_ids")},
            observed={"first": observed["article_markers_first"], "last": observed["article_markers_last"]},
            status="pass"
            if article_exp.get("first_article_ids") == observed["article_markers_first"]
            and article_exp.get("last_article_ids") == observed["article_markers_last"]
            else "blocked",
            rationale="First/last article marker order is the bounded sample for full order drift.",
            anchors=[first_article_anchor, last_article_anchor],
        )
    )

    parent_status = "pass" if observed["missing_parent_count"] == 0 else "blocked"
    checks.append(
        comparison_entry(
            check_id="STRUCT-PARENTS-AND-ORDER",
            rule_ids=[rule for rule in comparable_rule_ids if rule in {"STRUCT-003", "STRUCT-004", "STRUCT-005", "STRUCT-006"}],
            classification="structural-rules",
            expected={"missing_parent_count": 0, "non_monotonic_order_count": 0, "duplicate_id_count": 0},
            observed={
                "missing_parent_count": observed["missing_parent_count"],
                "non_monotonic_order_count": observed["non_monotonic_order_count"],
                "duplicate_id_count": len(observed["duplicate_ids"]),
            },
            status="pass" if parent_status == "pass" and observed["non_monotonic_order_count"] == 0 and not observed["duplicate_ids"] else "blocked",
            rationale="Comparable structural rules require non-orphaned hierarchy records, deterministic IDs, and monotonic source order.",
            anchors=observed["missing_parent_samples"] or observed["non_monotonic_order_samples"] or [first_article_anchor],
        )
    )

    expected_invalidity = {
        "article": article_counts.get("article_invalid_true_count"),
        "part": article_counts.get("part_invalid_true_count"),
        "clause": article_counts.get("clause_invalid_true_count"),
        "subclause": article_counts.get("subclause_invalid_true_count"),
    }
    invalidity_status = "pass" if expected_invalidity == observed["invalidity_marker_counts_by_level"] else "needs-review"
    checks.append(
        comparison_entry(
            check_id="INVALIDITY-MARKER-SAMPLES",
            rule_ids=["SEM-009"],
            classification="advisory-invalidity-marker",
            expected=expected_invalidity,
            observed=observed["invalidity_marker_counts_by_level"],
            status=invalidity_status,
            rationale="Invalidity wording is compared as advisory marker evidence only; it does not determine amendment legal effect.",
            anchors=observed["invalidity_marker_samples"][:10],
        )
    )

    parse_status = "pass" if not parse_diagnostics else "blocked"
    checks.append(
        comparison_entry(
            check_id="INPUT-VALIDATION",
            rule_ids=["STRUCT-001", "STRUCT-002", "STRUCT-003", "STRUCT-004", "STRUCT-005", "STRUCT-006"],
            classification="freshness-and-schema",
            expected={"parse_diagnostic_count": 0},
            observed={"parse_diagnostic_count": len(parse_diagnostics), "samples": parse_diagnostics[:MAX_DIAGNOSTICS]},
            status=parse_status,
            rationale="Comparison fails closed on malformed hierarchy JSONL records.",
        )
    )

    status_counts = Counter(check["status"] for check in checks)
    blocked_checks = [check for check in checks if check["status"] == "blocked"]
    needs_review_checks = [check for check in checks if check["status"] == "needs-review"]
    overall_status = "blocked" if blocked_checks else "needs-review" if needs_review_checks else "pass"

    return {
        "checks": checks,
        "classification_counts": dict(sorted(status_counts.items())),
        "observed": observed,
        "overall_status": overall_status,
        "blocked_check_count": len(blocked_checks),
        "needs_review_check_count": len(needs_review_checks),
    }


def source_entry(path: Path) -> dict[str, Any]:
    """Return source metadata for a comparison input/output artifact."""

    absolute = ROOT / path
    return {
        "path": str(path),
        "exists": absolute.exists(),
        "sha256": sha256_bytes(absolute),
        "size_bytes": absolute.stat().st_size if absolute.exists() else None,
    }


def freshness_map(expected: dict[Path, str]) -> dict[str, bool]:
    """Return whether generated artifact content matches files on disk."""

    result: dict[str, bool] = {}
    for relative_path, content in expected.items():
        path = ROOT / relative_path
        result[str(relative_path)] = path.exists() and path.read_text(encoding="utf-8") == content
    return result


def render_report(summary: dict[str, Any]) -> str:
    """Render compact deterministic Markdown for human review."""

    lines = [
        "# Consultant hierarchy prior-art comparison",
        "",
        "This report compares deterministic Consultant hierarchy records to normalized law-parser prior-art expectations. It is non-authoritative and does not claim legal correctness, parser completeness, amendment effect, or authoritative legal interpretation.",
        "",
        "## Overall status",
        "",
        f"- Overall status: `{summary['overall_status']}`",
        f"- Blocked checks: `{summary['blocked_check_count']}`",
        f"- Needs-review checks: `{summary['needs_review_check_count']}`",
        f"- Classification counts: `{json.dumps(summary['classification_counts'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Source anchors",
        "",
    ]
    for source in summary["sources"]:
        lines.append(f"- `{source['path']}` exists=`{str(source['exists']).lower()}` sha256=`{source.get('sha256')}` size=`{source.get('size_bytes')}`")
    lines.extend(["", "## Checks", ""])
    for check in summary["checks"]:
        lines.extend(
            [
                f"### {check['check_id']} — `{check['status']}`",
                "",
                f"- Classification: `{check['classification']}`",
                f"- Rule IDs: `{', '.join(check['rule_ids'])}`",
                f"- Expected: `{json.dumps(check['expected'], ensure_ascii=False, sort_keys=True)}`",
                f"- Observed: `{json.dumps(check['observed'], ensure_ascii=False, sort_keys=True)}`",
                f"- Rationale: {check['rationale']}",
                "- Evidence anchors:",
            ]
        )
        if check["evidence_anchors"]:
            for anchor in check["evidence_anchors"][:5]:
                lines.append(
                    f"  - `{anchor.get('record_id')}` level=`{anchor.get('level')}` marker=`{anchor.get('marker')}` source_sha=`{anchor.get('source_sha256')}` excerpt_sha=`{anchor.get('excerpt_sha256')}` excerpt={json.dumps(anchor.get('excerpt'), ensure_ascii=False)}"
                )
        else:
            lines.append("  - None")
        lines.append("")
    lines.extend(
        [
            "## Diagnostics",
            "",
            f"- Fatal errors: `{summary['fatal_error_count']}`",
            f"- Artifact freshness: `{json.dumps(summary.get('artifact_freshness'), ensure_ascii=False, sort_keys=True)}`",
            "",
        ]
    )
    return "\n".join(lines)


def build() -> BuildResult:
    """Build comparison JSON and Markdown diagnostics."""

    fatal_errors: list[dict[str, Any]] = []
    expectations, expectations_error = load_json(ROOT / EXPECTATIONS_PATH)
    if expectations_error is not None:
        fatal_errors.append(expectations_error)
        expectations = {}

    records, parse_diagnostics = hierarchy_records(ROOT / HIERARCHY_JSONL_PATH)
    if not (ROOT / HIERARCHY_JSONL_PATH).exists():
        fatal_errors.append(compact_error("missing_jsonl", f"missing hierarchy JSONL file: {HIERARCHY_JSONL_PATH}", path=str(HIERARCHY_JSONL_PATH)))

    comparison = compare(expectations or {}, records, parse_diagnostics)
    sources = [source_entry(HIERARCHY_JSONL_PATH), source_entry(EXPECTATIONS_PATH)]
    missing_sources = [compact_error("missing_source", f"comparison input is missing: {source['path']}", path=source["path"]) for source in sources if not source["exists"]]
    fatal_errors.extend(missing_sources)

    summary = {
        "artifact_paths": {"json": str(JSON_PATH), "report": str(REPORT_PATH)},
        "artifact_freshness": None,
        "blocked_check_count": comparison["blocked_check_count"],
        "checks": comparison["checks"],
        "classification_counts": comparison["classification_counts"],
        "diagnostics_bounded": True,
        "fatal_error_count": len(fatal_errors),
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "needs_review_check_count": comparison["needs_review_check_count"],
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
        "observed": comparison["observed"],
        "overall_status": "blocked" if fatal_errors else comparison["overall_status"],
        "phase": "consultant_hierarchy_prior_art_comparison",
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
    blocked = result.diagnostics.get("overall_status") == "blocked"
    if result.diagnostics.get("fatal_error_count", 0) or blocked:
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
