//! NPA typed members (M211 S01/S02, ADR-0029).
//!
//! Единый producer якорей: типизированный поток потребляет канонические
//! anchor'ы `npa_anchor::scan_anchors_diagnosed` (все guards: INBOUND,
//! MINJUST, date-overlap; локальные UTF-8 byte spans; occurrences не
//! сливаются по `(date, number)`). Собственный сканер дат удалён —
//! смысловое дублирование `scan_dates` устранено.
//!
//! TYPE-кандидаты сканируются в тексте, приклейка — `_type_for_span`
//! прототипа: ближайший preceding TYPE без TYPE за другим якорем.

use crate::npa_anchor::{self, AnchorDiagnostic, LocalSpan};

/// Как получен TYPE члена: записан в этом же блоке либо не разрешён.
///
/// `InheritedFromSeriesHead` здесь намеренно отсутствует: cross-block
/// наследование — граница S03, intra-block наследование живёт в
/// `local_grammar::DerivationSource` (T04). Здесь фиксируется только
/// provenance самого typed-потока.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum TypeDerivation {
    /// TYPE-голова найдена среди кандидатов текущего блока.
    WrittenHere,
    /// Ни одного кандидата до якоря не выжило — TYPE не разрешён.
    Unresolved,
}

/// Конкурирующее чтение TYPE с source-span головы в том же блоке.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct TypeHypothesis {
    pub canon: String,
    pub evidence: LocalSpan,
}

/// Типизированный член: нормализованная дата + номер + TYPE и локальный
/// byte-span якоря-вхождения (тот же поток, что S01; M207 `{fragment_id,
/// start, end}` shape, hand-rolled без внешнего (de)serializer'а).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct TypedMember {
    pub date: String,
    pub number: String,
    pub type_name: String,
    pub approved_by: String,
    pub span: LocalSpan,
    /// Provenance победившего TYPE (RC28-F09: победитель больше не молчит).
    pub derivation: TypeDerivation,
    /// Byte-span головы-победителя в блоке (`None` при `Unresolved`).
    pub type_evidence: Option<LocalSpan>,
    /// Соперники среди выживших гипотез (без победителя), с source-span.
    pub alternatives: Vec<TypeHypothesis>,
    /// `true`, если ни одна гипотеза не выжила: `type_name` пуст,
    /// `derivation == Unresolved`.
    pub unresolved: bool,
}

#[derive(Debug)]
pub struct TypeCandidate {
    pub start: usize,
    pub end: usize,
    pub canon: String,
}

fn is_cyr(c: char) -> bool {
    matches!(c, 'А'..='я' | 'Ё' | 'ё')
}
fn is_word(c: char) -> bool {
    c.is_ascii_alphanumeric() || is_cyr(c)
}

fn starts_lower(text_l: &[char], i: usize, pat: &str) -> bool {
    let p: Vec<char> = pat.chars().collect();
    i + p.len() <= text_l.len() && text_l[i..i + p.len()] == p[..]
}

fn slice_eq(text_l: &[char], i: usize, s: &str) -> bool {
    let sc: Vec<char> = s.chars().collect();
    i + sc.len() <= text_l.len() && text_l[i..i + sc.len()] == sc[..]
}

fn contains_lower(text_l: &[char], from: usize, pat: &str) -> bool {
    let p: Vec<char> = pat.chars().collect();
    if p.is_empty() {
        return false;
    }
    (from..text_l.len().saturating_sub(p.len().saturating_sub(1)))
        .any(|i| text_l[i..i + p.len()] == p[..])
}

fn skip_ws(text: &[char], mut i: usize) -> usize {
    while i < text.len() && text[i].is_whitespace() {
        i += 1;
    }
    i
}

/// Конец слова (буквы/цифры/дефис) от позиции `i`.
fn word_end(text: &[char], mut i: usize) -> usize {
    while i < text.len() && (is_word(text[i]) || text[i] == '-') {
        i += 1;
    }
    i
}

/// Полное совпадение слова с границей справа (`word_eq`), регистр снят.
fn word_eq(lower: &[char], i: usize, w: &str) -> bool {
    let wc: Vec<char> = w.chars().collect();
    if i + wc.len() > lower.len() || lower[i..i + wc.len()] != wc[..] {
        return false;
    }
    i + wc.len() == lower.len() || !is_word(lower[i + wc.len()])
}

/// Generic издатель после ствола («распоряжением МТУ Росимущества в ...»).
/// Возвращает (char-конец, текст издателя как написан). Останавливается на
/// служебных словах `от`/`об`/`о`/`не` и пунктуации (эталон TYPE_HEAD).
fn generic_issuer(text: &[char], from: usize) -> Option<(usize, String)> {
    let n = text.len();
    let mut pos = skip_ws(text, word_end(text, from));
    if pos >= n || !is_word(text[pos]) || !text[pos].is_uppercase() {
        return None;
    }
    let mut words: Vec<String> = Vec::new();
    let mut last_end = pos;
    for _ in 0..16 {
        let w0 = skip_ws(text, pos);
        if w0 >= n || !is_word(text[w0]) {
            break;
        }
        let w1 = word_end(text, w0);
        let w: String = text[w0..w1].iter().collect();
        let wl: Vec<char> = w.to_lowercase().chars().collect();
        let stop = wl == ['о', 'т'] || wl == ['о', 'б'] || wl == ['о'] || wl == ['н', 'е'];
        if stop {
            break;
        }
        words.push(w);
        last_end = w1;
        pos = w1;
    }
    if words.is_empty() {
        return None;
    }
    Some((last_end, words.join(" ")))
}

/// «Конституционн… Суд… (Российск… Федераци…)? в Постановлен…» —
/// вынесенный эмитент; canon «Постановление КС РФ» (TYPE_HEAD, D519).
fn constitutional_court_carry(text: &[char], lower: &[char], i: usize) -> Option<usize> {
    let n = text.len();
    let cend = word_end(text, i);
    let n1 = skip_ws(text, cend);
    if n1 >= n || !starts_lower(lower, n1, "суд") {
        return None;
    }
    let mut n2 = skip_ws(text, word_end(text, n1));
    if n2 < n && starts_lower(lower, n2, "российск") {
        let r1 = word_end(text, n2);
        let r2 = skip_ws(text, r1);
        if r2 < n && starts_lower(lower, r2, "федераци") {
            n2 = skip_ws(text, word_end(text, r2));
        }
    }
    if n2 >= n || !word_eq(lower, n2, "в") {
        return None;
    }
    let n3 = skip_ws(text, n2 + 1);
    if n3 >= n || !starts_lower(lower, n3, "постановлен") {
        return None;
    }
    Some(word_end(text, n3))
}

/// Скан TYPE-кандидатов.
pub fn scan_types(text: &[char]) -> Vec<TypeCandidate> {
    let n = text.len();
    let lower: Vec<char> = text
        .iter()
        .map(|c| c.to_lowercase().next().unwrap_or(*c))
        .collect();
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < n {
        // --- Приказ + issuer ---
        if starts_lower(&lower, i, "приказ") {
            // конец полного слова (приказом, приказ, приказы...)
            let mut wend = i;
            while wend < n && is_word(text[wend]) {
                wend += 1;
            }
            let iss = skip_ws(text, wend);
            if iss < n && text[iss].is_uppercase() {
                // issuer run до «от» / точки
                let mut ie = iss;
                let mut words: Vec<String> = Vec::new();
                for _ in 0..8 {
                    let w0 = skip_ws(text, ie);
                    if w0 >= n || !is_word(text[w0]) {
                        break;
                    }
                    if w0 + 2 < n
                        && lower[w0] == 'о'
                        && lower[w0 + 1] == 'т'
                        && !is_word(text[w0 + 2])
                    {
                        break;
                    }
                    let mut w1 = w0;
                    while w1 < n && (is_word(text[w1]) || text[w1] == '-') {
                        w1 += 1;
                    }
                    words.push(text[w0..w1].iter().collect());
                    ie = w1;
                }
                if !words.is_empty() {
                    let canon = format!("Приказ {}", words.join(" "));
                    out.push(TypeCandidate {
                        start: i,
                        end: ie,
                        canon,
                    });
                    i = ie;
                    continue;
                }
            }
            out.push(TypeCandidate {
                start: i,
                end: i + 6,
                canon: "приказ".into(),
            });
            let mut we = i;
            while we < n && is_word(text[we]) {
                we += 1;
            }
            i = we;
            continue;
        }
        // --- Постановление КС РФ (аббревиатура) ---
        if starts_lower(&lower, i, "постановлен") {
            let pwend = word_end(text, i);
            let nks = skip_ws(text, pwend);
            if word_eq(&lower, nks, "кс") {
                let nrf = skip_ws(text, nks + 2);
                if word_eq(&lower, nrf, "рф") {
                    let e = word_end(text, nrf);
                    out.push(TypeCandidate {
                        start: i,
                        end: e,
                        canon: "Постановление КС РФ".into(),
                    });
                    i = e;
                    continue;
                }
            }
        }
        // --- вынесенный эмитент: «Конституционн… Суд… в Постановлен…» ---
        if starts_lower(&lower, i, "конституционн") {
            if let Some(e) = constitutional_court_carry(text, &lower, i) {
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Постановление КС РФ".into(),
                });
                i = e;
                continue;
            }
        }
        // --- Постановление КС / Пленум / Правительства ---
        if starts_lower(&lower, i, "постановлен") {
            if contains_lower(&lower, i, "конституционн") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Постановление КС РФ".into(),
                });
                i = e;
                continue;
            }
            if contains_lower(&lower, i, "пленума") {
                if contains_lower(&lower, i, "вас") {
                    let e = type_end(text, i);
                    out.push(TypeCandidate {
                        start: i,
                        end: e,
                        canon: "Постановление Пленума ВАС РФ".into(),
                    });
                    i = e;
                    continue;
                }
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Постановление Пленума ВС РФ".into(),
                });
                i = e;
                continue;
            }
            if contains_lower(&lower, i, "правительств") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Постановление Правительства РФ".into(),
                });
                i = e;
                continue;
            }
        }
        // --- распоряжение Правительства / Президента / generic <issuer> ---
        if starts_lower(&lower, i, "распоряжен") {
            let wend = word_end(text, i);
            let n1 = skip_ws(text, wend);
            if starts_lower(&lower, n1, "правительств") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "распоряжение Правительства РФ".into(),
                });
                i = e;
                continue;
            }
            if starts_lower(&lower, n1, "президента") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Распоряжение Президента РФ".into(),
                });
                i = e;
                continue;
            }
            if let Some((e, issuer)) = generic_issuer(text, i) {
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: format!("Распоряжение {issuer}"),
                });
                i = e;
                continue;
            }
        }
        // --- Указ Президента ---
        if starts_lower(&lower, i, "указ") && contains_lower(&lower, i, "президента")
        {
            let e = type_end(text, i);
            out.push(TypeCandidate {
                start: i,
                end: e,
                canon: "Указ Президента РФ".into(),
            });
            i = e;
            continue;
        }
        // --- Федеральный / конституционный закон ---
        if starts_lower(&lower, i, "федеральн") {
            if contains_lower(&lower, i, "конституционн") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Федеральный конституционный закон".into(),
                });
                i = e;
                continue;
            }
            // следующее слово — «закон»?
            // word end of "федеральн*"
            let mut fw = i;
            while fw < n && is_word(text[fw]) {
                fw += 1;
            }
            let nw = skip_ws(text, fw);
            if nw < n && starts_lower(&lower, nw, "закон") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Федеральный закон".into(),
                });
                i = e;
                continue;
            }
        }
        // --- Закон РФ / СССР ---
        if starts_lower(&lower, i, "зако") {
            if contains_lower(&lower, i, "российск") && !contains_lower(&lower, i, "федеральн")
            {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Закон РФ".into(),
                });
                i = e;
                continue;
            }
            if contains_lower(&lower, i, "ссср") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Закон СССР".into(),
                });
                i = e;
                continue;
            }
        }
        // --- Решение/Письмо УФАС/ФАС ---
        for (pat, label) in [("решени", "Решение"), ("письм", "Письмо")] {
            if starts_lower(&lower, i, pat) {
                let has_fas = contains_lower(&lower, i, "уфас")
                    || (contains_lower(&lower, i, "фас") && !contains_lower(&lower, i, "уфас"));
                if has_fas {
                    let e = fas_end(text, i, n);
                    let span: String = text[i..e.min(n)].iter().collect();
                    let canon = canon_fas(&span, label);
                    out.push(TypeCandidate {
                        start: i,
                        end: e,
                        canon,
                    });
                    i = e;
                    continue;
                }
            }
        }
        // --- первичные ---
        // ВАЖНО: `i` — индекс по Vec<char>, поэтому шаг считается в char'ах
        // (`pat.chars().count()`), а не в байтах кириллицы (иначе перескок).
        let mut matched = false;
        for (pat, canon) in [
            ("жалоб", "жалоба"),
            ("доверенност", "доверенность"),
            ("контракт", "контракт"),
            ("соглашени", "соглашение"),
            ("протокол", "протокол"),
            ("лицензи", "лицензия"),
        ] {
            if starts_lower(&lower, i, pat) {
                let plen = pat.chars().count();
                out.push(TypeCandidate {
                    start: i,
                    end: i + plen,
                    canon: canon.into(),
                });
                i += plen;
                matched = true;
                break;
            }
        }
        if matched {
            continue;
        }
        i += 1;
    }
    out.sort_by_key(|c| c.start);
    out
}

fn type_end(text: &[char], from: usize) -> usize {
    let n = text.len();
    let lower: Vec<char> = text
        .iter()
        .map(|c| c.to_lowercase().next().unwrap_or(*c))
        .collect();
    let mut i = from;
    let mut last_word_end = from;
    while i < n {
        if lower[i] == '.' && (i + 1 >= n || !text[i + 1].is_ascii_digit()) {
            return i;
        }
        if i + 4 <= n && slice_eq(&lower, i, " от ") {
            return last_word_end;
        }
        if is_word(text[i]) {
            let _w0 = i;
            while i < n && is_word(text[i]) {
                i += 1;
            }
            last_word_end = i;
        } else if text[i].is_whitespace() {
            i += 1;
        } else {
            return last_word_end;
        }
    }
    last_word_end
}

fn fas_end(text: &[char], from: usize, n: usize) -> usize {
    let lower: Vec<char> = text
        .iter()
        .map(|c| c.to_lowercase().next().unwrap_or(*c))
        .collect();
    let mut i = from;
    let mut last = from;
    while i < n {
        if lower[i] == '.' || lower[i] == ',' || lower[i] == ';' {
            return last;
        }
        if i + 4 <= n && slice_eq(&lower, i, " от ") {
            return last;
        }
        if is_word(text[i]) {
            let w0 = i;
            while i < n && (is_word(text[i]) || text[i] == '-') {
                i += 1;
            }
            let w: String = text[w0..i].iter().collect();
            let wl = w.to_lowercase();
            if wl == "россии" || wl == "рф" || wl == "области" || wl == "края" || wl == "округа"
            {
                last = i;
            }
        } else {
            i += 1;
        }
    }
    last
}

fn canon_fas(span: &str, label: &str) -> String {
    let lower = span.to_lowercase();
    let region: String = if lower.contains("магаданск") {
        "Магаданского".into()
    } else if lower.contains("челябинск") {
        "Челябинского".into()
    } else if lower.contains("брянск") {
        "Брянского".into()
    } else if lower.contains("нижегородск") {
        "Нижегородского".into()
    } else if let Some(pos) = lower.find(" уфас") {
        span[..pos]
            .rsplit(' ')
            .find(|w| !w.is_empty())
            .unwrap_or("")
            .to_string()
    } else {
        String::new()
    };
    if region.is_empty() {
        format!("{} УФАС России", label)
    } else if lower.contains("уфас") {
        format!("{} {} УФАС России", label, region)
    } else {
        format!("{} ФАС России", label)
    }
}

/// Приклейка TYPE по `_type_for_span` прототипа: ближайший preceding TYPE,
/// отфильтрованный по date-crossing. Вход — канонический поток якорей S01
/// (occurrences + локальные byte spans), поэтому приклейка идёт по
/// `span.block`.
fn attach_types(paras: &[String], anchors: &[npa_anchor::Anchor]) -> Vec<TypedMember> {
    let mut out: Vec<TypedMember> = Vec::with_capacity(anchors.len());
    let mut idx = 0usize;

    for (block, para) in paras.iter().enumerate() {
        // якоря отсортированы по (block, start) — берём свою порцию блока
        let start_idx = idx;
        while idx < anchors.len() && anchors[idx].span.block == block {
            idx += 1;
        }
        if start_idx == idx {
            continue;
        }

        let chars: Vec<char> = para.chars().collect();
        let types = scan_types(&chars);

        // byte → char: префиксные байтовые смещения (границы code point
        // гарантированы `check_span` в producer'е).
        let mut offs: Vec<usize> = Vec::with_capacity(chars.len() + 1);
        let mut b = 0usize;
        for c in &chars {
            offs.push(b);
            b += c.len_utf8();
        }
        offs.push(b);
        let date_starts: Vec<usize> = (start_idx..idx)
            .map(|k| offs.partition_point(|&o| o < anchors[k].span.start))
            .collect();

        for (k, &d_start) in date_starts.iter().enumerate() {
            let a = &anchors[start_idx + k];
            // TYPE candidates before this date
            let before: Vec<&TypeCandidate> = types.iter().filter(|t| t.start <= d_start).collect();
            // date-crossing filter (intra-block). Reuse of a candidate crossed by an
            // intervening date is intra-block series-head inheritance, exactly as the
            // differential reference _type_for_span does (`if filtered: before = filtered`),
            // e.g. a list of Federal laws D1/D2/D3 in one sentence. Cross-block reuse is
            // structurally impossible because types/date_starts are built per block
            // (RC28-F07); silent-winner UX (RC28-F09) is addressed by the provenance
            // buffer in T02.
            let before: Vec<&TypeCandidate> = before;
            let survivors: Vec<&TypeCandidate> = if date_starts.is_empty() {
                before
            } else {
                let filtered: Vec<&TypeCandidate> = before
                    .iter()
                    .filter(|t| !date_starts.iter().any(|&ds| t.start < ds && ds < d_start))
                    .copied()
                    .collect();
                if filtered.is_empty() {
                    before
                } else {
                    filtered
                }
            };
            let winner = survivors.iter().max_by_key(|t| t.start).copied();
            let mut canon = winner.map(|t| t.canon.clone());
            // -ФЗ суффикс → Федеральный закон (Закон РФ override)
            if canon.as_deref() == Some("Закон РФ") && a.number.ends_with("-ФЗ") {
                canon = Some("Федеральный закон".to_string());
            }
            // Provenance победителя: byte-span головы в том же блоке.
            let type_evidence = winner.map(|t| LocalSpan {
                block,
                start: offs[t.start],
                end: offs[t.end],
            });
            // Буфер конкурирующих гипотез: все выжившие, кроме победителя.
            let alternatives: Vec<TypeHypothesis> = survivors
                .iter()
                .filter(|t| Some(t.start) != winner.map(|w| w.start))
                .map(|t| TypeHypothesis {
                    canon: t.canon.clone(),
                    evidence: LocalSpan {
                        block,
                        start: offs[t.start],
                        end: offs[t.end],
                    },
                })
                .collect();
            let unresolved = survivors.is_empty();
            let derivation = if unresolved {
                TypeDerivation::Unresolved
            } else {
                TypeDerivation::WrittenHere
            };
            // Occurrences не сливаются по `(date, number)`: каждая запись
            // несёт свой source-local byte span (M207 AMBIGUOUS_DUPLICATE).
            out.push(TypedMember {
                date: a.date.clone(),
                number: a.number.clone(),
                type_name: canon.unwrap_or_default(),
                approved_by: String::new(),
                span: a.span,
                derivation,
                type_evidence,
                alternatives,
                unresolved,
            });
        }
    }
    out
}

/// Единый producer: типизированный поток поверх канонических якорей S01.
/// Возвращает (`members`, `diagnostics`) — отказы guard'ов и duplicate
/// occurrences не проглатываются (та же семантика, что у `npa_anchor`).
pub fn scan_typed_diagnosed(paras: &[String]) -> (Vec<TypedMember>, Vec<AnchorDiagnostic>) {
    let (anchors, diagnostics) = npa_anchor::scan_anchors_diagnosed(paras);
    (attach_types(paras, &anchors), diagnostics)
}

/// Совместимый wrapper: типизированные члены без диагностик.
pub fn scan_typed(paras: &[String]) -> Vec<TypedMember> {
    scan_typed_diagnosed(paras).0
}
