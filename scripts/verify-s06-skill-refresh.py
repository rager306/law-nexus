#!/usr/bin/env python3
"""Verify the M001/S06 skill-refresh evidence contract.

Default mode is final mode: project-local LegalGraph Nexus skills, required
upstream evidence artifacts, and the S06 skill-evidence exercise must all be
present and must satisfy the refreshed evidence anchors. During T01-T03, pass
``--allow-missing-exercise`` to document that the S06 exercise is intentionally
not created yet; this mode only tolerates that one missing final artifact and
still fails missing skill evidence anchors or overclaims.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]

SKILL_PATHS = [
    Path(".agents/skills/legalgraph-nexus/SKILL.md"),
    Path(".agents/skills/falkordb-legalgraph/SKILL.md"),
    Path(".agents/skills/russian-legal-evidence/SKILL.md"),
]

EVIDENCE_ARTIFACTS = [
    Path(".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json"),
    Path(".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md"),
    Path(".gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json"),
    Path(".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json"),
]

EXERCISE = Path(".gsd/milestones/M001/slices/S06/S06-SKILL-EVIDENCE-UPDATE.md")

# Terms that must be present in the refreshed skill corpus. The file sets are
# intentionally explicit so diagnostics name the stale/missing skill directly.
REQUIRED_SKILL_ANCHORS: dict[Path, list[str]] = {
    Path(".agents/skills/legalgraph-nexus/SKILL.md"): [
        ".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json",
        ".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md",
        ".gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json",
        ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
        "deepvk/USER-bge-m3",
        "1024",
        "ai-sage/Giga-Embeddings-instruct",
        "GigaEmbeddings",
        "blocked-environment",
        "odfdo",
        "odfpy",
        "content.xml",
        "Old_project",
        "owner",
        "resolution",
        "verification",
        "M001",
        "architecture-only",
    ],
    Path(".agents/skills/falkordb-legalgraph/SKILL.md"): [
        ".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json",
        ".gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json",
        ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
        "deepvk/USER-bge-m3",
        "1024",
        "ai-sage/Giga-Embeddings-instruct",
        "GigaEmbeddings",
        "blocked-environment",
        "owner",
        "resolution",
        "verification",
        "M001",
        "architecture-only",
    ],
    Path(".agents/skills/russian-legal-evidence/SKILL.md"): [
        ".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md",
        "odfdo",
        "odfpy",
        "content.xml",
        "Old_project",
        "owner",
        "resolution",
        "verification",
        "M001",
        "architecture-only",
    ],
}

EXERCISE_ANCHORS = [
    *(artifact.as_posix() for artifact in EVIDENCE_ARTIFACTS),
    "deepvk/USER-bge-m3",
    "1024",
    "ai-sage/Giga-Embeddings-instruct",
    "GigaEmbeddings",
    "blocked-environment",
    "odfdo",
    "odfpy",
    "content.xml",
    "Old_project",
    "owner",
    "resolution",
    "verification",
    "M001",
    "architecture-only",
]

STALE_DECISIONS = ["D004", "D007", "D009", "D017"]
STALE_DECISION_RE = re.compile(r"\b(" + "|".join(STALE_DECISIONS) + r")\b")

OVERCLAIM_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "parser overclaim",
        re.compile(r"odfpy\s+(?:is|as|will be|should be)\s+(?:the\s+)?(?:sole|final|authoritative|production)", re.I),
        "odfpy must not be described as the sole/final/authoritative parser; S05 evidence keeps odfdo/odfpy/raw content.xml bounded.",
    ),
    (
        "parser overclaim",
        re.compile(r"(?:sole|final|authoritative|production)\s+parser[^.\n]{0,80}\bodfpy\b", re.I),
        "odfpy must not be described as the sole/final/authoritative parser; S05 evidence keeps odfdo/odfpy/raw content.xml bounded.",
    ),
    (
        "embedding quality overclaim",
        re.compile(r"GigaEmbeddings[^.\n]{0,120}\b(?:proven|confirmed|validated)[^.\n]{0,120}\bproduction\s+legal\s+retrieval\s+quality\b", re.I),
        "GigaEmbeddings runtime availability must not be upgraded into proven production legal retrieval quality.",
    ),
    (
        "embedding quality overclaim",
        re.compile(r"production\s+legal\s+retrieval\s+quality[^.\n]{0,120}\b(?:proven|confirmed|validated)\b", re.I),
        "Production legal retrieval quality remains unproven by S09/S10 local embedding/runtime evidence.",
    ),
    (
        "architecture-boundary violation",
        re.compile(r"\b(?:build|implement|ship|create)\b[^.\n]{0,120}\b(?:product\s+API|ETL/import|ETL|import\s+pipeline|Legal\s+KnowQL\s+parser|KnowQL\s+parser|hybrid\s+retrieval)\b", re.I),
        "M001 skill guidance must stay architecture-only and must not direct product ETL/import/API/KnowQL/hybrid retrieval implementation.",
    ),
]


@dataclass
class CheckResult:
    label: str
    ok: bool
    details: list[str]


def rel(path: Path) -> str:
    return path.as_posix()


def read_text(path: Path, root: Path) -> tuple[str | None, str | None]:
    full = root / path
    if not full.exists():
        return None, f"{rel(path)}: missing required file"
    if full.stat().st_size == 0:
        return "", f"{rel(path)}: file is empty"
    try:
        return full.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"{rel(path)}: malformed text file ({exc})"


def check_required_evidence_artifacts(root: Path = ROOT) -> CheckResult:
    errors: list[str] = []
    for artifact in EVIDENCE_ARTIFACTS:
        full = root / artifact
        if not full.exists():
            errors.append(f"{rel(artifact)}: missing required evidence artifact")
        elif full.stat().st_size == 0:
            errors.append(f"{rel(artifact)}: required evidence artifact is empty")
    return CheckResult("required S04/S05/S09/S10 evidence artifacts", not errors, errors or ["ok"])


def check_skill_file(path: Path, root: Path = ROOT) -> CheckResult:
    text, error = read_text(path, root)
    errors: list[str] = []
    if error:
        return CheckResult(rel(path), False, [error])
    assert text is not None

    for anchor in REQUIRED_SKILL_ANCHORS[path]:
        if anchor not in text:
            errors.append(f"{rel(path)}: missing required anchor: {anchor}")

    stale_ids = sorted(set(STALE_DECISION_RE.findall(text)))
    for decision_id in stale_ids:
        errors.append(f"{rel(path)}: stale/nonexistent authoritative decision reference: {decision_id}")

    for label, pattern, explanation in OVERCLAIM_PATTERNS:
        if pattern.search(text):
            errors.append(f"{rel(path)}: {label}: {explanation}")

    return CheckResult(rel(path), not errors, errors or ["ok"])


def check_exercise(path: Path = EXERCISE, root: Path = ROOT, allow_missing: bool = False) -> CheckResult:
    full = root / path
    if not full.exists():
        if allow_missing:
            return CheckResult(rel(path), True, [f"{rel(path)}: optional before T04 because --allow-missing-exercise was set"])
        return CheckResult(rel(path), False, [f"{rel(path)}: missing required S06 exercise artifact"])
    if full.stat().st_size == 0:
        return CheckResult(rel(path), False, [f"{rel(path)}: S06 exercise artifact is empty"])

    text, error = read_text(path, root)
    if error:
        return CheckResult(rel(path), False, [error])
    assert text is not None

    errors: list[str] = []
    for anchor in EXERCISE_ANCHORS:
        if anchor not in text:
            errors.append(f"{rel(path)}: missing required exercise anchor: {anchor}")
    stale_ids = sorted(set(STALE_DECISION_RE.findall(text)))
    for decision_id in stale_ids:
        errors.append(f"{rel(path)}: stale/nonexistent authoritative decision reference: {decision_id}")
    for label, pattern, explanation in OVERCLAIM_PATTERNS:
        if pattern.search(text):
            errors.append(f"{rel(path)}: {label}: {explanation}")
    return CheckResult(rel(path), not errors, errors or ["ok"])


def run_checks(root: Path = ROOT, allow_missing_exercise: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = [check_required_evidence_artifacts(root)]
    for skill_path in SKILL_PATHS:
        results.append(check_skill_file(skill_path, root))
    results.append(check_exercise(EXERCISE, root, allow_missing=allow_missing_exercise))
    return results


def print_results(results: Sequence[CheckResult]) -> None:
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.label}")
        for detail in result.details:
            print(f"  - {detail}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-missing-exercise",
        action="store_true",
        help=(
            "Pre-T04 mode: tolerate only the missing S06-SKILL-EVIDENCE-UPDATE.md exercise artifact; "
            "skill anchors, evidence artifacts, and overclaim checks still run."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    results = run_checks(allow_missing_exercise=args.allow_missing_exercise)
    print_results(results)
    if all(result.ok for result in results):
        print("S06 skill-refresh verification passed." + (" (missing exercise allowed)" if args.allow_missing_exercise else ""))
        return 0
    print("S06 skill-refresh verification failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
