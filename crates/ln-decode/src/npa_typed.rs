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

/// Типизированный член: нормализованная дата + номер + TYPE и локальный
/// byte-span якоря-вхождения (тот же поток, что S01; M207 `{fragment_id,
/// start, end}` shape без serde).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct TypedMember {
    pub date: String,
    pub number: String,
    pub type_name: String,
    pub approved_by: String,
    pub span: LocalSpan,
}

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
        // --- распоряжение Правительства / Президента ---
        if starts_lower(&lower, i, "распоряжен") {
            if contains_lower(&lower, i, "правительств") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "распоряжение Правительства РФ".into(),
                });
                i = e;
                continue;
            }
            if contains_lower(&lower, i, "президента") {
                let e = type_end(text, i);
                out.push(TypeCandidate {
                    start: i,
                    end: e,
                    canon: "Распоряжение Президента РФ".into(),
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
        for (pat, canon) in [
            ("жалоб", "жалоба"),
            ("доверенност", "доверенность"),
            ("контракт", "контракт"),
            ("соглашени", "соглашение"),
            ("протокол", "протокол"),
            ("лицензия", "лицензия"),
        ] {
            if starts_lower(&lower, i, pat) {
                out.push(TypeCandidate {
                    start: i,
                    end: i + pat.len(),
                    canon: canon.into(),
                });
                i += pat.len();
                break;
            }
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
            let mut before: Vec<&TypeCandidate> =
                types.iter().filter(|t| t.start <= d_start).collect();
            // date-crossing filter
            if !date_starts.is_empty() {
                let filtered: Vec<&TypeCandidate> = before
                    .iter()
                    .filter(|t| !date_starts.iter().any(|&ds| t.start < ds && ds < d_start))
                    .copied()
                    .collect();
                if !filtered.is_empty() {
                    before = filtered;
                }
            }
            let mut canon = before
                .iter()
                .max_by_key(|t| t.start)
                .map(|t| t.canon.clone());
            // -ФЗ суффикс → Федеральный закон (Закон РФ override)
            if canon.as_deref() == Some("Закон РФ") && a.number.ends_with("-ФЗ") {
                canon = Some("Федеральный закон".to_string());
            }
            // Occurrences не сливаются по `(date, number)`: каждая запись
            // несёт свой source-local byte span (M207 AMBIGUOUS_DUPLICATE).
            out.push(TypedMember {
                date: a.date.clone(),
                number: a.number.clone(),
                type_name: canon.unwrap_or_default(),
                approved_by: String::new(),
                span: a.span,
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
