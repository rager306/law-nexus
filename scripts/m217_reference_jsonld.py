#!/usr/bin/env python3
"""M217 reference prototype: XML -> JSONL digest-timeline + JSON-LD Named Graphs.

Python reference contract for the M217 bake-off (see
phases/217-kbike0-graph-vector-crash-consistency-citation/217-RESEARCH.md).
Deterministic re-derivation over the pinned 44-FZ edition corpus:

- effective day per edition: from-date, else rev-date, else catalog
  document_date (D765; rev-initial falls back to the catalog);
- non-monotonic raw days are clamped to the previous applied day and
  published as documented residuals (D767);
- CTV events are content digests diffed between consecutive editions;
- internal references are sentence-qualified (external-law markers excluded);
- Named Graphs sample: one JSON-LD named graph per edition for the sample
  article (digest identity, not decoded text).

Modes:
  (default)  derive and write artifacts, exit 0
  --check    derive and byte-compare against stored artifacts;
             exit 0 on identity, 6 on drift, 3 on unreadable inputs

Artifacts (prd/migration/rust-evidence/):
  m217-reference-timeline.json        schema m217-reference-timeline/v1
  m217-reference-digests.jsonl        schema m217-reference-digests/v1
  m217-reference-named-graphs.json    schema m217-reference-named-graphs/v1

Non-authoritative: this module is a repository-control reference, not product
runtime; it does not validate M224 pins, does not promote requirements, and
does not close findings.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz"
CATALOG = "consru_export/consru_export/catalog.sqlite"
OUT_DIR = Path("prd/migration/rust-evidence")
W = "{http://schemas.microsoft.com/office/word/2003/wordml}"
RE_CH = re.compile(r"^Глава (\d+(?:\.\d+)?)\.?\s+(.+)")
RE_ART = re.compile(r"^Статья (\d+(?:\.\d+)?)\.?\s*(.*)")
RE_FROM = re.compile(r"from-(\d{4}-\d{2}-\d{2})")
RE_REV = re.compile(r"rev-(\d{4}-\d{2}-\d{2})")
RE_PART = re.compile(r"^(\d+)\.\s")
RE_REF = re.compile(r"стать(?:ё|е|ей|и|ю|я)?\s+(\d{1,3})", re.I)
RE_EXT = re.compile(r"Федерального закона|закона|Кодекса|ТК РФ|ГК РФ|законе", re.I)
RE_SENT = re.compile(r"(?<=[.;])\s+")

EXIT_OK = 0
EXIT_ARGV = 2
EXIT_INPUT = 3
EXIT_DRIFT = 6

TIMELINE_ARTIFACT = OUT_DIR / "m217-reference-timeline.json"
DIGESTS_ARTIFACT = OUT_DIR / "m217-reference-digests.jsonl"
NAMED_GRAPHS_ARTIFACT = OUT_DIR / "m217-reference-named-graphs.json"
TIMELINE_SCHEMA_V2 = "m217-reference-timeline/v2"
DIGESTS_SCHEMA = "m217-reference-digests/v1"
NAMED_GRAPHS_SCHEMA = "m217-reference-named-graphs/v1"
NON_AUTHORITY = (
    "Non-authoritative reference projection",
    "Does not validate M224 pins or promote requirements",
    "Does not close review findings or lifecycle state",
    "Digest identity is not text CTV resolution",
)


@dataclass(frozen=True, slots=True)
class EditionDigest:
    edition_no: int
    raw_day: str
    applied_day: str
    clamped: bool
    article_count: int
    raw_headings: int
    parse_loss: int
    break_from_previous: bool
    removed_from_previous: int
    edge_count: int


@dataclass(frozen=True, slots=True)
class CtvEvent:
    article: str
    edition_no: int
    op: str


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_edition(path: Path) -> tuple[dict[str, str], list[tuple[str, str, str]], int]:
    """Return (article digest map, qualified internal edges, raw heading count)."""
    paras: list[str] = []
    raw_headings = 0
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == W + "p":
            text = "".join(x.text or "" for x in el.iter(W + "t")).replace("\xa0", " ").strip()
            if RE_ART.match(text):
                raw_headings += 1
            paras.append(text)
            el.clear()
    digests: dict[str, str] = {}
    full_text: dict[str, list[str]] = collections.defaultdict(list)
    cur_art: str | None = None
    for text in paras:
        m = RE_ART.match(text)
        if m:
            cur_art = f"statya-{m.group(1)}"
            body = m.group(2).strip()
            digests[cur_art] = sha12(f"H:{body}")
            if body:
                full_text[cur_art].append(body)
            continue
        if cur_art and text:
            full_text[cur_art].append(text)
            digests[cur_art] = sha12(digests[cur_art] + "|" + text)
    edges: dict[str, set[str]] = collections.defaultdict(set)
    for aid, chunks in full_text.items():
        for chunk in chunks:
            for sent in RE_SENT.split(chunk):
                if RE_EXT.search(sent) and "настоящего" not in sent and "прежнему" not in sent:
                    continue
                for m in RE_REF.finditer(sent):
                    ref = f"statya-{m.group(1)}"
                    if ref != aid and ref in digests:
                        edges[aid].add(ref)
    return digests, [(a, b) for a in sorted(edges) for b in sorted(edges[a])], raw_headings


def load_catalog_days(catalog: str) -> dict[str, str]:
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select relative_path, document_date from editions "
            "where relative_path like '%/npa/law_2013-04-05_44-fz/%'"
        ).fetchall()
    finally:
        con.close()
    return {rel: doc_date for rel, doc_date in rows}


def derive(
    corpus_dir: Path, catalog: str
) -> tuple[
    list[EditionDigest],
    list[CtvEvent],
    list[dict[str, object]],
    dict[str, dict[int, str]],
    list[dict[str, object]],
]:
    cat_days = load_catalog_days(catalog)
    files = sorted(
        glob_files(corpus_dir),
        key=lambda p: int(re.search(r"edition-(\d+)", p.name).group(1)),
    )
    if not files:
        raise ReviewInputError("no edition files under corpus dir")
    editions: list[EditionDigest] = []
    digests_by_ed: dict[int, dict[str, str]] = {}
    edges_by_ed: dict[int, list[tuple[str, str]]] = {}
    prev_day: str | None = None
    prev_digests: dict[str, str] | None = None
    for path in files:
        ed_no = int(RE_EDNO.search(path.name).group(1))
        m_from = RE_FROM.search(path.name)
        m_rev = RE_REV.search(path.name)
        if m_from:
            raw_day = m_from.group(1)
        elif m_rev:
            raw_day = m_rev.group(1)
        else:
            rel = "exports/npa/" + path.parts[-2] + "/" + path.name
            raw_day = cat_days.get(rel) or "9999-12-31"
        digests, edges, raw_headings = parse_edition(path)
        applied, clamped = raw_day, False
        if prev_day is not None and raw_day < prev_day:
            applied, clamped = prev_day, True
        prev_day = applied
        break_from_previous, removed_count = False, 0
        if prev_digests is not None:
            removed = set(prev_digests) - set(digests)
            break_from_previous, removed_count = bool(removed), len(removed)
        editions.append(
            EditionDigest(
                ed_no,
                raw_day,
                applied,
                clamped,
                len(digests),
                raw_headings,
                raw_headings - len(digests),
                break_from_previous,
                removed_count,
                len(edges),
            )
        )
        digests_by_ed[ed_no] = digests
        edges_by_ed[ed_no] = edges
        prev_digests = digests
    ctv: list[CtvEvent] = []
    prev: dict[str, str] | None = None
    for ed_no in sorted(digests_by_ed):
        cur = digests_by_ed[ed_no]
        if prev is not None:
            for aid in sorted(set(prev) | set(cur), key=article_sort_key):
                if aid not in prev:
                    ctv.append(CtvEvent(aid, ed_no, "created"))
                elif aid not in cur:
                    ctv.append(CtvEvent(aid, ed_no, "removed"))
                elif prev[aid] != cur[aid]:
                    ctv.append(CtvEvent(aid, ed_no, "amended"))
        prev = cur
    nonmono = [
        {"from_edition_no": e.edition_no - 1, "raw_day": e.raw_day, "applied_day": e.applied_day}
        for e in editions
        if e.clamped
    ]
    sample_article = "statya-44"
    named_graphs = build_named_graphs(sample_article, editions, digests_by_ed)
    return editions, ctv, nonmono, digests_by_ed, named_graphs


def glob_files(corpus_dir: Path) -> list[Path]:
    return sorted(corpus_dir.glob("edition-*.xml"))


RE_EDNO = re.compile(r"edition-(\d+)")


def article_sort_key(a: str) -> tuple[int, ...]:
    return tuple(int(p) for p in a.split("-")[1].split("."))


def build_named_graphs(
    sample_article: str,
    editions: list[EditionDigest],
    digests_by_ed: dict[int, dict[str, str]],
) -> list[dict[str, object]]:
    graphs = []
    for e in editions:
        digest = digests_by_ed[e.edition_no].get(sample_article)
        if digest is None:
            continue
        graphs.append(
            {
                "@id": f"eli:expression/44-fz/ed-{e.edition_no:04d}#{sample_article}",
                "digest": digest,
                "applied_day": e.applied_day,
            }
        )
    doc_graph = {
        "@id": "cc:44-fz:" + sample_article,
        "graphs": graphs,
    }
    return [{"@id": "eli:work/44-fz", "sample_article": sample_article}, doc_graph]


def render(
    editions: list[EditionDigest], ctv: list[CtvEvent], nonmono: list[dict[str, object]]
) -> str:
    return (
        json.dumps(
            {
                "schema_version": TIMELINE_SCHEMA_V2,
                "authoritative": False,
                "non_claims": list(NON_AUTHORITY)
                + [
                    "Article-count variance across editions reflects documented law history "
                    "(476-FZ purge band from edition 81), not parsing defect"
                ],
                "counts": {
                    "editions": len(editions),
                    "ctv_events": len(ctv),
                    "non_monotonic": len(nonmono),
                },
                "editions": [
                    {
                        "edition_no": e.edition_no,
                        "raw_day": e.raw_day,
                        "applied_day": e.applied_day,
                        "clamped": e.clamped,
                        "article_count": e.article_count,
                        "raw_headings": e.raw_headings,
                        "parse_loss": e.parse_loss,
                        "break_from_previous": e.break_from_previous,
                        "removed_from_previous": e.removed_from_previous,
                        "edge_count": e.edge_count,
                    }
                    for e in editions
                ],
                "ctv_events": [
                    {"article": c.article, "edition_no": c.edition_no, "op": c.op} for c in ctv
                ],
                "non_monotonic": nonmono,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=1,
        )
        + "\n"
    )


def render_digests(editions: list[EditionDigest], digests_by_ed: dict[int, dict[str, str]]) -> str:
    out = []
    for e in editions:
        for aid in sorted(digests_by_ed[e.edition_no], key=article_sort_key):
            out.append(
                canonical_json(
                    {
                        "schema_version": DIGESTS_SCHEMA,
                        "edition_no": e.edition_no,
                        "article": aid,
                        "digest": digests_by_ed[e.edition_no][aid],
                    }
                )
            )
    return "\n".join(out) + "\n"


def render_named_graphs(named: list[dict[str, object]]) -> str:
    return (
        json.dumps(
            {
                "schema_version": NAMED_GRAPHS_SCHEMA,
                "authoritative": False,
                "non_claims": list(NON_AUTHORITY),
                "graphs": named,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=1,
        )
        + "\n"
    )


class ReviewInputError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus-dir", default=CORPUS_DIR)
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument(
        "--check", action="store_true", help="byte-compare re-derived artifacts instead of writing"
    )
    args = parser.parse_args(argv)

    corpus = Path(args.corpus_dir)
    if not corpus.is_dir() or not Path(args.catalog).exists():
        print(f"unreadable inputs: corpus={corpus} catalog={args.catalog}", file=sys.stderr)
        return EXIT_INPUT
    try:
        editions, ctv, nonmono, digests_by_ed, named = derive(corpus, args.catalog)
    except ReviewInputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT

    timeline = render(editions, ctv, nonmono)
    digests = render_digests(editions, digests_by_ed)
    graphs = render_named_graphs(named)
    artifacts = (
        (TIMELINE_ARTIFACT, timeline),
        (DIGESTS_ARTIFACT, digests),
        (NAMED_GRAPHS_ARTIFACT, graphs),
    )
    if args.check:
        drift = []
        for path, body in artifacts:
            if not path.exists():
                drift.append(f"{path}: missing artifact")
                continue
            if path.read_text(encoding="utf-8") != body:
                drift.append(f"{path}: byte drift")
        if drift:
            for line in drift:
                print(f"drift: {line}", file=sys.stderr)
            return EXIT_DRIFT
        print("check=ok artifacts byte-identical")
        return EXIT_OK

    for path, body in artifacts:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path} ({len(body)} bytes)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
