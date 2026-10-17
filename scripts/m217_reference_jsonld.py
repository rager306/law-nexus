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
  m217-reference-amend-provenance.json  schema m217-reference-amend-provenance/v1
  m217-reference-references.json      schema m217-reference-references/v1
                                      ed-50 measurement (D4, D782); written and
                                      --check-ed only when the corpus carries
                                      edition 50, otherwise explicitly not
                                      applicable
  m217-reference-pageindex.json       schema m217-reference-pageindex/v1
                                      ed-50 contents ladder (D5, D782) under the
                                      same applicability gate as the references
                                      artifact

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
from collections.abc import Iterator
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
RE_AMEND_MARK = re.compile(r"\(в ред\.[^)]*?от\s+(\d{2}\.\d{2}\.\d{4})\s+N\s*([^\s)]+)")
RE_REF = re.compile(r"стать(?:ё|е|ей|и|ю|я)?\s+(\d{1,3})", re.I)
RE_EXT = re.compile(r"Федерального закона|закона|Кодекса|ТК РФ|ГК РФ|законе", re.I)
RE_SENT = re.compile(r"(?<=[.;])\s+")
# ADR-0031 D4 external requisite rules: each names the (type, DD.MM.YYYY, number)
# family it qualifies, so the counts are reproducible from a named rule instead
# of an anonymous magic constant.
# - law: any «Федеральный закон…»/«закон…» form followed by «от <date> N <number>».
# - sub-legislative acts: постановление / приказ / распоряжение / письмо, with an
#   optional issuing body (Government/Minfn/FNS of Russia) before the date.
# Bare code shorthands (ТК РФ, ГК РФ, …) carry neither date nor number, so they are
# outside the D4 «type+date+number» requisite rule.
RE_REQ_LAW = re.compile(
    r"(?:Федеральн\w+ закон\w+|закон\w*)\s+от\s+(\d{2}\.\d{2}\.\d{4})\s+N\s*([^\s,;)]+)",
    re.I,
)
RE_REQ_PPA = re.compile(
    r"(Постановлени\w+|Приказ\w*|Распоряжени\w+|Письмо)\s+([^)]{0,60}?"
    r"Правительств\w+ РФ|[^)]{0,60}?Минфина России|[^)]{0,60}?ФНС России)?\s*от\s+"
    r"(\d{2}\.\d{2}\.\d{4})\s+N\s*([^\s,;)]+)",
    re.I,
)
# ADR-0031 D5 contents ladder. Seven levels over the recognized heading
# paragraphs: 1 section, 2 chapter/paragraph(§) (one slot, `kind` discriminates),
# 3 article, 4 part, 5 punkt, 6 subpoint, 7 paragraph-block. Levels 4 and 6 use
# the dotted/general number form (`^§\s*(\d+)` would collapse § 3. and § 3.1. into
# one path id and break the uniqueness invariant). Level 7 is the D783 fallback:
# *every* remaining non-empty paragraph — preamble and appendix included — which
# is what makes the corpus-wide block count 669, not the article-scoped 633.
PAGEINDEX_BLOCK_LEVEL = 7
RE_SECTION = re.compile(r"^Раздел\s*([IVXLCXХ\d]+)?")
RE_PARA = re.compile(r"^§\s*(\d+(?:\.\d+)*)")
RE_PART_DOTTED = re.compile(r"^(\d+(?:\.\d+)*)\.\s")
RE_PUNKT = re.compile(r"^(\d+)\)\s")
RE_SUBPUNKT = re.compile(r"^([а-яё])\)\s")

EXIT_OK = 0
EXIT_ARGV = 2
EXIT_INPUT = 3
EXIT_DRIFT = 6
EXIT_SCHEMA = 5

TIMELINE_ARTIFACT = OUT_DIR / "m217-reference-timeline.json"
DIGESTS_ARTIFACT = OUT_DIR / "m217-reference-digests.jsonl"
NAMED_GRAPHS_ARTIFACT = OUT_DIR / "m217-reference-named-graphs.json"
AMEND_ARTIFACT = OUT_DIR / "m217-reference-amend-provenance.json"
TIMELINE_SCHEMA_V2 = "m217-reference-timeline/v2"
DIGESTS_SCHEMA = "m217-reference-digests/v1"
NAMED_GRAPHS_SCHEMA = "m217-reference-named-graphs/v1"
AMEND_SCHEMA = "m217-reference-amend-provenance/v1"
REFS_SCHEMA = "m217-reference-references/v1"
PAGEINDEX_SCHEMA = "m217-reference-pageindex/v1"
# ed-50-scoped measurement (D782): the D4/D5 decisions are measured on edition 50,
# so their artifacts are only derivable from a corpus that carries that edition.
MEASUREMENT_EDITION = 50
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
REFS_NON_CLAIMS = (
    "Deep-link mechanics are proven by non-empty candidates; a resolved deep link "
    "needs the target act's corpus and the edition in force at the citing act's "
    "applied day (ADR-0031 D4, never the enacting-date edition alone), which is "
    "outside this measurement's scope — the zero deep_links is a derived honest "
    "zero, not a silent skip",
    "Amendment-fact sentences and own-edition markers resolve to amendment "
    "provenance (D3), never to deep links (ADR-0031 D4)",
    "Requisite resolution identifies the citing act's changing act; it does not "
    "interpret amendment semantics",
    "Reference and requisite scope is the article body text; the article heading "
    "line is structural metadata (its digest already carries the H: prefix), so a "
    "requisite appearing only on a heading line is not counted",
)
PAGEINDEX_NON_CLAIMS = (
    "The ladder is a structural contents projection of one edition: a node is a "
    "recognized heading paragraph and every remaining non-empty paragraph is a "
    "level-7 paragraph-block (D783, corpus-wide — preamble and appendix paragraphs "
    "included); the ladder is not a text CTV or a semantic segmentation",
    "A node owns exactly one paragraph, so chars is that paragraph's character count "
    "and the nodes partition the non-empty paragraphs; char conservation is over "
    "all nodes, not over leaves",
    "max_depth is the deepest ladder level present (the ladder defines seven levels: "
    "section, chapter/paragraph(§), article, part, punkt, subpoint, paragraph-block), "
    "not the longest ancestor chain",
    "Numbering keeps its dotted form in the label (§ 3. vs § 3.1.) so path ids stay "
    "unique; empty paragraphs stay out of the ladder and add no chars",
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


def scan_paragraphs(path: Path) -> list[str]:
    """WordML 2003 paragraphs in document order under the pinned normalization
    (NBSP to space, strip; empty paragraphs stay as empty strings)."""
    paras: list[str] = []
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == W + "p":
            text = "".join(x.text or "" for x in el.iter(W + "t")).replace("\xa0", " ").strip()
            paras.append(text)
            el.clear()
    return paras


def article_chunks(
    paras: list[str],
) -> tuple[
    dict[str, str], dict[str, ArticleSpan], dict[str, list[str]], list[tuple[str, str, str]]
]:
    """Single article-scoped marking shared by the timeline and the D4 measurement.

    Returns (digests, spans, full_text, amend): the progressive sha12 per article,
    the paragraph span per article, the ordered chunks per article, and the
    amendment markers as (article|act, ISO date, number).
    """
    digests: dict[str, str] = {}
    spans: dict[str, ArticleSpan] = {}
    full_text: dict[str, list[str]] = collections.defaultdict(list)
    amend: list[tuple[str, str, str]] = []
    cur_art: str | None = None
    for idx, text in enumerate(paras):
        m_am = RE_AMEND_MARK.search(text)
        if m_am:
            art = cur_art if cur_art else "act"
            iso = f"{m_am.group(1)[6:10]}-{m_am.group(1)[3:5]}-{m_am.group(1)[0:2]}"
            num = m_am.group(2).rstrip(").,")
            entry = (art, iso, num)
            if entry not in amend:
                amend.append(entry)
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
    return digests, spans, full_text, amend


def parse_edition(
    path: Path,
) -> tuple[dict[str, str], list[tuple[str, str, str]], int, int, dict[str, ArticleSpan]]:
    """Return (digests, qualified edges, raw headings, part count, article spans)."""
    paras = scan_paragraphs(path)
    raw_headings = sum(1 for text in paras if RE_ART.match(text))
    digests, spans, full_text, amend = article_chunks(paras)
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
        amend,
    )


def load_catalog_days(con: sqlite3.Connection, act_dir: str) -> dict[str, str]:
    """Catalog days for the act directory actually in use. The filter used to be
    hardcoded to law_2013-04-05_44-fz, which bound the reference layer to a
    single act."""
    rows = con.execute(
        "select relative_path, document_date from editions where relative_path like ?",
        (f"%/npa/{act_dir}/%",),
    ).fetchall()
    return {rel: doc_date for rel, doc_date in rows}


def corpus_prefix(corpus_dir: Path) -> str:
    """Corpus root relative to the repository root, e.g. consru_export/consru_export.
    Mirrors the Rust port so both implementations report the same resolved_path."""
    repo_root = Path(__file__).resolve().parent.parent
    try:
        rel = corpus_dir.resolve().relative_to(repo_root)
    except ValueError:
        rel = corpus_dir
    text = rel.as_posix()
    head, sep, _ = text.partition("/exports/")
    return head if sep else ""


def edition_number_of(name: str) -> int:
    match = RE_EDNO.search(name)
    if match is None:
        raise ReviewInputError(f"edition file name has no numeric edition number: {name}")
    return int(match.group(1))


def derive(
    corpus_dir: Path, catalog: str
) -> tuple[
    list[EditionDigest],
    list[CtvEvent],
    list[dict[str, object]],
    dict[str, dict[int, str]],
    list[dict[str, object]],
]:
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    act_dir = corpus_dir.name
    cat_days = load_catalog_days(con, act_dir)
    amend_prefix = corpus_prefix(corpus_dir)
    files = sorted(glob_files(corpus_dir), key=lambda p: edition_number_of(p.name))
    if not files:
        raise ReviewInputError("no edition files under corpus dir")
    numbers = [edition_number_of(p.name) for p in files]
    if len(set(numbers)) != len(numbers):
        raise ReviewInputError(f"duplicate edition number in corpus dir {corpus_dir}")
    editions: list[EditionDigest] = []
    digests_by_ed: dict[int, dict[str, str]] = {}
    spans_by_ed: dict[int, dict[str, ArticleSpan]] = {}
    shas_by_ed: dict[int, str] = {}
    amend_rows: list[dict[str, object]] = []
    amend_cache: dict[tuple[str, str], tuple[str, str | None]] = {}
    edges_by_ed: dict[int, list[tuple[str, str]]] = {}
    prev_day: str | None = None
    prev_digests: dict[str, str] | None = None
    for path in files:
        ed_no = edition_number_of(path.name)
        m_from = RE_FROM.search(path.name)
        m_rev = RE_REV.search(path.name)
        if m_from:
            raw_day = m_from.group(1)
        elif m_rev:
            raw_day = m_rev.group(1)
        else:
            rel = "exports/npa/" + act_dir + "/" + path.name
            raw_day = cat_days.get(rel) or "9999-12-31"
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        digests, edges, raw_headings, part_count, spans, amend = parse_edition(path)
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
        for art, iso, num in amend:
            key = (iso, num)
            if key not in amend_cache:
                amend_cache[key] = resolve_amend(con, iso, num, amend_prefix)
            tier, rel = amend_cache[key]
            amend_rows.append(
                {
                    "edition_no": ed_no,
                    "article": art,
                    "date": iso,
                    "number": num,
                    "tier": tier,
                    **({"resolved_path": rel} if rel else {}),
                }
            )
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
    con.close()
    return (
        editions,
        ctv,
        nonmono,
        digests_by_ed,
        spans_by_ed,
        shas_by_ed,
        amend_rows,
        named_graphs,
    )


def glob_files(corpus_dir: Path) -> list[Path]:
    return sorted(corpus_dir.glob("edition-*.xml"))


RE_EDNO = re.compile(r"edition-(\d+)")


def resolve_amend(
    con: sqlite3.Connection, iso_date: str, number: str, prefix: str
) -> tuple[str, str | None]:
    """Amendment provenance: identify the changing act; enacting-date match is
    identification, corpus path is informational (not a deep-link target).
    con: one shared read-only connection (opened once per derive).
    prefix: corpus root, so the reported path is the act's, not 44-FZ's."""
    rows = con.execute(
        "select relative_path, document_date from editions where number like ? limit 60",
        (f"%{number}%",),
    ).fetchall()
    if rows:
        exact = [r for r in rows if r[1] == iso_date]
        rel = exact[0][0] if exact else rows[0][0]
        tier = "resolved_enacting_date" if exact else "resolved_number_only"
        return tier, f"{prefix}/{rel}" if prefix else rel
    return "unresolved", None


PAIR = tuple[str, str]


def iter_sentences(full_text: dict[str, list[str]]) -> Iterator[tuple[str, str]]:
    """(article, sentence) stream — the single sentence-scope definition shared by
    D4 classification, requisite measurement and deep-link candidates (the same
    RE_SENT split parse_edition uses)."""
    for aid, chunks in full_text.items():
        for chunk in chunks:
            for sent in RE_SENT.split(chunk):
                yield aid, sent


def article_body(full_text: dict[str, list[str]]) -> dict[str, list[str]]:
    """Chunks after the article heading line — the D4 measurement scope.

    The heading line is structural metadata (its text is already carried as the
    `H:` digest prefix), so the ADR-0031 D4 reference/requisite measurement is
    over the article body text. This is the scope the committed ed-50 oracle
    pins (379/346/33 candidates, 611/609 exact-date requisites); including the
    heading line would add three ed-50 heading-only requisite mentions.
    """
    return {aid: chunks[1:] for aid, chunks in full_text.items()}


def iso_from_dotted(value: str) -> str:
    """DD.MM.YYYY -> YYYY-MM-DD (catalog/date comparison form)."""
    return f"{value[6:10]}-{value[3:5]}-{value[0:2]}"


def find_requisites(sentence: str) -> list[tuple[str, str, str]]:
    """External requisite occurrences (type, ISO date, number) named by family:
    'law' for any «Федеральный закон…/закон…» form; the act-type word
    (постановление, приказ, распоряжение, письмо) for sub-legislative acts."""
    found: list[tuple[str, str, str]] = []
    for m in RE_REQ_LAW.finditer(sentence):
        found.append(("law", iso_from_dotted(m.group(1)), m.group(2).rstrip(").,")))
    for m in RE_REQ_PPA.finditer(sentence):
        found.append((m.group(1).lower(), iso_from_dotted(m.group(3)), m.group(4).rstrip(").,")))
    return found


def classify_references(
    digests: dict[str, str], full_text: dict[str, list[str]]
) -> tuple[list[PAIR], list[PAIR], list[PAIR]]:
    """Sentence-scoped reference qualification (ADR-0031 D4).

    candidates: (article, target) pairs whose target exists in this edition and is
    not the article itself.
    internal: candidates whose sentence has no external-law marker, or carries
    «настоящего/прежнему».
    external_sentence: the remaining candidates (sentence names an external act).
    """
    candidates: set[PAIR] = set()
    internal: set[PAIR] = set()
    external: set[PAIR] = set()
    for aid, sent in iter_sentences(full_text):
        external_marker = (
            bool(RE_EXT.search(sent)) and "настоящего" not in sent and "прежнему" not in sent
        )
        for m in RE_REF.finditer(sent):
            ref = f"statya-{m.group(1)}"
            if ref != aid and ref in digests:
                candidates.add((aid, ref))
                (external if external_marker else internal).add((aid, ref))
    return sorted(candidates), sorted(internal), sorted(external)


def measure_requisites(
    full_text: dict[str, list[str]], con: sqlite3.Connection, prefix: str
) -> dict[str, object]:
    """External requisites (type+date+number) resolved through resolve_amend.

    Returns the occurrence total, the exact-date (enacting-date tier) count, the
    unique (type, date, number) count and the sorted unique rows."""
    occurrences: list[tuple[str, str, str]] = []
    for _aid, sent in iter_sentences(full_text):
        occurrences.extend(find_requisites(sent))
    resolved: dict[tuple[str, str, str], tuple[str, str | None]] = {}
    tiers: collections.Counter = collections.Counter()
    for key in occurrences:
        if key not in resolved:
            resolved[key] = resolve_amend(con, key[1], key[2], prefix)
        tiers[resolved[key][0]] += 1
    rows: list[dict[str, object]] = []
    for typ, iso, num in sorted(resolved):
        tier, rel = resolved[(typ, iso, num)]
        row: dict[str, object] = {"type": typ, "date": iso, "number": num, "tier": tier}
        if rel:
            row["resolved_path"] = rel
        rows.append(row)
    return {
        "total": len(occurrences),
        "exact_date": tiers["resolved_enacting_date"],
        "unique": len(resolved),
        "tiers": dict(sorted(tiers.items())),
        "rows": rows,
    }


def measure_deep_links(full_text: dict[str, list[str]]) -> tuple[list[PAIR], list[PAIR]]:
    """Deep-link mechanics (ADR-0031 D4): a candidate is a (citing article, target
    article) pair whose sentence carries an external requisite and a reference to a
    different article. A *resolved* deep link additionally needs the target act's
    corpus and the edition in force at the citing act's applied day; the S02 corpus
    carries only 44-FZ, so resolution is empty by construction — an honest derived
    zero, published as counts.deep_links and qualified in non_claims."""
    candidates: set[PAIR] = set()
    for aid, sent in iter_sentences(full_text):
        if not find_requisites(sent):
            continue
        for m in RE_REF.finditer(sent):
            target = f"statya-{m.group(1)}"
            if target != aid:
                candidates.add((aid, target))
    resolved: set[PAIR] = set()
    return sorted(candidates), sorted(resolved)


def measurement_edition_path(corpus_dir: Path, edition_no: int) -> Path | None:
    """The edition file carrying `edition_no`, if the corpus has one. This is the
    applicability predicate both main branches (write and --check) must share."""
    for path in glob_files(corpus_dir):
        try:
            if edition_number_of(path.name) == edition_no:
                return path
        except ReviewInputError:
            continue
    return None


def measurement_applicable(corpus_dir: Path) -> bool:
    """The ed-50 measurement applies only where the corpus carries edition 50
    (D782). Fixture corpora without it must stay exit 0, never exit 3."""
    return measurement_edition_path(corpus_dir, MEASUREMENT_EDITION) is not None


def build_references_measurement(
    corpus_dir: Path, catalog: str, edition_no: int = MEASUREMENT_EDITION
) -> dict[str, object]:
    """Derive the D4 reference measurement from one edition of `corpus_dir`."""
    path = measurement_edition_path(corpus_dir, edition_no)
    if path is None:
        raise ReviewInputError(f"corpus has no edition {edition_no}")
    digests, _spans, full_text, _amend = article_chunks(scan_paragraphs(path))
    body = article_body(full_text)
    candidates, internal, external = classify_references(digests, body)
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    try:
        requisites = measure_requisites(body, con, corpus_prefix(corpus_dir))
    finally:
        con.close()
    deep_candidates, deep_links = measure_deep_links(body)
    return {
        "schema_version": REFS_SCHEMA,
        "authoritative": False,
        "scope": {"act_dir": corpus_dir.name, "edition_no": edition_no},
        "non_claims": list(NON_AUTHORITY) + list(REFS_NON_CLAIMS),
        "counts": {
            "candidates": len(candidates),
            "internal": len(internal),
            "external_sentence": len(external),
            "deep_link_candidates": len(deep_candidates),
            "deep_links": len(deep_links),
            "requisites": requisites["total"],
            "requisites_exact_date": requisites["exact_date"],
            "requisites_unique": requisites["unique"],
        },
        "edges_internal": [[a, b] for a, b in internal],
        "edges_external_sentence": [[a, b] for a, b in external],
        "requisites": requisites["rows"],
    }


def render_references(measurement: dict[str, object]) -> str:
    """Canonical measurement document: ensure_ascii=False, sorted keys, one-space
    indent, trailing newline (same style as render_amend)."""
    return json.dumps(measurement, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def pageindex_level(text: str) -> tuple[int, str, str] | None:
    """(level, kind, label) of a recognized heading paragraph, else None (block).

    Level precedence is ADR-0031 D5: section, chapter/paragraph(§) (one level-2
    slot, `kind` discriminates), article, part, punkt, subpoint. A paragraph that
    matches none of them is a level-7 block (D783).
    """
    match = RE_SECTION.match(text)
    if match:
        return 1, "section", match.group(1) or "unnumbered"
    match = RE_CH.match(text)
    if match:
        return 2, "chapter", match.group(1)
    match = RE_PARA.match(text)
    if match:
        return 2, "paragraph", match.group(1)
    match = RE_ART.match(text)
    if match:
        return 3, "statya", match.group(1)
    match = RE_PART_DOTTED.match(text)
    if match:
        return 4, "part", match.group(1)
    match = RE_PUNKT.match(text)
    if match:
        return 5, "punkt", match.group(1)
    match = RE_SUBPUNKT.match(text)
    if match:
        return 6, "subpunkt", match.group(1)
    return None


def check_pageindex_invariants(
    paras: list[str], digests: dict[str, str], nodes: list[dict[str, object]]
) -> None:
    """The four ADR-0031 D5 invariants, executed on the derived ladder.

    (a) char conservation: Σ node chars == the non-empty paragraph characters;
    (b) single assignment: every non-empty paragraph is in exactly one node;
    (c) no article outside the ladder: the ladder articles are the digest spine;
    (d) id uniqueness: path ids do not collide.
    A violation is a ReviewInputError (unreadable input, exit 3) — the ladder is
    never published half-derived.
    """
    owned = [node["p_start"] for node in nodes]
    expected = [idx for idx, text in enumerate(paras) if text]
    if owned != expected or any(node["p_start"] != node["p_end"] for node in nodes):
        raise ReviewInputError(
            "pageindex invariant violated: every non-empty paragraph must belong to "
            "exactly one node"
        )
    if sum(int(node["chars"]) for node in nodes) != sum(len(text) for text in paras if text):
        raise ReviewInputError("pageindex invariant violated: char conservation")
    ladder_articles = {
        str(node["id"]).rsplit("/", 1)[-1] for node in nodes if node["kind"] == "statya"
    }
    if ladder_articles != set(digests):
        raise ReviewInputError(
            "pageindex invariant violated: the ladder must carry exactly the "
            f"{len(digests)} articles of the digest spine"
        )
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise ReviewInputError("pageindex invariant violated: duplicate path id")


def build_pageindex(
    paras: list[str], digests: dict[str, str], act_dir: str, edition_no: int
) -> dict[str, object]:
    """ADR-0031 D5 contents ladder over one edition's paragraphs.

    A new node of level L closes every open node of level >= L (the level-2 slot
    is shared by chapter and §), so the ladder is a tree whose path ids
    (`chapter-1/statya-44/part-2/punkt-3/subpunkt-а/block-2718`) cannot collide
    across articles. Every non-empty paragraph is exactly one node: a recognized
    heading at its own level, or a level-7 block (D783). Empty paragraphs stay
    out of the ladder and add no chars, and a node owns exactly that one
    paragraph, so char conservation is over all nodes.

    `digests` is the digest spine of the same paragraphs (article_chunks), used by
    the no-article-outside-the-ladder invariant; `build_pageindex` executes all
    four D5 invariants before returning.
    """
    offsets: list[int] = []
    offset = 0
    for text in paras:
        offsets.append(offset)
        offset += len(text) + 1
    nodes: list[dict[str, object]] = []
    stack: list[tuple[int, str]] = []
    for idx, text in enumerate(paras):
        if not text:
            continue
        recognized = pageindex_level(text)
        if recognized is None:
            level, kind, label = PAGEINDEX_BLOCK_LEVEL, "block", str(idx)
        else:
            level, kind, label = recognized
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else None
        node_id = f"{parent}/{kind}-{label}" if parent is not None else f"{kind}-{label}"
        nodes.append(
            {
                "id": node_id,
                "level": level,
                "kind": kind,
                "label": label,
                "parent": parent,
                "p_start": idx,
                "p_end": idx,
                "chars": len(text),
                "char_start": offsets[idx],
                "char_end": offsets[idx] + len(text),
            }
        )
        stack.append((level, node_id))
    check_pageindex_invariants(paras, digests, nodes)
    kinds = collections.Counter(node["kind"] for node in nodes)
    counts = {
        "total_nodes": len(nodes),
        "sections": kinds["section"],
        "chapters": kinds["chapter"],
        "paragraphs": kinds["paragraph"],
        "articles": kinds["statya"],
        "parts": kinds["part"],
        "punkts": kinds["punkt"],
        "subpoints": kinds["subpunkt"],
        "blocks": kinds["block"],
        # deepest ladder level present (level index), not the longest ancestor chain
        "max_depth": max((int(node["level"]) for node in nodes), default=0),
        "chars": sum(int(node["chars"]) for node in nodes),
    }
    return {
        "schema_version": PAGEINDEX_SCHEMA,
        "authoritative": False,
        "scope": {"act_dir": act_dir, "edition_no": edition_no},
        "non_claims": list(NON_AUTHORITY) + list(PAGEINDEX_NON_CLAIMS),
        "counts": counts,
        "nodes": nodes,
    }


def render_pageindex(document: dict[str, object]) -> str:
    """Canonical pageindex document: ensure_ascii=False, sorted keys, one-space
    indent, trailing newline (same style as render_references)."""
    return json.dumps(document, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def build_pageindex_measurement(
    corpus_dir: Path, edition_no: int = MEASUREMENT_EDITION
) -> dict[str, object]:
    """Derive the D5 contents ladder from one edition of `corpus_dir`."""
    path = measurement_edition_path(corpus_dir, edition_no)
    if path is None:
        raise ReviewInputError(f"corpus has no edition {edition_no}")
    paras = scan_paragraphs(path)
    digests, _spans, _full_text, _amend = article_chunks(paras)
    return build_pageindex(paras, digests, corpus_dir.name, edition_no)


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


def measure_g_layer(
    corpus_dir: Path, editions: list[EditionDigest], catalog: str
) -> dict[str, object]:
    """Measured G-layer bytes on the densest edition + linear projections."""
    measured_ed = max(editions, key=lambda e: (e.part_count, e.edition_no))
    if measured_ed.part_count == 0:
        raise ReviewInputError(
            "no article parts under corpus dir: G-layer volume is not measurable"
        )
    path = next(
        p
        for p in sorted((corpus_dir).glob("edition-*.xml"))
        if edition_number_of(p.name) == measured_ed.edition_no
    )
    day = measured_ed.applied_day
    blob = edition_layer_document(path, measured_ed.edition_no, day)
    per_part = len(blob) / measured_ed.part_count
    act_parts = sum(e.part_count for e in editions)
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
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


def render_amend(amend_rows: list[dict[str, object]]) -> str:
    tiers = collections.Counter(r["tier"] for r in amend_rows)
    laws = {(r["date"], r["number"]) for r in amend_rows if r["article"] != "act"}
    eds = {r["edition_no"] for r in amend_rows}
    return (
        json.dumps(
            {
                "schema_version": AMEND_SCHEMA,
                "authoritative": False,
                "non_claims": list(NON_AUTHORITY)
                + [
                    "Amendment provenance identifies the changing act; it does not "
                    "interpret amendment semantics (M208 territory)"
                ],
                "counts": {
                    "editions_with_markers": len(eds),
                    "markers": len(amend_rows),
                    "unique_amending_laws": len(laws),
                },
                "resolution_tiers": dict(sorted(tiers.items())),
                "markers": amend_rows,
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
    items/enum/const/pattern/minItems/minimum/maximum/$ref. Honest non-claim: subset only."""
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
    if "maximum" in schema and isinstance(instance, (int, float)) and instance > schema["maximum"]:
        errors.append(f"{path}: above maximum")
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
    timeline_text: str,
    digests_text: str,
    graphs_text: str,
    amend_text: str,
    references_text: str | None,
    pageindex_text: str | None,
    schema_path: Path,
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
    amend = json.loads(amend_text)
    errors += _schema_validate(amend, schema["$defs"]["amend_provenance"], schema, "amend")
    if references_text is not None:
        references = json.loads(references_text)
        errors += _schema_validate(references, schema["$defs"]["references"], schema, "references")
    if pageindex_text is not None:
        pageindex = json.loads(pageindex_text)
        errors += _schema_validate(pageindex, schema["$defs"]["pageindex"], schema, "pageindex")
    return errors


def artifact_paths(out_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        out_dir / "m217-reference-timeline.json",
        out_dir / "m217-reference-digests.jsonl",
        out_dir / "m217-reference-named-graphs.json",
        out_dir / "m217-reference-amend-provenance.json",
    )


def measurement_artifact_paths(out_dir: Path) -> tuple[Path, Path]:
    """ed-50-scoped measurement artifacts (ADR-0031 D782), kept separate from the
    four full-corpus artifacts in artifact_paths(): the D4 references and the D5
    contents ladder."""
    return (
        out_dir / "m217-reference-references.json",
        out_dir / "m217-reference-pageindex.json",
    )


def unreadable(reason: str) -> "ReviewInputError":
    return ReviewInputError(f"unreadable inputs: {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus-dir", default=CORPUS_DIR)
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="directory holding the reference artifacts (check compares, default writes)",
    )
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
        try:
            files = sorted(glob_files(corpus))
            target = next((p for p in files if edition_number_of(p.name) == args.g_layer), None)
        except ReviewInputError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_INPUT
        if target is None:
            print(f"edition {args.g_layer} not found under {corpus}", file=sys.stderr)
            return EXIT_INPUT
        m_from = RE_FROM.search(target.name)
        m_rev = RE_REV.search(target.name)
        day = (m_from or m_rev).group(1) if (m_from or m_rev) else "9999-12-31"
        try:
            Path(args.out).write_bytes(edition_layer_document(target, args.g_layer, day))
        except ET.ParseError as exc:
            print(unreadable(str(exc)), file=sys.stderr)
            return EXIT_INPUT
        print(f"wrote {args.out} ({Path(args.out).stat().st_size} bytes)")
        return EXIT_OK
    if not corpus.is_dir() or not Path(args.catalog).exists():
        print(f"unreadable inputs: corpus={corpus} catalog={args.catalog}", file=sys.stderr)
        return EXIT_INPUT
    try:
        editions, ctv, nonmono, digests_by_ed, spans_by_ed, shas_by_ed, amend_rows, named = derive(
            corpus, args.catalog
        )
        g_volume = measure_g_layer(corpus, editions, args.catalog)
        # D782: the D4/D5 measurements are ed-50-scoped; they are built only where
        # the corpus carries edition 50, so a fixture corpus without it stays exit 0.
        applicable = measurement_applicable(corpus)
        measurement = build_references_measurement(corpus, args.catalog) if applicable else None
        pageindex = build_pageindex_measurement(corpus) if applicable else None
    except ReviewInputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT
    except (ET.ParseError, sqlite3.Error, OSError, ValueError, KeyError, ZeroDivisionError) as exc:
        # ADR-0031 D6: unreadable input is exit 3, never a traceback.
        print(unreadable(f"{type(exc).__name__}: {exc}"), file=sys.stderr)
        return EXIT_INPUT

    out_dir = Path(args.out_dir)
    timeline_path, digests_path, graphs_path, amend_path = artifact_paths(out_dir)
    digests_body = render_digests(editions, digests_by_ed, spans_by_ed, shas_by_ed)
    g_volume["digest_timeline_bytes_alternative"] = len(digests_body.encode())
    timeline = render(editions, ctv, nonmono, g_volume)
    graphs = render_named_graphs(named)
    amend_doc = render_amend(amend_rows)
    references_doc = render_references(measurement) if measurement is not None else None
    pageindex_doc = render_pageindex(pageindex) if pageindex is not None else None
    references_path, pageindex_path = measurement_artifact_paths(out_dir)
    artifacts = (
        (timeline_path, timeline),
        (digests_path, digests_body),
        (graphs_path, graphs),
        (amend_path, amend_doc),
    )
    if references_doc is not None:
        artifacts = artifacts + ((references_path, references_doc),)
    if pageindex_doc is not None:
        artifacts = artifacts + ((pageindex_path, pageindex_doc),)
    schema_path = Path(__file__).resolve().parent / "m217_reference.schema.json"
    violations = validate_artifacts(
        timeline, digests_body, graphs, amend_doc, references_doc, pageindex_doc, schema_path
    )
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
    else:
        for path, body in artifacts:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            print(f"wrote {path} ({len(body)} bytes)")
    if measurement is not None:
        counts = measurement["counts"]
        print(
            f"measurement ed-{MEASUREMENT_EDITION}: candidates={counts['candidates']} "
            f"internal={counts['internal']} external_sentence={counts['external_sentence']} "
            f"requisites={counts['requisites']} "
            f"requisites_exact_date={counts['requisites_exact_date']} "
            f"requisites_unique={counts['requisites_unique']} "
            f"deep_link_candidates={counts['deep_link_candidates']} "
            f"deep_links={counts['deep_links']}"
        )
    if pageindex is not None:
        ladder = pageindex["counts"]
        print(
            f"pageindex ed-{MEASUREMENT_EDITION}: total_nodes={ladder['total_nodes']} "
            f"sections={ladder['sections']} chapters={ladder['chapters']} "
            f"paragraphs={ladder['paragraphs']} articles={ladder['articles']} "
            f"parts={ladder['parts']} punkts={ladder['punkts']} "
            f"subpoints={ladder['subpoints']} blocks={ladder['blocks']} "
            f"max_depth={ladder['max_depth']} chars={ladder['chars']}"
        )
    if measurement is None and pageindex is None:
        print(f"measurement not applicable: corpus has no edition {MEASUREMENT_EDITION}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
