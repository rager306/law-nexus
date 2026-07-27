use std::collections::HashSet;

use crate::{
    deontic::{extract_deontic_lexemes, DeonticLexemeKind},
    domain::{HierarchyLevel, ParsedBlock, SourceFormatId, TextSpan},
    golden::{GoldenAnnotation, GoldenFixture, GoldenLayer},
    hierarchy::extract_hierarchy,
    references::{extract_reference_mentions, ReferenceMentionKind},
    temporal::{extract_temporal_phrases, TemporalPhraseKind},
};

/// Validation error for evaluator construction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvaluatorError {
    EmptyBlocks,
    ProviderMismatch {
        expected: SourceFormatId,
        actual: SourceFormatId,
    },
    BlockIndexOutOfRange {
        index: usize,
        block_count: usize,
    },
}

impl std::fmt::Display for EvaluatorError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyBlocks => write!(formatter, "empty blocks"),
            Self::ProviderMismatch { expected, actual } => {
                write!(
                    formatter,
                    "provider mismatch: expected {expected:?}, got {actual:?}"
                )
            }
            Self::BlockIndexOutOfRange { index, block_count } => write!(
                formatter,
                "block index {index} out of range (have {block_count} blocks)"
            ),
        }
    }
}

impl std::error::Error for EvaluatorError {}

/// Per-layer quality metrics computed from exact decoded `TextSpan` matches.
///
/// These values measure parser output agreement with structural annotations.
/// They do not encode legal correctness, citation authority or corpus coverage.
#[derive(Debug, Clone, PartialEq)]
pub struct LayerMetrics {
    layer: GoldenLayer,
    true_positives: usize,
    false_positives: usize,
    false_negatives: usize,
    precision: f64,
    recall: f64,
    f1: f64,
}

impl LayerMetrics {
    pub fn layer(&self) -> GoldenLayer {
        self.layer
    }

    pub fn true_positives(&self) -> usize {
        self.true_positives
    }

    pub fn false_positives(&self) -> usize {
        self.false_positives
    }

    pub fn false_negatives(&self) -> usize {
        self.false_negatives
    }

    pub fn precision(&self) -> f64 {
        self.precision
    }

    pub fn recall(&self) -> f64 {
        self.recall
    }

    pub fn f1(&self) -> f64 {
        self.f1
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum MatchIdentity {
    Hierarchy(HierarchyLevel),
    Reference {
        kind: ReferenceMentionKind,
        number: String,
    },
    Temporal(TemporalPhraseKind),
    Deontic {
        kind: DeonticLexemeKind,
        negated: bool,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct MatchKey {
    block_index: usize,
    identity: MatchIdentity,
    span: TextSpan,
}

impl MatchKey {
    fn from_annotation(annotation: &GoldenAnnotation) -> Option<Self> {
        Some(Self {
            block_index: annotation.block_index(),
            identity: match annotation {
                GoldenAnnotation::Hierarchy { level, .. } => MatchIdentity::Hierarchy(*level),
                GoldenAnnotation::Reference { kind, number, .. } => MatchIdentity::Reference {
                    kind: *kind,
                    number: number.clone(),
                },
                GoldenAnnotation::Temporal { kind, .. } => MatchIdentity::Temporal(*kind),
                GoldenAnnotation::Deontic { kind, negated, .. } => MatchIdentity::Deontic {
                    kind: *kind,
                    negated: *negated,
                },
            },
            span: annotation.span(),
        })
    }
}

fn collect_actual_keys(blocks: &[ParsedBlock], layer: GoldenLayer) -> Vec<MatchKey> {
    let mut keys = Vec::new();
    for (index, block) in blocks.iter().enumerate() {
        match layer {
            GoldenLayer::Hierarchy => {
                if let Some(node) = extract_hierarchy(block) {
                    keys.push(MatchKey {
                        block_index: index,
                        identity: MatchIdentity::Hierarchy(node.level()),
                        span: node.marker_span(),
                    });
                }
            }
            GoldenLayer::Reference => {
                for mention in extract_reference_mentions(block) {
                    keys.push(MatchKey {
                        block_index: index,
                        identity: MatchIdentity::Reference {
                            kind: mention.kind(),
                            number: mention.number().to_owned(),
                        },
                        span: mention.text_span(),
                    });
                }
            }
            GoldenLayer::Temporal => {
                for phrase in extract_temporal_phrases(block) {
                    keys.push(MatchKey {
                        block_index: index,
                        identity: MatchIdentity::Temporal(phrase.kind()),
                        span: phrase.text_span(),
                    });
                }
            }
            GoldenLayer::Deontic => {
                for lexeme in extract_deontic_lexemes(block) {
                    keys.push(MatchKey {
                        block_index: index,
                        identity: MatchIdentity::Deontic {
                            kind: lexeme.kind(),
                            negated: lexeme.negated(),
                        },
                        span: lexeme.text_span(),
                    });
                }
            }
        }
    }
    keys
}

fn compute_layer(
    expected: &HashSet<MatchKey>,
    actual: &HashSet<MatchKey>,
    layer: GoldenLayer,
) -> LayerMetrics {
    let true_positives = expected.intersection(actual).count();
    let false_positives = actual.difference(expected).count();
    let false_negatives = expected.difference(actual).count();

    let precision = if true_positives + false_positives == 0 {
        1.0
    } else {
        true_positives as f64 / (true_positives + false_positives) as f64
    };
    let recall = if true_positives + false_negatives == 0 {
        1.0
    } else {
        true_positives as f64 / (true_positives + false_negatives) as f64
    };
    let f1 = if precision + recall == 0.0 {
        0.0
    } else {
        2.0 * precision * recall / (precision + recall)
    };

    LayerMetrics {
        layer,
        true_positives,
        false_positives,
        false_negatives,
        precision,
        recall,
        f1,
    }
}

/// Evaluate parser output against golden fixture annotations.
///
/// Returns one `LayerMetrics` per layer present in the fixture. Metrics measure
/// exact decoded `TextSpan` agreement only; they do not encode legal
/// correctness, citation authority or corpus coverage.
pub fn evaluate(
    fixture: &GoldenFixture,
    blocks: &[ParsedBlock],
) -> Result<Vec<LayerMetrics>, EvaluatorError> {
    if blocks.is_empty() {
        return Err(EvaluatorError::EmptyBlocks);
    }

    let expected_provider = fixture.provider();
    for block in blocks {
        if block.source_format() != expected_provider {
            return Err(EvaluatorError::ProviderMismatch {
                expected: expected_provider,
                actual: block.source_format(),
            });
        }
    }

    for annotation in fixture.annotations() {
        if annotation.block_index() >= blocks.len() {
            return Err(EvaluatorError::BlockIndexOutOfRange {
                index: annotation.block_index(),
                block_count: blocks.len(),
            });
        }
    }

    let present_layers: HashSet<GoldenLayer> =
        fixture.annotations().iter().map(|a| a.layer()).collect();

    let mut results = Vec::new();
    for layer in [
        GoldenLayer::Hierarchy,
        GoldenLayer::Reference,
        GoldenLayer::Temporal,
        GoldenLayer::Deontic,
    ] {
        if !present_layers.contains(&layer) {
            continue;
        }

        let expected: HashSet<MatchKey> = fixture
            .annotations()
            .iter()
            .filter_map(|a| {
                if a.layer() == layer {
                    MatchKey::from_annotation(a)
                } else {
                    None
                }
            })
            .collect();

        let actual: HashSet<MatchKey> = collect_actual_keys(blocks, layer).into_iter().collect();

        results.push(compute_layer(&expected, &actual, layer));
    }

    Ok(results)
}
