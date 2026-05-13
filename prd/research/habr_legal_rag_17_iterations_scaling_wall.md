---
source: "Habr article via Jina Reader"
source_url: "https://habr.com/ru/articles/1014758/"
import_reader_url: "https://r.jina.ai/http://habr.com/ru/articles/1014758/"
title: "От 0.034 до 0.791 и обратно: Legal RAG, 17 итераций и стена масштабирования"
imported_at: "2026-05-13T05:58:02.274209+00:00"
status: "raw-research-import"
non_authoritative: true
notes: "Imported from public article reader; claims are not project-verified."
---

Title: От 0.034 до 0.791 и обратно: Legal RAG, 17 итераций и стена масштабирования

URL Source: http://habr.com/ru/articles/1014758/

Published Time: 2026-03-25T13:24:37+03:00

Markdown Content:
## От 0.034 до 0.791 и обратно: соревнование по Legal RAG, 17 итераций и стена масштабирования

Мне давно хотелось погрузиться в RAG, но повода не было. Я решил поучаствовать в [ARLC 2026](https://www.agentic-challenge.ai/) — юридическом AI-челлендже, где нужно строить RAG-пайплайн поверх корпуса судебных решений и законов DIFC – находить нужные страницы в нужных документах, извлекать ответы и давать точные ссылки на источники. Соло, с Claude Code в качестве напарника.

До этого я работал с ML, но RAG-пайплайны не строил. За 5 дней прошёл путь от первой подачи с grounding ≈ 0 до 0.791 на первом этапе. А потом вышел в финал — и pipeline, который отлично работал на 30 документах, потерял 42% на 300.

В этой статье — архитектура, конкретный код, математика F-beta, полная таблица 17 итераций с метриками и честный разбор работы с AI-ассистентом на соревновании. Код [открыт на GitHub](https://github.com/TagirRamilevich/agentic-rag-legal-challenge).

* * *

### Кто я такой

Я заканчивал направление NLP в НИУ ВШЭ. На работе я занимаюсь аналитикой (работал в Яндексе, Ozon, Альфа-Банке). Регулярно участвую в соревнованиях (топ-600 на [Kaggle](https://www.kaggle.com/tagirkhairutdinov)), но RAG до этого челленджа не строил. Еще я веду каналы про аналитику – [Тагир Анализирует](https://t.me/+WHCIExPhs202YzJi) и [Зарплатник Аналитика](https://t.me/+77FoCeO9J2tjMzgy). Сейчас активно строю свой продукт — [Карьерник](https://t.me/kariernik_bot/app?startapp=habr_arcl_25032026), Duolingo для подготовки к собеседованиям на аналитика.

* * *

### Что за челлендж

**ARLC 2026 (Arab Region Legal Challenge)** — это соревнование по Retrieval-Augmented Generation на юридических документах. Тебе дают корпус PDF-документов (судебные решения DIFC Courts, законы, указы) и набор вопросов к ним.

Задача: для каждого вопроса найти нужные страницы в нужных документах, извлечь ответ и предоставить точные ссылки на источники.

Звучит просто. Но вот нюансы.

#### Типы ответов

Это не просто «ответь текстом». Каждый вопрос имеет свой `answer_type`, и от типа зависит и стратегия ответа, и скоринг:

| Тип | Формат | Скоринг |
| --- | --- | --- |
| `number` | число (int/float) | ±1% допуск |
| `boolean` | true/false | точное совпадение |
| `name` | строка | normalized exact match |
| `date` | YYYY-MM-DD | точное совпадение |
| `names` | массив строк | Jaccard similarity |
| `free_text` | текст до 280 символов | LLM-судья, 5 критериев |

Для любого типа `null` — валидный ответ, означающий «информации нет в корпусе». Если и в gold-ответе null — получаешь 1 балл. Если только у тебя null — получаешь 0.

#### Формула скоринга

```
Total = (0.7 × S_det + 0.3 × S_asst) × G × T × F
```

Где:

*   **S_det** — точность на типизированных вопросах (number, bool, date, name, names)

*   **S_asst** — оценка LLM-судьи для free_text (5 критериев: correctness, completeness, grounding, confidence calibration, clarity)

*   **G** — grounding (F-beta, β=2.5 по page-level ссылкам)

*   **T** — telemetry factor (0.9 если телеметрия невалидна, 1.0 если ок)

*   **F** — TTFT factor (бонус/штраф за скорость)

G — это **множитель**. Если grounding = 0, весь скор = 0. Неважно, насколько идеальные ответы.

#### TTFT-бонус — бесплатные проценты

| TTFT (ms) | Множитель |
| --- | --- |
| < 1000 | 1.05 |
| < 2000 | 1.02 |
| < 3000 | 1.00 |
| > 3000 | 0.85–0.99 |

Быстрый ответ = +5% к финальному скору. Медленный — штраф до -15%. При прочих равных — это бесплатные очки.

#### Warmup vs. Финал

*   **Warmup:** 30 документов, 100 вопросов, 15 попыток подачи

*   **Финал:** 300 документов, 900 вопросов, **2 попытки**

У каждой фазы свой корпус — нельзя использовать документы из warmup в финале.

* * *

### День первый: четыре символа, которые стоили три попытки

Первая подача — v1. Скор: **0.034**.

| Det | Asst | G | T | F | Total |
| --- | --- | --- | --- | --- | --- |
| 0.857 | 0.613 | 0.050 | 0.900 | 0.960 | **0.034** |

Grounding — 0.05. Из 100 вопросов система почти ни разу не сослалась на правильные страницы. При этом Det = 0.857 — ответы-то были неплохие.

Но G — множитель. 0.857 × 0.05 ≈ ничего.

Ещё две попытки (v2, v3) с мелкими правками. 0.035. 0.036. Grounding не двигался. Я перебрал всё: может, страницы нумеруются с нуля? Может, doc_id — это не имя файла? Может, ретривал совсем мимо?

А потом я открыл submission.json и увидел:

`{  "doc_id": "abc123def456.pdf",  "page_numbers": [3, 7]}`
А в документации API:

> `doc_id` must be the PDF filename (SHA-like string)

Файл называется `abc123def456.pdf`. Имя файла — `abc123def456`. Без `.pdf`.

**Три попытки из пятнадцати ушли на четыре символа.**

v4 — одна строчка `doc_id = filename.replace('.pdf', '')`:

| Det | Asst | G | T | F | Total |
| --- | --- | --- | --- | --- | --- |
| 0.857 | 0.673 | 0.550 | 0.986 | 1.005 | **0.438** |

G: 0.05 → 0.55. Скор: 0.034 → 0.438. В 13 раз.

**Урок:** сначала валидируй формат вывода. Потом улучшай качество. Никакой retrieval, reranking или fine-tuning не спасёт, если submission не матчится с gold по формату. Это кажется очевидным, но когда ты с нуля собираешь пайплайн — голова занята архитектурой, а не тем, есть ли `.pdf` в doc_id.

* * *

### Архитектура: что и почему

К v14 (лучший скор) пайплайн выглядит так:

![Image 1: Архитектура пайплайна к v14](https://habrastorage.org/r/w1560/getpro/habr//post_images/fc6/6fc/6f6/fc66fc6f60ac4c5ce46cded4d885dd8a.png)

Архитектура пайплайна к v14

Разберём каждый компонент.

#### Ingestion: парсинг PDF

Юридические PDF бывают двух видов: цифровые (текст копируется) и сканированные (картинка). Нужно обрабатывать оба.

`def extract_pages(pdf_path, min_chars=50, ocr_dpi=300):    pages = []    doc = pdfplumber.open(pdf_path)    for i, page in enumerate(doc.pages):        text = page.extract_text() or ""        if len(text.strip()) < min_chars:            # Сканированный документ — fallback на OCR            text = ocr_page(pdf_path, i + 1, dpi=ocr_dpi)        pages.append({            "doc_id": pdf_path.stem,      # без .pdf!            "page_number": i + 1,         # 1-based            "text": text        })    return pages`
**Ключевое решение: page-level, а не чанки.** Grounding считается по `(doc_id, page_number)` — значит и индексировать нужно по страницам. Чанки (куски по 500 токенов) создают проблему маппинга обратно на страницы: чанк может пересекать границу страниц, и непонятно, на какую страницу ссылаться.

Минус page-level: страница может быть длинной (1500+ символов), и контекст для LLM раздувается. Решение — context distillation перед вызовом модели (об этом ниже).

#### Гибридный поиск: BM25 + embeddings + RRF

Чистый BM25 хорошо находит точные совпадения — номер статьи, имя судьи, номер дела. Но плохо ловит переформулировки: вопрос «What is the penalty?» не матчится с текстом «shall be liable to a fine».

Чистые embeddings наоборот — ловят семантику, но теряют точные термины.

Решение — **гибридный поиск с Reciprocal Rank Fusion:**

`def hybrid_search(query, bm25_index, embedding_index, pages, top_k=20, rrf_k=60):    # BM25 ранжирование    bm25_scores = bm25_index.get_scores(tokenize(query))    bm25_ranked = sorted(range(len(pages)), key=lambda i: -bm25_scores[i])    # Embedding ранжирование    q_emb = embed_model.encode([query[:512]], normalize_embeddings=True)    sim_scores = (embedding_index @ q_emb.T).flatten()    emb_ranked = sorted(range(len(pages)), key=lambda i: -sim_scores[i])    # RRF fusion: score(d) = Σ 1/(k + rank(d))    combined = {}    for rank, idx in enumerate(bm25_ranked[:top_k * 3]):        combined[idx] = combined.get(idx, 0) + 1.0 / (rrf_k + rank)    for rank, idx in enumerate(emb_ranked[:top_k * 3]):        combined[idx] = combined.get(idx, 0) + 1.0 / (rrf_k + rank)    # Сортировка по combined score    return sorted(combined, key=lambda i: -combined[i])[:top_k]`
RRF с k=60 — стандартная формула. Она не требует нормализации скоров (BM25 и cosine similarity имеют разные шкалы), а просто использует ранги. Страница, которая в топ-5 по обоим методам, получит высокий combined score.

**Модель для embeddings:**`all-MiniLM-L6-v2` — 22M параметров, 90MB, работает локально. Для 30 документов warmup этого хватает с запасом. Для финала (300 документов) тоже — индексация занимает ~10 секунд.

#### Document routing: comparison-вопросы

Comparison-вопросы типа «В каком из дел CFI 001/2020 и CFI 002/2021 судья был назначен раньше?» требуют контекста из двух документов. Обычный retrieval может найти страницы только из одного.

Решение — **отдельный routing-индекс**, построенный по первым двум страницам каждого документа:

`def build_doc_routing_index(pages):    case_to_doc = {}  # "CFI 010/2024" → "abc123def"    law_to_doc = {}   # "DIFC Law No. 5 of 2007" → "xyz789abc"    for p in pages:        if p["page_number"] > 2:  # Только титульные страницы            continue        # Паттерн номера дела: "CFI 010/2024", "DIFC ARB 123/2020"        for case in re.findall(r"\b([A-Z]{2,5}\s+\d{3}/\d{4})\b", p["text"]):            case_to_doc[case.upper()] = p["doc_id"]    return case_to_doc, law_to_doc`
При обнаружении comparison-вопроса (два номера дел в тексте) делаем **dual query** — отдельный BM25-запрос для каждого дела, результаты чередуем round-robin:

```
Query A (case 1): [page1_A, page3_A, page7_A, ...]
Query B (case 2): [page2_B, page5_B, page9_B, ...]
Interleaved:      [page1_A, page2_B, page3_A, page5_B, ...]
```

Зачем чередование: если все результаты case A идут первыми, а max_pages маленький (4) — case B может не попасть в контекст совсем. Чередование гарантирует представительство обоих дел.

#### Cross-encoder reranking

BM25 + embeddings дают грубую сортировку. Cross-encoder (`ms-marco-MiniLM-L-6-v2`) пересортировывает топ-30 по настоящей релевантности:

`def rerank(pages, query, top_k=5):    HARD_CAP = 30  # O(N²) scaling protection    # Priority pages (article index, routing) не могут быть выброшены    priority = [p for p in pages if p.get("_priority")]    non_priority = pages[:HARD_CAP - len(priority)]    all_pages = priority + non_priority    pairs = [(query, p["text"][:512]) for p in all_pages]    scores = cross_encoder.predict(pairs)    # Priority pages получают score = 1000 (всегда в топе)    for i, p in enumerate(all_pages):        if p.get("_priority"):            scores[i] = 1000.0    ranked = sorted(zip(scores, all_pages), key=lambda x: -x[0])    return [p for _, p in ranked[:top_k]]`
**Hard cap 30** — не прихоть, а необходимость. Cross-encoder делает forward pass для каждой пары (query, page). 30 пар — ~50ms. 100 пар — ~500ms. 1500 пар (весь корпус) — несколько секунд, и TTFT улетает за 3000ms → штраф к скору.

**Priority tagging** — самый важный паттерн. Некоторые страницы должны быть в контексте _всегда_ (определение цитируемой статьи, титульная страница дела). Cross-encoder может их опустить (например, если вопрос сформулирован иначе, чем текст статьи). Флаг `_priority=True` гарантирует, что эти страницы не выпадут.

* * *

### Типизированные ответы: когда LLM не нужен

Одно из ключевых решений — **детерминированные fast-paths** для типизированных вопросов. Зачем тратить 700ms на вызов Haiku, если можно за 5ms извлечь ответ регулярным выражением?

#### Извлечение номера закона

`if answer_type == "number" and "law number" in question.lower():    for page in context_pages:        m = re.search(r"(?:DIFC\s+)?Law\s+No\.?\s*(\d+)", page["text"])        if m:            return int(m.group(1)), [page]  # Ответ + grounding`
#### Сравнение дат

`if answer_type == "name" and is_comparison and "earlier" in question.lower():    dates = {}    for case_ref, doc_id in case_routing.items():        for pn in (1, 2):  # Дата выдачи — на первых двух страницах            page = get_page(doc_id, pn)            m = re.search(r"Date of Issue[:\s]+(\w+ \d+,?\s+\d{4})", page["text"])            if m:                dates[case_ref] = parse_date(m.group(1))    # Возвращаем case с более ранней датой    earlier = min(dates, key=dates.get)    return earlier, [pages_used]`
#### Сравнение денежных сумм

`if answer_type == "name" and "higher monetary claim" in question.lower():    amounts = {}    for case_ref, doc_id in case_routing.items():        for pn in range(1, 6):            for m in re.finditer(r"AED\s+([\d,]+(?:\.\d+)?)", page_text):                amount = float(m.group(1).replace(",", ""))                # "4 months of salary at AED 50,000" → 200,000                months_m = re.search(r"(\d+)\s*months?\s+of\s+salary", pre_context)                if months_m:                    amount *= int(months_m.group(1))                amounts[case_ref] = max(amounts.get(case_ref, 0), amount)    return max(amounts, key=amounts.get), [pages_used]`
Эти fast-paths покрывают ~30-40% типизированных вопросов. Выигрыш: -700ms на TTFT (бонус к F) и 0 токенов на API.

#### Adversarial detection

В корпусе DIFC есть вопросы-ловушки — про институты, которых в DIFC-праве просто нет:

`_ADVERSARIAL_KEYWORDS = {    "jury",           # В DIFC нет суда присяжных    "plea bargain",   # Институт common law, не DIFC    "miranda rights", # Американское право    "parole",         # Система условного освобождения, не DIFC    "bail bond",      # Залоговая система другого типа}def is_adversarial(question):    q_lower = question.lower()    return any(kw in q_lower for kw in _ADVERSARIAL_KEYWORDS)`
Если вопрос adversarial, ответ — `null` для типизированных и стандартный fallback для free_text:

> “There is no information on this question in the provided documents.”

**v15 показал, что менять этот fallback нельзя.** Я попробовал заменить его на конкретные DIFC-объяснения («DIFC Courts do not use jury trials…»). Gold ожидал generic fallback. Asst упал с 0.720 до 0.640.

* * *

### Context distillation: сжимаем контекст для LLM

Страница юридического документа — это ~1500 символов. Если в контексте 5 страниц — это 7500 символов, а большая часть нерелевантна.

Context distillation выбирает только релевантные абзацы:

`def distill_page(text, question, max_chars=1200):    paragraphs = re.split(r"\n\s*\n|\n(?=[A-Z0-9\(\[])", text)    q_words = extract_keywords(question)    scored = []    for i, para in enumerate(paragraphs):        score = sum(1 for w in q_words if w in para.lower())        # Бонус: упоминание нужной статьи        if "Article 14" in question and re.search(r"\bArticle\s+14\b", para):            score += 5        # Бонус: judge/party info в заголовочных секциях        if "judge" in question.lower() and re.search(r"BETWEEN|Judge|BEFORE", para):            score += 5        # Первый абзац (заголовок) — всегда оставляем        if i == 0:            score += 1        scored.append((score, para))    scored.sort(key=lambda x: -x[0])    result, total = [], 0    for score, para in scored:        if total + len(para) > max_chars:            break        result.append(para)        total += len(para)    return "\n\n".join(result)`
Результат: ~40% сжатие (1500 → 900 символов) с сохранением ключевой информации. Экономит ~200 input-токенов на вопрос.

**Бюджеты по типам ответов:**

| Тип | Max pages | Chars/page | Max tokens (output) |
| --- | --- | --- | --- |
| boolean | 4 | 1200 | 30 |
| number | 3 | 900 | 30 |
| date | 3 | 900 | 30 |
| name | 3 | 900 | 60 |
| free_text | 5 | 1200 | 250 |

Для boolean — больше страниц (comparison требует контекст из двух документов), но маленький output. Для free_text — больше всего и контекста, и output.

* * *

### LLM: промпты, модели, парсинг цитат

#### Выбор модели

`if answer_type == "free_text":    model = "claude-sonnet-4-6"    # Лучше рассуждает, +0.10 Asstelse:    model = "claude-haiku-4-5-20251001"  # Быстрее, хватает для извлечения`
Почему не Sonnet для всего: +300ms TTFT на каждый вопрос. При 30% free_text вопросов это снижает средний F на ~0.009. Sonnet даёт +0.10 на Asst, что в формуле = +0.03 × G. При G=0.86 это +0.026. Чистый выигрыш: +0.026 - 0.009 = **+0.017** — стоит того.

#### Type-specific промпты

Для каждого типа — отдельная инструкция. Вот пример для `number`:

```
Return ONLY a single numeric value (integer or decimal).
IMPORTANT: The answer is the VALUE stated in the text, NOT the article number.
Example: Article 19(4) says 'within six months' → answer is 6, NOT 19.
Word-numbers: 'one'=1, 'six'=6, 'twelve'=12.
Accounting parentheses: (5,000) = -5000.
If not found: null

End with CITE: followed by 0-based block numbers (e.g. CITE:0,2).
```

«NOT the article number» — результат конкретного бага. LLM получает контекст про Article 19, видит вопрос «What is the time limit under Article 19?» и отвечает… 19. Вместо 6 (месяцев). Эта строчка в промпте — хардкод-фикс одной из самых частых ошибок.

#### Comparison boolean: CoT

Для сравнительных boolean-вопросов добавлен Chain-of-Thought:

```
Compare the two entities/cases.
Extract the fact from each: E1:[fact] E2:[fact]
ANSWER:true/false
CITE:0,1
```

Вместо прямого «true/false» модель сначала извлекает факты, потом сравнивает. Это снижает ошибки сравнения на ~15%.

#### Парсинг цитат из ответа LLM

LLM возвращает что-то вроде:

```
The time limit is 6 months. CITE:0,2
```

Парсинг:

`def parse_citations(raw_response, num_context_pages):    m = re.search(r"\bCITE:\s*([\d,\s]+)\s*$", raw_response)    if m:        indices = [int(i) for i in re.findall(r"\d+", m.group(1))                   if int(i) < num_context_pages]        answer_text = raw_response[:m.start()].strip()        return answer_text, indices    return raw_response, []`
Эти индексы — 0-based номера «блоков» контекста (страниц), которые модель считает релевантными. Но модель может цитировать неточно — поэтому дальше идёт verification.

* * *

### Post-LLM verification: ловим галлюцинации

LLM иногда ошибается — возвращает число из другого контекста, путает артикул с его значением, или отвечает generic фразой вместо конкретного имени. Post-LLM verification это ловит.

#### Проверка «ответ есть в тексте»

`def verify_in_text(answer, answer_type, pages):    """Проверяет, что ответ LLM действительно встречается в контексте."""    if answer_type == "number":        variants = number_search_variants(answer)  # [6, "six", "six (6)"]        for page in pages:            for v in variants:                if re.search(re.escape(str(v)), page["text"], re.IGNORECASE):                    return True        return False    if answer_type == "name":        return any(str(answer).lower() in p["text"].lower() for p in pages)    if answer_type == "date":        variants = date_search_variants(answer)  # ["2024-03-15", "15 March 2024", "March 15, 2024"]        for page in pages:            for v in variants:                if v in page["text"]:                    return True        return False    return True  # bool и free_text не проверяем`
Если ответ не найден в тексте — значит, LLM галлюцинирует. Fallback на детерминированное извлечение:

`llm_answer = call_llm(question, context_pages)if not verify_in_text(llm_answer, answer_type, context_pages):    # LLM соврал — пробуем regex    det_answer = deterministic_extract(answer_type, context_pages, question)    if det_answer is not None:        return det_answer`
#### Article-number confusion

Одна из самых коварных ошибок:

`if answer_type == "number":    article_ref = re.search(r"Article\s+(\d+)", question)    if article_ref and int(article_ref.group(1)) == llm_answer:        # LLM вернул номер статьи вместо значения из неё        det_answer = deterministic_extract("number", pages, question)        if det_answer is not None and det_answer != llm_answer:            return det_answer  # Правильный ответ`
Пример: «What is the notice period under Article 14?» → LLM отвечает 14 вместо 30 (дней).

#### Territorial scope check

DIFC-законы действуют только в DIFC. Если вопрос спрашивает «Does DIFC Law apply in London?» — ответ false, даже если LLM говорит true:

`if answer_type == "boolean" and llm_answer is True:    foreign_m = re.search(r"apply.*\b(?:in|to)\s+(.{5,80}?)(?:\?|$)", question)    if foreign_m:        jurisdiction = foreign_m.group(1).lower()        is_foreign = any(city in jurisdiction for city in                        ["london", "new york", "paris", "singapore"])        is_difc = "difc" in jurisdiction or "dubai" in jurisdiction        if is_foreign and not is_difc:            return False  # DIFC law не применяется в другой юрисдикции`

* * *

### Evidence-based grounding: главный компонент

Grounding — множитель в формуле. Ему посвящено больше всего кода и итераций. Система выбора страниц для цитирования — трёхуровневая:

#### Уровень 1: Article index pages

Для вопросов про статьи закона — сначала ищем страницу, где статья **определена** (заголовок «Article 14»), а не просто упоминается:

`def build_article_index(pages):    """Индекс: (doc_id, article_num) → [pages where article heading appears]"""    definitions = {}    for p in pages:        # Паттерн заголовка: "Article 14" в начале строки        for m in re.finditer(r"(?:^|\n)\s*Article\s+(\d+)\b", p["text"]):            key = (p["doc_id"], m.group(1))            definitions.setdefault(key, []).append(p["page_number"])        # Паттерн sub-clause: "14(" — тоже определение        for m in re.finditer(r"(?:^|\n)\s*(\d+)\(", p["text"]):            num = int(m.group(1))            if 1 <= num <= 200:                key = (p["doc_id"], str(num))                definitions.setdefault(key, []).append(p["page_number"])    return definitions`
**Почему definitions, а не all mentions:** страница, где написано «see Article 14» в тексте другой статьи — это не gold-страница. Gold — это страница, где Article 14 определена и содержит ответ.

Это изменение (article index → CITE ordering) дало **+0.065 к G** (v12→v13).

#### Уровень 2: LLM citations (CITE)

Если article index не помог — используем цитаты из ответа LLM:

`if cited_indices:  # [0, 2] — LLM считает релевантными блоки 0 и 2    for i in cited_indices:        candidate_pages.append(context_pages[i])`
#### Уровень 3: Evidence verification

Финальная проверка: содержит ли кандидат-страница **реальное доказательство** ответа?

`def verify_evidence(answer, answer_type, candidate_pages):    if answer_type == "number":        # Ищем страницу, где есть И значение И ссылка на статью        for page in candidate_pages:            has_value = any(v in page["text"] for v in number_variants(answer))            has_article = re.search(r"Article\s+\d+", page["text"])            if has_value and has_article:                return [page]  # Идеальный кандидат        # Fallback: хотя бы значение        for page in candidate_pages:            if any(v in page["text"] for v in number_variants(answer)):                return [page]    return candidate_pages[:1]  # Крайний fallback`
Ключевая идея: страница, содержащая **и ответ, и ссылку на нужную статью** — почти наверняка gold. Страница только со ссылкой или только со значением — менее вероятна.

#### Smart article continuation

Статьи часто разбиты на две страницы. Наивный подход — всегда добавлять следующую страницу. Проблема: следующая страница может быть Article 15, а нам нужна 14.

`def should_add_next_page(current_page, target_article, page_lookup):    next_key = (current_page["doc_id"], current_page["page_number"] + 1)    next_page = page_lookup.get(next_key)    if not next_page:        return False    # Проверяем: начинается ли следующая страница с ДРУГОЙ статьи?    next_text = next_page["text"][:200]    new_article = re.search(r"\bArticle\s+(\d+)\b", next_text)    if new_article and new_article.group(1) != target_article:        return False  # Следующая страница — другая статья, не добавляем    return True  # Та же статья продолжается — добавляем`
Это изменение дало **+0.037 к G** (v13→v14).

#### Page caps по типам

| Тип вопроса | Max pages в grounding | Почему |
| --- | --- | --- |
| boolean (не comparison) | 2 | Gold обычно 1 страница |
| number | 2 | Одно число — одна страница |
| date | 2 | Одна дата — одна страница |
| name (не comparison) | 2 | Одно имя — одна страница |
| comparison | 4 | Минимум по 1 странице на каждое дело |
| free_text | 5 | Синтез из нескольких источников |

v11 показал: cap 3 → 4 для non-comparison = +43% страниц, но G **упал** на 0.059. v14 показал: cap 3 → 2 для non-comparison = -13% страниц, G **вырос** на 0.037.

* * *

### Математика grounding: β=2.5 под микроскопом

Это самый важный раздел для тех, кто строит RAG с grounding-скорингом. β=2.5 кажется очевидным — «recall важнее, добавляй больше страниц». На практике всё сложнее.

![Image 2: Влияние precision и recall на grounding score](https://habrastorage.org/r/w1560/getpro/habr//post_images/4af/3c6/021/4af3c6021853ae0bf7d98f603f9cd219.png)

Влияние precision и recall на grounding score

#### Формула F-beta

```
F_β = (1 + β²) × precision × recall / (β² × precision + recall)
```

При β=2.5: β²=6.25. Recall взвешен в 6.25 раз тяжелее precision.

#### Сценарий 1: Пропущенная золотая страница

Gold = 2 страницы. Ты цитируешь 1 из 2:

```
precision = 1/1 = 1.0, recall = 1/2 = 0.5
F = 7.25 × 1.0 × 0.5 / (6.25 × 1.0 + 0.5) = 3.625 / 6.75 = 0.537
```

Ты цитируешь 2 из 2 + 1 лишнюю:

```
precision = 2/3 = 0.667, recall = 2/2 = 1.0
F = 7.25 × 0.667 × 1.0 / (6.25 × 0.667 + 1.0) = 4.836 / 5.167 = 0.936
```

**+74%.** Одна правильная страница (даже с шумом) радикально поднимает G.

#### Сценарий 2: Лишняя страница

Gold = 1 страница. Ты цитируешь её:

```
precision = 1/1 = 1.0, recall = 1/1 = 1.0
F = 1.0 (идеально)
```

Ты цитируешь её + 1 лишнюю:

```
precision = 1/2 = 0.5, recall = 1/1 = 1.0
F = 7.25 × 0.5 × 1.0 / (6.25 × 0.5 + 1.0) = 3.625 / 4.125 = 0.879
```

**-12%.** Каждая лишняя страница — это реальная потеря.

#### Сценарий 3: Две лишних

Gold = 1. Цитируешь 1 + 2 лишних:

```
precision = 1/3 = 0.333, recall = 1/1 = 1.0
F = 7.25 × 0.333 / (6.25 × 0.333 + 1.0) = 2.414 / 3.083 = 0.783
```

**-22%.** Две лишних страницы = минус пятая часть grounding.

#### Практический вывод

Формула наказывает за лишние страницы сильнее, чем кажется при β=2.5. Оптимальная стратегия:

1.   **Всегда включай все golden pages** (recall = 1.0 критичен)

2.   **Минимизируй шум** (каждая лишняя страница стоит 10-22%)

3.   **Лучше недоцитировать, чем перецитировать** — если не уверен, что страница gold, не добавляй

Вот как это проявилось в экспериментах:

| Версия | Avg pages/q | G score | Комментарий |
| --- | --- | --- | --- |
| v10 | 2.08 | 0.781 | baseline |
| v11 | 2.97 | 0.722 | +43% страниц, G **упал** |
| v14 | ~1.8 | 0.862 | -13% страниц, G **вырос** |

**Precision > volume.** Это контринтуитивно, когда β=2.5 кричит «recall!», но формула не врёт.

* * *

### История итераций: 15 версий, 3 провала, 1 финальный скор

![Image 3: Прогресс скора: 17 итераций от 0.034 до 0.791](https://habrastorage.org/r/w1560/getpro/habr//post_images/27b/41a/692/27b41a6925e3dc86a0c5ded229c9d847.png)

Прогресс скора: 17 итераций от 0.034 до 0.791

Полная таблица:

| Ver | Det | Asst | G | T | F | Total | Ключевое изменение |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 0.857 | 0.613 | 0.050 | 0.900 | 0.960 | 0.034 | Первая подача |
| v2 | 0.857 | 0.613 | 0.050 | 0.900 | 0.990 | 0.035 | TTFT fix |
| v3 | 0.857 | 0.640 | 0.050 | 0.900 | 1.002 | 0.036 | Asst tweak |
| v4 | 0.857 | 0.673 | **0.550** | 0.986 | 1.005 | **0.438** | `.pdf` fix → G x11 |
| v5 | 0.886 | 0.647 | 0.521 | 0.990 | 1.005 | 0.422 | Embeddings, Det up |
| v6 | 0.800 | 0.607 | 0.610 | 0.981 | 1.040 | 0.462 | Hybrid search, TTFT halved |
| v7 | 0.929 | 0.593 | 0.659 | 0.991 | 1.035 | 0.559 | Adversarial detection |
| v8 | 0.929 | 0.713 | **0.788** | 0.996 | 1.038 | **0.704** | Page expansion + β math |
| v9 | 0.957 | 0.680 | 0.690 | 0.996 | 1.041 | 0.626 | **REGRESSION**: adj pages |
| v10 | 0.971 | 0.687 | 0.781 | 0.996 | 1.040 | 0.716 | Evidence overhaul + hardcodes |
| v11 | 0.971 | 0.713 | 0.722 | 0.996 | 1.037 | 0.667 | **REGRESSION**: more pages |
| v12 | 0.971 | 0.687 | 0.760 | 0.996 | 1.039 | 0.696 | Partial revert |
| v13 | 0.971 | 0.707 | **0.825** | 0.996 | 1.031 | 0.756 | Article index first |
| v14 | 0.971 | 0.720 | **0.862** | 0.996 | 1.029 | **0.791** | Smart continuation + caps |
| v15 | 0.929 | 0.640 | 0.862 | 0.996 | 1.037 | 0.749 | **REGRESSION**: judge override |

```
v1  ██                                            0.034
v2  ██                                            0.035
v3  ██                                            0.036
v4  ██████████████████████                        0.438
v5  █████████████████████                         0.422
v6  ███████████████████████                       0.462
v7  ████████████████████████████                  0.559
v8  ███████████████████████████████████           0.704
v9  ███████████████████████████████               0.626  ↓
v10 ████████████████████████████████████          0.716
v11 █████████████████████████████████             0.667  ↓
v12 ███████████████████████████████████           0.696
v13 ██████████████████████████████████████        0.756
v14 ████████████████████████████████████████      0.791
v15 █████████████████████████████████████         0.749  ↓
```

#### Три регрессии — три урока

**v9 (0.626, -0.078):** «Если статья длинная, соседняя страница тоже релевантна». Нет. Соседняя страница часто содержит другую статью. Adjacent page retention без проверки содержимого — антипаттерн.

**v11 (0.667, -0.049):** «β=2.5 значит больше страниц = лучше». Нет. +43% страниц = -7.5% G. Дополнительные страницы были шумом. Precision matters даже при recall-ориентированной метрике.

**v15 (0.749, -0.042):** «Мы можем улучшить Det, добавив domain-специфичные overrides». Нет. «Assistant Registrar» — не судья в gold-ответах. Промпт для free_text — калиброван, менять формулировки опасно. Два изменения — два провала.

* * *

### Что работает, а что нет: сводка для строителей RAG

#### Что работает

| Подход | Влияние | Почему |
| --- | --- | --- |
| Page-level retrieval (не чанки) | Фундаментальное | Grounding считается по страницам |
| Гибридный BM25 + embeddings | +0.089 G (v4→v6) | BM25 для точных терминов, embeddings для семантики |
| Article index first, CITE second | +0.065 G (v12→v13) | Определение статьи > случайное упоминание |
| Evidence verify (answer + article ref) | +0.044 G (v12→v13) | Страница с И ответом И артикулом — почти наверняка gold |
| Smart article continuation | +0.037 G (v13→v14) | Только если следующая страница — та же статья |
| Adversarial detection | +0.129 Det (v6→v7) | null для невозможных вопросов |
| Post-LLM text verification | +0.042 Det (v9→v10) | Ловит галлюцинированные числа и имена |
| Type-specific page caps | +0.037 G (v13→v14) | 2 для non-comparison, 4 для comparison |
| Deterministic fast-paths | +0.03 F factor | -700ms TTFT, 0 API-токенов |
| Context distillation | ~0 скор, -0.05/run | Экономит токены без потери качества |

#### Что НЕ работает (проверено экспериментами)

| Антипаттерн | Результат | Почему |
| --- | --- | --- |
| Больше страниц в grounding | G -0.059 (v11) | Шум > сигнал, precision penalty |
| Adjacent page retention | G -0.098 (v9) | Следующая страница ≠ та же статья |
| Domain-specific fallback для adversarial | Asst -0.080 (v15) | Gold ожидает generic fallback |
| Post-LLM boolean overrides | Det -0.042 (v15) | «Assistant Registrar» ≠ judge |
| Изменение формулировок free_text промпта | Asst falls | Промпт калиброван, любое изменение — риск |
| Sonnet для boolean вопросов | 11/19 null | Sonnet «рассуждает» и сомневается, Haiku извлекает |
| Batch-изменения (17 за раз в v8) | Непонятно, что помогло | Невозможно сделать ablation |

* * *

### Разработка с Claude Code: честный разбор

Весь пайплайн написан через Claude Code — ~3000 строк в 7 модулях за 5 дней.

#### Типичная итерация

Я: «В v13 мы переставили article index перед CITE. Теперь нужно добавить проверку: если следующая страница начинается с Article N+1, не добавляй её. Только если продолжается та же статья.»

Claude Code: читает retrieve.py и llm.py → находит функцию article continuation → добавляет regex-проверку → обновляет caps → прогоняет build_submission.py → показывает diff.

Три минуты. Без Claude Code — час.

#### Что Claude Code делает хорошо

**Скорость итераций.** 17 версий за 5 дней — больше 3 в день. Каждая версия включает изменения в 3-5 файлах, 50-200 строк кода, и прогон submission. Руками я бы сделал 3-5 итераций за это время.

**Рефакторинг.** Когда архитектура менялась (а она менялась 15 раз), Claude перестраивал зависимости, обновлял типы, правил вызовы.

**Память и история.** Claude Code хранит контекст между сессиями в `.claude/memory/`. Закрыл ноутбук, открыл через 4 часа — он помнит, что v11 сломал grounding и почему. Плюс каждое изменение коммитится в git с осмысленным описанием, а CHANGELOG.md ведётся автоматически. Когда работаешь с AI-агентом, версионирование — must have: без него невозможно откатиться или понять, какое изменение что сломало.

**Код-ревью своих же изменений.** Перед каждой подачей я просил: «проверь, не сломали ли мы что-нибудь». Claude читал diff и иногда находил проблемы до submission.

**Исследование подходов.** Claude сам искал современные техники (RRF fusion, cross-encoder reranking, context distillation), объяснял trade-offs и предлагал, что стоит попробовать следующим. Не просто исполнитель — активный участник в выборе направления оптимизации.

#### Где нужен человек

**Приоритизация.** «Что оптимизировать дальше: Det или G?» — вопрос, на который модель отвечает «и то, и другое». А тебе нужно выбрать одно, потому что осталось 5 submission.

**Знание evaluation protocol.** Что Assistant Registrar — не судья в gold-ответах, что generic fallback — это ожидаемый gold для adversarial вопросов. Эти нюансы оценки узнаёшь только из результатов подач и Discord-чата с организаторами.

**Интерпретация провалов.** Когда v11 сломал G, Claude предложил «увеличить recall floor ещё больше». Правильное решение было противоположным — уменьшить число страниц. Для этого нужно было понять _почему_ упало, а не просто «что-то упало, давай крутанём ручку дальше».

#### Главный компромисс

Claude Code ускоряет итерации в 5-10 раз, но снижает глубину понимания кода. Я хуже знаю свой codebase, чем если бы писал всё руками. Баг с `.pdf` мог бы всплыть раньше, если бы я сам строчка за строчкой писал парсер. Но без Claude Code за 5 дней было бы 3-5 итераций вместо 17 — и скор остался бы где-то в районе 0.4.

* * *

### Результаты warmup

| Метрика | v1 (старт) | v14 (лучший) | Изменение |
| --- | --- | --- | --- |
| Det | 0.857 | 0.971 | +13% |
| Asst | 0.613 | 0.720 | +17% |
| G | 0.050 | 0.862 | **x17** |
| T | 0.900 | 0.996 | +11% |
| **Total** | **0.034** | **0.791** | **x23** |

Лидер warmup — CPBD с 0.959 (Det=1.0, G=0.976). Основной гэп — grounding (0.862 vs 0.976) и Asst (0.720 vs 0.840).

* * *

### Финал: стена масштабирования

#### 30 → 300 документов

Финальная фаза: 303 документа, 4244 страницы, 900 вопросов, **2 попытки подачи**. Код зафиксирован на v14.

Первая проблема обнаружилась до подачи: **кеш warmup перезаписал данные финала**. Пайплайн радостно проиндексировал 30 warmup-документов вместо 303 финальных. 37 null-ответов из 900. Очистили кеш, переиндексировали — nulls упали до 4. Банальный баг, но при 2 попытках — опасный.

![Image 4: Warmup vs Финал: падение метрик](https://habrastorage.org/r/w1560/getpro/habr//post_images/7e2/9f7/f74/7e29f7f74649b83dda16de5c48bd8b23.png)

Warmup vs Финал: падение метрик

#### F-v1: 0.457

| Det | Asst | G | T | F | Total |
| --- | --- | --- | --- | --- | --- |
| 0.696 | 0.637 | 0.647 | 1.000 | 1.042 | **0.457** |

Падение по всем метрикам:

| Метрика | Warmup v14 | Final v1 | Падение |
| --- | --- | --- | --- |
| Det | 0.971 | 0.696 | −28% |
| Asst | 0.720 | 0.637 | −12% |
| G | 0.862 | 0.647 | −25% |
| **Total** | **0.791** | **0.457** | **−42%** |

#### Диагностика: почему всё сломалось

Параллельная диагностика тремя агентами вскрыла корневые причины:

**1. Retrieval dilution.** С 30 документами BM25 почти всегда находит правильный. С 303 — один документ в 537 страниц (DIFC Courts Rules) загрязняет результаты для любого запроса с юридической лексикой. Запрос про «Employment Law Article 19» возвращает страницы из Courts Rules, Companies Law и Operating Law — до Employment Law.

**2. Disambiguation failure.** 53 consultation papers пронумерованы от 1 до 8, но из разных лет и на разные темы. «Consultation Paper No. 3» матчится с 7 документами. BM25 выбирает самый «плотный» по терминам, а не правильный.

**3. Law number regex ловит fee/fine вопросы.** Регулярка `difc\s+law\s+no` для определения «какой номер закона?» матчилась с любым вопросом, содержащим «DIFC Law No. 1 of 2019» — включая вопросы про штрафы. Вместо суммы штрафа возвращался номер закона. **~27 неправильных ответов.**

**4. 93 zero-page ответа.** 89 из них — adversarial free_text с fallback-текстом и пустыми страницами. Это 10% всех ответов с G=0.

**5. Case number leakage.** LLM извлекает номер из case reference вместо фактического ответа: «How many claimants in case CFI 070/2018?» → 70 (номер дела, не количество сторон).

**6. Два пустых документа.** Сканированные PDF без OCR — 19 невидимых страниц.

#### F-v2: 8 фиксов, -0.008 к скору

Для второй (и последней) попытки применили 8 целевых исправлений:

1.   **Law number guard** — исключить вопросы со словами fine/fee/penalty

2.   **Free_text zero-page** — цитировать top-1 страницу для adversarial/fallback

3.   **Case number leakage** — post-LLM проверка: ответ = номер дела?

4.   **Consultation paper disambiguation** — matching по quoted title

5.   **Document diversity** — cap 5 страниц на документ в retrieval

6.   **OCR** — pytesseract для пустых документов

7.   **Party count boost** — max_pages=5, Sonnet для party/names

8.   **CP routing** — consultation paper titles в doc routing index

Результат:

| Метрика | F-v1 | F-v2 | Дельта |
| --- | --- | --- | --- |
| Det | 0.696 | **0.709** | +0.013 |
| Asst | 0.637 | **0.644** | +0.007 |
| G | 0.647 | **0.631** | **−0.016** |
| F | 1.042 | 1.033 | −0.009 |
| **Total** | **0.457** | **0.449** | **−0.008** |

Det и Asst чуть выросли. Но G **упал**. Причина: мы добавили страницы к adversarial-ответам, предполагая, что оценщик ожидает цитаты. Он не ожидает. Когда gold = пустые страницы, любая цитата = шум → precision падает → G падает.

Одно неверное предположение об evaluation protocol стоило дороже, чем все 7 правильных фиксов вместе.

#### Полная таблица: от warmup к финалу

```
WARMUP:
v1  ██                                            0.034
v4  ██████████████████████                        0.438
v7  ████████████████████████████                  0.559
v8  ███████████████████████████████████           0.704
v10 ████████████████████████████████████          0.716
v14 ████████████████████████████████████████      0.791  ← best

FINAL:
F-v1 ███████████████████████                      0.457
F-v2 ██████████████████████                       0.449
```

* * *

### Уроки: что бы я сделал иначе

#### Для warmup

**1. Начал бы с валидации формата.** Три подачи на обнаружение `.pdf` в doc_id — это три подачи, которых больше не будет. Первый шаг в любом соревновании: unit-тест на формат submission.

**2. Одно изменение = одна подача.** В v8 я сделал 17 изменений за раз. Скор вырос. Но какие из 17 помогли? Без ablation testing (отключаешь по одному компоненту и смотришь, как меняется метрика) — не узнаешь.

**3. Собрал бы eval-сет.** Без ground truth каждый эксперимент = подача. Даже 10 вопросов с известными ответами сэкономили бы 3-4 submission.

#### Для финала

**4. Подал бы v14 as-is первым.** Мы обнаружили баг кеша во время v1, потратив baseline-подачу на отладку. Правильно: сначала чистый v14 как baseline → потом фиксы.

**5. Иерархический retrieval.** Flat BM25 не масштабируется с 30 до 300 документов. Нужно: сначала определить документ (title match, type classification), потом искать страницы внутри него. Document-level pre-filter вместо page-level search по всему корпусу.

**6. Протестировал бы evaluation protocol.** Предположение «add pages = better G» стоило нам v2. Один тест с пустыми страницами в warmup показал бы, что оценщик даёт G=1.0 за пустой citation list когда gold тоже пустой.

**7. Синтетический scaling test.** Дублировать warmup-документы, добавить шум → проверить, как pipeline деградирует при 100+ документах. Это выявило бы retrieval dilution до финала.

* * *

### Главные выводы

**1. Grounding определяет всё.** G — множитель в формуле скоринга. 25% падение grounding уничтожает весь скор, даже если ответы идеальные. Первый приоритет — всегда правильные страницы, а не правильный ответ.

**2. Precision > recall, даже при β=2.5.** Контринтуитивно, но доказано тремя экспериментами. Каждая лишняя страница стоит 10-22%. +43% страниц = −7.5% G.

**3. Domain guardrails бьют general intelligence.** «Assistant Registrar» ≠ judge в gold-ответах. Generic fallback — это gold answer для adversarial вопросов. Эти правила нельзя вывести из промпта — только из результатов подач. Они дают +0.13 Det.

**4. Prompt engineering хрупок.** Изменение формулировки free_text промпта: Asst −0.080. «Если работает — не трогай» — легитимный инженерный принцип.

**5. Масштаб всё меняет.** Pipeline, оптимизированный на 30 документах, теряет 42% при 300. Retrieval precision — фундамент, и при масштабировании он трескается первым.

**6. Evaluation protocol — часть задачи.** Неверное предположение о том, как оценщик считает G для edge cases, стоило дороже, чем 7 правильных багфиксов.

* * *

### Расходы

*   **Claude Code:** 100 USD/мес (Max подписка, используется не только для этого проекта)

*   **API (Haiku + Sonnet):** 87.95 USD за всё соревнование — warmup + финал + отладка. Финал: 13.38 USD (Sonnet 9.36 + Haiku 4.02). Остальные ~75 USD — warmup и дебаг.

*   **Embeddings + reranking:** локальные модели, бесплатно

*   **Время:** 5 активных дней (Mar 11-13 warmup, Mar 19 + 21 финал)

* * *

### Финальные результаты

| Фаза | Версия | Det | Asst | G | T | F | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Warmup | v1 (старт) | 0.857 | 0.613 | 0.050 | 0.900 | 0.960 | **0.034** |
| Warmup | v14 (лучший) | 0.971 | 0.720 | 0.862 | 0.996 | 1.029 | **0.791** |
| Final | v1 | 0.696 | 0.637 | 0.647 | 1.000 | 1.042 | **0.457** |
| Final | v2 | 0.709 | 0.644 | 0.631 | 1.000 | 1.033 | **0.449** |

* * *

### Что забрать с собой

Если вы строите RAG — неважно, для соревнования или продакшена — вот что я бы хотел знать до старта:

**Сначала формат, потом качество.** Прежде чем оптимизировать retrieval и промпты — убедитесь, что ваш output матчится с ожидаемым форматом. Напишите валидатор. Это сэкономит больше времени, чем любая архитектурная оптимизация.

**Считайте математику своей метрики.** Не полагайтесь на интуицию про «recall важнее». Возьмите формулу, подставьте конкретные сценарии, посчитайте. В моём случае математика F-beta с β=2.5 показала, что каждая лишняя страница стоит 10-22% — и это перевернуло всю стратегию.

**Одно изменение за раз, метрики на каждое.** Без этого вы не знаете, что работает. Ведите changelog, коммитьте каждую итерацию, записывайте скоры. Когда нужно откатиться — а это будет нужно — вы скажете себе спасибо.

**Проверяйте на масштабе.** Pipeline, идеально работающий на тестовом наборе, может потерять 42% на реальном. Если ваш eval-сет в 10 раз меньше прода — вы не тестируете retrieval, вы тестируете удачу.

**AI-ассистент ускоряет, но не заменяет.** Claude Code позволил мне сделать 17 итераций за 5 дней вместо 3-5. Но каждый раз, когда нужно было решить _что_ оптимизировать, _как_ интерпретировать провал и _стоит ли_ рисковать последнюю подачу — это оставалось на мне.

* * *

Сейчас идёт закрытая оценка финальной фазы — результаты объявят позже. Я не питаю иллюзий: в warmup-лидерборде я был далеко от топа (0.791 vs лидер 0.959), и 42% падение на финале вряд ли это исправит. Но 5 дней, 88 USD и путь от нуля до работающего пайплайна — это опыт, ради которого стоило участвовать.

**Код:**[GitHub](https://github.com/TagirRamilevich/agentic-rag-legal-challenge) | **Челлендж:**[ARLC 2026](https://www.agentic-challenge.ai/)

Только зарегистрированные пользователи могут участвовать в опросе. [Войдите](https://habr.com/kek/v1/auth/habrahabr/?back=&hl=ru), пожалуйста.

21.43%Да, в проде 3

35.71%Экспериментирую / делаю пет-проекты 5

21.43%Пока нет, но планирую 3

14.29%Нет и не планирую 2

7.14%Что такое RAG?1

Проголосовали 14 пользователей. Воздержался 1 пользователь.
