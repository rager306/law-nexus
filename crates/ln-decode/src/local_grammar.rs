//! Immutable, fragment-local local-grammar frames (D384, S03).
//!
//! The YAML contract is design data only (D216/D098); these Rust types are
//! intentionally defined here rather than generated from it. Frames are
//! structural alternatives above the covering lexer. They do not mint
//! identities, join blocks, authorize inheritance, or expand arithmetic
//! designation ranges. A `TextSpan` is the sole anchor coordinate and must be
//! supplied from one decoded fragment on character boundaries.

use crate::domain::TextSpan;
use crate::lexer::{NpaToken, TokenKind};
use crate::morphology::{LegalMarkerKind, MorphologyMatch};

/// The only two frame families admitted by D384.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameKind {
    ActRequisites,
    StructuralDesignation,
}

/// Provenance of an inherited or explicit member field. The authorized
/// current-document variant is reserved for the D381 sidecar and cannot be
/// constructed by S03 frame constructors.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DerivationSource {
    ExplicitMember,
    SameSeriesHead,
    PriorFrame,
    AuthorizedCurrentDocumentRequisites,
}

/// Closed enumeration FSM from D384. Terminal states never transition again.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnumerationState {
    NotEvaluated,
    Candidate,
    Compatible,
    Conflicting,
    Incomplete,
    Rejected,
}

/// An event which can advance the local enumeration FSM.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnumerationTransition {
    LocalRolesAndValuesCaptured,
    AuthorizedFieldClaimsAgree,
    ExplicitOrInheritedClaimsDisagree,
    RequiredOwnerOrValueMissing,
    GrammarOrBoundContractRefused,
}

impl EnumerationState {
    /// Apply exactly one D384 transition; invalid or terminal transitions are
    /// refused without changing the state.
    pub const fn transition(self, event: EnumerationTransition) -> Option<Self> {
        match (self, event) {
            (Self::NotEvaluated, EnumerationTransition::LocalRolesAndValuesCaptured) => {
                Some(Self::Candidate)
            }
            (Self::Candidate, EnumerationTransition::AuthorizedFieldClaimsAgree) => {
                Some(Self::Compatible)
            }
            (Self::Candidate, EnumerationTransition::ExplicitOrInheritedClaimsDisagree) => {
                Some(Self::Conflicting)
            }
            (Self::Candidate, EnumerationTransition::RequiredOwnerOrValueMissing) => {
                Some(Self::Incomplete)
            }
            (Self::Candidate, EnumerationTransition::GrammarOrBoundContractRefused) => {
                Some(Self::Rejected)
            }
            _ => None,
        }
    }

    pub const fn is_terminal(self) -> bool {
        matches!(
            self,
            Self::Compatible | Self::Conflicting | Self::Incomplete | Self::Rejected
        )
    }
}

/// Lifecycle status of a proposed frame, separate from enumeration state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameStatus {
    Proposed,
    Ambiguous,
    Rejected,
}

/// Closed diagnostics; competing frames are retained rather than selected by
/// proximity or source order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameDiagnostic {
    FrameMemberLimitReached,
    ConflictingFramesRetained,
    OwnerUnresolved,
    GrammarContractRefused,
    TypeUnresolved,
}

impl FrameDiagnostic {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::FrameMemberLimitReached => "frame_member_limit_reached",
            Self::ConflictingFramesRetained => "conflicting_frames_retained",
            Self::OwnerUnresolved => "owner_unresolved",
            Self::GrammarContractRefused => "grammar_contract_refused",
            Self::TypeUnresolved => "type_unresolved",
        }
    }
}

/// One structural member, carrying its literal value and derivation evidence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameMember {
    pub value: String,
    pub value_span: TextSpan,
    /// Act-list slot values when this member came from a LawRef capture.
    /// Structural members leave these fields absent.
    pub date: Option<String>,
    pub date_span: Option<TextSpan>,
    pub doc_no: Option<String>,
    pub doc_no_span: Option<TextSpan>,
    pub derivation: DerivationSource,
    pub evidence: Vec<TextSpan>,
    pub state: EnumerationState,
}

impl FrameMember {
    pub fn new(
        value: String,
        value_span: TextSpan,
        derivation: DerivationSource,
        evidence: Vec<TextSpan>,
        state: EnumerationState,
    ) -> Self {
        Self {
            value,
            value_span,
            date: None,
            date_span: None,
            doc_no: None,
            doc_no_span: None,
            derivation,
            evidence,
            state,
        }
    }
}

/// One step in a fragment-local owner path. Every step has independent proof
/// evidence; no step is an identity or a document-wide context reference.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OwnerPathState {
    Resolved,
    Unresolved,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnerPathStep {
    pub value: String,
    pub span: TextSpan,
    pub evidence: Vec<TextSpan>,
    pub state: OwnerPathState,
}

impl OwnerPathStep {
    pub fn new(value: String, span: TextSpan, evidence: Vec<TextSpan>) -> Self {
        Self {
            value,
            span,
            evidence,
            state: OwnerPathState::Resolved,
        }
    }

    pub fn unresolved(span: TextSpan, evidence: Vec<TextSpan>) -> Self {
        Self {
            value: String::new(),
            span,
            evidence,
            state: OwnerPathState::Unresolved,
        }
    }
}

/// Shared shape for the two D384 frame families.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoordinatingFrame {
    pub frame_kind: FrameKind,
    pub local_anchor: TextSpan,
    pub head_roles: Vec<String>,
    pub members: Vec<FrameMember>,
    pub separators: Vec<TextSpan>,
    pub continuation: bool,
    pub alternatives: Vec<FrameMember>,
    pub bounds: FrameBounds,
    pub status: FrameStatus,
    pub diagnostic: Option<FrameDiagnostic>,
}

/// Explicit bound metadata carried by a frame, without pretending proposed
/// values are final corpus limits.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FrameBounds {
    pub max_members: usize,
    pub max_expanded_candidates: usize,
}

/// Structural designation frame with endpoint-pair policy. Expansion itself
/// belongs to the later resolve side and is deliberately absent here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralDesignationFrame {
    pub local_anchor: TextSpan,
    pub marker: LegalMarkerKind,
    pub values: Vec<FrameMember>,
    pub owner_path: Vec<OwnerPathStep>,
    pub expansion_policy: ExpansionPolicy,
    pub status: FrameStatus,
    pub diagnostic: Option<FrameDiagnostic>,
}

/// The sole S03 expansion declaration; it is not an arithmetic enumerator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ExpansionPolicy {
    EndpointPair,
}

/// [proposed] G06 bound. The bounded C4 smoke baseline measured a maximum
/// of 3 act-list members (`prd/migration/rust-evidence/m203-s03-frames-baseline.json`);
/// 64 therefore retains more than 2x headroom. This is diagnostic sizing,
/// not a promoted corpus limit.
pub const PROPOSED_MAX_FRAME_MEMBERS: usize = 64;
/// [proposed] G07 resolve-side candidate bound. The same bounded C4 smoke
/// measured 16 structural values at its maximum; 64 retains more than 2x
/// headroom. S03 declares the endpoint-expansion ceiling only; expansion is
/// not performed here (`prd/migration/rust-evidence/m203-s03-frames-baseline.json`).
pub const PROPOSED_MAX_EXPANDED_CANDIDATES: usize = 64;

/// Data-only vocabulary for the act-type head. Matchers do not carry a
/// second law-reference vocabulary: these lemmas only classify an already
/// admitted capture window.
pub const ACT_TYPE_LEMMAS: &[&str] = &[
    "закон",
    "законов",
    "кодекс",
    "кодексов",
    "основы",
    "указ",
    "указов",
    "постановление",
    "постановлений",
    "распоряжение",
    "распоряжений",
    "приказ",
    "приказов",
    "письмо",
    "писем",
    "указание",
    "указаний",
];

/// Extract coordinating act-requisite frames from admitted capture output.
///
/// This function never calls `capture_lawrefs` and never sees refused captures:
/// its only candidate inputs are `batch.captures()`. A member is emitted only
/// when the admitted LawRef has both date and document-number slots and is
/// preceded by the local `от` grammar marker. Type inheritance is represented
/// by `SameSeriesHead` and the head span in `evidence`; it is not a document
/// context lookup.
pub fn extract_act_list_frames(
    src: &str,
    batch: &crate::lawref::LawRefCaptureBatch,
) -> Vec<CoordinatingFrame> {
    let tokens = crate::lexer::lex(src);
    let mut groups: Vec<(Option<usize>, Vec<&crate::lawref::LawRef>)> = Vec::new();
    for capture in batch.captures() {
        // A capture with neither slot cannot be an act-list member. A DATE
        // without NUMBER is retained as an incomplete member when the local
        // `от` grammar admits it; inventing a number is prohibited.
        if capture.slots.date.is_none() && capture.slots.doc_no.is_none() {
            continue;
        }
        let Some(date_text) = capture.slots.date.as_deref() else {
            continue;
        };
        let Some(date_start) =
            find_subspan(src, capture.span.start(), capture.span.end(), date_text)
        else {
            continue;
        };
        if !has_local_ot(&tokens, src, date_start) {
            continue;
        }
        let head = find_act_head(&tokens, src, date_start);
        if let Some((existing, members)) = groups.iter_mut().find(|(key, _)| *key == head) {
            let _ = existing;
            members.push(capture);
        } else {
            groups.push((head, vec![capture]));
        }
    }
    groups
        .into_iter()
        .filter_map(|(head, captures)| {
            let first = captures.first()?;
            let mut members = Vec::with_capacity(captures.len());
            for (index, capture) in captures.iter().enumerate() {
                let date = capture.slots.date.clone();
                let date_span = date.as_deref().and_then(|value| {
                    find_subspan(src, capture.span.start(), capture.span.end(), value)
                });
                let doc_no = capture.slots.doc_no.clone();
                let doc_no_span = doc_no.as_deref().and_then(|value| {
                    find_subspan(src, capture.span.start(), capture.span.end(), value)
                });
                let value = doc_no.clone().unwrap_or_default();
                let derivation = if index == 0 {
                    DerivationSource::ExplicitMember
                } else {
                    DerivationSource::SameSeriesHead
                };
                let evidence = if derivation == DerivationSource::SameSeriesHead {
                    head.and_then(|i| tokens.get(i).map(|t| vec![t.span]))
                        .unwrap_or_default()
                } else {
                    vec![capture.span]
                };
                members.push(FrameMember {
                    value,
                    value_span: capture.span,
                    date,
                    date_span,
                    doc_no,
                    doc_no_span,
                    derivation,
                    evidence,
                    state: if capture.slots.date.is_some() && capture.slots.doc_no.is_some() {
                        EnumerationState::Candidate
                    } else {
                        EnumerationState::Incomplete
                    },
                });
            }
            let type_alternatives = head
                .map(|i| act_heads_at(&tokens, src, i))
                .unwrap_or_default();
            let unresolved = head.is_none();
            let ambiguous = type_alternatives.len() > 1;
            let too_many = members.len() > PROPOSED_MAX_FRAME_MEMBERS;
            let status = if too_many {
                FrameStatus::Rejected
            } else if unresolved || ambiguous {
                FrameStatus::Ambiguous
            } else {
                FrameStatus::Proposed
            };
            let diagnostic = if too_many {
                Some(FrameDiagnostic::FrameMemberLimitReached)
            } else if unresolved {
                Some(FrameDiagnostic::TypeUnresolved)
            } else if ambiguous {
                Some(FrameDiagnostic::ConflictingFramesRetained)
            } else {
                None
            };
            let start = head
                .and_then(|i| tokens.get(i).map(|t| t.span.start()))
                .unwrap_or(first.span.start());
            let end = captures
                .last()
                .map(|c| c.span.end())
                .unwrap_or(first.span.end());
            Some(CoordinatingFrame {
                frame_kind: FrameKind::ActRequisites,
                local_anchor: TextSpan::try_new(start, end).ok()?,
                head_roles: type_alternatives,
                members,
                separators: Vec::new(),
                continuation: captures.len() > 1,
                alternatives: Vec::new(),
                bounds: FrameBounds {
                    max_members: PROPOSED_MAX_FRAME_MEMBERS,
                    max_expanded_candidates: PROPOSED_MAX_EXPANDED_CANDIDATES,
                },
                status,
                diagnostic,
            })
        })
        .collect()
}

fn find_subspan(src: &str, start: usize, end: usize, needle: &str) -> Option<TextSpan> {
    let offset = src.get(start..end)?.find(needle)? + start;
    TextSpan::try_new(offset, offset + needle.len()).ok()
}

fn has_local_ot(tokens: &[NpaToken], src: &str, date: TextSpan) -> bool {
    let date_index = tokens.iter().position(|t| t.span == date);
    let Some(index) = date_index else {
        return false;
    };
    (0..index)
        .rev()
        .find(|i| tokens[*i].kind != TokenKind::Space)
        .is_some_and(|i| tokens[i].lexeme(src).eq_ignore_ascii_case("от"))
}

fn find_act_head(tokens: &[NpaToken], src: &str, date: TextSpan) -> Option<usize> {
    let date_index = tokens.iter().position(|t| t.span == date)?;
    (0..date_index).rev().find(|i| {
        tokens[*i].kind == TokenKind::Word
            && ACT_TYPE_LEMMAS.contains(&tokens[*i].lexeme(src).to_lowercase().as_str())
    })
}

fn act_heads_at(tokens: &[NpaToken], src: &str, head: usize) -> Vec<String> {
    let mut result = vec![tokens[head].lexeme(src).to_owned()];
    let mut i = head;
    while i > 0 && head - i < 4 {
        i -= 1;
        if tokens[i].kind == TokenKind::Word
            && ACT_TYPE_LEMMAS.contains(&tokens[i].lexeme(src).to_lowercase().as_str())
        {
            result.push(tokens[i].lexeme(src).to_owned());
        }
    }
    result.sort();
    result.dedup();
    result
}

/// Extract structural designation frames from the immutable covering stream.
///
/// This is deliberately a local grammar: marker morphology narrows the
/// marker alphabet, but every member and owner claim is proved by source
/// spans. Ranges remain endpoint pairs and are never arithmetically expanded.
pub fn extract_structural_frames(
    tokens: &[NpaToken],
    src: &str,
    markers: &[MorphologyMatch],
) -> Vec<StructuralDesignationFrame> {
    let structural = |kind: LegalMarkerKind| {
        matches!(
            kind,
            LegalMarkerKind::Statya
                | LegalMarkerKind::Punkt
                | LegalMarkerKind::Glava
                | LegalMarkerKind::Chast
                | LegalMarkerKind::Podpunkt
                | LegalMarkerKind::Razdel
        )
    };
    let marker_at = |marker: MorphologyMatch| {
        tokens
            .iter()
            .position(|token| token.span == marker.text_span())
    };
    let mut frames = Vec::new();
    for marker in markers.iter().copied().filter(|m| structural(m.kind())) {
        let Some(head) = marker_at(marker) else {
            continue;
        };
        // A trailing `статьи N` is the owner of an already-started local
        // designation, not a second designation candidate. The leading form
        // `статьи N части M` remains a candidate for the later frame.
        if marker.kind() == LegalMarkerKind::Statya
            && is_trailing_owner_marker(tokens, src, head, markers, marker.text_span())
        {
            continue;
        }
        let mut cursor = head + 1;
        let mut value_indices = Vec::new();
        let mut separators = Vec::new();
        let mut saw_dash = false;
        let mut expect_value = true;
        while cursor < tokens.len() {
            let token = tokens[cursor];
            if token.kind == TokenKind::Space {
                cursor += 1;
                continue;
            }
            if token.kind == TokenKind::HierNum || is_bare_number(token, src) {
                if !expect_value && !saw_dash {
                    break;
                }
                value_indices.push(cursor);
                expect_value = false;
                cursor += 1;
                continue;
            }
            let lexeme = token.lexeme(src);
            if token.kind == TokenKind::Punct && (lexeme == "," || is_dash(lexeme)) {
                separators.push(token.span);
                saw_dash |= is_dash(lexeme);
                expect_value = true;
                cursor += 1;
                continue;
            }
            if token.kind == TokenKind::Word && lexeme == "и" {
                separators.push(token.span);
                expect_value = true;
                cursor += 1;
                continue;
            }
            break;
        }
        if value_indices.is_empty() || expect_value {
            continue;
        }
        let mut values = Vec::new();
        for (position, index) in value_indices.iter().copied().enumerate() {
            let token = tokens[index];
            let derivation = if position == 0 || !saw_dash {
                DerivationSource::ExplicitMember
            } else {
                DerivationSource::SameSeriesHead
            };
            let evidence = if derivation == DerivationSource::SameSeriesHead {
                vec![marker.text_span()]
            } else {
                vec![token.span]
            };
            values.push(FrameMember::new(
                token.lexeme(src).to_owned(),
                token.span,
                derivation,
                evidence,
                EnumerationState::Candidate,
            ));
        }
        let mut owner_path = owner_before(tokens, src, head, markers, marker.text_span());
        let end = value_indices
            .last()
            .map(|index| tokens[*index].span.end())
            .unwrap_or(marker.end());
        if let Some(owner) = owner_after(tokens, src, cursor, markers) {
            owner_path.push(owner);
        }
        if owner_path.is_empty() {
            owner_path.push(OwnerPathStep::unresolved(
                marker.text_span(),
                vec![marker.text_span()],
            ));
        }
        let too_many = values.len() > PROPOSED_MAX_FRAME_MEMBERS;
        let status = if too_many {
            FrameStatus::Rejected
        } else if owner_path
            .iter()
            .any(|step| step.state == OwnerPathState::Unresolved)
        {
            FrameStatus::Ambiguous
        } else {
            FrameStatus::Proposed
        };
        let diagnostic = if too_many {
            Some(FrameDiagnostic::FrameMemberLimitReached)
        } else if owner_path
            .iter()
            .any(|step| step.state == OwnerPathState::Unresolved)
        {
            Some(FrameDiagnostic::OwnerUnresolved)
        } else {
            None
        };
        let anchor = TextSpan::try_new(marker.start(), end).expect("local grammar span is bounded");
        frames.push(StructuralDesignationFrame {
            local_anchor: anchor,
            marker: marker.kind(),
            values,
            owner_path,
            expansion_policy: ExpansionPolicy::EndpointPair,
            status,
            diagnostic,
        });
    }
    let overlap = frames.len() > 1;
    if overlap {
        for frame in &mut frames {
            if frame.diagnostic.is_none() {
                frame.status = FrameStatus::Ambiguous;
                frame.diagnostic = Some(FrameDiagnostic::ConflictingFramesRetained);
            }
        }
    }
    frames
}

fn is_bare_number(token: NpaToken, src: &str) -> bool {
    token.kind == TokenKind::Word && token.lexeme(src).bytes().all(|byte| byte.is_ascii_digit())
}

fn is_dash(lexeme: &str) -> bool {
    matches!(lexeme, "-" | "–" | "—")
}

fn is_trailing_owner_marker(
    tokens: &[NpaToken],
    src: &str,
    head: usize,
    markers: &[MorphologyMatch],
    current: TextSpan,
) -> bool {
    let Some(number) = (0..head)
        .rev()
        .find(|index| tokens[*index].kind != TokenKind::Space)
    else {
        return false;
    };
    if tokens[number].kind != TokenKind::HierNum && !is_bare_number(tokens[number], src) {
        return false;
    }
    let Some(previous_marker) = (0..number).rev().find_map(|index| {
        markers
            .iter()
            .copied()
            .find(|marker| marker.text_span() == tokens[index].span)
    }) else {
        return false;
    };
    previous_marker.text_span() != current
}

fn owner_before(
    tokens: &[NpaToken],
    src: &str,
    head: usize,
    markers: &[MorphologyMatch],
    current: TextSpan,
) -> Vec<OwnerPathStep> {
    let Some(previous) = (0..head).rev().find(|index| {
        tokens[*index].kind == TokenKind::Word
            && markers
                .iter()
                .any(|marker| marker.text_span() == tokens[*index].span)
    }) else {
        return Vec::new();
    };
    let marker = markers
        .iter()
        .find(|marker| marker.text_span() == tokens[previous].span);
    if marker.is_none() || marker.is_some_and(|marker| marker.text_span() == current) {
        return Vec::new();
    }
    let mut number = previous + 1;
    while number < head && tokens[number].kind == TokenKind::Space {
        number += 1;
    }
    if number < head
        && (tokens[number].kind == TokenKind::HierNum || is_bare_number(tokens[number], src))
    {
        return vec![OwnerPathStep::new(
            tokens[number].lexeme(src).to_owned(),
            tokens[number].span,
            vec![tokens[previous].span, tokens[number].span],
        )];
    }
    Vec::new()
}

fn owner_after(
    tokens: &[NpaToken],
    src: &str,
    mut cursor: usize,
    markers: &[MorphologyMatch],
) -> Option<OwnerPathStep> {
    while cursor < tokens.len() && tokens[cursor].kind == TokenKind::Space {
        cursor += 1;
    }
    let marker = tokens.get(cursor)?;
    let marker_match = markers
        .iter()
        .find(|item| item.text_span() == marker.span)?;
    if !matches!(marker_match.kind(), LegalMarkerKind::Statya) {
        return None;
    }
    cursor += 1;
    while cursor < tokens.len() && tokens[cursor].kind == TokenKind::Space {
        cursor += 1;
    }
    let value = tokens.get(cursor)?;
    if value.kind != TokenKind::HierNum && !is_bare_number(*value, src) {
        return None;
    }
    Some(OwnerPathStep::new(
        value.lexeme(src).to_owned(),
        value.span,
        vec![marker.span, value.span],
    ))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FrameLimitOutcome {
    Accepted,
    LimitReached,
}

impl FrameLimitOutcome {
    pub const fn is_accepted(self) -> bool {
        matches!(self, Self::Accepted)
    }
    pub const fn diagnostic(self) -> Option<FrameDiagnostic> {
        match self {
            Self::Accepted => None,
            Self::LimitReached => Some(FrameDiagnostic::FrameMemberLimitReached),
        }
    }
}

/// Stateless G06 admission decision. Existing members are never truncated.
pub const fn on_frame_limit(accepted_members: usize) -> FrameLimitOutcome {
    if accepted_members < PROPOSED_MAX_FRAME_MEMBERS {
        FrameLimitOutcome::Accepted
    } else {
        FrameLimitOutcome::LimitReached
    }
}

/// Immutable result of attempting to append a member to a coordinating frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameAdmission {
    pub frame: CoordinatingFrame,
    pub outcome: FrameLimitOutcome,
}

impl CoordinatingFrame {
    /// Constructs a proposed frame. S03 constructors cannot create the
    /// authorized-current-document derivation; callers receive that source
    /// only from a future D381 sidecar integration.
    pub fn new(
        frame_kind: FrameKind,
        local_anchor: TextSpan,
        head_roles: Vec<String>,
        members: Vec<FrameMember>,
        separators: Vec<TextSpan>,
        continuation: bool,
        alternatives: Vec<FrameMember>,
    ) -> Self {
        Self {
            frame_kind,
            local_anchor,
            head_roles,
            members,
            separators,
            continuation,
            alternatives,
            bounds: FrameBounds {
                max_members: PROPOSED_MAX_FRAME_MEMBERS,
                max_expanded_candidates: PROPOSED_MAX_EXPANDED_CANDIDATES,
            },
            status: FrameStatus::Proposed,
            diagnostic: None,
        }
    }

    /// Returns a new value; the original frame and its members are untouched.
    pub fn admit_member(&self, member: FrameMember) -> FrameAdmission {
        match on_frame_limit(self.members.len()) {
            FrameLimitOutcome::Accepted => {
                let mut next = self.clone();
                next.members.push(member);
                FrameAdmission {
                    frame: next,
                    outcome: FrameLimitOutcome::Accepted,
                }
            }
            FrameLimitOutcome::LimitReached => {
                let mut rejected = self.clone();
                rejected.status = FrameStatus::Rejected;
                rejected.diagnostic = FrameLimitOutcome::LimitReached.diagnostic();
                FrameAdmission {
                    frame: rejected,
                    outcome: FrameLimitOutcome::LimitReached,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn span(start: usize) -> TextSpan {
        TextSpan::try_new(start, start + 1).unwrap()
    }
    fn member(start: usize) -> FrameMember {
        FrameMember::new(
            "x".into(),
            span(start),
            DerivationSource::ExplicitMember,
            vec![span(start)],
            EnumerationState::Candidate,
        )
    }

    #[test]
    fn vocabulary_is_closed_to_exactly_two_frame_kinds() {
        assert_eq!(FrameKind::ActRequisites as u8, 0);
        assert_eq!(FrameKind::StructuralDesignation as u8, 1);
    }

    #[test]
    fn fsm_has_only_contract_transitions_and_terminal_states() {
        assert_eq!(
            EnumerationState::NotEvaluated
                .transition(EnumerationTransition::LocalRolesAndValuesCaptured),
            Some(EnumerationState::Candidate)
        );
        assert_eq!(
            EnumerationState::Candidate
                .transition(EnumerationTransition::GrammarOrBoundContractRefused),
            Some(EnumerationState::Rejected)
        );
        assert!(EnumerationState::Rejected.is_terminal());
        assert_eq!(
            EnumerationState::Rejected
                .transition(EnumerationTransition::AuthorizedFieldClaimsAgree),
            None
        );
    }

    #[test]
    fn frame_limit_rejects_without_losing_existing_members() {
        let mut frame = CoordinatingFrame::new(
            FrameKind::ActRequisites,
            span(0),
            vec![],
            vec![],
            vec![],
            false,
            vec![],
        );
        for index in 0..PROPOSED_MAX_FRAME_MEMBERS {
            frame = frame.admit_member(member(index + 1)).frame;
        }
        let result = frame.admit_member(member(999));
        assert_eq!(result.outcome, FrameLimitOutcome::LimitReached);
        assert_eq!(result.frame.status, FrameStatus::Rejected);
        assert_eq!(
            result.frame.diagnostic,
            Some(FrameDiagnostic::FrameMemberLimitReached)
        );
        assert_eq!(result.frame.members.len(), PROPOSED_MAX_FRAME_MEMBERS);
    }

    #[test]
    fn structural_designation_declares_endpoint_pair_without_expansion() {
        let frame = StructuralDesignationFrame {
            local_anchor: span(0),
            marker: LegalMarkerKind::Statya,
            values: vec![member(1), member(3)],
            owner_path: vec![],
            expansion_policy: ExpansionPolicy::EndpointPair,
            status: FrameStatus::Proposed,
            diagnostic: None,
        };
        assert_eq!(frame.values.len(), 2);
        assert_eq!(frame.expansion_policy, ExpansionPolicy::EndpointPair);
    }
}
