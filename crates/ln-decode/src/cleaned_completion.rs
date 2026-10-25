//! Closed Hold/TextOnly classification semantics for the cleaned-projection
//! wire envelope (`cleaned-projection-contract.md` §13).
//!
//! The S01 contract reserves `completion_basis` / `incomplete_reasons` and
//! their closed syntax only; it does not decide what qualifies as Hold or
//! TextOnly (§11). This module closes that gap with a producer-declared
//! partial-basis classifier: a caller declares the scope it actually
//! projected, and the declaration maps deterministically onto the frozen
//! [`WireCompletion`] vocabulary.
//!
//! Semantics:
//!
//! - [`ScopeDeclaration::WholeProjection`] declares the whole bounded
//!   projection attributed without loss and maps to
//!   [`WireCompletion::Complete`].
//! - [`ScopeDeclaration::StructureHold`] and
//!   [`ScopeDeclaration::TextOnlyScope`] declare an **honest partial basis**:
//!   the structural or normative interpretation is incomplete or inapplicable,
//!   so the export is `incomplete` with basis `hold` / `text_only`. The text
//!   channel stays full — decoded-text loss is still not permitted, and an
//!   independent battery proves that separately.
//! - [`ScopeDeclaration::NarrowedScope`] and
//!   [`ScopeDeclaration::UnsupportedSource`] declare a caller scope and an
//!   out-of-profile source respectively.
//!
//! [`classify_completion`] additionally corrects the declaration against the
//! real [`ReaderSourceClass`]: a source that is not supported WordML can never
//! be `Complete`, and `unsupported_source` is added to a non-empty reason set
//! (deduplicated, basis preserved). The result always satisfies the §8.1
//! invariant: `Complete` carries no reasons, and every `Incomplete` has a
//! non-empty reason set containing its basis.
//!
//! This module is dependency-free: `std` plus the frozen
//! [`crate::cleaned_wire`] and [`crate::reader_gate`] types only.

use std::fmt;

use crate::cleaned_wire::{IncompleteReason, WireCompletion};
use crate::reader_gate::ReaderSourceClass;

// ------------------------------------------------------------ scope types #

/// Closed producer-declared projection scope.
///
/// A declaration states what the producer actually projected; it never carries
/// a legal claim and never permits decoded-text loss.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ScopeDeclaration {
    /// The whole bounded projection attributed without text loss.
    WholeProjection,
    /// Structural interpretation was withheld (Hold); the declaring producer
    /// declares a partial structural basis while keeping the text channel full.
    StructureHold,
    /// Only the text channel was in scope; the structure is partial.
    TextOnlyScope,
    /// The caller declared a scope narrower than the whole projection.
    NarrowedScope,
    /// The source is outside the bounded provider profile.
    UnsupportedSource,
}

impl ScopeDeclaration {
    /// Closed declaration token (also the §8.1 `completion_basis` form for the
    /// mapped completion).
    pub const fn as_str(self) -> &'static str {
        match self {
            ScopeDeclaration::WholeProjection => "complete",
            ScopeDeclaration::StructureHold => "hold",
            ScopeDeclaration::TextOnlyScope => "text_only",
            ScopeDeclaration::NarrowedScope => "caller_scope",
            ScopeDeclaration::UnsupportedSource => "unsupported_source",
        }
    }

    /// Fail-closed parse of the closed declaration vocabulary. An unknown token
    /// is a [`CompletionError`]; `limit_reached` is intentionally not a
    /// declaration (see [`completion_for`]).
    pub fn from_token(token: &str) -> Result<Self, CompletionError> {
        match token {
            "complete" => Ok(ScopeDeclaration::WholeProjection),
            "hold" => Ok(ScopeDeclaration::StructureHold),
            "text_only" => Ok(ScopeDeclaration::TextOnlyScope),
            "caller_scope" => Ok(ScopeDeclaration::NarrowedScope),
            "unsupported_source" => Ok(ScopeDeclaration::UnsupportedSource),
            _ => Err(CompletionError::UnknownToken),
        }
    }
}

/// Closed failure of a scope-declaration parse. Carries no payload string, so a
/// diagnostic can never leak a caller-supplied token into a wire message.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CompletionError {
    /// The token is not part of the closed declaration vocabulary.
    UnknownToken,
}

impl CompletionError {
    /// Closed error token.
    pub const fn as_str(self) -> &'static str {
        match self {
            CompletionError::UnknownToken => "unknown_scope_declaration_token",
        }
    }
}

impl fmt::Display for CompletionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::error::Error for CompletionError {}

// ------------------------------------------------------------ mapping #

/// Deterministic declaration → completion mapping.
///
/// `WholeProjection` is the only declaration that yields
/// [`WireCompletion::Complete`]. `LimitReached` is never produced by any
/// declaration: a reached writer cap is discovered by the writer itself during
/// validate-before-write, not declared by a caller, and is therefore outside
/// this classifier's vocabulary.
pub fn completion_for(declaration: ScopeDeclaration) -> WireCompletion {
    match declaration {
        ScopeDeclaration::WholeProjection => WireCompletion::Complete,
        ScopeDeclaration::StructureHold => WireCompletion::Incomplete {
            basis: IncompleteReason::Hold,
            reasons: vec![IncompleteReason::Hold],
        },
        ScopeDeclaration::TextOnlyScope => WireCompletion::Incomplete {
            basis: IncompleteReason::TextOnly,
            reasons: vec![IncompleteReason::TextOnly],
        },
        ScopeDeclaration::NarrowedScope => WireCompletion::Incomplete {
            basis: IncompleteReason::CallerScope,
            reasons: vec![IncompleteReason::CallerScope],
        },
        ScopeDeclaration::UnsupportedSource => WireCompletion::Incomplete {
            basis: IncompleteReason::UnsupportedSource,
            reasons: vec![IncompleteReason::UnsupportedSource],
        },
    }
}

/// Classify a declared scope against the real reader source class.
///
/// The declaration alone can claim `Complete`, but a source that is not
/// [`ReaderSourceClass::SupportedWordml`] cannot be a whole supported
/// projection. The correction is honest and closed:
///
/// - a declared `Complete` on an unsupported source becomes
///   `Incomplete { basis: UnsupportedSource, reasons: [UnsupportedSource] }`;
/// - an already-`Incomplete` completion keeps its basis and gains
///   `UnsupportedSource` in its reason set exactly once (dedup, deterministic
///   order).
///
/// The result always satisfies the §8.1 invariant: reasons are non-empty and
/// contain the basis; `Complete` is reachable **iff** the source class is
/// `SupportedWordml` and the declaration is `WholeProjection`.
pub fn classify_completion(
    source_class: ReaderSourceClass,
    declaration: ScopeDeclaration,
) -> WireCompletion {
    let declared = completion_for(declaration);
    if source_class == ReaderSourceClass::SupportedWordml {
        return declared;
    }
    match declared {
        WireCompletion::Complete => WireCompletion::Incomplete {
            basis: IncompleteReason::UnsupportedSource,
            reasons: vec![IncompleteReason::UnsupportedSource],
        },
        WireCompletion::Incomplete { basis, mut reasons } => {
            if !reasons.contains(&IncompleteReason::UnsupportedSource) {
                reasons.push(IncompleteReason::UnsupportedSource);
            }
            WireCompletion::Incomplete { basis, reasons }
        }
    }
}

// ------------------------------------------------------------ tests #

#[cfg(test)]
mod tests {
    use super::*;

    const ALL_DECLARATIONS: [ScopeDeclaration; 5] = [
        ScopeDeclaration::WholeProjection,
        ScopeDeclaration::StructureHold,
        ScopeDeclaration::TextOnlyScope,
        ScopeDeclaration::NarrowedScope,
        ScopeDeclaration::UnsupportedSource,
    ];

    const ALL_SOURCES: [ReaderSourceClass; 5] = [
        ReaderSourceClass::SupportedWordml,
        ReaderSourceClass::SourceNotWordml,
        ReaderSourceClass::UnsupportedSchema,
        ReaderSourceClass::NamespaceAbsent,
        ReaderSourceClass::EmptySource,
    ];

    fn assert_invariant(completion: &WireCompletion) {
        if let WireCompletion::Incomplete { basis, reasons } = completion {
            assert!(
                !reasons.is_empty(),
                "an incomplete completion must carry a non-empty reason set"
            );
            assert!(
                reasons.contains(basis),
                "the reason set must contain the basis ({})",
                basis.as_str()
            );
        }
    }

    fn contains_limit_reached(completion: &WireCompletion) -> bool {
        match completion {
            WireCompletion::Complete => false,
            WireCompletion::Incomplete { basis, reasons } => {
                *basis == IncompleteReason::LimitReached
                    || reasons.contains(&IncompleteReason::LimitReached)
            }
        }
    }

    #[test]
    fn declaration_tokens_round_trip() {
        for declaration in ALL_DECLARATIONS {
            let token = declaration.as_str();
            assert_eq!(
                ScopeDeclaration::from_token(token),
                Ok(declaration),
                "round-trip failed for token {token:?}"
            );
        }
    }

    #[test]
    fn declaration_token_forms_are_closed() {
        assert_eq!(ScopeDeclaration::WholeProjection.as_str(), "complete");
        assert_eq!(ScopeDeclaration::StructureHold.as_str(), "hold");
        assert_eq!(ScopeDeclaration::TextOnlyScope.as_str(), "text_only");
        assert_eq!(ScopeDeclaration::NarrowedScope.as_str(), "caller_scope");
        assert_eq!(
            ScopeDeclaration::UnsupportedSource.as_str(),
            "unsupported_source"
        );
    }

    #[test]
    fn unknown_declaration_token_is_refused() {
        assert_eq!(
            ScopeDeclaration::from_token("not_a_declaration"),
            Err(CompletionError::UnknownToken)
        );
        assert_eq!(
            ScopeDeclaration::from_token(""),
            Err(CompletionError::UnknownToken)
        );
        assert_eq!(
            ScopeDeclaration::from_token("limit_reached"),
            Err(CompletionError::UnknownToken)
        );
        assert_eq!(
            CompletionError::UnknownToken.as_str(),
            "unknown_scope_declaration_token"
        );
        assert_eq!(
            CompletionError::UnknownToken.to_string(),
            "unknown_scope_declaration_token"
        );
    }

    #[test]
    fn whole_projection_maps_to_complete() {
        assert_eq!(
            completion_for(ScopeDeclaration::WholeProjection),
            WireCompletion::Complete
        );
    }

    #[test]
    fn every_declaration_maps_to_invariant_preserving_completion() {
        for declaration in ALL_DECLARATIONS {
            if declaration == ScopeDeclaration::WholeProjection {
                continue;
            }
            let completion = completion_for(declaration);
            assert_invariant(&completion);
            assert!(
                matches!(completion, WireCompletion::Incomplete { .. }),
                "only WholeProjection may be complete, got {:?}",
                completion
            );
        }
    }

    #[test]
    fn limit_reached_is_unreachable_from_declaration() {
        assert_eq!(
            ScopeDeclaration::from_token("limit_reached"),
            Err(CompletionError::UnknownToken)
        );
        for declaration in ALL_DECLARATIONS {
            assert!(
                !contains_limit_reached(&completion_for(declaration)),
                "declaration {:?} must never produce LimitReached",
                declaration
            );
        }
    }

    #[test]
    fn classify_is_total_over_sources_and_declarations() {
        for source_class in ALL_SOURCES {
            for declaration in ALL_DECLARATIONS {
                let completion = classify_completion(source_class, declaration);
                assert_invariant(&completion);
                let is_complete = matches!(completion, WireCompletion::Complete);
                let expected_complete = source_class == ReaderSourceClass::SupportedWordml
                    && declaration == ScopeDeclaration::WholeProjection;
                assert_eq!(
                    is_complete, expected_complete,
                    "Complete iff SupportedWordml and WholeProjection; \
                     source={:?} declaration={:?}",
                    source_class, declaration
                );
                assert!(
                    !contains_limit_reached(&completion),
                    "classify_completion must never produce LimitReached; \
                     source={:?} declaration={:?}",
                    source_class,
                    declaration
                );
            }
        }
    }

    #[test]
    fn unsupported_source_corrects_declared_complete() {
        for source_class in ALL_SOURCES {
            if source_class == ReaderSourceClass::SupportedWordml {
                continue;
            }
            let completion = classify_completion(source_class, ScopeDeclaration::WholeProjection);
            assert_eq!(
                completion,
                WireCompletion::Incomplete {
                    basis: IncompleteReason::UnsupportedSource,
                    reasons: vec![IncompleteReason::UnsupportedSource],
                }
            );
        }
    }

    #[test]
    fn unsupported_source_is_added_once_and_keeps_basis() {
        for source_class in ALL_SOURCES {
            if source_class == ReaderSourceClass::SupportedWordml {
                continue;
            }
            for declaration in ALL_DECLARATIONS {
                if declaration == ScopeDeclaration::WholeProjection {
                    continue;
                }
                let completion = classify_completion(source_class, declaration);
                let expected_basis = match completion_for(declaration) {
                    WireCompletion::Incomplete { basis, .. } => basis,
                    WireCompletion::Complete => unreachable!(),
                };
                match completion {
                    WireCompletion::Incomplete { basis, reasons } => {
                        assert_eq!(basis, expected_basis, "basis must be preserved");
                        let count = reasons
                            .iter()
                            .filter(|reason| **reason == IncompleteReason::UnsupportedSource)
                            .count();
                        assert_eq!(count, 1, "UnsupportedSource must appear exactly once");
                    }
                    WireCompletion::Complete => {
                        panic!("non-WholeProjection declaration must stay incomplete")
                    }
                }
            }
        }
    }

    #[test]
    fn unsupported_source_token_is_deduplicated() {
        // The UnsupportedSource declaration already carries the reason; the
        // correction must not duplicate it.
        for source_class in ALL_SOURCES {
            if source_class == ReaderSourceClass::SupportedWordml {
                continue;
            }
            let completion = classify_completion(source_class, ScopeDeclaration::UnsupportedSource);
            if let WireCompletion::Incomplete { reasons, .. } = completion {
                let count = reasons
                    .iter()
                    .filter(|reason| **reason == IncompleteReason::UnsupportedSource)
                    .count();
                assert_eq!(count, 1);
            } else {
                panic!("UnsupportedSource declaration must classify as incomplete");
            }
        }
    }
}
