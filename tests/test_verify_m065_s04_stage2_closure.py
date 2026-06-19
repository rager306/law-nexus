from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-m065-s04-stage2-closure.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m065_s04_stage2_closure", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


class _FakeProc:
    """Minimal stand-in for subprocess.CompletedProcess (only .returncode used)."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _all_ok_runner(cmd: list[str]) -> _FakeProc:
    return _FakeProc(0)


def _failing_runner(cmd: list[str]) -> _FakeProc:
    return _FakeProc(1, stderr="boom")


def _write_overclaim_corpus(tmp_path: Path, texts: dict[str, str]) -> tuple[Path, ...]:
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
        "prior_verifier_failed",
        "overclaim_detected",
        "main_state_residue",
        "boundary_markers_missing",
    }


def test_imports_subprocess_only_for_prior_verifiers() -> None:
    """Unlike S02/S03 (subprocess-free), S04 legitimately re-runs the prior
    verifiers, so subprocess is allowed. The overclaim scan must not shell out."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    # subprocess IS imported and used (only for the prior verifiers)
    assert "import subprocess" in source
    # no shell pipes / grep subprocess; subprocess.run uses a list, no shell=True
    assert "shell=True" not in source
    assert "subprocess.check_output" not in source


def test_prior_verifier_scripts_set() -> None:
    verifier = load_verifier()

    assert set(verifier.PRIOR_VERIFIER_SCRIPTS) == {
        ("s01", ROOT / "scripts" / "verify-m065-s01-install-contract.py"),
        ("s02", ROOT / "scripts" / "verify-m065-s02-release-install.py"),
        ("s03", ROOT / "scripts" / "verify-m065-s03-workflow-proof.py"),
    }


def test_overclaim_scan_files_include_artifacts_and_scripts() -> None:
    verifier = load_verifier()
    expected = {
        ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s01" / "install-contract.md",
        ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s02" / "install-proof.json",
        ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s03" / "workflow-proof.json",
        ROOT / "scripts" / "verify-m065-s01-install-contract.py",
        ROOT / "scripts" / "verify-m065-s02-release-install.py",
        ROOT / "scripts" / "verify-m065-s03-workflow-proof.py",
        ROOT / "scripts" / "verify-m065-s04-stage2-closure.py",
    }
    assert set(verifier.OVERCLAIM_SCAN_FILES) == expected


def test_expected_boundary_markers_set() -> None:
    verifier = load_verifier()

    labels = {label for label, _ in verifier.EXPECTED_BOUNDARY_MARKERS}
    assert labels == {"no R035/R037/R038 validation", "R047", "CLI-install-only", "D084"}


# --------------------------------------------------------------------------
# check_prior_verifiers
# --------------------------------------------------------------------------


def test_check_prior_verifiers_all_pass() -> None:
    verifier = load_verifier()

    per_rc, diagnostics = verifier.check_prior_verifiers(runner=_all_ok_runner)

    assert diagnostics == []
    assert per_rc == {"s01": 0, "s02": 0, "s03": 0}


def test_check_prior_verifiers_one_fails(tmp_path: Path) -> None:
    verifier = load_verifier()

    per_rc, diagnostics = verifier.check_prior_verifiers(runner=_failing_runner)

    ids = diagnostic_ids(diagnostics)
    assert "prior_verifier_failed" in ids
    # all three keys present even on failure
    assert per_rc == {"s01": 1, "s02": 1, "s03": 1}
    assert any("exited 1" in d.message for d in diagnostics)


def test_check_prior_verifiers_runner_raises() -> None:
    verifier = load_verifier()

    def raising_runner(cmd: list[str]) -> object:
        raise TimeoutError("timed out")

    per_rc, diagnostics = verifier.check_prior_verifiers(runner=raising_runner)

    ids = diagnostic_ids(diagnostics)
    assert "prior_verifier_failed" in ids
    assert per_rc == {"s01": -1, "s02": -1, "s03": -1}
    assert any("could not run" in d.message for d in diagnostics)


# --------------------------------------------------------------------------
# scan_overclaim
# --------------------------------------------------------------------------


def _overclaim_summary(diagnostics: list[object]) -> object:
    return getattr(diagnostics[0], "diagnostic_id") if diagnostics else None


def test_scan_overclaim_clean_corpus(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(
        tmp_path,
        {
            "a.md": "Stage 2 keeps the boundary: no R035/R037/R038 validation.\n",
            "b.json": '{"r": "R047 contract-phase honored", "d": "D084 Stage 3"}',
        },
    )

    summary, diagnostics = verifier.scan_overclaim(corpus)

    assert diagnostics == []
    assert summary["status"] == "clean"
    assert summary["hits"] == 0
    assert summary["patterns_scanned"] == len(verifier.OVERCLAIM_PATTERNS)


@pytest.mark.parametrize(
    "phrase",
    [
        "validated R035",
        "R035 validated",
        "R037 validated",
        "R038 validated",
        "R035/R037/R038 validated",
        "validated R037",
        "validated R038",
        "We validated R035 in Stage 2.",
    ],
)
def test_scan_overclaim_flags_affirmative_verb_adjacency(tmp_path: Path, phrase: str) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(tmp_path, {"over.md": phrase + "\n"})

    summary, diagnostics = verifier.scan_overclaim(corpus)

    assert "overclaim_detected" in diagnostic_ids(diagnostics)
    assert summary["status"] == "overclaim_detected"
    assert summary["hits"] >= 1
    assert any(phrase.strip().splitlines()[0][:20] in (getattr(d, "text", "") + getattr(d, "message", ""))
               or getattr(d, "line", 0) == 1 for d in diagnostics)


@pytest.mark.parametrize(
    "phrase",
    [
        "no R035/R037/R038 validation",          # boundary negation (noun) — critical
        "R035/R037/R038 validation gate",         # noun, no verb
        "R035/R037/R038 must not be validated",   # negated verb, non-adjacent
        "did not validate R035",                  # negation guard
        "without validating R035",                # negation guard
        "R035",                                    # bare token only
        "R035/R037/R038",                          # bare tokens only
        "validation of R035/R037/R038",            # noun
    ],
)
def test_scan_overclaim_does_not_false_positive(tmp_path: Path, phrase: str) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(tmp_path, {"ok.md": phrase + "\n"})

    summary, diagnostics = verifier.scan_overclaim(corpus)

    assert diagnostics == [], f"unexpected overclaim for phrase: {phrase!r}"
    assert summary["status"] == "clean"


def test_scan_overclaim_reports_line_number(tmp_path: Path) -> None:
    verifier = load_verifier()
    path = tmp_path / "over.md"
    path.write_text("line one\nline two\nvalidated R035 here\n", encoding="utf-8")

    _, diagnostics = verifier.scan_overclaim((path,))

    assert diagnostics
    assert diagnostics[0].line == 3


def test_scan_overclaim_missing_file_is_silent(tmp_path: Path) -> None:
    verifier = load_verifier()

    summary, diagnostics = verifier.scan_overclaim((tmp_path / "nope.md",))

    assert diagnostics == []
    assert summary["status"] == "clean"


# --------------------------------------------------------------------------
# check_boundary_markers
# --------------------------------------------------------------------------


def test_check_boundary_markers_all_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(
        tmp_path,
        {
            "a.md": "Boundary: no R035/R037/R038 validation. R047 honored.",
            "b.md": "This is CLI-install-only; D084 Stage 3 next.",
        },
    )

    all_present, diagnostics = verifier.check_boundary_markers(corpus)

    assert diagnostics == []
    assert all_present is True


def test_check_boundary_markers_cli_install_only_accepts_underscore_form(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(
        tmp_path,
        {
            "a.md": "no R035/R037/R038 validation; R047; D084",
            "b.json": '{"cli_install_only": {"wont": []}}',
        },
    )

    all_present, diagnostics = verifier.check_boundary_markers(corpus)

    assert diagnostics == []
    assert all_present is True


def test_check_boundary_markers_missing_one(tmp_path: Path) -> None:
    verifier = load_verifier()
    # present: no R035/R037/R038 validation, R047, D084 ; MISSING: CLI-install-only
    corpus = _write_overclaim_corpus(
        tmp_path,
        {"a.md": "no R035/R037/R038 validation; R047 honored; D084 Stage 3"},
    )

    all_present, diagnostics = verifier.check_boundary_markers(corpus)

    ids = diagnostic_ids(diagnostics)
    assert all_present is False
    assert "boundary_markers_missing" in ids
    assert any("CLI-install-only" in d.message for d in diagnostics)


# --------------------------------------------------------------------------
# residue guard (filesystem)
# --------------------------------------------------------------------------


def test_check_main_state_residue_absent(tmp_path: Path) -> None:
    verifier = load_verifier()

    status, diagnostics = verifier.check_main_state_residue(tmp_path)

    assert diagnostics == []
    assert set(status.keys()) == {".lex", "Squad", "Raw", ".artifacts"}
    assert all(v == "absent" for v in status.values())


def test_check_main_state_residue_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    (tmp_path / "Squad").mkdir()

    status, diagnostics = verifier.check_main_state_residue(tmp_path)

    assert "main_state_residue" in diagnostic_ids(diagnostics)
    assert status["Squad"] == "present"
    assert status[".lex"] == "absent"


# --------------------------------------------------------------------------
# verify() aggregation
# --------------------------------------------------------------------------


def _green_corpus(tmp_path: Path) -> tuple[Path, ...]:
    return _write_overclaim_corpus(
        tmp_path,
        {
            "a.md": "Boundary honored: no R035/R037/R038 validation. R047 contract-phase.",
            "b.md": "CLI-install-only milestone; D084 Stage 3 single-repo .lex adoption is next.",
        },
    )


def test_verify_happy_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_all_ok_runner,
        root=residue_root,
        scan_files=corpus,
    )

    assert diagnostics == []
    assert closure_ok is True
    assert review_log["schema_version"] == "m065-s04-closure-review/v1"
    assert review_log["per_verifier_rc"] == {"s01": 0, "s02": 0, "s03": 0}
    assert review_log["overclaim_scan"] == {"status": "clean", "hits": 0, "patterns_scanned": 2}
    assert review_log["live_residue"] == {
        ".lex": "absent", "Squad": "absent", "Raw": "absent", ".artifacts": "absent"}
    assert review_log["boundary_markers_present"] is True
    assert review_log["closure_verdict"] == "stage2_closed"
    assert "timestamp" in review_log


def test_verify_prior_verifier_failure_yields_not_closed(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_failing_runner,
        root=residue_root,
        scan_files=corpus,
    )

    assert closure_ok is False
    assert "prior_verifier_failed" in diagnostic_ids(diagnostics)
    assert review_log["closure_verdict"] == "not_closed"
    assert review_log["per_verifier_rc"] == {"s01": 1, "s02": 1, "s03": 1}


def test_verify_overclaim_failure_yields_not_closed(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(
        tmp_path,
        {"over.md": "We validated R035 in Stage 2.\nno R035/R037/R038 validation boundary R047 D084 CLI-install-only"},
    )
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_all_ok_runner,
        root=residue_root,
        scan_files=corpus,
    )

    assert closure_ok is False
    assert "overclaim_detected" in diagnostic_ids(diagnostics)
    assert review_log["overclaim_scan"]["status"] == "overclaim_detected"
    assert review_log["closure_verdict"] == "not_closed"


def test_verify_residue_failure_yields_not_closed(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / ".lex").mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_all_ok_runner,
        root=residue_root,
        scan_files=corpus,
    )

    assert closure_ok is False
    assert "main_state_residue" in diagnostic_ids(diagnostics)
    assert review_log["live_residue"][".lex"] == "present"
    assert review_log["closure_verdict"] == "not_closed"


def test_verify_boundary_missing_failure_yields_not_closed(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _write_overclaim_corpus(
        tmp_path,
        {"a.md": "no R035/R037/R038 validation; R047 honored"},  # missing D084 + CLI-install-only
    )
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_all_ok_runner,
        root=residue_root,
        scan_files=corpus,
    )

    assert closure_ok is False
    assert "boundary_markers_missing" in diagnostic_ids(diagnostics)
    assert review_log["boundary_markers_present"] is False


def test_verify_skip_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / ".lex").mkdir()

    closure_ok, diagnostics, review_log = verifier.verify(
        runner=_all_ok_runner,
        root=residue_root,
        scan_files=corpus,
        check_residue=False,
    )

    assert "main_state_residue" not in diagnostic_ids(diagnostics)
    assert diagnostics == []
    assert closure_ok is True
    assert set(review_log["live_residue"].values()) == {"skipped"}


# --------------------------------------------------------------------------
# write_closure_review
# --------------------------------------------------------------------------


def test_write_closure_review_creates_dir_and_file(tmp_path: Path) -> None:
    verifier = load_verifier()
    review_log = {"schema_version": "m065-s04-closure-review/v1", "closure_verdict": "stage2_closed"}
    out = tmp_path / "nested" / "deep" / "stage2-closure-review.json"

    written = verifier.write_closure_review(review_log, out)

    assert written == out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["closure_verdict"] == "stage2_closed"
    assert data["schema_version"] == "m065-s04-closure-review/v1"


# --------------------------------------------------------------------------
# CLI main()
# --------------------------------------------------------------------------


def test_main_exits_nonzero_on_prior_verifier_failure(tmp_path: Path, monkeypatch) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()
    review_out = tmp_path / "review.json"
    monkeypatch.setattr(verifier, "OVERCLAIM_SCAN_FILES", corpus)
    monkeypatch.setattr(verifier, "_default_runner", lambda cmd, **kw: _FakeProc(2))

    rc = verifier.main(["--root", str(residue_root), "--review", str(review_out)])

    assert rc == 1


def test_main_exits_zero_clean_and_writes_log(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()
    review_out = tmp_path / "stage2-closure-review.json"
    monkeypatch.setattr(verifier, "OVERCLAIM_SCAN_FILES", corpus)
    monkeypatch.setattr(verifier, "_default_runner", lambda cmd, **kw: _FakeProc(0))

    rc = verifier.main(["--root", str(residue_root), "--review", str(review_out)])

    assert rc == 0
    captured = capsys.readouterr()
    assert "M065 S04 stage2-closure verification passed: diagnostics=0" in captured.out
    data = json.loads(review_out.read_text(encoding="utf-8"))
    assert data["overclaim_scan"]["status"] == "clean"
    assert data["closure_verdict"] == "stage2_closed"
    assert data["live_residue"][".lex"] == "absent"


def test_main_no_write_skips_log(tmp_path: Path, monkeypatch) -> None:
    verifier = load_verifier()
    corpus = _green_corpus(tmp_path)
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()
    review_out = tmp_path / "never-written.json"
    monkeypatch.setattr(verifier, "OVERCLAIM_SCAN_FILES", corpus)
    monkeypatch.setattr(verifier, "_default_runner", lambda cmd, **kw: _FakeProc(0))

    rc = verifier.main(["--root", str(residue_root), "--review", str(review_out), "--no-write"])

    assert rc == 0
    assert not review_out.exists()


# --------------------------------------------------------------------------
# real-state integration (skip when the real evidence is not present)
# --------------------------------------------------------------------------


def test_current_real_state_check_passes() -> None:
    verifier = load_verifier()
    scripts = [script for _, script in verifier.PRIOR_VERIFIER_SCRIPTS]
    if not all(p.exists() for p in scripts) or not all(p.exists() for p in verifier.OVERCLAIM_SCAN_FILES):
        pytest.skip("real M065 Stage-2 evidence anchors not present in this environment")

    closure_ok, diagnostics, review_log = verifier.verify()

    assert diagnostics == []
    assert closure_ok is True
    assert review_log["per_verifier_rc"] == {"s01": 0, "s02": 0, "s03": 0}
    assert review_log["overclaim_scan"] == {"status": "clean", "hits": 0, "patterns_scanned": 2}
    assert review_log["boundary_markers_present"] is True
    assert review_log["closure_verdict"] == "stage2_closed"
    assert all(v == "absent" for v in review_log["live_residue"].values())
