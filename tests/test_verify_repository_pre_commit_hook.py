from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-repository-pre-commit-hook.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_repository_pre_commit_hook", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path, hook: str) -> Path:
    path = tmp_path
    hook_path = path / ".git/hooks/pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text(hook, encoding="utf-8")
    hook_path.chmod(0o755)
    (path / ".lex").mkdir()
    (path / ".lex/repo.yml").write_text("kit: old\n", encoding="utf-8")
    transition = path / "prd/migration/decommission/pre-commit-hook-transition.json"
    transition.parent.mkdir(parents=True)
    module = load_module()
    transition.write_text(
        json.dumps(
            {
                "new_hook": {
                    "sha256": module.sha256_bytes(hook_path.read_bytes()),
                    "contains_git_lex": False,
                },
                "external_repository_mutated": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_current_hook_is_standard_and_matches_transition_record() -> None:
    module = load_module()
    payload = module.verify(ROOT)
    assert payload["status"] == "pass", payload
    assert payload["hook"]["owner"] == "pre-commit"
    assert payload["hook"]["contains_git_lex"] is False


def test_git_lex_hook_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(tmp_path, "#!/bin/sh\ngit-lex hook pre-commit\n")
    payload = module.verify(root)
    assert payload["status"] == "fail"
    assert "git_lex_invocation_present" in payload["errors"]


def test_legacy_hook_is_rejected_even_when_active_wrapper_is_clean(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(tmp_path, "#!/bin/sh\n# pre-commit generated\nexit 0\n")
    legacy = root / ".git/hooks/pre-commit.legacy"
    legacy.write_text("#!/bin/sh\ngit-lex hook pre-commit\n", encoding="utf-8")
    legacy.chmod(0o755)
    payload = module.verify(root)
    assert payload["status"] == "fail"
    assert payload["hook"]["legacy_hook_present"] is True
    assert "legacy_hook_present" in payload["errors"]


def test_standard_hook_execution_preserves_lex(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(tmp_path, "#!/bin/sh\n# pre-commit generated\nexit 0\n")
    payload = module.verify(root, execute=True)
    assert payload["status"] == "pass", payload
    assert payload["execution"]["lex_unchanged"] is True
    assert payload["execution"]["exit_code"] == 0


def test_mutating_hook_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(
        tmp_path,
        "#!/bin/sh\n# pre-commit generated\nprintf changed > .lex/repo.yml\nexit 0\n",
    )
    payload = module.verify(root, execute=True)
    assert payload["status"] == "fail"
    assert payload["execution"]["lex_unchanged"] is False
    assert "lex_mutated" in payload["errors"]


def test_nonzero_hook_is_visible(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(tmp_path, "#!/bin/sh\n# pre-commit generated\nexit 7\n")
    payload = module.verify(root, execute=True)
    assert payload["status"] == "fail"
    assert payload["execution"]["exit_code"] == 7
    assert "hook_failed" in payload["errors"]


def test_hook_sha_drift_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    root = make_repo(tmp_path, "#!/bin/sh\n# pre-commit generated\nexit 0\n")
    hook = root / ".git/hooks/pre-commit"
    hook.write_text(hook.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
    os.chmod(hook, 0o755)
    payload = module.verify(root)
    assert "hook_sha256_drift" in payload["errors"]
