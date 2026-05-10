from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-legalgraph-shaped-falkordb.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_legalgraph_shape", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_proof_confirms_exact_observed_contract() -> None:
    module = load_module()

    proof = module.build_proof(
        "legalgraph-node-counts",
        "label-cardinality",
        {"acts": 1, "articles": 2},
        {"acts": 1, "articles": 2},
        1.25,
    )

    assert proof.status == "confirmed-runtime"
    assert proof.evidence_class == "confirmed"
    assert proof.diagnostics["root_cause"] == "none"


def test_build_proof_marks_mismatch_as_failed_runtime() -> None:
    module = load_module()

    proof = module.build_proof(
        "legalgraph-node-counts",
        "label-cardinality",
        {"acts": 1},
        {"acts": 0},
        1.25,
    )

    assert proof.status == "failed-runtime"
    assert proof.evidence_class == "contradicted"
    assert proof.diagnostics["root_cause"] == "unexpected-result"


def test_payload_status_requires_all_query_proofs_confirmed() -> None:
    module = load_module()
    ok = module.build_proof("ok", "class", {"x": 1}, {"x": 1}, 1)
    bad = module.build_proof("bad", "class", {"x": 1}, {"x": 2}, 1)

    assert module.payload_status([ok]) == "confirmed-runtime"
    assert module.payload_status([ok, bad]) == "failed-runtime"


def test_markdown_preserves_bounded_claim_boundary(tmp_path: Path) -> None:
    module = load_module()
    payload = {
        "schema_version": module.SCHEMA_VERSION,
        "generated_at": "2026-05-10T00:00:00Z",
        "graph_name": "fixture",
        "endpoint": {"host": "127.0.0.1", "port": 6380},
        "status": "confirmed-runtime",
        "query_proofs": [
            {
                "proof_id": "legalgraph-evidence-chain",
                "status": "confirmed-runtime",
                "query_class": "evidence-sourceblock-article-traversal",
                "expected": {"article_id": "article:44fz:1"},
                "observed": {"article_id": "article:44fz:1"},
                "duration_ms": 1.0,
            }
        ],
    }

    path = tmp_path / "proof.md"
    module.write_markdown(path, payload)
    text = path.read_text(encoding="utf-8")

    assert "bounded synthetic runtime evidence" in text
    assert "does not prove ODT parsing" in text
    assert "legal-answer correctness" in text
    assert "legalgraph-evidence-chain" in text
