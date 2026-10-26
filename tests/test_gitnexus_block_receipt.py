"""Mechanical pins for the GitNexus index receipt and the AGENTS.md tool block (M001 task T006).

SC5 with E5 and N6: the tracked receipt must record the exact tracked analyze
command, a full 40-hex indexed head, the index counts, and the sha256 of the
exact AGENTS.md block between the gitnexus markers; the live block must match
that receipt, so a hand-edited block, a stale block, or a missing receipt is
detectable instead of being presented as the live index. A failed analyze
leaves the previous block and the previous receipt untouched and consistent,
which is exactly the state these pins enforce (E5).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS = REPO / "AGENTS.md"
RECEIPT = REPO / "prd" / "project-state" / "data" / "gitnexus-index.json"

SCHEMA = "law-nexus/gitnexus-index-receipt/v1"
BLOCK_START = "<!-- gitnexus:start -->"
BLOCK_END = "<!-- gitnexus:end -->"


def _tool_block() -> str:
    """The GitNexus-owned AGENTS.md block, inclusive of both markers."""
    text = AGENTS.read_text(encoding="utf-8")
    start = text.index(BLOCK_START)
    end = text.index(BLOCK_END) + len(BLOCK_END)
    return text[start:end]


def test_receipt_exists_with_schema_command_and_full_head() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["schema"] == SCHEMA
    command = receipt["command"]
    assert command.startswith("node .gitnexus/run.cjs analyze"), (
        f"receipt must record the tracked runner command: {command!r}"
    )
    assert "law-nexus" in command
    assert re.fullmatch(r"[0-9a-f]{40}", receipt["indexed_head"]), (
        f"indexed head is not a full 40-hex SHA: {receipt['indexed_head']!r}"
    )
    assert receipt["generated_at"]


def test_agents_block_hash_matches_receipt() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    digest = hashlib.sha256(_tool_block().encode("utf-8")).hexdigest()
    assert digest == receipt["agents_block_sha256"], (
        "the AGENTS.md tool block does not match the recorded receipt: "
        "the block was hand-edited or the receipt is stale (E5, N6)"
    )


def test_receipt_counts_appear_in_block() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    block = _tool_block()
    for field in ("symbols", "relationships", "execution_flows"):
        count = receipt["counts"][field]
        assert str(count) in block, f"receipt count {field}={count} is absent from the block"


def test_block_names_the_indexed_repo() -> None:
    assert "law-nexus" in _tool_block()
