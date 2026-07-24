use crate::domain::{CitationOutcome, CitationRequest, CitationResult, CITATION_POLICY_VERSION};
use crate::ports::CitationSourcePort;

pub struct ResolveCitation<S> {
    source: S,
}

impl<S> ResolveCitation<S>
where
    S: CitationSourcePort,
{
    pub fn new(source: S) -> Self {
        Self { source }
    }

    pub fn resolve(&self, request: CitationRequest) -> CitationResult {
        if request.anchor_invention_attempt {
            return CitationResult {
                outcome: CitationOutcome::AnchorInventionRejected,
                citation_id: request.citation_id,
                resolved_anchor: None,
                authoritative: false,
                policy_version: CITATION_POLICY_VERSION.to_owned(),
            };
        }
        if request.mirror_relabel_attempt {
            return CitationResult {
                outcome: CitationOutcome::MirrorRelabelRejected,
                citation_id: request.citation_id,
                resolved_anchor: None,
                authoritative: false,
                policy_version: CITATION_POLICY_VERSION.to_owned(),
            };
        }
        match self.source.resolve(&request.source_ref) {
            Some((anchor, authority)) => {
                let is_official = authority == crate::domain::SourceAuthority::Official;
                CitationResult {
                    outcome: if is_official {
                        CitationOutcome::Resolved
                    } else {
                        CitationOutcome::Invalid
                    },
                    citation_id: request.citation_id,
                    resolved_anchor: Some(anchor),
                    authoritative: is_official,
                    policy_version: CITATION_POLICY_VERSION.to_owned(),
                }
            }
            None => CitationResult {
                outcome: CitationOutcome::Missing,
                citation_id: request.citation_id,
                resolved_anchor: None,
                authoritative: false,
                policy_version: CITATION_POLICY_VERSION.to_owned(),
            },
        }
    }
}
