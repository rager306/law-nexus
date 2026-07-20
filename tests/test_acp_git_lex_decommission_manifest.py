from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-acp-git-lex-decommission-manifest.py"
JSON_OUT = ROOT / "prd/migration/decommission/acp-git-lex-manifest.json"
MD_OUT = ROOT / "prd/migration/decommission/acp-git-lex-manifest.md"


def load_module():
    spec = importlib.util.spec_from_file_location("acp_git_lex_decommission_manifest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def init_repo(path: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    for relative, content in files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)


def test_current_manifest_is_deterministic_and_fresh() -> None:
    module = load_module()
    first = module.build_manifest(ROOT)
    second = module.build_manifest(ROOT)
    assert module.render_json(first) == module.render_json(second)
    assert JSON_OUT.read_text(encoding="utf-8") == module.render_json(first)
    assert MD_OUT.read_text(encoding="utf-8") == module.render_markdown(first)
    assert module.validate(first) == []


def test_manifest_has_unique_targets_and_no_product_archive_candidates() -> None:
    payload = json.loads(JSON_OUT.read_text(encoding="utf-8"))
    assert payload["duplicate_archive_targets"] == []
    assert payload["product_denylist_violations"] == []
    targets = [entry["archive_path"] for entry in payload["entries"] if entry["archive_path"]]
    assert len(targets) == len(set(targets))
    assert not any(
        entry["source_path"].startswith("src/law_nexus/") and entry["action"] == "archive"
        for entry in payload["entries"]
    )


def test_external_repository_is_explicitly_excluded() -> None:
    payload = json.loads(JSON_OUT.read_text(encoding="utf-8"))
    assert payload["external_repository"] == "/root/git-lex-kit-acp/"
    assert payload["external_repository_mutation_allowed"] is False
    assert not any(str(entry["source_path"]).startswith("/root/") for entry in payload["entries"])


def test_temp_repo_classifies_explicit_roots_and_manual_review(tmp_path: Path) -> None:
    module = load_module()
    init_repo(
        tmp_path,
        {
            ".lex/repo.yml": "kit: law-nexus\n",
            ".agents/skills/acp/SKILL.md": "ACP active skill\n",
            "src/law_nexus/domain/example.py": "# historical ACP mention requiring review\n",
            "README.md": "ordinary project readme\n",
        },
    )
    payload = module.build_manifest(tmp_path)
    by_path = {entry["source_path"]: entry for entry in payload["entries"]}
    assert by_path[".lex/repo.yml"]["classification"] == "derived_lex_state"
    assert by_path[".agents/skills/acp/SKILL.md"]["classification"] == "active_skill"
    assert by_path["src/law_nexus/domain/example.py"]["classification"] == "manual_review_reference"
    assert by_path["src/law_nexus/domain/example.py"]["archive_path"] is None
    assert "README.md" not in by_path
    assert payload["product_denylist_violations"] == []


def test_source_hash_changes_when_tracked_content_drifts(tmp_path: Path) -> None:
    module = load_module()
    init_repo(tmp_path, {".lex/repo.yml": "kit: old\n"})
    before = module.build_manifest(tmp_path)
    (tmp_path / ".lex/repo.yml").write_text("kit: changed\n", encoding="utf-8")
    after = module.build_manifest(tmp_path)
    assert before["entries"][0]["source_sha256"] != after["entries"][0]["source_sha256"]
    assert module.render_json(before) != module.render_json(after)


def test_validate_fails_closed_for_duplicate_target_and_product_violation() -> None:
    module = load_module()
    payload = {
        "duplicate_archive_targets": ["python_archive/acp_git_lex/scripts/x.py"],
        "product_denylist_violations": ["src/law_nexus/domain/x.py"],
    }
    assert module.validate(payload) == ["duplicate_archive_targets", "product_denylist_violations"]


def test_check_mode_reports_current_outputs() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "pass"
    assert payload["archive_candidate_count"] > 500
    assert payload["manual_review_count"] > 0
