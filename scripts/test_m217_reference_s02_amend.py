"""Amendment-provenance pin for 44-FZ edition 50 (ADR-0031 D4/D8).

The S02 demo ("ed-50 amend markers: 22 laws, act marker 188-ФЗ") had no
dedicated carrier before this slice: the only ed-50 pins lived inside
``scripts/test_m217_reference_jsonld.py`` and covered just the 22 unique
(date, number) pairs plus "some act exists" -- never the marker count (151),
the concrete amending law, or its tier / ``resolved_path``. This battery pins
all of those, in two layers:

* **hermetic** -- reads the committed
  ``prd/migration/rust-evidence/m217-reference-amend-provenance.json`` and pins
  151 markers / 22 unique (date, number) pairs / exactly one ``act`` marker
  (``2013-07-02``, ``188-ФЗ``) with tier ``resolved_enacting_date`` and the
  act's resolved path. Needs no corpus.
* **corpus-gated re-derivation** -- when the pinned 44-FZ corpus is present,
  re-runs the Python reference (``glob_files`` / ``edition_number_of`` /
  ``parse_edition`` / ``resolve_amend``) on the ed-50 file and checks the same
  four facts, proving the committed artifact is reproducible rather than
  hand-written. Without the corpus it prints ``SKIP:`` and exits 0.

``scripts/m217_reference_jsonld.py`` is the differential reference (ADR-0031
D8); it is imported as-is and never modified here.

Run: ``uv run pytest -q scripts/test_m217_reference_s02_amend.py``
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import m217_reference_jsonld as reference  # noqa: E402

AMEND = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-amend-provenance.json"
CORPUS = REPO / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
CATALOG = REPO / "consru_export" / "consru_export" / "catalog.sqlite"

EDITION_NO = 50
EXPECTED_MARKERS = 151
EXPECTED_UNIQUE_LAWS = 22
ACT_DATE = "2013-07-02"
ACT_NUMBER = "188-ФЗ"
ACT_PATH_SUFFIX = "law_2013-07-02_188-fz_rev-unknown_5ea52dab.xml"


def corpus_available_at(root: Path) -> bool:
    """Pure, corpus-free predicate: does ``root`` hold the pinned 44-FZ corpus
    directory *and* its catalog? Both the hermetic gate and the re-derivation
    test use this so the skip decision can never disagree between them."""
    return (
        root / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
    ).is_dir() and (root / "consru_export" / "consru_export" / "catalog.sqlite").is_file()


def corpus_available() -> bool:
    return corpus_available_at(REPO)


def test_corpus_predicate_is_false_for_a_missing_root() -> None:
    # Negative test for the gate itself: a broken predicate would let the
    # corpus-dependent code run on a missing corpus and fail-open into a
    # traceback instead of a documented SKIP (exit 0).
    assert corpus_available_at(Path("/nonexistent-lns02-repo-root")) is False


def test_ed50_amend_markers_are_pinned_hermetically() -> None:
    assert AMEND.exists(), f"missing committed artifact: {AMEND}"
    artifact = json.loads(AMEND.read_text(encoding="utf-8"))

    # Self-consistency of the committed artifact (its own header count).
    assert artifact["counts"]["markers"] == len(artifact["markers"])

    markers = [m for m in artifact["markers"] if m["edition_no"] == EDITION_NO]
    assert len(markers) == EXPECTED_MARKERS, (
        f"ed-50 must carry {EXPECTED_MARKERS} amend markers, got {len(markers)}"
    )
    assert len({(m["date"], m["number"]) for m in markers}) == EXPECTED_UNIQUE_LAWS, (
        f"ed-50 must cite {EXPECTED_UNIQUE_LAWS} distinct (date, number) laws"
    )
    assert {m["tier"] for m in markers} == {"resolved_enacting_date"}, (
        "every ed-50 marker must resolve by enacting date"
    )

    acts = [m for m in markers if m["article"] == "act"]
    assert len(acts) == 1, f"exactly one act-level marker expected, got {len(acts)}"
    act = acts[0]
    assert act["date"] == ACT_DATE
    assert act["number"] == ACT_NUMBER
    assert act["tier"] == "resolved_enacting_date"
    assert act["resolved_path"].endswith(ACT_PATH_SUFFIX)

    print(
        "ed-50 amend (hermetic): "
        f"markers={len(markers)}, unique_laws={len({(m['date'], m['number']) for m in markers})}, "
        f"acts={len(acts)} act=({act['date']}, {act['number']}) tier={act['tier']}"
    )


def test_ed50_amend_markers_rederive_on_the_pinned_corpus() -> None:
    if not corpus_available():
        print("SKIP: consru_export 44-FZ corpus not available (ed-50 amend re-derivation)")
        return

    # Locate ed-50 by scanning the corpus (never hardcode the cache-buster hash).
    ed50 = [
        path
        for path in reference.glob_files(CORPUS)
        if reference.edition_number_of(path.name) == EDITION_NO
    ]
    assert len(ed50) == 1, f"exactly one ed-50 edition file expected, got {ed50}"
    path = ed50[0]

    # `parse_edition`'s annotation names five return values; the implementation
    # returns six (digests, edges, raw_headings, part_count, spans, amend).
    _digests, _edges, _raw_headings, _part_count, _spans, amend = reference.parse_edition(path)

    assert len(amend) == EXPECTED_MARKERS, (
        f"re-derived ed-50 must carry {EXPECTED_MARKERS} amend markers, got {len(amend)}"
    )
    assert len({(date, number) for _art, date, number in amend}) == EXPECTED_UNIQUE_LAWS

    acts = [entry for entry in amend if entry[0] == "act"]
    assert len(acts) == 1, f"exactly one act-level marker expected, got {acts}"
    (_art, iso, number) = acts[0]
    assert (iso, number) == (ACT_DATE, ACT_NUMBER)

    prefix = reference.corpus_prefix(CORPUS)
    con = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        tier, resolved = reference.resolve_amend(con, iso, number, prefix)
    finally:
        con.close()
    assert tier == "resolved_enacting_date"
    assert resolved is not None and resolved.endswith(ACT_PATH_SUFFIX)

    print(
        "ed-50 amend (re-derived): "
        f"markers={len(amend)}, "
        f"unique_laws={len({(date, number) for _art, date, number in amend})}, "
        f"acts={len(acts)} act=({iso}, {number}) tier={tier} path={resolved}"
    )
