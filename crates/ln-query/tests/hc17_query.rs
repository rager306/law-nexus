use ln_query::adapters::{HostileGapInventorState, InMemoryQueryState};
use ln_query::application::ExecuteEvidenceBoundedQuery;
use ln_query::domain::{EvidenceId, QueryId, QueryOutcome, QueryRequest, ScopeId};

fn req(evidence: &[&str], invention: bool, fabrication: bool) -> QueryRequest {
    QueryRequest {
        query_id: QueryId::parse("q:1").unwrap(),
        scope_id: ScopeId::parse("scope:S1").unwrap(),
        requested_evidence: evidence
            .iter()
            .map(|s| EvidenceId::parse(s).unwrap())
            .collect(),
        invention_attempt: invention,
        fabrication_attempt: fabrication,
    }
}

#[test]
fn answered_when_all_evidence_exists() {
    let svc = ExecuteEvidenceBoundedQuery::new(
        InMemoryQueryState::new()
            .with_evidence("ev:1")
            .with_evidence("ev:2"),
    );
    let result = svc.query(req(&["ev:1", "ev:2"], false, false));
    assert_eq!(result.outcome, QueryOutcome::Answered);
    assert_eq!(result.returned_evidence.len(), 2);
    assert!(!result.authoritative);
}

#[test]
fn no_answer_when_evidence_missing() {
    let svc = ExecuteEvidenceBoundedQuery::new(InMemoryQueryState::new());
    let result = svc.query(req(&["ev:missing"], false, false));
    assert_eq!(result.outcome, QueryOutcome::NoAnswer);
    assert!(result.returned_evidence.is_empty());
}

#[test]
fn partial_when_some_evidence_exists() {
    let svc = ExecuteEvidenceBoundedQuery::new(InMemoryQueryState::new().with_evidence("ev:1"));
    let result = svc.query(req(&["ev:1", "ev:missing"], false, false));
    assert_eq!(result.outcome, QueryOutcome::Partial);
    assert_eq!(result.returned_evidence.len(), 1);
}

#[test]
fn invention_attempt_rejected() {
    let svc = ExecuteEvidenceBoundedQuery::new(InMemoryQueryState::new());
    let result = svc.query(req(&["ev:1"], true, false));
    assert_eq!(result.outcome, QueryOutcome::InventedRejected);
    assert!(result.returned_evidence.is_empty());
}

#[test]
fn fabrication_attempt_rejected() {
    let svc = ExecuteEvidenceBoundedQuery::new(InMemoryQueryState::new());
    let result = svc.query(req(&["ev:1"], false, true));
    assert_eq!(result.outcome, QueryOutcome::InventedRejected);
}

#[test]
fn hostile_gap_inventor_app_still_rejects_invention_flag() {
    let svc = ExecuteEvidenceBoundedQuery::new(HostileGapInventorState::new());
    let result = svc.query(req(&["ev:anything"], true, false));
    assert_eq!(result.outcome, QueryOutcome::InventedRejected);
}
