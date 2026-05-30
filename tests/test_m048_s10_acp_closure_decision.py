from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md"
DELTA_PATH = ROOT / "prd/architecture/acp/M048-S10-ACP-NATIVE-IMPLEMENTATION-DELTA.md"
PACKAGE_PATH = ROOT / "prd/architecture/acp/M048-S10-ACP-CLOSURE-PACKAGE.md"

REQUIRED_CAPABILITIES = [
    "Typed records",
    "Schema/frontmatter validation",
    "Evidence anchors",
    "Lifecycle states and transitions",
    "Transition history",
    "Proof gates",
    "Derived projection boundary",
    "Query/recovery",
    "Health findings and blocked diagnostics",
    "Git semantics beyond ordinary git",
    "Isolation and mutation guards",
    "Profile adapters",
]

ALLOWED_DISPOSITIONS = [
    "implement ACP-native",
    "adapter later",
    "absorb approach",
    "reject",
    "blocked",
]

FORBIDDEN_OVERCLAIMS = [
    "full runtime git-lex adoption is approved",
    "full acp git-lex runtime adoption is approved",
    "git-lex is adopted.",
    "runtime git-lex adoption is approved",
    "use git-lex runtime | typed records",
    "use git-lex runtime | schema/frontmatter validation",
    "use git-lex runtime | proof gates",
    "r035 is validated",
    "r037 is validated",
    "r038 is validated",
    "validates r035",
    "validates r037",
    "validates r038",
    "law-nexus architecture binding may start before acp closure",
]


def read(path: Path) -> str:
    assert path.exists(), f"Missing expected S10 artifact: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def markdown_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_s10_decision_records_every_required_capability_with_non_runtime_disposition() -> None:
    text = read(DECISION_PATH)
    table = section(text, "Per-capability adoption table")
    rows = markdown_rows(table)

    assert rows[0][:4] == ["Capability", "Evidence", "Status", "Final disposition"]
    by_capability = {row[0]: row for row in rows[1:] if row}
    assert set(REQUIRED_CAPABILITIES) <= set(by_capability)

    for capability in REQUIRED_CAPABILITIES:
        row = by_capability[capability]
        disposition = row[3]
        assert disposition, f"Missing final disposition for {capability}"
        assert any(allowed in disposition for allowed in ALLOWED_DISPOSITIONS), (
            f"Disposition for {capability} must use bounded S08 vocabulary: {disposition}"
        )
        assert "use git-lex runtime" not in disposition, (
            f"S10 must not approve runtime git-lex for {capability}"
        )
        assert row[4], f"Missing rationale for {capability}"
        assert row[5], f"Missing risk for {capability}"
        assert row[6], f"Missing ACP delta for {capability}"


def test_s10_decision_is_not_binary_and_preserves_adapter_later_boundary() -> None:
    text = read(DECISION_PATH)
    lowered = text.casefold()

    assert "do **not** adopt runtime git-lex" in lowered
    assert "per-capability adoption table" in lowered
    assert "`use git-lex runtime` | none from m048 evidence." in lowered
    assert "`adapter later`" in text
    assert "future isolated adapter/runtime spike" in lowered
    assert "ordinary git" in lowered
    assert "runtime git-lex acquisition/build/invocation" in lowered
    assert "blocked" in lowered


def test_s10_artifacts_preserve_authority_and_anti_imitation_rule() -> None:
    combined = "\n".join([read(DECISION_PATH), read(DELTA_PATH)])

    assert "No artifact is authoritative by shape alone." in combined
    assert "source category + lifecycle state + evidence anchor + proof gate or accepted decision" in combined
    assert "anti-imitation" in combined.casefold()
    assert "polished summaries" in combined.casefold() or "polished text" in combined.casefold()
    assert "generated projections" in combined.casefold() or "derived projection" in combined.casefold()
    assert "source truth" in combined.casefold()
    assert "non-authoritative" in combined.casefold()


def test_no_main_repo_mutation_and_law_nexus_binding_block_are_explicit() -> None:
    decision = read(DECISION_PATH)
    delta = read(DELTA_PATH)
    combined = f"{decision}\n{delta}"

    for required in [
        "Do not run blind `git lex init`",
        "do not create or mutate .lex state in /root/law-nexus",
        "No-main-repo mutation rule",
        "No main-repo git-lex state",
        "Downstream law-nexus architecture binding remains blocked",
        "Do not begin downstream law-nexus architecture binding until",
    ]:
        assert required in combined


def test_profile_requirements_are_not_validated_or_absorbed_into_acp_core() -> None:
    combined = "\n".join([read(DECISION_PATH), read(DELTA_PATH)])
    lowered = combined.casefold()

    for requirement_id in ["R035", "R037", "R038"]:
        assert requirement_id in combined
        assert f"{requirement_id.lower()} is validated" not in lowered
        assert f"{requirement_id.lower()} has been validated" not in lowered
        assert f"validates {requirement_id.lower()}" not in lowered
        assert f"validated {requirement_id.lower()}" not in lowered

    assert "law-nexus profile owns" in lowered
    assert "not reusable acp core semantics" in lowered
    assert "not validated by acp closure" in lowered


def test_no_full_adoption_claim_with_blocked_critical_capabilities() -> None:
    combined = "\n".join([read(DECISION_PATH), read(DELTA_PATH)])
    lowered = combined.casefold()

    for forbidden in FORBIDDEN_OVERCLAIMS:
        assert forbidden not in lowered, f"Forbidden S10 closure overclaim present: {forbidden}"

    assert "runtime git-lex remains blocked" in lowered
    assert "proof gates" in lowered
    assert "implement acp-native" in lowered
    assert "unsupportedgitlexruntime" in lowered or "unsupported runtime" in lowered


def test_closure_package_preserves_s08_s10_evidence_and_remaining_blockers_when_present() -> None:
    if not PACKAGE_PATH.exists():
        return

    text = read(PACKAGE_PATH)
    lowered = text.casefold()

    for required in [
        "S08 Evidence",
        "S09 Evidence",
        "S10 Evidence",
        "Requirement status package",
        "Closure verdict",
        "Remaining blockers",
        "Allowed next actions",
        "Blocked actions",
    ]:
        assert f"## {required}" in text

    for artifact in [
        "M048-S08-GIT-LEX-CAPABILITY-MATRIX.md",
        "M048-S08-GIT-LEX-PROOF-CONTRACT.md",
        "M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md",
        "M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md",
        "M048-S09-INDEPENDENT-PROOF-REVIEW.md",
        "M048-S10-GIT-LEX-ADOPTION-DECISION.md",
        "M048-S10-ACP-NATIVE-IMPLEMENTATION-DELTA.md",
    ]:
        assert artifact in text

    assert "acp closure is complete for m048 decision-package scope" in lowered
    assert "runtime git-lex remains blocked" in lowered
    assert "r035" in lowered and "not validated" in lowered
    assert "r037" in lowered and "not validated" in lowered
    assert "r038" in lowered and "not validated" in lowered
    assert "do not validate r035/r037/r038" in lowered
    assert "no downstream law-nexus binding before this package" not in lowered
