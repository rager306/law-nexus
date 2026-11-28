//! Compile-time Typestate pipeline (`P0 -> P5`) and optional morphology seam
//! for `DocumentContext` (ADR-0032 D2; ADR-0028 dual-tokenizer discipline).
//!
//! Lifecycle: `[proposed]` (ADR-0032 D2). [`BoundedLegalMarkerMorphProvider`]
//! exposes bounded lexical-marker evidence only, not dictionary morphology.
//!
//! Enforces four invariants at compile time and seam boundaries:
//! 1. Phases cannot be skipped or reordered (`Raw -> Indexed -> Analyzed -> ContextClosed`);
//! 2. `DocumentPipeline<P>` is neither `Clone` nor `Copy`, and fallible
//!    transitions return ownership on error (`Err((self, IndexBuildError))` for
//!    `into_indexed` and `Err((Box<Self>, OverlayBuildError))` for `into_analyzed`);
//! 3. `MorphEvidenceProvider` receives covering `TokenKind::Word` tokens only
//!    and every returned record is verified against those `Word` spans (ADR-0028);
//! 4. Captured literal `LawRef` mentions from `P3` are frozen read-only before
//!    `P5` context closure (`INV-06` and `npa-semantic-process.yaml` mention invariant).

use crate::current_requisites::CurrentDocumentRequisites;
use crate::document_context::{
    BlockId, ContextBudgets, ContextEnvironment, ContextRequest, ContextRunReport, ContextWorklist,
    DocumentAnalysisOverlay, DocumentStructureIndex, DocumentVersionRef, IndexBuildError,
    OverlayBuildError, build_document_analysis_overlay, build_document_structure_index,
};
use crate::domain::{ParsedBlock, TextSpan};
use crate::lawref::{LawRef, capture_lawrefs};
use crate::lexer::{NpaToken, TokenKind, lex};
use crate::local_grammar::{
    CoordinatingFrame, StructuralDesignationFrame, extract_act_list_frames,
    extract_structural_frames,
};
use crate::morphology::{LegalMarkerKind, find_legal_markers};

// ── Optional Morphology Evidence Seam (ADR-0032 D2 / ADR-0028) ──────────────

/// One source-anchored morphology evidence entry attached strictly to a
/// covering [`TokenKind::Word`] token span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MorphEvidenceRecord {
    pub span: TextSpan,
    pub lemma: String,
    pub tags: Vec<String>,
}

/// Immutable per-block morphology evidence set produced by a
/// [`MorphEvidenceProvider`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MorphEvidenceSet {
    pub block_index: usize,
    pub provider_id: &'static str,
    pub records: Vec<MorphEvidenceRecord>,
}

/// Optional morphology boundary over covering `Word` tokens only (ADR-0028:
/// morphology must never inspect `Abbrev` stems or collapse the dual tokenizer).
pub trait MorphEvidenceProvider {
    fn provider_id(&self) -> &'static str;

    /// Receives only pre-filtered covering [`TokenKind::Word`] tokens.
    fn analyze_covering_words(
        &self,
        block_index: usize,
        src: &str,
        word_tokens: &[NpaToken],
    ) -> MorphEvidenceSet;
}

/// Fail-closed default provider when dictionary morphology is deferred:
/// emits zero heuristic claims.
#[derive(Debug, Clone, Copy, Default)]
pub struct NullMorphProvider;

impl MorphEvidenceProvider for NullMorphProvider {
    fn provider_id(&self) -> &'static str {
        "null-morph/v1"
    }

    fn analyze_covering_words(
        &self,
        block_index: usize,
        _src: &str,
        _word_tokens: &[NpaToken],
    ) -> MorphEvidenceSet {
        MorphEvidenceSet {
            block_index,
            provider_id: self.provider_id(),
            records: Vec::new(),
        }
    }
}

/// Bounded adapter projecting existing [`find_legal_markers`] onto the
/// [`MorphEvidenceProvider`] seam while verifying every record falls on a
/// covering [`TokenKind::Word`] token.
#[derive(Debug, Clone, Copy, Default)]
pub struct BoundedLegalMarkerMorphProvider;

fn marker_lemma(kind: LegalMarkerKind) -> &'static str {
    match kind {
        LegalMarkerKind::Statya => "статья",
        LegalMarkerKind::Punkt => "пункт",
        LegalMarkerKind::Obyazan => "обязан",
        LegalMarkerKind::Vprave => "вправе",
        LegalMarkerKind::Zapret => "запрет",
        LegalMarkerKind::Glava => "глава",
        LegalMarkerKind::Chast => "часть",
        LegalMarkerKind::Podpunkt => "подпункт",
        LegalMarkerKind::Razdel => "раздел",
    }
}

impl MorphEvidenceProvider for BoundedLegalMarkerMorphProvider {
    fn provider_id(&self) -> &'static str {
        "bounded-legal-markers/v1"
    }

    fn analyze_covering_words(
        &self,
        block_index: usize,
        src: &str,
        word_tokens: &[NpaToken],
    ) -> MorphEvidenceSet {
        let word_spans: Vec<TextSpan> = word_tokens
            .iter()
            .filter(|tok| tok.kind == TokenKind::Word)
            .map(|tok| tok.span)
            .collect();
        let records = find_legal_markers(src)
            .into_iter()
            .filter(|m| word_spans.contains(&m.text_span()))
            .map(|m| {
                let mut tags = vec!["legal_marker".to_owned()];
                if m.negated() {
                    tags.push("negated".to_owned());
                }
                MorphEvidenceRecord {
                    span: m.text_span(),
                    lemma: marker_lemma(m.kind()).to_owned(),
                    tags,
                }
            })
            .collect();
        MorphEvidenceSet {
            block_index,
            provider_id: self.provider_id(),
            records,
        }
    }
}

// ── Sealed Typestate Phases (P0 -> P5) ──────────────────────────────────────

mod private {
    pub trait Sealed {}
}

/// Sealed marker trait for compile-time [`DocumentPipeline`] phases.
pub trait PipelinePhase: private::Sealed {}

/// P0: Raw decoded blocks awaiting base structural indexing.
#[derive(Debug)]
pub struct RawPhase {
    blocks: Vec<ParsedBlock>,
}

/// P1: Immutable [`DocumentStructureIndex`] built over decoded blocks.
#[derive(Debug)]
pub struct IndexedPhase {
    blocks: Vec<ParsedBlock>,
    index: DocumentStructureIndex,
}

/// Immutable per-block local analysis bundle produced by P2 + P3.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlockLocalAnalysis {
    pub block_id: BlockId,
    pub tokens: Vec<NpaToken>,
    pub morph: MorphEvidenceSet,
    pub act_frames: Vec<CoordinatingFrame>,
    pub structural_frames: Vec<StructuralDesignationFrame>,
    pub literal_mentions: Vec<LawRef>,
}

/// P2–P4: Local covering lexing, optional morphology, frozen literal mentions,
/// and derived [`DocumentAnalysisOverlay`].
#[derive(Debug)]
pub struct AnalyzedPhase {
    index: DocumentStructureIndex,
    local_analysis: Vec<BlockLocalAnalysis>,
    overlay: DocumentAnalysisOverlay,
}

/// P5: Context worklist closed deterministically; source index, frozen
/// literal mentions, and overlay remain immutable and inspectable.
#[derive(Debug)]
pub struct ContextClosedPhase {
    index: DocumentStructureIndex,
    local_analysis: Vec<BlockLocalAnalysis>,
    overlay: DocumentAnalysisOverlay,
    report: ContextRunReport,
}

impl private::Sealed for RawPhase {}
impl private::Sealed for IndexedPhase {}
impl private::Sealed for AnalyzedPhase {}
impl private::Sealed for ContextClosedPhase {}

impl PipelinePhase for RawPhase {}
impl PipelinePhase for IndexedPhase {}
impl PipelinePhase for AnalyzedPhase {}
impl PipelinePhase for ContextClosedPhase {}

/// Typestate document analysis pipeline (`Raw -> Indexed -> Analyzed -> ContextClosed`).
///
/// Deliberately does **not** implement `Clone` or `Copy` so pre-transition
/// handles cannot be duplicated and reused out of order.
#[derive(Debug)]
pub struct DocumentPipeline<P: PipelinePhase> {
    version: DocumentVersionRef,
    phase: P,
}

impl<P: PipelinePhase> DocumentPipeline<P> {
    pub fn version(&self) -> &DocumentVersionRef {
        &self.version
    }
}

impl DocumentPipeline<RawPhase> {
    /// Enter the pipeline at P0 with decoded source blocks.
    pub fn new(version: DocumentVersionRef, blocks: Vec<ParsedBlock>) -> Self {
        Self {
            version,
            phase: RawPhase { blocks },
        }
    }

    pub fn block_count(&self) -> usize {
        self.phase.blocks.len()
    }

    /// P0 -> P1: Build the immutable [`DocumentStructureIndex`].
    ///
    /// On failure, returns the original `DocumentPipeline<RawPhase>` alongside
    /// the [`IndexBuildError`] so ownership is preserved.
    pub fn into_indexed(self) -> Result<DocumentPipeline<IndexedPhase>, (Self, IndexBuildError)> {
        match build_document_structure_index(self.version.clone(), &self.phase.blocks) {
            Ok(index) => Ok(DocumentPipeline {
                version: self.version,
                phase: IndexedPhase {
                    blocks: self.phase.blocks,
                    index,
                },
            }),
            Err(err) => Err((self, err)),
        }
    }
}

impl DocumentPipeline<IndexedPhase> {
    pub fn index(&self) -> &DocumentStructureIndex {
        &self.phase.index
    }

    /// P1 -> P2/P3/P4: Run covering lexing, optional morphology strictly over
    /// covering `TokenKind::Word` tokens (verified fail-closed), literal
    /// `LawRef` capture, local grammar frame extraction, and overlay construction.
    pub fn into_analyzed<M: MorphEvidenceProvider>(
        self,
        morph_provider: &M,
    ) -> Result<DocumentPipeline<AnalyzedPhase>, (Box<Self>, OverlayBuildError)> {
        let mut local_analysis = Vec::with_capacity(self.phase.blocks.len());
        let mut frames_per_block = Vec::with_capacity(self.phase.blocks.len());
        let mut captures_per_block = Vec::with_capacity(self.phase.blocks.len());

        for (i, block) in self.phase.blocks.iter().enumerate() {
            let Ok(block_id) = BlockId::parse(&format!("block-{i}")) else {
                return Err((Box::new(self), OverlayBuildError::UnknownBlock));
            };
            let text = block.text();
            let tokens = lex(text);
            let word_tokens: Vec<NpaToken> = tokens
                .iter()
                .copied()
                .filter(|tok| tok.kind == TokenKind::Word)
                .collect();
            let morph = morph_provider.analyze_covering_words(i, text, &word_tokens);

            // Fail-closed ADR-0028 enforcement: morph output must belong to this
            // block and align strictly to covering `TokenKind::Word` spans.
            if morph.block_index != i
                || !morph
                    .records
                    .iter()
                    .all(|rec| word_tokens.iter().any(|wt| wt.span == rec.span))
            {
                return Err((Box::new(self), OverlayBuildError::InvalidCaptureSpan));
            }

            let markers = find_legal_markers(text);
            let batch = capture_lawrefs(text);
            let act_frames = extract_act_list_frames(text, &batch);
            let structural_frames = extract_structural_frames(&tokens, text, &markers);
            let literal_mentions: Vec<LawRef> = batch.captures().to_vec();

            frames_per_block.push((
                block_id.clone(),
                act_frames.clone(),
                structural_frames.clone(),
            ));
            captures_per_block.push((block_id.clone(), literal_mentions.clone()));
            local_analysis.push(BlockLocalAnalysis {
                block_id,
                tokens,
                morph,
                act_frames,
                structural_frames,
                literal_mentions,
            });
        }

        match build_document_analysis_overlay(
            &self.phase.index,
            &frames_per_block,
            &captures_per_block,
        ) {
            Ok(overlay) => Ok(DocumentPipeline {
                version: self.version,
                phase: AnalyzedPhase {
                    index: self.phase.index,
                    local_analysis,
                    overlay,
                },
            }),
            Err(err) => Err((Box::new(self), err)),
        }
    }
}

impl DocumentPipeline<AnalyzedPhase> {
    pub fn index(&self) -> &DocumentStructureIndex {
        &self.phase.index
    }

    pub fn overlay(&self) -> &DocumentAnalysisOverlay {
        &self.phase.overlay
    }

    pub fn local_analysis(&self) -> &[BlockLocalAnalysis] {
        &self.phase.local_analysis
    }

    /// P4 -> P5: Execute deterministic bounded [`ContextWorklist`] closure
    /// without mutating the base index, overlay, or frozen P3 literal mentions.
    pub fn into_context_closed(
        self,
        requisites: Option<&CurrentDocumentRequisites>,
        requests: &[ContextRequest],
        budgets: ContextBudgets,
    ) -> DocumentPipeline<ContextClosedPhase> {
        let mut worklist = ContextWorklist::new(budgets);
        let env = ContextEnvironment {
            index: &self.phase.index,
            overlay: &self.phase.overlay,
            requisites,
        };
        let report = worklist.run(env, requests);
        DocumentPipeline {
            version: self.version,
            phase: ContextClosedPhase {
                index: self.phase.index,
                local_analysis: self.phase.local_analysis,
                overlay: self.phase.overlay,
                report,
            },
        }
    }
}

impl DocumentPipeline<ContextClosedPhase> {
    pub fn index(&self) -> &DocumentStructureIndex {
        &self.phase.index
    }

    pub fn overlay(&self) -> &DocumentAnalysisOverlay {
        &self.phase.overlay
    }

    pub fn local_analysis(&self) -> &[BlockLocalAnalysis] {
        &self.phase.local_analysis
    }

    pub fn context_report(&self) -> &ContextRunReport {
        &self.phase.report
    }
}
