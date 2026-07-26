use ln_citation::adapters::InMemoryCitationSource;
use ln_citation::application::ResolveCitation;
use ln_citation::domain::{
    CitationId, CitationOutcome, CitationRequest, SourceAuthority, SourceRef,
    CITATION_POLICY_VERSION,
};

fn req(source: &str, authority: SourceAuthority) -> CitationRequest {
    CitationRequest {
        citation_id: CitationId::parse("cit:1").unwrap(),
        source_ref: SourceRef::parse(source).unwrap(),
        requested_authority: authority,
        anchor_invention_attempt: false,
        mirror_relabel_attempt: false,
    }
}

#[test]
fn official_source_resolved() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new().with(
        "src:law",
        "anchor:1",
        SourceAuthority::Official,
    ));
    let result = svc.resolve(req("src:law", SourceAuthority::Official));
    assert_eq!(result.outcome, CitationOutcome::Resolved);
    assert!(result.authoritative);
    assert!(result.resolved_anchor.is_some());
}

#[test]
fn missing_source_returns_missing() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new());
    let result = svc.resolve(req("src:missing", SourceAuthority::Official));
    assert_eq!(result.outcome, CitationOutcome::Missing);
    assert!(!result.authoritative);
}

#[test]
fn mirror_source_returns_invalid_not_authoritative() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new().with(
        "src:mirror",
        "anchor:2",
        SourceAuthority::Mirror,
    ));
    let result = svc.resolve(req("src:mirror", SourceAuthority::Official));
    assert_eq!(result.outcome, CitationOutcome::Invalid);
    assert!(!result.authoritative);
}

#[test]
fn anchor_invention_rejected() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new());
    let mut r = req("src:1", SourceAuthority::Official);
    r.anchor_invention_attempt = true;
    let result = svc.resolve(r);
    assert_eq!(result.outcome, CitationOutcome::AnchorInventionRejected);
    assert!(result.resolved_anchor.is_none());
}

#[test]
fn mirror_relabel_rejected() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new());
    let mut r = req("src:1", SourceAuthority::Official);
    r.mirror_relabel_attempt = true;
    let result = svc.resolve(r);
    assert_eq!(result.outcome, CitationOutcome::MirrorRelabelRejected);
}

#[test]
fn policy_version_stable() {
    let svc = ResolveCitation::new(InMemoryCitationSource::new());
    let result = svc.resolve(req("src:1", SourceAuthority::Official));
    assert_eq!(result.policy_version, CITATION_POLICY_VERSION);
}
