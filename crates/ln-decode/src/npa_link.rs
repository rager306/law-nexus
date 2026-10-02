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
use crate::npa_anchor::LocalSpan;
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

/// Document letterhead (head zone). Placeholder shape wired in T01; the
/// recognizer and issuer table land in T02.
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
