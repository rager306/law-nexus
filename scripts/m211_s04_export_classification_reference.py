#!/usr/bin/env python3
"""M211 S04: Python differential reference export for NPA classification.

D519: this fixture is a *differential reference*, not an independent gold.
It is produced by reusing the executable spec in
``scripts/m207_context_graph_demo.py`` (``classify_type`` / ``classify_layers`` /
``lexicon`` / ``axes_contract``). No classification logic is copied here; the
original functions are called directly so the reference cannot silently drift
into a second implementation.

Usage:
  uv run python scripts/m211_s04_export_classification_reference.py          # write
  uv run python scripts/m211_s04_export_classification_reference.py --check  # verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m207_context_graph_demo as ref  # noqa: E402  (path inserted above)

PARITY = ROOT / "crates/ln-decode/tests/fixtures/npa-members/typed-parity-fixture.tsv"
LAWREF = ROOT / "crates/ln-decode/tests/fixtures/npa-lawref"
FIXTURE = ROOT / "crates/ln-decode/tests/fixtures/npa-members/classification-parity-fixture.tsv"

COLUMNS = [
    "kind",
    "doc",
    "canon",
    "body",
    "lemma",
    "bucket",
    "verdict",
    "graph",
    "identity_key",
    "why",
]

# (canon, body, expected graph, expected identity_key or None)
# All bodies are single-line snippets (no newlines); this is a fixture contract.
SYNTHETIC: list[tuple[str, str, str, str | None]] = [
    ("ТК", "", "refuse", None),
    ("ГОСТ 1234-2020", "", "overlay", None),
    ("ТР ТС 005/2011", "", "overlay", "deferred-undefined"),
    ("Письмо Минфина России", "", "refuse", None),
    ("Приказ", "ООО Ромашка", "refuse", None),
    ("КоАП РФ", "", "identifying_act", None),
    ("Постановление Пленума ВС РФ", "", "overlay", None),
    ("Решение УФАС по Челябинской области", "", "overlay", None),
    ("Распоряжение", "", "hold", None),
]

HEADER = [
    "# m211-classification-parity-fixture/v1 [bounded]",
    "# source = Python differential reference, NOT independent gold (D519)",
    "# exporter = scripts/m211_s04_export_classification_reference.py",
    "# frozen docs/canons = crates/ln-decode/tests/fixtures/npa-members/typed-parity-fixture.tsv",
    "# doc_text convention = raw UTF-8 fragment files from",
    "#   crates/ln-decode/tests/fixtures/npa-lawref/, concatenated with a single",
    '#   "\\n" separator and NO trimming. Per-block Python pipeline text is',
    "#   deliberately NOT reproduced here; both sides MUST use this convention.",
    '# synthetic body = single-line snippet (no newlines); doc column is "-" for',
    "#   synthetic rows; frozen rows keep body empty (both sides compute doc_text).",
    "# cyrillic is verbatim UTF-8, never escaped",
    "# " + "\t".join(COLUMNS),
]


def read_typed_parity() -> list[dict[str, object]]:
    """Parse the S02 typed-parity fixture into per-doc frags + distinct canons."""
    docs: list[dict[str, object]] = []
    cur: dict[str, object] | None = None
    for line in PARITY.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts[0] == "doc":
            cur = {"doc": parts[1], "frags": [], "types": []}
            docs.append(cur)
        elif parts[0] == "frag" and cur is not None:
            frags = cur["frags"]
            assert isinstance(frags, list)
            frags.append(parts[1])
        elif parts[0] == "typed" and cur is not None:
            canon = parts[3]
            types = cur["types"]
            assert isinstance(types, list)
            if canon not in types:
                types.append(canon)
    return docs


def doc_text(doc: dict[str, object]) -> str:
    frags = doc["frags"]
    assert isinstance(frags, list)
    return "\n".join((LAWREF / str(f)).read_text(encoding="utf-8") for f in frags)


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def _emit(kind: str, doc: str, canon: str, body: str, row: dict[str, str]) -> str:
    cells = [
        kind,
        doc,
        canon,
        body,
        row.get("lemma", ""),
        row.get("bucket", ""),
        row.get("verdict", ""),
        row.get("graph", ""),
        row.get("identity_key", ""),
        row.get("why", ""),
    ]
    return "\t".join(_cell(c) for c in cells)


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for doc in read_typed_parity():
        text = doc_text(doc)
        types = doc["types"]
        assert isinstance(types, list)
        for canon in types:
            form = ref.classify_type(str(canon), ref.lexicon())
            result = ref.classify_layers(str(canon), text, form)
            rows.append(
                {
                    "kind": "frozen",
                    "doc": doc["doc"],
                    "canon": str(canon),
                    "body": "",
                    "row": result,
                }
            )
    for canon, body, expected, expected_key in SYNTHETIC:
        form = ref.classify_type(canon, ref.lexicon())
        result = ref.classify_layers(canon, body, form)
        rows.append(
            {
                "kind": "synthetic",
                "doc": "-",
                "canon": canon,
                "body": body,
                "row": result,
                "expected": expected,
                "expected_key": expected_key,
            }
        )
    return rows


def render(rows: list[dict[str, object]]) -> str:
    lines = list(HEADER)
    for row in rows:
        result = row["row"]
        assert isinstance(result, dict)
        lines.append(
            _emit(
                str(row["kind"]),
                str(row["doc"]),
                str(row["canon"]),
                str(row["body"]),
                result,
            )
        )
    return "\n".join(lines) + "\n"


def _counts(rows: list[dict[str, object]]) -> tuple[int, int, int]:
    frozen = sum(1 for r in rows if r["kind"] == "frozen")
    synthetic = sum(1 for r in rows if r["kind"] == "synthetic")
    return len(rows), frozen, synthetic


def check(rows: list[dict[str, object]], rendered: str) -> list[str]:
    problems: list[str] = []
    if not FIXTURE.exists():
        return [f"fixture missing: {FIXTURE}"]
    on_disk = FIXTURE.read_text(encoding="utf-8")
    if on_disk != rendered:
        disk_lines = on_disk.splitlines()
        mem_lines = rendered.splitlines()
        diff = sum(
            1
            for i in range(max(len(disk_lines), len(mem_lines)))
            if (disk_lines[i] if i < len(disk_lines) else None)
            != (mem_lines[i] if i < len(mem_lines) else None)
        )
        problems.append(f"fixture differs from recomputation ({diff} differing lines)")
    total, frozen, synthetic = _counts(rows)
    if total < 40:
        problems.append(f"row count {total} < 40")
    index = {(str(r["kind"]), str(r["canon"]), str(r["body"])): r for r in rows}
    for canon, body, expected, expected_key in SYNTHETIC:
        entry = index.get(("synthetic", canon, body))
        if entry is None:
            problems.append(f"missing mandatory synthetic case: {canon!r} body={body!r}")
            continue
        result = entry["row"]
        assert isinstance(result, dict)
        if result.get("graph") != expected:
            problems.append(
                f"synthetic {canon!r}: graph={result.get('graph')!r} expected {expected!r}"
            )
        if expected_key is not None and result.get("identity_key") != expected_key:
            problems.append(
                f"synthetic {canon!r}: identity_key={result.get('identity_key')!r} "
                f"expected {expected_key!r}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="recompute in memory and compare against the tracked fixture",
    )
    args = parser.parse_args(argv)

    if FIXTURE.parent.name != "npa-members" or "npa-lawref" in FIXTURE.parts:
        print(f"refusing to write outside npa-members: {FIXTURE}", file=sys.stderr)
        return 2

    rows = build_rows()
    rendered = render(rows)
    total, frozen, synthetic = _counts(rows)

    if args.check:
        problems = check(rows, rendered)
        if problems:
            for problem in problems:
                print(f"FAIL: {problem}", file=sys.stderr)
            return 1
        print(
            "m211-s04-classification-reference: check ok "
            f"rows={total} frozen={frozen} synthetic={synthetic}"
        )
        return 0

    FIXTURE.write_text(rendered, encoding="utf-8")
    print(
        "m211-s04-classification-reference: wrote "
        f"rows={total} frozen={frozen} synthetic={synthetic} "
        f"path={FIXTURE.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
