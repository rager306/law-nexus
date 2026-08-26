"""Repository-document contracts for the bounded temporal model crosswalk."""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "prd" / "temporal-legal-model.md"
REGISTER = ROOT / "prd" / "architecture" / "temporal-semantic-gap-register.md"

# Same principle as governor._GOLDEN_CORPUS_EXPECTED_COVERAGE: expected counters
# are the review canon, never re-derived from the files.
EXPECTED_TL_GC_COUNT = 19  # review-26 companion / temporal-legal-model §11 table
EXPECTED_GC_COUNT = 40  # D275 / review-26 section 10


def _tsg015_counter_drifts(model_text: str, register_text: str) -> list[str]:
    """Return neutral process-language drift findings for the TSG-015 counter formula.

    Pure in-memory inspection (no I/O); tests read the tracked canon files and
    pass their text here. Pinned claims:

    - temporal-legal-model §11 staged golden-case table holds exactly the
      canonical TL-GC01..TL-GC{EXPECTED_TL_GC_COUNT} identifiers once; slicing
      stops before ### 11.1 because the reconciliation map repeats every id.
    - The register row ``| TSG-015 |`` claims "19 TL-GC paper oracles" plus
      "40 GC catalog rows", without asserting the stale collapsed figure.
    - Section 11.1 states the two series are counted ``separately``. The stale
      '18 paper cases' quote is only banned in the register row; section 11.1
      keeps an honest disclaimer citing it.
    """
    drifts: list[str] = []

    rows = re.findall(r"^\| TSG-015 \|.*$", register_text, flags=re.MULTILINE)
    if len(rows) != 1:
        drifts.append(
            f"temporal-semantic-gap-register holds {len(rows)} '| TSG-015 |' rows, expected 1"
        )
    else:
        row = rows[0]
        if "19 TL-GC paper oracles" not in row:
            drifts.append("register TSG-015 row misses the canon claim '19 TL-GC paper oracles'")
        if "40 GC catalog rows" not in row:
            drifts.append("register TSG-015 row misses the canon claim '40 GC catalog rows'")
        if "18 paper cases" in row:
            drifts.append(
                "register TSG-015 row asserts the stale collapsed counter '18 paper cases'"
            )

    heading = "## 11. Staged golden-case catalog"
    _, sep, after_heading = model_text.partition(heading)
    if not sep:
        drifts.append("temporal-legal-model lost the '## 11. Staged golden-case catalog' heading")
        return drifts

    table_text, sub_sep, after_subheading = after_heading.partition("\n### 11.1")
    if not sub_sep:
        drifts.append("temporal-legal-model section 11 lost the '### 11.1' subsection marker")
        return drifts

    ids = re.findall(r"\| (TL-GC\d{2}) \|", table_text)
    expected_ids = [f"TL-GC{index:02d}" for index in range(1, EXPECTED_TL_GC_COUNT + 1)]
    if len(ids) != EXPECTED_TL_GC_COUNT:
        drifts.append(
            f"section 11 staged catalog lists {len(ids)} TL-GC identifier cells,"
            f" review canon pins {EXPECTED_TL_GC_COUNT}"
        )
    if sorted(set(ids)) != expected_ids:
        missing = sorted(set(expected_ids) - set(ids))
        unexpected = sorted(set(ids) - set(expected_ids))
        drifts.append(
            f"section 11 staged catalog id set drifted from TL-GC01..TL-GC{EXPECTED_TL_GC_COUNT}"
            f" (missing={missing}, unexpected={unexpected})"
        )
    elif ids != expected_ids:
        drifts.append(
            "section 11 staged catalog lists TL-GC identifiers out of canonical"
            f" order TL-GC01..TL-GC{EXPECTED_TL_GC_COUNT}"
        )

    subsection_text = after_subheading.partition("\n## ")[0]
    for fragment in ("19 TL-GC", "40 GC catalog", "separately"):
        if fragment not in subsection_text:
            drifts.append(
                f"temporal-legal-model section 11.1 misses canon fragment '{fragment}'"
                " for the separately counted series"
            )

    return drifts


def test_primary_critique_contract_matrix_accounts_for_all_fourteen_areas() -> None:
    text = MODEL.read_text(encoding="utf-8")
    heading = "## 14. Primary-critique contract completeness matrix"
    assert heading in text
    section = text.split(heading, maxsplit=1)[1].split("\n## ", maxsplit=1)[0]

    areas = (
        "Glossary",
        "Entity model",
        "Event taxonomy",
        "Temporal axes",
        "Applicability DSL",
        "Status model",
        "Provenance",
        "Conflict",
        "Correction",
        "Invariants",
        "Deterministic API",
        "Golden cases",
        "Error taxonomy",
        "Proof gates",
    )
    rows = [line for line in section.splitlines() if line.startswith("|")]
    area_rows = [line for line in rows if any(line.startswith(f"| {area} |") for area in areas)]
    for area in areas:
        assert sum(line.startswith(f"| {area} |") for line in area_rows) == 1

    allowed_statuses = {
        "present",
        "present as paper rules",
        "present as paper gates",
        "partial",
        "absent",
        "deferred-undefined",
        "design-only inventory",
    }
    assert {line.split("|")[2].strip() for line in area_rows} <= allowed_statuses
    assert "paper coverage only" in " ".join(section.split())
    assert "no stable Rust signature or wire contract may be inferred" in section
    assert "not executable legal gold" in section


def test_primary_critique_matrix_preserves_absent_and_deferred_cells() -> None:
    text = MODEL.read_text(encoding="utf-8")
    section = text.split("## 14. Primary-critique contract completeness matrix", maxsplit=1)[
        1
    ].split("\n## ", maxsplit=1)[0]

    assert "| Event taxonomy | design-only inventory |" in section
    assert "| Applicability DSL | deferred-undefined |" in section
    assert "| Deterministic API | absent |" in section
    assert "| Error taxonomy | absent |" in section
    assert "neither accepts a schema nor closes a TSG row" in section


def test_tsg015_live_surfaces_count_nineteen_tl_gc_and_forty_gc_separately() -> None:
    model_text = MODEL.read_text(encoding="utf-8")
    register_text = REGISTER.read_text(encoding="utf-8")
    assert _tsg015_counter_drifts(model_text, register_text) == []


# ---------------------------------------------------------------------------
# Inline-negative fixtures (T02): known historical counter regressions the
# detector must catch. All mutations are pure in-memory string edits of the
# tracked canon texts -- no tmp_path, no writes to disk. The live §11.1 stale
# disclaimer stays intact everywhere, so the live-positive test above must
# remain green alongside these fixtures (MEM1145).
# ---------------------------------------------------------------------------

_LIVE_REGISTER_FORMULA = (
    "19 TL-GC paper oracles in temporal-legal-model §11"
    " plus 40 GC catalog rows in golden-corpus-catalog.yaml"
)


def _mutate_register_row_to_stale_collapsed_counter(
    model_text: str, register_text: str
) -> tuple[str, str]:
    """M184 regression: the TSG-015 row re-claims the collapsed figure alone."""
    assert _LIVE_REGISTER_FORMULA in register_text, (
        "fixture drifted: live register no longer contains the pinned formula"
    )
    return model_text, register_text.replace(_LIVE_REGISTER_FORMULA, "18 paper cases")


def _mutate_section11_to_drop_tl_gc19_table_row(
    model_text: str, register_text: str
) -> tuple[str, str]:
    """Canonical id-set regression: section 11 loses the TL-GC19 table row."""
    heading_start = model_text.index("## 11. Staged golden-case catalog")
    subsection_start = model_text.index("\n### 11.1", heading_start)
    table = model_text[heading_start:subsection_start]
    trimmed_table, dropped_rows = re.subn(r"^.*\| TL-GC19 \|.*\n", "", table, flags=re.MULTILINE)
    assert dropped_rows == 1, f"fixture expected one TL-GC19 row, found {dropped_rows}"
    return (
        model_text[:heading_start] + trimmed_table + model_text[subsection_start:],
        register_text,
    )


def _mutate_register_row_to_merge_both_counters(
    model_text: str, register_text: str
) -> tuple[str, str]:
    """Separateness regression: both counted series collapse into one figure."""
    assert _LIVE_REGISTER_FORMULA in register_text, (
        "fixture drifted: live register no longer contains the pinned formula"
    )
    return model_text, register_text.replace(
        _LIVE_REGISTER_FORMULA, "59 cases in golden-corpus-catalog.yaml"
    )


@pytest.mark.parametrize(
    ("drift_mutator", "expected_fragments"),
    [
        pytest.param(
            _mutate_register_row_to_stale_collapsed_counter,
            ("register TSG-015 row asserts the stale collapsed counter '18 paper cases'",),
            id="register-row-reasserts-stale-18-paper-cases",
        ),
        pytest.param(
            _mutate_section11_to_drop_tl_gc19_table_row,
            ("section 11 staged catalog id set drifted from TL-GC01..TL-GC19",),
            id="section-11-drops-the-tl-gc19-table-row",
        ),
        pytest.param(
            _mutate_register_row_to_merge_both_counters,
            (
                "register TSG-015 row misses the canon claim '19 TL-GC paper oracles'",
                "register TSG-015 row misses the canon claim '40 GC catalog rows'",
            ),
            id="register-row-merges-counters-into-one-figure",
        ),
    ],
)
def test_tsg015_counter_drift_detector_flags_known_counter_regressions(
    drift_mutator: Callable[[str, str], tuple[str, str]],
    expected_fragments: tuple[str, ...],
) -> None:
    """Red-on-fixture, green-as-test: each mutation produces a named drift."""
    model_text = MODEL.read_text(encoding="utf-8")
    register_text = REGISTER.read_text(encoding="utf-8")

    drifted_model, drifted_register = drift_mutator(model_text, register_text)

    drifts = _tsg015_counter_drifts(drifted_model, drifted_register)
    assert drifts, f"{drift_mutator.__name__} produced no drift finding"
    joined_findings = "\n".join(drifts)
    for fragment in expected_fragments:
        assert fragment in joined_findings
