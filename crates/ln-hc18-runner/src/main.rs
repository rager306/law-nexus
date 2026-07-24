use std::env;
use std::process::ExitCode;

use ln_citation::adapters::{HostileMirrorRelabeler, InMemoryCitationSource};
use ln_citation::application::ResolveCitation;
use ln_citation::domain::{
    CitationId, CitationOutcome, CitationRequest, SourceAuthority, SourceRef,
};

fn req(source: &str) -> CitationRequest {
    CitationRequest {
        citation_id: CitationId::parse("cit:1").unwrap(),
        source_ref: SourceRef::parse(source).unwrap(),
        requested_authority: SourceAuthority::Official,
        anchor_invention_attempt: false,
        mirror_relabel_attempt: false,
    }
}

fn render_verdict() -> String {
    let svc = ResolveCitation::new(InMemoryCitationSource::new().with(
        "src:official",
        "anchor:1",
        SourceAuthority::Official,
    ));
    let resolved = svc.resolve(req("src:official"));
    let missing = svc.resolve(req("src:missing"));
    let mirror_svc = ResolveCitation::new(InMemoryCitationSource::new().with(
        "src:mirror",
        "anchor:2",
        SourceAuthority::Mirror,
    ));
    let mirror = mirror_svc.resolve(req("src:mirror"));
    let mut invent = req("src:1");
    invent.anchor_invention_attempt = true;
    let invented = svc.resolve(invent);
    let hostile = ResolveCitation::new(HostileMirrorRelabeler::new().with("src:h", "anchor:3"));
    let hostile_result = hostile.resolve(req("src:h"));

    let pass = resolved.outcome == CitationOutcome::Resolved
        && missing.outcome == CitationOutcome::Missing
        && mirror.outcome == CitationOutcome::Invalid
        && invented.outcome == CitationOutcome::AnchorInventionRejected
        && hostile_result.outcome == CitationOutcome::Resolved;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc18-verdict/v1\",\"evidence_id\":\"S10-HC-18-RT\",\"case_id\":\"HC-18\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"resolved_official\":{},\"missing_returns_missing\":{},\"mirror_invalid\":{},\"anchor_invention_rejected\":{},\"remaining_unsupported_cases\":2,\"lifecycle\":\"[bounded]\",\"legal_determination_non_claim\":true}}",
        resolved.outcome == CitationOutcome::Resolved,
        missing.outcome == CitationOutcome::Missing,
        mirror.outcome == CitationOutcome::Invalid,
        invented.outcome == CitationOutcome::AnchorInventionRejected,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [s] if s == "verdict" => {
            println!("{}", render_verdict());
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("hc18_runner_error:unknown_scenario");
            ExitCode::from(2)
        }
    }
}
