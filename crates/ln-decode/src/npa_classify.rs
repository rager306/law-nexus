//! NPA form classification (axis A) — std-only.
//!
//! Port of the executable Python differential reference in
//! `scripts/m207_context_graph_demo.py` (`classify_type`, `stem_kind`,
//! `lemma_match`, and the `act_type_lemmas` block of the frozen
//! `prd/architecture/npa-identifying-cycle.yaml`). D602: this module has no
//! serialization, filesystem, environment, or child-process dependencies. All
//! vocabulary lives in `const` tables, not runtime configuration.
//!
//! Axis A answers only *what a TYPE surface names*. Axes B..H and the
//! four-valued graph class are layered on top later; [`FormGraph`] here is the
//! internal form hint (`Undecided` for closed-dictionary forms).

/// Python `_INFLECT`: accepted suffix residuals for inflection matching.
/// `"ание"` is deliberately absent, so `"указ"` must not match `"указание"`.
const INFLECT: &[&str] = &[
    "", "а", "у", "е", "ом", "ем", "ов", "ам", "ами", "ах", "ы", "и", "й", "я", "ю", "ей", "ий",
    "ие", "ия", "ием", "иям", "иями", "иях", "ое", "ая", "ые", "ого", "ому", "ым", "ых", "ыми",
];

/// Python `_STEMS` (declaration order; equal-length ties keep this order).
const STEMS: &[&str] = &[
    "постановление",
    "распоряжение",
    "доверенность",
    "соглашение",
    "извещение",
    "указание",
    "лицензия",
    "положение",
    "контракт",
    "протокол",
    "приказ",
    "письмо",
    "жалоба",
    "кодекс",
    "коап",
    "апк",
    "указ",
    "закон",
];

/// Python `_STEM_ALIAS`.
const STEM_ALIAS: &[(&str, &str)] = &[
    ("коап", "кодекс"),
    ("апк", "кодекс"),
    ("гпк", "кодекс"),
    ("упк", "кодекс"),
    ("кас", "кодекс"),
    ("уик", "кодекс"),
    ("гк", "кодекс"),
    ("ук", "кодекс"),
    ("нк", "кодекс"),
    ("бк", "кодекс"),
    ("зк", "кодекс"),
    ("жк", "кодекс"),
    ("ск", "кодекс"),
    ("лк", "кодекс"),
];

/// Python `CODE_ABBREV` (acronym, canonical, full name). The full name is
/// kept as data for the axis layer even though the form pass only needs the
/// acronym and canonical spelling.
const CODE_ABBREV: &[(&str, &str, &str)] = &[
    (
        "КОАП",
        "КоАП РФ",
        "Кодекс об административных правонарушениях",
    ),
    ("АПК", "АПК РФ", "Арбитражный процессуальный кодекс"),
    ("ГПК", "ГПК РФ", "Гражданский процессуальный кодекс"),
    ("УПК", "УПК РФ", "Уголовно-процессуальный кодекс"),
    ("КАС", "КАС РФ", "Кодекс административного судопроизводства"),
    (
        "УИК",
        "Уголовно-исполнительный кодекс",
        "Уголовно-исполнительный кодекс",
    ),
    ("ГК", "Гражданский кодекс", "Гражданский кодекс"),
    ("УК", "Уголовный кодекс", "Уголовный кодекс"),
    ("НК", "НК РФ", "Налоговый кодекс"),
    ("БК", "БК РФ", "Бюджетный кодекс"),
    ("ЗК", "ЗК РФ", "Земельный кодекс"),
    ("ЖК", "ЖК РФ", "Жилищный кодекс"),
    ("СК", "СК РФ", "Семейный кодекс"),
    ("ЛК", "ЛК РФ", "Лесной кодекс"),
];

/// Python lexicon `skip_as_type`.
const SKIP_AS_TYPE: &[&str] = &["извещение", "лот", "заявка"];

/// Python lexicon `instrument`.
const INSTRUMENT: &[&str] = &[
    "доверенность",
    "лицензии",
    "лицензия",
    "протокол",
    "протоколом",
    "жалоба",
    "жалобу",
    "соглашение",
    "контракт",
    "контракту",
];

/// Python lexicon `named`.
const NAMED: &[&str] = &["положение", "положением", "правил", "правилами"];

/// Python lexicon identifying buckets, in `npa-identifying-cycle.yaml` order.
const IDENTIFYING: &[(&str, &str)] = &[
    ("закон", "federal"),
    ("федерального", "federal"),
    ("федеральным", "federal"),
    ("кодекс", "federal"),
    ("основы", "federal"),
    ("указ", "presidential"),
    ("постановление", "government"),
    ("постановлений", "government"),
    ("распоряжение", "government"),
    ("распоряжения", "government"),
    ("приказ", "agency"),
    ("приказа", "agency"),
    ("письмо", "agency"),
    ("письмом", "agency"),
    ("указание", "agency"),
    ("постановления", "court"),
];

/// Prefixes of full codex names (Python `stem_kind` regex alternation).
const CODEX_PREFIXES: &[&str] = &[
    "трудов",
    "таможенн",
    "гражданск",
    "уголовно-исполнительн",
    "уголовно-процессуальн",
    "уголовн",
    "арбитражн",
    "налогов",
    "бюджетн",
    "земельн",
    "жилищн",
    "семейн",
    "лесн",
];

const WHY_TYPE_MISSING: &str =
    "нет типа — ребро в граф актов не строим (иначе появится узел «неизвестно N 446»)";
const WHY_UNKNOWN_KIND: &str = "вида нет в словаре — не выдумываем узел графа";
const WHY_NOT_AN_ACT: &str = "извещение/лот/заявка — не идентифицирующий акт, в граф НПА не кладём";
const WHY_INSTRUMENT: &str =
    "доверенность/жалоба/контракт — документ, но не НПА; ребро «цитирует акт» было бы ложным";
const WHY_NAMED: &str =
    "положение/правила — часто приложение, не отдельный идентифицирующий акт без издателя";
const WHY_DOCUMENTACIYA: &str =
    "конкурсная документация — named annex утверждающего приказа, не отдельный акт и не TYPE приказа";
const WHY_REKOMENDACII: &str =
    "методические рекомендации — named annex утверждающего приказа, свой DATE+N нет";
const WHY_REGLEMENT: &str =
    "регламент торговой площадки — named annex; корпоративный гендиректор ≠ ФОИВ";
const WHY_PERECHEN_PORYADOK: &str =
    "перечень/порядок — named annex утверждающего указа/распоряжения, свой DATE+N нет";

/// Internal form-plane graph hint. The public four-valued graph class
/// (`IdentifyingAct | Hold | Overlay | Refuse`) is layered on top later.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormGraph {
    Refuse,
    Hold,
    Undecided,
}

impl FormGraph {
    pub fn as_str(self) -> &'static str {
        match self {
            FormGraph::Refuse => "refuse",
            FormGraph::Hold => "hold",
            FormGraph::Undecided => "undecided",
        }
    }
}

/// Form-axis verdict (Python `classify_type`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormVerdict {
    TypeMissing,
    UnknownKind,
    NotAnAct,
    InstrumentNotNpa,
    NamedAnnex,
    FormInDictionary,
}

impl FormVerdict {
    pub fn as_str(self) -> &'static str {
        match self {
            FormVerdict::TypeMissing => "type_missing",
            FormVerdict::UnknownKind => "unknown_kind",
            FormVerdict::NotAnAct => "not_an_act",
            FormVerdict::InstrumentNotNpa => "instrument_not_npa",
            FormVerdict::NamedAnnex => "named_annex",
            FormVerdict::FormInDictionary => "form_in_dictionary",
        }
    }
}

/// Form bucket. `Identifying` carries the closed identifying family
/// (`federal`/`presidential`/`government`/`agency`/`court`) so `as_str()`
/// reproduces the Python reference `bucket` field exactly; the family is
/// needed again when axes B..H decide the graph class.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormBucket {
    SkipAsType,
    Instrument,
    Named,
    Identifying(&'static str),
    Unknown,
    Empty,
}

impl FormBucket {
    pub fn as_str(self) -> &'static str {
        match self {
            FormBucket::SkipAsType => "skip_as_type",
            FormBucket::Instrument => "instrument",
            FormBucket::Named => "named",
            FormBucket::Identifying(family) => family,
            FormBucket::Unknown => "unknown",
            FormBucket::Empty => "",
        }
    }
}

/// Result of form classification (axis A only; body-independent).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FormClassification {
    pub lemma: String,
    pub bucket: FormBucket,
    pub verdict: FormVerdict,
    pub graph: FormGraph,
    pub why: &'static str,
}

/// Python `str.casefold()` is approximated by `str::to_lowercase()`. For the
/// bounded Cyrillic/ASCII legal vocabulary of the frozen reference the two
/// agree; this is a documented port boundary, not a general Unicode claim.
fn fold(value: &str) -> String {
    value.to_lowercase()
}

/// Python `re.sub(r"\s+", " ", canon).strip().casefold()`.
fn collapse_and_fold(value: &str) -> String {
    value
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
}

fn stem_alias(key: &str) -> Option<&'static str> {
    STEM_ALIAS
        .iter()
        .find(|(stem, _)| *stem == key)
        .map(|(_, alias)| *alias)
}

/// Exact or inflected match; never a substring match. `"указ"` must not match
/// `"указание"` (`"ание"` is not an accepted inflectional residual).
pub fn lemma_match(written: &str, key: &str) -> bool {
    let a = fold(written);
    let b = fold(key);
    if a == b {
        return true;
    }
    if let Some(rest) = a.strip_prefix(&b) {
        if INFLECT.contains(&rest) {
            return true;
        }
    }
    if let Some(rest) = b.strip_prefix(&a) {
        if INFLECT.contains(&rest) {
            return true;
        }
    }
    false
}

/// `prefix` followed by zero or more word characters, then at least one
/// whitespace, then `tail`. Equivalent to Python `re.search(prefix + r"\w*\s+" + tail)`.
fn word_prefix_then(haystack: &str, prefix: &str, tail: &str) -> bool {
    let mut search_from = 0usize;
    while let Some(relative) = haystack[search_from..].find(prefix) {
        let start = search_from + relative;
        let after = &haystack[start + prefix.len()..];
        let word_end = after
            .find(|c: char| !(c.is_alphanumeric() || c == '_'))
            .unwrap_or(after.len());
        let rest = &after[word_end..];
        let ws_end = rest
            .find(|c: char| !c.is_whitespace())
            .unwrap_or(rest.len());
        if ws_end > 0 && rest[ws_end..].starts_with(tail) {
            return true;
        }
        search_from = start + prefix.len();
        if search_from >= haystack.len() {
            break;
        }
    }
    false
}

/// Python `stem_kind` codex regex: a full codex name carries a stem ending in
/// `кодекс`, or contains `процессуальн` next to `кодекс`.
fn is_codex_full_name(folded: &str) -> bool {
    if CODEX_PREFIXES
        .iter()
        .any(|prefix| word_prefix_then(folded, prefix, "кодекс"))
    {
        return true;
    }
    folded.contains("процессуальн") && folded.contains("кодекс")
}

/// Python `stem_kind`. Returns the normalized kind lemma.
pub fn stem_kind(canon: &str) -> String {
    let folded = collapse_and_fold(canon);
    if folded.is_empty() {
        return String::new();
    }
    if folded.starts_with("федеральн") {
        return "закон".to_string();
    }
    if is_codex_full_name(&folded) {
        return "кодекс".to_string();
    }
    if matches!(folded.as_str(), "тк" | "тк рф" | "вк" | "вк рф") {
        // Homograph: bare ТК/ВК is not a codex without the full name (D517).
        return "тк".to_string();
    }
    for (acronym, _canonical, _full) in CODE_ABBREV.iter().copied() {
        let stem = fold(acronym);
        if folded == stem
            || folded.starts_with(&format!("{stem} "))
            || folded.starts_with(&format!("{stem}рф"))
            || folded == format!("{stem} рф")
        {
            return "кодекс".to_string();
        }
    }
    if CODE_ABBREV
        .iter()
        .any(|(_, canonical, _)| fold(canonical) == folded)
    {
        return "кодекс".to_string();
    }
    let first = folded.split(' ').next().unwrap_or("");
    let mut order: Vec<&str> = STEMS.to_vec();
    order.sort_by_key(|key| std::cmp::Reverse(key.chars().count()));
    for key in order {
        if lemma_match(first, key) {
            return stem_alias(key).unwrap_or(key).to_string();
        }
    }
    first.to_string()
}

#[derive(Debug, Clone, Copy)]
enum Family {
    Skip,
    Instrument,
    Named,
    Identifying(&'static str),
}

#[derive(Debug, Clone, Copy)]
struct Candidate {
    exact: u8,
    len: usize,
    family: Family,
    key: &'static str,
}

fn push_candidates(out: &mut Vec<Candidate>, folded: &str, keys: &[&'static str], family: Family) {
    for key in keys {
        if lemma_match(folded, key) {
            out.push(Candidate {
                exact: u8::from(folded == *key),
                len: key.chars().count(),
                family,
                key,
            });
        }
    }
}

fn named_annex(lemma: &str, why: &'static str) -> FormClassification {
    FormClassification {
        lemma: lemma.to_string(),
        bucket: FormBucket::Named,
        verdict: FormVerdict::NamedAnnex,
        graph: FormGraph::Hold,
        why,
    }
}

/// Hardcoded named-annex branches from Python `classify_type` that fire before
/// the dictionary candidate scan.
fn hardcoded_named(lemma_folded: &str, canon_folded: &str) -> Option<FormClassification> {
    if lemma_folded.contains("документац")
        || word_prefix_then(canon_folded, "конкурсн", "документац")
    {
        return Some(named_annex("документация", WHY_DOCUMENTACIYA));
    }
    if lemma_folded.contains("рекомендац") || canon_folded.contains("рекомендац")
    {
        return Some(named_annex("рекомендации", WHY_REKOMENDACII));
    }
    if lemma_folded.starts_with("регламент") {
        return Some(named_annex("регламент", WHY_REGLEMENT));
    }
    if lemma_folded.starts_with("переч") {
        return Some(named_annex("перечень", WHY_PERECHEN_PORYADOK));
    }
    if lemma_folded.starts_with("поряд") {
        return Some(named_annex("порядок", WHY_PERECHEN_PORYADOK));
    }
    None
}

fn identifying_why(family: &'static str) -> &'static str {
    match family {
        "federal" => "форма из закрытого списка (federal); класс ещё не решён",
        "presidential" => "форма из закрытого списка (presidential); класс ещё не решён",
        "government" => "форма из закрытого списка (government); класс ещё не решён",
        "agency" => "форма из закрытого списка (agency); класс ещё не решён",
        "court" => "форма из закрытого списка (court); класс ещё не решён",
        _ => "форма из закрытого списка; класс ещё не решён",
    }
}

/// Classify the TYPE surface along axis A. Total and fail-closed: an empty
/// (or whitespace-only) canon is `TypeMissing`/`Refuse`, an off-dictionary
/// kind is `UnknownKind`/`Refuse`. Never panics.
pub fn classify_form(canon: &str) -> FormClassification {
    let folded_all = collapse_and_fold(canon);
    if folded_all.is_empty() {
        return FormClassification {
            lemma: String::new(),
            bucket: FormBucket::Empty,
            verdict: FormVerdict::TypeMissing,
            graph: FormGraph::Refuse,
            why: WHY_TYPE_MISSING,
        };
    }

    let lemma = stem_kind(canon);
    let lemma_folded = fold(&lemma);
    let canon_folded = fold(canon);

    if let Some(hit) = hardcoded_named(&lemma_folded, &canon_folded) {
        return hit;
    }

    let mut candidates: Vec<Candidate> = Vec::new();
    push_candidates(&mut candidates, &lemma_folded, SKIP_AS_TYPE, Family::Skip);
    push_candidates(
        &mut candidates,
        &lemma_folded,
        INSTRUMENT,
        Family::Instrument,
    );
    push_candidates(&mut candidates, &lemma_folded, NAMED, Family::Named);
    for (key, bucket) in IDENTIFYING.iter().copied() {
        if lemma_match(&lemma_folded, key) {
            candidates.push(Candidate {
                exact: u8::from(lemma_folded == key),
                len: key.chars().count(),
                family: Family::Identifying(bucket),
                key,
            });
        }
    }

    if candidates.is_empty() {
        return FormClassification {
            lemma,
            bucket: FormBucket::Unknown,
            verdict: FormVerdict::UnknownKind,
            graph: FormGraph::Refuse,
            why: WHY_UNKNOWN_KIND,
        };
    }

    // Python `max(..., key=(exact, len))` keeps the first maximum on ties;
    // the candidates are pushed in a fixed reference order.
    let mut best = 0usize;
    for index in 1..candidates.len() {
        let current = (candidates[index].exact, candidates[index].len);
        let incumbent = (candidates[best].exact, candidates[best].len);
        if current > incumbent {
            best = index;
        }
    }
    let Candidate {
        family,
        key: matched,
        ..
    } = candidates[best];
    let lemma = matched.to_string();

    match family {
        Family::Skip => FormClassification {
            lemma,
            bucket: FormBucket::SkipAsType,
            verdict: FormVerdict::NotAnAct,
            graph: FormGraph::Refuse,
            why: WHY_NOT_AN_ACT,
        },
        Family::Instrument => FormClassification {
            lemma,
            bucket: FormBucket::Instrument,
            verdict: FormVerdict::InstrumentNotNpa,
            graph: FormGraph::Refuse,
            why: WHY_INSTRUMENT,
        },
        Family::Named => FormClassification {
            lemma,
            bucket: FormBucket::Named,
            verdict: FormVerdict::NamedAnnex,
            graph: FormGraph::Hold,
            why: WHY_NAMED,
        },
        Family::Identifying(bucket) => FormClassification {
            lemma,
            bucket: FormBucket::Identifying(bucket),
            verdict: FormVerdict::FormInDictionary,
            graph: FormGraph::Undecided,
            why: identifying_why(bucket),
        },
    }
}
