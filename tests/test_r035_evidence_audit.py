from pathlib import Path


AUDIT_PATH = Path("prd/research/ontology_architecture_requirements/06-r035-evidence-audit.md")


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
    "Active requirement with completed owning milestones",
    "Registry-mapping absence",
    "Missing named proof gate",
    "Incomplete R035 gate-status view",
    "Verifier-policy-only false positive",
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


def read_audit() -> str:
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_r035_evidence_audit_has_required_sections() -> None:
    text = read_audit()

    for section in REQUIRED_SECTIONS:
        assert section in text


def test_r035_evidence_audit_preserves_active_not_validated_verdict() -> None:
    text = read_audit()

    assert "R035 remains **Active / not validated**" in text
    assert "Completion of M017/M018" in text
    assert "is **not** evidence that R035 can be marked validated" in text
    assert "until extractor integration regenerates the derived registry" in text


def test_r035_evidence_audit_names_candidate_items_and_missing_gate_example() -> None:
    text = read_audit()

    for candidate_id in CANDIDATE_ITEMS:
        assert candidate_id in text


def test_r035_evidence_audit_lists_exact_s02_drift_signals() -> None:
    text = read_audit()

    for signal in REQUIRED_DRIFT_SIGNALS:
        assert signal in text


def test_r035_evidence_audit_keeps_verifier_policy_non_claim_boundary() -> None:
    text = read_audit()

    assert "This is only **verifier-policy evidence**" in text
    assert "must not be cited as proof that those gates exist in the registry" in text
    assert "Manual JSONL/view edits" in text
