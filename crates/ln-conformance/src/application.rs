use crate::domain::{CaseResult, CaseVerdict, ConformanceResult, CONFORMANCE_POLICY_VERSION};
use crate::ports::ConformanceOraclePort;

pub struct EvaluateConformance<O> {
    oracle: O,
}

impl<O> EvaluateConformance<O>
where
    O: ConformanceOraclePort,
{
    pub fn new(oracle: O) -> Self {
        Self { oracle }
    }

    pub fn evaluate(&self) -> ConformanceResult {
        let case_ids = self.oracle.all_case_ids();
        let mut cases = vec![];
        let mut pass_count = 0;
        let mut fail_count = 0;
        let mut unsupported_count = 0;

        for id in &case_ids {
            let verdict = self.oracle.case_verdict(id);
            match verdict {
                CaseVerdict::Pass => pass_count += 1,
                CaseVerdict::Fail => fail_count += 1,
                CaseVerdict::Unsupported => unsupported_count += 1,
            }
            cases.push(CaseResult {
                case_id: id.clone(),
                verdict,
            });
        }

        let overall = if fail_count > 0 {
            CaseVerdict::Fail
        } else if unsupported_count > 0 {
            CaseVerdict::Unsupported
        } else {
            CaseVerdict::Pass
        };

        ConformanceResult {
            schema: "law-nexus-hc20-conformance/v1".to_owned(),
            total_cases: case_ids.len(),
            pass_count,
            fail_count,
            unsupported_count,
            cases,
            overall_verdict: overall,
            policy_version: CONFORMANCE_POLICY_VERSION.to_owned(),
        }
    }
}
