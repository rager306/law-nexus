"""Mechanical pins for the minimal PDD product model (T005, SC4).

The model maps established observable behavior only: StubEmbedding is named
as the fail-closed stub it is, the stores are recorded as in-memory, and no
capability claims a live embedding or a persistent store.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "product-model"

LAYOUT_CORE = [
    "README.md",
    ".gitignore",
    "config.yaml",
    "taxonomies.yaml",
    "product.md",
    "coverage.md",
]

EXPECTED_CAPABILITY_IDS = {
    "check-health",
    "inspect-document",
    "replay-edition",
    "resolve-subordinates",
}

# Tokens that would mark a capability as claiming live embeddings or a
# persistent store. The model records the stub and the in-memory adapters, so
# none of these may appear under capabilities/.
FORBIDDEN_IN_CAPABILITIES = [
    r"\bTEI\b",
    r"\bRuVector\b",
    r"\bFalkorDB\b",
    r"\bSQLite\b",
    r"persist",
    r"semantic embedding",
]


def _model_file(rel: str) -> str:
    return (MODEL_DIR / rel).read_text(encoding="utf-8")


def test_layout_core_exists() -> None:
    assert MODEL_DIR.is_dir(), "product-model/ must exist in the tracked tree"
    for rel in LAYOUT_CORE:
        assert (MODEL_DIR / rel).is_file(), f"missing product-model/{rel}"
    config = _model_file("config.yaml")
    assert "schema: 11" in config
    assert "sdd:" in config and "paths:" in config


def test_at_least_one_interface_with_capabilities_scenarios_and_entities() -> None:
    interfaces = list((MODEL_DIR / "interfaces").glob("**/interface.md"))
    assert interfaces, "the model needs at least one interface"
    terminal = _model_file("interfaces/terminal/interface.md")
    assert "type: cli" in terminal
    assert "operator" in terminal

    capability_ids = {
        path.parent.name for path in (MODEL_DIR / "capabilities").glob("*/capability.md")
    }
    assert EXPECTED_CAPABILITY_IDS <= capability_ids, (
        "the four law-nexus-inspect subcommands must be capabilities"
    )
    for capability_id in sorted(EXPECTED_CAPABILITY_IDS):
        scenarios = list((MODEL_DIR / "capabilities" / capability_id / "scenarios").glob("*.md"))
        assert scenarios, f"capability {capability_id} has no scenarios"

    entities = list((MODEL_DIR / "entities").glob("*.md"))
    assert entities, "the model needs entities"
    document = _model_file("entities/document.md")
    for fact in ("Path", "Byte size", "Content fingerprint", "Source family"):
        assert f"**{fact}**" in document, f"document entity must keep fact {fact}"


def test_stub_embedding_is_named_as_the_fail_closed_stub_it_is() -> None:
    hits = [
        path
        for path in MODEL_DIR.rglob("*.md")
        if "StubEmbedding" in path.read_text(encoding="utf-8")
    ]
    assert hits, "the model must name StubEmbedding"
    for path in hits:
        text = path.read_text(encoding="utf-8").lower()
        assert "stub" in text, f"{path.name} names StubEmbedding without calling it a stub"
        assert "fail-closed" in text, f"{path.name} names StubEmbedding without fail-closed"
    capability = _model_file("capabilities/inspect-document/capability.md")
    assert "StubEmbedding" in capability and "in-memory" in capability, (
        "inspect-document must attribute retrieval to the fail-closed StubEmbedding over the in-memory stores"
    )
    product = _model_file("product.md")
    assert "in-memory" in product, "product.md must record the stores as in-memory"


def test_no_capability_claims_a_live_embedding_or_a_persistent_store() -> None:
    for path in sorted((MODEL_DIR / "capabilities").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_IN_CAPABILITIES:
            assert re.search(pattern, text, re.IGNORECASE) is None, (
                f"{path.relative_to(MODEL_DIR)} must not match {pattern!r}"
            )
