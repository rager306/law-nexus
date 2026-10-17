"""Hermetic + corpus-gated pins for the D5 contents ladder (ADR-0031 D5, D783).

Scope: the ed-50 pageindex measurement `m217-reference-pageindex.json` (D782)
derived by `scripts/m217_reference_jsonld.py`. The committed artifact is pinned
without the gitignored corpus, and the four D5 invariants are *recomputed from
`nodes` independently of the derivation* so the pins cannot be satisfied by a
ladder the module never validated. The re-derivation runs only when the pinned
44-FZ corpus is present and prints a visible ``SKIP:`` otherwise (D780
convention). The synthetic ladder tests pin the exact scoring rule of each
level (including the D783 block fallback) without the corpus.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import m217_reference_jsonld as ref  # noqa: E402

SCHEMA = REPO / "scripts" / "m217_reference.schema.json"
ARTIFACT = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-pageindex.json"
DIGESTS = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-digests.jsonl"
CORPUS = REPO / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
FIXTURES = REPO / "crates" / "ln-consultant-parser" / "tests" / "fixtures" / "reference-layer"

# ed-50 oracle pinned by ADR-0031 D5 (D783 explains the 669 blocks).
ED50_COUNTS = {
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
KINDS = ("section", "chapter", "paragraph", "statya", "part", "punkt", "subpunkt", "block")


def corpus_available() -> bool:
    return CORPUS.is_dir()


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def ladder(paras: list[str]) -> dict:
    digests, _spans, _full_text, _amend = ref.article_chunks(paras)
    return ref.build_pageindex(paras, digests, "synthetic-act", 50)


def test_artifact_present_and_pinned() -> None:
    assert ARTIFACT.is_file(), f"missing committed artifact: {ARTIFACT}"
    doc = load_artifact()
    assert doc["schema_version"] == "m217-reference-pageindex/v1"
    assert doc["authoritative"] is False
    assert doc["scope"] == {"act_dir": "law_2013-04-05_44-fz", "edition_no": 50}
    assert doc["counts"] == ED50_COUNTS
    assert {node["kind"] for node in doc["nodes"]} <= set(KINDS)


def test_invariant_char_conservation_from_nodes() -> None:
    """(a) Σ node chars == the non-empty paragraph characters, recomputed from
    `nodes` alone; char_end - char_start is the node's own character span."""
    doc = load_artifact()
    nodes = doc["nodes"]
    assert sum(node["chars"] for node in nodes) == doc["counts"]["chars"] == 848535
    for node in nodes:
        assert node["chars"] == node["char_end"] - node["char_start"], node["id"]
        assert node["char_start"] < node["char_end"] or node["chars"] == 0


def test_invariant_single_assignment_from_nodes() -> None:
    """(b) every non-empty paragraph belongs to exactly one node: the p_start
    values are strictly increasing (no paragraph is claimed twice) and each node
    owns exactly its one paragraph."""
    nodes = load_artifact()["nodes"]
    starts = [node["p_start"] for node in nodes]
    assert starts == sorted(starts), "nodes must be in document order"
    assert len(set(starts)) == len(starts), "a paragraph must not be claimed twice"
    for node in nodes:
        assert node["p_start"] == node["p_end"], node["id"]
        assert node["p_start"] >= 0


def test_invariant_no_article_outside_the_ladder() -> None:
    """(c) the ladder articles are exactly the digest spine of the same edition —
    cross-checked against the committed digests artifact, not against the ladder."""
    doc = load_artifact()
    rows = [json.loads(line) for line in DIGESTS.read_text(encoding="utf-8").splitlines()[1:]]
    digest_articles = {row["article"] for row in rows if row["edition_no"] == 50}
    ladder_articles = {
        node["id"].rsplit("/", 1)[-1] for node in doc["nodes"] if node["kind"] == "statya"
    }
    assert len(digest_articles) == doc["counts"]["articles"] == 141
    assert ladder_articles == digest_articles


def test_invariant_id_uniqueness_and_tree_shape() -> None:
    """(d) path ids never collide, each id ends in its own `kind-label`, and every
    parent reference resolves to an ancestor of a strictly lower level."""
    nodes = load_artifact()["nodes"]
    ids = [node["id"] for node in nodes]
    assert len(ids) == len(set(ids)) == 3003
    by_id = {node["id"]: node for node in nodes}
    for node in nodes:
        assert node["id"].rsplit("/", 1)[-1] == f"{node['kind']}-{node['label']}", node["id"]
        parent = node["parent"]
        if parent is None:
            assert node["id"] == f"{node['kind']}-{node['label']}", node["id"]
        else:
            assert parent in by_id, f"{node['id']}: dangling parent {parent}"
            assert by_id[parent]["level"] < node["level"], node["id"]
            assert node["id"] == f"{parent}/{node['kind']}-{node['label']}", node["id"]
    assert {node["kind"] for node in nodes} == set(KINDS) - {"section"}
    assert all(node["level"] <= 7 for node in nodes)


def test_counts_partition_the_paragraphs() -> None:
    """The seven level counts sum to total_nodes: every non-empty paragraph is
    exactly one node, so the ladder is a partition with no unnamed remainder."""
    counts = load_artifact()["counts"]
    parts = [
        counts[key]
        for key in (
            "sections",
            "chapters",
            "paragraphs",
            "articles",
            "parts",
            "punkts",
            "subpoints",
            "blocks",
        )
    ]
    assert sum(parts) == counts["total_nodes"] == 3003


def test_artifact_validates_against_the_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = ref._schema_validate(
        load_artifact(), schema["$defs"]["pageindex"], schema, "pageindex"
    )
    assert errors == []


def test_schema_rejects_malformed_pageindex() -> None:
    """Fail-closed schema subset: the pageindex $def must reject a bad kind enum,
    a level beyond the seven-level ladder, extra properties, a missing required
    key and negative counts."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    definition = schema["$defs"]["pageindex"]

    def errors(doc: dict) -> list[str]:
        return ref._schema_validate(doc, definition, schema, "pageindex")

    good = load_artifact()
    assert errors(good) == []

    bad_kind = json.loads(json.dumps(good))
    bad_kind["nodes"][0]["kind"] = "not-a-kind"
    assert errors(bad_kind)

    bad_level = json.loads(json.dumps(good))
    bad_level["nodes"][0]["level"] = 8
    assert errors(bad_level)

    bad_parent = json.loads(json.dumps(good))
    bad_parent["nodes"][0]["parent"] = 7
    assert errors(bad_parent)

    extra_property = json.loads(json.dumps(good))
    extra_property["counts"]["surprise"] = 1
    assert errors(extra_property)

    missing_key = json.loads(json.dumps(good))
    del missing_key["counts"]["max_depth"]
    assert errors(missing_key)

    negative = json.loads(json.dumps(good))
    negative["counts"]["blocks"] = -1
    assert errors(negative)


def test_invariants_fail_closed_when_violated() -> None:
    """The four invariants are *executed* by the derivation: a crafted ladder that
    violates any of them must raise ReviewInputError (exit 3), never publish."""
    paras = ["Глава 1. Т", "Статья 1. П", "1. Часть", "1) пункт"]
    document = ladder(paras)
    digests, _spans, _full_text, _amend = ref.article_chunks(paras)
    nodes = document["nodes"]

    broken = json.loads(json.dumps(nodes))
    broken[1]["id"] = broken[0]["id"]  # duplicate path id
    with pytest.raises(ref.ReviewInputError):
        ref.check_pageindex_invariants(paras, digests, broken)

    broken = json.loads(json.dumps(nodes))
    broken[0]["chars"] += 1  # char conservation broken
    with pytest.raises(ref.ReviewInputError):
        ref.check_pageindex_invariants(paras, digests, broken)

    with pytest.raises(ref.ReviewInputError):
        ref.check_pageindex_invariants(paras, digests, nodes[:-1])  # a paragraph unassigned

    with pytest.raises(ref.ReviewInputError):
        ref.check_pageindex_invariants(paras, dict(digests, **{"statya-99": "x"}), nodes)


def test_block_rule_is_the_corpus_wide_fallback() -> None:
    """D783: level 7 is *every* remaining non-empty paragraph — preamble, body
    filler and appendix alike — which is what lifts the block count above the
    article-scoped 633 without a magic constant."""
    paras = [
        "Преамбула акта",  # block-0, before the first article
        "Раздел I. Общие",
        "Глава 1. Название",
        "§ 1. Что-то",
        "Статья 1. Предмет",
        "Текст статьи без номера",  # block-5, inside the article
        "1. Часть первая",
        "1) пункт",
        "а) подпункт",
        "2) пункт",
        "Глава 2. Вторая",
        "Статья 2. Ещё",
        "1. Часть",
        "хвост приложения",  # block-13, appendix
    ]
    document = ladder(paras)
    assert document["counts"] == {
        "total_nodes": 14,
        "sections": 1,
        "chapters": 2,
        "paragraphs": 1,
        "articles": 2,
        "parts": 2,
        "punkts": 2,
        "subpoints": 1,
        "blocks": 3,
        "max_depth": 7,
        "chars": sum(len(text) for text in paras),
    }
    shape = {node["id"]: (node["level"], node["kind"]) for node in document["nodes"]}
    assert shape["block-0"] == (7, "block")
    assert shape["section-I"] == (1, "section")
    assert shape["section-I/chapter-1"] == (2, "chapter")
    assert shape["section-I/paragraph-1"] == (2, "paragraph")
    assert shape["section-I/paragraph-1/statya-1"] == (3, "statya")
    assert shape["section-I/paragraph-1/statya-1/block-5"] == (7, "block")
    assert shape["section-I/paragraph-1/statya-1/part-1"] == (4, "part")
    assert shape["section-I/paragraph-1/statya-1/part-1/punkt-1"] == (5, "punkt")
    assert shape["section-I/paragraph-1/statya-1/part-1/punkt-1/subpunkt-а"] == (6, "subpunkt")
    assert shape["section-I/paragraph-1/statya-1/part-1/punkt-2"] == (5, "punkt")
    assert shape["section-I/chapter-2/statya-2/part-1/block-13"] == (7, "block")


def test_dotted_paragraph_labels_keep_ids_unique() -> None:
    """§ 3. and § 3.1. share the level-2 slot and the same parent: the dotted
    label form is what keeps their path ids distinct (a bare `(\\d+)` label would
    collapse both to `paragraph-3` and trip the uniqueness invariant)."""
    paras = ["§ 3. Третья", "§ 3.1. Три один"]
    document = ladder(paras)
    ids = [node["id"] for node in document["nodes"]]
    assert ids == ["paragraph-3", "paragraph-3.1"]
    assert len(ids) == len(set(ids))
    assert document["counts"]["paragraphs"] == 2
    assert document["counts"]["total_nodes"] == 2


def test_rederivation_matches_committed_artifact() -> None:
    if not corpus_available():
        print("SKIP: pinned 44-FZ corpus (gitignored) is not present")
        return
    expected = ARTIFACT.read_text(encoding="utf-8")
    document = ref.build_pageindex_measurement(CORPUS)
    assert ref.render_pageindex(document) == expected


def test_measurement_not_applicable_without_edition_50() -> None:
    # A fixture corpus (editions 1 and 2, no edition 50) must not build a ladder —
    # otherwise the fixture write/--check paths would exit 3 instead of 0.
    assert ref.measurement_applicable(FIXTURES / "basic") is False
    assert ref.measurement_applicable(FIXTURES / "other-act") is False
    with pytest.raises(ref.ReviewInputError):
        ref.build_pageindex_measurement(FIXTURES / "basic")
