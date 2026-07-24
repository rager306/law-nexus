use crate::domain::CaseVerdict;

pub trait ConformanceOraclePort: Send + Sync {
    fn case_verdict(&self, case_id: &str) -> CaseVerdict;
    fn all_case_ids(&self) -> Vec<String>;
}
