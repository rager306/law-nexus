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

use crate::npa_anchor::{check_span, LocalSpan};
use crate::npa_link::LinkedDocument;

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

/// Literal named-annex branches from Python `classify_type` that fire before
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

// ═══════════════════════════════════════════════════════════════════════════
// Axes B..H (D516 / ADR-0028) and the four-valued graph class.
//
// Ported 1:1 from the Python executable differential reference
// (`classify_layers` / `_layer_row` in `scripts/m207_context_graph_demo.py`).
// Branch order is load-bearing: reordering it breaks differential parity with
// the tracked reference fixture. The module stays std-only (D602).
// ═══════════════════════════════════════════════════════════════════════════

/// Four-valued graph class (`graph` in the Python reference). The internal
/// form hint `FormGraph::Undecided` never escapes here: axes B..H decide a
/// concrete class (an off-dictionary form still resolves to `refuse`/`overlay`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GraphClass {
    IdentifyingAct,
    Hold,
    Overlay,
    Refuse,
}

impl GraphClass {
    pub fn as_str(self) -> &'static str {
        match self {
            GraphClass::IdentifyingAct => "identifying_act",
            GraphClass::Hold => "hold",
            GraphClass::Overlay => "overlay",
            GraphClass::Refuse => "refuse",
        }
    }
}

/// Axis B: what the act is in law. Fail-closed: `unknown` blocks identity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegalClass {
    Npa,
    IndividualLegalAct,
    ClarificationLetter,
    JudicialAct,
    PrimaryInstrument,
    Unknown,
}

impl LegalClass {
    pub fn as_str(self) -> &'static str {
        match self {
            LegalClass::Npa => "npa",
            LegalClass::IndividualLegalAct => "individual_legal_act",
            LegalClass::ClarificationLetter => "clarification_letter",
            LegalClass::JudicialAct => "judicial_act",
            LegalClass::PrimaryInstrument => "primary_instrument",
            LegalClass::Unknown => "unknown",
        }
    }
}

/// Axis C: whose public power. GEO is never a substitute for competence.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Competence {
    International,
    Federal,
    Subject,
    Municipal,
    NotApplicable,
    Unknown,
}

impl Competence {
    pub fn as_str(self) -> &'static str {
        match self {
            Competence::International => "international",
            Competence::Federal => "federal",
            Competence::Subject => "subject",
            Competence::Municipal => "municipal",
            Competence::NotApplicable => "not_applicable",
            Competence::Unknown => "unknown",
        }
    }
}

/// Axis F: general legal rule for an indefinite circle.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Normativity {
    Yes,
    No,
    Unknown,
}

impl Normativity {
    pub fn as_str(self) -> &'static str {
        match self {
            Normativity::Yes => "yes",
            Normativity::No => "no",
            Normativity::Unknown => "unknown",
        }
    }
}

/// Axis G: bound as by a statute for everyone the norm addresses. The KS RF
/// exception is `yes_as_to_reviewed_norm` (G=yes without F=yes).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Binding {
    YesIfInForce,
    No,
    NotApplicable,
    Unknown,
    YesAsToReviewedNorm,
}

impl Binding {
    pub fn as_str(self) -> &'static str {
        match self {
            Binding::YesIfInForce => "yes_if_in_force",
            Binding::No => "no",
            Binding::NotApplicable => "not_applicable",
            Binding::Unknown => "unknown",
            Binding::YesAsToReviewedNorm => "yes_as_to_reviewed_norm",
        }
    }
}

/// Axis H: public-administration / KoAP genre, never a force regime.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Admin {
    LegislativeOnAdminSubject,
    AdministrativeNpa,
    AdministrativeIndividual,
    KoapProceedingAct,
    AdministrativeClarification,
    NotAdministrative,
    Unknown,
}

impl Admin {
    pub fn as_str(self) -> &'static str {
        match self {
            Admin::LegislativeOnAdminSubject => "legislative_on_admin_subject",
            Admin::AdministrativeNpa => "administrative_npa",
            Admin::AdministrativeIndividual => "administrative_individual",
            Admin::KoapProceedingAct => "koap_proceeding_act",
            Admin::AdministrativeClarification => "administrative_clarification",
            Admin::NotAdministrative => "not_administrative",
            Admin::Unknown => "unknown",
        }
    }
}

/// ADR-0016 identity key selector. `hold`/`do_not_project`/`overlay_not_rank`/
/// `deferred-undefined` are explicit non-projections, not an error state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityKey {
    Federal,
    PresidentialAgency,
    RegionalMunicipal,
    DoNotProject,
    OverlayNotRank,
    DeferredUndefined,
    Hold,
}

impl IdentityKey {
    pub fn as_str(self) -> &'static str {
        match self {
            IdentityKey::Federal => "federal",
            IdentityKey::PresidentialAgency => "presidential_agency",
            IdentityKey::RegionalMunicipal => "regional_municipal",
            IdentityKey::DoNotProject => "do_not_project",
            IdentityKey::OverlayNotRank => "overlay_not_rank",
            IdentityKey::DeferredUndefined => "deferred-undefined",
            IdentityKey::Hold => "hold",
        }
    }
}

/// One classification row: axis A form plus axes B..H and the identity key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClassificationRow {
    pub lemma: String,
    pub bucket: FormBucket,
    pub verdict: FormVerdict,
    pub legal_class: LegalClass,
    pub competence: Competence,
    pub geo: String,
    pub issuer: String,
    pub normativity: Normativity,
    pub binding: Binding,
    pub admin: Admin,
    pub graph: GraphClass,
    pub identity_key: IdentityKey,
    pub why: String,
}

// ── case / character helpers ────────────────────────────────────────────────

fn ascii_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn cyr_upper(c: char) -> bool {
    matches!(c, 'А'..='Я' | 'Ё')
}

fn cyr_lower(c: char) -> bool {
    matches!(c, 'а'..='я' | 'ё')
}

fn cyr_letter(c: char) -> bool {
    cyr_upper(c) || cyr_lower(c)
}

fn ci_eq(a: char, b: char) -> bool {
    a.to_lowercase().eq(b.to_lowercase())
}

fn at_word_start(chars: &[char], pos: usize) -> bool {
    pos == 0 || !ascii_word_char(chars[pos - 1])
}

fn at_word_end(chars: &[char], pos: usize) -> bool {
    pos >= chars.len() || !ascii_word_char(chars[pos])
}

fn matches_ci(chars: &[char], pos: usize, pat: &str) -> bool {
    let mut i = pos;
    for p in pat.chars() {
        match chars.get(i) {
            Some(c) if ci_eq(*c, p) => i += 1,
            _ => return false,
        }
    }
    true
}

fn matches_exact(chars: &[char], pos: usize, pat: &str) -> bool {
    for (i, p) in (pos..).zip(pat.chars()) {
        if chars.get(i) != Some(&p) {
            return false;
        }
    }
    true
}

/// Python `re.sub(r"\s+", " ", value).strip()`.
fn collapse_ws(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn find_from(chars: &[char], from: usize, pat: &[char]) -> Option<usize> {
    if pat.is_empty() || pat.len() > chars.len() || from > chars.len() - pat.len() {
        return None;
    }
    for start in from..=chars.len() - pat.len() {
        if &chars[start..start + pat.len()] == pat {
            return Some(start);
        }
    }
    None
}

fn word_run_end(chars: &[char], pos: usize) -> usize {
    let mut k = pos;
    while k < chars.len() && ascii_word_char(chars[k]) {
        k += 1;
    }
    k
}

/// Python `\s+`: at least one whitespace character.
fn ws_run_end(chars: &[char], pos: usize) -> Option<usize> {
    let mut k = pos;
    while k < chars.len() && chars[k].is_whitespace() {
        k += 1;
    }
    if k > pos {
        Some(k)
    } else {
        None
    }
}

/// `\s*` followed by `tail` followed by `\w*`.
fn ws_then_word_run(chars: &[char], pos: usize, tail: &str) -> Option<usize> {
    let mut k = pos;
    while k < chars.len() && chars[k].is_whitespace() {
        k += 1;
    }
    if !matches_ci(chars, k, tail) {
        return None;
    }
    Some(word_run_end(chars, k + tail.chars().count()))
}

fn has_whole_word_from(chars: &[char], from: usize, word: &str) -> bool {
    let pat: Vec<char> = word.chars().collect();
    if pat.is_empty() {
        return false;
    }
    let mut i = from;
    while let Some(start) = find_from(chars, i, &pat) {
        if at_word_start(chars, start) && at_word_end(chars, start + pat.len()) {
            return true;
        }
        i = start + 1;
    }
    false
}

fn has_whole_word(chars: &[char], word: &str) -> bool {
    has_whole_word_from(chars, 0, word)
}

fn text_has_word_start(hay: &str, word: &str) -> bool {
    let chars: Vec<char> = hay.chars().collect();
    let pat: Vec<char> = word.chars().collect();
    let mut i = 0;
    while let Some(start) = find_from(&chars, i, &pat) {
        if at_word_start(&chars, start) {
            return true;
        }
        i = start + 1;
    }
    false
}

fn text_has_g_dot(hay: &str) -> bool {
    let chars: Vec<char> = hay.chars().collect();
    for i in 0..chars.len() {
        if chars[i] == 'г' && chars.get(i + 1) == Some(&'.') && at_word_start(&chars, i) {
            return true;
        }
    }
    false
}

// ── Python `_FED_ORG` ──────────────────────────────────────────────────────

/// Python `_FED_ORG` search: the first federal-organ mention in `canon`, in
/// original case, `\s+`-collapsed and trimmed.
fn fed_org(canon: &str) -> Option<String> {
    let chars: Vec<char> = canon.chars().collect();
    for pos in 0..chars.len() {
        if !at_word_start(&chars, pos) {
            continue;
        }
        if let Some(end) = fed_org_at(&chars, pos) {
            return Some(collapse_ws(&chars[pos..end].iter().collect::<String>()));
        }
    }
    None
}

fn fed_org_at(chars: &[char], pos: usize) -> Option<usize> {
    // 1. Мин[а-яё]+развития (greedy run, backtrack to the suffix).
    if matches_ci(chars, pos, "мин") {
        let start = pos + 3;
        let mut k = start;
        while k < chars.len() && cyr_letter(chars[k]) {
            k += 1;
        }
        if k >= start + 9 && matches_ci(chars, k - 8, "развития") && at_word_end(chars, k) {
            return Some(k);
        }
    }
    // 2. Мин[а-яё]{3,}
    if matches_ci(chars, pos, "мин") {
        let mut k = pos + 3;
        let mut count = 0usize;
        while k < chars.len() && cyr_letter(chars[k]) {
            k += 1;
            count += 1;
        }
        if count >= 3 && at_word_end(chars, k) {
            return Some(k);
        }
    }
    // 3. ФАС / 4. УФАС / 5. ФАНО
    for token in ["фас", "уфас", "фано"] {
        if matches_ci(chars, pos, token) && at_word_end(chars, pos + token.chars().count()) {
            return Some(pos + token.chars().count());
        }
    }
    // 6. Росимуществ\w*
    if matches_ci(chars, pos, "росимуществ") {
        return Some(word_run_end(chars, pos + 11));
    }
    // 7. Правительств\w*\s+РФ / 8. Президент\w*\s+РФ
    for (stem, len) in [("правительств", 12usize), ("президент", 9usize)] {
        if matches_ci(chars, pos, stem) {
            let k = word_run_end(chars, pos + len);
            if let Some(w) = ws_run_end(chars, k) {
                if matches_ci(chars, w, "рф") && at_word_end(chars, w + 2) {
                    return Some(w + 2);
                }
            }
        }
    }
    // 9. КС\s+РФ
    if matches_ci(chars, pos, "кс") {
        if let Some(w) = ws_run_end(chars, pos + 2) {
            if matches_ci(chars, w, "рф") && at_word_end(chars, w + 2) {
                return Some(w + 2);
            }
        }
    }
    None
}

/// Python `^(?:письмо|приказ|распоряжение|решение)\s+(.+)$` (case-insensitive).
fn tail_org(canon: &str) -> Option<String> {
    let lower = canon.to_lowercase();
    for kw in ["письмо", "приказ", "распоряжение", "решение"] {
        if let Some(rest) = lower.strip_prefix(kw) {
            if rest.starts_with(|c: char| c.is_whitespace()) {
                let chars: Vec<char> = canon.chars().collect();
                let tail: String = chars[kw.chars().count()..].iter().collect();
                let collapsed = collapse_ws(&tail);
                if !collapsed.is_empty() {
                    return Some(collapsed);
                }
            }
        }
    }
    None
}

/// Python `_TERRITORIAL_FOIV` (УФАС | МТУ Росимущества | управление федеральное).
fn territorial_foiv(value: &str) -> bool {
    let folded = value.to_lowercase();
    folded.contains("уфас")
        || word_prefix_then(&folded, "мту", "росимущества")
        || word_prefix_then(&folded, "управлени", "федеральн")
}

/// Python `_CORP_ACTOR` = `\b(?:ООО|АО|ПАО|ИП|ЗАО)\b` (case-sensitive).
fn corp_actor(text: &str) -> bool {
    let chars: Vec<char> = text.chars().collect();
    for pos in 0..chars.len() {
        for token in ["ООО", "АО", "ПАО", "ИП", "ЗАО"] {
            let pat: Vec<char> = token.chars().collect();
            if chars[pos..].starts_with(&pat)
                && at_word_start(&chars, pos)
                && at_word_end(&chars, pos + pat.len())
            {
                return true;
            }
        }
    }
    false
}

/// Python `решение\w*.*\b(?:уфас|фас)\b` on the casefolded canon.
fn decision_ufas(folded: &str) -> bool {
    let chars: Vec<char> = folded.chars().collect();
    let pat: Vec<char> = "решени".chars().collect();
    let mut i = 0;
    while let Some(start) = find_from(&chars, i, &pat) {
        if has_whole_word_from(&chars, start + 6, "уфас")
            || has_whole_word_from(&chars, start + 6, "фас")
        {
            return true;
        }
        i = start + 1;
    }
    false
}

// ── Python `_GEO_SUBJ` / `canon_geo` ───────────────────────────────────────

/// Python `_Oblast` = `[А-ЯЁ][а-яё]+(?:ской|цкой)`. Returns the end index.
fn oblast_end(chars: &[char], pos: usize) -> Option<usize> {
    if !chars.get(pos).copied().is_some_and(cyr_upper) {
        return None;
    }
    let mut run_end = pos + 1;
    while run_end < chars.len() && cyr_lower(chars[run_end]) {
        run_end += 1;
    }
    // `[а-яё]+` must consume at least one char before the suffix, so the
    // suffix cannot start earlier than `pos + 2`; the greedy run backtracks to
    // the last usable `ской` / `цкой` inside the run.
    let mut e = run_end;
    while e >= pos + 6 {
        let suffix: String = chars[e - 4..e].iter().collect();
        if suffix == "ской" || suffix == "цкой" {
            return Some(e);
        }
        e -= 1;
    }
    None
}

fn capital_lower_word(chars: &[char], pos: usize) -> Option<usize> {
    if !chars.get(pos).copied().is_some_and(cyr_upper) {
        return None;
    }
    if !chars.get(pos + 1).copied().is_some_and(cyr_lower) {
        return None;
    }
    let mut k = pos + 1;
    while k < chars.len() && cyr_lower(chars[k]) {
        k += 1;
    }
    Some(k)
}

fn geo_alt1(chars: &[char], pos: usize) -> Option<usize> {
    let mut k = oblast_end(chars, pos)?;
    let mut count = 0usize;
    loop {
        let mut p = k;
        if chars.get(p) != Some(&',') {
            break;
        }
        p += 1;
        while p < chars.len() && chars[p].is_whitespace() {
            p += 1;
        }
        match oblast_end(chars, p) {
            Some(e) => {
                k = e;
                count += 1;
            }
            None => break,
        }
    }
    if count == 0 {
        return None;
    }
    let k2 = geo_and_oblast(chars, k)?;
    ws_then_word_run(chars, k2, "област")
}

/// `\s+и\s+<_Oblast>` (the shared coordinator of `_GEO_SUBJ`).
fn geo_and_oblast(chars: &[char], pos: usize) -> Option<usize> {
    let k = ws_run_end(chars, pos)?;
    if !matches_ci(chars, k, "и") {
        return None;
    }
    let w = ws_run_end(chars, k + 1)?;
    oblast_end(chars, w)
}

fn geo_alt2(chars: &[char], pos: usize) -> Option<usize> {
    let e1 = oblast_end(chars, pos)?;
    let k = geo_and_oblast(chars, e1).unwrap_or(e1);
    ws_then_word_run(chars, k, "област")
}

fn geo_alt3(chars: &[char], pos: usize) -> Option<usize> {
    if !matches_ci(chars, pos, "город") {
        return None;
    }
    let mut k = pos + 5;
    if let Some(c) = chars.get(k) {
        if *c == 'а' || *c == 'е' {
            k += 1;
        }
    }
    let w = ws_run_end(chars, k)?;
    capital_lower_word(chars, w)
}

fn geo_alt4(chars: &[char], pos: usize) -> Option<usize> {
    if !matches_exact(chars, pos, "г.") {
        return None;
    }
    let mut k = pos + 2;
    while k < chars.len() && chars[k].is_whitespace() {
        k += 1;
    }
    capital_lower_word(chars, k)
}

const GEO_CITY_TOKENS: &[&str] = &[
    "Челябинск",
    "Брянск",
    "Белгород",
    "Магадан",
    "Владимирск",
    "Ивановск",
    "Костромск",
    "Ярославск",
    "Смоленск",
];

fn geo_city(chars: &[char], pos: usize) -> Option<usize> {
    for tok in GEO_CITY_TOKENS {
        if matches_exact(chars, pos, tok) {
            return Some(word_run_end(chars, pos + tok.chars().count()));
        }
    }
    None
}

fn geo_subject_at(chars: &[char], pos: usize) -> Option<usize> {
    if let Some(e) = geo_alt1(chars, pos) {
        return Some(e);
    }
    if let Some(e) = geo_alt2(chars, pos) {
        return Some(e);
    }
    if let Some(e) = geo_alt3(chars, pos) {
        return Some(e);
    }
    if let Some(e) = geo_alt4(chars, pos) {
        return Some(e);
    }
    geo_city(chars, pos)
}

/// Python `_GEO_SUBJ.search` (case-sensitive). Returns the matched toponym.
fn geo_subject(raw: &str) -> Option<String> {
    let chars: Vec<char> = raw.chars().collect();
    for pos in 0..chars.len() {
        if let Some(end) = geo_subject_at(&chars, pos) {
            return Some(chars[pos..end].iter().collect());
        }
    }
    None
}

const GEO_CITY_STEM: &[(&str, &str)] = &[
    ("челябинск", "Челябинск"),
    ("брянск", "Брянск"),
    ("белгород", "Белгород"),
    ("магадан", "Магадан"),
];

/// Python `canon_geo`: axis D keeps the toponym, not the adjective case.
fn canon_geo(raw: &str) -> String {
    let folded = raw.to_lowercase();
    let trimmed = folded.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    if folded.contains("област") || text_has_word_start(trimmed, "город") || text_has_g_dot(trimmed)
    {
        return collapse_ws(raw);
    }
    for (stem, nominative) in GEO_CITY_STEM {
        if trimmed.starts_with(stem) {
            return (*nominative).to_string();
        }
    }
    collapse_ws(raw)
}

// ── Python `_ISO_STD` ──────────────────────────────────────────────────────

fn iso_fam_at(chars: &[char], pos: usize, alt: u8) -> Option<usize> {
    match alt {
        1 => {
            // техническ\w*\s+регламент\w*(\s+(таможенн\w*\s+союза|еаэс))?
            if !matches_ci(chars, pos, "техническ") {
                return None;
            }
            let k = word_run_end(chars, pos + 9);
            let w = ws_run_end(chars, k)?;
            if !matches_ci(chars, w, "регламент") {
                return None;
            }
            let mut e = word_run_end(chars, w + 9);
            if let Some(w2) = ws_run_end(chars, e) {
                let mut extended = None;
                if matches_ci(chars, w2, "таможенн") {
                    let e2 = word_run_end(chars, w2 + 8);
                    if let Some(w3) = ws_run_end(chars, e2) {
                        if matches_ci(chars, w3, "союза") {
                            extended = Some(w3 + 5);
                        }
                    }
                }
                if extended.is_none() && matches_ci(chars, w2, "еаэс") {
                    extended = Some(w2 + 4);
                }
                if let Some(e3) = extended {
                    e = e3;
                }
            }
            Some(e)
        }
        2 => {
            // ТР\s+(ТС|ЕАЭС)
            if !matches_ci(chars, pos, "тр") {
                return None;
            }
            let w = ws_run_end(chars, pos + 2)?;
            if matches_ci(chars, w, "тс") {
                return Some(w + 2);
            }
            if matches_ci(chars, w, "еаэс") {
                return Some(w + 4);
            }
            None
        }
        3 => {
            // ГОСТ(\s+Р)?
            if !matches_ci(chars, pos, "гост") {
                return None;
            }
            let mut e = pos + 4;
            if let Some(w) = ws_run_end(chars, e) {
                if matches_ci(chars, w, "р") {
                    e = w + 1;
                }
            }
            Some(e)
        }
        4 => {
            for token in ["исо", "iso", "iec"] {
                if matches_ci(chars, pos, token) {
                    return Some(pos + 3);
                }
            }
            None
        }
        5 => {
            if matches_ci(chars, pos, "снип") {
                return Some(pos + 4);
            }
            if matches_ci(chars, pos, "санпин") {
                return Some(pos + 6);
            }
            None
        }
        6 => {
            if matches_ci(chars, pos, "сп") && at_word_end(chars, pos + 2) {
                return Some(pos + 2);
            }
            None
        }
        _ => None,
    }
}

/// Python `\s*(?P<num>[\d][\d./\-]*(?::\d{4})?)` — a fam without a number is
/// not a standard hit.
fn iso_num_at(chars: &[char], pos: usize) -> Option<usize> {
    let mut k = pos;
    while k < chars.len() && chars[k].is_whitespace() {
        k += 1;
    }
    if !chars.get(k).is_some_and(|c| c.is_ascii_digit()) {
        return None;
    }
    k += 1;
    while k < chars.len() && (chars[k].is_ascii_digit() || matches!(chars[k], '.' | '/' | '-')) {
        k += 1;
    }
    if chars.get(k) == Some(&':') {
        let d = k + 1;
        if d + 4 <= chars.len() && chars[d..d + 4].iter().all(|c| c.is_ascii_digit()) {
            k = d + 4;
        }
    }
    Some(k)
}

/// Python `_ISO_STD.search(canon)`: returns the `fam` group of the first hit.
fn iso_std(canon: &str) -> Option<String> {
    let chars: Vec<char> = canon.chars().collect();
    for pos in 0..chars.len() {
        if !at_word_start(&chars, pos) {
            continue;
        }
        for alt in 1..=6u8 {
            if let Some(end) = iso_fam_at(&chars, pos, alt) {
                if iso_num_at(&chars, end).is_some() {
                    return Some(chars[pos..end].iter().collect());
                }
            }
        }
    }
    None
}

// ── Python `_layer_row` ────────────────────────────────────────────────────

fn identity_key_for(legal_class: LegalClass, competence: Competence, lemma: &str) -> IdentityKey {
    let mut key = IdentityKey::Hold;
    if legal_class == LegalClass::Npa
        && matches!(
            competence,
            Competence::Federal | Competence::Subject | Competence::Municipal
        )
    {
        if competence == Competence::Federal {
            key = if matches!(lemma, "закон" | "кодекс") {
                IdentityKey::Federal
            } else if matches!(
                lemma,
                "указ" | "постановление" | "распоряжение" | "приказ" | "письмо"
            ) {
                IdentityKey::PresidentialAgency
            } else {
                IdentityKey::Federal
            };
        } else {
            key = IdentityKey::RegionalMunicipal;
        }
    }
    if matches!(
        legal_class,
        LegalClass::Unknown | LegalClass::ClarificationLetter | LegalClass::PrimaryInstrument
    ) {
        key = IdentityKey::DoNotProject;
    }
    if legal_class == LegalClass::JudicialAct {
        key = IdentityKey::OverlayNotRank;
    }
    if competence == Competence::International {
        key = IdentityKey::DeferredUndefined;
    }
    key
}

#[allow(clippy::too_many_arguments)]
fn layer_row(
    form: &FormClassification,
    legal_class: LegalClass,
    competence: Competence,
    geo: String,
    issuer: String,
    normativity: Normativity,
    binding: Binding,
    admin: Admin,
    graph: GraphClass,
    why: String,
) -> ClassificationRow {
    let identity_key = identity_key_for(legal_class, competence, &form.lemma);
    ClassificationRow {
        lemma: form.lemma.clone(),
        bucket: form.bucket,
        verdict: form.verdict,
        legal_class,
        competence,
        geo,
        issuer,
        normativity,
        binding,
        admin,
        graph,
        identity_key,
        why,
    }
}

/// Full-codex-name resolver used only for the `why` text of the codex branch.
fn codex_name(folded: &str) -> Option<&'static str> {
    if folded.contains("коап") {
        return Some("КоАП РФ");
    }
    if (folded.contains("процессуальн") && folded.contains("гражданск"))
        || folded.starts_with("гпк")
    {
        return Some("ГПК РФ");
    }
    if folded.contains("уголовно-процессуальн") || folded.starts_with("упк")
    {
        return Some("УПК РФ");
    }
    if folded.starts_with("апк") || folded.contains("арбитражн") {
        return Some("АПК РФ");
    }
    if folded.starts_with("кас") || folded.contains("судопроизводств") {
        return Some("КАС РФ");
    }
    if word_prefix_then(folded, "таможенн", "кодекс") {
        return Some("Таможенный кодекс");
    }
    if word_prefix_then(folded, "трудов", "кодекс") {
        return Some("Трудовой кодекс");
    }
    if word_prefix_then(folded, "уголовно-исполнительн", "кодекс") || folded.contains("уик")
    {
        return Some("Уголовно-исполнительный кодекс");
    }
    if word_prefix_then(folded, "гражданск", "кодекс") {
        return Some("Гражданский кодекс");
    }
    if word_prefix_then(folded, "уголовн", "кодекс") {
        return Some("Уголовный кодекс");
    }
    if folded.starts_with("нк") || folded.contains("налогов") {
        return Some("НК РФ");
    }
    if folded.starts_with("бк") || folded.contains("бюджетн") {
        return Some("БК РФ");
    }
    if folded.starts_with("зк") || folded.contains("земельн") {
        return Some("ЗК РФ");
    }
    if folded.starts_with("жк") || folded.contains("жилищн") {
        return Some("ЖК РФ");
    }
    if folded.starts_with("ск") || folded.contains("семейн") {
        return Some("СК РФ");
    }
    if folded.starts_with("лк") || word_prefix_then(folded, "лесн", "кодекс") {
        return Some("ЛК РФ");
    }
    None
}

/// Classify along all axes: axis A form plus axes B..H, the graph class and
/// the ADR-0016 identity key. `text` is the member's own source block; it is
/// read only for GEO org fallback, the corporate-actor refusal, and the
/// administrativeness hint. Total and fail-closed; never panics.
pub fn classify(canon: &str, text: &str) -> ClassificationRow {
    let form = classify_form(canon);
    let lemma = form.lemma.clone();
    let lemma = lemma.as_str();
    let bucket = form.bucket;
    let folded = canon.to_lowercase();
    let body = text.to_lowercase();

    // Defaults, exactly as the Python reference initialises them.
    let mut geo = String::new();
    let issuer = {
        let mut value = fed_org(canon).map(|s| collapse_ws(&s)).unwrap_or_default();
        if let Some(tail) = tail_org(canon) {
            value = tail;
        }
        value
    };
    let mut geo_hit = geo_subject(canon);
    let territorial_type = territorial_foiv(canon)
        || matches!(lemma, "письмо" | "приказ" | "распоряжение")
        || folded.contains("уфас")
        || folded.contains("мту");
    if geo_hit.is_none() && territorial_type {
        geo_hit = geo_subject(text);
    }
    if let Some(hit) = &geo_hit {
        geo = canon_geo(hit);
    }

    // Isо-стандарты (техрегламент / ГОСТ / ИСО / СНиП / СанПиН) — не НПА ПП 1009.
    if let Some(fam_raw) = iso_std(canon) {
        let fam = fam_raw.to_lowercase();
        if fam.contains("регламент") || fam.starts_with("тр") {
            let international =
                fam.contains("тс") || fam.contains("еаэс") || fam.contains("таможенн");
            return layer_row(
                &form,
                LegalClass::Npa,
                if international {
                    Competence::International
                } else {
                    Competence::Federal
                },
                geo,
                issuer,
                Normativity::Yes,
                Binding::YesIfInForce,
                Admin::NotAdministrative,
                if international {
                    GraphClass::Overlay
                } else {
                    GraphClass::IdentifyingAct
                },
                "технический регламент (ТР ТС/ЕАЭС) — обязательный; голый «ТР» не ловим 
(омограф «третье»); international identity_key deferred-undefined"
                    .to_string(),
            );
        }
        let competence = if fam.contains("iso")
            || fam.contains("iec")
            || fam.starts_with("изо")
            || fam.contains("исо")
        {
            Competence::International
        } else {
            Competence::Federal
        };
        return layer_row(
            &form,
            LegalClass::Unknown,
            competence,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Overlay,
            "ГОСТ/ИСО/СНиП/СанПиН — стандарт, не НПА ПП 1009; обязательность только через 
техрегламент; не Work identity"
                .to_string(),
        );
    }

    // Решение территориального ФАС/УФАС — практика (ADR-0020), не НПА.
    if decision_ufas(&folded)
        || (lemma.starts_with("решени") && {
            let chars: Vec<char> = folded.chars().collect();
            has_whole_word(&chars, "уфас") || has_whole_word(&chars, "фас")
        })
    {
        return layer_row(
            &form,
            LegalClass::IndividualLegalAct,
            Competence::Federal,
            geo,
            issuer,
            Normativity::No,
            Binding::No,
            Admin::AdministrativeIndividual,
            GraphClass::Overlay,
            "решение УФАС/ФАС по делу — индивидуальный акт территориального ФОИВ, не НПА и не 
ступенька ADR-0019; overlay практики (ADR-0020); GEO города не делает его муниципальным"
                .to_string(),
        );
    }

    if matches!(
        form.verdict,
        FormVerdict::TypeMissing | FormVerdict::UnknownKind | FormVerdict::NotAnAct
    ) {
        return layer_row(
            &form,
            LegalClass::Unknown,
            Competence::Unknown,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Refuse,
            form.why.to_string(),
        );
    }

    // Письмо ФОИВ — не НПА и не общеобязательно.
    if lemma == "письмо"
        || (bucket == FormBucket::Identifying("agency") && folded.starts_with("письм"))
    {
        return layer_row(
            &form,
            LegalClass::ClarificationLetter,
            Competence::Federal,
            geo,
            issuer,
            Normativity::No,
            Binding::No,
            Admin::AdministrativeClarification,
            GraphClass::Refuse,
            "письмо ФОИВ — не НПА (ПП 1009) и не общеобязательно; GEO города не делает его 
муниципальным; ребро идентичности НПА не строим"
                .to_string(),
        );
    }

    // Простой/первичный документ.
    if form.verdict == FormVerdict::InstrumentNotNpa
        || matches!(
            lemma,
            "доверенность"
                | "жалоба"
                | "контракт"
                | "лицензия"
                | "соглашение"
                | "протокол"
        )
    {
        return layer_row(
            &form,
            LegalClass::PrimaryInstrument,
            Competence::NotApplicable,
            geo,
            issuer,
            Normativity::No,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Refuse,
            "простой/первичный документ: не акт власти как источник права; не нормативность, 
не общеобязательность"
                .to_string(),
        );
    }

    // Пленум ВС/ВАС РФ — разъяснение практики (overlay ADR-0020).
    if folded.contains("пленум") {
        let plenary = if folded.contains("вас") {
            "Пленум ВАС РФ"
        } else {
            "Пленум ВС РФ"
        };
        let plenary_issuer = if issuer.is_empty() {
            plenary.to_string()
        } else {
            issuer.clone()
        };
        return layer_row(
            &form,
            LegalClass::JudicialAct,
            Competence::Federal,
            geo,
            plenary_issuer,
            Normativity::No,
            Binding::No,
            Admin::NotAdministrative,
            GraphClass::Overlay,
            format!(
                "постановление {plenary} — разъяснение практики, не НПА и не ступенька 
ADR-0019; overlay судебной практики (ADR-0020)"
            ),
        );
    }

    // Постановление КС РФ — исключение G без F (общеобязательно в части нормы).
    if folded.contains("кс рф")
        || (lemma == "постановление" && body.contains("кс рф") && folded.contains("кс"))
    {
        let ks_issuer = if issuer.is_empty() {
            "КС РФ".to_string()
        } else {
            issuer.clone()
        };
        return layer_row(
            &form,
            LegalClass::JudicialAct,
            Competence::Federal,
            geo,
            ks_issuer,
            Normativity::No,
            Binding::YesAsToReviewedNorm,
            Admin::NotAdministrative,
            GraphClass::Overlay,
            "постановление КС — не НПА и не ступенька ADR-0019, но общеобязательно в части 
судьбы проверенной нормы (исключение G без F)"
                .to_string(),
        );
    }

    // Голый ТК/ВК — омограф (D517).
    if lemma == "тк" || folded == "тк" {
        return layer_row(
            &form,
            LegalClass::Unknown,
            Competence::Unknown,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Refuse,
            "голый ТК — омограф (трудовой / таможенный / торговый комплекс); без полного 
имени, соседа ТС/ЕАЭС или уже выбранного канона в документе OfficialIdentityClaim 
не проецируем (D517)"
                .to_string(),
        );
    }

    // Кодексы и аббревиатуры.
    if lemma == "кодекс" || folded.starts_with("коап") || folded.contains("кодекс")
    {
        let is_koap = folded.starts_with("коап") || folded.contains("коап");
        if is_koap {
            return layer_row(
                &form,
                LegalClass::Npa,
                Competence::Federal,
                geo,
                issuer,
                Normativity::Yes,
                Binding::YesIfInForce,
                Admin::LegislativeOnAdminSubject,
                GraphClass::IdentifyingAct,
                "КоАП как кодекс = ФЗ; постановление по делу КоАП сюда не входит".to_string(),
            );
        }
        let named = codex_name(&folded).unwrap_or(canon);
        return layer_row(
            &form,
            LegalClass::Npa,
            Competence::Federal,
            geo,
            issuer,
            Normativity::Yes,
            Binding::YesIfInForce,
            Admin::NotAdministrative,
            GraphClass::IdentifyingAct,
            format!(
                "полное имя кодекса ({named}) — НПА, не голый ТК; омограф аббревиатуры 
здесь не стоит"
            ),
        );
    }

    // Распоряжение органа — форма, не класс (распоряжение Правительства ниже).
    if lemma == "распоряжение" && !folded.contains("правительств") {
        let competence = if fed_org(canon).is_some() || territorial_foiv(canon) {
            Competence::Federal
        } else {
            Competence::Unknown
        };
        return layer_row(
            &form,
            LegalClass::Unknown,
            competence,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Hold,
            "распоряжение органа — форма, не класс: как приказ бывает НПА и индивидуальным; 
распоряжение Правительства — отдельная ветка НПА"
                .to_string(),
        );
    }

    // Приказ: юрлицо-актор без издателя → первичный документ, иначе hold.
    if lemma == "приказ"
        || (bucket == FormBucket::Identifying("agency") && folded.starts_with("приказ"))
    {
        if issuer.is_empty() && corp_actor(text) {
            return layer_row(
                &form,
                LegalClass::PrimaryInstrument,
                Competence::NotApplicable,
                geo,
                issuer,
                Normativity::No,
                Binding::NotApplicable,
                Admin::NotAdministrative,
                GraphClass::Refuse,
                "приказ юрлица (ООО/АО/ИП) — не акт ФОИВ; не НПА и не hold до F".to_string(),
            );
        }
        let mut competence = if fed_org(canon).is_some() {
            Competence::Federal
        } else {
            Competence::Unknown
        };
        if territorial_foiv(canon) || territorial_foiv(text) {
            competence = Competence::Federal;
        }
        let issuer_or_canon = if issuer.is_empty() {
            canon
        } else {
            issuer.as_str()
        };
        if issuer_or_canon.to_lowercase().contains("област")
            || (!geo.is_empty()
                && geo.to_lowercase().contains("област")
                && !issuer.to_lowercase().contains("росси"))
        {
            competence = Competence::Subject;
        }
        let admin = if body.contains("утвержден") {
            Admin::AdministrativeNpa
        } else {
            Admin::Unknown
        };
        return layer_row(
            &form,
            LegalClass::Unknown,
            competence,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            admin,
            GraphClass::Hold,
            "приказ — форма, не класс: бывает НПА и индивидуальный; пока F неясна, 
OfficialIdentityClaim не проецируем"
                .to_string(),
        );
    }

    // Закон/указ/постановление Правительства — НПА.
    if matches!(
        bucket,
        FormBucket::Identifying("federal")
            | FormBucket::Identifying("presidential")
            | FormBucket::Identifying("government")
    ) || matches!(
        lemma,
        "закон" | "указ" | "постановление" | "распоряжение" | "кодекс"
    ) {
        return layer_row(
            &form,
            LegalClass::Npa,
            Competence::Federal,
            geo,
            issuer,
            Normativity::Yes,
            Binding::YesIfInForce,
            Admin::NotAdministrative,
            GraphClass::IdentifyingAct,
            "форма закона/указа/постановления Правительства — НПА; общеобязательность после 
режима силы (публикация), не из номера"
                .to_string(),
        );
    }

    if form.verdict == FormVerdict::NamedAnnex {
        return layer_row(
            &form,
            LegalClass::Unknown,
            Competence::Unknown,
            geo,
            issuer,
            Normativity::Unknown,
            Binding::NotApplicable,
            Admin::NotAdministrative,
            GraphClass::Hold,
            form.why.to_string(),
        );
    }

    layer_row(
        &form,
        LegalClass::Unknown,
        Competence::Unknown,
        geo,
        issuer,
        Normativity::Unknown,
        Binding::NotApplicable,
        Admin::NotAdministrative,
        GraphClass::Hold,
        "класс по форме не закрыт — ребро идентичности не строим".to_string(),
    )
}

// ── pipeline entry point ───────────────────────────────────────────────────

/// Fail-closed classification diagnostics for the member pipeline.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClassificationDiagnostic {
    /// A member span is out of range or fails `npa_anchor::check_span`.
    SpanInvalid,
    /// A member carries no TYPE surface (axis A `type_missing`).
    TypeMissing,
    /// A member TYPE is off the closed dictionary (axis A `unknown_kind`).
    UnknownKind,
}

/// A member classified along all axes. `evidence` is the member's own
/// source-local anchor; the typed and linked streams are never mutated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClassifiedMember {
    pub member_id: usize,
    pub graph: GraphClass,
    pub legal_class: LegalClass,
    pub competence: Competence,
    pub identity_key: IdentityKey,
    pub evidence: LocalSpan,
    pub why: String,
}

/// Classify every linked member against its own source block. A span that is
/// out of range or fails `npa_anchor::check_span` is reported as
/// `SpanInvalid` and the member is skipped (fail-closed, no panic). The
/// `LinkedDocument` is read-only.
pub fn classify_members(
    linked: &LinkedDocument,
    paras: &[String],
) -> (Vec<ClassifiedMember>, Vec<ClassificationDiagnostic>) {
    let mut members = Vec::new();
    let mut diagnostics = Vec::new();
    for member in &linked.members {
        let Some(para) = paras.get(member.evidence.block) else {
            diagnostics.push(ClassificationDiagnostic::SpanInvalid);
            continue;
        };
        if check_span(para, member.evidence).is_err() {
            diagnostics.push(ClassificationDiagnostic::SpanInvalid);
            continue;
        }
        let row = classify(&member.type_name, para);
        match row.verdict {
            FormVerdict::TypeMissing => diagnostics.push(ClassificationDiagnostic::TypeMissing),
            FormVerdict::UnknownKind => diagnostics.push(ClassificationDiagnostic::UnknownKind),
            _ => {}
        }
        members.push(ClassifiedMember {
            member_id: member.id,
            graph: row.graph,
            legal_class: row.legal_class,
            competence: row.competence,
            identity_key: row.identity_key,
            evidence: member.evidence,
            why: row.why,
        });
    }
    (members, diagnostics)
}
