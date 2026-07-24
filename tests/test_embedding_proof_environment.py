from __future__ import annotations

import json
from pathlib import Path

import pytest

from law_nexus.adapters.embeddings.proof_environment import (
    EMBEDDING_PROOF_ENVIRONMENT_NON_CLAIMS,
    huggingface_cache_roots,
    import_name_for_requirement,
    model_cache_name,
    normalized_path,
    probe_package_availability,
    requirement_package_name,
    unique_paths,
    write_json_log,
)


def test_non_claims_exclude_quality_authority_and_raw_vectors() -> None:
    joined = " ".join(EMBEDDING_PROOF_ENVIRONMENT_NON_CLAIMS)

    assert "managed GigaChat" in joined
    assert "retrieval quality" in joined
    assert "legal correctness" in joined
    assert "FalkorDB vector-index production readiness" in joined
    assert "raw vectors" in joined


def test_normalized_path_prefers_gsd_root_when_requested(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    gsd = root / ".gsd"
    artifact = gsd / "milestones" / "M001" / "proof.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")

    assert (
        normalized_path(artifact, root=root, prefer_gsd_root=True)
        == ".gsd/milestones/M001/proof.json"
    )
    assert normalized_path(artifact, root=root) == ".gsd/milestones/M001/proof.json"


def test_unique_paths_expands_and_deduplicates_without_sorting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    paths = unique_paths([Path("~/cache"), Path("~/cache"), Path("/tmp/other")])

    assert paths == (home / "cache", Path("/tmp/other"))


def test_huggingface_cache_roots_supports_s09_and_s10_shapes(tmp_path: Path) -> None:
    env = {
        "HUGGINGFACE_HUB_CACHE": str(tmp_path / "hub-cache"),
        "HF_HOME": str(tmp_path / "hf-home"),
        "TRANSFORMERS_CACHE": str(tmp_path / "transformers"),
    }

    s09_roots = huggingface_cache_roots(env)
    s10_roots = huggingface_cache_roots(env, include_transformers_cache=True)

    assert Path(env["HUGGINGFACE_HUB_CACHE"]) in s09_roots
    assert Path(env["HF_HOME"]) / "hub" in s09_roots
    assert Path(env["TRANSFORMERS_CACHE"]) not in s09_roots
    assert Path(env["TRANSFORMERS_CACHE"]) in s10_roots


def test_requirement_import_mapping_and_package_probe() -> None:
    assert (
        requirement_package_name("sentence-transformers>=2; python_version>'3.10'")
        == "sentence-transformers"
    )
    assert (
        import_name_for_requirement(
            "sentence-transformers>=2",
            {"sentence-transformers": "sentence_transformers"},
        )
        == "sentence_transformers"
    )

    probe = probe_package_availability("definitely-law-nexus-missing-package>=1")

    assert probe.requirement == "definitely-law-nexus-missing-package>=1"
    assert probe.distribution == "definitely-law-nexus-missing-package"
    assert probe.status == "absent"
    assert probe.to_json()["package"] == "definitely-law-nexus-missing-package>=1"


def test_model_cache_name_and_safe_json_log(tmp_path: Path) -> None:
    assert model_cache_name("deepvk/USER-bge-m3") == "models--deepvk--USER-bge-m3"

    path = write_json_log(tmp_path, "deepvk/USER-bge-m3", {"status": "blocked"})
    assert path.name == "deepvk__USER-bge-m3.log"
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "blocked"

    with pytest.raises(ValueError, match="forbidden term"):
        write_json_log(tmp_path, "secret", {"token": "Bearer abc"}, forbidden_terms=("Bearer ",))
