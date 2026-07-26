use crate::domain::{QueryOutcome, QueryRequest, QueryResult, QUERY_POLICY_VERSION};
use crate::ports::QueryStatePort;

pub struct ExecuteEvidenceBoundedQuery<S> {
    state: S,
}

impl<S> ExecuteEvidenceBoundedQuery<S>
where
    S: QueryStatePort,
{
    pub fn new(state: S) -> Self {
        Self { state }
    }

    pub fn query(&self, request: QueryRequest) -> QueryResult {
        if request.invention_attempt || request.fabrication_attempt {
            return QueryResult {
                outcome: QueryOutcome::InventedRejected,
                query_id: request.query_id,
                returned_evidence: vec![],
                authoritative: false,
                policy_version: QUERY_POLICY_VERSION.to_owned(),
            };
        }
        let mut found = vec![];
        let mut all_found = true;
        for eid in &request.requested_evidence {
            if self.state.has_evidence(eid) {
                found.push(eid.clone());
            } else {
                all_found = false;
            }
        }
        let outcome = if all_found && !found.is_empty() {
            QueryOutcome::Answered
        } else if !found.is_empty() {
            QueryOutcome::Partial
        } else {
            QueryOutcome::NoAnswer
        };
        QueryResult {
            outcome,
            query_id: request.query_id,
            returned_evidence: found,
            authoritative: false,
            policy_version: QUERY_POLICY_VERSION.to_owned(),
        }
    }
}
