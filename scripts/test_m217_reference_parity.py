#!/usr/bin/env python3
"""Differential battery: the Rust reference-layer port vs the Python reference.

The contract (ADR-0031 D8) is byte parity against the Python reference, and the
contract's exit codes (D6) are `0` ok / `2` argv / `3` unreadable / `5` schema /
`6` drift. This battery runs *both* implementations over one fixture corpus and
asserts:

* **derivable fixtures** — the four derived artifacts are byte-identical;
* **unreadable fixtures** — both fail closed with exit `3` (never a traceback
  on the Python side, never a panic on the Rust side);
* **the pinned 44-FZ corpus** — both accept the committed artifacts (`--check`
  exits `0`), so the extended fixtures cannot have been bought by loosening the
  original oracle.

The fixtures live under
``crates/ln-consultant-parser/tests/fixtures/reference-layer/`` and are the same
ones the Rust battery (``tests/reference_layer_fail_closed.rs``) uses. Catalogs
are built here (they are sqlite binaries, so they are not committed); the 44-FZ
catalog is a gitignored 410 MB corpus input and stays out of scope, checked for
presence only.

Run: ``uv run pytest scripts/test_m217_reference_parity.py -q``
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "scripts" / "m217_reference_jsonld.py"
FIXTURES = REPO / "crates" / "ln-consultant-parser" / "tests" / "fixtures" / "reference-layer"
CORPUS = REPO / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
CATALOG = REPO / "consru_export" / "consru_export" / "catalog.sqlite"
ARTIFACTS = (
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
)
COMMITTED = REPO / "prd" / "migration" / "rust-evidence"

# Both implementations must derive these and agree byte for byte.
DERIVABLE = (
    "basic",
    "nonmonotonic",
    "shrink",
    "entities",
    "decimal",
    "amends",
    "mixed",
    "selfclose",
    "table",
    "other-act",
)

# Both implementations must refuse these with exit 3 (ADR-0031 D6).
UNREADABLE = (
    "zero",  # 0-byte edition file
    "malformed",  # XML that never closes
    "notwordml",  # well-formed XML with no w:p
    "ns2006",  # WordML 2006, not the 2003 contract namespace
    "unclosed",  # <w:p> without </w:p>
    "badnum",  # edition file name without a numeric edition number
    "badentity",  # undeclared &nbsp; entity
    "dupnum",  # two editions claiming the same edition number
    # built by the battery, not committed:
    "empty",  # corpus dir with no edition files
    "corruptcat",  # catalog that is not a sqlite database
)

EXIT_INPUT = 3


def real_binary() -> Path:
    # Build before locating: a stale `target/release/reference_layer` from an
    # earlier build silently lacks newer flags (`--corpus-dir`), and preferring
    # release over debug would then test the wrong binary. cargo is a no-op when
    # the binary is already fresh.
    subprocess.run(
        ["cargo", "build", "-p", "ln-consultant-parser", "--offline", "--bin", "reference_layer"],
        cwd=str(REPO),
        check=True,
        capture_output=True,
    )
    return REPO / "target/debug/reference_layer"


def build_catalog(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.execute("create table editions (relative_path text, document_date text, number text)")
        con.executemany("insert into editions values (?, ?, ?)", rows)
        con.commit()
    finally:
        con.close()
    return path


def run_python(corpus: Path, catalog: Path, out_dir: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(REFERENCE),
            "--corpus-dir",
            str(corpus),
            "--catalog",
            str(catalog),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


def run_rust(binary: Path, corpus: Path, catalog: Path, out_dir: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            str(binary),
            "--corpus-dir",
            str(corpus),
            "--catalog",
            str(catalog),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


def make_corpus(tmp: Path) -> dict[str, tuple[Path, Path]]:
    """Copy the committed fixtures into a scratch corpus and add the two cases
    that cannot be committed (an empty directory, a corrupt catalog)."""
    cases: dict[str, tuple[Path, Path]] = {}
    for name in DERIVABLE + tuple(c for c in UNREADABLE if c not in ("empty", "corruptcat")):
        source = FIXTURES / name
        assert source.is_dir(), f"missing fixture {name}"
        target = tmp / name
        shutil.copytree(source, target)
        cases[name] = (target, tmp / "cat.sqlite")

    empty = tmp / "empty"
    empty.mkdir()
    cases["empty"] = (empty, tmp / "cat.sqlite")

    corrupt = tmp / "corruptcat"
    shutil.copytree(FIXTURES / "basic", corrupt)
    garbage = tmp / "corrupt.sqlite"
    garbage.write_bytes(b"not a sqlite database, just text\n" * 20)
    cases["corruptcat"] = (corrupt, garbage)

    build_catalog(
        tmp / "cat.sqlite",
        [
            ("exports/npa/x_rev-2013-07-02_a.xml", "2013-07-02", "188-ФЗ"),
            ("exports/npa/y_rev-2014-04-05_b.xml", "2014-04-05", "99-ФЗ"),
            (
                "exports/npa/other-act/edition-0001_rev-unknown_from-unknown_aaaaaaaa.xml",
                "2019-03-03",
                "11-ФЗ",
            ),
            (
                "exports/npa/other-act/edition-0002_rev-unknown_from-unknown_bbbbbbbb.xml",
                "2022-09-09",
                "11-ФЗ",
            ),
            (
                "exports/npa/law_2013-04-05_44-fz/edition-0001_rev-initial_from-unknown_x.xml",
                "2013-04-05",
                "44-ФЗ",
            ),
        ],
    )
    return cases


def test_derivable_fixtures_are_byte_identical(tmp_path: Path) -> None:
    binary = real_binary()
    cases = make_corpus(tmp_path)
    for name in DERIVABLE:
        corpus, catalog = cases[name]
        py_out = tmp_path / f"py-{name}"
        rs_out = tmp_path / f"rs-{name}"
        py_code, py_err = run_python(corpus, catalog, py_out)
        rs_code, rs_err = run_rust(binary, corpus, catalog, rs_out)
        assert py_code == 0, f"{name}: python exited {py_code}: {py_err}"
        assert rs_code == 0, f"{name}: rust exited {rs_code}: {rs_err}"
        for artifact in ARTIFACTS:
            py_bytes = (py_out / artifact).read_bytes()
            rs_bytes = (rs_out / artifact).read_bytes()
            assert py_bytes == rs_bytes, (
                f"{name}/{artifact}: the Rust port drifted from the Python reference"
            )


def test_unreadable_fixtures_fail_closed_in_both(tmp_path: Path) -> None:
    binary = real_binary()
    cases = make_corpus(tmp_path)
    for name in UNREADABLE:
        corpus, catalog = cases[name]
        py_code, py_err = run_python(corpus, catalog, tmp_path / f"py-neg-{name}")
        rs_code, rs_err = run_rust(binary, corpus, catalog, tmp_path / f"rs-neg-{name}")
        assert py_code == EXIT_INPUT, (
            f"{name}: python must exit {EXIT_INPUT} on unreadable input, got {py_code}: {py_err}"
        )
        assert rs_code == EXIT_INPUT, (
            f"{name}: rust must exit {EXIT_INPUT} on unreadable input, got {rs_code}: {rs_err}"
        )
        assert "Traceback" not in py_err, f"{name}: python must not traceback: {py_err}"


def test_committed_44fz_artifacts_still_accepted_by_both(tmp_path: Path) -> None:
    if not CORPUS.is_dir() or not CATALOG.is_file():
        import pytest

        pytest.skip("pinned 44-FZ corpus (gitignored) is not present")
    binary = real_binary()
    for who, command in (
        ("python", [sys.executable, str(REFERENCE)]),
        ("rust", [str(binary)]),
    ):
        result = subprocess.run(
            [*command, "--check"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{who} --check failed: {result.stdout} {result.stderr}"


def test_extended_corpus_did_not_change_the_pinned_oracle() -> None:
    # The four committed artifacts are the acceptance oracle; the fixture work
    # must not have rewritten them.
    for artifact in ARTIFACTS:
        assert (COMMITTED / artifact).is_file(), f"missing committed artifact {artifact}"
    timeline = json.loads((COMMITTED / ARTIFACTS[0]).read_text(encoding="utf-8"))
    assert timeline["counts"]["editions"] == 118
    assert timeline["counts"]["non_monotonic"] == 1
