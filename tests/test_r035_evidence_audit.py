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


def test_r035_evidence_audit_rejects_unsafe_final_validation_language() -> None:
    text = read_audit()

    for phrase in UNSAFE_FINAL_VALIDATION_PHRASES:
        for sentence in sentences_containing(text, phrase):
            assert re.search(r"\bnot\b|\bno\b|must stay Active|remains \*\*Active", sentence, re.IGNORECASE), sentence

    assert "mark R035 complete" not in text
    assert "Manual JSONL/view edits" in text
