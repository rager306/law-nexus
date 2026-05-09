from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify-s06-skill-refresh.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_s06_skill_refresh", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(root: Path, relative: str, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


VALID_SKILL_TEXT = """---
name: legalgraph-nexus
description: Routes S06 refreshed LegalGraph Nexus evidence guidance.
---

<objective>
S04 evidence path .gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json.
S05 evidence path .gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md.
S09 evidence path .gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json.
S10 evidence path .gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json.
Mention deepvk/USER-bge-m3 with 1024 dimensions, ai-sage/Giga-Embeddings-instruct, GigaEmbeddings, and blocked-environment runtime diagnostics.
Mention odfdo, odfpy, and raw content.xml parser evidence.
Treat Old_project as prior art with owner, resolution, and verification fields.
Preserve M001 architecture-only guidance by keeping ETL/import, product API, Legal KnowQL parser, and hybrid retrieval product behavior outside this verifier's implementation scope.
</objective>
"""

VALID_EXERCISE_TEXT = """# S06 Skill Evidence Update

References .gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json, .gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md, .gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json, and .gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json.
It covers deepvk/USER-bge-m3, 1024, ai-sage/Giga-Embeddings-instruct, GigaEmbeddings, blocked-environment, odfdo, odfpy, raw content.xml, Old_project, owner, resolution, verification, and M001 architecture-only boundaries.
"""

SKILL_PATHS = [
    ".agents/skills/legalgraph-nexus/SKILL.md",
    ".agents/skills/falkordb-legalgraph/SKILL.md",
    ".agents/skills/russian-legal-evidence/SKILL.md",
]

EVIDENCE_PATHS = [
    ".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json",
    ".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md",
    ".gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json",
    ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
]

EXERCISE_PATH = ".gsd/milestones/M001/slices/S06/S06-SKILL-EVIDENCE-UPDATE.md"


def make_valid_tree(root: Path, *, include_exercise: bool = True) -> None:
    for path in SKILL_PATHS:
        write_fixture(root, path, VALID_SKILL_TEXT)
    for path in EVIDENCE_PATHS:
        write_fixture(root, path, "{}\n")
    if include_exercise:
        write_fixture(root, EXERCISE_PATH, VALID_EXERCISE_TEXT)


def messages(results) -> str:
    return "\n".join(detail for result in results for detail in result.details)


def test_valid_fixture_passes_in_final_mode(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert all(result.ok for result in results), messages(results)


def test_pre_exercise_mode_tolerates_only_missing_exercise(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path, include_exercise=False)

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=True)

    assert all(result.ok for result in results), messages(results)
    assert "optional before T04" in messages(results)


def test_final_mode_requires_s06_exercise(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path, include_exercise=False)

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert EXERCISE_PATH in messages(results)
    assert "missing required S06 exercise artifact" in messages(results)


def test_missing_evidence_path_is_actionable(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    (tmp_path / EVIDENCE_PATHS[0]).unlink()

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert EVIDENCE_PATHS[0] in messages(results)
    assert "missing required evidence artifact" in messages(results)


def test_missing_required_anchor_is_actionable(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    target = tmp_path / SKILL_PATHS[0]
    target.write_text(VALID_SKILL_TEXT.replace("deepvk/USER-bge-m3", ""), encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert SKILL_PATHS[0] in messages(results)
    assert "missing required anchor: deepvk/USER-bge-m3" in messages(results)


def test_stale_decision_reference_fails(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    target = tmp_path / SKILL_PATHS[0]
    target.write_text(VALID_SKILL_TEXT + "\nD017 is authoritative.\n", encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert "stale/nonexistent authoritative decision reference: D017" in messages(results)


def test_parser_overclaim_fails(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    target = tmp_path / SKILL_PATHS[1]
    target.write_text(VALID_SKILL_TEXT + "\nodfpy is the sole final parser for Garant ODT.\n", encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert "parser overclaim" in messages(results)


def test_embedding_quality_overclaim_fails(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    target = tmp_path / SKILL_PATHS[1]
    target.write_text(VALID_SKILL_TEXT + "\nGigaEmbeddings is proven for production legal retrieval quality.\n", encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert "embedding quality overclaim" in messages(results)


def test_architecture_boundary_violation_fails(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    target = tmp_path / SKILL_PATHS[2]
    target.write_text(VALID_SKILL_TEXT + "\nBuild the product API and implement hybrid retrieval now.\n", encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=False)

    assert not all(result.ok for result in results)
    assert "architecture-boundary violation" in messages(results)


def test_empty_exercise_artifact_fails_even_when_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    make_valid_tree(tmp_path)
    (tmp_path / EXERCISE_PATH).write_text("", encoding="utf-8")

    results = verifier.run_checks(root=tmp_path, allow_missing_exercise=True)

    assert not all(result.ok for result in results)
    assert "S06 exercise artifact is empty" in messages(results)
