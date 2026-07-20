"""Read-only and stale-detection checks for Consultant hierarchy artifacts.

Only two subprocesses run: one single ``--check`` and one corpus ``--check``.
Both use the interpreter supplied by ``uv run pytest`` and must leave every
watched repository file byte- and metadata-identical. Stale cases use an
isolated temporary root and never modify tracked artifacts.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build-consultant-hierarchy-records.py"
MANIFEST_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_baseline_manifest.json"
SINGLE_OUTPUTS = [
    ROOT / "prd" / "parser" / "consultant_hierarchy_records.json",
    ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl",
    ROOT / "prd" / "parser" / "consultant_hierarchy_records.md",
]
CORPUS_OUTPUTS = [
    ROOT / "prd" / "parser" / "consultant_hierarchy_corpus_records.json",
    ROOT / "prd" / "parser" / "consultant_hierarchy_corpus_records.jsonl",
    ROOT / "prd" / "parser" / "consultant_hierarchy_corpus_records.md",
]


def _snapshot(paths: list[Path]) -> dict[Path, tuple[int, int, str]]:
    return {
        path: (
            path.stat().st_mtime_ns,
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in paths
    }


def _tree_metadata(root: Path) -> dict[Path, tuple[int, int]]:
    return {
        path: (path.stat().st_mtime_ns, path.stat().st_size)
        for path in root.rglob("*")
        if path.is_file()
    }


def _load_builder_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "readonly_consultant_hierarchy_builder", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def check_results() -> dict[str, dict]:
    watched = SINGLE_OUTPUTS + CORPUS_OUTPUTS + [MANIFEST_PATH]
    before = _snapshot(watched)
    lex_before = _tree_metadata(ROOT / ".lex")
    law_before = _tree_metadata(ROOT / "law-source")

    results: dict[str, dict] = {}
    for mode, extra in (("single", []), ("corpus", ["--corpus"])):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *extra, "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert completed.returncode == 0, completed.stdout[-1000:] + completed.stderr[-1000:]
        results[mode] = json.loads(completed.stdout)

    assert _snapshot(watched) == before, "--check changed output bytes or metadata"
    assert _tree_metadata(ROOT / ".lex") == lex_before, "--check mutated .lex"
    assert _tree_metadata(ROOT / "law-source") == law_before, "--check mutated source fixtures"
    return results


@pytest.mark.slow
def test_single_and_corpus_cli_checks_are_fresh_and_read_only(
    check_results: dict[str, dict],
) -> None:
    assert check_results["single"]["status"] == "pass"
    assert check_results["single"]["mode"] == "single"
    assert check_results["corpus"]["status"] == "pass"
    assert check_results["corpus"]["mode"] == "corpus"
    assert check_results["single"]["emitted_counts_by_level"]["document"] == 1
    assert check_results["corpus"]["totals"]["record_count"] == 15249


def test_check_artifacts_detects_stale_temporary_copy_without_repair(tmp_path: Path) -> None:
    module = _load_builder_module()
    paths = module.ArtifactPaths(
        jsonl=Path("single.jsonl"),
        json=Path("single.json"),
        report=Path("single.md"),
        mode="single",
    )
    result = module.BuildResult(
        records=[],
        jsonl="record\n",
        summary_json="{}\n",
        report_md="# report\n",
        diagnostics={},
        paths=paths,
    )
    original_root = module.ROOT
    module.ROOT = tmp_path
    try:
        module.write_artifacts(result)
        fresh_snapshot = _snapshot(
            [tmp_path / path for path in (paths.jsonl, paths.json, paths.report)]
        )
        assert module.check_artifacts(result) is True
        assert (
            _snapshot([tmp_path / path for path in (paths.jsonl, paths.json, paths.report)])
            == fresh_snapshot
        )

        stale_path = tmp_path / paths.report
        stale_path.write_text("# stale\n", encoding="utf-8")
        stale_snapshot = _snapshot([stale_path])
        assert module.check_artifacts(result) is False
        assert _snapshot([stale_path]) == stale_snapshot
    finally:
        module.ROOT = original_root
