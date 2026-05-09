#!/usr/bin/env python3
"""Verify the M001/S02 project-local skill baseline.

Default mode is final mode: all required S02 outputs must exist and pass
structural/content checks. During T01, use --partial-router to validate the
router skill while tolerating focused skills and the final exercise being
incomplete or absent.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

ROUTER = Path(".agents/skills/legalgraph-nexus/SKILL.md")
FALKOR = Path(".agents/skills/falkordb-legalgraph/SKILL.md")
FALKOR_ARCH_WORKFLOW = Path(".agents/skills/falkordb-legalgraph/workflows/answer-architecture-question.md")
FALKOR_CAPABILITY_WORKFLOW = Path(".agents/skills/falkordb-legalgraph/workflows/check-capability-claim.md")
FALKOR_PROTOCOL = Path(".agents/skills/falkordb-legalgraph/references/falkordb-evidence-protocol.md")
RUSSIAN = Path(".agents/skills/russian-legal-evidence/SKILL.md")
RUSSIAN_ODT_WORKFLOW = Path(".agents/skills/russian-legal-evidence/workflows/review-odt-parser-assumption.md")
RUSSIAN_STRUCTURE_REF = Path(".agents/skills/russian-legal-evidence/references/russian-legal-structure.md")
RUSSIAN_PRIOR_ART_REF = Path(".agents/skills/russian-legal-evidence/references/old-project-prior-art.md")
RUSSIAN_EVIDENCE_TEMPLATE = Path(".agents/skills/russian-legal-evidence/templates/evidence-answer.md")
EXERCISE = Path(".gsd/milestones/M001/slices/S02/S02-SKILL-EXERCISE.md")

SKILL_PATHS = [ROUTER, FALKOR, RUSSIAN]
FALKOR_DETAIL_PATHS = [FALKOR_ARCH_WORKFLOW, FALKOR_CAPABILITY_WORKFLOW, FALKOR_PROTOCOL]
RUSSIAN_DETAIL_PATHS = [RUSSIAN_ODT_WORKFLOW, RUSSIAN_STRUCTURE_REF, RUSSIAN_PRIOR_ART_REF, RUSSIAN_EVIDENCE_TEMPLATE]
FINAL_REQUIRED_PATHS = [*SKILL_PATHS, *FALKOR_DETAIL_PATHS, *RUSSIAN_DETAIL_PATHS, EXERCISE]

REQUIRED_TERMS = {
    ROUTER: [
        "LegalGraph Nexus",
        "FalkorDB Legal Graph",
        "Legal Nexus",
        "Legal KnowQL",
        "EvidenceSpan",
        "SourceBlock",
        "citation-safe retrieval",
        "deterministic-first",
        "temporal-first",
        "LLM non-authoritative",
        "M001",
        "architecture-only",
        "ETL/import",
        "KnowQL parser",
        "falkordb-legalgraph",
        "russian-legal-evidence",
    ],
    FALKOR: [
        "FalkorDB",
        "GraphBLAS",
        "OpenCypher",
        "full-text",
        "vector",
        "UDF",
        "GitNexus",
        "/root/vendor-source/",
        "capability",
        "smoke",
        "LLM non-authoritative",
        "docs-backed/source-pending",
        "smoke-needed",
        "contradicted",
        "out-of-scope",
    ],
    RUSSIAN: [
        "Russian legal",
        "EvidenceSpan",
        "SourceBlock",
        "44-fz.odt",
        "Old_project",
        "LLM non-authoritative",
        "citation-safe retrieval",
        "temporal-first",
        "deterministic-first",
        "ODT",
        "S05",
        "S07/S08",
    ],
}

FALKOR_DETAIL_REQUIRED_TERMS = {
    FALKOR_ARCH_WORKFLOW: [
        "gitnexus_list_repos",
        "gitnexus_query",
        "gitnexus_context",
        "/root/vendor-source/",
        "docs-backed/source-pending",
        "smoke-needed",
        "out-of-scope",
        "S03",
        "S04",
    ],
    FALKOR_CAPABILITY_WORKFLOW: [
        "docs-backed",
        "source-backed",
        "runtime-smoke",
        "contradicted",
        "out-of-scope",
        "Neo4j",
        "GraphBLAS",
        "S03",
        "S04",
    ],
    FALKOR_PROTOCOL: [
        "confirmed",
        "docs-backed/source-pending",
        "smoke-needed",
        "contradicted",
        "out-of-scope",
        "FalkorDB",
        "GraphBLAS",
        "OpenCypher",
        "full-text",
        "vector",
        "UDF",
        "GitNexus",
        "/root/vendor-source/",
    ],
}

RUSSIAN_DETAIL_REQUIRED_TERMS = {
    RUSSIAN_ODT_WORKFLOW: [
        "WordML-vs-ODT",
        "44-fz.odt",
        "law-source/garant/44-fz.odt",
        "S05",
        "S07/S08",
        "Old_project",
        "EvidenceSpan",
        "SourceBlock",
        "hypothesis-pending-S05",
    ],
    RUSSIAN_STRUCTURE_REF: [
        "Russian legal",
        "EvidenceSpan",
        "SourceBlock",
        "citation-safe retrieval",
        "temporal-first",
        "deterministic-first",
        "law",
        "article",
        "part",
        "clause",
        "subclause",
        "44-fz.odt",
        "LLM non-authoritative",
    ],
    RUSSIAN_PRIOR_ART_REF: [
        "Old_project",
        "prior art",
        "keep-as-is",
        "adapt",
        "defer",
        "reject",
        "WordML/XML",
        "44-fz.odt",
        "S05",
        "S07/S08",
    ],
    RUSSIAN_EVIDENCE_TEMPLATE: [
        "EvidenceSpan",
        "SourceBlock",
        "Claim class",
        "source path",
        "confidence",
        "downstream owner",
        "LLM non-authoritative",
    ],
}

EXERCISE_SECTIONS = [
    "## Question",
    "## Skills / Workflows Used",
    "## Evidence Sources",
    "## Claim Classification Table",
    "## Downstream Owners",
    "## Verification Notes",
]

CLAIM_CLASSES = [
    "Verified from source",
    "Bounded by evidence",
    "Hypothesis / pending verification",
    "Out of scope for M001",
]

XML_TAG_RE = re.compile(r"<([a-z][a-z0-9_-]*)>.*?</\1>", re.DOTALL)
TAG_OPEN_RE = re.compile(r"<([a-z][a-z0-9_-]*)>")
TAG_CLOSE_RE = re.compile(r"</([a-z][a-z0-9_-]*)>")


@dataclass
class CheckResult:
    label: str
    ok: bool
    details: list[str]


def rel(path: Path) -> str:
    return path.as_posix()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, text, ["missing YAML frontmatter opener"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text, ["missing YAML frontmatter closer"]
    raw = text[4:end]
    body = text[end + 5 :]
    fields: dict[str, str] = {}
    for idx, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"frontmatter line {idx} is not key: value")
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, body, errors


def check_skill(path: Path, root: Path = ROOT) -> CheckResult:
    full = root / path
    errors: list[str] = []
    if not full.exists():
        return CheckResult(rel(path), False, ["missing required skill file"])
    if full.stat().st_size == 0:
        return CheckResult(rel(path), False, ["skill file is empty"])

    text = full.read_text(encoding="utf-8")
    fields, body, fm_errors = parse_frontmatter(text)
    errors.extend(fm_errors)

    expected_name = path.parent.name
    if fields.get("name") != expected_name:
        errors.append(f"frontmatter name must be {expected_name!r}")
    if not fields.get("description"):
        errors.append("frontmatter description is required")
    elif len(fields["description"]) < 80:
        errors.append("frontmatter description should be intent-rich, not terse")

    heading_lines = [line for line in body.splitlines() if re.match(r"^#{1,6}\s+", line)]
    if heading_lines:
        errors.append("skill body must not use markdown headings: " + "; ".join(heading_lines[:3]))

    opens = TAG_OPEN_RE.findall(body)
    closes = TAG_CLOSE_RE.findall(body)
    if not opens or not closes:
        errors.append("skill body must contain XML-like semantic tags")
    if opens != closes:
        errors.append(f"XML-like tag order mismatch: opens={opens}, closes={closes}")
    if not XML_TAG_RE.search(body):
        errors.append("skill body must include at least one complete XML-like section")

    for term in REQUIRED_TERMS.get(path, []):
        if term not in text:
            errors.append(f"missing required vocabulary term: {term}")

    return CheckResult(rel(path), not errors, errors or ["ok"])


def check_text_file(path: Path, required_terms: Iterable[str], root: Path = ROOT) -> CheckResult:
    full = root / path
    errors: list[str] = []
    if not full.exists():
        return CheckResult(rel(path), False, ["missing required workflow/reference file"])
    if full.stat().st_size == 0:
        return CheckResult(rel(path), False, ["workflow/reference file is empty"])
    text = full.read_text(encoding="utf-8")
    opens = TAG_OPEN_RE.findall(text)
    closes = TAG_CLOSE_RE.findall(text)
    if not opens or not closes:
        errors.append("workflow/reference file must contain XML-like semantic tags")
    elif sorted(opens) != sorted(closes):
        errors.append(f"XML-like tag mismatch: opens={opens}, closes={closes}")
    if not XML_TAG_RE.search(text):
        errors.append("workflow/reference file must include at least one complete XML-like section")
    for term in required_terms:
        if term not in text:
            errors.append(f"missing required vocabulary term: {term}")
    return CheckResult(rel(path), not errors, errors or ["ok"])


def check_exercise(path: Path = EXERCISE, root: Path = ROOT, required: bool = True) -> CheckResult:
    full = root / path
    errors: list[str] = []
    if not full.exists():
        if required:
            return CheckResult(rel(path), False, ["missing required exercise file"])
        return CheckResult(rel(path), True, ["optional in partial mode and not present"])
    if full.stat().st_size == 0:
        return CheckResult(rel(path), False, ["exercise file is empty"])
    text = full.read_text(encoding="utf-8")
    for section in EXERCISE_SECTIONS:
        if section not in text:
            errors.append(f"missing exercise section: {section}")
    for claim_class in CLAIM_CLASSES:
        if claim_class not in text:
            errors.append(f"missing claim class: {claim_class}")
    placeholders = ["T04", "PLACEHOLDER", "not complete"]
    if not any(marker in text for marker in placeholders):
        errors.append("exercise skeleton should clearly signal pending completion for T04")
    forbidden_completion = [
        "exercise complete",
        "final exercise complete",
        "all claims verified",
    ]
    lowered = text.lower()
    for phrase in forbidden_completion:
        if phrase in lowered:
            errors.append(f"exercise skeleton overclaims completion: {phrase}")
    return CheckResult(rel(path), not errors, errors or ["ok"])


def check_required_paths(paths: Iterable[Path], root: Path = ROOT) -> CheckResult:
    missing = [rel(path) for path in paths if not (root / path).exists()]
    empty = [rel(path) for path in paths if (root / path).exists() and (root / path).stat().st_size == 0]
    details = []
    if missing:
        details.append("missing: " + ", ".join(missing))
    if empty:
        details.append("empty: " + ", ".join(empty))
    return CheckResult("required files", not details, details or ["ok"])


def run_checks(
    partial_router: bool,
    root: Path = ROOT,
    allow_missing_russian: bool = False,
    allow_missing_exercise_final: bool = False,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    if partial_router:
        results.append(check_required_paths([ROUTER], root))
        results.append(check_skill(ROUTER, root))
        results.append(check_exercise(EXERCISE, root, required=False))
        for optional_skill in (FALKOR, RUSSIAN):
            if (root / optional_skill).exists():
                results.append(check_skill(optional_skill, root))
            else:
                results.append(CheckResult(rel(optional_skill), True, ["optional in partial mode and not present"]))
    else:
        required_paths = [ROUTER, FALKOR, *FALKOR_DETAIL_PATHS]
        if not allow_missing_russian:
            required_paths.extend([RUSSIAN, *RUSSIAN_DETAIL_PATHS])
        if not allow_missing_exercise_final:
            required_paths.append(EXERCISE)
        results.append(check_required_paths(required_paths, root))
        results.append(check_skill(ROUTER, root))
        results.append(check_skill(FALKOR, root))
        for detail_path in FALKOR_DETAIL_PATHS:
            results.append(check_text_file(detail_path, FALKOR_DETAIL_REQUIRED_TERMS[detail_path], root))
        if allow_missing_russian and not (root / RUSSIAN).exists():
            results.append(CheckResult(rel(RUSSIAN), True, ["optional because --allow-missing-russian was set"]))
        else:
            results.append(check_skill(RUSSIAN, root))
            for detail_path in RUSSIAN_DETAIL_PATHS:
                results.append(check_text_file(detail_path, RUSSIAN_DETAIL_REQUIRED_TERMS[detail_path], root))
        results.append(check_exercise(EXERCISE, root, required=not allow_missing_exercise_final))
    return results


def print_results(results: list[CheckResult]) -> None:
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.label}")
        for detail in result.details:
            print(f"  - {detail}")


def write_fixture(root: Path, relative: Path, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def run_self_test() -> int:
    valid_router = """---
name: legalgraph-nexus
description: Routes LegalGraph Nexus architecture, FalkorDB Legal Graph, Legal Nexus, Legal KnowQL, EvidenceSpan, SourceBlock, citation-safe retrieval, deterministic-first, temporal-first, and LLM non-authoritative M001 architecture-only questions.
---

<objective>LegalGraph Nexus FalkorDB Legal Graph Legal Nexus Legal KnowQL EvidenceSpan SourceBlock citation-safe retrieval deterministic-first temporal-first LLM non-authoritative M001 architecture-only ETL/import KnowQL parser falkordb-legalgraph russian-legal-evidence</objective>
"""
    malformed_missing_name = valid_router.replace("name: legalgraph-nexus\n", "")
    malformed_heading = valid_router + "\n## Bad Heading\n"
    malformed_no_xml = valid_router.replace("<objective>", "").replace("</objective>", "")
    malformed_missing_vocab = valid_router.replace("Legal KnowQL", "")

    cases = [
        ("valid partial router passes", valid_router, True),
        ("missing name fails", malformed_missing_name, False),
        ("markdown heading fails", malformed_heading, False),
        ("missing XML-like tags fails", malformed_no_xml, False),
        ("missing vocabulary fails", malformed_missing_vocab, False),
    ]

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for label, content, should_pass in cases:
            case_root = tmp_root / re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            write_fixture(case_root, ROUTER, content)
            results = run_checks(partial_router=True, root=case_root)
            passed = all(result.ok for result in results)
            if passed != should_pass:
                failures.append(f"{label}: expected {should_pass}, got {passed}")
    if failures:
        print("Self-test failures:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Self-test passed: malformed frontmatter, markdown headings, missing XML tags, missing vocabulary, and valid partial router cases behaved as expected.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partial-router",
        action="store_true",
        help="T01 mode: require and validate only the router, while reporting focused skills as optional.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run verifier negative tests against temporary malformed fixtures.",
    )
    parser.add_argument(
        "--allow-missing-russian",
        action="store_true",
        help="T02/T03 mode: validate router and FalkorDB skill artifacts while tolerating the later Russian legal evidence skill.",
    )
    parser.add_argument(
        "--allow-missing-exercise-final",
        action="store_true",
        help="T02/T03 mode: tolerate the final S02 exercise remaining a placeholder until T04.",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    results = run_checks(
        partial_router=args.partial_router,
        allow_missing_russian=args.allow_missing_russian,
        allow_missing_exercise_final=args.allow_missing_exercise_final,
    )
    print_results(results)
    if all(result.ok for result in results):
        print("S02 skill verification passed." + (" (partial-router mode)" if args.partial_router else ""))
        return 0
    print("S02 skill verification failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
