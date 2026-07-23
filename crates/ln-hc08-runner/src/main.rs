use std::env;
use std::process::ExitCode;

use ln_relation::adapters::InMemoryClosedRegistry;
use ln_relation::application::ValidateRelation;
use ln_relation::domain::{
    EndpointId, EvidenceRef, FamilyId, PredicateId, RelationOutcome, RelationProposal,
    C13_GATE_VERSION, DEFAULT_REGISTRY_VERSION,
};

struct ScenarioResult {
    outcome: RelationOutcome,
    registry_unchanged: bool,
    stored_as_fact: bool,
    exposed_as_query_fact: bool,
    c13_version_ok: bool,
    registry_version_ok: bool,
    digest_present: bool,
    pass: bool,
}

fn use_case() -> ValidateRelation<InMemoryClosedRegistry> {
    ValidateRelation::new(InMemoryClosedRegistry::with_family_a_predicate())
}

fn run_unknown_predicate_reject() -> ScenarioResult {
    let mut gate = use_case();
    let before = gate.registered_count();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("relates-to").expect("static id"),
        subject: EndpointId::parse("E1").expect("static id"),
        object: EndpointId::parse("E2").expect("static id"),
        proposed_owner: FamilyId::parse("family-A").expect("static id"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("static id")],
    });
    let pass = result.outcome == RelationOutcome::UnknownPredicate
        && result.registry_unchanged
        && !result.stored_as_fact
        && !result.exposed_as_query_fact
        && gate.registered_count() == before
        && gate.accepted_fact_count() == 0
        && result.c13_version == C13_GATE_VERSION
        && result.registry_version.as_str() == DEFAULT_REGISTRY_VERSION
        && result.input_chain_digest.as_str().starts_with("fnv1a64:");
    ScenarioResult {
        outcome: result.outcome,
        registry_unchanged: result.registry_unchanged,
        stored_as_fact: result.stored_as_fact,
        exposed_as_query_fact: result.exposed_as_query_fact,
        c13_version_ok: result.c13_version == C13_GATE_VERSION,
        registry_version_ok: result.registry_version.as_str() == DEFAULT_REGISTRY_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn run_wrong_owner_reject() -> ScenarioResult {
    let mut gate = use_case();
    let before = gate.registered_count();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("static id"),
        subject: EndpointId::parse("E1").expect("static id"),
        object: EndpointId::parse("E2").expect("static id"),
        proposed_owner: FamilyId::parse("family-B").expect("static id"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("static id")],
    });
    let pass = result.outcome == RelationOutcome::WrongOwner
        && result.registry_unchanged
        && !result.stored_as_fact
        && !result.exposed_as_query_fact
        && gate.registered_count() == before
        && gate.accepted_fact_count() == 0;
    ScenarioResult {
        outcome: result.outcome,
        registry_unchanged: result.registry_unchanged,
        stored_as_fact: result.stored_as_fact,
        exposed_as_query_fact: result.exposed_as_query_fact,
        c13_version_ok: result.c13_version == C13_GATE_VERSION,
        registry_version_ok: result.registry_version.as_str() == DEFAULT_REGISTRY_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn run_correct_owner_accept() -> ScenarioResult {
    let mut gate = use_case();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("static id"),
        subject: EndpointId::parse("E1").expect("static id"),
        object: EndpointId::parse("E2").expect("static id"),
        proposed_owner: FamilyId::parse("family-A").expect("static id"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("static id")],
    });
    let pass = result.outcome == RelationOutcome::Accepted
        && result.registry_unchanged
        && result.stored_as_fact
        && result.exposed_as_query_fact
        && gate.accepted_fact_count() == 1
        && gate.query_has_fact(
            &PredicateId::parse("amends").expect("static id"),
            &EndpointId::parse("E1").expect("static id"),
            &EndpointId::parse("E2").expect("static id"),
        );
    ScenarioResult {
        outcome: result.outcome,
        registry_unchanged: result.registry_unchanged,
        stored_as_fact: result.stored_as_fact,
        exposed_as_query_fact: result.exposed_as_query_fact,
        c13_version_ok: result.c13_version == C13_GATE_VERSION,
        registry_version_ok: result.registry_version.as_str() == DEFAULT_REGISTRY_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc08-receipt/v1\",\"case_id\":\"HC-08\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"registry_unchanged\":{},\"stored_as_fact\":{},\"exposed_as_query_fact\":{},\"c13_version_ok\":{},\"registry_version_ok\":{},\"digest_present\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"graph_schema_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.registry_unchanged,
        result.stored_as_fact,
        result.exposed_as_query_fact,
        result.c13_version_ok,
        result.registry_version_ok,
        result.digest_present,
        result.pass,
    )
}

fn render_verdict() -> String {
    let unknown = run_unknown_predicate_reject();
    let wrong_owner = run_wrong_owner_reject();
    let accepted = run_correct_owner_accept();
    let pass = unknown.pass && wrong_owner.pass && accepted.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc08-verdict/v1\",\"evidence_id\":\"S10-HC-08-RT\",\"case_id\":\"HC-08\",\"verdict\":\"{verdict}\",\"scenario_count\":3,\"unknown_predicate_reject\":{},\"wrong_owner_reject\":{},\"correct_owner_accept\":{},\"registry_unchanged_on_reject\":{},\"rejected_not_query_facts\":{},\"remaining_unsupported_cases\":12,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"graph_schema_selected\":false}}",
        unknown.pass,
        wrong_owner.pass,
        accepted.pass,
        unknown.registry_unchanged && wrong_owner.registry_unchanged,
        !unknown.exposed_as_query_fact && !wrong_owner.exposed_as_query_fact,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc08_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "unknown-predicate-reject" => run_unknown_predicate_reject(),
        "wrong-owner-reject" => run_wrong_owner_reject(),
        "correct-owner-accept" => run_correct_owner_accept(),
        _ => {
            eprintln!("hc08_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
