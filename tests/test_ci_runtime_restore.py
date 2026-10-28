"""Pins for the vendored GSD Path runtime restore (installer and CI wiring).

The tracked vendored archive must carry the pinned 1.6.2 release content, the
standalone installer must reproduce the rehearsed restore contract (dry-run
success and digest-mismatch abort; idempotent reuse of a valid store), and the
repository-quality workflow must restore the pinned runtime before any
operational check in both jobs that run the live harness suites, publish the
governor diagnostics only on failure while keeping the exit non-zero, and
require the shipped-integrated governor report on push-to-main runs.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / ".ai/vendor/gsd-path-1.6.2.tgz"
DECLARATION_PATH = ROOT / ".gsd-path/runtime.json"
INSTALLER = ROOT / "scripts/install.py"
WORKFLOW = ROOT / ".github/workflows/repository-quality.yml"
RESTORE_STEP_NAME = "Restore pinned GSD Path runtime (vendored archive, digest-verified)"
GOVERNOR_STEP_NAME = "Governor report is honest about bootstrap mode"
DIAGNOSTICS_STEP_NAME = "Publish governor diagnostics on failure"
LIVE_SUITE_JOBS = ("migration-layer-quality", "rust-harness-quality")


def _load_installer():
    spec = importlib.util.spec_from_file_location("vendored_runtime_installer", INSTALLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


INSTALLER_MODULE = _load_installer()


def _declaration() -> dict:
    return json.loads(DECLARATION_PATH.read_text(encoding="utf-8"))


def _extract(destination: Path) -> Path:
    with tarfile.open(ARCHIVE) as tar:
        tar.extractall(destination, filter="data")
    source = destination / "gsd-path"
    assert source.is_dir()
    return source


def _run_installer(
    source: Path, project: Path, *extra: str, home: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run(
        [
            sys.executable,
            str(source / "scripts/install.py"),
            "--runtime-restore",
            "--project",
            str(project),
            "--source-root",
            str(source),
            *extra,
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )


def _job_steps(job: str) -> list[dict]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"][job]["steps"]


def _named_step(steps: list[dict], name: str) -> dict:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _run_text(step: dict) -> str:
    run = step.get("run")
    return run if isinstance(run, str) else ""


def test_archive_carries_single_top_level_release_tree() -> None:
    with tarfile.open(ARCHIVE) as tar:
        names = tar.getnames()
        packaged_file = tar.extractfile("gsd-path/package.json")
        assert packaged_file is not None
        packaged = json.load(packaged_file)
    assert {name.split("/")[0] for name in names} == {"gsd-path"}
    assert "gsd-path/scripts/install.py" in names
    assert "gsd-path/scripts/pipeline_state.py" in names
    declaration = _declaration()
    assert packaged["version"] == declaration["version"] == "1.6.2"


def test_archive_installer_matches_tracked_installer_bytes() -> None:
    with tarfile.open(ARCHIVE) as tar:
        archived = tar.extractfile("gsd-path/scripts/install.py")
        assert archived is not None
        assert archived.read() == INSTALLER.read_bytes()


def test_archive_content_digests_to_the_pinned_runtime() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        source = _extract(Path(temporary))
        _, pin = INSTALLER_MODULE.source_manifest(source)
    declaration = _declaration()
    assert pin["schema"] == declaration["schema"]
    assert pin["version"] == declaration["version"]
    assert pin["digest"] == declaration["digest"]


def test_installer_dry_run_prints_the_pinned_pair() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        source = _extract(Path(temporary))
        result = _run_installer(source, ROOT, "--dry-run")
    declaration = _declaration()
    assert result.returncode == 0, result.stderr
    assert (
        f"runtime: restore {declaration['version']} ({declaration['digest']}) (dry run)"
        in result.stdout
    )


def test_installer_aborts_on_doctored_source_with_the_recorded_pair() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        source = _extract(Path(temporary))
        victim = source / "scripts/pipeline_state.py"
        victim.write_bytes(victim.read_bytes() + b"\n# doctored\n")
        result = _run_installer(source, ROOT, "--dry-run")
    declaration = _declaration()
    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        f"error: source does not match declared runtime {declaration['version']} "
        f"({declaration['digest']}); use its matching package"
    ) in result.stderr


def test_restore_installs_a_fresh_store_then_reuses_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    declaration = _declaration()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = _extract(root)
        home = root / "home"
        first = _run_installer(source, ROOT, home=home)
        assert first.returncode == 0, first.stderr
        assert "(dry run)" not in first.stdout
        assert (
            f"runtime: restore {declaration['version']} ({declaration['digest']})" in first.stdout
        )
        store = home / ".gsd-path" / "runtimes" / declaration["digest"]
        manifest = json.loads((store / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["version"] == declaration["version"]
        before = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in store.iterdir()
        }
        second = _run_installer(source, ROOT, home=home)
        assert second.returncode == 0, second.stderr
        after = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in store.iterdir()
        }
        assert before == after
        monkeypatch.setenv("HOME", str(home))
        validated = INSTALLER_MODULE.validate_runtime(declaration)
        assert validated == store


def test_workflow_restores_the_runtime_before_any_operational_check() -> None:
    for job in LIVE_SUITE_JOBS:
        steps = _job_steps(job)
        restore_index = steps.index(_named_step(steps, RESTORE_STEP_NAME))
        restore_text = _run_text(steps[restore_index])
        assert "set -euo pipefail" in restore_text
        assert "tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C" in restore_text
        assert 'python3 "$restore_dir/gsd-path/scripts/install.py"' in restore_text
        assert "--runtime-restore" in restore_text
        assert "--project" in restore_text
        assert "--source-root" in restore_text
        assert "--dry-run" not in restore_text
        for index, step in enumerate(steps):
            text = _run_text(step)
            operational = "uv run pytest" in text or "law_nexus_harness" in text
            if index != restore_index and operational:
                assert index > restore_index, (
                    f"{job}: operational step before restore: {step.get('name')}"
                )


def test_missing_archive_fails_the_job_loudly_with_no_unpinned_fallback() -> None:
    for job in LIVE_SUITE_JOBS:
        restore_text = _run_text(_named_step(_job_steps(job), RESTORE_STEP_NAME))
        assert "pinned GSD Path runtime archive is missing" in restore_text
        assert "cat .gsd-path/runtime.json" in restore_text
        assert "npx" not in restore_text and "npm" not in restore_text


def test_no_suppression_around_restore_and_governor_exits() -> None:
    for job in LIVE_SUITE_JOBS:
        for step in _job_steps(job):
            if step.get("name") not in (RESTORE_STEP_NAME, GOVERNOR_STEP_NAME):
                continue
            text = _run_text(step)
            assert "|| true" not in text, step.get("name")
            assert "continue-on-error" not in step, step.get("name")
            assert "pipefail" in text, step.get("name")


def test_governor_failure_publishes_diagnostics_and_keeps_the_exit_non_zero() -> None:
    steps = _job_steps("migration-layer-quality")
    governor_text = _run_text(_named_step(steps, GOVERNOR_STEP_NAME))
    assert "set -o pipefail" in governor_text
    assert "-m law_nexus_harness.governor | tee governor.json" in governor_text
    diagnostics = _named_step(steps, DIAGNOSTICS_STEP_NAME)
    assert diagnostics.get("if") == "failure()"
    assert str(diagnostics.get("uses", "")).startswith("actions/upload-artifact@")
    assert diagnostics["with"]["name"] == "governor-diagnostics"
    assert diagnostics["with"]["path"] == "governor.json"
    other_artifacts = [
        step
        for step in steps
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
        and step is not diagnostics
    ]
    assert other_artifacts == []


def test_push_to_main_requires_the_shipped_integrated_governor_report() -> None:
    steps = _job_steps("migration-layer-quality")
    text = _run_text(_named_step(steps, GOVERNOR_STEP_NAME))
    assert 'os.environ.get("GITHUB_REF") == "refs/heads/main"' in text
    assert '"kind=shipped-integrated;"' in text
    # The archive path moves every milestone: pin the shape, never a literal.
    assert '".project/archive/"' in text
    assert "001-001-native-workflow-acceptance" not in text
    assert 'finding.get("check_id") == "workflow-state-surface"' in text


def test_migration_checkout_supplies_the_integration_proof_inputs() -> None:
    steps = _job_steps("migration-layer-quality")
    checkout = next(
        step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout["with"]["fetch-depth"] == 0
    proof = _named_step(steps, "Prepare shipped-main integration proof inputs")
    proof_text = _run_text(proof)
    assert "set -euo pipefail" in proof_text
    assert "git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main" in proof_text
    restore_index = steps.index(_named_step(steps, RESTORE_STEP_NAME))
    assert steps.index(proof) > restore_index


def test_pinned_declaration_is_track_level_input_for_the_restore() -> None:
    declaration = _declaration()
    assert declaration["version"] == "1.6.2"
    assert declaration["digest"] == (
        "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"
    )


def test_restore_step_wiring_survives_in_the_ci_suite_list() -> None:
    migration_text = yaml.safe_dump(_job_steps("migration-layer-quality"), sort_keys=False)
    assert "tests/test_ci_runtime_restore.py" in migration_text


def test_harness_validator_rejects_a_doctored_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    declaration = _declaration()
    home = tmp_path / "home"
    store = home / ".gsd-path" / "runtimes" / declaration["digest"]
    store.mkdir(parents=True)
    (store / "pipeline_state.py").write_bytes(b"broken\n")
    monkeypatch.setenv("HOME", str(home))
    with pytest.raises(ValueError, match="unavailable or invalid"):
        INSTALLER_MODULE.validate_runtime(declaration)
