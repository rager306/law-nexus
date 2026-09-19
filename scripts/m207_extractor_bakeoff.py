#!/usr/bin/env python3
"""Диагностика на ОДНОМ документе: мы / Pullenti / наивный дата+N.

Pullenti — ориентация (D380/D514), не продукт, не gold, не второй кодировщик.
Не копирует SDK в crates/. Запуск:

  PYTHONPATH=/root/vendor-source/pullenti/sdk-python \\
    uv run python scripts/m207_extractor_bakeoff.py --doc npa-doc-032
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/root/vendor-source/pullenti/sdk-python")

from scripts import m207_context_graph_demo as d  # noqa: E402


def naive_date_n(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in d.OT_DATE.finditer(text)]


def pullenti_init() -> object:
    from pullenti.morph.MorphLang import MorphLang
    from pullenti.ner.ProcessorService import ProcessorService
    from pullenti.ner.date.DateAnalyzer import DateAnalyzer
    from pullenti.ner.geo.GeoAnalyzer import GeoAnalyzer
    from pullenti.ner.org.OrganizationAnalyzer import OrganizationAnalyzer
    from pullenti.ner.person.PersonAnalyzer import PersonAnalyzer
    from pullenti.ner.decree.DecreeAnalyzer import DecreeAnalyzer
    from pullenti.Sdk import Sdk

    if not ProcessorService.is_initialized():
        Sdk.initialize(MorphLang.RU)
        DateAnalyzer.initialize()
        GeoAnalyzer.initialize()
        OrganizationAnalyzer.initialize()
        PersonAnalyzer.initialize()  # иначе Decree падает на списках ФЗ
        DecreeAnalyzer.initialize()
    return ProcessorService.create_processor()


def pullenti_decrees(proc, text: str) -> list[dict[str, str]]:
    from pullenti.ner.SourceOfAnalysis import SourceOfAnalysis
    from pullenti.ner.decree.DecreeReferent import DecreeReferent
    from pullenti.ner.decree.DecreePartReferent import DecreePartReferent

    ar = proc.process(SourceOfAnalysis(text), None, None)
    out: list[dict[str, str]] = []
    for ent in ar.entities:
        if isinstance(ent, DecreeReferent):
            out.append(
                {
                    "kind": "DECREE",
                    "type": ent.typ or "",
                    "number": ent.number or "",
                    "date": ent.get_string_value(DecreeReferent.ATTR_DATE) or "",
                    "source": ent.get_string_value(DecreeReferent.ATTR_SOURCE) or "",
                    "geo": ent.get_string_value(DecreeReferent.ATTR_GEO) or "",
                    "text": str(ent),
                }
            )
        elif isinstance(ent, DecreePartReferent):
            out.append(
                {
                    "kind": "DECREEPART",
                    "type": "",
                    "number": "",
                    "date": "",
                    "source": "",
                    "geo": "",
                    "text": str(ent),
                }
            )
    return out


def key_dn(date: str, number: str) -> tuple[str, str]:
    return (date.replace(".", "-"), number.casefold())


def print_bakeoff(doc_id: str) -> int:
    g = d.load_docs(d.ROOT, doc_id)[0]
    ordered = sorted(g.blocks, key=lambda x: x.order)
    joined_nl = "\n".join(b.text for b in ordered)
    joined_space = " ".join(b.text.strip() for b in ordered)
    series_join = ""
    for chain in d.series_chains(g):
        ids = g.by_id()
        series_join = " ".join(ids[fid].text.strip() for fid in chain)
        break
    print("=" * 72)
    print(f"ДОКУМЕНТ {g.doc_id}  блоков={len(g.blocks)}  xml=…/{Path(g.source_path).name}")
    print("Pullenti = диагностика (D380), не продукт.")
    print()
    print("Текст (склейка seed-блоков, не весь XML):")
    for b in sorted(g.blocks, key=lambda x: x.order):
        print(f"  {b.fragment_id}  «{b.text.strip().replace(chr(10), ' ')[:110]}»")

    ours_a = d.collect_members(g, with_neighbor=False)
    ours_b = d.collect_members(g, with_neighbor=True)
    naive: list[tuple[str, str, str]] = []
    for b in g.blocks:
        for date, num in naive_date_n(b.text):
            naive.append((date, num, b.fragment_id))

    print()
    print("-" * 72)
    print("НАИВНЫЙ дата+N (нет TYPE вообще)")
    for date, num, fid in naive:
        print(f"  {date:<12} N {num:<18} {fid}")

    print()
    print("-" * 72)
    print("МЫ  ветка А (один w:p) / ветка Б (серия + тот же номер в документе)")
    print(
        f"  {'дата':<12} {'номер':<16} {'TYPE':<36} {'B':<20} {'граф':<16} from"
    )
    seen_ours: set[tuple[str, str, str]] = set()
    ours_unique = []
    for m in ours_b:
        key = (m.date, m.number, m.type_name or "")
        if key in seen_ours:
            continue
        seen_ours.add(key)
        ours_unique.append(m)
        print(
            f"  {m.date:<12} {m.number:<16} {(m.type_name or '—'):<36} "
            f"{m.legal_class:<20} {m.graph:<16} {m.type_from}"
        )

    print()
    print("  Pullenti init…")
    proc = pullenti_init()
    per_block: list[tuple[str, dict[str, str]]] = []
    for b in sorted(g.blocks, key=lambda x: x.order):
        for ent in pullenti_decrees(proc, b.text):
            per_block.append((b.fragment_id, ent))
    joined_ents = pullenti_decrees(proc, joined_space)
    joined_nl_ents = pullenti_decrees(proc, joined_nl)
    series_ents = pullenti_decrees(proc, series_join) if series_join else []

    print()
    print("-" * 72)
    print("PULLENTI  по каждому seed-блоку отдельно")
    if not per_block:
        print("  (пусто)")
    for fid, ent in per_block:
        print(
            f"  {fid}  {ent['kind']:<10} TYPE={ent['type']!r:28} "
            f"N={ent['number']!r:16} DATE={ent['date']!r} SRC={ent['source']!r} GEO={ent['geo']!r}"
        )

    print()
    print("-" * 72)
    print("PULLENTI  склейка блоков пробелом (ближе к Sofa, не \\n)")
    if not joined_ents:
        print("  (пусто)")
    for ent in joined_ents:
        print(
            f"  {ent['kind']:<10} TYPE={ent['type']!r:28} "
            f"N={ent['number']!r:16} DATE={ent['date']!r} SRC={ent['source']!r} GEO={ent['geo']!r}"
        )
        print(f"             {ent['text']}")
    if series_join:
        print()
        print(f"PULLENTI  только серия continues_series склеена пробелом ({len(series_ents)} сущностей)")
        print(f"  текст: «{series_join[:140]}»")
        if not series_ents:
            print("  (пусто — хвост не восстановил)")
        for ent in series_ents:
            print(
                f"  {ent['kind']:<10} TYPE={ent['type']!r:28} "
                f"N={ent['number']!r:16} DATE={ent['date']!r}"
            )

    print()
    print("=" * 72)
    print("РАСХОЖДЕНИЯ (дата+N как ключ, где есть)")
    def norm_date(value: str) -> str:
        value = (value or "").strip()
        if not value or value in {"—", "-"}:
            return ""
        if "." in value and value.count(".") == 2:
            parts = value.split(".")
            if len(parts[0]) == 4:
                y, mo, da = parts
                return f"{da}.{mo}.{y}"
            return value
        if "-" in value and value.count("-") == 2:
            y, mo, da = value.split("-")
            if len(y) == 4:
                return f"{da}.{mo}.{y}"
        return value

    ours_rows = ours_unique
    naive_keys = {(norm_date(date), num) for date, num, _ in naive}
    pul_rows = [ent for ent in joined_ents if ent["kind"] == "DECREE"]

    print(f"  {'кто':<10} {'дата':<12} {'номер':<16} TYPE")
    print("  наши:")
    for m in ours_rows:
        print(f"    мы         {m.date:<12} {m.number:<16} {m.type_name or '—'}  B={m.legal_class} graph={m.graph}")
    print("  Pullenti:")
    for ent in pul_rows:
        print(
            f"    Pullenti   {norm_date(ent['date']) or '—':<12} {(ent['number'] or '—'):<16} "
            f"{ent['type'] or '—'}  SRC={ent['source']!r} GEO={ent['geo']!r}"
        )
    print("  наивный дата+N без TYPE:")
    for date, num, fid in naive:
        print(f"    наив       {date:<12} {num:<16} {fid}")

    print()
    print("Итог для итерации:")
    print(f"  наивных дата+N: {len(naive)}")
    print(f"  наших членов Б: {len(ours_b)}  (А без соседа: {len(ours_a)})")
    print(f"  Pullenti DECREE на склейке: {sum(1 for e in joined_ents if e['kind']=='DECREE')}")
    print(f"  Pullenti DECREE по блокам:  {sum(1 for _, e in per_block if e['kind']=='DECREE')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--doc",
        action="append",
        default=None,
        help="npa-doc-032; можно несколько раз. По умолчанию 032 и 020",
    )
    args = parser.parse_args()
    docs = args.doc or [
        "npa-doc-014",  # приказ ФАНО + Положение о…
        "npa-doc-028",  # решение УФАС + Правила, утв.
        "npa-doc-032",  # письмо / ГК / положение об
        "npa-doc-020",  # короткий эллипсис 446
        "npa-doc-001",  # ложный «контрактн*»
    ]
    rc = 0
    for doc in docs:
        rc = print_bakeoff(doc) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
