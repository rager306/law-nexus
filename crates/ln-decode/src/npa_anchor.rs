//! NPA requisites anchors (M211 S01, ADR-0029).
//!
//! Дата+номер — якорь члена. Сканер воспроизводит семантику Python-прототипа
//! `scripts/m207_context_graph_demo.py` (executable spec):
//! - `OT_DATE`:  «от DD.MM.YYYY N NUM» | «от DD.MM.YYYY б/н»
//! - `OT_DUMA`:  «от D месяца YYYY г[ода|.][ ]N NUM»
//! - `INBOUND`:  «(вх. DD.MM.YYYY N NUM | (вх. N NUM от DD.MM.YYYY» — зона
//!   исключения [+0..+80) для якорей `OT_DATE`
//! - `MINJUST`:  «Зарегистрировано в Минюсте России …» — зона исключения для
//!   якорей `OT_DUMA`
//!
//! Никаких заявляемых identity здесь нет: якорь — это только реквизиты
//! (fail-closed; TYPE/эмитент приклеиваются более поздними проходами).

/// Корпусный корень по умолчанию (M185 S03 / D282: empty-as-unset).
pub const DEFAULT_EXPORT_DIR: &str = "consru_export";

/// `CONSULTANT_EXPORT_DIR` пуст-как-не-задан (M185 S03 pattern).
pub fn resolve_export_dir(env: Option<&str>) -> String {
    match env {
        Some(v) if !v.trim().is_empty() => v.trim().to_string(),
        _ => DEFAULT_EXPORT_DIR.to_string(),
    }
}

/// Якорь реквизитов: нормализованная дата + номер как написан.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Anchor {
    pub date: String,
    pub number: String,
}

/// Месяцы русского правописания (родительный падеж) -> номер месяца.
pub fn month_num(name: &str) -> Option<u8> {
    let lower = name.to_lowercase();
    let m = match lower.as_str() {
        "января" => 1,
        "февраля" => 2,
        "марта" => 3,
        "апреля" => 4,
        "мая" => 5,
        "июня" => 6,
        "июля" => 7,
        "августа" => 8,
        "сентября" => 9,
        "октября" => 10,
        "ноября" => 11,
        "декабря" => 12,
        _ => return None,
    };
    Some(m)
}

fn is_cyr(c: char) -> bool {
    matches!(c, 'А'..='я' | 'Ё' | 'ё')
}

/// Символ номера: класс прототипа `[0-9А-ЯA-Z]` под re.I
/// (латиница/кириллица в любом регистре + цифры).
fn is_num_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || is_cyr(c)
}

/// Читает `NUM` = `[0-9А-ЯA-Z]+(?:[./-][0-9А-ЯA-Z]+)*` с позиции `i`.
/// Возвращает (новая позиция, номер).
fn read_number(text: &[char], mut i: usize) -> Option<(usize, String)> {
    let start = i;
    while i < text.len() && is_num_char(text[i]) {
        i += 1;
    }
    if i == start {
        return None;
    }
    let mut end = i;
    // разделительные группы: [./-] + хотя бы один символ номера
    loop {
        let mut j = end;
        if j < text.len() && matches!(text[j], '.' | '/' | '-') {
            j += 1;
            let grp = j;
            while j < text.len() && is_num_char(text[j]) {
                j += 1;
            }
            if j > grp {
                end = j;
            } else {
                break;
            }
        } else {
            break;
        }
    }
    let num: String = text[start..end].iter().collect();
    Some((end, num))
}

/// Читает `DD.MM.YYYY` с позиции `i`. Возвращает (новая позиция, дата).
fn read_dot_date(text: &[char], i: usize) -> Option<(usize, String)> {
    let mut j = i;
    let mut parts: Vec<String> = Vec::new();
    for part_len in [2usize, 2, 4] {
        let start = j;
        while j < text.len() && text[j].is_ascii_digit() && j - start < part_len {
            j += 1;
        }
        if j - start != part_len {
            return None;
        }
        parts.push(text[start..j].iter().collect());
        if parts.len() < 3 {
            if j < text.len() && text[j] == '.' {
                j += 1;
            } else {
                return None;
            }
        }
    }
    Some((j, parts.join(".")))
}

/// `skip_ws` возвращает позицию первого не-whitespace символа от `i`.
fn skip_ws(text: &[char], mut i: usize) -> usize {
    while i < text.len() && text[i].is_whitespace() {
        i += 1;
    }
    i
}

/// Совпадает ли литерал с позиции `i` (без учёта регистра ASCII/кириллицы
/// не требуется: литералы латиницей/«N»/«б/н» проверяем как написано).
fn starts_with_lit(text: &[char], i: usize, lit: &str) -> bool {
    let lc: Vec<char> = lit.chars().collect();
    i + lc.len() <= text.len() && text[i..i + lc.len()] == lc[..]
}

pub struct OtDateHit {
    pub start: usize,
    pub end: usize,
    date: String,
    number: String,
}

/// `OT_DATE`: «от DD.MM.YYYY (N NUM | б/н)» с lookbehind-стражами «вх.».
fn scan_ot_date(text: &[char]) -> Vec<OtDateHit> {
    let mut hits = Vec::new();
    let n = text.len();
    let mut i = 0usize;
    while i + 2 < n {
        // литерал «от»
        if text[i] == 'о' && text[i + 1] == 'т' {
            let after = skip_ws(text, i + 2);
            if after > i + 2 {
                if let Some((dend, date)) = read_dot_date(text, after) {
                    let j = skip_ws(text, dend);
                    let mut number: Option<(usize, String)> = None;
                    if starts_with_lit(text, j, "б/н") {
                        number = Some((j + 3, "б/н".to_string()));
                    } else if j < n && (text[j] == 'N' || text[j] == 'n' || text[j] == '№') {
                        let k = skip_ws(text, j + 1);
                        if let Some((nend, num)) = read_number(text, k) {
                            number = Some((nend, num));
                        }
                    }
                    if let Some((nend, num)) = number {
                        // lookbehind: не «вх. » / «вх » непосредственно перед «от»
                        let lb_ok = {
                            let a = skip_ws_back(text, i);
                            !(a >= 1
                                && text[a - 1] == '.'
                                && a >= 3
                                && text[a - 3] == 'в'
                                && text[a - 2] == 'х')
                                && !(a >= 2
                                    && text[a - 2] == 'в'
                                    && text[a - 1] == 'х'
                                    && a < n
                                    && (text[a] == ' ' || text[a] == '\u{a0}'))
                        };
                        if lb_ok {
                            hits.push(OtDateHit {
                                start: i,
                                end: nend,
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
        i += 1;
    }
    hits
}

fn skip_ws_back(text: &[char], i: usize) -> usize {
    let mut a = i;
    while a > 0 && text[a - 1].is_whitespace() {
        a -= 1;
    }
    a
}

struct DumaHit {
    start: usize,
    date: String,
    number: String,
}

/// `OT_DUMA`: «от D месяца YYYY г[ода|.] N NUM» (месяц словом).
fn scan_ot_duma(text: &[char]) -> Vec<DumaHit> {
    let mut hits = Vec::new();
    let n = text.len();
    let mut i = 0usize;
    while i + 2 < n {
        if text[i] == 'о' && text[i + 1] == 'т' {
            let after = skip_ws(text, i + 2);
            if after > i + 2 {
                // день: 1-2 цифры
                let d0 = after;
                let mut d1 = d0;
                while d1 < n && text[d1].is_ascii_digit() && d1 - d0 < 2 {
                    d1 += 1;
                }
                if d1 > d0 {
                    let m0 = skip_ws(text, d1);
                    if m0 > d1 {
                        // месяц словом (кириллица)
                        let mw0 = m0;
                        let mut mw1 = mw0;
                        while mw1 < n && is_cyr(text[mw1]) {
                            mw1 += 1;
                        }
                        if mw1 > mw0 {
                            let month: String = text[mw0..mw1].iter().collect();
                            if let Some(mm) = month_num(&month) {
                                let y0 = skip_ws(text, mw1);
                                if y0 > mw1 {
                                    let mut y1 = y0;
                                    while y1 < n && text[y1].is_ascii_digit() && y1 - y0 < 4 {
                                        y1 += 1;
                                    }
                                    if y1 - y0 == 4 {
                                        // «года» | «г.»
                                        let g0 = skip_ws(text, y1);
                                        let (gend, ok) = if starts_with_lit(text, g0, "года") {
                                            (g0 + 4, true)
                                        } else if g0 < n && text[g0] == 'г' {
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
                                            if j < n && (text[j] == 'N' || text[j] == 'n') {
                                                let k = skip_ws(text, j + 1);
                                                if let Some((nend, num)) = read_number(text, k) {
                                                    hits.push(DumaHit {
                                                        start: i,
                                                        date: format!(
                                                            "{:02}.{:02}.{}",
                                                            text[d0..d1]
                                                                .iter()
                                                                .collect::<String>()
                                                                .parse::<u32>()
                                                                .unwrap_or(0),
                                                            mm,
                                                            text[y0..y1].iter().collect::<String>()
                                                        ),
                                                        number: num,
                                                    });
                                                    i = nend.max(gend);
                                                    continue;
                                                }
                                            }
                                        }
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

struct InboundZone {
    start: usize,
}

/// `INBOUND`: «(вх. DD.MM.YYYY N NUM | (вх. N NUM от DD.MM.YYYY».
fn scan_inbound(text: &[char]) -> Vec<InboundZone> {
    let mut zones = Vec::new();
    let n = text.len();
    let mut i = 0usize;
    while i + 1 < n {
        if text[i] == '(' {
            let j = skip_ws(text, i + 1);
            if j + 2 < n && text[j] == 'в' && text[j + 1] == 'х' && text[j + 2] == '.' {
                let k = skip_ws(text, j + 3);
                // форма 1: от DD.MM.YYYY N NUM
                if starts_with_lit(text, k, "от") {
                    let a = skip_ws(text, k + 2);
                    if let Some((dend, _)) = read_dot_date(text, a) {
                        let b = skip_ws(text, dend);
                        if b < n && (text[b] == 'N' || text[b] == 'n') {
                            let c = skip_ws(text, b + 1);
                            if let Some((_, _)) = read_number(text, c) {
                                zones.push(InboundZone { start: i });
                                i += 1;
                                continue;
                            }
                        }
                    }
                } else {
                    // форма 2: N NUM от DD.MM.YYYY
                    if text[k] == 'N' || text[k] == 'n' {
                        let a = skip_ws(text, k + 1);
                        if let Some((nend, _)) = read_number(text, a) {
                            let b = skip_ws(text, nend);
                            if starts_with_lit(text, b, "от") {
                                let c = skip_ws(text, b + 2);
                                if read_dot_date(text, c).is_some() {
                                    zones.push(InboundZone { start: i });
                                    i += 1;
                                    continue;
                                }
                            }
                        }
                    }
                }
            }
        }
        i += 1;
    }
    zones
}

struct MinjustSpan {
    start: usize,
    end: usize,
}

/// `MINJUST`: «Зарегистрировано в Минюсте России (DD.MM.YYYY | D month YYYY г[ода|.]) N NUM».
fn scan_minjust(text: &[char]) -> Vec<MinjustSpan> {
    let mut spans = Vec::new();
    let lit: Vec<char> = "Зарегистрировано в Минюсте России".chars().collect();
    let n = text.len();
    let mut i = 0usize;
    'outer: while i + lit.len() <= n {
        if text[i..i + lit.len()].eq_ignore_case(&lit) {
            let mut j = skip_ws(text, i + lit.len());
            // форма 1: DD.MM.YYYY
            if let Some((dend, _)) = read_dot_date(text, j) {
                j = skip_ws(text, dend);
            } else {
                // форма 2: D month YYYY г[ода|.]
                let d0 = j;
                let mut d1 = d0;
                while d1 < n && text[d1].is_ascii_digit() && d1 - d0 < 2 {
                    d1 += 1;
                }
                if d1 == d0 {
                    i += 1;
                    continue;
                }
                let m0 = skip_ws(text, d1);
                let mut mw1 = m0;
                while mw1 < n && is_cyr(text[mw1]) {
                    mw1 += 1;
                }
                if mw1 == m0 {
                    i += 1;
                    continue;
                }
                let month: String = text[m0..mw1].iter().collect();
                if month_num(&month).is_none() {
                    i += 1;
                    continue;
                }
                let y0 = skip_ws(text, mw1);
                let mut y1 = y0;
                while y1 < n && text[y1].is_ascii_digit() && y1 - y0 < 4 {
                    y1 += 1;
                }
                if y1 - y0 != 4 {
                    i += 1;
                    continue;
                }
                j = skip_ws(text, y1);
                if starts_with_lit(text, j, "года") {
                    j += 4;
                } else if j < n && text[j] == 'г' {
                    j += if j + 1 < n && text[j + 1] == '.' {
                        2
                    } else {
                        1
                    };
                }
            }
            if j < n && (text[j] == 'N' || text[j] == 'n') {
                let k = skip_ws(text, j + 1);
                let mut e = k;
                while e < n && (text[e].is_ascii_digit()) {
                    e += 1;
                }
                if e > k {
                    spans.push(MinjustSpan { start: i, end: e });
                    i = e;
                    continue 'outer;
                }
            }
        }
        i += 1;
    }
    spans
}

trait EqIgnoreCase {
    fn eq_ignore_case(&self, other: &[char]) -> bool;
}

impl EqIgnoreCase for [char] {
    fn eq_ignore_case(&self, other: &[char]) -> bool {
        self.len() == other.len()
            && self
                .iter()
                .zip(other)
                .all(|(a, b)| a.to_lowercase().eq(b.to_lowercase()))
    }
}

/// Минимальный декодер consultant w:t (прототип `_decode_consultant_text`):
/// HTML-энтити, `{КонсультантПлюс}` вырезается, переводы строк схлопываются.
pub fn decode_consultant_text(s: &str) -> String {
    let chars: Vec<char> = s.chars().collect();
    let mut decoded = String::with_capacity(s.len());
    let mut i = 0usize;
    while i < chars.len() {
        if chars[i] == '&' {
            let mut handled = false;
            for (name, rep) in [
                ("amp", '&'),
                ("lt", '<'),
                ("gt", '>'),
                ("quot", '"'),
                ("apos", '\''),
                ("nbsp", '\u{a0}'),
            ] {
                let nc: Vec<char> = name.chars().collect();
                if chars[i + 1..].starts_with(&nc[..])
                    && i + 1 + nc.len() < chars.len()
                    && chars[i + 1 + nc.len()] == ';'
                {
                    decoded.push(rep);
                    i += 1 + nc.len() + 1;
                    handled = true;
                    break;
                }
            }
            if handled {
                continue;
            }
            if i + 1 < chars.len() && chars[i + 1] == '#' {
                let hex = i + 2 < chars.len() && (chars[i + 2] == 'x' || chars[i + 2] == 'X');
                let dstart = if hex { i + 3 } else { i + 2 };
                let mut e = dstart;
                while e < chars.len()
                    && (if hex {
                        chars[e].is_ascii_hexdigit()
                    } else {
                        chars[e].is_ascii_digit()
                    })
                {
                    e += 1;
                }
                if e < chars.len() && chars[e] == ';' && e > dstart {
                    let digits: String = chars[dstart..e].iter().collect();
                    if let Ok(cp) = u32::from_str_radix(&digits, if hex { 16 } else { 10 }) {
                        if let Some(ch) = char::from_u32(cp) {
                            decoded.push(ch);
                            i = e + 1;
                            continue;
                        }
                    }
                }
            }
        }
        decoded.push(chars[i]);
        i += 1;
    }
    let no_brand = decoded.replace("{КонсультантПлюс}", "");
    no_brand.split_whitespace().collect::<Vec<&str>>().join(" ")
}

/// Абзацы Consultant WordML: `w:p`-блоки, конкатенация `w:t`, декод текста.
/// Воспроизводит `_xml_para_bodies` прототипа (тело используется для hlink —
/// здесь достаточно текста).
pub fn extract_paragraphs(xml: &str) -> Vec<String> {
    let chars: Vec<char> = xml.chars().collect();
    let mut paras = Vec::new();
    let mut i = 0usize;
    while i + 4 <= chars.len() {
        if chars[i] == '<'
            && chars[i + 1] == 'w'
            && chars[i + 2] == ':'
            && chars[i + 3] == 'p'
            && (i + 4 == chars.len() || chars[i + 4].is_whitespace() || chars[i + 4] == '>')
        {
            // конец открывающего тега
            let mut j = i + 4;
            while j < chars.len() && chars[j] != '>' {
                j += 1;
            }
            if j >= chars.len() {
                break;
            }
            let body_start = j + 1;
            // </w:p>
            let mut e = body_start;
            let mut body_end = chars.len();
            while e + 6 <= chars.len() {
                if chars[e] == '<'
                    && chars[e + 1] == '/'
                    && chars[e + 2] == 'w'
                    && chars[e + 3] == ':'
                    && chars[e + 4] == 'p'
                    && chars[e + 5] == '>'
                {
                    body_end = e;
                    break;
                }
                e += 1;
            }
            // конкатенация w:t внутри body
            let mut text = String::new();
            let mut k = body_start;
            while k + 4 <= body_end {
                if chars[k] == '<'
                    && chars[k + 1] == 'w'
                    && chars[k + 2] == ':'
                    && chars[k + 3] == 't'
                    && (k + 4 == body_end || chars[k + 4] == '>' || chars[k + 4].is_whitespace())
                {
                    let mut m = k + 4;
                    while m < body_end && chars[m] != '>' {
                        m += 1;
                    }
                    let tstart = m + 1;
                    let mut t = tstart;
                    while t < body_end && chars[t] != '<' {
                        t += 1;
                    }
                    if t > tstart {
                        text.extend(chars[tstart..t].iter());
                    }
                    k = t;
                } else {
                    k += 1;
                }
            }
            paras.push(decode_consultant_text(&text));
            i = body_end + 6;
        } else {
            i += 1;
        }
    }
    paras
}

/// Скан якорей по абзацам: OT_DATE + OT_DUMA, guard'ы INBOUND/MINJUST,
/// дедуп + сортировка (множество (дата, номер)).
pub fn scan_anchors(paras: &[String]) -> Vec<Anchor> {
    let mut set: std::collections::BTreeSet<Anchor> = std::collections::BTreeSet::new();
    for para in paras {
        let chars: Vec<char> = para.chars().collect();
        let inbound = scan_inbound(&chars);
        let minjust = scan_minjust(&chars);
        let ot_dates = scan_ot_date(&chars);
        for h in &ot_dates {
            if inbound
                .iter()
                .any(|z| z.start <= h.start && h.start < z.start + 80)
            {
                continue;
            }
            set.insert(Anchor {
                date: h.date.clone(),
                number: h.number.clone(),
            });
        }
        for h in scan_ot_duma(&chars) {
            if inbound
                .iter()
                .any(|z| z.start <= h.start && h.start < z.start + 80)
            {
                continue;
            }
            if minjust
                .iter()
                .any(|s| s.start <= h.start && h.start < s.end)
            {
                continue;
            }
            if ot_dates
                .iter()
                .any(|o| (o.start as i64 - h.start as i64).abs() < 8)
            {
                continue;
            }
            set.insert(Anchor {
                date: h.date.clone(),
                number: h.number.clone(),
            });
        }
    }
    set.into_iter().collect()
}

#[cfg(test)]
mod tests {

    use super::*;

    #[test]
    fn debug_scan_literal() {
        let s = "(п. 2.1 введен Федеральным законом от 02.07.2021 N 351-ФЗ)";
        let chars: Vec<char> = s.chars().collect();
        let od = scan_ot_date(&chars);
        eprintln!("ot_date hits: {}", od.len());
        for h in &od {
            eprintln!("  {} N {}", h.date, h.number);
        }
        let paras = vec![s.to_string()];
        let anchors = scan_anchors(&paras);
        eprintln!("anchors: {:?}", anchors);
        assert_eq!(od.len(), 1);
        assert_eq!(anchors.len(), 1);
    }
}
