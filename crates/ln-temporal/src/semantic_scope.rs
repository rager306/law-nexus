//! Source-backed semantic scope claims with deterministic bounded extraction.
//!
//! This module produces candidates only. Claims are not legal facts or NormRules;
//! every claim retains a source-local anchor and extraction is fail-closed at a
//! per-block budget.
//!
//! Cue recognition is token-bound (RC28-F11). A cue is a sequence of whole
//! tokens inside one statement, never a substring of a larger token, and an
//! adjacent negation particle is scoped into the polarity span instead of being
//! dropped. Participants are minted from a proven source span only, so a frame
//! can never widen an Actor to the whole block.

use crate::document_context::{
    AnalysisOverlay, BlockId, SourceBlock, Terminal, TextSpan, ThisRefEvidence,
};
use std::borrow::Borrow;
use std::collections::BTreeSet;

/// Closed role vocabulary for the semantic scope contour.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum SemanticClaimKind {
    Actor,
    Action,
    Object,
    Polarity,
    Condition,
    Exception,
    TemporalQualifier,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ClaimError {
    EmptySpan,
    MissingEvidence,
    EvidenceOutsideClaim,
}

/// A source-backed semantic claim. `evidence` is non-empty by construction.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SemanticClaim {
    kind: SemanticClaimKind,
    block: BlockId,
    span: TextSpan,
    evidence: Vec<TextSpan>,
}

impl SemanticClaim {
    pub fn new(
        kind: SemanticClaimKind,
        block: BlockId,
        span: TextSpan,
        evidence: Vec<TextSpan>,
    ) -> Result<Self, ClaimError> {
        if span.start() >= span.end() {
            return Err(ClaimError::EmptySpan);
        }
        if evidence.is_empty() {
            return Err(ClaimError::MissingEvidence);
        }
        if evidence.iter().any(|anchor| {
            anchor.start() >= anchor.end()
                || anchor.start() < span.start()
                || anchor.end() > span.end()
        }) {
            return Err(ClaimError::EvidenceOutsideClaim);
        }
        Ok(Self {
            kind,
            block,
            span,
            evidence,
        })
    }

    pub const fn kind(&self) -> SemanticClaimKind {
        self.kind
    }
    pub const fn block(&self) -> BlockId {
        self.block
    }
    pub const fn span(&self) -> TextSpan {
        self.span
    }
    pub fn evidence(&self) -> &[TextSpan] {
        &self.evidence
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ClaimLimit {
    pub limit: usize,
    pub attempted: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExtractionOutcome {
    claims: Vec<SemanticClaim>,
    limit: Option<ClaimLimit>,
}

impl ExtractionOutcome {
    pub fn claims(&self) -> &[SemanticClaim] {
        &self.claims
    }
    pub const fn limit(&self) -> Option<ClaimLimit> {
        self.limit
    }
    pub const fn was_limited(&self) -> bool {
        self.limit.is_some()
    }
}

/// Closed cue vocabulary: one claim kind plus the exact token sequence to match.
///
/// Every entry is a list of whole tokens, so a multiword phrase is spelled as
/// its separate tokens (`&["must", "not"]`, not `&["must not"]`). A cue is a
/// token sequence, never a substring, so `до` inside `должен` and `must` inside
/// `mustered` cannot match. Negated polarity is derived from an adjacent particle
/// rather than from a hardcoded phrase list, so `не вправе` can never also mint a
/// bare positive `вправе` cue.
const CUES: &[(SemanticClaimKind, &[&str])] = &[
    (SemanticClaimKind::Polarity, &["обязан"]),
    (SemanticClaimKind::Polarity, &["должен"]),
    (SemanticClaimKind::Polarity, &["вправе"]),
    (SemanticClaimKind::Polarity, &["запрещается"]),
    (SemanticClaimKind::Polarity, &["shall"]),
    (SemanticClaimKind::Polarity, &["must", "not"]),
    (SemanticClaimKind::Polarity, &["must"]),
    (SemanticClaimKind::Condition, &["если"]),
    (SemanticClaimKind::Condition, &["при", "условии"]),
    (SemanticClaimKind::Condition, &["provided", "that"]),
    (SemanticClaimKind::Exception, &["кроме"]),
    (SemanticClaimKind::Exception, &["за", "исключением"]),
    (SemanticClaimKind::Exception, &["except"]),
    (SemanticClaimKind::TemporalQualifier, &["до"]),
    (SemanticClaimKind::TemporalQualifier, &["после"]),
    (SemanticClaimKind::TemporalQualifier, &["в", "течение"]),
    (SemanticClaimKind::TemporalQualifier, &["с", "момента"]),
    (SemanticClaimKind::TemporalQualifier, &["before"]),
    (SemanticClaimKind::TemporalQualifier, &["after"]),
];

/// The particle that scopes an adjacent polarity cue.
const NEGATION_PARTICLE: &str = "не";

/// Longest prefix of a statement that can still be one grammatical participant.
///
/// Morphology is unavailable on this surface, so a longer prefix is more likely
/// an adjunct clause than the participant. The bound is a local fail-closed
/// radius for this contour, not a linguistic rule and not a deferred budget.
const MAX_PARTICIPANT_TOKENS: usize = 4;

/// Punctuation that separates clauses inside one statement. A candidate span may
/// not cross one, because the owning clause of the participant cannot be proven
/// without morphology.
const CLAUSE_SEPARATORS: &[char] = &[
    ',', ';', ':', '.', '!', '?', '(', ')', '[', ']', '{', '}', '«', '»', '„', '“', '”', '—', '–',
];

/// One token of a source block, addressed by original UTF-8 byte offsets.
#[derive(Debug, Clone, Copy)]
struct Token {
    start: usize,
    end: usize,
    /// Statement ordinal. One cue never spans two statements.
    statement: usize,
}

/// One cue occurrence resolved to a contiguous, single-statement token range.
#[derive(Debug, Clone, Copy)]
struct CueMatch {
    kind: SemanticClaimKind,
    start: usize,
    end: usize,
}

/// True when `character` at `index` ends a statement.
fn is_statement_terminator(text: &str, index: usize, character: char, previous: char) -> bool {
    match character {
        '!' | '?' | ';' | '…' | '\n' | '\r' => true,
        // A dot between two digits is a decimal separator, not a statement end.
        '.' => {
            let next = text[index + character.len_utf8()..].chars().next();
            !(previous.is_ascii_digit() && next.is_some_and(|value| value.is_ascii_digit()))
        }
        _ => false,
    }
}

/// Tokenize a block into alphanumeric runs and assign a statement ordinal.
///
/// Tokens always start and end on UTF-8 character boundaries, so every span
/// derived from them stays on the original byte offsets.
fn tokenize(text: &str) -> Vec<Token> {
    let mut tokens = Vec::new();
    let mut statement = 0usize;
    let mut previous: Option<char> = None;
    let mut pending: Option<(usize, usize)> = None;
    for (index, character) in text.char_indices() {
        if character.is_alphanumeric() {
            let end = index + character.len_utf8();
            pending = Some(match pending {
                Some((start, _)) => (start, end),
                None => (index, end),
            });
        } else {
            if let Some((start, end)) = pending.take() {
                tokens.push(Token {
                    start,
                    end,
                    statement,
                });
            }
            let terminated = previous
                .is_some_and(|value| is_statement_terminator(text, index, character, value));
            if terminated {
                statement += 1;
            }
        }
        previous = Some(character);
    }
    if let Some((start, end)) = pending {
        tokens.push(Token {
            start,
            end,
            statement,
        });
    }
    tokens
}

/// Case-folded equality between one source token and one cue token.
///
/// The comparison allocates nothing and never leaves the original byte offsets.
fn token_matches(text: &str, token: Token, expected: &str) -> bool {
    let mut actual = text[token.start..token.end].chars();
    let mut wanted = expected.chars();
    loop {
        match (actual.next(), wanted.next()) {
            (None, None) => return true,
            (Some(left), Some(right)) if left.to_lowercase().eq(right.to_lowercase()) => {}
            _ => return false,
        }
    }
}

/// First token index of every statement ordinal, in ordinal order.
fn statement_starts(tokens: &[Token]) -> Vec<usize> {
    let mut starts = Vec::new();
    for (index, token) in tokens.iter().enumerate() {
        if starts.len() <= token.statement {
            starts.push(index);
        }
    }
    starts
}

fn is_clause_separator(character: char) -> bool {
    CLAUSE_SEPARATORS.contains(&character)
}

/// True when the original text between two tokens carries clause punctuation.
fn gap_has_clause_separator(text: &str, from: usize, to: usize) -> bool {
    match text.get(from..to) {
        Some(gap) => gap.chars().any(is_clause_separator),
        // An unreadable gap cannot be proven clean, so it abstains.
        None => true,
    }
}

/// True when two tokens are separated by whitespace only.
///
/// A cue phrase and the particle that scopes it must be adjacent, so
/// punctuation between them breaks the match. An unreadable gap is never
/// adjacency.
fn gap_is_whitespace(text: &str, from: usize, to: usize) -> bool {
    match text.get(from..to) {
        Some(gap) => gap.chars().all(char::is_whitespace),
        None => false,
    }
}

/// Match one cue's token sequence at `start`, inside a single statement.
///
/// The cue tokens must be separated by whitespace only, so `must,not` is not the
/// `must not` cue.
fn cue_at(
    text: &str,
    tokens: &[Token],
    start: usize,
    cue: (SemanticClaimKind, &[&str]),
) -> Option<usize> {
    let statement = tokens.get(start)?.statement;
    let mut end = start;
    for (offset, expected) in cue.1.iter().enumerate() {
        let token = tokens.get(start + offset)?;
        if token.statement != statement || !token_matches(text, *token, expected) {
            return None;
        }
        if offset > 0 && !gap_is_whitespace(text, tokens[end].end, token.start) {
            return None;
        }
        end = start + offset;
    }
    Some(end)
}

/// Resolve every cue occurrence with maximal munch.
///
/// The longest cue at one start wins, and the earlier vocabulary entry wins a
/// tie, so the result is deterministic. Matches are ordered by token position.
fn cue_matches(text: &str, tokens: &[Token]) -> Vec<CueMatch> {
    let mut matches = Vec::new();
    for (start, _) in tokens.iter().enumerate() {
        let mut best: Option<(SemanticClaimKind, usize)> = None;
        for cue in CUES {
            let Some(end) = cue_at(text, tokens, start, *cue) else {
                continue;
            };
            let longer = match best {
                Some((_, best_end)) => end > best_end,
                None => true,
            };
            if longer {
                best = Some((cue.0, end));
            }
        }
        if let Some((kind, end)) = best {
            matches.push(CueMatch { kind, start, end });
        }
    }
    matches
}

/// Scope one polarity cue to an adjacent negation particle.
///
/// `не обязан`, `обязан не` and `не вправе` all resolve to a span that keeps the
/// negation visible. At most one particle is attached, left before right, only
/// inside the statement the cue belongs to and only when whitespace alone
/// separates them. No scoped negation can leak across a statement boundary,
/// across punctuation, or into a positive cue, and a token that already opens
/// another cue is never consumed.
fn negated_range(
    text: &str,
    tokens: &[Token],
    matched: CueMatch,
    cue_starts: &BTreeSet<usize>,
) -> (usize, usize) {
    if matched.kind != SemanticClaimKind::Polarity {
        return (matched.start, matched.end);
    }
    let statement = tokens[matched.start].statement;
    let is_particle = |index: usize| {
        tokens
            .get(index)
            .filter(|token| token.statement == statement)
            .is_some_and(|token| token_matches(text, *token, NEGATION_PARTICLE))
    };
    if let Some(left) = matched.start.checked_sub(1) {
        if !cue_starts.contains(&left)
            && gap_is_whitespace(text, tokens[left].end, tokens[matched.start].start)
            && is_particle(left)
        {
            return (left, matched.end);
        }
    }
    let right = matched.end + 1;
    if !cue_starts.contains(&right)
        && is_particle(right)
        && gap_is_whitespace(text, tokens[matched.end].end, tokens[right].start)
    {
        return (matched.start, right);
    }
    (matched.start, matched.end)
}

/// The proven participant span of the statement owning `polarity_start`.
///
/// The prefix between the statement start and its first polarity cue is accepted
/// only when it is short, free of clause punctuation, and free of other cue
/// tokens. Anything else abstains: without morphology a wider prefix cannot be
/// proven to be one participant, and guessing one would invent an Actor.
fn participant_tokens(
    text: &str,
    tokens: &[Token],
    starts: &[usize],
    polarity_start: usize,
    cue_starts: &BTreeSet<usize>,
) -> Option<(usize, usize)> {
    let first = *starts.get(tokens.get(polarity_start)?.statement)?;
    let length = polarity_start.checked_sub(first)?;
    if length == 0 || length > MAX_PARTICIPANT_TOKENS {
        return None;
    }
    let blocked = (first..polarity_start).any(|index| {
        cue_starts.contains(&index)
            || (index > first
                && gap_has_clause_separator(text, tokens[index - 1].end, tokens[index].start))
    });
    (!blocked).then_some((first, polarity_start - 1))
}

/// Span from the first byte of `start` to the last byte of `end`.
fn token_span(tokens: &[Token], start: usize, end: usize) -> Option<TextSpan> {
    let first = tokens.get(start)?;
    let last = tokens.get(end)?;
    TextSpan::new(first.start, last.end)
        .ok()
        .filter(|span| span.start() < span.end())
}

/// A `ThisRef` span is admissible only when it is non-empty, inside the block,
/// and aligned to UTF-8 character boundaries.
fn evidence_in_block(text: &str, span: TextSpan) -> bool {
    span.start() < span.end()
        && span.end() <= text.len()
        && text.is_char_boundary(span.start())
        && text.is_char_boundary(span.end())
}

/// Build one claim whose only evidence is its own preserved source span.
fn claim(kind: SemanticClaimKind, block: BlockId, span: TextSpan) -> Option<SemanticClaim> {
    SemanticClaim::new(kind, block, span, vec![span]).ok()
}

/// Extract explicit semantic cue candidates from one source block.
///
/// Extraction mints only source-anchored candidates: an Actor requires both
/// structural act scope and a proven participant span, and a polarity cue keeps
/// its adjacent negation particle in the span. No operation here reaches a
/// NormRule, an applicability result or any other legal IR.
pub fn extract_semantic_claims(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    let text = block.text();
    let tokens = tokenize(text);
    let matches = cue_matches(text, &tokens);
    let cue_starts: BTreeSet<usize> = matches.iter().map(|matched| matched.start).collect();
    let mut candidates = BTreeSet::new();

    // Structural act scope is a precondition for a participant claim, never an
    // actor by itself: the frame says the block carries an act, the token prefix
    // says which participant that act belongs to. Neither alone mints an Actor.
    if overlay
        .frames()
        .iter()
        .any(|frame| frame.block() == block.id())
    {
        let starts = statement_starts(&tokens);
        let mut claimed_statements = BTreeSet::new();
        for matched in &matches {
            if matched.kind != SemanticClaimKind::Polarity
                || !claimed_statements.insert(tokens[matched.start].statement)
            {
                continue;
            }
            let Some((first, last)) =
                participant_tokens(text, &tokens, &starts, matched.start, &cue_starts)
            else {
                continue;
            };
            let Some(span) = token_span(&tokens, first, last) else {
                continue;
            };
            if let Some(actor) = claim(SemanticClaimKind::Actor, block.id(), span) {
                candidates.insert(actor);
            }
        }
    }

    for evidence in this_refs
        .iter()
        .filter(|evidence| evidence_in_block(text, evidence.span()))
    {
        if let Some(actor) = claim(SemanticClaimKind::Actor, block.id(), evidence.span()) {
            candidates.insert(actor);
        }
    }

    for matched in &matches {
        let (start, end) = negated_range(text, &tokens, *matched, &cue_starts);
        let Some(span) = token_span(&tokens, start, end) else {
            continue;
        };
        if let Some(found) = claim(matched.kind, block.id(), span) {
            candidates.insert(found);
        }
    }

    let attempted = candidates.len();
    let claims: Vec<_> = candidates.into_iter().take(max_claims).collect();
    let limit = (attempted > claims.len()).then_some(ClaimLimit {
        limit: max_claims,
        attempted,
    });
    ExtractionOutcome { claims, limit }
}

pub fn extract(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    extract_semantic_claims(block, overlay, this_refs, max_claims)
}

/// The four singular slots needed before a candidate can be considered complete.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CandidateSlot {
    Actor,
    Action,
    Object,
    Polarity,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormRuleCandidate {
    candidate_id: String,
    actor: SemanticClaim,
    action: SemanticClaim,
    object: SemanticClaim,
    polarity: SemanticClaim,
    conditions: Vec<SemanticClaim>,
    exceptions: Vec<SemanticClaim>,
    temporal_qualifier: Vec<SemanticClaim>,
    anchors: Vec<TextSpan>,
}

impl NormRuleCandidate {
    pub fn candidate_id(&self) -> &str {
        &self.candidate_id
    }
    pub fn actor(&self) -> &SemanticClaim {
        &self.actor
    }
    pub fn action(&self) -> &SemanticClaim {
        &self.action
    }
    pub fn object(&self) -> &SemanticClaim {
        &self.object
    }
    pub fn polarity(&self) -> &SemanticClaim {
        &self.polarity
    }
    pub fn conditions(&self) -> &[SemanticClaim] {
        &self.conditions
    }
    pub fn exceptions(&self) -> &[SemanticClaim] {
        &self.exceptions
    }
    pub fn temporal_qualifier(&self) -> &[SemanticClaim] {
        &self.temporal_qualifier
    }
    pub fn anchors(&self) -> &[TextSpan] {
        &self.anchors
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum AbstentionReason {
    MissingActor,
    MissingAction,
    MissingObject,
    MissingPolarity,
    ConflictingSlots,
    ContextTerminal(Terminal),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AbstentionRecord {
    reasons: Vec<AbstentionReason>,
    missing: Vec<CandidateSlot>,
    claims: Vec<SemanticClaim>,
    anchors: Vec<TextSpan>,
}
impl AbstentionRecord {
    pub fn reasons(&self) -> &[AbstentionReason] {
        &self.reasons
    }
    pub fn missing(&self) -> &[CandidateSlot] {
        &self.missing
    }
    pub fn claims(&self) -> &[SemanticClaim] {
        &self.claims
    }
    pub fn anchors(&self) -> &[TextSpan] {
        &self.anchors
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectionOutcome {
    Complete(Box<NormRuleCandidate>),
    Abstained(AbstentionRecord),
}

/// Zero-tolerance counters for one semantic projection run.
///
/// Counters are not inferred from strings or repaired after the fact. The run
/// records only explicit events, while valid claims and projection outcomes
/// make source-span loss and fact minting unavailable through this API.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct SemanticScopeCounters {
    pub critical_field_loss: usize,
    pub source_span_loss: usize,
    pub false_fact_mint: usize,
    pub unconditionalized_scope: usize,
    pub unexplained_abstention: usize,
    pub candidates_total: usize,
    pub abstained_total: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SemanticScopeEvent {
    CriticalFieldLoss,
    SourceSpanLoss,
    FalseFactMint,
    UnconditionalizedScope,
    UnexplainedAbstention,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SemanticScopeViolation {
    CriticalFieldLoss,
    SourceSpanLoss,
    FalseFactMint,
    UnconditionalizedScope,
    UnexplainedAbstention,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SemanticScopeRun {
    counters: SemanticScopeCounters,
}

impl SemanticScopeRun {
    pub const fn new() -> Self {
        Self {
            counters: SemanticScopeCounters {
                critical_field_loss: 0,
                source_span_loss: 0,
                false_fact_mint: 0,
                unconditionalized_scope: 0,
                unexplained_abstention: 0,
                candidates_total: 0,
                abstained_total: 0,
            },
        }
    }

    pub const fn counters(&self) -> SemanticScopeCounters {
        self.counters
    }

    /// Record one projection outcome without weakening or rewriting it.
    pub fn record_projection(&mut self, outcome: &ProjectionOutcome) {
        self.counters.candidates_total += 1;
        if matches!(outcome, ProjectionOutcome::Abstained(_)) {
            self.counters.abstained_total += 1;
        }
    }

    /// Inject a diagnostic event for a hostile test or an upstream audit.
    /// Production projection code does not call this implicitly.
    pub fn record_event(&mut self, event: SemanticScopeEvent) {
        match event {
            SemanticScopeEvent::CriticalFieldLoss => self.counters.critical_field_loss += 1,
            SemanticScopeEvent::SourceSpanLoss => self.counters.source_span_loss += 1,
            SemanticScopeEvent::FalseFactMint => self.counters.false_fact_mint += 1,
            SemanticScopeEvent::UnconditionalizedScope => {
                self.counters.unconditionalized_scope += 1
            }
            SemanticScopeEvent::UnexplainedAbstention => self.counters.unexplained_abstention += 1,
        }
    }

    pub fn record_batch<I>(&mut self, outcomes: I)
    where
        I: IntoIterator,
        I::Item: Borrow<ProjectionOutcome>,
    {
        for outcome in outcomes {
            self.record_projection(outcome.borrow());
        }
    }
}

/// Returns every non-zero zero-tolerance counter, in stable diagnostic order.
pub fn verify_zero_tolerance(run: &SemanticScopeRun) -> Result<(), Vec<SemanticScopeViolation>> {
    let c = run.counters;
    let mut violations = Vec::new();
    if c.critical_field_loss != 0 {
        violations.push(SemanticScopeViolation::CriticalFieldLoss);
    }
    if c.source_span_loss != 0 {
        violations.push(SemanticScopeViolation::SourceSpanLoss);
    }
    if c.false_fact_mint != 0 {
        violations.push(SemanticScopeViolation::FalseFactMint);
    }
    if c.unconditionalized_scope != 0 {
        violations.push(SemanticScopeViolation::UnconditionalizedScope);
    }
    if c.unexplained_abstention != 0 {
        violations.push(SemanticScopeViolation::UnexplainedAbstention);
    }
    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

/// Render only diagnostic data. This is deliberately not a readiness or legal
/// authority report, and its key order is fixed for byte-stable artifacts.
pub fn render_scope_run_json(run: &SemanticScopeRun) -> String {
    let c = run.counters;
    format!(
        "{{\"semantic_loss\":{{\"critical_field_loss\":{},\"source_span_loss\":{},\"false_fact_mint\":{},\"unconditionalized_scope\":{},\"unexplained_abstention\":{}}},\"candidates_total\":{},\"abstained_total\":{}}}",
        c.critical_field_loss,
        c.source_span_loss,
        c.false_fact_mint,
        c.unconditionalized_scope,
        c.unexplained_abstention,
        c.candidates_total,
        c.abstained_total
    )
}

fn id_for(claims: &[SemanticClaim]) -> String {
    claims
        .iter()
        .map(|c| {
            format!(
                "{}:{}-{}",
                c.block().get(),
                c.span().start(),
                c.span().end()
            )
        })
        .collect::<Vec<_>>()
        .join("|")
}

/// Projects only a resolved, non-conflicting, fully slotted scope. No default
/// actor and no condition dropping are possible because required fields are owned.
pub fn project_norm_rule(
    claims: impl IntoIterator<Item = SemanticClaim>,
    terminal: Terminal,
) -> ProjectionOutcome {
    let mut claims: Vec<_> = claims.into_iter().collect();
    claims.sort();
    let anchors = claims
        .iter()
        .flat_map(|c| c.evidence().iter().copied())
        .collect();
    if terminal != Terminal::Resolved {
        return ProjectionOutcome::Abstained(AbstentionRecord {
            reasons: vec![AbstentionReason::ContextTerminal(terminal)],
            missing: Vec::new(),
            claims,
            anchors,
        });
    }
    let mut slots = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
    let mut conditions = Vec::new();
    let mut exceptions = Vec::new();
    let mut temporal = Vec::new();
    for claim in &claims {
        match claim.kind() {
            SemanticClaimKind::Actor => slots[0].push(claim.clone()),
            SemanticClaimKind::Action => slots[1].push(claim.clone()),
            SemanticClaimKind::Object => slots[2].push(claim.clone()),
            SemanticClaimKind::Polarity => slots[3].push(claim.clone()),
            SemanticClaimKind::Condition => conditions.push(claim.clone()),
            SemanticClaimKind::Exception => exceptions.push(claim.clone()),
            SemanticClaimKind::TemporalQualifier => temporal.push(claim.clone()),
        }
    }
    let missing = [
        CandidateSlot::Actor,
        CandidateSlot::Action,
        CandidateSlot::Object,
        CandidateSlot::Polarity,
    ]
    .into_iter()
    .enumerate()
    .filter_map(|(i, slot)| slots[i].is_empty().then_some(slot))
    .collect::<Vec<_>>();
    let conflicting = slots.iter().any(|slot| slot.len() > 1);
    let mut reasons = missing
        .iter()
        .map(|slot| match slot {
            CandidateSlot::Actor => AbstentionReason::MissingActor,
            CandidateSlot::Action => AbstentionReason::MissingAction,
            CandidateSlot::Object => AbstentionReason::MissingObject,
            CandidateSlot::Polarity => AbstentionReason::MissingPolarity,
        })
        .collect::<Vec<_>>();
    if conflicting {
        reasons.push(AbstentionReason::ConflictingSlots);
    }
    if !reasons.is_empty() {
        return ProjectionOutcome::Abstained(AbstentionRecord {
            reasons,
            missing,
            claims,
            anchors,
        });
    }
    let candidate_id = id_for(&claims);
    ProjectionOutcome::Complete(Box::new(NormRuleCandidate {
        candidate_id,
        actor: slots[0].remove(0),
        action: slots[1].remove(0),
        object: slots[2].remove(0),
        polarity: slots[3].remove(0),
        conditions,
        exceptions,
        temporal_qualifier: temporal,
        anchors,
    }))
}
