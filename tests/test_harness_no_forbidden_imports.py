"""Enforce the Python repository-harness boundary from ADR-0007."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = ROOT / "src" / "law_nexus_harness"
CARGO_MANIFESTS = [ROOT / "Cargo.toml", ROOT / "crates" / "ln-status" / "Cargo.toml"]
FORBIDDEN_MODULES = {"law_nexus", "ctypes", "cffi", "pyo3"}
# Product-domain rules and in-process dynamic loaders. Architecture-direction
# vocabulary that keeps FalkorDB historical-only is allowed and checked
# separately so governor remediation text does not create a false positive.
FORBIDDEN_SOURCE_TERMS = {
    "cdll",
    "dlopen",
    "normstatement",
    "evidencespan",
    "citation policy",
    "legal authority",
    "xml parser",
    "odt parser",
}
# Allowed harness mentions of the historical graph backend name.
_ALLOWED_FALKORDB_PATTERNS = (
    re.compile(r'"falkordb"\s*:\s*"historical-only"'),
    re.compile(r"legacy acp/git-lex/falkordb"),
    re.compile(r"falkordb=historical-only"),
    # Governor historical-test-debt-visibility probe references the decommissioned
    # era name 'falkordb' as a detection keyword; this is a historical-only
    # mention by construction (the probe inventories historical debt).
    re.compile(r"falkordb\|git"),
    # active-surface-era-noise probe: detection keyword regex source fragment
    # plus historical-only ban language in docstrings/remediation.
    re.compile(r"falkordb\(\?:lite\)"),
    re.compile(r"falkordb/acp/git-lex/pyo3/minimax", re.IGNORECASE),
    re.compile(r"historical[- ]only.*falkordb|falkordb.*historical", re.IGNORECASE),
    re.compile(r"unqualified historical-only era", re.IGNORECASE),
)


def _python_sources() -> list[Path]:
    return sorted(
        path
        for path in HARNESS_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and ".venv" not in path.parts
    )


_REVIEW_CASE_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "pydantic",
        "adaptix",
        "pathlib",
        "argparse",
        "gsd",
        "law_nexus",
        "ctypes",
        "cffi",
        "pyo3",
    }
)
_REVIEW_CASE_INNER_MODULE_PATHS = frozenset(
    {
        "review_case/__init__.py",
        "review_case/domain.py",
        "review_case/policy.py",
        "review_case/ports.py",
        "review_case/application.py",
    }
)
_REVIEW_CASE_FORBIDDEN_LOCAL_MODULES = frozenset(
    {
        "law_nexus_harness.cli",
        "law_nexus_harness.governor",
        "law_nexus_harness.preflight",
    }
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_harness_imports_no_product_or_in_process_bridge_modules() -> None:
    violations: list[str] = []
    for path in _python_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for module in imported:
                if module.split(".", 1)[0].lower() in FORBIDDEN_MODULES:
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []


def test_harness_contains_no_product_domain_rules_or_dynamic_loader_terms() -> None:
    violations: list[str] = []
    for path in _python_sources():
        source = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_SOURCE_TERMS:
            if term in source:
                violations.append(f"{path.relative_to(ROOT)} contains {term!r}")
    assert violations == []


def test_harness_falkordb_mentions_are_historical_only_direction() -> None:
    """Governor may name FalkorDB only to enforce historical-only direction."""
    violations: list[str] = []
    for path in _python_sources():
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        if "falkordb" not in lowered:
            continue
        # Strip string/comment contexts that match allowlist patterns first.
        residual = lowered
        for pattern in _ALLOWED_FALKORDB_PATTERNS:
            residual = pattern.sub("", residual)
        if "falkordb" in residual:
            violations.append(f"{path.relative_to(ROOT)} has non-historical-only FalkorDB mention")
    assert violations == []


def test_forbidden_source_terms_still_ban_product_domain_examples() -> None:
    """Regression: product-domain terms remain in the forbidden set."""
    for term in (
        "normstatement",
        "evidencespan",
        "citation policy",
        "legal authority",
        "xml parser",
        "odt parser",
        "cdll",
        "dlopen",
    ):
        assert term in FORBIDDEN_SOURCE_TERMS
    assert "falkordb" not in FORBIDDEN_SOURCE_TERMS


def test_rust_status_tracer_has_zero_third_party_dependencies() -> None:
    crate_manifest = CARGO_MANIFESTS[1].read_text(encoding="utf-8")
    dependency_section = crate_manifest.split("[dependencies]", 1)[1].strip()
    assert dependency_section == ""


def test_harness_package_is_separate_from_python_product_package() -> None:
    assert HARNESS_ROOT.is_dir()
    assert HARNESS_ROOT.parent / "law_nexus" != HARNESS_ROOT
    names = {path.name for path in _python_sources()}
    assert {
        "__init__.py",
        "__main__.py",
        "cli.py",
        "result_schema.py",
        "subprocess_runner.py",
    } <= names
    assert any(
        path.relative_to(HARNESS_ROOT).parts[0] == "review_case" for path in _python_sources()
    )


def test_review_case_inner_modules_reject_outer_framework_imports() -> None:
    violations: list[str] = []
    for path in _python_sources():
        relative = path.relative_to(HARNESS_ROOT)
        if relative.as_posix() not in _REVIEW_CASE_INNER_MODULE_PATHS:
            continue
        for module in _imported_modules(path):
            root = module.split(".", 1)[0].lower()
            if root in _REVIEW_CASE_FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{relative} imports {module}")
            if module in _REVIEW_CASE_FORBIDDEN_LOCAL_MODULES:
                violations.append(f"{relative} imports {module}")
            if module.startswith("law_nexus_harness.") and module.split(".")[1] in {
                "cli",
                "governor",
                "preflight",
            }:
                violations.append(f"{relative} imports {module}")
    assert violations == []
