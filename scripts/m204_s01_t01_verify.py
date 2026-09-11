#!/usr/bin/env python3
"""Deterministic T01 inventory verifier. Exit 0 prints T01_VERIFY_OK."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "prd/migration/rust-evidence/m204-s01-t01-gsd-inventory.json"
EXPECTED_PENDING = {
    "M205-p7xc54",
    "M206-jnbhlz",
    "M207-b2i96m",
    "M208-wrz6fg",
    "M209-2yg6ix",
    "M210-3afp79",
}


def main() -> int:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    scope = data["scope"]
    assert scope["external_paths_read"] is False
    assert scope["direct_database_access"] is False
    assert scope["database_written"] is False
    recon = data["status_reconciliation"]
    assert (recon["registry_total"], recon["complete"], recon["active"], recon["pending"]) == (
        211,
        204,
        1,
        6,
    )
    assert set(recon["observed_pending_ids"]) == EXPECTED_PENDING
    count = data["incidents"]["claim_matching_coordination_dispatch"]["count"]
    assert count == 190
    print("T01_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
