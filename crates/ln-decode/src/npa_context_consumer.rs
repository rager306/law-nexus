//! S03 T03: bounded consumer seam over the emitted `context` family
//! (M221-wbslul, `prd/architecture/npa-analysis-jsonl-contract.md` §8C).
//!
//! The producer is the unchanged
//! [`crate::npa_context_records::build_context_records`]. This module is the
//! closed consumer described by §8C: it maps the emitted `context` records to
//! the closed [`ThisDocumentReferenceOutcome`] decision about this-document
//! reference authorization. It is deliberately **not** feedback into
//! `npa_typed`/`npa_link`/`npa_classify` and **not** legal-semantic acceptance;
//! no variant carries decoded text.
//!
//! Fail-closed mapping (§8C.3):
//!
//! | condition | outcome |
//! |---|---|
//! | no `current_document_requisites` result | `NotRequested` |
//! | `resolved` with an inherited `authorized_current_document_requisites` claim | `Authorized { claim_ref }` |
//! | `resolved` with no such claim | `Conflicting` |
//! | `partial` / `conflicting` | `Conflicting` |
//! | `unavailable` / `cycle` / `limit` | `Unavailable` |
//!
//! The producer emits at most one requisites result per document. If several
//! are present anyway, the worst outcome wins: `Conflicting` outranks
//! `Unavailable`, which outranks `Authorized`.

use crate::analysis_source_mapping::SourceMapping;
use crate::document_context::{ContextClaimStatus, ContextRequestKind, ContextStatus};
use crate::local_grammar::DerivationSource;
use crate::npa_analysis_records::AnalysisBlockLayout;
use crate::npa_context_records::{ContextRecord, build_context_records};

/// The closed, bounded this-document reference decision (§8C).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ThisDocumentReferenceOutcome {
    /// A `resolved` requisites result carries the inherited
    /// `authorized_current_document_requisites` claim. `claim_ref` is the
    /// family-local `ref` of the result that carries the authorizing claim.
    Authorized {
        /// Family-local reference of the authorizing context result (`ctx:<n>`).
        claim_ref: String,
    },
    /// A requisites result is `partial`/`conflicting`, or a `resolved` result
    /// lacks the authorizing inherited claim (fail-closed).
    Conflicting,
    /// A requisites result is `unavailable`/`cycle`/`limit`.
    Unavailable,
    /// No `current_document_requisites` result was emitted.
    NotRequested,
}

impl ThisDocumentReferenceOutcome {
    /// Closed token for the outcome. Count-only; never decoded text.
    pub const fn token(&self) -> &'static str {
        match self {
            Self::Authorized { .. } => "authorized",
            Self::Conflicting => "conflicting",
            Self::Unavailable => "unavailable",
            Self::NotRequested => "not_requested",
        }
    }
}

/// The bounded consumer: maps the emitted `context` family to the closed
/// this-document reference decision (§8C.3). Pure and deterministic.
pub fn consume_this_document_reference(records: &[ContextRecord]) -> ThisDocumentReferenceOutcome {
    let mut requested = false;
    let mut conflicting = false;
    let mut unavailable = false;
    let mut authorized: Option<String> = None;

    for record in records {
        let ContextRecord::Result(result) = record else {
            continue;
        };
        if result.request_kind != ContextRequestKind::CurrentDocumentRequisites {
            continue;
        }
        requested = true;
        match result.status {
            ContextStatus::Partial | ContextStatus::Conflicting => conflicting = true,
            ContextStatus::Unavailable | ContextStatus::Cycle | ContextStatus::Limit => {
                unavailable = true;
            }
            ContextStatus::Resolved => {
                // `Authorized` requires the authorizing inherited claim to carry a
                // bound source anchor (a refused/missing anchor is inadmissible)
                // and no sibling claim to be left conflicting.
                let authorized_claim = result.claims.iter().find(|claim| {
                    claim.derivation == DerivationSource::AuthorizedCurrentDocumentRequisites
                        && claim.claim_status == ContextClaimStatus::Inherited
                        && claim.anchor.is_bound()
                });
                let has_conflicting_claim = result
                    .claims
                    .iter()
                    .any(|claim| claim.claim_status == ContextClaimStatus::Conflicting);
                if authorized_claim.is_some() && !has_conflicting_claim {
                    if authorized.is_none() {
                        authorized = Some(result.reference.clone());
                    }
                } else {
                    // A `resolved` requisites result without a bound authorizing
                    // inherited claim cannot be promoted to success.
                    conflicting = true;
                }
            }
        }
    }

    if !requested {
        return ThisDocumentReferenceOutcome::NotRequested;
    }
    if conflicting {
        return ThisDocumentReferenceOutcome::Conflicting;
    }
    if unavailable {
        return ThisDocumentReferenceOutcome::Unavailable;
    }
    match authorized {
        Some(claim_ref) => ThisDocumentReferenceOutcome::Authorized { claim_ref },
        // Requested, every result `resolved`, but no authorizing claim: refused.
        None => ThisDocumentReferenceOutcome::Conflicting,
    }
}

/// Document-level consumer entrypoint (§8C): builds the deterministic context
/// record stream from the analysis layout and the pinned parent mapping, then
/// consumes it. The records are returned so the caller can render the exact
/// same stream (for example the wire `context` family) without a second build.
pub fn consume_document_this_document_reference(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> (Vec<ContextRecord>, ThisDocumentReferenceOutcome) {
    let records = build_context_records(layout, mapping);
    let outcome = consume_this_document_reference(&records);
    (records, outcome)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_stream_is_not_requested() {
        assert_eq!(
            consume_this_document_reference(&[]),
            ThisDocumentReferenceOutcome::NotRequested
        );
    }

    #[test]
    fn token_table_is_closed() {
        assert_eq!(
            ThisDocumentReferenceOutcome::Authorized {
                claim_ref: "ctx:0".to_owned()
            }
            .token(),
            "authorized"
        );
        assert_eq!(
            ThisDocumentReferenceOutcome::Conflicting.token(),
            "conflicting"
        );
        assert_eq!(
            ThisDocumentReferenceOutcome::Unavailable.token(),
            "unavailable"
        );
        assert_eq!(
            ThisDocumentReferenceOutcome::NotRequested.token(),
            "not_requested"
        );
    }
}
