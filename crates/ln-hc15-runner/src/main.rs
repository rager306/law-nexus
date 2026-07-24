use std::env;
use std::process::ExitCode;

use ln_publish::adapters::{HostileDualWriterLedger, InMemoryPublicationLedger};
use ln_publish::application::PublishAuthoritativeH1;
use ln_publish::domain::{
    AuthoritySurface, CompletenessEvidence, CutoffId, InputDigest, OperationId, PublicationOutcome,
    PublishRequest, RuleVersion, ScopeId, WriterId, PUBLICATION_POLICY_VERSION,
};

struct ScenarioResult {
    outcome: PublicationOutcome,
    authoritative: bool,
    has_authority: bool,
    authority_surface_publication: bool,
    policy_version_ok: bool,
    authoritative_count: usize,
    pass: bool,
}

fn request(
    op: &str,
    writer: &str,
    scope: &str,
    digest: &str,
    completeness: CompletenessEvidence,
) -> PublishRequest {
    PublishRequest {
        operation_id: OperationId::parse(op).expect("static op"),
        writer_id: WriterId::parse(writer).expect("static writer"),
        scope_id: ScopeId::parse(scope).expect("static scope"),
        cutoff_id: CutoffId::parse("cutoff:2026-07-01").expect("static cutoff"),
        rule_version: RuleVersion::parse("rules:v1").expect("static rules"),
        input_digest: InputDigest::parse(digest).expect("static digest"),
        completeness,
    }
}

fn run_first_complete_publish() -> ScenarioResult {
    let mut svc = PublishAuthoritativeH1::new(InMemoryPublicationLedger::new());
    let result = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let pass = result.outcome == PublicationOutcome::Published
        && result.authoritative
        && result.has_publication_authority()
        && result.authority_surface == AuthoritySurface::Publication
        && result.policy_version == PUBLICATION_POLICY_VERSION
        && svc.authoritative_count() == 1;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.authoritative,
        has_authority: result.has_publication_authority(),
        authority_surface_publication: result.authority_surface == AuthoritySurface::Publication,
        policy_version_ok: result.policy_version == PUBLICATION_POLICY_VERSION,
        authoritative_count: svc.authoritative_count(),
        pass,
    }
}

fn run_identical_duplicate() -> ScenarioResult {
    let mut svc = PublishAuthoritativeH1::new(InMemoryPublicationLedger::new());
    let req = request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    );
    let first = svc.publish(req.clone());
    let second = svc.publish(req);
    let pass = first.outcome == PublicationOutcome::Published
        && second.outcome == PublicationOutcome::Duplicate
        && second.authoritative
        && second.h1_unit_id == first.h1_unit_id
        && svc.authoritative_count() == 1;
    ScenarioResult {
        outcome: second.outcome,
        authoritative: second.authoritative,
        has_authority: second.has_publication_authority(),
        authority_surface_publication: second.authority_surface == AuthoritySurface::Publication,
        policy_version_ok: second.policy_version == PUBLICATION_POLICY_VERSION,
        authoritative_count: svc.authoritative_count(),
        pass,
    }
}

fn run_competing_writer_rejected() -> ScenarioResult {
    let mut svc = PublishAuthoritativeH1::new(InMemoryPublicationLedger::new());
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let competitor = svc.publish(request(
        "op:2",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));
    let pass = first.outcome == PublicationOutcome::Published
        && competitor.outcome == PublicationOutcome::CompetingWriterRejected
        && !competitor.authoritative
        && competitor.h1_unit_id == first.h1_unit_id
        && svc.authoritative_count() == 1;
    ScenarioResult {
        outcome: competitor.outcome,
        authoritative: competitor.authoritative,
        has_authority: competitor.has_publication_authority(),
        authority_surface_publication: competitor.authority_surface
            == AuthoritySurface::Publication,
        policy_version_ok: competitor.policy_version == PUBLICATION_POLICY_VERSION,
        authoritative_count: svc.authoritative_count(),
        pass,
    }
}

fn run_partial_incomplete() -> ScenarioResult {
    let mut svc = PublishAuthoritativeH1::new(InMemoryPublicationLedger::new());
    let result = svc.publish(request(
        "op:partial",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Partial,
    ));
    let pass = result.outcome == PublicationOutcome::Incomplete
        && !result.authoritative
        && !result.has_publication_authority()
        && result.h1_unit_id.is_none()
        && svc.authoritative_count() == 0;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.authoritative,
        has_authority: result.has_publication_authority(),
        authority_surface_publication: result.authority_surface == AuthoritySurface::Publication,
        policy_version_ok: result.policy_version == PUBLICATION_POLICY_VERSION,
        authoritative_count: svc.authoritative_count(),
        pass,
    }
}

fn run_hostile_dual_writer_one_authority() -> ScenarioResult {
    let mut svc = PublishAuthoritativeH1::new(HostileDualWriterLedger::new());
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let hostile = svc.publish(request(
        "op:hostile",
        "writer:hostile",
        "scope:S1",
        "digest:D-evil",
        CompletenessEvidence::Complete,
    ));
    let pass = first.outcome == PublicationOutcome::Published
        && first.authoritative
        && hostile.outcome == PublicationOutcome::CompetingWriterRejected
        && !hostile.authoritative
        && hostile.h1_unit_id == first.h1_unit_id
        && svc.authoritative_count() == 1;
    ScenarioResult {
        outcome: hostile.outcome,
        authoritative: hostile.authoritative,
        has_authority: hostile.has_publication_authority(),
        authority_surface_publication: hostile.authority_surface == AuthoritySurface::Publication,
        policy_version_ok: hostile.policy_version == PUBLICATION_POLICY_VERSION,
        authoritative_count: svc.authoritative_count(),
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc15-receipt/v1\",\"case_id\":\"HC-15\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"authoritative\":{},\"has_authority\":{},\"authority_surface_publication\":{},\"policy_version_ok\":{},\"authoritative_count\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"fencing_selected\":false,\"transaction_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.authoritative,
        result.has_authority,
        result.authority_surface_publication,
        result.policy_version_ok,
        result.authoritative_count,
        result.pass,
    )
}

fn render_verdict() -> String {
    let first = run_first_complete_publish();
    let duplicate = run_identical_duplicate();
    let competing = run_competing_writer_rejected();
    let partial = run_partial_incomplete();
    let hostile = run_hostile_dual_writer_one_authority();
    let pass = first.pass && duplicate.pass && competing.pass && partial.pass && hostile.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc15-verdict/v1\",\"evidence_id\":\"S10-HC-15-RT\",\"case_id\":\"HC-15\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"first_complete_publish\":{},\"identical_duplicate\":{},\"competing_writer_rejected\":{},\"partial_incomplete_non_authoritative\":{},\"hostile_dual_writer_one_authority\":{},\"authority_surface_publication_only\":{},\"one_authoritative_unit_per_scope\":{},\"remaining_unsupported_cases\":5,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"fencing_selected\":false,\"transaction_selected\":false}}",
        first.pass,
        duplicate.pass,
        competing.pass,
        partial.pass,
        hostile.pass,
        first.authority_surface_publication
            && duplicate.authority_surface_publication
            && competing.authority_surface_publication
            && partial.authority_surface_publication
            && hostile.authority_surface_publication,
        first.authoritative_count == 1
            && duplicate.authoritative_count == 1
            && competing.authoritative_count == 1
            && partial.authoritative_count == 0
            && hostile.authoritative_count == 1,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc15_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "first-complete-publish" => run_first_complete_publish(),
        "identical-duplicate" => run_identical_duplicate(),
        "competing-writer-rejected" => run_competing_writer_rejected(),
        "partial-incomplete" => run_partial_incomplete(),
        "hostile-dual-writer-one-authority" => run_hostile_dual_writer_one_authority(),
        _ => {
            eprintln!("hc15_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
