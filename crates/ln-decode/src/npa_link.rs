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
