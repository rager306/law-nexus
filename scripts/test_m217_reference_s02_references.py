"""Hermetic + corpus-gated pins for the D4 reference measurement (ADR-0031 D4).

Scope: the ed-50 reference measurement `m217-reference-references.json` (D782)
derived by `scripts/m217_reference_jsonld.py`. The committed artifact is pinned
without the gitignored corpus; the re-derivation runs only when the pinned 44-FZ
corpus and its catalog are present and prints a visible ``SKIP:`` otherwise
(D780 convention). The applicability test proves a corpus without edition 50
never builds a measurement (so the fixture corpora stay exit 0, not exit 3).
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
ARTIFACT = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-references.json"
CORPUS = REPO / "consru_export" / "consru_export" / "exports" / "npa" / "law_2013-04-05_44-fz"
CATALOG = REPO / "consru_export" / "consru_export" / "catalog.sqlite"
FIXTURES = REPO / "crates" / "ln-consultant-parser" / "tests" / "fixtures" / "reference-layer"

# ed-50 oracle pinned by ADR-0031 D4 and D784.
ED50_COUNTS = {
    "candidates": 379,
    "internal": 346,
    "external_sentence": 33,
    "deep_link_candidates": 1,
    "deep_links": 0,
    "requisites": 611,
    "requisites_exact_date": 609,
    "requisites_unique": 50,
}
VALID_TIERS = {"resolved_enacting_date", "resolved_number_only", "unresolved"}


def corpus_available() -> bool:
    return CORPUS.is_dir() and CATALOG.is_file()


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_artifact_present_and_pinned() -> None:
    assert ARTIFACT.is_file(), f"missing committed artifact: {ARTIFACT}"
    doc = load_artifact()
    assert doc["schema_version"] == "m217-reference-references/v1"
    assert doc["authoritative"] is False
    assert doc["scope"] == {"act_dir": "law_2013-04-05_44-fz", "edition_no": 50}
    assert doc["counts"] == ED50_COUNTS


def test_internal_edges_reconcile_with_the_timeline_oracle() -> None:
    doc = load_artifact()
    internal = doc["edges_internal"]
    external = doc["edges_external_sentence"]
    counts = doc["counts"]
    assert len(internal) == counts["internal"] == 346
    assert len(external) == counts["external_sentence"] == 33
    assert len(internal) + len(external) == counts["candidates"] == 379
    for edges in (internal, external):
        pairs = [tuple(edge) for edge in edges]
        assert edges == sorted(edges), "edges must be sorted pairs"
        assert len(set(pairs)) == len(pairs), "edges must be unique"
        assert all(a.startswith("statya-") and b.startswith("statya-") for a, b in pairs), (
            "edge endpoints must be article ids"
        )
    assert not (set(map(tuple, internal)) & set(map(tuple, external)))
    # The internal edge set is the very set the full-corpus timeline publishes as
    # ed-50 edge_count: 346 (parse_edition's qualified edges must not drift).
    timeline = json.loads(
        (REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-timeline.json").read_text(
            encoding="utf-8"
        )
    )
    ed50 = next(e for e in timeline["editions"] if e["edition_no"] == 50)
    assert len(internal) == ed50["edge_count"] == 346


def test_requisites_pins_and_resolution_tiers() -> None:
    doc = load_artifact()
    requisites = doc["requisites"]
    counts = doc["counts"]
    assert len(requisites) == counts["requisites_unique"] == 50
    keys = [(r["type"], r["date"], r["number"]) for r in requisites]
    assert keys == sorted(keys), "unique requisites must be sorted"
    assert len(set(keys)) == len(keys), "unique requisites must be unique by (type,date,number)"
    assert {r["tier"] for r in requisites} <= VALID_TIERS
    assert all(r["number"] and r["type"] for r in requisites)
    # ADR-0031 D4 oracle: 611 occurrences of which 609 resolve to the exact
    # (enacting) catalog date; the two residuals are the act's own malformed title
    # requisite and one sub-legislative letter absent from the catalog.
    assert counts["requisites"] == 611
    assert counts["requisites_exact_date"] == 609
    unresolved = [r for r in requisites if r["tier"] == "unresolved"]
    assert {r["number"] for r in unresolved} == {"44-ФЗ(ред", "24-02-05/34911"}
    # The act-marker requisite of the slice demo resolves by exact date.
    act_law = next(r for r in requisites if r["number"] == "188-ФЗ")
    assert (act_law["type"], act_law["date"]) == ("law", "2013-07-02")
    assert act_law["tier"] == "resolved_enacting_date"
    assert act_law["resolved_path"].endswith("law_2013-07-02_188-fz_rev-unknown_5ea52dab.xml")


def test_deep_links_are_a_derived_honest_zero() -> None:
    doc = load_artifact()
    assert doc["counts"]["deep_link_candidates"] >= 1, "deep-link mechanics must be non-empty"
    assert doc["counts"]["deep_links"] == 0, "no target-act corpus is in S02 scope"
    joined = " ".join(doc["non_claims"]).lower()
    assert "deep link" in joined
    assert "provenance" in joined
    assert "honest zero" in joined


def test_artifact_validates_against_the_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = ref._schema_validate(
        load_artifact(), schema["$defs"]["references"], schema, "references"
    )
    assert errors == []


def test_schema_rejects_malformed_measurement() -> None:
    """Fail-closed schema subset: the references $def must reject bad enums,
    wrong schema version, extra properties, missing required keys and negatives."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    definition = schema["$defs"]["references"]

    def errors(doc: dict) -> list[str]:
        return ref._schema_validate(doc, definition, schema, "references")

    good = load_artifact()
    assert errors(good) == []

    bad_tier = json.loads(json.dumps(good))
    bad_tier["requisites"][0]["tier"] = "not-a-tier"
    assert errors(bad_tier)

    bad_version = json.loads(json.dumps(good))
    bad_version["schema_version"] = "m217-reference-references/v2"
    assert errors(bad_version)

    extra_property = json.loads(json.dumps(good))
    extra_property["counts"]["surprise"] = 1
    assert errors(extra_property)

    missing_key = json.loads(json.dumps(good))
    del missing_key["counts"]["deep_links"]
    assert errors(missing_key)

    negative = json.loads(json.dumps(good))
    negative["counts"]["candidates"] = -1
    assert errors(negative)


def test_rederivation_matches_committed_artifact() -> None:
    if not corpus_available():
        print("SKIP: pinned 44-FZ corpus/catalog (gitignored) is not present")
        return
    expected = ARTIFACT.read_text(encoding="utf-8")
    measurement = ref.build_references_measurement(CORPUS, str(CATALOG))
    assert ref.render_references(measurement) == expected


def test_measurement_not_applicable_without_edition_50(tmp_path: Path) -> None:
    # A fixture corpus (editions 1 and 2, no edition 50) must not build a
    # measurement — otherwise the fixture write/--check paths would exit 3.
    assert ref.measurement_applicable(FIXTURES / "basic") is False
    assert ref.measurement_applicable(FIXTURES / "other-act") is False
    assert ref.measurement_applicable(tmp_path / "missing") is False
    with pytest.raises(ref.ReviewInputError):
        ref.build_references_measurement(FIXTURES / "basic", str(tmp_path / "no.sqlite"))


def test_applicability_predicate_detects_edition_50(tmp_path: Path) -> None:
    corpus = tmp_path / "ed50-corpus"
    corpus.mkdir()
    (corpus / "edition-0049_rev-unknown_from-unknown_aaaaaaaa.xml").write_text(
        "<x/>", encoding="utf-8"
    )
    assert ref.measurement_applicable(corpus) is False
    (corpus / "edition-0050_rev-unknown_from-unknown_bbbbbbbb.xml").write_text(
        "<x/>", encoding="utf-8"
    )
    assert ref.measurement_applicable(corpus) is True
