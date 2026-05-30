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

REQUIRED_ROW_LANGUAGE = {
    "Typed records": ["source category", "lifecycle state", "schema version", "round-tripped"],
    "Schema/frontmatter validation": ["negative validation fixtures", "invalid status", "invalid disposition"],
    "Evidence anchors": ["repo-relative", "resolvable", "broken or local-only anchors are rejected"],
    "Lifecycle transitions": ["candidate", "accepted", "blocked/deferred", "invalid transitions fail"],
    "Transition history": ["previous state", "new state", "rationale", "evidence anchor"],
    "Proof gates": ["proof command/result evidence", "failed proof cannot promote acceptance"],
    "Derived projection boundary": ["marked derived", "non-authoritative", "source records"],
    "Query/recovery": ["authority chain", "blocked findings", "fluent summary text"],
    "Health findings and blocked diagnostics": ["typed", "durable", "queryable", "proof summaries"],
    "Git semantics beyond ordinary git": ["ordinary git", "record-aware", "branding"],
    "Isolation and mutation guard": ["outside the main checkout", "no main-repo `.lex`", "rollback/delete path"],
    "Profile adapters": ["Core/profile boundary", "law-nexus-only", "reusable core"],
}

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


def table_rows(table_text: str) -> list[list[str]]:
    rows = []
    for line in table_text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def capability_row(matrix: str, capability: str) -> list[str]:
    for row in table_rows(matrix):
        if len(row) >= 8 and row[1] == capability:
            return row
    raise AssertionError(f"Missing capability row: {capability}")


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
        row = capability_row(matrix, capability)
        assert len(row) == 8, f"Capability row should have all contract columns: {capability}"
        assert row[2], f"Priority must be populated: {capability}"
        assert row[4], f"Proof method must be populated: {capability}"
        assert row[5], f"Pass condition must be populated: {capability}"
        assert row[6], f"Fail consequence must be populated: {capability}"
        assert row[7], f"Allowed disposition must be populated: {capability}"
        assert any(disposition in row[7] for disposition in ALLOWED_DISPOSITIONS), (
            f"Allowed disposition must use approved status vocabulary: {capability}"
        )
        for required_phrase in REQUIRED_ROW_LANGUAGE[capability]:
            assert required_phrase.casefold() in " | ".join(row).casefold(), (
                f"Capability row is missing required proof-contract language for {capability}: "
                f"{required_phrase}"
            )

    for priority in ["P0 required", "P1 high", "P2 conditional"]:
        assert priority in matrix

    for category in FAILURE_CATEGORIES:
        assert category in matrix, f"Capability rows should reference failure category: {category}"


def test_every_p0_capability_has_pass_fail_and_blocking_semantics() -> None:
    matrix = section(matrix_text(), "Capability Matrix")

    for capability in REQUIRED_CAPABILITIES:
        row = capability_row(matrix, capability)
        priority, proof_method, pass_condition, fail_consequence = row[2], row[4], row[5], row[6]
        if priority != "P0 required":
            continue

        assert proof_method, f"P0 capability requires a proof method: {capability}"
        assert pass_condition, f"P0 capability requires a pass condition: {capability}"
        assert any(category in fail_consequence for category in FAILURE_CATEGORIES), (
            f"P0 fail consequence must name an explicit failure category: {capability}"
        )
        assert any(
            blocking_word in fail_consequence.casefold()
            for blocking_word in ["reject", "blocked", "cannot", "fail closed"]
        ), f"P0 fail consequence must prevent silent adoption: {capability}"


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


def test_no_main_repository_mutation_constraints_are_required() -> None:
    text = matrix_text()
    capability = " | ".join(capability_row(section(text, "Capability Matrix"), "Isolation and mutation guard"))
    scenarios = section(text, "Proof Scenarios")
    failure_modes = section(text, "Failure Modes")

    for required in [
        "outside the main checkout",
        "no main-repo `.lex`",
        "rollback/delete path",
        "fails closed",
    ]:
        assert required in capability

    assert "verify no `.lex` or runtime state mutation in main checkout" in scenarios
    assert "blind `git lex init`" in text
    assert "fail closed" in failure_modes


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
