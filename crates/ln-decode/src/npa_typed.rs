//! NPA typed members (M211 S02, ADR-0029).
//!
//! TYPE-кандидаты сканируются в тексте, приклейка — `_type_for_span`
//! прототипа: ближайший preceding TYPE без TYPE за другим якорем.

/// Типизированный член.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct TypedMember {
    pub date: String,
    pub number: String,
    pub type_name: String,
}

pub struct TypeCandidate {
    pub start: usize,
    pub end: usize,
    pub canon: String,
}

pub struct DateHit {
    pub start: usize,
    pub date: String,
    pub number: String,
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

fn is_num_start(c: char) -> bool {
    c.is_ascii_alphanumeric() || is_cyr(c)
}

fn read_num(text: &[char], mut i: usize) -> (usize, String) {
    let s = i;
    while i < text.len() && (is_num_start(text[i])) {
        i += 1;
    }
    let mut end = i;
    loop {
        if end < text.len() && matches!(text[end], '.' | '/' | '-') {
            let g0 = end + 1;
            let mut g = g0;
            while g < text.len() && is_num_start(text[g]) {
                g += 1;
            }
            if g > g0 {
                end = g;
            } else {
                break;
            }
        } else {
            break;
        }
    }
    (end, text[s..end].iter().collect())
}

fn read_dot_date(text: &[char], mut i: usize) -> Option<(usize, String)> {
    let mut parts = Vec::new();
    for len in [2usize, 2, 4] {
        let s = i;
        while i < text.len() && text[i].is_ascii_digit() && i - s < len {
            i += 1;
        }
        if i - s != len {
            return None;
        }
        parts.push(text[s..i].iter().collect::<String>());
        if parts.len() < 3 {
            if i < text.len() && text[i] == '.' {
                i += 1;
            } else {
                return None;
            }
        }
    }
    Some((i, parts.join(".")))
}

fn month_num(name: &str) -> Option<u8> {
    match name {
        "января" => Some(1),
        "февраля" => Some(2),
        "марта" => Some(3),
        "апреля" => Some(4),
        "мая" => Some(5),
        "июня" => Some(6),
        "июля" => Some(7),
        "августа" => Some(8),
        "сентября" => Some(9),
        "октября" => Some(10),
        "ноября" => Some(11),
        "декабря" => Some(12),
        _ => None,
    }
}

/// Скан всех дат (OT_DATE + OT_DUMA) в абзаце.
pub fn scan_dates(text: &[char]) -> Vec<DateHit> {
    let n = text.len();
    let lower: Vec<char> = text
        .iter()
        .map(|c| c.to_lowercase().next().unwrap_or(*c))
        .collect();
    let mut hits = Vec::new();
    let mut i = 0usize;
    while i < n {
        // OT_DATE: от DD.MM.YYYY (N NUM | б/н)
        if starts_lower(&lower, i, "от ") {
            let d0 = skip_ws(text, i + 2);
            if let Some((dend, date)) = read_dot_date(text, d0) {
                let j = skip_ws(text, dend);
                if j < n && (lower[j] == 'n' || text[j] == '№') {
                    let k = skip_ws(text, j + 1);
                    let (nend, num) = read_num(text, k);
                    if nend > k {
                        hits.push(DateHit {
                            start: i,
                            date,
                            number: num,
                        });
                        i = nend;
                        continue;
                    }
                }
            }
        }
        // OT_DUMA: от D месяца YYYY г[ода|.] N NUM
        if starts_lower(&lower, i, "от ") {
            let d0 = skip_ws(text, i + 2);
            let mut d1 = d0;
            while d1 < n && text[d1].is_ascii_digit() && d1 - d0 < 2 {
                d1 += 1;
            }
            if d1 > d0 {
                let m0 = skip_ws(text, d1);
                let mut m1 = m0;
                while m1 < n && is_cyr(text[m1]) {
                    m1 += 1;
                }
                if m1 > m0 {
                    let mon: String = text[m0..m1].iter().collect();
                    if let Some(mm) = month_num(&mon) {
                        let y0 = skip_ws(text, m1);
                        let mut y1 = y0;
                        while y1 < n && text[y1].is_ascii_digit() && y1 - y0 < 4 {
                            y1 += 1;
                        }
                        if y1 - y0 == 4 {
                            let g0 = skip_ws(text, y1);
                            let (gend, ok) = if g0 + 4 <= n && slice_eq(&lower, g0, "года") {
                                (g0 + 4, true)
                            } else if g0 < n && lower[g0] == 'г' {
                                if g0 + 1 < n && text[g0 + 1] == '.' {
                                    (g0 + 2, true)
                                } else {
                                    (g0 + 1, true)
                                }
                            } else {
                                (g0, false)
                            };
                            if ok {
                                let j = skip_ws(text, gend);
                                if j < n && lower[j] == 'n' {
                                    let k = skip_ws(text, j + 1);
                                    let (nend, num) = read_num(text, k);
                                    if nend > k {
                                        let day: String = text[d0..d1].iter().collect();
                                        let year: String = text[y0..y1].iter().collect();
                                        let date = format!(
                                            "{:02}.{:02}.{}",
                                            day.parse::<u32>().unwrap_or(0),
                                            mm,
                                            year
                                        );
                                        hits.push(DateHit {
                                            start: i,
                                            date,
                                            number: num,
                                        });
                                        i = nend;
                                        continue;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        i += 1;
    }
    hits
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

/// Приклейка TYPE по `_type_for_span` прототипа:
/// ближайший preceding TYPE, отфильтрованный по date-crossing.
pub fn scan_typed(paras: &[String]) -> Vec<TypedMember> {
    let mut out: Vec<TypedMember> = Vec::new();
    let mut seen: std::collections::BTreeMap<(String, String), usize> =
        std::collections::BTreeMap::new();

    for para in paras {
        let chars: Vec<char> = para.chars().collect();
        let dates = scan_dates(&chars);
        let types = scan_types(&chars);
        let date_starts: Vec<usize> = dates.iter().map(|d| d.start).collect();

        for d in &dates {
            // TYPE candidates before this date
            let mut before: Vec<&TypeCandidate> =
                types.iter().filter(|t| t.start <= d.start).collect();
            // date-crossing filter
            if !date_starts.is_empty() {
                let filtered: Vec<&TypeCandidate> = before
                    .iter()
                    .filter(|t| !date_starts.iter().any(|&ds| t.start < ds && ds < d.start))
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
            if canon.as_deref() == Some("Закон РФ") && d.number.ends_with("-ФЗ") {
                canon = Some("Федеральный закон".to_string());
            }
            let key = (d.date.clone(), d.number.clone());
            match seen.get(&key) {
                None => {
                    seen.insert(key.clone(), out.len());
                    out.push(TypedMember {
                        date: d.date.clone(),
                        number: d.number.clone(),
                        type_name: canon.unwrap_or_default(),
                    });
                }
                Some(&j) => {
                    if let Some(c) = canon {
                        if out[j].type_name.is_empty() {
                            out[j].type_name = c;
                        }
                    }
                }
            }
        }
    }
    out
}
