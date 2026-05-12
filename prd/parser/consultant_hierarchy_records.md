# Consultant WordML hierarchy records

This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness.

## Source

- Path: `law-source/consultant/44-FZ-2026.xml`
- SHA-256: `69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86`
- Inventory hash matches: `true`
- WordML namespace detected: `http://schemas.microsoft.com/office/word/2003/wordml`

## Counts

- Source paragraphs: `3601`
- Empty paragraphs skipped: `439`
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
- Skipped marker counts: `{}`
- Style observations: `{"0": 3268, "2": 131, "5": 3, "<none>": 199}`

## First records

- `HIER-CONS-DOCUMENT` `document` parent=`None` title="Федеральный закон от 05.04.2013 N 44-ФЗ(ред. от 28.12.2025)\"О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд\"(с изм. и доп., вступ. в силу с 01.01.2026)"
- `HIER-CONS-CHAPTER-0001` `chapter` parent=`HIER-CONS-DOCUMENT` title="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ"
- `HIER-CONS-ARTICLE-0001` `article` parent=`HIER-CONS-CHAPTER-0001` title="Статья 1. Сфера применения настоящего Федерального закона"
- `HIER-CONS-PART-0001` `part` parent=`HIER-CONS-ARTICLE-0001` title="1. Настоящий Федеральный закон регулирует отношения, направленные на обеспечение государственных и муниципальных нужд в целях повышения эффективности, результативности осуществления закупок товаров, работ, услуг, обеспечения гласности и пр…"
- `HIER-CONS-CLAUSE-0001` `clause` parent=`HIER-CONS-PART-0001` title="1) планирования закупок товаров, работ, услуг;"
- `HIER-CONS-CLAUSE-0002` `clause` parent=`HIER-CONS-PART-0001` title="2) определения поставщиков (подрядчиков, исполнителей);"
- `HIER-CONS-CLAUSE-0003` `clause` parent=`HIER-CONS-PART-0001` title="3) заключения предусмотренных настоящим Федеральным законом контрактов;"
- `HIER-CONS-CLAUSE-0004` `clause` parent=`HIER-CONS-PART-0001` title="4) особенностей исполнения контрактов;"
- `HIER-CONS-CLAUSE-0005` `clause` parent=`HIER-CONS-PART-0001` title="5) мониторинга закупок товаров, работ, услуг;"
- `HIER-CONS-CLAUSE-0006` `clause` parent=`HIER-CONS-PART-0001` title="6) аудита в сфере закупок товаров, работ, услуг;"
