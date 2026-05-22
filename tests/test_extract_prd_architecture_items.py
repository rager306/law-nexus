from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from test_architecture_registry_schema import (
    format_errors,
    load_records,
    load_schema,
    validate_decision_rules,
    validate_schema_records,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/extract-prd-architecture-items.py"
ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
REQUIRED_ITEM_IDS = {
    "REQ-R001",
    "REQ-R009",
    "REQ-R010",
    "REQ-R017",
    "REQ-R022",
    "REQ-R028",
    "REQ-R029",
    "REQ-R034",
    "DEC-D031",
    "DEC-D032",
    "GATE-G005",
    "GATE-G008",
    "GATE-G011",
    "GATE-G015",
    "S07-FIXED-PRD-CONSISTENCY",
    "S04-FALKORDB-RUNTIME-BOUNDED",
    "S05-PARSER-ODT-BOUNDARY",
    "S05-OLD-PROJECT-PRIOR-ART",
    "S10-USER-BGE-M3-BASELINE",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
    "M001-ARCHITECTURE-ONLY-GUARDRAIL",
    "ASSUMP-PRD-SOURCE-TRUTH",
    "RISK-OVERCLAIM-RUNTIME",
    "CHECK-ARCHITECTURE-EXTRACTOR",
    "EVID-PARSER-GOLDEN-TEST-PROOF",
    "EVID-PARSER-CONSULTANT-HIERARCHY-PROOF",
    "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
    "EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF",
    "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF",
    "EVID-OFFLINE-CITATION-RETRIEVAL-PROOF",
    "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF",
    "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF",
    "EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "DATA-LEGAL-DOCUMENT-IDENTITY-FRBR",
    "DATA-LKIF-DEONTIC-MAPPING",
    "DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY",
    "DATA-LEGAL-SOURCE-HIERARCHY",
    "GATE-AKOMA-FRBR-NORMALIZATION",
    "GATE-LKIF-DEONTIC-BENCHMARK",
    "GATE-RUSLEGALCORE-SCOPE",
    "GATE-BFO-GOST-ALIGNMENT",
    "GATE-LEGAL-COLLISION-POLICY",
    "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
    "GATE-PILOT-SCALE-READINESS",
}
FORBIDDEN_ONTOLOGY_ALIAS_ITEM_IDS = {
    "GATE-DEONTIC-MAPPING-PROOF",
    "GATE-1000-DOC-PILOT",
}
REQUIRED_EDGE_IDS = {
    "EDGE-DEC-D031-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-GATE-G005-BLOCKS-TEMPORAL-VALIDATION",
    "EDGE-GATE-G008-BLOCKS-PARSER-RETRIEVAL-PROOF",
    "EDGE-GATE-G011-BLOCKS-RETRIEVAL-QUALITY-CLAIMS",
    "EDGE-GATE-G015-BLOCKS-RUNTIME-MIGRATION-CLAIMS",
    "EDGE-S04-FALKORDB-RUNTIME-BOUNDED-BOUNDED-BY-RISK-OVERCLAIM-RUNTIME",
    "EDGE-S05-PARSER-ODT-BOUNDARY-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-PARSER-GOLDEN-TEST-PROOF-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-PARSER-CONSULTANT-HIERARCHY-PROOF-BOUNDED-BY-GATE-G008",
    "EDGE-QS-OBSERVABILITY-BASELINE-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G011",
    "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G015",
    "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G005",
    "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-GENERATED-CYPHER-SAFETY",
    "EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-SATISFIES-REQ-R034",
    "EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-BOUNDED-BY-GATE-G011",
    "EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE",
    "EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-SATISFIES-REQ-R034",
    "EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G011",
    "EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G008",
    "EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE",
    "EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-BOUNDED-BY-GATE-G011",
    "EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-DEPENDS-ON-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF",
    "EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-BOUNDED-BY-GATE-G011",
    "EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-DEPENDS-ON-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF",
    "EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-DEPENDS-ON-S10-USER-BGE-M3-BASELINE",
    "EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
    "EDGE-S10-USER-BGE-M3-BASELINE-BOUNDED-BY-GATE-G011",
    "EDGE-M001-ARCHITECTURE-ONLY-GUARDRAIL-BOUNDS-REQ-R029",
    "EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-DATA-LKIF-DEONTIC-MAPPING-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-DATA-LEGAL-SOURCE-HIERARCHY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-AKOMA-FRBR-NORMALIZATION-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-LKIF-DEONTIC-BENCHMARK-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-RUSLEGALCORE-SCOPE-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-BFO-GOST-ALIGNMENT-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-LEGAL-COLLISION-POLICY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-GATE-PILOT-SCALE-READINESS-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "EDGE-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO-BOUNDED-BY-RISK-OVERCLAIM-RUNTIME",
    "EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-REFINES-DATA-TEMPORAL-PROPERTY-BUNDLE",
    "EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-REFINES-REQ-TEMPORAL-STATUS-SEMANTICS",
    "EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-BOUNDED-BY-GATE-AKOMA-FRBR-NORMALIZATION",
    "EDGE-GATE-AKOMA-FRBR-NORMALIZATION-REFINES-EVID-PARSER-RECORD-CONTRACT",
    "EDGE-DATA-LKIF-DEONTIC-MAPPING-BOUNDED-BY-GATE-LKIF-DEONTIC-BENCHMARK",
    "EDGE-DATA-LKIF-DEONTIC-MAPPING-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE",
    "EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-BOUNDED-BY-GATE-RUSLEGALCORE-SCOPE",
    "EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-DEPENDS-ON-DATA-LEGAL-SOURCE-HIERARCHY",
    "EDGE-GATE-LEGAL-COLLISION-POLICY-DEPENDS-ON-DATA-LEGAL-SOURCE-HIERARCHY",
    "EDGE-GATE-LEGAL-COLLISION-POLICY-REFINES-GATE-G005",
    "EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-BOUNDED-BY-REQ-R034",
    "EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-REFINES-GATE-G011",
    "EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-REFINES-GATE-G008",
}
EXPECTED_CONSERVATIVE_RECORDS = {
    "GATE-G005": {
        "status": "active",
        "proof_level": "none",
        "risk_level": "high",
        "non_claims": ["Does not validate temporal conflict resolution."],
    },
    "GATE-G008": {
        "status": "active",
        "proof_level": "none",
        "risk_level": "high",
        "non_claims": ["No parser completeness claim.", "No product retrieval quality claim."],
    },
    "GATE-G011": {
        "status": "active",
        "proof_level": "none",
        "risk_level": "high",
        "non_claims": ["No product retrieval quality claim.", "No managed embedding API fallback claim."],
    },
    "GATE-G015": {
        "status": "active",
        "proof_level": "none",
        "risk_level": "medium",
        "non_claims": ["No production-scale FalkorDB claim."],
    },
    "S04-FALKORDB-RUNTIME-BOUNDED": {
        "status": "bounded-evidence",
        "proof_level": "runtime-smoke",
        "risk_level": "medium",
        "non_claims": ["No production-scale FalkorDB claim.", "No legal retrieval quality claim."],
    },
    "S05-PARSER-ODT-BOUNDARY": {
        "status": "bounded-evidence",
        "proof_level": "real-document-proof",
        "risk_level": "high",
        "non_claims": ["No final legal hierarchy extraction claim.", "No parser completeness claim."],
    },
    "S10-USER-BGE-M3-BASELINE": {
        "status": "bounded-evidence",
        "proof_level": "runtime-smoke",
        "risk_level": "medium",
        "non_claims": ["No product retrieval quality claim.", "No managed embedding API fallback claim."],
    },
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED": {
        "status": "blocked",
        "proof_level": "none",
        "risk_level": "medium",
        "non_claims": ["No managed embedding API fallback claim.", "No default promotion while blocked-environment."],
    },
    "EVID-PARSER-GOLDEN-TEST-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "unit-test",
        "risk_level": "medium",
        "non_claims": ["Does not prove parser completeness.", "Does not prove product retrieval quality."],
    },
    "EVID-PARSER-CONSULTANT-HIERARCHY-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "real-document-proof",
        "risk_level": "medium",
        "non_claims": ["Does not prove multi-document Consultant expansion.", "Does not prove parser completeness."],
    },
    "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS": {
        "status": "bounded-evidence",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove product retrieval quality.", "Does not prove GraphRAG-SDK compatibility."],
    },
    "EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "unit-test",
        "risk_level": "high",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove parser completeness.",
            "Does not prove production FalkorDB runtime behavior.",
            "Does not make LLM output legal authority.",
            "Does not promote D045 research into validated product behavior.",
        ],
    },
    "EVID-REAL-ARTIFACT-RETRIEVAL-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "unit-test",
        "risk_level": "high",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove parser completeness.",
            "Does not prove production FalkorDB runtime behavior.",
            "Does not prove local embedding quality.",
            "Does not close GATE-G008.",
            "Does not close GATE-G011.",
            "Does not make LLM output legal authority.",
        ],
    },
    "EVID-OFFLINE-CITATION-RETRIEVAL-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "unit-test",
        "risk_level": "high",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove parser completeness.",
            "Does not prove production FalkorDB runtime behavior.",
            "Does not prove local embedding quality.",
            "Does not close GATE-G008.",
            "Does not close GATE-G011.",
            "Does not make LLM output legal authority.",
        ],
    },
    "EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "unit-test",
        "risk_level": "high",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove parser completeness.",
            "Does not prove production FalkorDB runtime behavior.",
            "Does not allow managed embedding API fallback.",
            "Does not promote GigaEmbeddings.",
            "Does not close GATE-G011.",
            "Does not close GATE-G008.",
            "Does not make LLM output legal authority.",
        ],
    },
    "EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF": {
        "status": "bounded-evidence",
        "proof_level": "runtime-smoke",
        "risk_level": "high",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove parser completeness.",
            "Does not allow managed embedding API fallback.",
            "Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice.",
            "Does not close GATE-G011.",
        ],
    },
    "EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO": {
        "status": "bounded-evidence",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": [
            "Does not prove parser completeness.",
            "Does not prove legal-answer correctness.",
            "Does not prove product Legal KnowQL behavior.",
            "Does not prove ontology benchmark quality.",
            "Does not prove pilot-scale readiness.",
        ],
    },
    "DATA-LEGAL-DOCUMENT-IDENTITY-FRBR": {
        "status": "hypothesis",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove parser completeness.", "Does not prove legal-answer correctness."],
    },
    "DATA-LKIF-DEONTIC-MAPPING": {
        "status": "hypothesis",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove product Legal KnowQL behavior.", "Does not prove ontology benchmark quality."],
    },
    "DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY": {
        "status": "hypothesis",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove legal-answer correctness.", "Does not prove ontology benchmark quality."],
    },
    "DATA-LEGAL-SOURCE-HIERARCHY": {
        "status": "hypothesis",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove automated legal collision resolution.", "Does not prove legal-answer correctness."],
    },
    "GATE-AKOMA-FRBR-NORMALIZATION": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove parser completeness.", "Does not make Akoma Ntoso canonical."],
    },
    "GATE-LKIF-DEONTIC-BENCHMARK": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove ontology benchmark quality.", "Does not prove product Legal KnowQL behavior."],
    },
    "GATE-RUSLEGALCORE-SCOPE": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove ontology completeness.", "Does not prove legal-answer correctness."],
    },
    "GATE-BFO-GOST-ALIGNMENT": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "medium",
        "non_claims": ["Does not assert GOST requirements.", "Does not prove ontology benchmark quality."],
    },
    "GATE-LEGAL-COLLISION-POLICY": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove automated legal collision resolution.", "Does not prove legal-answer correctness."],
    },
    "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove product retrieval quality.", "Does not prove legal-answer correctness."],
    },
    "GATE-PILOT-SCALE-READINESS": {
        "status": "proposed",
        "proof_level": "source-anchor",
        "risk_level": "high",
        "non_claims": ["Does not prove pilot-scale readiness.", "Does not prove production-scale FalkorDB claim."],
    },
    "M001-ARCHITECTURE-ONLY-GUARDRAIL": {
        "status": "out-of-scope",
        "proof_level": "source-anchor",
        "risk_level": "critical",
        "non_claims": ["No product ETL.", "No production graph schema.", "No legal-answering runtime."],
    },
}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover - assertion text is the useful branch
            raise AssertionError(f"{path}:{line_number}: malformed JSONL: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise AssertionError(f"{path}:{line_number}: expected object record, got {type(record).__name__}")
        records.append(record)
    return records


def records_by_id(records: list[dict[str, Any]], path: Path) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, 1):
        record_id = record.get("id")
        assert isinstance(record_id, str), f"{path}:{index}: record missing string id"
        assert record_id not in by_id, f"{path}:{index}: duplicate record id {record_id}"
        by_id[record_id] = record
    assert by_id, f"{path}: generated output is empty"
    assert list(by_id) == sorted(by_id), f"{path}: record IDs are not sorted deterministically"
    return by_id


def load_extractor_module() -> Any:
    spec = importlib.util.spec_from_file_location("extract_prd_architecture_items", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_no_validated_items(items: list[dict[str, Any]]) -> None:
    bad = sorted(str(item.get("id", "<missing-id>")) for item in items if item.get("status") == "validated")
    assert not bad, "unsafe status/proof mapping: generated items must not be validated: " + ", ".join(bad)


def test_generated_lines_match_architecture_schema_and_fitness_rules() -> None:
    schema = load_schema()
    records = load_records([ITEMS, EDGES])

    errors = validate_schema_records(records, schema) + validate_decision_rules(records)

    assert not errors, format_errors(errors)


def test_check_mode_matches_generated_outputs_and_required_ids() -> None:
    result = run_cli("--check")

    assert result.returncode == 0, result.stderr
    assert "architecture JSONL outputs are current" in result.stdout

    item_by_id = records_by_id(read_jsonl(ITEMS), ITEMS)
    edge_by_id = records_by_id(read_jsonl(EDGES), EDGES)

    assert REQUIRED_ITEM_IDS <= set(item_by_id), "missing required item IDs: " + ", ".join(sorted(REQUIRED_ITEM_IDS - set(item_by_id)))
    assert not (FORBIDDEN_ONTOLOGY_ALIAS_ITEM_IDS & set(item_by_id)), "forbidden ontology alias item IDs emitted: " + ", ".join(sorted(FORBIDDEN_ONTOLOGY_ALIAS_ITEM_IDS & set(item_by_id)))
    assert REQUIRED_EDGE_IDS <= set(edge_by_id), "missing required edge IDs: " + ", ".join(sorted(REQUIRED_EDGE_IDS - set(edge_by_id)))
    assert ITEMS.read_text(encoding="utf-8").endswith("\n"), f"{ITEMS}: missing trailing newline"
    assert EDGES.read_text(encoding="utf-8").endswith("\n"), f"{EDGES}: missing trailing newline"


def test_generated_records_are_conservative_and_anchored() -> None:
    items = read_jsonl(ITEMS)
    edges = read_jsonl(EDGES)
    item_by_id = records_by_id(items, ITEMS)

    assert_no_validated_items(items)

    for record_id, expectations in EXPECTED_CONSERVATIVE_RECORDS.items():
        record = item_by_id[record_id]
        for field in ["status", "proof_level", "risk_level"]:
            assert record[field] == expectations[field], f"id={record_id} field={field} expected {expectations[field]!r}, got {record[field]!r}"
        non_claims = record.get("non_claims", [])
        assert isinstance(non_claims, list), f"id={record_id} field=non_claims expected list"
        for claim in expectations["non_claims"]:
            assert claim in non_claims, f"id={record_id} field=non_claims missing {claim!r}"

    m016_anchor_paths = {
        anchor["path"]
        for anchor in item_by_id["EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF"]["source_anchors"]
    }
    assert {
        "prd/retrieval/representative_retrieval_runtime_benchmark_proof.md",
        "prd/retrieval/representative_retrieval_runtime_benchmark_contract.md",
        "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json",
    } <= m016_anchor_paths

    for record in [*items, *edges]:
        anchors = record.get("source_anchors")
        assert isinstance(anchors, list) and anchors, f"id={record.get('id')} field=source_anchors missing"
        for source_anchor in anchors:
            assert isinstance(source_anchor, dict), f"id={record.get('id')} field=source_anchors contains non-object"
            path = str(source_anchor.get("path", ""))
            assert path, f"id={record.get('id')} field=source_anchors.path empty"
            assert not path.startswith("/"), f"id={record.get('id')} field=source_anchors.path absolute: {path}"
            assert not path.startswith(".gsd/exec"), f"id={record.get('id')} field=source_anchors.path ignored local-only path: {path}"
            assert path.startswith(".gsd/") or (ROOT / path).exists(), f"id={record.get('id')} field=source_anchors.path missing: {path}"


def test_default_extractor_emits_bounded_acp_governance_rows() -> None:
    items = read_jsonl(ITEMS)
    edges = read_jsonl(EDGES)
    item_by_id = records_by_id(items, ITEMS)
    edge_by_id = records_by_id(edges, EDGES)

    expected_items = {
        "ACP-AHF-0001": "health_finding",
        "ACP-AP-0001": "proposal",
        "ACP-APR-0001": "prompt_record",
        "ACP-DC-0001": "decision_candidate",
        "ACP-PG-0001": "proof_gate",
    }
    expected_edges = {
        "ACP-EDGE-AHF-0001-affects-DC-0001": "blocks",
        "ACP-EDGE-AHF-0001-affects-PG-0001": "affects",
        "ACP-EDGE-AP-0001-originProposal-DC-0001": "origin_proposal",
        "ACP-EDGE-AP-0001-suggestedDecision-DC-0001": "suggested_decision",
        "ACP-EDGE-APR-0001-originPromptRecord-AP-0001": "origin_prompt_record",
        "ACP-EDGE-APR-0001-producedProposal-AP-0001": "produced_proposal",
        "ACP-EDGE-DC-0001-requiresProof-PG-0001": "requires_proof",
    }

    assert set(expected_items) <= set(item_by_id)
    assert set(expected_edges) <= set(edge_by_id)

    for record_id, item_type in expected_items.items():
        record = item_by_id[record_id]
        assert record["type"] == item_type
        assert record["layer"] == "architecture-governance"
        assert record["generated_draft"] is False
        non_claims = record["non_claims"]
        for claim in ["Does not validate R035.", "Does not validate R037.", "Does not validate R038."]:
            assert claim in non_claims
        assert not any(anchor["path"].startswith("prd/architecture/acp/derived/") for anchor in record["source_anchors"])

    assert item_by_id["ACP-DC-0001"]["authority_required"] is True
    assert item_by_id["ACP-DC-0001"]["type"] != "decision"
    assert item_by_id["ACP-PG-0001"]["type"] == "proof_gate"
    assert item_by_id["ACP-PG-0001"]["status"] == "active"

    for record_id, edge_type in expected_edges.items():
        record = edge_by_id[record_id]
        assert record["type"] == edge_type
        assert record["from"] in item_by_id
        assert record["to"] in item_by_id
        assert record["type"] not in {"satisfies", "validated_by"}
        assert not any(anchor["path"].startswith("prd/architecture/acp/derived/") for anchor in record["source_anchors"])


def test_tmp_generation_check_mode_and_deterministic_bytes(tmp_path: Path) -> None:
    item_out = tmp_path / "architecture_items.jsonl"
    edge_out = tmp_path / "architecture_edges.jsonl"

    first = run_cli("--items", str(item_out), "--edges", str(edge_out))
    assert first.returncode == 0, first.stderr
    first_items = item_out.read_bytes()
    first_edges = edge_out.read_bytes()

    check = run_cli("--items", str(item_out), "--edges", str(edge_out), "--check")
    assert check.returncode == 0, check.stderr
    assert "architecture JSONL outputs are current" in check.stdout

    second = run_cli("--items", str(item_out), "--edges", str(edge_out))
    assert second.returncode == 0, second.stderr
    assert item_out.read_bytes() == first_items, f"{item_out}: generation is not byte-deterministic"
    assert edge_out.read_bytes() == first_edges, f"{edge_out}: generation is not byte-deterministic"


def test_check_mode_reports_stale_and_missing_outputs_without_rewriting(tmp_path: Path) -> None:
    item_out = tmp_path / "architecture_items.jsonl"
    edge_out = tmp_path / "architecture_edges.jsonl"
    write_result = run_cli("--items", str(item_out), "--edges", str(edge_out))
    assert write_result.returncode == 0, write_result.stderr

    stale_bytes = item_out.read_text(encoding="utf-8") + "{}\n"
    item_out.write_text(stale_bytes, encoding="utf-8")

    stale_result = run_cli("--items", str(item_out), "--edges", str(edge_out), "--check")

    assert stale_result.returncode != 0
    assert "stale generated output" in stale_result.stderr
    assert str(item_out) in stale_result.stderr
    assert "python scripts/extract-prd-architecture-items.py" in stale_result.stderr
    assert item_out.read_text(encoding="utf-8") == stale_bytes

    item_out.unlink()
    missing_result = run_cli("--items", str(item_out), "--edges", str(edge_out), "--check")
    assert missing_result.returncode != 0
    assert "stale generated output" in missing_result.stderr
    assert str(item_out) in missing_result.stderr
    assert not item_out.exists(), "--check must not rewrite missing generated output"


def test_check_mode_reports_malformed_existing_jsonl_with_line_number(tmp_path: Path) -> None:
    item_out = tmp_path / "architecture_items.jsonl"
    edge_out = tmp_path / "architecture_edges.jsonl"
    write_result = run_cli("--items", str(item_out), "--edges", str(edge_out))
    assert write_result.returncode == 0, write_result.stderr

    item_out.write_text('{"ok": true}\n{not-json}\n', encoding="utf-8")

    result = run_cli("--items", str(item_out), "--edges", str(edge_out), "--check")

    assert result.returncode != 0
    assert "existing generated JSONL is unparsable" in result.stderr
    assert f"{item_out}:2" in result.stderr


def test_missing_or_malformed_s08_findings_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing-S08-FINDINGS.json"
    missing_result = run_cli("--s08-findings", str(missing), "--items", str(tmp_path / "i.jsonl"), "--edges", str(tmp_path / "e.jsonl"))
    assert missing_result.returncode != 0
    assert "missing required source" in missing_result.stderr
    assert str(missing) in missing_result.stderr

    malformed = tmp_path / "S08-FINDINGS.json"
    malformed.write_text("{not-json", encoding="utf-8")
    malformed_result = run_cli("--s08-findings", str(malformed), "--items", str(tmp_path / "i2.jsonl"), "--edges", str(tmp_path / "e2.jsonl"))
    assert malformed_result.returncode != 0
    assert "malformed source JSON" in malformed_result.stderr
    assert str(malformed) in malformed_result.stderr
    assert "line 1 column 2" in malformed_result.stderr

    missing_ids = tmp_path / "S08-FINDINGS-missing-ids.json"
    missing_ids.write_text(json.dumps({"findings": [{"id": "G-005"}]}), encoding="utf-8")
    missing_ids_result = run_cli("--s08-findings", str(missing_ids), "--items", str(tmp_path / "i3.jsonl"), "--edges", str(tmp_path / "e3.jsonl"))
    assert missing_ids_result.returncode != 0
    assert "missing required finding IDs" in missing_ids_result.stderr
    assert "G-008" in missing_ids_result.stderr


def test_missing_source_anchor_and_validated_status_have_record_level_diagnostics() -> None:
    extractor = load_extractor_module()
    bad_anchor_record = extractor.item(
        "BAD-MISSING-ANCHOR",
        "workflow_check",
        "Bad anchor fixture",
        "Fixture used to prove missing source anchors name the offending record.",
        "workflow-governance",
        "active",
        "source-anchor",
        "high",
        [extractor.anchor("prd/architecture/does-not-exist.md", "prd")],
        "M004/S02 tests",
        "Should fail before downstream graph work consumes it.",
        ["Test fixture only."],
    )
    config = extractor.ExtractionConfig(
        root=ROOT,
        items_path=ITEMS,
        edges_path=EDGES,
        s08_findings_path=ROOT / ".gsd/milestones/M001/slices/S08/S08-FINDINGS.json",
        check=True,
    )

    try:
        extractor.validate_anchor_paths(config, [bad_anchor_record])
    except extractor.ExtractionError as exc:
        diagnostic = str(exc)
    else:  # pragma: no cover - failure branch produces clearer assertion below
        diagnostic = ""

    assert "record BAD-MISSING-ANCHOR references missing source anchor" in diagnostic
    assert "prd/architecture/does-not-exist.md" in diagnostic

    try:
        assert_no_validated_items([
            {"id": "BAD-VALIDATED-OVERCLAIM", "status": "validated"},
        ])
    except AssertionError as exc:
        status_diagnostic = str(exc)
    else:  # pragma: no cover - failure branch produces clearer assertion below
        status_diagnostic = ""

    assert "unsafe status/proof mapping" in status_diagnostic
    assert "BAD-VALIDATED-OVERCLAIM" in status_diagnostic
