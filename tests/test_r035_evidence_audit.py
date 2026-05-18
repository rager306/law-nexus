import json
import re
from pathlib import Path


AUDIT_PATH = Path("prd/research/ontology_architecture_requirements/06-r035-evidence-audit.md")
INTEGRATION_PLAN_PATH = Path(
    "prd/research/ontology_architecture_requirements/05-registry-integration-plan.md"
)
VERIFIER_PATH = Path("scripts/verify-architecture-graph.py")
ARCHITECTURE_ITEMS_PATH = Path("prd/architecture/architecture_items.jsonl")
CLAIMS_LEDGER_PATH = Path("prd/architecture/claims_ledger.md")
LIFECYCLE_RECOMMENDATION_PATH = Path(
    "prd/research/ontology_architecture_requirements/12-r035-m020-lifecycle-recommendation.md"
)
RUNTIME_REMEDIATION_PATH = Path(
    "prd/research/ontology_architecture_requirements/13-r035-runtime-integration-remediation.md"
)
RUNTIME_PROOF_PATH = Path(
    "prd/research/ontology_architecture_requirements/ontology_graphrag_runtime_integration_proof.json"
)


REQUIRED_SECTIONS = [
    "## Audit Verdict",
    "## Requirement Clause Matrix",
    "## Evidence Inventory",
    "## Missing Proof Decisions",
    "## S02 Drift Signals",
    "## S03 Handoff",
    "## Non-Claims",
]


REQUIRED_DRIFT_SIGNALS = [
    "Active requirement not owned by an in-progress milestone",
    "Registry-mapping absence",
    "Missing named proof gate",
    "Stale or empty derived views",
    "Enforced verifier rules with missing registry endpoints",
    "Candidate-vs-current mismatch",
    "Gate ID drift",
    "Unsafe lifecycle language",
]


CANDIDATE_ITEMS = [
    "EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "DATA-LEGAL-DOCUMENT-IDENTITY-FRBR",
    "DATA-LKIF-DEONTIC-MAPPING",
    "DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY",
    "DATA-LEGAL-SOURCE-HIERARCHY",
    "GATE-AKOMA-FRBR-NORMALIZATION",
    "GATE-DEONTIC-MAPPING-PROOF",
    "GATE-RUSLEGALCORE-SCOPE",
    "GATE-BFO-GOST-ALIGNMENT",
    "GATE-LEGAL-COLLISION-POLICY",
    "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
    "GATE-1000-DOC-PILOT",
]


UNSAFE_FINAL_VALIDATION_PHRASES = [
    "R035 is validated",
    "R035 validated",
    "mark R035 complete",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_audit() -> str:
    return read_text(AUDIT_PATH)


def architecture_item_ids() -> set[str]:
    ids: set[str] = set()
    for line in read_text(ARCHITECTURE_ITEMS_PATH).splitlines():
        if line.strip():
            ids.add(json.loads(line)["id"])
    return ids


def sentences_containing(text: str, phrase: str) -> list[str]:
    # The audit is Markdown, so treat bullets/headings as sentence boundaries too.
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if phrase in chunk]


def test_r035_evidence_audit_has_required_sections() -> None:
    text = read_audit()

    for section in REQUIRED_SECTIONS:
        assert section in text


def test_r035_evidence_audit_preserves_active_not_validated_verdict() -> None:
    text = read_audit()

    assert "R035 remains **Active / not runtime-validated**" in text
    assert "Completion of M017/M018" in text
    assert "is still **not** validation evidence for R035" in text
    assert "registry/view synchronization only" in text


def test_r035_evidence_audit_names_candidate_items_and_missing_registry_evidence() -> None:
    text = read_audit()
    integration_plan = read_text(INTEGRATION_PLAN_PATH)
    registry_ids = architecture_item_ids()
    claims_ledger = read_text(CLAIMS_LEDGER_PATH)

    canonical_aliases = {
        "GATE-DEONTIC-MAPPING-PROOF": "GATE-LKIF-DEONTIC-BENCHMARK",
        "GATE-1000-DOC-PILOT": "GATE-PILOT-SCALE-READINESS",
    }
    for candidate_id in CANDIDATE_ITEMS:
        assert candidate_id in integration_plan
        assert candidate_id in text
        assert canonical_aliases.get(candidate_id, candidate_id) in registry_ids

    assert "GATE-AKOMA-FRBR-NORMALIZATION" in registry_ids
    assert "architecture_items.jsonl" in text
    assert "claims_ledger.md" in text
    assert "R035 Gate Status" in claims_ledger
    assert "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION" in claims_ledger


def test_r035_evidence_audit_tracks_verifier_policy_without_counting_it_as_proof() -> None:
    text = read_audit()
    verifier = read_text(VERIFIER_PATH)

    assert "GATE-AKOMA-FRBR-NORMALIZATION" in verifier
    assert "ONTOLOGY_PROMOTION_RULES" in verifier
    assert "validate_ontology_promotion_gates" in verifier
    assert "This is only **verifier-policy evidence**" in text
    assert "must not be cited as proof that those gates are satisfied" in text
    assert "policy names `GATE-AKOMA-FRBR-NORMALIZATION`" in text


def test_r035_evidence_audit_lists_exact_s02_drift_signals() -> None:
    text = read_audit()

    for signal in REQUIRED_DRIFT_SIGNALS:
        assert signal in text

    assert "R035 is still Active" in text
    assert "Active requirement not owned by an in-progress milestone" in text
    assert "resolved for current registry existence of `GATE-AKOMA-FRBR-NORMALIZATION`" in text
    assert "resolved for current ontology verifier-policy gate endpoints" in text
    assert "resolved for current claims-ledger R035 gate-status coverage" in text


def test_r035_lifecycle_recommendation_documents_runtime_prerequisite_boundary() -> None:
    text = read_text(LIFECYCLE_RECOMMENDATION_PATH)

    assert "## Runtime Prerequisite Diagnostics" in text
    assert "S07/S08 composed local proof command" in text
    assert "separate boundary checks" in text
    assert "do **not** promote R035" in text
    assert "`confirmed_runtime` or explicit blocked prerequisite diagnostic" in text
    assert "Bounded prerequisite diagnostic only" in text
    assert "does not validate R035" in text
    assert "`confirmed-runtime` bounded synthetic runtime proof or explicit blocked prerequisite diagnostic" in text
    assert "blocked/unavailable status is not negative R035 evidence and not R035 validation" in text
    assert "must not persist secrets, provider payloads, raw legal text, raw queries, raw vectors" in text
    assert "ontology_graphrag_runtime_integration_proof.json" in text
    assert "13-r035-runtime-integration-remediation.md" in text
    assert "bounded runtime remediation or blocked prerequisite diagnostics only" in text


def test_r035_runtime_remediation_artifact_keeps_s07_bounded_and_active() -> None:
    text = read_text(RUNTIME_REMEDIATION_PATH)
    proof = json.loads(read_text(RUNTIME_PROOF_PATH))

    assert "R035 remains Active" in text
    assert "bounded runtime remediation evidence or blocked prerequisite diagnostics" in text
    assert "do not close the gate and do not move R035 out of Active" in text
    assert proof["r035_lifecycle_disposition"] == "remains_active_bounded_runtime_evidence_only"
    assert proof["gate_disposition"].startswith("gate_remains_open")
    assert set(proof["phases"]) == {
        "embedding_runtime",
        "falkordb_runtime",
        "fixture_materialization",
        "ontology_temporal_query",
        "citation_evidence_validation",
        "query_safety",
        "overclaim_safety",
        "r035_lifecycle_disposition",
    }
    assert "Does not satisfy broad ontology" in " ".join(proof["non_claims"])
    for forbidden in ("raw legal text", "raw queries", "raw vectors", ".gsd/exec", "/root/"):
        assert forbidden not in json.dumps(proof, ensure_ascii=False)


def test_r035_evidence_audit_points_to_s07_runtime_remediation_without_broad_validation() -> None:
    text = read_audit()

    assert "M020/S07-S08 runtime remediation update" in text
    assert "graph-route, local/open-weight embedding candidate ranking, deterministic evidence-ID, stale-evidence diagnostics" in text
    assert "13-r035-runtime-integration-remediation.md" in text
    assert "ontology_graphrag_runtime_integration_proof.json" in text
    assert "bounded runtime remediation or prerequisite diagnostics only" in text
    assert "R035 remains Active" in text
    assert "do not validate broad ontology behavior" in text
    assert "FalkorDB production behavior" in text


def test_claims_ledger_r035_status_is_synchronization_only_not_runtime_validation() -> None:
    claims_ledger = read_text(CLAIMS_LEDGER_PATH)

    assert "registry/view synchronization-only guardrails" in claims_ledger
    assert "not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation" in claims_ledger
    assert "do not validate the referenced standard or product behavior" not in claims_ledger


def test_r035_evidence_audit_rejects_unsafe_final_validation_language() -> None:
    text = read_audit()

    for phrase in UNSAFE_FINAL_VALIDATION_PHRASES:
        for sentence in sentences_containing(text, phrase):
            assert re.search(r"\bnot\b|\bno\b|must stay Active|remains \*\*Active", sentence, re.IGNORECASE), sentence

    assert "mark R035 complete" not in text
    assert "Manual JSONL/view edits" in text
