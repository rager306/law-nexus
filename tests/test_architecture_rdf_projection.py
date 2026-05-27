from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export-architecture-rdf-projection.py"
ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
TTL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.ttl"
SHACL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.shacl.ttl"
SPARQL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.sparql"
REPORT_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection-rdf-report.json"


def run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXPORTER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def temp_output_args(tmp_path: Path) -> list[str]:
    return [
        "--ttl-output",
        str(tmp_path / "projection.ttl"),
        "--shacl-output",
        str(tmp_path / "projection.shacl.ttl"),
        "--sparql-output",
        str(tmp_path / "projection.sparql"),
        "--report-output",
        str(tmp_path / "projection-report.json"),
    ]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def test_architecture_rdf_projection_outputs_are_current() -> None:
    result = run_exporter("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["non_authoritative"] is True
    assert payload["mode"] == "custom"
    assert payload["diagnostic_count"] == 0
    assert payload["diagnostic_summary"] == {"by_category": {}, "by_rule": {}, "by_severity": {}}
    assert payload["safety_boundary"].startswith("Derived, custom-only ACP projection")
    assert payload["vocabulary"]["namespaces"] == {
        "acp": "urn:law-nexus:vocab:acp:",
        "lgarch": "urn:law-nexus:vocab:architecture:",
    }
    assert "lgarch:ArchitectureItem" in payload["vocabulary"]["classes"]
    assert "acp:authorityRequired" in payload["vocabulary"]["predicates"]
    assert payload["counts"] == {
        "items": 63,
        "edges": 98,
        "acp_items": 5,
        "acp_edges": 7,
        "rdf_resources": 161,
        "statements": 422,
    }
    assert payload["shape_smoke"] == {
        "status": "ok",
        "engine": "deterministic-structural-check",
        "checked_rules": [
            "item-required-fields",
            "edge-endpoints",
            "source-anchor-safety",
            "acp-non-claims",
            "decision-candidate-authority-required",
        ],
    }
    assert payload["sparql_smoke"]["engine"] == "not-executed"


def test_architecture_rdf_projection_artifact_content_boundaries() -> None:
    ttl = TTL_OUTPUT.read_text(encoding="utf-8")
    shacl = SHACL_OUTPUT.read_text(encoding="utf-8")
    sparql = SPARQL_OUTPUT.read_text(encoding="utf-8")
    report_text = REPORT_OUTPUT.read_text(encoding="utf-8")
    report = json.loads(report_text)

    assert "@prefix lgarch: <urn:law-nexus:vocab:architecture:> ." in ttl
    assert "<urn:law-nexus:architecture:ACP-DC-0001>" in ttl
    assert "lgarch:DecisionCandidate" in ttl
    assert "acp:authorityRequired true" in ttl
    assert 'lgarch:nonClaim "Does not validate R035."' in ttl
    assert 'lgarch:nonClaim "Does not validate R037."' in ttl
    assert 'lgarch:nonClaim "Does not validate R038."' in ttl
    assert "lgarch:requiresProof <urn:law-nexus:architecture:ACP-PG-0001>" in ttl
    assert "urn:law-nexus:architecture-source:" in ttl

    assert "lgarch:ArchitectureItemShape" in shacl
    assert "lgarch:ArchitectureEdgeShape" in shacl
    assert "acp:DecisionCandidateShape" in shacl
    assert "sh:hasValue true" in shacl

    assert "SELECT (COUNT(?item) AS ?itemCount)" in sparql
    assert "SELECT (COUNT(?edge) AS ?edgeCount)" in sparql
    assert "list ACP governance rows" in sparql or "List ACP governance rows" in sparql
    assert "Does not validate R035." in sparql
    assert "Does not validate R037." in sparql
    assert "Does not validate R038." in sparql

    assert report["non_authoritative"] is True
    assert report["diagnostic_summary"] == {"by_category": {}, "by_rule": {}, "by_severity": {}}
    assert report["vocabulary"]["boundary"].startswith("Custom projection vocabulary only")
    assert "lgarch:recordId" in report["vocabulary"]["predicates"]
    assert report["safety_boundary"].startswith("Derived, custom-only ACP projection")
    assert "This projection does not validate R035." in report["non_claims"]
    assert "This projection does not validate R037." in report["non_claims"]
    assert "This projection does not validate R038." in report["non_claims"]

    for content in (ttl, shacl, sparql, report_text):
        assert "/root/" not in content
        assert ".gsd/exec" not in content
        assert "sk-" not in content
        assert "R035 is validated" not in content
        assert "R037 is validated" not in content
        assert "R038 is validated" not in content


def test_architecture_rdf_projection_temp_outputs_are_deterministic(tmp_path: Path) -> None:
    args = temp_output_args(tmp_path)
    first = run_exporter(*args)
    second = run_exporter(*args, "--check")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    payload = json.loads(second.stdout)
    assert payload["status"] == "ok"
    assert (tmp_path / "projection.ttl").read_text(encoding="utf-8") == TTL_OUTPUT.read_text(encoding="utf-8")
    assert (tmp_path / "projection.shacl.ttl").read_text(encoding="utf-8") == SHACL_OUTPUT.read_text(encoding="utf-8")
    assert (tmp_path / "projection.sparql").read_text(encoding="utf-8") == SPARQL_OUTPUT.read_text(encoding="utf-8")
    first_report = (tmp_path / "projection-report.json").read_text(encoding="utf-8")
    third = run_exporter(*args, "--check")
    assert third.returncode == 0, third.stdout + third.stderr
    assert (tmp_path / "projection-report.json").read_text(encoding="utf-8") == first_report
    temp_report = json.loads(first_report)
    assert temp_report["outputs"]["report"] == str(tmp_path / "projection-report.json")


def test_architecture_rdf_projection_detects_stale_outputs(tmp_path: Path) -> None:
    for name in ("projection.ttl", "projection.shacl.ttl", "projection.sparql", "projection-report.json"):
        (tmp_path / name).write_text("stale\n", encoding="utf-8")

    result = run_exporter(*temp_output_args(tmp_path), "--check")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["diagnostic_summary"]["by_rule"] == {"stale-output": 4}
    assert payload["diagnostic_summary"]["by_category"] == {"freshness": 4}
    assert payload["diagnostic_summary"]["by_severity"] == {"error": 4}
    stale_diagnostics = [diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "stale-output"]
    assert all(diagnostic["severity"] == "error" for diagnostic in stale_diagnostics)
    assert all(diagnostic["category"] == "freshness" for diagnostic in stale_diagnostics)
    assert all("Run the exporter in write mode" in diagnostic["remediation"] for diagnostic in stale_diagnostics)
    stale_paths = {diagnostic["path"] for diagnostic in stale_diagnostics}
    assert stale_paths == {
        str(tmp_path / "projection.ttl"),
        str(tmp_path / "projection.shacl.ttl"),
        str(tmp_path / "projection.sparql"),
        str(tmp_path / "projection-report.json"),
    }


def test_architecture_rdf_projection_refuses_canonical_registry_output() -> None:
    before_items = ITEMS.read_text(encoding="utf-8")

    result = run_exporter("--ttl-output", str(ITEMS))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["message"] == "refusing to write canonical architecture registry file"
    assert ITEMS.read_text(encoding="utf-8") == before_items


def test_architecture_rdf_projection_rejects_duplicate_ids(tmp_path: Path) -> None:
    duplicate_items = tmp_path / "items.jsonl"
    records = load_jsonl(ITEMS)
    records[1]["id"] = records[0]["id"]
    write_jsonl(duplicate_items, records)

    result = run_exporter("--items", str(duplicate_items), *temp_output_args(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    duplicate = next(diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "duplicate-id")
    assert duplicate["category"] == "shape"
    assert duplicate["severity"] == "error"
    assert "generator ID derivation" in duplicate["remediation"]


def test_architecture_rdf_projection_rejects_missing_endpoint(tmp_path: Path) -> None:
    broken_edges = tmp_path / "edges.jsonl"
    records = load_jsonl(EDGES)
    records[0]["to"] = "MISSING-ENDPOINT"
    write_jsonl(broken_edges, records)

    result = run_exporter("--edges", str(broken_edges), *temp_output_args(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    missing_endpoint = next(diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "missing-endpoint")
    assert missing_endpoint["category"] == "shape"
    assert "Fix the edge endpoint" in missing_endpoint["remediation"]


def test_architecture_rdf_projection_rejects_unsafe_source_anchor(tmp_path: Path) -> None:
    unsafe_items = tmp_path / "items.jsonl"
    records = load_jsonl(ITEMS)
    records[0]["source_anchors"][0]["path"] = "/tmp/not-allowed"
    write_jsonl(unsafe_items, records)

    result = run_exporter("--items", str(unsafe_items), *temp_output_args(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    unsafe_anchor = next(diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "unsafe-source-anchor")
    assert unsafe_anchor["category"] == "safety"
    assert "safe repository-relative" in unsafe_anchor["remediation"]


def test_architecture_rdf_projection_rejects_missing_acp_non_claim(tmp_path: Path) -> None:
    invalid_items = tmp_path / "items.jsonl"
    records = load_jsonl(ITEMS)
    for record in records:
        if record["id"] == "ACP-DC-0001":
            record["non_claims"] = [claim for claim in record["non_claims"] if claim != "Does not validate R035."]
    write_jsonl(invalid_items, records)

    result = run_exporter("--items", str(invalid_items), *temp_output_args(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    missing_non_claim = next(diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "missing-non-claim")
    assert missing_non_claim["category"] == "authority"
    assert "R035/R037/R038 non-claims" in missing_non_claim["remediation"]


def test_architecture_rdf_projection_rejects_missing_authority_requirement(tmp_path: Path) -> None:
    invalid_items = tmp_path / "items.jsonl"
    records = load_jsonl(ITEMS)
    for record in records:
        if record["id"] == "ACP-DC-0001":
            record["authority_required"] = False
    write_jsonl(invalid_items, records)

    result = run_exporter("--items", str(invalid_items), *temp_output_args(tmp_path))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    authority_required = next(diagnostic for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "authority-required")
    assert authority_required["category"] == "authority"
    assert "authority_required to true" in authority_required["remediation"]


def test_architecture_rdf_projection_diff_mode_is_non_writing_and_current() -> None:
    before = {path: path.read_text(encoding="utf-8") for path in (TTL_OUTPUT, SHACL_OUTPUT, SPARQL_OUTPUT, REPORT_OUTPUT)}

    result = run_exporter("--diff")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["non_authoritative"] is True
    assert payload["diff"]["mode"] == "diff"
    assert payload["diff"]["non_writing"] is True
    assert payload["diff"]["status"] == "current"
    assert payload["diff"]["states"] == ["current"]
    assert set(payload["diff"]["outputs"]) == {"ttl", "shacl", "sparql", "report"}
    for output in payload["diff"]["outputs"].values():
        assert output["state"] == "current"
        assert output["current_sha256"] == output["expected_sha256"]
        assert output["current_bytes"] == output["expected_bytes"]
    assert before == {path: path.read_text(encoding="utf-8") for path in before}


def test_architecture_rdf_projection_diff_mode_reports_missing_without_writing(tmp_path: Path) -> None:
    args = temp_output_args(tmp_path)

    result = run_exporter(*args, "--diff")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["diff"]["status"] == "changed"
    assert payload["diff"]["states"] == ["missing"]
    assert all(output["state"] == "missing" for output in payload["diff"]["outputs"].values())
    assert not (tmp_path / "projection.ttl").exists()
    assert not (tmp_path / "projection.shacl.ttl").exists()
    assert not (tmp_path / "projection.sparql").exists()
    assert not (tmp_path / "projection-report.json").exists()
