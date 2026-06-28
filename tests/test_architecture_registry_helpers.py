from __future__ import annotations

from pathlib import Path

from law_nexus.adapters.governance.architecture_registry import (
    display_repo_path,
    is_safe_repo_relative_path,
    is_same_resolved_path,
    load_jsonl_objects,
    load_located_jsonl_objects,
    normalize_repo_path,
)


def test_display_and_normalize_repo_paths(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "prd" / "architecture" / "items.jsonl"
    nested.parent.mkdir(parents=True)
    nested.write_text("", encoding="utf-8")

    assert display_repo_path(nested, root=root) == "prd/architecture/items.jsonl"
    assert normalize_repo_path(Path("prd/architecture/items.jsonl"), root=root) == nested
    assert normalize_repo_path(nested, root=root) == nested


def test_is_same_resolved_path_matches_canonical_paths(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    canonical = root / "prd" / "architecture" / "architecture_items.jsonl"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("", encoding="utf-8")

    assert is_same_resolved_path(Path("prd/architecture/architecture_items.jsonl"), {canonical}, root=root)
    assert not is_same_resolved_path(Path("prd/architecture/other.jsonl"), {canonical}, root=root)


def test_safe_repo_relative_path_rejects_absolute_parent_and_exec_paths() -> None:
    assert is_safe_repo_relative_path("prd/architecture/items.jsonl")
    assert not is_safe_repo_relative_path("")
    assert not is_safe_repo_relative_path("/tmp/items.jsonl")
    assert not is_safe_repo_relative_path("../items.jsonl")
    assert not is_safe_repo_relative_path("prd/../items.jsonl")
    assert not is_safe_repo_relative_path(".gsd/exec/raw-output.json")
    assert not is_safe_repo_relative_path("bad\x00path")


def test_load_jsonl_objects_returns_records_and_diagnostics(tmp_path: Path) -> None:
    path = tmp_path / "items.jsonl"
    path.write_text(
        '\n'.join(
            [
                '{"id": "A", "record_kind": "item"}',
                "",
                "not-json",
                '["not", "object"]',
                '{"id": "B", "record_kind": "item"}',
            ]
        ),
        encoding="utf-8",
    )

    records, diagnostics = load_jsonl_objects(path)
    located_records, located_diagnostics = load_located_jsonl_objects(path)

    assert [record["id"] for record in records] == ["A", "B"]
    assert [(record.line_number, record.record["id"]) for record in located_records] == [(1, "A"), (5, "B")]
    assert diagnostics == located_diagnostics
    assert [(diagnostic.rule, diagnostic.line_number) for diagnostic in diagnostics] == [
        ("malformed-jsonl", 3),
        ("jsonl-object", 4),
    ]


def test_load_jsonl_objects_reports_read_failures(tmp_path: Path) -> None:
    records, diagnostics = load_jsonl_objects(tmp_path / "missing.jsonl")

    assert records == []
    assert len(diagnostics) == 1
    assert diagnostics[0].rule == "read-jsonl"
    assert "missing.jsonl" in diagnostics[0].message
