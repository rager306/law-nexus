//! NPA linked document (M211 S03, ADR-0029).
//!
//! Derived, source-anchored linked pipeline over the canonical typed stream
//! (`npa_typed::scan_typed_diagnosed`) and the intra-block local-grammar
//! frames (`local_grammar::extract_act_list_frames_from_typed`). Linking
//! derives new records; it never mutates `TypedMember` and never emits a
//! cross-block `TextSpan` — a continuation relation carries the two separate
//! local anchors (D603 / RC28-F07).
//!
//! No external (de)serialization crate, filesystem, or environment access,
//! and no runtime state (D602).

use std::collections::BTreeMap;

use crate::document_context::PROPOSED_MAX_SERIES_HOPS;
use crate::local_grammar::{self, FrameStatus};
use crate::npa_anchor::{self, LocalSpan};
use crate::npa_continuation::{eligible_continuation_head_for, ContinuationEligibility};
use crate::npa_typed::{self, TypedMember};

/// How a [`LinkedMember`] was derived from the canonical typed stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkedMemberKind {
    /// A `date`+`number` occurrence from `npa_typed` (identity not minted).
    Anchored,
    /// A named annex type found in text without its own `date`+`number`
    /// anchor (later slices).
    NamedType,
}

/// Provenance of a linked member field.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkDerivation {
    /// Read directly from the typed anchor stream.
    TypedAnchor,
    /// Carried from the document letterhead.
    DocumentHead,
    /// Quoted from an approving act (`approved_by`).
    ApprovedByQuote,
    /// Resolved through a scoped `(далее — X)` declaration.
    ScopedAlias,
    /// A `настоящий …` reference to this document's own head/annex.
    ThisDocumentRef,
    /// A continuation of an open cross-block series.
    SeriesContinuation,
    /// A named annex found in text with no requisites of its own and no
    /// approving act (still a named type, but uncited).
    NamedTypeText,
    /// A corporate regulation whose approval was refused (`do_not_project`):
    /// no normative citation is minted (ADR-0029 §5).
    Refused,
}

/// Derived linked member. `TypedMember` fields are cloned, never mutated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkedMember {
    pub id: usize,
    pub kind: LinkedMemberKind,
    pub date: String,
    pub number: String,
    pub type_name: String,
    pub approved_by: Option<String>,
    pub alias: Option<String>,
    pub derivation: LinkDerivation,
    /// The member's own source-local anchor (half-open UTF-8 byte bounds).
    pub evidence: LocalSpan,
    /// All source-local spans that back this member, in discovery order.
    pub provenance: Vec<LocalSpan>,
}

/// Derived contextual relation kind (`prd/architecture/npa-document-context.yaml`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkedRelationKind {
    ContinuesSeries,
    ApprovedBy,
    ScopedAlias,
    ThisDocumentRef,
    HeadFamilyCarry,
}

/// A derived relation between two linked members. Evidence is always a list
/// of separate local anchors — never one cross-block span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkedRelation {
    pub kind: LinkedRelationKind,
    pub from_id: usize,
    pub to_id: usize,
    pub evidence: Vec<LocalSpan>,
    pub why: &'static str,
}

/// Fail-closed diagnostics for refused or unresolved contextual relations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkDiagnostic {
    /// An open coordination had no eligible cross-block head.
    OpenSeriesWithoutHead,
    /// An eligible head existed but was farther than the series hop bound.
    IncompatibleSeriesHead,
    /// A cross-block TYPE was not (and must not be) inherited into a tail.
    TypeNotInherited,
    /// A corporate head-family carry was refused (`do_not_project`).
    HeadFamilyCarryRefused,
    /// A short reference had no declaration in this document.
    AliasWithoutDeclaration,
    /// A `this`-reference had no usable document head.
    HeadUnavailable,
}

/// Letterhead recognition status; `Unrecognized` never fabricates requisites.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LetterheadStatus {
    Recognized,
    Unrecognized,
}

/// Document letterhead (head zone). Recognized from the leading paragraphs;
/// `Unrecognized` is represented by the recognizer returning `None`, so no
/// requisites are ever fabricated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Letterhead {
    pub kind: String,
    pub issuer: String,
    pub date: String,
    pub number: String,
    pub evidence: LocalSpan,
    pub status: LetterheadStatus,
}

/// Derived linked document. The canonical typed stream, source blocks, and
/// tokens are left untouched; this is a new projection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkedDocument {
    pub members: Vec<LinkedMember>,
    pub relations: Vec<LinkedRelation>,
    pub letterhead: Option<Letterhead>,
    pub diagnostics: Vec<LinkDiagnostic>,
}

/// Builds the anchored member list from the canonical typed stream.
///
/// `TypedMember` is read only: its field set is cloned into a derived record
/// and no identity is minted. Member ids are the typed-stream indices, so
/// relation endpoints stay stable across repeated calls (deterministic
/// replay) and across the series pass.
pub fn anchored_members(paras: &[String]) -> Vec<LinkedMember> {
    let (typed, _diagnostics) = npa_typed::scan_typed_diagnosed(paras);
    typed
        .iter()
        .enumerate()
        .map(|(id, member)| LinkedMember {
            id,
            kind: LinkedMemberKind::Anchored,
            date: member.date.clone(),
            number: member.number.clone(),
            type_name: member.type_name.clone(),
            approved_by: None,
            alias: None,
            derivation: LinkDerivation::TypedAnchor,
            evidence: member.span,
            provenance: provenance_of(member),
        })
        .collect()
}

fn provenance_of(member: &TypedMember) -> Vec<LocalSpan> {
    let mut provenance = Vec::new();
    if let Some(span) = member.type_evidence {
        provenance.push(span);
    }
    provenance.push(member.span);
    provenance
}

/// Cross-block series continuation (RC28-F07).
///
/// A **tail** is an intra-block frame with no locally admitted act type
/// (`head_roles` empty): an open coordination that cannot stand alone. A
/// **head** is a `Proposed` frame whose own block admitted an act type, whose
/// saved block text ends open (the list is visibly unfinished), in an earlier
/// block, satisfying the shared RC28-F07 predicate. The nearest eligible
/// head within `PROPOSED_MAX_SERIES_HOPS` blocks is linked. An unrelated
/// *complete* citation ends closed and therefore can never head a series.
///
/// Every relation carries the two separate local anchors of the head and tail
/// members. The input is never mutated.
pub fn link_series(paras: &[String]) -> (Vec<LinkedRelation>, Vec<LinkDiagnostic>) {
    let (typed, _diagnostics) = npa_typed::scan_typed_diagnosed(paras);
    let frames = local_grammar::extract_act_list_frames_from_typed(paras);
    let member_by_block = first_member_id_by_block(&typed);

    let mut relations = Vec::new();
    let mut diagnostics = Vec::new();

    for tail in frames.iter().filter(|frame| frame.head_roles.is_empty()) {
        if !retains_local_derivation(tail) {
            diagnostics.push(LinkDiagnostic::OpenSeriesWithoutHead);
            continue;
        }
        // Nearest earlier frame that proves its own act type and ends open.
        let head = frames
            .iter()
            .filter(|head| head.block < tail.block && eligible_head(paras, head, tail))
            .max_by_key(|head| head.block);
        let Some(head) = head else {
            diagnostics.push(LinkDiagnostic::OpenSeriesWithoutHead);
            continue;
        };
        if tail.block - head.block > PROPOSED_MAX_SERIES_HOPS {
            diagnostics.push(LinkDiagnostic::IncompatibleSeriesHead);
            continue;
        }
        let (Some(&from_id), Some(&to_id)) = (
            member_by_block.get(&head.block),
            member_by_block.get(&tail.block),
        ) else {
            diagnostics.push(LinkDiagnostic::OpenSeriesWithoutHead);
            continue;
        };
        relations.push(LinkedRelation {
            kind: LinkedRelationKind::ContinuesSeries,
            from_id,
            to_id,
            evidence: vec![typed[from_id].span, typed[to_id].span],
            why: "open series head continues into the next block's «от ДАТА N» tail (RC28-F07)",
        });
    }

    (relations, diagnostics)
}

/// Maps each source block to the id of its first typed member. A frame exists
/// only for a block that has typed members, so a frame's representative anchor
/// is always present.
fn first_member_id_by_block(typed: &[TypedMember]) -> BTreeMap<usize, usize> {
    let mut map = BTreeMap::new();
    for (id, member) in typed.iter().enumerate() {
        map.entry(member.span.block).or_insert(id);
    }
    map
}

fn eligible_head(
    paras: &[String],
    head: &local_grammar::CoordinatingFrame,
    tail: &local_grammar::CoordinatingFrame,
) -> bool {
    // An *open* head is the differential reference's `Block.ends_open`
    // (`scripts/m207_context_graph_demo.py`): a complete citation can never
    // authorize an unrelated continuation.
    let Some(head_text) = paras.get(head.block) else {
        return false;
    };
    if !block_ends_open(head_text) {
        return false;
    }
    eligible_continuation_head_for(&ContinuationEligibility {
        head_status_proposed: head.status == FrameStatus::Proposed,
        tail_status_not_rejected: tail.status != FrameStatus::Rejected,
        distinct_frames: head.block != tail.block,
        distinct_blocks: head.block != tail.block,
        head_admits_act_type: !head.head_roles.is_empty(),
        head_order_before_tail: head.block < tail.block,
        // All frames come from one document's paragraph slice.
        same_scope: true,
        head_retains_derivation: retains_local_derivation(head),
        tail_retains_derivation: retains_local_derivation(tail),
    })
}

fn retains_local_derivation(frame: &local_grammar::CoordinatingFrame) -> bool {
    frame.local_anchor.start() < frame.local_anchor.end()
}

/// `Block.ends_open` from the differential reference: the saved block stopped
/// mid-list — a trailing comma or an unclosed bracket.
fn block_ends_open(text: &str) -> bool {
    let trimmed = text.trim_end();
    if trimmed.is_empty() {
        return false;
    }
    if trimmed.ends_with(',') {
        return true;
    }
    trimmed.matches('(').count() > trimmed.matches(')').count()
}

// ---------------------------------------------------------------------------
// Letterhead recognizer (ADR-0029 §5; differential reference
// `_LETTERHEAD` / `_document_head_member` in
// `scripts/m207_context_graph_demo.py`).
//
// The issuer table is data, not a regex; matching is case-insensitive word /
// substring search. The implementation is bounded to the head zone and to
// kind + issuer + date/N — the full prototype `TYPE_HEAD` is out of scope.
// ---------------------------------------------------------------------------

/// Leading paragraphs that form the head zone. ADR-0029 §5: the court guard
/// lives on the letterhead, not on the body, so body mentions never
/// misclassify the document.
const LETTERHEAD_HEAD_ZONE: usize = 3;

/// Issuer letterhead table, equivalent to `_LETTERHEAD`
/// (`scripts/m207_context_graph_demo.py` L2509-2535). Patterns are lowercase
/// and whitespace-normalized; short names are kept exactly as written there.
const LETTERHEAD_ISSUERS: &[(&str, &str)] = &[
    ("министерство внутренних дел", "МВД России"),
    ("министерство юстиции", "Минюста России"),
    ("министерство труда", "Минтруда России"),
    ("министерство финансов", "Минфина России"),
    ("министерство здравоохранения", "Минздрава России"),
    (
        "министерство промышленности и торговли",
        "Минпромторга России",
    ),
    (
        "министерство экономического развития",
        "Минэкономразвития России",
    ),
    ("министерство природных ресурсов", "Минприроды России"),
    ("министерство сельского хозяйства", "Минсельхоза России"),
    ("министерство транспорта", "Минтранса России"),
    ("министерство строительства", "Минстроя России"),
    ("министерство цифрового развития", "Минцифры России"),
    ("министерство связи", "Минкомсвязи России"),
    ("министерство образования", "Минпросвещения России"),
    ("министерство науки", "Минобрнауки России"),
    ("министерство спорта", "Минспорта России"),
    ("министерство культуры", "Минкультуры России"),
    ("министерство энергетики", "Минэнерго России"),
    ("федеральная антимонопольная", "ФАС России"),
    ("федеральная служба безопасности", "ФСБ России"),
    ("федеральная служба охраны", "Росгвардия России"),
    ("федеральная таможенная", "ФТС России"),
    ("федеральное казначейство", "Федерального казначейства"),
    (
        "федеральная пробирная палата",
        "Федеральной пробирной палаты",
    ),
];

/// Recognized head family, used to pick the requisite source.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum HeadClass {
    Prikaz,
    Postanovlenie,
    Rasporyazhenie,
    Ukaz,
    Fas,
}

impl Letterhead {
    /// The `head_type` consumed by later passes (head-family carry, this_ref).
    /// ADR-0029 §5: the letterhead outranks matching body mentions, so the
    /// kind read here is never overridden by a citation from the body.
    pub fn head_type(&self) -> &str {
        &self.kind
    }
}

/// Recognizes the document letterhead from the leading paragraphs.
///
/// Fail-closed: court letterheads, unknown heads, and recognized kinds with no
/// source requisites all yield `None`; date/number are never fabricated. A
/// recognized letterhead carries a validated source-local [`LocalSpan`].
pub fn recognize_letterhead(paras: &[String]) -> Option<Letterhead> {
    if paras.is_empty() {
        return None;
    }
    let zone = paras.len().min(LETTERHEAD_HEAD_ZONE);
    let head_paras = &paras[..zone];

    // Court letterhead: fail-closed (ADR-0029 §5). Bounded to the head zone
    // so a body mention («арбитражных судах») cannot misclassify an act.
    if is_court_head(&court_tokens(head_paras)) {
        return None;
    }

    let head_raw = head_paras.join("\n");
    let head_lower = lower_ws(&head_raw);
    let (class, kind, issuer) = detect_letterhead_kind(&head_raw, &head_lower)?;

    let anchors = npa_anchor::scan_anchors(head_paras);
    let first = anchors.first();

    let (date, number, evidence) = match class {
        HeadClass::Fas => {
            let date = first
                .map(|a| a.date.clone())
                .unwrap_or_else(|| "—".to_string());
            match (find_case_number(head_paras), first) {
                (Some((number, span)), _) => (date, number, span),
                (None, Some(a)) => (date, a.number.clone(), a.span),
                (None, None) => return None,
            }
        }
        _ => {
            let anchor = first?;
            (anchor.date.clone(), anchor.number.clone(), anchor.span)
        }
    };

    let para = paras.get(evidence.block)?;
    if npa_anchor::check_span(para, evidence).is_err() {
        return None;
    }

    Some(Letterhead {
        kind,
        issuer,
        date,
        number,
        evidence,
        status: LetterheadStatus::Recognized,
    })
}

fn detect_letterhead_kind(head_raw: &str, head_lower: &str) -> Option<(HeadClass, String, String)> {
    // Приказ <issuer>: an explicit issuer phrase wins; the table is a fallback
    // for uppercase ministry letterheads (issuer on its own line).
    if find_word_ci(head_raw, "приказ").is_some() {
        let issuer = generic_issuer_after_prikaz(head_raw)
            .or_else(|| issuer_from_table(head_lower).map(str::to_string))
            .unwrap_or_default();
        let kind = if issuer.is_empty() {
            "Приказ".to_string()
        } else {
            format!("Приказ {issuer}")
        };
        return Some((HeadClass::Prikaz, kind, issuer));
    }
    if head_lower.contains("постановлен") && head_lower.contains("правительств")
    {
        return Some((
            HeadClass::Postanovlenie,
            "Постановление Правительства РФ".to_string(),
            "Правительство РФ".to_string(),
        ));
    }
    if head_lower.contains("распоряжен") && head_lower.contains("правительств")
    {
        return Some((
            HeadClass::Rasporyazhenie,
            "распоряжение Правительства РФ".to_string(),
            "Правительство РФ".to_string(),
        ));
    }
    if find_word_ci(head_raw, "указ").is_some() && head_lower.contains("президента") {
        return Some((
            HeadClass::Ukaz,
            "Указ Президента РФ".to_string(),
            "Президент РФ".to_string(),
        ));
    }
    if let Some(label) = fas_label(head_raw, head_lower) {
        let issuer = if head_lower.contains("уфас")
            || (head_lower.contains("управлени") && head_lower.contains("федеральн"))
        {
            "УФАС России"
        } else {
            "ФАС России"
        };
        return Some((
            HeadClass::Fas,
            format!("{label} {issuer}"),
            issuer.to_string(),
        ));
    }
    None
}

/// РЕШЕНИЕ / ПРЕДПИСАНИЕ / ОПРЕДЕЛЕНИЕ in an antitrust letterhead.
fn fas_label(head_raw: &str, head_lower: &str) -> Option<&'static str> {
    let fas_context = head_lower.contains("фас")
        || head_lower.contains("уфас")
        || head_lower.contains("антимонопольн");
    if !fas_context {
        return None;
    }
    if find_word_ci(head_raw, "решение").is_some() {
        Some("Решение")
    } else if find_word_ci(head_raw, "предписание").is_some() {
        Some("Предписание")
    } else if find_word_ci(head_raw, "определение").is_some() {
        Some("Определение")
    } else {
        None
    }
}

/// Lowercase, whitespace-collapsed view for the data-table lookup.
fn lower_ws(s: &str) -> String {
    s.to_lowercase()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

fn issuer_from_table(head_lower: &str) -> Option<&'static str> {
    LETTERHEAD_ISSUERS
        .iter()
        .find(|(pattern, _)| head_lower.contains(pattern))
        .map(|(_, short)| *short)
}

/// Captures the `issuer` phrase that follows an explicit `Приказ` token, e.g.
/// «Приказ Минэкономразвития России от …» -> «Минэкономразвития России».
/// Stops at the first non-capitalized token (`от`, `об`, `N`, …).
fn generic_issuer_after_prikaz(head: &str) -> Option<String> {
    let idx = find_word_ci(head, "приказ")?;
    let rest = &head[idx + "приказ".len()..];
    let mut words: Vec<String> = Vec::new();
    for raw in rest.split_whitespace() {
        let token = raw.trim_matches(|c: char| !(c.is_alphanumeric() || c == '-'));
        if token.is_empty() {
            break;
        }
        let first = token.chars().next()?;
        if !first.is_uppercase() {
            break;
        }
        if token == "N" || token == "n" || token == "№" {
            break;
        }
        words.push(token.to_string());
        if words.len() >= 8 {
            break;
        }
    }
    if words.is_empty() {
        None
    } else {
        Some(words.join(" "))
    }
}

/// Case number from `по делу N <num>` (antitrust letterheads).
fn find_case_number(paras: &[String]) -> Option<(String, LocalSpan)> {
    for (block, para) in paras.iter().enumerate() {
        let pos = match find_ci(para, "по делу") {
            Some(pos) => pos,
            None => continue,
        };
        let rest = &para[pos + "по делу".len()..];
        let mut i = 0usize;
        while i < rest.len() && rest.as_bytes()[i].is_ascii_whitespace() {
            i += 1;
        }
        if rest[i..].starts_with('N') || rest[i..].starts_with('n') {
            i += 1;
        } else if rest[i..].starts_with('№') {
            i += '№'.len_utf8();
        }
        while i < rest.len() && rest.as_bytes()[i].is_ascii_whitespace() {
            i += 1;
        }
        let start = pos + "по делу".len() + i;
        let mut end = start;
        while end < para.len() {
            let ch = para[end..].chars().next().unwrap_or('\0');
            if ch.is_alphanumeric() || matches!(ch, '/' | '-' | '.') {
                end += ch.len_utf8();
            } else {
                break;
            }
        }
        if end > start {
            let span = LocalSpan { block, start, end };
            if npa_anchor::check_span(para, span).is_ok() {
                return Some((para[start..end].to_string(), span));
            }
        }
    }
    None
}

/// Tokens of the head zone (lowercased, punctuation-trimmed) for the court
/// guard.
fn court_tokens(paras: &[String]) -> Vec<String> {
    paras
        .iter()
        .flat_map(|p| p.split_whitespace())
        .map(|w| {
            w.trim_matches(|c: char| !c.is_alphanumeric())
                .to_lowercase()
        })
        .filter(|w| !w.is_empty())
        .collect()
}

/// Court letterhead marker: a court stem followed by «суд…» (or «суд общей
/// юрисдикции»), mirroring the prototype court regex but bounded to tokens.
fn is_court_head(words: &[String]) -> bool {
    const STEMS: &[&str] = &[
        "верховн",
        "арбитражн",
        "кассационн",
        "апелляционн",
        "областн",
        "краев",
        "районн",
        "городск",
        "миров",
    ];
    for i in 0..words.len() {
        if STEMS.iter().any(|stem| words[i].starts_with(stem))
            && i + 1 < words.len()
            && words[i + 1].starts_with("суд")
        {
            return true;
        }
    }
    for i in 0..words.len().saturating_sub(2) {
        if words[i] == "суд"
            && words[i + 1].starts_with("общей")
            && words[i + 2].starts_with("юрисдикц")
        {
            return true;
        }
    }
    false
}

/// Case-insensitive substring search; returns the byte offset of the first
/// match. Cyrillic case-folding is applied per char, so the offset is always a
/// valid char boundary of `hay`.
fn find_ci(hay: &str, needle: &str) -> Option<usize> {
    let hay_chars: Vec<(usize, char)> = hay.char_indices().collect();
    let needle_chars: Vec<char> = needle.chars().collect();
    if needle_chars.is_empty() || hay_chars.len() < needle_chars.len() {
        return None;
    }
    for i in 0..=hay_chars.len() - needle_chars.len() {
        let matched = needle_chars.iter().enumerate().all(|(k, nc)| {
            let hc = hay_chars[i + k].1;
            hc.to_lowercase().next().unwrap_or(hc) == nc.to_lowercase().next().unwrap_or(*nc)
        });
        if matched {
            return Some(hay_chars[i].0);
        }
    }
    None
}

/// Whole-word case-insensitive search; returns the byte offset of the match.
fn find_word_ci(hay: &str, needle: &str) -> Option<usize> {
    let hay_chars: Vec<(usize, char)> = hay.char_indices().collect();
    let needle_chars: Vec<char> = needle.chars().collect();
    if needle_chars.is_empty() || hay_chars.len() < needle_chars.len() {
        return None;
    }
    let is_word = |c: char| c.is_alphanumeric() || c == '_';
    for i in 0..=hay_chars.len() - needle_chars.len() {
        let matched = needle_chars.iter().enumerate().all(|(k, nc)| {
            let hc = hay_chars[i + k].1;
            hc.to_lowercase().next().unwrap_or(hc) == nc.to_lowercase().next().unwrap_or(*nc)
        });
        if !matched {
            continue;
        }
        let before_ok = i == 0 || !is_word(hay_chars[i - 1].1);
        let end = i + needle_chars.len();
        let after_ok = end >= hay_chars.len() || !is_word(hay_chars[end].1);
        if before_ok && after_ok {
            return Some(hay_chars[i].0);
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Approved-by linking for named annexes (ADR-0029 §4/§5, ADR-0016).
//
// A named annex («Правила», «Положение», «Методические рекомендации», …) that
// has no `date`+`number` of its own is a reference mention: it quotes the
// approving act but never merges with its Work (Work ≠ approver, ADR-0016).
// The pass derives new records and never mutates the typed stream. Windows are
// ±450/700 **characters** (ADR-0029 §5) measured on a flattened view of the
// paragraphs; evidence is always the two separate source-local anchors.
// ---------------------------------------------------------------------------

/// A one- or two-word annex stem. `first`/`second` are lowercase prefixes; the
/// matched word may inflect after the prefix.
struct AnnexStem {
    canon: &'static str,
    first: &'static str,
    second: Option<&'static str>,
}

/// Annex types whose bare mention (no own requisites) becomes a named annex.
/// The set mirrors the differential reference
/// (`scripts/m207_context_graph_demo.py` `_link_approved_by`).
const ANNEX_STEMS: &[AnnexStem] = &[
    AnnexStem {
        canon: "Правила",
        first: "правил",
        second: None,
    },
    AnnexStem {
        canon: "Положение",
        first: "положени",
        second: None,
    },
    AnnexStem {
        canon: "Перечень",
        first: "перечен",
        second: None,
    },
    AnnexStem {
        canon: "Порядок",
        first: "порядк",
        second: None,
    },
    AnnexStem {
        canon: "Требования",
        first: "требовани",
        second: None,
    },
    AnnexStem {
        canon: "Методические рекомендации",
        first: "методическ",
        second: Some("рекомендац"),
    },
    AnnexStem {
        canon: "Регламент",
        first: "регламент",
        second: None,
    },
    AnnexStem {
        canon: "Конкурсная документация",
        first: "конкурсн",
        second: Some("документац"),
    },
];

/// A bounded named-annex occurrence in a paragraph.
struct AnnexHit {
    canon: &'static str,
    capitalized: bool,
    span: LocalSpan,
}

fn is_letter_char(c: char) -> bool {
    c.is_alphabetic()
}

/// Matches `prefix` (case-insensitive) at char index `i` and returns the char
/// index one past the end of the whole word.
fn match_annex_prefix(chars: &[char], i: usize, prefix: &str) -> Option<usize> {
    let p: Vec<char> = prefix.chars().collect();
    if i + p.len() > chars.len() {
        return None;
    }
    for (k, want) in p.iter().enumerate() {
        let got = chars[i + k].to_lowercase().next().unwrap_or(chars[i + k]);
        if got != *want {
            return None;
        }
    }
    let mut end = i + p.len();
    while end < chars.len() && is_letter_char(chars[end]) {
        end += 1;
    }
    Some(end)
}

/// Matches an annex stem at char index `i` (left word boundary enforced).
fn match_annex_at(chars: &[char], i: usize, stem: &AnnexStem) -> Option<usize> {
    if i > 0 && is_letter_char(chars[i - 1]) {
        return None;
    }
    let end = match_annex_prefix(chars, i, stem.first)?;
    if let Some(second) = stem.second {
        let mut j = end;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j == end {
            return None;
        }
        return match_annex_prefix(chars, j, second);
    }
    Some(end)
}

/// Scans every paragraph for annex-stem occurrences with a source-local span.
fn find_annex_hits(paras: &[String]) -> Vec<AnnexHit> {
    let mut hits = Vec::new();
    for (block, para) in paras.iter().enumerate() {
        let chars: Vec<char> = para.chars().collect();
        let mut offs: Vec<usize> = Vec::with_capacity(chars.len() + 1);
        let mut b = 0usize;
        for c in &chars {
            offs.push(b);
            b += c.len_utf8();
        }
        offs.push(b);
        let mut i = 0usize;
        'scan: while i < chars.len() {
            for stem in ANNEX_STEMS {
                if let Some(end) = match_annex_at(&chars, i, stem) {
                    hits.push(AnnexHit {
                        canon: stem.canon,
                        capitalized: chars[i].is_uppercase(),
                        span: LocalSpan {
                            block,
                            start: offs[i],
                            end: offs[end],
                        },
                    });
                    i = end;
                    continue 'scan;
                }
            }
            i += 1;
        }
    }
    hits
}

/// A named type owns its requisites when a typed anchor directly follows the
/// mention (only whitespace between): then it is a regular anchored member.
fn annex_has_own_requisites(para: &str, hit: &AnnexHit, typed: &[TypedMember]) -> bool {
    typed.iter().any(|m| {
        m.span.block == hit.span.block
            && m.span.start >= hit.span.end
            && m.span.start <= para.len()
            && para[hit.span.end..m.span.start].trim().is_empty()
    })
}

/// The approver verb set of the differential reference.
fn approve_verb(text: &str) -> bool {
    find_ci(text, "утвержденн").is_some()
        || find_ci(text, "об утвержден").is_some()
        || find_ci(text, "вместе с").is_some()
}

/// A flattened view of the paragraph slice with a global byte index per local
/// anchor. Windows are measured in characters (ADR-0029 §5).
struct FlatDoc {
    text: String,
    block_start: Vec<usize>,
}

impl FlatDoc {
    fn new(paras: &[String]) -> Self {
        let mut text = String::new();
        let mut block_start = Vec::with_capacity(paras.len());
        for (i, para) in paras.iter().enumerate() {
            if i > 0 {
                text.push('\n');
            }
            block_start.push(text.len());
            text.push_str(para);
        }
        FlatDoc { text, block_start }
    }

    fn global_byte(&self, span: LocalSpan) -> usize {
        self.block_start
            .get(span.block)
            .copied()
            .unwrap_or(0)
            .saturating_add(span.start)
    }

    /// Number of `char`s in `text[a..b]` (both on char boundaries).
    fn char_distance(&self, a: usize, b: usize) -> usize {
        if a >= b {
            return 0;
        }
        self.text[a..b].chars().count()
    }

    /// Byte offset `n` characters after `byte_start` (clamped to the end).
    fn advance_chars(&self, byte_start: usize, n: usize) -> usize {
        advance_chars_str(&self.text, byte_start, n)
    }
}

fn advance_chars_str(s: &str, byte_start: usize, n: usize) -> usize {
    let mut idx = byte_start;
    let mut seen = 0usize;
    while idx < s.len() && seen < n {
        let c = s[idx..].chars().next().unwrap_or('\0');
        idx += c.len_utf8();
        seen += 1;
    }
    idx
}

/// Picks the approving act for an annex.
///
/// Direct later window: `0 < approver − annex < 450` chars, verb in the gap.
/// Otherwise earlier window: `0 < annex − approver < 700` chars, verb in
/// `approver..annex+80`. Otherwise the «вместе с …» list fallback: the last
/// dated act before the first `вместе с` token.
fn find_approver(flat: &FlatDoc, annex: &AnnexHit, typed: &[TypedMember]) -> Option<usize> {
    let annex_g = flat.global_byte(annex.span);

    let later = typed
        .iter()
        .enumerate()
        .filter_map(|(id, m)| {
            let g = flat.global_byte(m.span);
            (g > annex_g && flat.char_distance(annex_g, g) < 450).then_some((g, id))
        })
        .min_by_key(|(g, _)| *g);
    if let Some((g, id)) = later {
        if approve_verb(&flat.text[annex_g..g]) {
            return Some(id);
        }
    }

    let earlier = typed
        .iter()
        .enumerate()
        .filter_map(|(id, m)| {
            let g = flat.global_byte(m.span);
            (g < annex_g && flat.char_distance(g, annex_g) < 700).then_some((g, id))
        })
        .max_by_key(|(g, _)| *g);
    if let Some((g, id)) = earlier {
        let end = flat.advance_chars(annex_g, 80);
        if approve_verb(&flat.text[g..end]) {
            return Some(id);
        }
    }

    if let Some(vmeste) = find_ci(&flat.text, "вместе с") {
        if annex_g > vmeste {
            let before = typed
                .iter()
                .enumerate()
                .filter_map(|(id, m)| {
                    let g = flat.global_byte(m.span);
                    (g < vmeste).then_some((g, id))
                })
                .max_by_key(|(g, _)| *g);
            if let Some((_, id)) = before {
                return Some(id);
            }
        }
    }
    None
}

/// Finds the first `DD.MM.YYYY` in a slice (char-safe).
fn dot_date_in(slice: &str) -> Option<String> {
    let chars: Vec<char> = slice.chars().collect();
    let mut i = 0usize;
    while i + 10 <= chars.len() {
        let c = |k: usize| chars[i + k];
        if c(0).is_ascii_digit()
            && c(1).is_ascii_digit()
            && c(2) == '.'
            && c(3).is_ascii_digit()
            && c(4).is_ascii_digit()
            && c(5) == '.'
            && c(6).is_ascii_digit()
            && c(7).is_ascii_digit()
            && c(8).is_ascii_digit()
            && c(9).is_ascii_digit()
        {
            return Some(chars[i..i + 10].iter().collect());
        }
        i += 1;
    }
    None
}

/// Case-sensitive whole-word search (the `_CORP_ACTOR` tokens are uppercase).
fn find_word_cs(hay: &str, needle: &str) -> Option<usize> {
    let chars: Vec<(usize, char)> = hay.char_indices().collect();
    let pat: Vec<char> = needle.chars().collect();
    if pat.is_empty() || chars.len() < pat.len() {
        return None;
    }
    let is_word = |c: char| c.is_alphanumeric() || c == '_';
    for i in 0..=chars.len() - pat.len() {
        if (0..pat.len()).all(|k| chars[i + k].1 == pat[k])
            && (i == 0 || !is_word(chars[i - 1].1))
            && (i + pat.len() >= chars.len() || !is_word(chars[i + pat.len()].1))
        {
            return Some(chars[i].0);
        }
    }
    None
}

fn corp_actor(window: &str) -> bool {
    ["ООО", "АО", "ПАО", "ИП", "ЗАО"]
        .iter()
        .any(|token| find_word_cs(window, token).is_some())
}

fn named_annex_member(
    id: usize,
    hit: &AnnexHit,
    approved_by: Option<String>,
    derivation: LinkDerivation,
) -> LinkedMember {
    LinkedMember {
        id,
        kind: LinkedMemberKind::NamedType,
        date: String::new(),
        number: String::new(),
        type_name: hit.canon.to_string(),
        approved_by,
        alias: None,
        derivation,
        evidence: hit.span,
        provenance: vec![hit.span],
    }
}

/// Links named annexes to their approving acts.
///
/// Returns the derived `NamedType` members (ids start after the typed-stream
/// indices so they never collide with `anchored_members`), the `ApprovedBy`
/// relations, and the fail-closed diagnostics. A corporate regulation is
/// refused: its `approved_by` is the corporate body, its derivation is
/// [`LinkDerivation::Refused`], a [`LinkDiagnostic::HeadFamilyCarryRefused`]
/// is emitted, and **no** normative citation/relation is minted. A lowercase
/// annex mention without an approving act is not a named annex (ADR-0029 §5).
pub fn link_approved_by(
    paras: &[String],
) -> (Vec<LinkedMember>, Vec<LinkedRelation>, Vec<LinkDiagnostic>) {
    let (typed, _anchor_diagnostics) = npa_typed::scan_typed_diagnosed(paras);
    let flat = FlatDoc::new(paras);
    let hits = find_annex_hits(paras);
    let annex_base = typed.len();

    let mut members: Vec<LinkedMember> = Vec::new();
    let mut relations: Vec<LinkedRelation> = Vec::new();
    let mut diagnostics: Vec<LinkDiagnostic> = Vec::new();

    for hit in &hits {
        let Some(para) = paras.get(hit.span.block) else {
            continue;
        };
        if annex_has_own_requisites(para, hit, &typed) {
            continue;
        }
        let annex_g = flat.global_byte(hit.span);

        // Corporate regulation: refuse, mint no normative citation.
        if hit.canon == "Регламент" {
            let window_end = flat.advance_chars(annex_g, 280);
            let window = &flat.text[annex_g..window_end];
            if let Some(offset) = find_ci(window, "генеральным директором") {
                let tail_start = annex_g + offset;
                let tail_end = flat.advance_chars(tail_start, 80);
                let approved = match dot_date_in(&flat.text[tail_start..tail_end]) {
                    Some(date) => format!("генеральный директор от {date}"),
                    None => "генеральный директор (дата обрезана в seed)".to_string(),
                };
                let id = annex_base + members.len();
                members.push(named_annex_member(
                    id,
                    hit,
                    Some(approved),
                    LinkDerivation::Refused,
                ));
                diagnostics.push(LinkDiagnostic::HeadFamilyCarryRefused);
                continue;
            }
            if find_ci(window, "генеральный директор").is_some() || corp_actor(window)
            {
                let id = annex_base + members.len();
                members.push(named_annex_member(
                    id,
                    hit,
                    Some("генеральный директор (дата обрезана в seed)".to_string()),
                    LinkDerivation::Refused,
                ));
                diagnostics.push(LinkDiagnostic::HeadFamilyCarryRefused);
                continue;
            }
        }

        let approver = find_approver(&flat, hit, &typed);
        let approved_by = approver.map(|id| {
            format!(
                "{} от {} N {}",
                typed[id].type_name, typed[id].date, typed[id].number
            )
        });

        // Capitalization gate on uncited annexes (ADR-0029 §5): an uncited
        // lowercase mention is not a named annex.
        if approved_by.is_none() && !hit.capitalized {
            continue;
        }

        let has_approver = approver.is_some();
        let id = annex_base + members.len();
        let derivation = if has_approver {
            LinkDerivation::ApprovedByQuote
        } else {
            LinkDerivation::NamedTypeText
        };
        members.push(named_annex_member(id, hit, approved_by, derivation));
        if let Some(approver_id) = approver {
            relations.push(LinkedRelation {
                kind: LinkedRelationKind::ApprovedBy,
                from_id: id,
                to_id: approver_id,
                evidence: vec![hit.span, typed[approver_id].span],
                why: "named annex quotes its approving act; Work is never merged (ADR-0016)",
            });
        }
    }

    (members, relations, diagnostics)
}

// ---------------------------------------------------------------------------
// Narrow head-family carry (ADR-0029 §4, differential reference
// `CTX_CARRY`/`_ctx_carry_type` in `scripts/m207_context_graph_demo.py`).
// ---------------------------------------------------------------------------

/// Issuer phrases of the narrow carry cliché, longest first.
const CONTEXT_CARRY_ISSUERS: &[(&str, &str)] = &[
    ("пленума верховного суда", "Пленума Верховного Суда"),
    ("конституционного суда", "Конституционного суда"),
    ("верховного суда", "Верховного Суда"),
    ("антимонопольного органа", "антимонопольного органа"),
];

/// A typeless quoted requisite that receives a head family inside the narrow
/// «правовой позиции … изложенной в Постановлении/Определении от DATE N»
/// cliché. This is a reference mention, never a Work or a Binding (ADR-0019).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeadFamilyCarry {
    pub family: String,
    pub issuer: String,
    pub date: String,
    pub number: String,
    pub evidence: Vec<LocalSpan>,
    pub why: &'static str,
}

fn ctx_carry_type(issuer_kind: &str, kind_word: &str) -> Option<String> {
    let fold = issuer_kind.to_lowercase();
    let act = if kind_word.starts_with("Пост") {
        "Постановление"
    } else {
        "Определение"
    };
    if fold.contains("конституционн") {
        Some(format!("{act} КС РФ"))
    } else if fold.contains("пленума") {
        (act == "Постановление").then(|| "Постановление Пленума ВС РФ".to_string())
    } else if fold.contains("верховного") {
        Some(format!("{act} ВС РФ"))
    } else if fold.contains("антимонопольн") {
        Some("Решение УФАС России".to_string())
    } else {
        None
    }
}

/// Carries a head family onto typeless quoted requisites, but only inside the
/// narrow cliché. Outside it, a bare requisite keeps its own (absent) type —
/// proximity is never evidence (fail-closed).
pub fn carry_head_family(paras: &[String]) -> Vec<HeadFamilyCarry> {
    let anchors = npa_anchor::scan_anchors(paras);
    let mut carries = Vec::new();
    for (block, para) in paras.iter().enumerate() {
        // Earliest issuer phrase in this block.
        let mut best: Option<(usize, usize, &'static str)> = None;
        for (pattern, kind) in CONTEXT_CARRY_ISSUERS {
            if let Some(start) = find_ci(para, pattern) {
                let end = start + pattern.len();
                if best.is_none_or(|(bs, _, _)| start < bs) {
                    best = Some((start, end, kind));
                }
            }
        }
        let Some((issuer_start, issuer_end, issuer_kind)) = best else {
            continue;
        };
        let win_end = advance_chars_str(para, issuer_end, 200);
        let Some(izl_rel) = find_ci(&para[issuer_end..win_end], "изложенн") else {
            continue;
        };
        let after = &para[issuer_end + izl_rel..];
        let Some(v_rel) = find_ci(after, " в ") else {
            continue;
        };
        let from = issuer_end + izl_rel + v_rel + " в ".len();
        let kind_end = advance_chars_str(para, from, 60);
        let slice = &para[from..kind_end];
        let kind_word = if find_ci(slice, "постановлени").is_some() {
            "Постановление"
        } else if find_ci(slice, "определени").is_some() {
            "Определение"
        } else {
            continue;
        };
        let Some(anchor) = anchors
            .iter()
            .find(|a| a.span.block == block && a.span.start >= from && a.span.start <= kind_end)
        else {
            continue;
        };
        let Some(family) = ctx_carry_type(issuer_kind, kind_word) else {
            continue;
        };
        let issuer_span = LocalSpan {
            block,
            start: issuer_start,
            end: issuer_end,
        };
        if npa_anchor::check_span(para, issuer_span).is_err() {
            continue;
        }
        carries.push(HeadFamilyCarry {
            family,
            issuer: issuer_kind.to_string(),
            date: anchor.date.clone(),
            number: anchor.number.clone(),
            evidence: vec![issuer_span, anchor.span],
            why: "quoted requisite inside a narrow context-carry cliché; a reference mention, never a Binding (ADR-0019)",
        });
    }
    carries
}

// ---------------------------------------------------------------------------
// Scoped aliases and this-document references (ADR-0029 §4, D385).
//
// Differential reference: `collect_aliases` / `_nearest_member` / `_alias_keys`
// / `_is_party_alias` / `_short_ref_covered` / `THIS_REF` / `UKAZANNY` in
// `scripts/m207_context_graph_demo.py`.
//
// A `(далее — X)` declaration binds an alias only inside the document that
// declares it (D385 scoped_alias, not `CurrentDocumentRequisites`). A short
// reference resolves only through that per-document table; without a
// declaration there is no binding (fail-closed). A `настоящ…` reference points
// at this document's own head or annex — never at the nearest foreign act. The
// pass derives new records; it never mutates `TypedMember`.
// ---------------------------------------------------------------------------

/// A resolved `(далее — X)` declaration: the alias wording, its search keys,
/// and the target member it binds to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AliasBinding {
    /// The declared alias wording, e.g. `Закон N 2487-1`.
    pub alias: String,
    /// Normalized search keys derived from the wording (`_alias_keys`).
    pub keys: Vec<String>,
    /// Id of the target in the `anchored_members` + `link_approved_by` space.
    pub target_id: usize,
    pub target_type: String,
    pub target_date: String,
    pub target_number: String,
    /// Evidence for the whole `(далее — X)` declaration.
    pub declaration_evidence: LocalSpan,
    /// Evidence for the target member occurrence.
    pub target_evidence: LocalSpan,
}

/// Searchable member (typed anchor or named annex) with a stable id and a
/// character position inside its block.
#[derive(Debug, Clone)]
struct SearchMember {
    id: usize,
    type_name: String,
    date: String,
    number: String,
    span: LocalSpan,
    char_pos: usize,
}

struct DaleeHit {
    wording: String,
    span: LocalSpan,
}

struct ShortRefHit {
    written: String,
    span: LocalSpan,
}

struct ThisRefHit {
    noun: String,
    span: LocalSpan,
}

struct UkazannyHit {
    span: LocalSpan,
}

fn member_kind(date: &str, number: &str) -> LinkedMemberKind {
    if date.is_empty() || date == "—" || number.is_empty() || number == "—" {
        LinkedMemberKind::NamedType
    } else {
        LinkedMemberKind::Anchored
    }
}

fn fail_closed_this_ref(id: usize, canon: &str, evidence: LocalSpan) -> LinkedMember {
    LinkedMember {
        id,
        kind: LinkedMemberKind::NamedType,
        date: "—".to_string(),
        number: "—".to_string(),
        type_name: canon.to_string(),
        approved_by: None,
        alias: None,
        derivation: LinkDerivation::ThisDocumentRef,
        evidence,
        provenance: vec![evidence],
    }
}

/// Builds the searchable member set: typed anchors first (ids are the typed
/// stream indices), then named annexes (ids continue after the typed stream,
/// matching `link_approved_by`).
fn build_search_members(paras: &[String]) -> Vec<SearchMember> {
    let (typed, _) = npa_typed::scan_typed_diagnosed(paras);
    let (annexes, _, _) = link_approved_by(paras);
    let mut out = Vec::with_capacity(typed.len() + annexes.len());
    for (id, member) in typed.iter().enumerate() {
        out.push(SearchMember {
            id,
            type_name: member.type_name.clone(),
            date: member.date.clone(),
            number: member.number.clone(),
            span: member.span,
            char_pos: char_index(paras, member.span),
        });
    }
    for (offset, member) in annexes.iter().enumerate() {
        out.push(SearchMember {
            id: typed.len() + offset,
            type_name: member.type_name.clone(),
            date: member.date.clone(),
            number: member.number.clone(),
            span: member.evidence,
            char_pos: char_index(paras, member.evidence),
        });
    }
    out
}

fn char_index(paras: &[String], span: LocalSpan) -> usize {
    paras
        .get(span.block)
        .map(|para| char_len_before(para, span.start))
        .unwrap_or(0)
}

fn char_len_before(text: &str, byte: usize) -> usize {
    if byte >= text.len() {
        return text.chars().count();
    }
    text[..byte].chars().count()
}

fn char_offsets(text: &str) -> (Vec<char>, Vec<usize>) {
    let chars: Vec<char> = text.chars().collect();
    let mut offs = Vec::with_capacity(chars.len() + 1);
    let mut byte = 0usize;
    for c in &chars {
        offs.push(byte);
        byte += c.len_utf8();
    }
    offs.push(byte);
    (chars, offs)
}

fn match_word_ci(chars: &[char], i: usize, needle: &str) -> Option<usize> {
    let want: Vec<char> = needle.chars().collect();
    if i + want.len() > chars.len() {
        return None;
    }
    for (k, expected) in want.iter().enumerate() {
        let got = chars[i + k].to_lowercase().next().unwrap_or(chars[i + k]);
        let expected = expected.to_lowercase().next().unwrap_or(*expected);
        if got != expected {
            return None;
        }
    }
    Some(i + want.len())
}

fn consume_letters(chars: &[char], mut i: usize) -> usize {
    while i < chars.len() && is_letter_char(chars[i]) {
        i += 1;
    }
    i
}

fn is_num_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || ('А'..='Я').contains(&c) || ('а'..='я').contains(&c)
}

fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn is_number_token(s: &str) -> bool {
    let chars: Vec<char> = s.chars().collect();
    if chars.is_empty() {
        return false;
    }
    let mut prev_num = false;
    for (i, c) in chars.iter().enumerate() {
        if is_num_char(*c) {
            prev_num = true;
            continue;
        }
        if (*c == '/' || *c == '-') && prev_num && i + 1 < chars.len() && is_num_char(chars[i + 1])
        {
            prev_num = false;
            continue;
        }
        return false;
    }
    prev_num
}

/// Scans `(...)` declarations of the closed `(далее - X)` / `(далее — X)`
/// surface. Returns the wording and the span of the whole parenthesized group.
fn find_dalee(block: usize, para: &str) -> Vec<DaleeHit> {
    let (chars, offs) = char_offsets(para);
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        if chars[i] != '(' {
            i += 1;
            continue;
        }
        let Some(mut j) = match_word_ci(&chars, i + 1, "далее") else {
            i += 1;
            continue;
        };
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j >= chars.len() || (chars[j] != '-' && chars[j] != '—') {
            i += 1;
            continue;
        }
        j += 1;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        let value_start = j;
        let mut end = j;
        while end < chars.len() && chars[end] != ')' {
            end += 1;
        }
        if end >= chars.len() || end == value_start {
            i += 1;
            continue;
        }
        let wording = collapse_ws(&para[offs[value_start]..offs[end]]);
        if !wording.is_empty() {
            out.push(DaleeHit {
                wording,
                span: LocalSpan {
                    block,
                    start: offs[i],
                    end: offs[end + 1],
                },
            });
        }
        i = end + 1;
    }
    out
}

/// A party/role alias wording (`_is_party_alias`): never a scoped alias.
fn is_party_alias(wording: &str) -> bool {
    const HEADS: &[&str] = &[
        "заявитель",
        "истец",
        "ответчик",
        "оператор",
        "организатор",
        "продажа",
        "еис",
    ];
    const NEEDLES: &[&str] = &[
        "организатор",
        "заявитель",
        "истец",
        "ответчик",
        "оператор",
        "продажа",
        "еис",
        "конкурсный отбор",
    ];
    let folded = collapse_ws(&wording.to_lowercase());
    let head = folded.split_whitespace().next().unwrap_or("");
    if HEADS.contains(&head) {
        return true;
    }
    NEEDLES.iter().any(|needle| folded.contains(needle))
}

fn alias_stem(folded: &str) -> Option<String> {
    let first = folded.split_whitespace().next().unwrap_or("");
    for prefix in ["закон", "постановлен", "приказ", "указ"] {
        if first.starts_with(prefix) {
            let stem = first.trim_end_matches(|c| "ыиауеом".contains(c));
            return Some(stem.to_string());
        }
    }
    None
}

fn alias_number(folded: &str) -> Option<String> {
    let words: Vec<&str> = folded.split_whitespace().collect();
    for i in 0..words.len().saturating_sub(1) {
        if words[i] == "n" && is_number_token(words[i + 1]) {
            return Some(words[i + 1].to_string());
        }
    }
    None
}

fn alias_annex_key(folded: &str) -> Option<&'static str> {
    if folded.starts_with("положен") {
        return Some("положение");
    }
    if folded.starts_with("правил") {
        return Some("правила");
    }
    if folded.starts_with("протокол") {
        return Some("протокол");
    }
    if folded == "регламент" || folded == "регламента" {
        return Some("регламент");
    }
    if folded.starts_with("методическ") {
        return Some("методические рекомендации");
    }
    None
}

/// `_alias_keys`: full name, `закон n 44-фз`, the bare number, and the annex
/// key. A bare `закон` is deliberately absent — it would merge several acts.
fn alias_keys(wording: &str) -> Vec<String> {
    let folded = collapse_ws(&wording.to_lowercase()).replace('№', "n");
    let mut keys: Vec<String> = Vec::new();
    if !folded.is_empty() {
        keys.push(folded.clone());
    }
    if let Some(number) = alias_number(&folded) {
        keys.push(number.clone());
        keys.push(format!("n {number}"));
        if let Some(stem) = alias_stem(&folded) {
            keys.push(format!("{stem} n {number}"));
        }
    }
    if let Some(key) = alias_annex_key(&folded) {
        keys.push(key.to_string());
    }
    let mut out: Vec<String> = Vec::with_capacity(keys.len());
    for key in keys {
        if !key.is_empty() && !out.contains(&key) {
            out.push(key);
        }
    }
    out
}

/// `_nearest_member`: binds a declaration to the nearest same-block member to
/// its left. Named annex types only bind to their own kind (never to the
/// approving act); an explicit `N` only binds to a matching number; otherwise
/// the last member to the left. No suitable member -> `None` (fail-closed).
fn nearest_member<'a>(
    search: &'a [SearchMember],
    block: usize,
    decl_pos: usize,
    wording: &str,
) -> Option<&'a SearchMember> {
    let folded = collapse_ws(&wording.to_lowercase());
    let mut before: Vec<&SearchMember> = search
        .iter()
        .filter(|m| m.span.block == block && m.char_pos < decl_pos)
        .collect();
    if before.is_empty() {
        return None;
    }
    before.sort_by_key(|m| m.char_pos);
    let near = |m: &&SearchMember| decl_pos.saturating_sub(m.char_pos) < 500;

    if folded.contains("положен") || folded.contains("правил") {
        return before
            .iter()
            .rev()
            .find(|m| {
                near(m)
                    && (m.type_name.to_lowercase() == "положение"
                        || m.type_name.to_lowercase() == "правила")
            })
            .copied();
    }
    if folded.contains("документац") {
        return before
            .iter()
            .rev()
            .find(|m| near(m) && m.type_name.to_lowercase().contains("документац"))
            .copied();
    }
    if folded.contains("регламент") {
        return before
            .iter()
            .rev()
            .find(|m| near(m) && m.type_name.to_lowercase() == "регламент")
            .copied();
    }
    if folded.contains("протокол") {
        return before
            .iter()
            .rev()
            .find(|m| near(m) && m.type_name.to_lowercase() == "протокол")
            .copied();
    }
    if let Some(number) = alias_number(&folded) {
        return before
            .iter()
            .rev()
            .find(|m| m.number.to_lowercase() == number)
            .copied();
    }
    before.last().copied()
}

fn collect_aliases_internal(paras: &[String], search: &[SearchMember]) -> Vec<AliasBinding> {
    let mut out = Vec::new();
    for (block, para) in paras.iter().enumerate() {
        for decl in find_dalee(block, para) {
            if is_party_alias(&decl.wording) {
                continue;
            }
            let decl_pos = char_len_before(para, decl.span.start);
            let Some(target) = nearest_member(search, block, decl_pos, &decl.wording) else {
                continue;
            };
            out.push(AliasBinding {
                alias: decl.wording.clone(),
                keys: alias_keys(&decl.wording),
                target_id: target.id,
                target_type: target.type_name.clone(),
                target_date: target.date.clone(),
                target_number: target.number.clone(),
                declaration_evidence: decl.span,
                target_evidence: target.span,
            });
        }
    }
    out
}

/// Collects the `(далее — X)` declarations of one document into a per-document
/// alias table. Party/role aliases are dropped; declarations with no suitable
/// same-block member to the left are dropped (fail-closed).
pub fn collect_aliases(paras: &[String]) -> Vec<AliasBinding> {
    let search = build_search_members(paras);
    collect_aliases_internal(paras, &search)
}

/// Scans the closed short-reference surface
/// `(Закон|Постановление|Приказ|Указ) N <number>`.
fn find_short_refs(block: usize, para: &str) -> Vec<ShortRefHit> {
    const STEMS: &[&str] = &["закон", "постановлен", "приказ", "указ"];
    let (chars, offs) = char_offsets(para);
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        if !is_letter_char(chars[i]) || (i > 0 && is_letter_char(chars[i - 1])) {
            i += 1;
            continue;
        }
        let Some(word_end) = STEMS
            .iter()
            .find_map(|stem| match_word_ci(&chars, i, stem).map(|e| consume_letters(&chars, e)))
        else {
            i += 1;
            continue;
        };
        let mut j = word_end;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j == word_end || j >= chars.len() || (chars[j] != 'N' && chars[j] != 'n') {
            i += 1;
            continue;
        }
        j += 1;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        let num_start = j;
        let mut k = num_start;
        while k < chars.len() {
            if is_num_char(chars[k]) {
                k += 1;
                continue;
            }
            if (chars[k] == '/' || chars[k] == '-')
                && k + 1 < chars.len()
                && is_num_char(chars[k + 1])
            {
                k += 1;
                continue;
            }
            break;
        }
        if k == num_start {
            i += 1;
            continue;
        }
        out.push(ShortRefHit {
            written: collapse_ws(&para[offs[i]..offs[k]]),
            span: LocalSpan {
                block,
                start: offs[i],
                end: offs[k],
            },
        });
        i = k;
    }
    out
}

/// `_short_ref_covered`: a reference already carried by an adjacent anchor or
/// by a `далее —` declaration is not a standalone short reference.
fn short_ref_covered(para: &str, start_byte: usize, local: &[&SearchMember]) -> bool {
    let before = window_before(para, start_byte, 40);
    if ends_with_date_prefix(&before) || ends_with_dalee_dash(&before) {
        return true;
    }
    let start_char = char_len_before(para, start_byte);
    local
        .iter()
        .any(|m| start_char.abs_diff(m.char_pos) < 60 && !m.number.is_empty() && m.number != "—")
}

fn window_before(text: &str, start_byte: usize, chars: usize) -> String {
    let prefix: Vec<char> = text[..start_byte].chars().collect();
    let from = prefix.len().saturating_sub(chars);
    prefix[from..].iter().collect()
}

fn ends_with_date_prefix(s: &str) -> bool {
    let tokens: Vec<&str> = s.split_whitespace().collect();
    if tokens.len() < 2 {
        return false;
    }
    let is_date = |t: &str| {
        let b = t.as_bytes();
        b.len() == 10
            && b[0].is_ascii_digit()
            && b[1].is_ascii_digit()
            && b[2] == b'.'
            && b[3].is_ascii_digit()
            && b[4].is_ascii_digit()
            && b[5] == b'.'
            && b[6].is_ascii_digit()
            && b[7].is_ascii_digit()
            && b[8].is_ascii_digit()
            && b[9].is_ascii_digit()
    };
    tokens[tokens.len() - 2] == "от" && is_date(tokens[tokens.len() - 1])
}

fn ends_with_dalee_dash(s: &str) -> bool {
    let trimmed = s.trim_end();
    for dash in ['-', '—'] {
        if let Some(head) = trimmed.strip_suffix(dash) {
            if head.trim_end().to_lowercase().ends_with("далее") {
                return true;
            }
        }
    }
    false
}

/// Scans `настоящ… (Положение|Правила|Федеральный закон|Кодекс)`.
fn find_this_refs(block: usize, para: &str) -> Vec<ThisRefHit> {
    let (chars, offs) = char_offsets(para);
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        if !is_letter_char(chars[i]) || (i > 0 && is_letter_char(chars[i - 1])) {
            i += 1;
            continue;
        }
        let Some(na) = match_word_ci(&chars, i, "настоящ") else {
            i += 1;
            continue;
        };
        let mut j = consume_letters(&chars, na);
        let ws_start = j;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j == ws_start {
            i += 1;
            continue;
        }
        let (noun_start, noun_end) = if let Some(e) = match_word_ci(&chars, j, "положен") {
            (j, consume_letters(&chars, e))
        } else if let Some(e) = match_word_ci(&chars, j, "правил") {
            (j, consume_letters(&chars, e))
        } else if let Some(e) = match_word_ci(&chars, j, "кодекс") {
            (j, consume_letters(&chars, e))
        } else if let Some(e) = match_word_ci(&chars, j, "федеральн") {
            let mut k = consume_letters(&chars, e);
            let ws2 = k;
            while k < chars.len() && chars[k].is_whitespace() {
                k += 1;
            }
            if k == ws2 {
                i += 1;
                continue;
            }
            let Some(ze) = match_word_ci(&chars, k, "закон") else {
                i += 1;
                continue;
            };
            (j, consume_letters(&chars, ze))
        } else {
            i += 1;
            continue;
        };
        if noun_end <= noun_start {
            i += 1;
            continue;
        }
        out.push(ThisRefHit {
            noun: collapse_ws(&para[offs[noun_start]..offs[noun_end]]),
            span: LocalSpan {
                block,
                start: offs[i],
                end: offs[noun_end],
            },
        });
        i = noun_end;
    }
    out
}

fn classify_this_ref(noun: &str) -> (&'static str, &'static str) {
    let folded = noun.to_lowercase();
    if folded.contains("положен") {
        ("положение", "Положение")
    } else if folded.contains("правил") {
        ("правила", "Правила")
    } else if folded.contains("кодекс") {
        ("кодекс", "Кодекс")
    } else {
        ("федеральный закон", "Федеральный закон")
    }
}

/// Scans `указанн… Федеральн… закон…`.
fn find_ukazanny(block: usize, para: &str) -> Vec<UkazannyHit> {
    let (chars, offs) = char_offsets(para);
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        if !is_letter_char(chars[i]) || (i > 0 && is_letter_char(chars[i - 1])) {
            i += 1;
            continue;
        }
        let Some(u) = match_word_ci(&chars, i, "указанн") else {
            i += 1;
            continue;
        };
        let mut j = consume_letters(&chars, u);
        let ws = j;
        while j < chars.len() && chars[j].is_whitespace() {
            j += 1;
        }
        if j == ws {
            i += 1;
            continue;
        }
        let Some(f) = match_word_ci(&chars, j, "федеральн") else {
            i += 1;
            continue;
        };
        let mut k = consume_letters(&chars, f);
        let ws2 = k;
        while k < chars.len() && chars[k].is_whitespace() {
            k += 1;
        }
        if k == ws2 {
            i += 1;
            continue;
        }
        let Some(z) = match_word_ci(&chars, k, "закон") else {
            i += 1;
            continue;
        };
        let end = consume_letters(&chars, z);
        out.push(UkazannyHit {
            span: LocalSpan {
                block,
                start: offs[i],
                end: offs[end],
            },
        });
        i = end;
    }
    out
}

/// Resolves scoped short references and this-document references.
///
/// Returns the derived members (ids continue after `anchored_members` and
/// `link_approved_by`), the `ScopedAlias`/`ThisDocumentRef` relations, and the
/// fail-closed diagnostics. A short reference with no declaration in this
/// document mints no member ([`LinkDiagnostic::AliasWithoutDeclaration`]); a
/// `настоящий` reference with no usable head/annex mints a requisites-free
/// member ([`LinkDiagnostic::HeadUnavailable`]).
pub fn link_aliases_and_this_refs(
    paras: &[String],
) -> (Vec<LinkedMember>, Vec<LinkedRelation>, Vec<LinkDiagnostic>) {
    let (typed, _) = npa_typed::scan_typed_diagnosed(paras);
    let (annexes, _, _) = link_approved_by(paras);
    let search = build_search_members(paras);
    let bindings = collect_aliases_internal(paras, &search);
    let letterhead = recognize_letterhead(paras);
    let base = typed.len() + annexes.len();

    let mut by_key: BTreeMap<&str, &AliasBinding> = BTreeMap::new();
    for binding in &bindings {
        for key in &binding.keys {
            by_key.entry(key.as_str()).or_insert(binding);
        }
    }

    let mut members: Vec<LinkedMember> = Vec::new();
    let mut relations: Vec<LinkedRelation> = Vec::new();
    let mut diagnostics: Vec<LinkDiagnostic> = Vec::new();

    // (1) Short references resolved through this document's alias table.
    for (block, para) in paras.iter().enumerate() {
        let local: Vec<&SearchMember> = search.iter().filter(|m| m.span.block == block).collect();
        for hit in find_short_refs(block, para) {
            if short_ref_covered(para, hit.span.start, &local) {
                continue;
            }
            let keys = alias_keys(&hit.written);
            let target = keys
                .iter()
                .find_map(|key| by_key.get(key.as_str()).copied());
            let Some(binding) = target else {
                diagnostics.push(LinkDiagnostic::AliasWithoutDeclaration);
                continue;
            };
            let id = base + members.len();
            members.push(LinkedMember {
                id,
                kind: member_kind(&binding.target_date, &binding.target_number),
                date: binding.target_date.clone(),
                number: binding.target_number.clone(),
                type_name: binding.target_type.clone(),
                approved_by: None,
                alias: Some(binding.alias.clone()),
                derivation: LinkDerivation::ScopedAlias,
                evidence: hit.span,
                provenance: vec![hit.span, binding.target_evidence],
            });
            relations.push(LinkedRelation {
                kind: LinkedRelationKind::ScopedAlias,
                from_id: id,
                to_id: binding.target_id,
                evidence: vec![hit.span, binding.target_evidence],
                why: "short reference resolved through a `(далее — X)` declaration in this document (D385 scoped_alias)",
            });
        }
    }

    // (2) This-document references: this XML's head or annex, never a foreign act.
    for (block, para) in paras.iter().enumerate() {
        for hit in find_this_refs(block, para) {
            let (key, canon) = classify_this_ref(&hit.noun);
            match key {
                "федеральный закон" => match &letterhead {
                    Some(head) => {
                        let id = base + members.len();
                        members.push(LinkedMember {
                            id,
                            kind: member_kind(&head.date, &head.number),
                            date: head.date.clone(),
                            number: head.number.clone(),
                            type_name: head.kind.clone(),
                            approved_by: None,
                            alias: None,
                            derivation: LinkDerivation::ThisDocumentRef,
                            evidence: hit.span,
                            provenance: vec![hit.span, head.evidence],
                        });
                    }
                    None => {
                        members.push(fail_closed_this_ref(base + members.len(), canon, hit.span));
                        diagnostics.push(LinkDiagnostic::HeadUnavailable);
                    }
                },
                "положение" | "правила" => {
                    let target = annexes
                        .iter()
                        .find(|m| {
                            m.type_name.to_lowercase() == canon.to_lowercase()
                                && m.approved_by.is_some()
                        })
                        .or_else(|| {
                            annexes
                                .iter()
                                .find(|m| m.type_name.to_lowercase() == canon.to_lowercase())
                        });
                    match target {
                        Some(annex) => {
                            let id = base + members.len();
                            members.push(LinkedMember {
                                id,
                                kind: annex.kind,
                                date: annex.date.clone(),
                                number: annex.number.clone(),
                                type_name: annex.type_name.clone(),
                                approved_by: None,
                                alias: None,
                                derivation: LinkDerivation::ThisDocumentRef,
                                evidence: hit.span,
                                provenance: vec![hit.span, annex.evidence],
                            });
                            relations.push(LinkedRelation {
                                kind: LinkedRelationKind::ThisDocumentRef,
                                from_id: id,
                                to_id: annex.id,
                                evidence: vec![hit.span, annex.evidence],
                                why: "«настоящее …» refers to this document's own annex, never a foreign act (ADR-0029 §4)",
                            });
                        }
                        None => {
                            members.push(fail_closed_this_ref(
                                base + members.len(),
                                canon,
                                hit.span,
                            ));
                            diagnostics.push(LinkDiagnostic::HeadUnavailable);
                        }
                    }
                }
                _ => {
                    // «настоящего Кодекса»: the codex this XML points at is not
                    // a member of the linked model here — fail closed.
                    members.push(fail_closed_this_ref(base + members.len(), canon, hit.span));
                    diagnostics.push(LinkDiagnostic::HeadUnavailable);
                }
            }
        }
    }

    // (3) `указанного Федерального закона`: nearest preceding FZ with DATE+N in
    // the same block; otherwise skipped.
    for (block, para) in paras.iter().enumerate() {
        for hit in find_ukazanny(block, para) {
            let hit_pos = char_len_before(para, hit.span.start);
            let target = search
                .iter()
                .filter(|m| {
                    m.span.block == block
                        && m.char_pos < hit_pos
                        && !m.number.is_empty()
                        && m.number != "—"
                        && m.type_name.to_lowercase().starts_with("федеральн")
                })
                .max_by_key(|m| m.char_pos);
            let Some(target) = target else {
                continue;
            };
            let id = base + members.len();
            members.push(LinkedMember {
                id,
                kind: LinkedMemberKind::Anchored,
                date: target.date.clone(),
                number: target.number.clone(),
                type_name: target.type_name.clone(),
                approved_by: None,
                alias: None,
                derivation: LinkDerivation::ScopedAlias,
                evidence: hit.span,
                provenance: vec![hit.span, target.span],
            });
            relations.push(LinkedRelation {
                kind: LinkedRelationKind::ScopedAlias,
                from_id: id,
                to_id: target.id,
                evidence: vec![hit.span, target.span],
                why: "«указанного Федерального закона» resolves to the nearest preceding FZ with DATE+N in the same block",
            });
        }
    }

    (members, relations, diagnostics)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn block_ends_open_tracks_trailing_comma_and_unbalanced_bracket() {
        assert!(block_ends_open(
            "(в ред. Приказов Росгидромета от 18.07.2014 N 426,"
        ));
        assert!(block_ends_open("от 02.02.2021 N 2-ФЗ,"));
        assert!(block_ends_open("(от 02.02.2021 N 2-ФЗ"));
        assert!(!block_ends_open("Федеральный закон от 01.01.2020 N 1-ФЗ"));
        assert!(!block_ends_open("(ред. от 08.09.2018)"));
        assert!(!block_ends_open(""));
    }

    #[test]
    fn link_series_is_deterministic_and_leaves_input_untouched() {
        let paras = vec![
            "Федерального закона от 01.01.2020 N 1-ФЗ,".to_string(),
            "от 02.02.2021 N 2-ФЗ".to_string(),
        ];
        let before = paras.clone();
        let (first, _) = link_series(&paras);
        let (second, _) = link_series(&paras);
        assert_eq!(first, second, "replay must be stable");
        assert_eq!(paras, before, "link_series must not mutate its input");
    }
}
