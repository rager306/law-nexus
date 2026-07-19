# Consultant WordML hierarchy records

This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness.

## Source

- Path: `law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml`
- SHA-256: `c111119c6c3001b5b4fde0e35bffbe382bcb877df2bba9cd54ab0290c92c1b14`
- Inventory hash matches: `true`
- WordML namespace detected: `http://schemas.microsoft.com/office/word/2003/wordml`

## Counts

- Source paragraphs: `3585`
- Empty paragraphs skipped: `428`
- Records emitted: `2185`
- `article`: `94`
- `chapter`: `8`
- `clause`: `997`
- `document`: `1`
- `part`: `793`
- `section`: `9`
- `subclause`: `283`

## Diagnostics

- Malformed XML: `None`
- Validation errors: `0`
- Structural errors: `0`
- Rejected context markers: `0`
- Fatal errors: `0`
- Skipped marker counts: `{"exception_markers": 2, "invalidity_markers": 6, "obligation_markers": 1, "permission_markers": 19, "preambula_paragraphs": 61, "unnumbered_paragraphs_within_article": 896}`
- Style observations: `{"0": 3263, "2": 131, "5": 3, "<none>": 188}`

## First records

- `HIER-CONS-DOCUMENT` `document` parent=`None` title="Федеральный закон от 05.04.2013 N 44-ФЗ(ред. от 28.12.2025)\"О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд\"(с изм. и доп., вступ. в силу с 01.07.2026)"
- `HIER-CONS-CHAPTER-0001` `chapter` parent=`HIER-CONS-DOCUMENT` title="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ"
- `HIER-CONS-ARTICLE-0001` `article` parent=`HIER-CONS-CHAPTER-0001` title="Статья 1. Сфера применения настоящего Федерального закона"
- `HIER-CONS-PART-0001` `part` parent=`HIER-CONS-ARTICLE-0001` title="1. Настоящий Федеральный закон регулирует отношения, направленные на обеспечение государственных и муниципальных нужд в целях повышения эффективности, результативности осуществления закупок товаров, работ, услуг, обеспечения гласности и пр…"
- `HIER-CONS-CLAUSE-0001` `clause` parent=`HIER-CONS-PART-0001` title="1) планирования закупок товаров, работ, услуг;"
- `HIER-CONS-CLAUSE-0002` `clause` parent=`HIER-CONS-PART-0001` title="2) определения поставщиков (подрядчиков, исполнителей);"
- `HIER-CONS-CLAUSE-0003` `clause` parent=`HIER-CONS-PART-0001` title="3) заключения предусмотренных настоящим Федеральным законом контрактов;"
- `HIER-CONS-CLAUSE-0004` `clause` parent=`HIER-CONS-PART-0001` title="4) особенностей исполнения контрактов;"
- `HIER-CONS-CLAUSE-0005` `clause` parent=`HIER-CONS-PART-0001` title="5) мониторинга закупок товаров, работ, услуг;"
- `HIER-CONS-CLAUSE-0006` `clause` parent=`HIER-CONS-PART-0001` title="6) аудита в сфере закупок товаров, работ, услуг;"
