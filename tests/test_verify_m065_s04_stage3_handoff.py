from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-m065-s04-stage3-handoff.py"
HANDOFF_PATH = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s04" / "stage3-handoff.md"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m065_s04_stage3_handoff", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def _write_corpus(tmp_path: Path, texts: dict[str, str]) -> tuple[Path, ...]:
    files: tuple[Path, ...] = tuple()
    for name, text in texts.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        files = files + (path,)
    return files


# --------------------------------------------------------------------------
# diagnostic surface
# --------------------------------------------------------------------------


def test_lists_required_diagnostic_ids() -> None:
    verifier = load_verifier()

    assert set(verifier.DIAGNOSTIC_IDS) == {
        "missing_section",
        "missing_boundary_marker",
        "missing_proof_anchor",
        "missing_mem549_marker",
        "overclaim_detected",
    }


def test_no_subprocess_import() -> None:
    """This verifier is stdlib-only and inspection-only: NO subprocess anywhere."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "import subprocess" not in source
    assert "subprocess.run" not in source
    assert "subprocess.check_output" not in source
    assert "shell=True" not in source


def test_expected_sections_set() -> None:
    verifier = load_verifier()

    assert tuple(verifier.EXPECTED_SECTIONS) == (
        "## Status",
        "## Stage 2 \u2014 proven",
        "## Stage 3 \u2014 scope and gates",
        "## Preserved boundaries",
        "## Open revisit-triggers",
    )


def test_required_boundary_markers_set() -> None:
    verifier = load_verifier()

    labels = tuple(label for label, _ in verifier.REQUIRED_BOUNDARY_MARKERS)
    assert labels == (
        "R035/R037/R038",
        "R047",
        "R057",
        "R053",
        "CLI-install-only",
        "D084 Stage 3",
        "eaa4b24d",
    )


def test_required_proof_anchor_paths_set() -> None:
    verifier = load_verifier()

    assert tuple(verifier.REQUIRED_PROOF_ANCHOR_PATHS) == (
        "prd/architecture/acp/runtime/m065-s01/install-contract.md",
        "prd/architecture/acp/runtime/m065-s02/install-proof.json",
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json",
    )


def test_mem549_marker_value() -> None:
    verifier = load_verifier()
    assert verifier.MEM549_MARKER == "auto_commit_landed"


def test_overclaim_patterns_count() -> None:
    verifier = load_verifier()
    assert len(verifier.OVERCLAIM_PATTERNS) == 2


# --------------------------------------------------------------------------
# check_sections
# --------------------------------------------------------------------------


def test_check_sections_all_present() -> None:
    verifier = load_verifier()
    text = "\n".join(verifier.EXPECTED_SECTIONS)

    assert verifier.check_sections(text, HANDOFF_PATH) == []


@pytest.mark.parametrize("drop_index", range(5))
def test_check_sections_one_missing(drop_index: int) -> None:
    verifier = load_verifier()
    kept = list(verifier.EXPECTED_SECTIONS)
    dropped = kept.pop(drop_index)
    text = "\n".join(kept)

    diagnostics = verifier.check_sections(text, HANDOFF_PATH)
    assert len(diagnostics) == 1
    assert diagnostics[0].diagnostic_id == "missing_section"
    assert dropped in diagnostics[0].message


# --------------------------------------------------------------------------
# check_boundary_markers
# --------------------------------------------------------------------------


def test_check_boundary_markers_all_present() -> None:
    verifier = load_verifier()
    text = " ".join(alts[0] for _, alts in verifier.REQUIRED_BOUNDARY_MARKERS)

    assert verifier.check_boundary_markers(text, HANDOFF_PATH) == []


@pytest.mark.parametrize("drop_index", range(7))
def test_check_boundary_markers_one_missing(drop_index: int) -> None:
    verifier = load_verifier()
    markers = verifier.REQUIRED_BOUNDARY_MARKERS
    # include every marker EXCEPT the one at drop_index
    parts = []
    for idx, (_, alts) in enumerate(markers):
        if idx == drop_index:
            # replace with a neutral token that is NOT any of the alternatives
            parts.append("__definitely_not_present__")
        else:
            parts.append(alts[0])
    text = " ".join(parts)
    dropped_label = markers[drop_index][0]

    diagnostics = verifier.check_boundary_markers(text, HANDOFF_PATH)
    assert len(diagnostics) == 1
    assert diagnostics[0].diagnostic_id == "missing_boundary_marker"
    assert dropped_label in diagnostics[0].message


def test_check_boundary_markers_cli_install_only_space_form_satisfies() -> None:
    verifier = load_verifier()
    # the space-separated alternative must satisfy the hyphenated requirement
    text = "R035/R037/R038 R047 R057 R053 CLI install only D084 Stage 3 eaa4b24d"

    assert verifier.check_boundary_markers(text, HANDOFF_PATH) == []


# --------------------------------------------------------------------------
# check_proof_anchors
# --------------------------------------------------------------------------


def test_check_proof_anchors_all_present() -> None:
    verifier = load_verifier()
    text = "\n".join(verifier.REQUIRED_PROOF_ANCHOR_PATHS)

    assert verifier.check_proof_anchors(text, HANDOFF_PATH) == []


@pytest.mark.parametrize("drop_index", range(3))
def test_check_proof_anchors_one_missing(drop_index: int) -> None:
    verifier = load_verifier()
    kept = list(verifier.REQUIRED_PROOF_ANCHOR_PATHS)
    dropped = kept.pop(drop_index)
    text = "\n".join(kept)

    diagnostics = verifier.check_proof_anchors(text, HANDOFF_PATH)
    assert len(diagnostics) == 1
    assert diagnostics[0].diagnostic_id == "missing_proof_anchor"
    assert dropped in diagnostics[0].message


# --------------------------------------------------------------------------
# check_mem549_marker
# --------------------------------------------------------------------------


def test_check_mem549_marker_present() -> None:
    verifier = load_verifier()
    assert verifier.check_mem549_marker("the auto_commit_landed flag is true", HANDOFF_PATH) == []


def test_check_mem549_marker_missing() -> None:
    verifier = load_verifier()
    diagnostics = verifier.check_mem549_marker("nothing relevant here", HANDOFF_PATH)
    assert len(diagnostics) == 1
    assert diagnostics[0].diagnostic_id == "missing_mem549_marker"


# --------------------------------------------------------------------------
# scan_overclaim
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "validated R035",
        "R035 validated",
        "R037 validated",
        "R038 validated",
        "R035/R037/R038 validated",
        "validated R037/R038",
        "validated R035 fully",
    ],
)
def test_scan_overclaim_flags_affirmative_verb_adjacency(phrase: str, tmp_path: Path) -> None:
    verifier = load_verifier()
    files = _write_corpus(tmp_path, {"doc.md": phrase})

    summary, diagnostics = verifier.scan_overclaim(files)

    assert summary["status"] == "overclaim_detected"
    assert summary["hits"] >= 1
    assert diagnostics
    assert all(d.diagnostic_id == "overclaim_detected" for d in diagnostics)


@pytest.mark.parametrize(
    "phrase",
    [
        "no R035/R037/R038 validation",
        "R035/R037/R038 validation",  # noun, not a verb
        "must not be validated",
        "did not validate",
        "without validating",
        "R035",
        "R037/R038",
        "validation",
        "there is no R035/R037/R038 validation in Stage 2",
        "R035/R037/R038 \u2014 NOT validated by Stage 2",
    ],
)
def test_scan_overclaim_does_not_false_positive(phrase: str, tmp_path: Path) -> None:
    verifier = load_verifier()
    files = _write_corpus(tmp_path, {"doc.md": phrase})

    summary, diagnostics = verifier.scan_overclaim(files)

    assert summary["status"] == "clean"
    assert summary["hits"] == 0
    assert diagnostics == []


def test_scan_overclaim_missing_file_is_silent(tmp_path: Path) -> None:
    verifier = load_verifier()
    missing = tmp_path / "does_not_exist.md"

    summary, diagnostics = verifier.scan_overclaim((missing,))

    assert summary["status"] == "clean"
    assert diagnostics == []


def test_scan_overclaim_self_scans_zero_hits() -> None:
    """The verifier scans its own source as part of the default corpus; it must
    not flag itself (self-reference-safe design, same as T01)."""
    verifier = load_verifier()
    files = verifier._overclaim_scan_files()

    # the verifier's own source is in the default corpus
    assert SCRIPT_PATH in files
    summary, diagnostics = verifier.scan_overclaim(files)
    assert summary["status"] == "clean"
    assert diagnostics == []


# --------------------------------------------------------------------------
# verify() aggregation
# --------------------------------------------------------------------------


def test_verify_section_missing_yields_not_ok(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    # has markers/anchors/mem549 but NO required section headers
    handoff.write_text(
        "R035/R037/R038 R047 R057 R053 CLI-install-only D084 Stage 3 eaa4b24d\n"
        "prd/architecture/acp/runtime/m065-s01/install-contract.md\n"
        "prd/architecture/acp/runtime/m065-s02/install-proof.json\n"
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json\n"
        "auto_commit_landed\n",
        encoding="utf-8",
    )

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is False
    assert "missing_section" in diagnostic_ids(diagnostics)


def test_verify_boundary_missing_yields_not_ok(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        "\n".join(verifier.EXPECTED_SECTIONS) + "\n"
        "prd/architecture/acp/runtime/m065-s01/install-contract.md\n"
        "prd/architecture/acp/runtime/m065-s02/install-proof.json\n"
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json\n"
        "auto_commit_landed\n",
        encoding="utf-8",
    )  # no boundary markers

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is False
    assert "missing_boundary_marker" in diagnostic_ids(diagnostics)


def test_verify_proof_anchor_missing_yields_not_ok(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        "\n".join(verifier.EXPECTED_SECTIONS) + "\n"
        "R035/R037/R038 R047 R057 R053 CLI-install-only D084 Stage 3 eaa4b24d\n"
        "auto_commit_landed\n",
        encoding="utf-8",
    )  # no proof-anchor paths

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is False
    assert "missing_proof_anchor" in diagnostic_ids(diagnostics)


def test_verify_mem549_missing_yields_not_ok(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        "\n".join(verifier.EXPECTED_SECTIONS) + "\n"
        "R035/R037/R038 R047 R057 R053 CLI-install-only D084 Stage 3 eaa4b24d\n"
        "prd/architecture/acp/runtime/m065-s01/install-contract.md\n"
        "prd/architecture/acp/runtime/m065-s02/install-proof.json\n"
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json\n",
        encoding="utf-8",
    )  # no auto_commit_landed

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is False
    assert "missing_mem549_marker" in diagnostic_ids(diagnostics)


def test_verify_overclaim_yields_not_ok(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        "\n".join(verifier.EXPECTED_SECTIONS) + "\n"
        "R035/R037/R038 R047 R057 R053 CLI-install-only D084 Stage 3 eaa4b24d\n"
        "prd/architecture/acp/runtime/m065-s01/install-contract.md\n"
        "prd/architecture/acp/runtime/m065-s02/install-proof.json\n"
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json\n"
        "auto_commit_landed\n"
        "Stage 2 validated R035 fully.\n",  # overclaim
        encoding="utf-8",
    )

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is False
    assert "overclaim_detected" in diagnostic_ids(diagnostics)


def test_verify_synthetic_minimal_handoff_passes(tmp_path: Path) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        "\n".join(verifier.EXPECTED_SECTIONS) + "\n"
        "R035/R037/R038 R047 R057 R053 CLI-install-only D084 Stage 3 eaa4b24d\n"
        "prd/architecture/acp/runtime/m065-s01/install-contract.md\n"
        "prd/architecture/acp/runtime/m065-s02/install-proof.json\n"
        "prd/architecture/acp/runtime/m065-s03/workflow-proof.json\n"
        "auto_commit_landed\n",
        encoding="utf-8",
    )

    ok, diagnostics, summary = verifier.verify(handoff)
    assert ok is True
    assert diagnostics == []
    assert summary["handoff_ok"] is True
    assert summary["overclaim_scan"]["status"] == "clean"


def test_verify_real_handoff_passes() -> None:
    """Integration: the tracked handoff document is well-formed and honest."""
    verifier = load_verifier()
    assert HANDOFF_PATH.exists(), f"handoff document missing at {HANDOFF_PATH}"

    ok, diagnostics, summary = verifier.verify(HANDOFF_PATH)
    assert ok is True, diagnostics
    assert diagnostics == []
    assert summary["sections_expected"] == 5
    assert summary["boundary_markers_expected"] == 7
    assert summary["proof_anchors_expected"] == 3
    assert summary["overclaim_scan"]["status"] == "clean"
    assert summary["overclaim_scan"]["hits"] == 0


# --------------------------------------------------------------------------
# main() CLI behavior
# --------------------------------------------------------------------------


def test_main_exits_nonzero_on_section_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    verifier = load_verifier()
    handoff = tmp_path / "handoff.md"
    handoff.write_text("no sections here\n", encoding="utf-8")

    rc = verifier.main(["--handoff", str(handoff)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "missing_section" in captured.out


def test_main_passes_on_real_handoff(capsys: pytest.CaptureFixture[str]) -> None:
    verifier = load_verifier()
    rc = verifier.main(["--handoff", str(HANDOFF_PATH)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "stage3-handoff verification passed" in captured.out
