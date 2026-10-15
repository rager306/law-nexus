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
EXIT_SCHEMA = 5

TIMELINE_ARTIFACT = OUT_DIR / "m217-reference-timeline.json"
DIGESTS_ARTIFACT = OUT_DIR / "m217-reference-digests.jsonl"
NAMED_GRAPHS_ARTIFACT = OUT_DIR / "m217-reference-named-graphs.json"
TIMELINE_SCHEMA_V2 = "m217-reference-timeline/v2"
DIGESTS_SCHEMA = "m217-reference-digests/v1"
NAMED_GRAPHS_SCHEMA = "m217-reference-named-graphs/v1"
NORMALIZATION_PROFILE = {
    "id": "m217-norm/v1",
    "rules": [
        "nbsp_to_space",
        "strip_paragraph_text",
        "skip_empty_paragraphs",
        "article_digest_progressive_sha12_pipe",
        "join_parts_newline",
    ],
}
NON_AUTHORITY = (
    "Non-authoritative reference projection",
    "Does not validate M224 pins or promote requirements",
    "Does not close review findings or lifecycle state",
    "Digest identity is not text CTV resolution",
)


@dataclass(frozen=True, slots=True)
class EditionDigest:
    source_sha256: str
    edition_no: int
    raw_day: str
    applied_day: str
    clamped: bool
    article_count: int
    raw_headings: int
    parse_loss: int
    break_from_previous: bool
    removed_from_previous: int
    part_count: int
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


@dataclass(frozen=True, slots=True)
class ArticleSpan:
    p_start: int
    p_end: int


def parse_edition(
    path: Path,
) -> tuple[dict[str, str], list[tuple[str, str, str]], int, int, dict[str, ArticleSpan]]:
    """Return (digests, qualified edges, raw headings, part count, article spans)."""
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
    spans: dict[str, ArticleSpan] = {}
    full_text: dict[str, list[str]] = collections.defaultdict(list)
    cur_art: str | None = None
    for idx, text in enumerate(paras):
        m = RE_ART.match(text)
        if m:
            cur_art = f"statya-{m.group(1)}"
            body = m.group(2).strip()
            digests[cur_art] = sha12(f"H:{body}")
            spans[cur_art] = ArticleSpan(idx, idx)
            if body:
                full_text[cur_art].append(body)
            continue
        if cur_art and text:
            full_text[cur_art].append(text)
            digests[cur_art] = sha12(digests[cur_art] + "|" + text)
            spans[cur_art] = ArticleSpan(spans[cur_art].p_start, idx)
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
    part_count = sum(len(chunks) for chunks in full_text.values())
    return (
        digests,
        [(a, b) for a in sorted(edges) for b in sorted(edges[a])],
        raw_headings,
        part_count,
        spans,
    )


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
    spans_by_ed: dict[int, dict[str, ArticleSpan]] = {}
    shas_by_ed: dict[int, str] = {}
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
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        digests, edges, raw_headings, part_count, spans = parse_edition(path)
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
                source_sha256,
                ed_no,
                raw_day,
                applied,
                clamped,
                len(digests),
                raw_headings,
                raw_headings - len(digests),
                break_from_previous,
                removed_count,
                part_count,
                len(edges),
            )
        )
        digests_by_ed[ed_no] = digests
        spans_by_ed[ed_no] = spans
        shas_by_ed[ed_no] = source_sha256
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
    named_graphs = build_named_graphs(
        sample_article, editions, digests_by_ed, spans_by_ed, shas_by_ed
    )
    return editions, ctv, nonmono, digests_by_ed, spans_by_ed, shas_by_ed, named_graphs


def glob_files(corpus_dir: Path) -> list[Path]:
    return sorted(corpus_dir.glob("edition-*.xml"))


RE_EDNO = re.compile(r"edition-(\d+)")


def article_sort_key(a: str) -> tuple[int, ...]:
    return tuple(int(p) for p in a.split("-")[1].split("."))


def build_named_graphs(
    sample_article: str,
    editions: list[EditionDigest],
    digests_by_ed: dict[int, dict[str, str]],
    spans_by_ed: dict[int, dict[str, ArticleSpan]],
    shas_by_ed: dict[int, str],
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


def edition_layer_document(path: Path, edition_no: int, day: str) -> bytes:
    """Full-text JSON-LD layer for one edition (on-demand projection; not committed)."""
    ctx = {
        "cc": "https://law-nexus.local/vocab/cc#",
        "eli": "http://data.europa.eu/eli/",
        "ex": "https://law-nexus.local/vocab/ex#",
        "heading": "ex:heading",
        "text": "ex:text",
        "part_no": "ex:partNo",
        "effect_day": {"@id": "ex:effectDay", "@type": "xsd:date"},
        "has_part": {"@id": "ex:hasPart", "@type": "@id"},
        "refs": {"@id": "ex:refs", "@type": "@id", "@container": "@set"},
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }
    re_art = re.compile(r"^Статья (\d+(?:\.\d+)?)\.?\s*(.*)")
    re_part = re.compile(r"^(\d+)\.\s")
    paras = []
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == W + "p":
            text = "".join(x.text or "" for x in el.iter(W + "t")).replace("\xa0", " ").strip()
            paras.append(text)
            el.clear()
    nodes: dict[str, dict[str, object]] = {}
    cur = None
    for text in paras:
        m = re_art.match(text)
        if m:
            cur = f"cc:44-fz:statya-{m.group(1)}"
            nodes.setdefault(
                cur,
                {
                    "@id": cur,
                    "@type": "cc:ComponentConcept",
                    "heading": m.group(2).strip(),
                    "has_part": [],
                    "refs": [],
                },
            )
            continue
        if cur and text:
            pm = re_part.match(text)
            nodes[cur]["has_part"].append(
                {
                    "@id": f"ex:p/{edition_no}/{cur}/{pm.group(1) if pm else 'c'}",
                    "part_no": pm.group(1) if pm else "cont",
                    "text": text,
                }
            )
    doc = {
        "@context": ctx,
        "@id": f"eli:expression/44-fz/ed-{edition_no:04d}",
        "effect_day": day,
        "@graph": list(nodes.values()),
    }
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1).encode()


def measure_g_layer(corpus_dir: Path, editions: list[EditionDigest]) -> dict[str, object]:
    """Measured G-layer bytes on the densest edition + linear projections."""
    measured_ed = max(editions, key=lambda e: (e.part_count, e.edition_no))
    path = next(
        p
        for p in sorted((corpus_dir).glob("edition-*.xml"))
        if int(RE_EDNO.search(p.name).group(1)) == measured_ed.edition_no
    )
    day = measured_ed.applied_day
    blob = edition_layer_document(path, measured_ed.edition_no, day)
    per_part = len(blob) / measured_ed.part_count
    act_parts = sum(e.part_count for e in editions)
    con = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True)
    try:
        corpus_editions = con.execute("select count(*) from editions").fetchone()[0]
    finally:
        con.close()
    act_projection = round(act_parts * per_part + len(editions) * 400)
    corpus_projection = round(act_projection / len(editions) * corpus_editions)
    return {
        "methodology": (
            "bytes measured on the densest edition, scaled linearly by part counts; "
            "corpus projection is coarse (one-act average over all catalog editions)"
        ),
        "measured_edition_no": measured_ed.edition_no,
        "measured_jsonld_bytes": len(blob),
        "measured_parts": measured_ed.part_count,
        "bytes_per_part": round(per_part, 2),
        "act_text_inline_projection_bytes": act_projection,
        "corpus_editions_in_catalog": corpus_editions,
        "corpus_text_inline_projection_bytes": corpus_projection,
    }


def render(
    editions: list[EditionDigest],
    ctv: list[CtvEvent],
    nonmono: list[dict[str, object]],
    g_volume: dict[str, object],
) -> str:
    return (
        json.dumps(
            {
                "schema_version": TIMELINE_SCHEMA_V2,
                "authoritative": False,
                "normalization_profile": NORMALIZATION_PROFILE,
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
                "g_layer_volume": g_volume,
                "editions": [
                    {
                        "edition_no": e.edition_no,
                        "source_sha256": e.source_sha256,
                        "raw_day": e.raw_day,
                        "applied_day": e.applied_day,
                        "clamped": e.clamped,
                        "article_count": e.article_count,
                        "raw_headings": e.raw_headings,
                        "parse_loss": e.parse_loss,
                        "break_from_previous": e.break_from_previous,
                        "removed_from_previous": e.removed_from_previous,
                        "part_count": e.part_count,
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


def render_digests(
    editions: list[EditionDigest],
    digests_by_ed: dict[int, dict[str, str]],
    spans_by_ed: dict[int, dict[str, ArticleSpan]],
    shas_by_ed: dict[int, str],
) -> str:
    out = [
        canonical_json(
            {
                "record_kind": "header",
                "schema_version": DIGESTS_SCHEMA,
                "normalization_profile": NORMALIZATION_PROFILE,
                "non_claims": list(NON_AUTHORITY),
            }
        )
    ]
    for e in editions:
        for aid in sorted(digests_by_ed[e.edition_no], key=article_sort_key):
            span = spans_by_ed[e.edition_no][aid]
            out.append(
                canonical_json(
                    {
                        "record_kind": "art_digest",
                        "schema_version": DIGESTS_SCHEMA,
                        "edition_no": e.edition_no,
                        "article": aid,
                        "digest": digests_by_ed[e.edition_no][aid],
                        "source": {
                            "sha256": shas_by_ed[e.edition_no],
                            "p_start": span.p_start,
                            "p_end": span.p_end,
                        },
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


SCHEMA_FILE = Path(__file__).resolve().parent / "m217_reference.schema.json"


def _schema_validate(instance: object, schema: dict, root: dict, path: str) -> list[str]:
    """Minimal Draft-2020-12 subset: type/required/properties/additionalProperties/
    items/enum/const/pattern/minItems/minimum/$ref. Honest non-claim: subset only."""
    errors: list[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        target = root
        for part in ref.lstrip("#/").split("/"):
            target = target[part]
        return _schema_validate(instance, target, root, path)
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: const != {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
    if (
        "pattern" in schema
        and isinstance(instance, str)
        and not re.search(schema["pattern"], instance)
    ):
        errors.append(f"{path}: pattern mismatch ({schema['pattern']})")
    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        errors.append(f"{path}: below minimum")
    if "minItems" in schema and isinstance(instance, list) and len(instance) < schema["minItems"]:
        errors.append(f"{path}: fewer than minItems")
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        type_map = {
            "object": dict,
            "array": list,
            "string": str,
            "boolean": bool,
            "integer": int,
            "number": (int, float),
            "null": type(None),
        }
        ok = any(
            isinstance(instance, type_map[t])
            and not (t in ("integer",) and isinstance(instance, bool))
            for t in types
        )
        if not ok:
            errors.append(f"{path}: expected type {types}")
            return errors
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}.{key}: additional property not allowed")
        for key, sub in props.items():
            if key in instance:
                errors.extend(_schema_validate(instance[key], sub, root, f"{path}.{key}"))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(_schema_validate(item, schema["items"], root, f"{path}[{i}]"))
    return errors


def validate_artifacts(
    timeline_text: str, digests_text: str, graphs_text: str, schema_path: Path
) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    timeline = json.loads(timeline_text)
    errors += _schema_validate(timeline, schema["$defs"]["timeline"], schema, "timeline")
    dlines = digests_text.splitlines()
    errors += _schema_validate(
        json.loads(dlines[0]), schema["$defs"]["digests_header"], schema, "digests[header]"
    )
    for i, line in enumerate(dlines[1:]):
        errors += _schema_validate(
            json.loads(line), schema["$defs"]["digests_record"], schema, f"digests[{i + 1}]"
        )
    graphs = json.loads(graphs_text)
    errors += _schema_validate(graphs, schema["$defs"]["named_graphs"], schema, "named_graphs")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus-dir", default=CORPUS_DIR)
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument(
        "--check", action="store_true", help="byte-compare re-derived artifacts instead of writing"
    )
    parser.add_argument(
        "--g-layer",
        type=int,
        metavar="EDITION_NO",
        default=None,
        help="emit the full-text JSON-LD layer for one edition to --out",
    )
    parser.add_argument("--out", default=None, help="output path for --g-layer mode")
    args = parser.parse_args(argv)

    corpus = Path(args.corpus_dir)
    if args.g_layer is not None:
        if not args.out:
            print("--g-layer requires --out", file=sys.stderr)
            return EXIT_ARGV
        files = sorted(glob_files(corpus))
        target = next(
            (p for p in files if int(RE_EDNO.search(p.name).group(1)) == args.g_layer), None
        )
        if target is None:
            print(f"edition {args.g_layer} not found under {corpus}", file=sys.stderr)
            return EXIT_INPUT
        m_from = RE_FROM.search(target.name)
        m_rev = RE_REV.search(target.name)
        day = (m_from or m_rev).group(1) if (m_from or m_rev) else "9999-12-31"
        Path(args.out).write_bytes(edition_layer_document(target, args.g_layer, day))
        print(f"wrote {args.out} ({Path(args.out).stat().st_size} bytes)")
        return EXIT_OK
    corpus = Path(args.corpus_dir)
    if not corpus.is_dir() or not Path(args.catalog).exists():
        print(f"unreadable inputs: corpus={corpus} catalog={args.catalog}", file=sys.stderr)
        return EXIT_INPUT
    try:
        editions, ctv, nonmono, digests_by_ed, spans_by_ed, shas_by_ed, named = derive(
            corpus, args.catalog
        )
    except ReviewInputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT

    g_volume = measure_g_layer(corpus, editions)
    digests_body = render_digests(editions, digests_by_ed, spans_by_ed, shas_by_ed)
    g_volume["digest_timeline_bytes_alternative"] = len(digests_body.encode())
    timeline = render(editions, ctv, nonmono, g_volume)
    graphs = render_named_graphs(named)
    artifacts = (
        (TIMELINE_ARTIFACT, timeline),
        (DIGESTS_ARTIFACT, digests_body),
        (NAMED_GRAPHS_ARTIFACT, graphs),
    )
    schema_path = Path(__file__).resolve().parent / "m217_reference.schema.json"
    violations = validate_artifacts(timeline, digests_body, graphs, schema_path)
    if violations:
        for line in violations[:10]:
            print(f"schema violation: {line}", file=sys.stderr)
        return EXIT_SCHEMA
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
