from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/git-lex-isolated-proof"

REQUIRED_KINDS = {
    "requirement_binding": "RB-ACP-0001",
    "architecture_decision": "AD-ACP-0001",
    "architecture_prompt_record": "APR-ACP-0001",
    "architecture_proposal": "AP-ACP-0001",
    "decision_candidate": "DC-ACP-0001",
    "proof_gate": "PG-ACP-0001",
    "evidence_anchor": "EA-ACP-0001",
    "architecture_health_finding": "AHF-ACP-0001",
    "derived_projection_reference": "DPR-ACP-0001",
    "profile_constraint": "PC-LN-0001",
    "blocked_action": "BA-ACP-0001",
}

FIXTURE_RECORD_IDS = set(REQUIRED_KINDS.values())
PROJECT_SPECIFIC_TERMS = {
    "law-nexus",
    "Russian legal evidence",
    "FalkorDB",
    "parser completeness",
    "LLM authority",
    "GSD operational quirks",
    "R035",
    "R037",
    "R038",
}
NON_CLAIM_FLAGS = [
    "claims_product_readiness",
    "claims_parser_completeness",
    "claims_falkordb_ingestion",
    "claims_legal_correctness",
    "claims_r035_validated",
    "claims_r037_validated",
    "claims_r038_validated",
]
UNSAFE_ANCHOR_PATTERNS = [
    r"^/",
    r"\.gsd/exec/",
    r"\.lex(?:/|$)",
    r"provider_payload",
    r"raw_vectors?",
    r"secret",
]


def fixture_files() -> list[Path]:
    assert FIXTURE_DIR.exists(), f"Missing isolated git-lex fixture dir: {FIXTURE_DIR.relative_to(ROOT)}"
    return sorted(FIXTURE_DIR.glob("*.md"))


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n([\s\S]*?)\n---\n", text)
    assert match, f"Missing YAML frontmatter in {path.relative_to(ROOT)}"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"Frontmatter must parse to a mapping in {path.relative_to(ROOT)}"
    return data


def records() -> dict[str, dict[str, Any]]:
    parsed = {record["id"]: record for record in map(parse_frontmatter, fixture_files())}
    assert len(parsed) == len(fixture_files()), "Record ids must be unique across fixture files"
    return parsed


def flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        out: list[Any] = []
        for item in value.values():
            out.extend(flatten(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten(item))
        return out
    return [value]


def referenced_fixture_ids(record: dict[str, Any]) -> set[str]:
    values = flatten(record)
    return {value for value in values if isinstance(value, str) and value in FIXTURE_RECORD_IDS and value != record["id"]}


def assert_repo_relative_path(path: str) -> None:
    candidate = Path(path)
    assert not candidate.is_absolute(), f"Anchor path must be repository-relative, got {path!r}"
    assert ".." not in candidate.parts, f"Anchor path must not escape the repository, got {path!r}"
    assert not any(re.search(pattern, path, flags=re.IGNORECASE) for pattern in UNSAFE_ANCHOR_PATTERNS), (
        f"Unsafe durable anchor path in isolated fixture: {path!r}"
    )


def test_fixture_pack_declares_full_reusable_acp_taxonomy_once() -> None:
    parsed = records()
    ids_by_kind = {record["record_kind"]: record["id"] for record in parsed.values()}

    assert ids_by_kind == REQUIRED_KINDS
    assert set(parsed) == set(REQUIRED_KINDS.values())
    assert not (FIXTURE_DIR / ".lex").exists(), "S04 fixture must not create git-lex .lex state"


def test_record_identity_relationship_references_and_safe_anchors_are_valid() -> None:
    parsed = records()
    files_by_id = {parse_frontmatter(path)["id"]: path for path in fixture_files()}

    for record_id, record in parsed.items():
        assert files_by_id[record_id].name.startswith(record_id.split("-")[0]), (
            f"Fixture filename should remain traceable to record id for {record_id}"
        )
        assert record.get("title"), f"{record_id} should have a title"
        safety = record.get("safety")
        assert isinstance(safety, dict), f"{record_id} should expose safety flags"
        assert all(safety.get(flag) is False for flag in NON_CLAIM_FLAGS), (
            f"{record_id} must not claim product/R035/R037/R038 validation via S04 fixtures"
        )

    graph = {record_id: referenced_fixture_ids(record) for record_id, record in parsed.items()}
    unresolved = sorted(ref for refs in graph.values() for ref in refs if ref not in parsed)
    assert not unresolved, f"Fixture relationship references must resolve: {unresolved}"

    required_edges = {
        "APR-ACP-0001": {"AP-ACP-0001", "EA-ACP-0001"},
        "AP-ACP-0001": {"APR-ACP-0001", "DC-ACP-0001", "EA-ACP-0001"},
        "DC-ACP-0001": {"APR-ACP-0001", "AP-ACP-0001", "PG-ACP-0001", "BA-ACP-0001"},
        "AD-ACP-0001": {"PG-ACP-0001", "EA-ACP-0001"},
        "PG-ACP-0001": {"EA-ACP-0001", "DC-ACP-0001", "BA-ACP-0001"},
        "AHF-ACP-0001": {"BA-ACP-0001", "PG-ACP-0001", "EA-ACP-0001"},
        "BA-ACP-0001": {"PG-ACP-0001", "AHF-ACP-0001", "EA-ACP-0001"},
        "RB-ACP-0001": {"PG-ACP-0001", "PC-LN-0001", "EA-ACP-0001"},
        "DPR-ACP-0001": {"APR-ACP-0001", "AP-ACP-0001", "DC-ACP-0001", "PG-ACP-0001", "EA-ACP-0001"},
        "PC-LN-0001": {"PG-ACP-0001", "EA-ACP-0001"},
    }
    for record_id, expected_refs in required_edges.items():
        assert expected_refs <= graph[record_id], f"{record_id} missing required refs {expected_refs - graph[record_id]}"

    anchor = parsed["EA-ACP-0001"]
    assert_repo_relative_path(anchor["repo_relative_path"])
    assert (ROOT / anchor["repo_relative_path"]).exists(), "Primary evidence anchor should point to tracked source input"
    for path in anchor.get("secondary_repo_relative_paths", []):
        assert_repo_relative_path(path)
        assert (ROOT / path).exists(), f"Secondary evidence anchor is missing: {path}"


def test_lifecycle_and_proof_gate_chain_cover_required_mechanics() -> None:
    parsed = records()
    prompt = parsed["APR-ACP-0001"]
    proposal = parsed["AP-ACP-0001"]
    candidate = parsed["DC-ACP-0001"]
    decision = parsed["AD-ACP-0001"]
    gate = parsed["PG-ACP-0001"]
    finding = parsed["AHF-ACP-0001"]
    blocked_action = parsed["BA-ACP-0001"]

    assert prompt["status"] == "linked"
    assert proposal["status"] == "candidate_extracted"
    assert candidate["status"] == "requires_proof"
    assert decision["status"] == "requires_proof"
    assert gate["status"] == "pending_evidence"
    assert finding["status"] == "blocked"
    assert blocked_action["status"] == "active"

    mechanics_text = " ".join(gate["claim_or_requirement"].casefold().split())
    for term in [
        "typed records",
        "validation",
        "extraction/projection",
        "query/recovery",
        "lifecycle/proof-gate",
        "source/projection boundary",
        "blocked-action mechanics",
    ]:
        assert term in mechanics_text

    command = "uv run pytest tests/test_m048_s04_git_lex_isolated_fixtures.py"
    assert command in gate["verification_commands"]
    assert any(".lex" in action for action in finding["allowed_next_actions"] + [blocked_action["action"], blocked_action["reason"]])
    assert "PG-ACP-0001" in blocked_action["required_unblock_evidence"][0]


def test_source_records_are_authoritative_and_derived_projection_reference_is_not() -> None:
    parsed = records()
    derived = parsed["DPR-ACP-0001"]
    requirement_binding = parsed["RB-ACP-0001"]

    assert derived["authority_status"] == "non_authoritative"
    blocked_uses = " ".join(derived["blocked_acp_use"]).casefold()
    assert "serve as sole source anchor" in blocked_uses
    assert "validate requirements" in blocked_uses
    assert "override source records" in blocked_uses

    assert requirement_binding["requirement_status"] == "not-validated-by-this-fixture"
    binding_blocked_uses = " ".join(requirement_binding["blocked_acp_use"]).casefold()
    assert "validate requirements from projection evidence alone" in binding_blocked_uses
    assert "infer active requirements from stale project-state outputs" in binding_blocked_uses


def test_profile_specific_constraints_do_not_leak_into_reusable_core_records() -> None:
    parsed = records()
    profile = parsed["PC-LN-0001"]
    assert profile["record_kind"] == "profile_constraint"
    assert profile["profile_id"] == "law-nexus"
    assert profile["required_proof_gates"] == ["PG-ACP-0001"]

    profile_text = yaml.safe_dump(profile, sort_keys=True)
    for term in PROJECT_SPECIFIC_TERMS:
        assert term in profile_text

    for record_id, record in parsed.items():
        if record_id == "PC-LN-0001":
            continue
        record_text = yaml.safe_dump(record, sort_keys=True)
        leaked = sorted(term for term in PROJECT_SPECIFIC_TERMS if term in record_text)
        assert not leaked, f"Project-specific profile terms leaked into reusable core record {record_id}: {leaked}"


def test_negative_boundaries_block_main_repo_mutation_and_validation_overclaims() -> None:
    parsed = records()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in fixture_files())

    assert not (ROOT / ".lex").exists(), "The main repository must not gain .lex state from this fixture task"
    assert not list(FIXTURE_DIR.rglob(".lex")), "The isolated fixture directory must not contain .lex state"
    assert "git lex init" in parsed["BA-ACP-0001"]["action"]
    assert parsed["BA-ACP-0001"]["severity"] == "critical"

    forbidden_validation_patterns = [
        r"R035\s+(?:is\s+)?validated",
        r"R037\s+(?:is\s+)?validated",
        r"R038\s+(?:is\s+)?validated",
        r"claims_r035_validated:\s+true",
        r"claims_r037_validated:\s+true",
        r"claims_r038_validated:\s+true",
    ]
    violations = [pattern for pattern in forbidden_validation_patterns if re.search(pattern, combined, re.IGNORECASE)]
    assert not violations, f"Fixture must not contain R035/R037/R038 validation claims: {violations}"

    for record in parsed.values():
        safety = record["safety"]
        assert safety["claims_r035_validated"] is False
        assert safety["claims_r037_validated"] is False
        assert safety["claims_r038_validated"] is False
