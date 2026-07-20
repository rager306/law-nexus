"""Enforce the Python repository-harness boundary from ADR-0007."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = ROOT / "src" / "law_nexus_harness"
CARGO_MANIFESTS = [ROOT / "Cargo.toml", ROOT / "crates" / "ln-status" / "Cargo.toml"]
FORBIDDEN_MODULES = {"law_nexus", "ctypes", "cffi", "pyo3"}
FORBIDDEN_SOURCE_TERMS = {
    "cdll",
    "dlopen",
    "falkordb",
    "normstatement",
    "evidencespan",
    "citation policy",
    "legal authority",
    "xml parser",
    "odt parser",
}


def _python_sources() -> list[Path]:
    return sorted(HARNESS_ROOT.glob("*.py"))


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


def test_rust_status_tracer_has_zero_third_party_dependencies() -> None:
    crate_manifest = CARGO_MANIFESTS[1].read_text(encoding="utf-8")
    dependency_section = crate_manifest.split("[dependencies]", 1)[1].strip()
    assert dependency_section == ""


def test_harness_package_is_separate_from_python_product_package() -> None:
    assert HARNESS_ROOT.is_dir()
    assert HARNESS_ROOT.parent / "law_nexus" != HARNESS_ROOT
    assert {path.name for path in _python_sources()} >= {
        "__init__.py",
        "__main__.py",
        "cli.py",
        "result_schema.py",
        "subprocess_runner.py",
    }
