"""Red-green tests for the M215/S04 embedding supply-chain gate packet verifier.

The helper builds a valid in-memory packet that references real tracked repo
files. Each mutation must make the fail-closed verifier exit 1.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-m215-s04-gate-packet.py"


def valid_packet() -> dict:
    return {
        "schema": "law-nexus/m215-s04-embedding-supply-chain-gate-packet/v1",
        "gate_id": "GATE-EMBEDDING-SUPPLY-CHAIN",
        "milestone": "M215-w9jsgn",
        "slice": "S04",
        "recordedAt": "2026-10-08T00:00:00Z",
        "lifecycle": "[bounded]",
        "authoritative": False,
        "gate_promoted": False,
        "promotion": False,
        "proof_level": "contract",
        "surfaces": [
            {
                "id": "S01",
                "evidence": [
                    "crates/ln-storage/src/embedding_artifact.rs",
                    "crates/ln-storage/src/adapters/tei_http.rs",
                ],
            },
            {
                "id": "S02",
                "evidence": ["crates/ln-storage/src/adapters/tei_http.rs"],
            },
            {
                "id": "S03",
                "evidence": ["crates/ln-testkit/src/deterministic_embedding.rs"],
            },
        ],
        "checks": [
            {
                "id": "ln-storage-embedding-artifact-contract",
                "command": (
                    "cargo test -p ln-storage --offline --test embedding_artifact_contract"
                ),
                "observed": "12 passed; 0 failed",
                "exitCode": 0,
            },
            {
                "id": "ln-testkit-deterministic-embedding-battery",
                "command": (
                    "cargo test -p ln-testkit --offline --test deterministic_embedding_battery"
                ),
                "observed": "9 passed; 0 failed",
                "exitCode": 0,
            },
        ],
        "rust_scope": {
            "scope": "crates/*/src",
            "status": "no_managed_provider_reference",
            "managed_provider_hits": [],
        },
        "non_claims": [
            {
                "key": "no-live-validation",
                "statement": (
                    "No live TEI endpoint was contacted; the HTTP surface remains "
                    "unproven and not validated."
                ),
            },
            {
                "key": "no-retrieval-quality",
                "statement": (
                    "No retrieval-quality claim is made; embedding ranking quality "
                    "is not measured in this packet."
                ),
            },
            {
                "key": "no-product-runtime",
                "statement": (
                    "No product runtime is provided; this is bounded repository evidence only."
                ),
            },
            {
                "key": "cleartext-transport",
                "statement": (
                    "The live TEI transport is cleartext HTTP without TLS and is "
                    "not for untrusted networks."
                ),
            },
            {
                "key": "canonical-render-non-injective",
                "statement": (
                    "canonical_string() provenance rendering is deterministic but "
                    "not injective (unescaped fields), so the byte pin is not "
                    "tamper-resistant."
                ),
            },
            {
                "key": "deterministic-pin-drift-detector",
                "statement": (
                    "The deterministic pin is drift detection, not a correctness "
                    "proof; it does not validate embedding quality."
                ),
            },
            {
                "key": "r012-scope-level",
                "statement": (
                    "R012 enforcement remains scope-level; the settings source is a "
                    "free string and managed exclusion is not structurally enforced."
                ),
            },
            {
                "key": "test-port-not-product-provider",
                "statement": (
                    "The ln-testkit embedding port is test support, not a product provider."
                ),
            },
            {
                "key": "no-gate-promotion",
                "statement": (
                    "GATE-EMBEDDING-SUPPLY-CHAIN is not promoted; this packet is non-authoritative."
                ),
            },
        ],
    }


def write_packet(tmp_path: Path, packet: dict) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    return path


def run_verifier(packet_path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--packet",
            str(packet_path),
            "--root",
            str(ROOT),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_fixture_passes(tmp_path: Path) -> None:
    packet_path = write_packet(tmp_path, valid_packet())
    result = run_verifier(packet_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_valid_fixture_passes_strict_cross_check(tmp_path: Path) -> None:
    packet_path = write_packet(tmp_path, valid_packet())
    result = run_verifier(packet_path, "--strict")
    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_injected_overclaim(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["checks"][0]["observed"] = "TEI is validated and production-ready"
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1
    assert "overclaim" in (result.stdout + result.stderr).lower()


def test_rejects_missing_non_claim_key(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["non_claims"] = [
        entry for entry in packet["non_claims"] if entry["key"] != "cleartext-transport"
    ]
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1
    assert "cleartext-transport" in (result.stdout + result.stderr)


def test_rejects_missing_surface(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["surfaces"] = [s for s in packet["surfaces"] if s["id"] != "S03"]
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1
    assert "S03" in (result.stdout + result.stderr)


def test_rejects_empty_observed(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["checks"][0]["observed"] = ""
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1


def test_rejects_missing_evidence_path(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["surfaces"][0]["evidence"] = ["crates/ln-storage/src/does_not_exist.rs"]
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1
    assert "does_not_exist" in (result.stdout + result.stderr)


def test_rejects_non_empty_managed_provider_hits(tmp_path: Path) -> None:
    packet = valid_packet()
    packet["rust_scope"]["managed_provider_hits"] = ["crates/foo/src/x.rs:openai"]
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1
    assert "managed_provider_hits" in (result.stdout + result.stderr)


def test_rejects_unparseable_recorded_at(tmp_path: Path) -> None:
    packet = copy.deepcopy(valid_packet())
    packet["recordedAt"] = "not-a-timestamp"
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1


def test_rejects_promoted_gate(tmp_path: Path) -> None:
    packet = copy.deepcopy(valid_packet())
    packet["promotion"] = True
    result = run_verifier(write_packet(tmp_path, packet))
    assert result.returncode == 1


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("verify_m215_s04_gate_packet_module", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def stage_s05_root(tmp_path: Path, verifier) -> Path:
    """Populate a temp root with the real S05 consuming test and frozen fixture."""
    test_target = tmp_path / verifier.S05_TEST_REF
    test_target.parent.mkdir(parents=True, exist_ok=True)
    test_target.write_bytes((ROOT / verifier.S05_TEST_REF).read_bytes())
    fixture_target = tmp_path / verifier.S05_FIXTURE_REF
    fixture_target.parent.mkdir(parents=True, exist_ok=True)
    fixture_target.write_bytes((ROOT / verifier.S05_FIXTURE_REF).read_bytes())
    return tmp_path


def test_s05_integration_consumer_present_in_real_root() -> None:
    verifier = load_verifier_module()
    # The real repository must satisfy the declared Integration-class binding.
    verifier.verify_s05_integration_consumer(ROOT)


def test_s05_integration_consumer_rejects_missing_test(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    root = stage_s05_root(tmp_path, verifier)
    (root / verifier.S05_TEST_REF).unlink()
    with pytest.raises(verifier.VerificationError) as excinfo:
        verifier.verify_s05_integration_consumer(root)
    assert "S05 consuming test is missing" in str(excinfo.value)


def test_s05_integration_consumer_rejects_fixture_drift(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    root = stage_s05_root(tmp_path, verifier)
    (root / verifier.S05_FIXTURE_REF).write_bytes(b"<altered/>")
    with pytest.raises(verifier.VerificationError) as excinfo:
        verifier.verify_s05_integration_consumer(root)
    assert "sha256 drift" in str(excinfo.value)


def test_s05_integration_consumer_rejects_missing_pipeline_marker(
    tmp_path: Path,
) -> None:
    verifier = load_verifier_module()
    root = stage_s05_root(tmp_path, verifier)
    test_path = root / verifier.S05_TEST_REF
    text = test_path.read_text(encoding="utf-8").replace(
        "export_cleaned_projection", "renamed_export"
    )
    test_path.write_text(text, encoding="utf-8")
    with pytest.raises(verifier.VerificationError) as excinfo:
        verifier.verify_s05_integration_consumer(root)
    assert "export_cleaned_projection" in str(excinfo.value)
