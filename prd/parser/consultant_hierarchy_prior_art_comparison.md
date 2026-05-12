# Consultant hierarchy prior-art comparison

This report compares deterministic Consultant hierarchy records to normalized law-parser prior-art expectations. It is non-authoritative and does not claim legal correctness, parser completeness, amendment effect, or authoritative legal interpretation.

## Overall status

- Overall status: `needs-review`
- Blocked checks: `0`
- Needs-review checks: `1`
- Classification counts: `{"accepted": 4, "needs-review": 1, "pass": 6}`

## Source anchors

- `prd/parser/consultant_hierarchy_records.jsonl` exists=`true` sha256=`b8c5f810c96da71a3f6517bb88aa93133d07949e0f538f25ecf9b0591e92e708` size=`4175013`
- `prd/parser/consultant_prior_art_expectations.json` exists=`true` sha256=`31955d8bc6d7ae30d769aeb09cebbcf51a4d0811d6839b34f014c0a0fb1e82b0` size=`13537`

## Checks

### COUNT-CHAPTER — `pass`

- Classification: `major-count`
- Rule IDs: `STRUCT-002`
- Expected: `8`
- Observed: `8`
- Rationale: Major chapter/article counts must match prior-art structure safeguards exactly.
- Evidence anchors:
  - `HIER-CONS-CHAPTER-0001` level=`chapter` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`246b161464b9c9919d4a40b45d04936426fb3c437d4cca2c906f024d0d2801e6` excerpt="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ"
  - `HIER-CONS-CHAPTER-0008` level=`chapter` marker=`8` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`48f9df0efb6d9a96fb0371f06b81ebcac78a519c22afc42a5e0797f33be0eb93` excerpt="Глава 8. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ"

### COUNT-ARTICLE — `pass`

- Classification: `major-count`
- Rule IDs: `STRUCT-006`
- Expected: `94`
- Observed: `94`
- Rationale: Major chapter/article counts must match prior-art structure safeguards exactly.
- Evidence anchors:
  - `HIER-CONS-ARTICLE-0001` level=`article` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`82d0072d6346a9cfd9cf81dbeca76dfbd21851a1970f5abdd24fdd031d12ff57` excerpt="Статья 1. Сфера применения настоящего Федерального закона"
  - `HIER-CONS-ARTICLE-0094` level=`article` marker=`114` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`de2f0e842f499444d6a1337996d596b3983cd128c8a6a02452d615e7f42ef631` excerpt="Статья 114. Порядок вступления в силу настоящего Федерального закона"

### COUNT-PART — `accepted`

- Classification: `granular-count`
- Rule IDs: `STRUCT-004`
- Expected: `668`
- Observed: `793`
- Rationale: Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL.
- Evidence anchors:
  - `HIER-CONS-PART-0001` level=`part` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`29a4e4203d89deda196f30928c350197ec50571f7a922f9c1d0fd1f7add4b4d2` excerpt="1. Настоящий Федеральный закон регулирует отношения, направленные на обеспечение государственных и муниципальных нужд в целях повышения эффективности, результативности осуществлен…"
  - `HIER-CONS-PART-0793` level=`part` marker=`4` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`a8be4bef5e2747e8013de01595eb7905f642af8d63c170cf780f32d991d90f40` excerpt="4. Утратил силу. - Федеральный закон от 31.12.2014 N 498-ФЗ."

### COUNT-CLAUSE — `accepted`

- Classification: `granular-count`
- Rule IDs: `STRUCT-004`
- Expected: `912`
- Observed: `997`
- Rationale: Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL.
- Evidence anchors:
  - `HIER-CONS-CLAUSE-0001` level=`clause` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`48c1a3625d2c7ebae40edfadd29c138726076fd671dab5dce0f7aea12c1526c5` excerpt="1) планирования закупок товаров, работ, услуг;"
  - `HIER-CONS-CLAUSE-0997` level=`clause` marker=`31` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`9e64ceeb2440a433face7b11bdb1b677d545e077a7eb88a973a5c13c70d7ee65` excerpt="31) статью 7 Федерального закона от 30 декабря 2012 года N 318-ФЗ \"О внесении изменений в Градостроительный кодекс Российской Федерации и отдельные законодательные акты Российской…"

### COUNT-SUBCLAUSE — `accepted`

- Classification: `granular-count`
- Rule IDs: `STRUCT-004`
- Expected: `272`
- Observed: `283`
- Rationale: Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL.
- Evidence anchors:
  - `HIER-CONS-SUBCLAUSE-0001` level=`subclause` marker=`а` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`16f1d509bc4f643c4676b9215fd71084d404baa88a9f0163fc4e2ddd1850c201` excerpt="а) требования к технологическим и лингвистическим средствам, обеспечивающим сбор, обработку, хранение и использование информации, содержащейся в указанной системе;"
  - `HIER-CONS-SUBCLAUSE-0283` level=`subclause` marker=`в` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`93e3f1c8ca4fe398b467694fbce8b53c4aea80df2be035e0df7012446172e998` excerpt="в) при выполнении работ по строительству, реконструкции и (или) капитальному ремонту объекта капитального строительства в целях увеличения сроков исполнения контракта в случаях, п…"

### COUNT-SECTION — `accepted`

- Classification: `granular-count`
- Rule IDs: `STRUCT-005`
- Expected: `0`
- Observed: `9`
- Rationale: Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL.
- Evidence anchors:
  - `HIER-CONS-SECTION-0001` level=`section` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`0f0dfcddb2da59f6459d1f3efb2a7772257789c71524306f53c23b631844e176` excerpt="§ 1. Общие положения"
  - `HIER-CONS-SECTION-0009` level=`section` marker=`7` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`5696dcfe8a2c3f01320f56ca3cc95767ff011143f03dfbbe414c35b29fe527e1` excerpt="§ 7. Исполнение, изменение, расторжение контракта"

### ORDER-CHAPTER-ARTICLE-COUNTS — `pass`

- Classification: `order-and-parentage`
- Rule IDs: `STRUCT-003, STRUCT-006`
- Expected: `{"1": 15, "2": 8, "3": 47, "4": 2, "5": 6, "6": 3, "7": 10, "8": 3}`
- Observed: `{"1": 15, "2": 8, "3": 47, "4": 2, "5": 6, "6": 3, "7": 10, "8": 3}`
- Rationale: Articles must map to the same chapter-count distribution even when sections are present.
- Evidence anchors:
  - `HIER-CONS-ARTICLE-0001` level=`article` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`82d0072d6346a9cfd9cf81dbeca76dfbd21851a1970f5abdd24fdd031d12ff57` excerpt="Статья 1. Сфера применения настоящего Федерального закона"
  - `HIER-CONS-ARTICLE-0094` level=`article` marker=`114` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`de2f0e842f499444d6a1337996d596b3983cd128c8a6a02452d615e7f42ef631` excerpt="Статья 114. Порядок вступления в силу настоящего Федерального закона"

### ORDER-FIRST-LAST-ARTICLES — `pass`

- Classification: `order-and-boundary-samples`
- Rule IDs: `STRUCT-001, STRUCT-003`
- Expected: `{"first": ["1", "2", "3", "4", "5"], "last": ["111.3", "111.4", "112", "113", "114"]}`
- Observed: `{"first": ["1", "2", "3", "4", "5"], "last": ["111.3", "111.4", "112", "113", "114"]}`
- Rationale: First/last article marker order is the bounded sample for full order drift.
- Evidence anchors:
  - `HIER-CONS-ARTICLE-0001` level=`article` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`82d0072d6346a9cfd9cf81dbeca76dfbd21851a1970f5abdd24fdd031d12ff57` excerpt="Статья 1. Сфера применения настоящего Федерального закона"
  - `HIER-CONS-ARTICLE-0094` level=`article` marker=`114` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`de2f0e842f499444d6a1337996d596b3983cd128c8a6a02452d615e7f42ef631` excerpt="Статья 114. Порядок вступления в силу настоящего Федерального закона"

### STRUCT-PARENTS-AND-ORDER — `pass`

- Classification: `structural-rules`
- Rule IDs: `STRUCT-003, STRUCT-004, STRUCT-005, STRUCT-006`
- Expected: `{"duplicate_id_count": 0, "missing_parent_count": 0, "non_monotonic_order_count": 0}`
- Observed: `{"duplicate_id_count": 0, "missing_parent_count": 0, "non_monotonic_order_count": 0}`
- Rationale: Comparable structural rules require non-orphaned hierarchy records, deterministic IDs, and monotonic source order.
- Evidence anchors:
  - `HIER-CONS-ARTICLE-0001` level=`article` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`82d0072d6346a9cfd9cf81dbeca76dfbd21851a1970f5abdd24fdd031d12ff57` excerpt="Статья 1. Сфера применения настоящего Федерального закона"

### INVALIDITY-MARKER-SAMPLES — `needs-review`

- Classification: `advisory-invalidity-marker`
- Rule IDs: `SEM-009`
- Expected: `{"article": 11, "clause": 17, "part": 41, "subclause": 1}`
- Observed: `{"article": 10, "clause": 19, "part": 40, "subclause": 1}`
- Rationale: Invalidity wording is compared as advisory marker evidence only; it does not determine amendment legal effect.
- Evidence anchors:
  - `HIER-CONS-PART-0002` level=`part` marker=`2` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`7aba756862a9d67bfb0e2a039897c2b091c691a6f7c2bb26d524ef513684e40a` excerpt="2. Настоящий Федеральный закон не применяется к отношениям, связанным с:"
  - `HIER-CONS-CLAUSE-0015` level=`clause` marker=`8` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`7a60b67b509aff5dc8f0f8f28f2f5903d31551bbb3fd1d3f3e5798208e0494c3` excerpt="8) не применяется с 31 июля 2018 года. - Федеральный закон от 03.07.2016 N 266-ФЗ; утратил силу. - Федеральный закон от 08.08.2024 N 318-ФЗ;"
  - `HIER-CONS-PART-0012` level=`part` marker=`2` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`573ed029615741051e59ee424cf698c05793bddae47580a3f84efdf849187be9` excerpt="2. Утратил силу с 1 января 2022 года. - Федеральный закон от 02.07.2021 N 360-ФЗ."
  - `HIER-CONS-CLAUSE-0051` level=`clause` marker=`4` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`fdb381a5b873938052e3c10c80f7e5e4293d0a557b39dcc4a163e33771690766` excerpt="4) утратил силу с 1 июля 2018 года. - Федеральный закон от 31.12.2017 N 504-ФЗ."
  - `HIER-CONS-CLAUSE-0052` level=`clause` marker=`1` source_sha=`69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` excerpt_sha=`8c1235f79cfd256ab42ec93ecfece0b9145ff9c7c0845d78d98b49244972c18a` excerpt="1) утратил силу с 1 октября 2019 года. - Федеральный закон от 01.05.2019 N 71-ФЗ;"

### INPUT-VALIDATION — `pass`

- Classification: `freshness-and-schema`
- Rule IDs: `STRUCT-001, STRUCT-002, STRUCT-003, STRUCT-004, STRUCT-005, STRUCT-006`
- Expected: `{"parse_diagnostic_count": 0}`
- Observed: `{"parse_diagnostic_count": 0, "samples": []}`
- Rationale: Comparison fails closed on malformed hierarchy JSONL records.
- Evidence anchors:
  - None

## Diagnostics

- Fatal errors: `0`
- Artifact freshness: `null`
