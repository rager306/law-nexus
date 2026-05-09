"""Smoke tests for the S04 Python tooling baseline."""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
PYTHON_VERSION_FILE = PROJECT_ROOT / ".python-version"

REQUIRED_DISTRIBUTIONS = {
    "pytest",
    "pytest-xdist",
    "hypothesis",
    "ruff",
    "ty",
    "pyrefly",
    "adaptix",
}
REQUIRED_IMPORT_MODULES = ("pytest", "hypothesis", "adaptix")


def _read_python_version_pin(path: Path = PYTHON_VERSION_FILE) -> tuple[int, int]:
    raw = path.read_text(encoding="utf-8").strip()
    parts = raw.split(".")
    if len(parts) < 2:
        raise ValueError(f"Python version pin must include major.minor: {raw!r}")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Python version pin must be numeric: {raw!r}") from exc
    return major, minor


def _read_pyproject(path: Path = PYPROJECT) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_uv_environment_uses_python_313_or_newer() -> None:
    assert sys.version_info >= (3, 13), sys.version


def test_python_version_pin_is_present_and_targets_python_313() -> None:
    assert PYTHON_VERSION_FILE.is_file()
    assert _read_python_version_pin() == (3, 13)


@pytest.mark.parametrize("raw", ["", "3", "three.thirteen", "3.x"])
def test_python_version_pin_rejects_malformed_values(tmp_path: Path, raw: str) -> None:
    version_file = tmp_path / ".python-version"
    version_file.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError):
        _read_python_version_pin(version_file)


def test_pyproject_metadata_is_present_for_lsp_and_uv_discovery() -> None:
    assert PYPROJECT.is_file()
    pyproject = _read_pyproject()

    project = cast("dict[str, Any]", pyproject["project"])
    assert project["requires-python"] == ">=3.13"

    tool_config = cast("dict[str, Any]", pyproject["tool"])
    uv_config = cast("dict[str, Any]", tool_config["uv"])
    assert uv_config["package"] is False
    assert "ruff" in tool_config
    assert "pytest" in tool_config


def test_pyproject_reader_fails_when_metadata_is_absent(tmp_path: Path) -> None:
    missing = tmp_path / "pyproject.toml"

    with pytest.raises(FileNotFoundError):
        _read_pyproject(missing)


def test_required_tooling_distributions_are_installed() -> None:
    missing = []
    for distribution in sorted(REQUIRED_DISTRIBUTIONS):
        try:
            importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            missing.append(distribution)

    assert missing == []


@pytest.mark.parametrize("module_name", REQUIRED_IMPORT_MODULES)
def test_core_runtime_modules_import(module_name: str) -> None:
    importlib.import_module(module_name)
