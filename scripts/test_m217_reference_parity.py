#!/usr/bin/env python3
"""Differential battery: the Rust reference-layer port vs the Python reference.

The contract (ADR-0031 D8) is byte parity against the Python reference, and the
contract's exit codes (D6) are `0` ok / `2` argv / `3` unreadable / `5` schema /
`6` drift. This battery runs *both* implementations over one fixture corpus and
asserts:

* **derivable fixtures** — the four derived artifacts are byte-identical, and
  the two ed-50 measurement artifacts are *absent* (D782 non-applicability is
  not drift: those corpora carry no edition 50);
* **the hermetic ed-50 fixture** (`measure-ed50`) — both implementations derive
  all six artifacts (the four derived plus the D4 references and the D5
  contents ladder) and they are byte-identical, without the gitignored 44-FZ
  corpus and without the 44-FZ catalog;
* **non-applicable `--check`** — a fixture corpus without edition 50 stays exit
  `0` in check mode (never `3`, never `6`);
* **unreadable fixtures** — both fail closed with exit `3` (never a traceback
  on the Python side, never a panic on the Rust side);
* **the pinned 44-FZ corpus** — both accept the committed six artifacts
  (`--check` exits `0`), so the extended fixtures cannot have been bought by
  loosening the original oracle.

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

# The four full-corpus artifacts (always written) and the two ed-50-scoped
# measurement artifacts (written only where the corpus carries edition 50).
CORE_ARTIFACTS = (
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
)
MEASUREMENT_ARTIFACTS = (
    "m217-reference-references.json",
    "m217-reference-pageindex.json",
)
ARTIFACTS = CORE_ARTIFACTS + MEASUREMENT_ARTIFACTS
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

# The hermetic ed-50 fixture: one WordML-2003 edition carrying every S02 layer
# (preamble block, chapter, §, two articles with part/punkt/subpunkt/block, an
# internal reference, an external-requisite sentence, a deep-link candidate and
# an amendment marker). Its own catalog (below) resolves the requisites, so all
# three resolution tiers are exercised without the 44-FZ corpus.
MEASURE_FIXTURE = "measure-ed50"
MEASURE_EDITION_FILE = "edition-0050_rev-2017-01-01_from-unknown_deadbeef.xml"
MEASURE_CATALOG_ROWS = (
    (
        "exports/npa/measure-ed50/law_2017-01-01_1-fz/edition-0001_rev-2017-01-01_from-unknown_11111111.xml",
        "2017-01-01",
        "1-ФЗ",
    ),
    (
        "exports/npa/measure-ed50/law_2017-02-02_2-fz/edition-0001_rev-2017-02-02_from-unknown_22222222.xml",
        "2017-02-02",
        "2-ФЗ",
    ),
)


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


def run_python(corpus: Path, catalog: Path, out_dir: Path, *extra: str) -> tuple[int, str, str]:
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
            *extra,
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def run_rust(
    binary: Path, corpus: Path, catalog: Path, out_dir: Path, *extra: str
) -> tuple[int, str, str]:
    result = subprocess.run(
        [
            str(binary),
            "--corpus-dir",
            str(corpus),
            "--catalog",
            str(catalog),
            "--out-dir",
            str(out_dir),
            *extra,
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def make_corpus(tmp: Path) -> dict[str, tuple[Path, Path]]:
    """Copy the committed fixtures into a scratch corpus and add the two cases
    that cannot be committed (an empty directory, a corrupt catalog). The ed-50
    case gets its own catalog so its measurement cannot perturb the other
    fixtures' oracle output."""
    cases: dict[str, tuple[Path, Path]] = {}
    names = (
        DERIVABLE
        + (MEASURE_FIXTURE,)
        + tuple(c for c in UNREADABLE if c not in ("empty", "corruptcat"))
    )
    for name in names:
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
    # Dedicated catalog for the ed-50 fixture: the two enacting acts its
    # requisites name. The 2018-03-03 / 2-ФЗ mention resolves by number only and
    # the 2019-04-04 / 999-ФЗ mention stays unresolved, so the fixture exercises
    # all three resolution tiers.
    ed50_corpus, _shared = cases[MEASURE_FIXTURE]
    cases[MEASURE_FIXTURE] = (
        ed50_corpus,
        build_catalog(tmp / "cat-ed50.sqlite", list(MEASURE_CATALOG_ROWS)),
    )
    return cases


def test_derivable_fixtures_are_byte_identical(tmp_path: Path) -> None:
    binary = real_binary()
    cases = make_corpus(tmp_path)
    for name in DERIVABLE:
        corpus, catalog = cases[name]
        py_out = tmp_path / f"py-{name}"
        rs_out = tmp_path / f"rs-{name}"
        py_code, _py_stdout, py_err = run_python(corpus, catalog, py_out)
        rs_code, _rs_stdout, rs_err = run_rust(binary, corpus, catalog, rs_out)
        assert py_code == 0, f"{name}: python exited {py_code}: {py_err}"
        assert rs_code == 0, f"{name}: rust exited {rs_code}: {rs_err}"
        for artifact in CORE_ARTIFACTS:
            py_bytes = (py_out / artifact).read_bytes()
            rs_bytes = (rs_out / artifact).read_bytes()
            assert py_bytes == rs_bytes, (
                f"{name}/{artifact}: the Rust port drifted from the Python reference"
            )
        # D782: without edition 50 the measurement is not applicable — not an
        # error and not drift, so nothing is written where the ed-50 artifacts
        # would go.
        for artifact in MEASUREMENT_ARTIFACTS:
            assert not (py_out / artifact).exists(), (
                f"{name}: python wrote {artifact} for a corpus without edition 50"
            )
            assert not (rs_out / artifact).exists(), (
                f"{name}: rust wrote {artifact} for a corpus without edition 50"
            )


def test_measure_ed50_artifacts_are_byte_identical(tmp_path: Path) -> None:
    """The hermetic six-artifact differential barrier (ADR-0031 D4 + D5, D782).

    Both implementations derive the four full-corpus artifacts plus the ed-50 D4
    references and D5 contents ladder from one committed fixture and one
    committed catalog seed, and every one of the six must be byte-identical.
    """
    binary = real_binary()
    cases = make_corpus(tmp_path)
    corpus, catalog = cases[MEASURE_FIXTURE]
    assert (corpus / MEASURE_EDITION_FILE).is_file(), "ed-50 fixture is not edition 50"

    py_out = tmp_path / "py-ed50"
    rs_out = tmp_path / "rs-ed50"
    py_code, py_stdout, py_err = run_python(corpus, catalog, py_out)
    rs_code, rs_stdout, rs_err = run_rust(binary, corpus, catalog, rs_out)
    assert py_code == 0, f"python exited {py_code}: {py_err}"
    assert rs_code == 0, f"rust exited {rs_code}: {rs_err}"
    assert "measurement not applicable" not in py_stdout, py_stdout
    assert "measurement not applicable" not in rs_stdout, rs_stdout

    for artifact in ARTIFACTS:
        py_path = py_out / artifact
        rs_path = rs_out / artifact
        assert py_path.is_file(), f"python did not write {artifact}: {py_stdout}"
        assert rs_path.is_file(), f"rust did not write {artifact}: {rs_stdout}"
        assert py_path.read_bytes() == rs_path.read_bytes(), (
            f"{MEASURE_FIXTURE}/{artifact}: the Rust port drifted from the Python reference"
        )

    # The fixture must actually carry every S02 layer — a differential case that
    # silently degenerates into a trivial corpus would still be byte-identical
    # and prove nothing. These pins mirror the layer definitions (D4/D5) and are
    # updated only together with the fixture.
    references = json.loads((py_out / "m217-reference-references.json").read_text("utf-8"))
    counts = references["counts"]
    assert counts == {
        "candidates": 2,
        "internal": 1,
        "external_sentence": 1,
        "deep_link_candidates": 2,
        "deep_links": 0,
        "requisites": 6,
        "requisites_exact_date": 4,
        "requisites_unique": 4,
    }, counts
    assert references["edges_internal"] == [["statya-2", "statya-1"]]
    assert references["edges_external_sentence"] == [["statya-1", "statya-2"]]
    assert {row["tier"] for row in references["requisites"]} == {
        "resolved_enacting_date",
        "resolved_number_only",
        "unresolved",
    }

    pageindex = json.loads((py_out / "m217-reference-pageindex.json").read_text("utf-8"))
    ladder = pageindex["counts"]
    assert ladder == {
        "total_nodes": 16,
        "sections": 0,
        "chapters": 1,
        "paragraphs": 1,
        "articles": 2,
        "parts": 5,
        "punkts": 2,
        "subpoints": 2,
        "blocks": 3,
        "max_depth": 7,
        "chars": 1119,
    }, ladder
    levels = {node["level"] for node in pageindex["nodes"]}
    assert levels == {2, 3, 4, 5, 6, 7}, levels


def test_check_on_a_corpus_without_edition_50_stays_exit_0(tmp_path: Path) -> None:
    """Non-applicability is not drift: a fixture corpus without edition 50 writes
    the four core artifacts, leaves the two measurement artifacts absent, and
    `--check` over the same directory exits 0 in both implementations (D782)."""
    binary = real_binary()
    cases = make_corpus(tmp_path)
    corpus, catalog = cases["basic"]
    py_out = tmp_path / "py-gate"
    rs_out = tmp_path / "rs-gate"
    py_code, py_stdout, py_err = run_python(corpus, catalog, py_out)
    rs_code, rs_stdout, rs_err = run_rust(binary, corpus, catalog, rs_out)
    assert py_code == 0, f"python exited {py_code}: {py_err}"
    assert rs_code == 0, f"rust exited {rs_code}: {rs_err}"
    assert "measurement not applicable" in py_stdout, py_stdout
    assert "measurement not applicable" in rs_stdout, rs_stdout
    for artifact in MEASUREMENT_ARTIFACTS:
        assert not (py_out / artifact).exists(), f"python wrote {artifact}"
        assert not (rs_out / artifact).exists(), f"rust wrote {artifact}"

    for who, out_dir, run in (
        ("python", py_out, run_python),
        ("rust", rs_out, run_rust),
    ):
        args = (binary, corpus, catalog, out_dir) if who == "rust" else (corpus, catalog, out_dir)
        code, stdout, stderr = run(*args, "--check")
        assert code == 0, f"{who} --check on a corpus without edition 50 exited {code}: {stderr}"
        assert "check=ok" in stdout, stdout


def test_unreadable_fixtures_fail_closed_in_both(tmp_path: Path) -> None:
    binary = real_binary()
    cases = make_corpus(tmp_path)
    for name in UNREADABLE:
        corpus, catalog = cases[name]
        py_code, _py_stdout, py_err = run_python(corpus, catalog, tmp_path / f"py-neg-{name}")
        rs_code, _rs_stdout, rs_err = run_rust(binary, corpus, catalog, tmp_path / f"rs-neg-{name}")
        assert py_code == EXIT_INPUT, (
            f"{name}: python must exit {EXIT_INPUT} on unreadable input, got {py_code}: {py_err}"
        )
        assert rs_code == EXIT_INPUT, (
            f"{name}: rust must exit {EXIT_INPUT} on unreadable input, got {rs_code}: {rs_err}"
        )
        assert "Traceback" not in py_err, f"{name}: python must not traceback: {py_err}"


def test_committed_44fz_artifacts_still_accepted_by_both() -> None:
    if not CORPUS.is_dir() or not CATALOG.is_file():
        import pytest

        pytest.skip("SKIP: pinned 44-FZ corpus (gitignored) is not present")
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
        # The 44-FZ corpus carries edition 50, so the same run must have checked
        # all six artifacts — the extended fixture work cannot have loosened the
        # pinned oracle into a four-artifact check.
        assert "check=ok" in result.stdout, result.stdout
        assert "measurement not applicable" not in result.stdout, result.stdout


def test_extended_corpus_did_not_change_the_pinned_oracle() -> None:
    # The committed artifacts are the acceptance oracle; the fixture work must
    # not have rewritten them. The ed-50 measurement counts are the S02 pins.
    for artifact in ARTIFACTS:
        assert (COMMITTED / artifact).is_file(), f"missing committed artifact {artifact}"
    timeline = json.loads((COMMITTED / CORE_ARTIFACTS[0]).read_text(encoding="utf-8"))
    assert timeline["counts"]["editions"] == 118
    assert timeline["counts"]["non_monotonic"] == 1

    references = json.loads((COMMITTED / "m217-reference-references.json").read_text("utf-8"))
    assert references["counts"] == {
        "candidates": 379,
        "internal": 346,
        "external_sentence": 33,
        "deep_link_candidates": 1,
        "deep_links": 0,
        "requisites": 611,
        "requisites_exact_date": 609,
        "requisites_unique": 50,
    }
    assert references["scope"] == {"act_dir": "law_2013-04-05_44-fz", "edition_no": 50}

    pageindex = json.loads((COMMITTED / "m217-reference-pageindex.json").read_text("utf-8"))
    assert pageindex["counts"] == {
        "total_nodes": 3003,
        "sections": 0,
        "chapters": 8,
        "paragraphs": 9,
        "articles": 141,
        "parts": 1164,
        "punkts": 904,
        "subpoints": 108,
        "blocks": 669,
        "max_depth": 7,
        "chars": 848535,
    }
