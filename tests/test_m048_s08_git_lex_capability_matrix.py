from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md"

REQUIRED_SECTIONS = [
    "Status",
    "Authority Rule",
    "Allowed Dispositions",
    "Failure Categories",
    "Capability Matrix",
    "Proof Scenarios",
    "Priority Interpretation",
    "Current M048 Evidence Boundary",
    "Failure Modes",
    "Load Profile",
    "Negative Tests",
    "Observability Impact",
]

REQUIRED_CAPABILITIES = [
    "Typed records",
    "Schema/frontmatter validation",
    "Evidence anchors",
    "Lifecycle transitions",
    "Transition history",
    "Proof gates",
    "Derived projection boundary",
    "Query/recovery",
    "Health findings and blocked diagnostics",
    "Git semantics beyond ordinary git",
    "Isolation and mutation guard",
    "Profile adapters",
]

ALLOWED_DISPOSITIONS = [
    "use git-lex runtime",
    "absorb approach",
    "implement ACP-native",
    "adapter later",
    "reject",
    "blocked",
]

FAILURE_CATEGORIES = [
    "ImitativeArtifact",
    "BlockedCapability",
    "UnsupportedGitLexRuntime",
    "UnsafeMutation",
    "InsufficientEvidence",
]

FORBIDDEN_OVERCLAIMS = [
    "full runtime git-lex adoption is approved",
    "full acp git-lex runtime adoption is approved",
    "git-lex is adopted.",
    "runtime git-lex adoption is approved",
    "r035 is validated",
    "r037 is validated",
    "r038 is validated",
    "validates r035",
    "validates r037",
    "validates r038",
]


def matrix_text() -> str:
    assert MATRIX_PATH.exists(), f"Missing matrix document: {MATRIX_PATH.relative_to(ROOT)}"
    return MATRIX_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required matrix section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_matrix_exists_and_has_required_sections() -> None:
    text = matrix_text()

    assert text.startswith("# M048 S08 git-lex Capability Matrix")
    for heading in REQUIRED_SECTIONS:
        body = section(text, heading)
        assert body.strip(), f"Section must not be empty: {heading}"

    assert "No artifact is authoritative by shape alone." in section(text, "Authority Rule")
    assert "source category + lifecycle state + evidence anchor + proof gate or accepted decision" in text


def test_allowed_dispositions_and_failure_categories_are_explicit() -> None:
    text = matrix_text()
    dispositions = section(text, "Allowed Dispositions")
    failures = section(text, "Failure Categories")

    for disposition in ALLOWED_DISPOSITIONS:
        assert f"`{disposition}`" in dispositions

    for category in FAILURE_CATEGORIES:
        assert f"`{category}`" in failures

    assert "blocked" in section(text, "Observability Impact")
    assert "ACP-native" in section(text, "Observability Impact")
    assert "adapter-later" in section(text, "Observability Impact")
    assert "runtime-adopt" in section(text, "Observability Impact")


def test_capability_matrix_contains_all_required_capabilities_and_columns() -> None:
    text = matrix_text()
    matrix = section(text, "Capability Matrix")

    expected_header = (
        "| # | Capability | Priority | Why ACP needs it | Proof method | "
        "Pass condition | Fail consequence | Allowed disposition |"
    )
    assert expected_header in matrix

    for capability in REQUIRED_CAPABILITIES:
        assert f"| {capability} |" in matrix, f"Missing capability row: {capability}"

    for priority in ["P0 required", "P1 high", "P2 conditional"]:
        assert priority in matrix

    for category in FAILURE_CATEGORIES:
        assert category in matrix, f"Capability rows should reference failure category: {category}"


def test_proof_contract_covers_required_scenarios_and_boundaries() -> None:
    text = matrix_text()
    scenarios = section(text, "Proof Scenarios")

    for scenario in [
        "A — Source record lifecycle",
        "B — Blocked claim",
        "C — Projection boundary",
        "D — Recovery query",
        "E — Git semantics",
        "F — Isolation safety",
    ]:
        assert scenario in scenarios

    assert "projection remains diagnostic" in scenarios.casefold()
    assert "no `.lex`" in scenarios
    assert "rollback/delete path" in scenarios
    assert "git semantics" in section(text, "Capability Matrix").casefold()


def test_matrix_preserves_runtime_adoption_and_requirement_non_validation_boundaries() -> None:
    text = matrix_text()
    lowered = text.casefold()

    for claim in FORBIDDEN_OVERCLAIMS:
        assert claim not in lowered, f"Forbidden overclaim present: {claim}"

    evidence_boundary = section(text, "Current M048 Evidence Boundary")
    assert "Runtime git-lex acquisition/build/invocation remains blocked/deferred" in evidence_boundary
    assert "`R035`, `R037`, and `R038` remain non-validated" in evidence_boundary
    assert "`R046`, `R047`, and `R048` remain hard boundaries" in evidence_boundary

    failure_modes = section(text, "Failure Modes")
    assert "do not clone, install, initialize, or claim runtime adoption" in failure_modes
    assert "Main repository gains `.lex`" in failure_modes
    assert "Network acquisition is deliberately not a dependency" in failure_modes


def test_quality_gate_sections_are_populated_with_document_level_evidence() -> None:
    text = matrix_text()

    failure_modes = section(text, "Failure Modes")
    assert "Tracked source artifacts" in failure_modes
    assert "Runtime git-lex surface" in failure_modes
    assert "Filesystem / repository state" in failure_modes
    assert "Validation/proof evidence" in failure_modes
    assert "Human-readable matrix drift" in failure_modes

    load_profile = section(text, "Load Profile")
    assert "no production runtime load dimension" in load_profile
    assert "At 10x the expected matrix size" in load_profile
    assert "No pool sizing, rate limiting, pagination, caching" in load_profile

    negative_tests = section(text, "Negative Tests")
    assert "tests/test_m048_s08_git_lex_capability_matrix.py" in negative_tests
    assert "rejects omission of any required ACP capability" in negative_tests
    assert "requirement-validation leaks" in negative_tests
    assert "document-level" in negative_tests
