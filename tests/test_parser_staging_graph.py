from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build-parser-staging-graph.py"
DOCUMENT_RECORDS_PATH = ROOT / "prd" / "parser" / "odt_document_records.jsonl"
SOURCE_BLOCK_RECORDS_PATH = ROOT / "prd" / "parser" / "odt_source_block_records.jsonl"
RELATION_RECORDS_PATH = ROOT / "prd" / "parser" / "consultant_relation_candidates.jsonl"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_parser_staging_graph", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def fixture_paths(tmp_path: Path, *, documents: list[dict[str, Any]], source_blocks: list[dict[str, Any]], relations: list[dict[str, Any]]) -> tuple[Path, Path, Path]:
    documents_path = write_jsonl(tmp_path / "documents.jsonl", documents)
    source_blocks_path = write_jsonl(tmp_path / "source_blocks.jsonl", source_blocks)
    relations_path = write_jsonl(tmp_path / "relations.jsonl", relations)
    return documents_path, source_blocks_path, relations_path


def build_from_rows(
    tmp_path: Path,
    *,
    documents: list[dict[str, Any]] | None = None,
    source_blocks: list[dict[str, Any]] | None = None,
    relations: list[dict[str, Any]] | None = None,
):
    builder = load_builder_module()
    paths = fixture_paths(
        tmp_path,
        documents=documents if documents is not None else [read_jsonl(DOCUMENT_RECORDS_PATH)[0]],
        source_blocks=source_blocks if source_blocks is not None else [read_jsonl(SOURCE_BLOCK_RECORDS_PATH)[0]],
        relations=relations if relations is not None else [],
    )
    return builder.build_staging_graph(
        document_records_path=paths[0],
        source_block_records_path=paths[1],
        relation_candidate_records_path=paths[2],
    )


def diagnostics_by_rule(result) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for diagnostic in result.diagnostics:
        grouped.setdefault(diagnostic.rule, []).append(diagnostic)
    return grouped


def test_multigraph_preserves_real_artifact_counts_and_non_authoritative_state():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()

    rules = diagnostics_by_rule(result)
    assert result.summary.error_count == 0
    assert result.summary.warning_count >= 3
    assert result.summary.status == "pass"
    assert {diagnostic.severity for diagnostic in result.diagnostics} <= {"warning", "info"}
    assert {"unresolved_subject_ref", "unresolved_object_ref", "missing_source_block_record"} <= set(rules)
    assert "candidate_only_relation" in rules
    assert "no_falkordb_load_executed" in rules
    assert isinstance(result.graph, nx.MultiDiGraph)
    assert result.graph.is_multigraph()
    assert result.summary.node_counts == {
        "document": 2,
        "source_block": 48,
        "unresolved_reference": 2,
    }
    assert result.summary.edge_counts == {
        "contains_source_block": 48,
        "relation_candidate": 1,
    }
    assert result.summary.non_authoritative is True
    assert result.summary.relation_candidate_edge_keys == ["REL-CONS-0001"]


def test_keyed_consultant_relation_uses_unresolved_reference_nodes_without_doc_rewrite():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()
    relation = result.graph.get_edge_data(
        "consultant-list:law-source/consultant/Список документов (5).xml",
        "consultant:LAW:179581@11.05.2026",
        key="REL-CONS-0001",
    )

    assert relation is not None
    assert relation["edge_kind"] == "relation_candidate"
    assert relation["record"].id == "REL-CONS-0001"
    assert result.graph.nodes["consultant-list:law-source/consultant/Список документов (5).xml"]["node_kind"] == "unresolved_reference"
    assert result.graph.nodes["consultant:LAW:179581@11.05.2026"]["node_kind"] == "unresolved_reference"
    assert not result.graph.has_edge("DOC-PP-60", "DOC-44-FZ", key="REL-CONS-0001")
    assert not result.graph.has_edge("DOC-44-FZ", "DOC-PP-60", key="REL-CONS-0001")


def test_source_block_records_keep_full_attributes_and_document_order_links():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()
    document_blocks = [
        edge_data["record"].id
        for _, target, key, edge_data in result.graph.out_edges("DOC-44-FZ", keys=True, data=True)
        if edge_data["edge_kind"] == "contains_source_block"
        for node_data in [result.graph.nodes[target]]
        if node_data["record"].document_id == "DOC-44-FZ"
    ]
    ordered_records = [result.graph.nodes[node_id]["record"] for node_id in document_blocks]

    assert document_blocks == sorted(document_blocks, key=lambda block_id: result.graph.nodes[block_id]["record"].order_index)
    assert ordered_records[0].record_kind == "source_block"
    assert ordered_records[0].document_id == "DOC-44-FZ"
    assert ordered_records[0].excerpt
    assert result.graph.nodes["DOC-44-FZ"]["record"].title
    assert result.graph.has_edge("DOC-44-FZ", ordered_records[0].id, key=f"contains:{ordered_records[0].id}")


def test_malformed_jsonl_becomes_path_line_rule_error_diagnostic(tmp_path: Path):
    builder = load_builder_module()
    malformed = tmp_path / "bad.jsonl"
    missing = tmp_path / "missing.jsonl"
    malformed.write_text('{"record_kind":"document"\n', encoding="utf-8")

    result = builder.build_staging_graph(
        document_records_path=malformed,
        source_block_records_path=missing,
        relation_candidate_records_path=missing,
    )

    assert result.graph.number_of_nodes() == 0
    assert result.summary.status == "fail"
    assert result.summary.error_count == len(result.diagnostics)
    assert {diagnostic.rule for diagnostic in result.diagnostics} >= {"json_invalid", "missing_file"}
    assert any(diagnostic.path == malformed and diagnostic.line == 1 for diagnostic in result.diagnostics)
    assert all(diagnostic.severity == "error" for diagnostic in result.diagnostics)
    assert all(diagnostic.message for diagnostic in result.diagnostics)


def test_duplicate_global_ids_fail_with_rule_qualified_diagnostic(tmp_path: Path):
    documents = read_jsonl(DOCUMENT_RECORDS_PATH)

    result = build_from_rows(tmp_path, documents=[documents[0], documents[0].copy()])
    rules = diagnostics_by_rule(result)

    assert result.summary.status == "fail"
    assert result.summary.error_count == 1
    assert rules["duplicate_global_id"][0].record_id == "DOC-44-FZ"
    assert rules["duplicate_global_id"][0].field == "id"


def test_duplicate_document_identity_hazard_fails_without_legal_claim(tmp_path: Path):
    document = read_jsonl(DOCUMENT_RECORDS_PATH)[0]
    duplicate_identity = document | {"id": "DOC-44-FZ-COPY"}

    result = build_from_rows(tmp_path, documents=[document, duplicate_identity])
    diagnostic = diagnostics_by_rule(result)["duplicate_document_identity"][0]

    assert result.summary.status == "fail"
    assert diagnostic.severity == "error"
    assert diagnostic.field == "source_path"
    assert "legal correctness" not in diagnostic.message.lower()
    assert result.summary.legal_correctness_claimed is False
    assert result.summary.falkordb_loading_runtime_readiness_claimed is False


def test_source_block_with_unknown_document_id_fails_with_localizable_diagnostic(tmp_path: Path):
    source_block = read_jsonl(SOURCE_BLOCK_RECORDS_PATH)[0] | {"id": "BLOCK-MISSING-DOC-000", "document_id": "DOC-MISSING"}

    result = build_from_rows(tmp_path, source_blocks=[source_block])
    diagnostic = diagnostics_by_rule(result)["missing_document_endpoint"][0]

    assert result.summary.status == "fail"
    assert diagnostic.severity == "error"
    assert diagnostic.record_id == "BLOCK-MISSING-DOC-000"
    assert diagnostic.field == "document_id"


def test_missing_relation_source_block_id_fails_through_parser_validation(tmp_path: Path):
    relation = read_jsonl(RELATION_RECORDS_PATH)[0]
    relation.pop("source_block_id")

    result = build_from_rows(tmp_path, relations=[relation])
    diagnostic = result.diagnostics[0]

    assert result.summary.status == "fail"
    assert diagnostic.severity == "error"
    assert diagnostic.record_kind == "relation_candidate"
    assert diagnostic.field == "source_block_id"


def test_invalid_relation_status_fails_through_parser_validation(tmp_path: Path):
    relation = read_jsonl(RELATION_RECORDS_PATH)[0] | {"status": "confirmed"}

    result = build_from_rows(tmp_path, relations=[relation])
    diagnostic = result.diagnostics[0]

    assert result.summary.status == "fail"
    assert diagnostic.severity == "error"
    assert diagnostic.record_id == "REL-CONS-0001"
    assert diagnostic.field == "status"


def test_unresolved_refs_and_missing_source_block_are_warnings_that_keep_relation_key(tmp_path: Path):
    relation = read_jsonl(RELATION_RECORDS_PATH)[0]

    result = build_from_rows(tmp_path, relations=[relation])
    rules = diagnostics_by_rule(result)

    assert result.summary.status == "pass"
    assert result.summary.error_count == 0
    assert {"unresolved_subject_ref", "unresolved_object_ref", "missing_source_block_record"} <= set(rules)
    assert all(diagnostic.severity == "warning" for rule in ("unresolved_subject_ref", "unresolved_object_ref", "missing_source_block_record") for diagnostic in rules[rule])
    assert "REL-CONS-0001" in result.summary.relation_candidate_edge_keys


def test_candidate_only_status_and_no_falkordb_load_are_info_not_readiness_claims(tmp_path: Path):
    relation = read_jsonl(RELATION_RECORDS_PATH)[0]

    result = build_from_rows(tmp_path, relations=[relation])
    rules = diagnostics_by_rule(result)

    assert result.summary.status == "pass"
    assert rules["candidate_only_relation"][0].severity == "info"
    assert rules["no_falkordb_load_executed"][0].severity == "info"
    assert result.summary.product_etl_claimed is False
    assert result.summary.falkordb_loading_runtime_readiness_claimed is False
    assert all("ready" not in diagnostic.message.lower() for diagnostic in result.diagnostics)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_write_then_check_generates_deterministic_staging_reports(tmp_path: Path):
    builder = load_builder_module()
    output_dir = tmp_path / "parser"
    result = builder.build_default_staging_graph()

    builder.write_outputs(result, output_dir)

    expected = builder.output_contents(result)
    assert sorted(expected) == ["parser_staging_graph.json", "parser_staging_graph.md"]
    for name, content in expected.items():
        assert (output_dir / name).read_text(encoding="utf-8") == content

    check = run_cli("--check", "--output-dir", str(output_dir))
    assert check.returncode == 0, check.stdout + check.stderr
    summary = parse_stdout_json(check)
    assert summary["status"] == "pass"
    assert summary["artifact_freshness"]["status"] == "pass"
    assert summary["document_count"] == 2
    assert summary["source_block_count"] == 48
    assert summary["relation_candidate_count"] == 1
    assert summary["keyed_relation_edges"] == ["REL-CONS-0001"]
    assert summary["error_count"] == 0
    assert summary["warning_count"] == 3
    assert {diagnostic["rule"] for diagnostic in summary["diagnostics"]} >= {
        "missing_source_block_record",
        "unresolved_object_ref",
        "unresolved_subject_ref",
        "no_falkordb_load_executed",
    }


def test_check_reports_missing_and_stale_staging_reports(tmp_path: Path):
    builder = load_builder_module()
    output_dir = tmp_path / "parser"
    builder.write_outputs(builder.build_default_staging_graph(), output_dir)

    (output_dir / "parser_staging_graph.json").write_text("stale\n", encoding="utf-8")
    (output_dir / "parser_staging_graph.md").unlink()

    result = run_cli("--check", "--output-dir", str(output_dir))

    assert result.returncode == 1
    summary = parse_stdout_json(result)
    assert summary["status"] == "fail"
    freshness = summary["artifact_freshness"]
    assert freshness["status"] == "stale"
    stale_paths = set(freshness["stale_paths"])
    assert any(path.endswith("parser_staging_graph.json") for path in stale_paths)
    assert any(path.endswith("parser_staging_graph.md") for path in stale_paths)
    assert all(diagnostic["rule"] == "stale-artifact" for diagnostic in freshness["diagnostics"])


def test_tracked_staging_reports_preserve_counts_warnings_and_non_claims():
    builder = load_builder_module()
    expected_contents = builder.output_contents(builder.build_default_staging_graph())
    for name, expected in expected_contents.items():
        assert (ROOT / "prd/parser" / name).read_text(encoding="utf-8") == expected

    report = json.loads((ROOT / "prd/parser/parser_staging_graph.json").read_text(encoding="utf-8"))
    markdown = (ROOT / "prd/parser/parser_staging_graph.md").read_text(encoding="utf-8")

    assert report["status"] == "pass"
    assert report["document_count"] == 2
    assert report["source_block_count"] == 48
    assert report["relation_candidate_count"] == 1
    assert report["keyed_relation_edges"] == ["REL-CONS-0001"]
    assert report["error_count"] == 0
    assert report["warning_count"] == 3
    assert report["non_authoritative"] is True
    assert report["parser_completeness_claimed"] is False
    assert report["legal_correctness_claimed"] is False
    assert report["product_etl_claimed"] is False
    assert report["falkordb_loading_runtime_readiness_claimed"] is False
    assert report["relation_correctness_claimed"] is False

    for phrase in [
        "NetworkX",
        "MultiDiGraph",
        "keyed",
        "unresolved",
        "non-authoritative",
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB loading/runtime readiness",
        "relation correctness",
        "R031",
    ]:
        assert phrase in markdown


def test_readme_documents_s05_contract_and_avoids_positive_claims():
    readme = (ROOT / "prd/parser/README.md").read_text(encoding="utf-8")
    markdown = (ROOT / "prd/parser/parser_staging_graph.md").read_text(encoding="utf-8")
    docs = "\n".join([readme, markdown])

    for phrase in [
        "NetworkX",
        "MultiDiGraph",
        "keyed",
        "unresolved",
        "non-authoritative",
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB loading/runtime readiness",
        "relation correctness",
        "R031",
    ]:
        assert phrase in docs

    forbidden_positive_claims = [
        "claims parser completeness",
        "claims legal correctness",
        "claims product ETL readiness",
        "claims FalkorDB loading/runtime readiness",
        "claims relation correctness",
        "is FalkorDB-ready",
        "is product-ready",
        "is legally authoritative",
    ]
    lower_docs = docs.lower()
    for phrase in forbidden_positive_claims:
        assert phrase.lower() not in lower_docs

