use crate::domain::CaseVerdict;
use crate::ports::ConformanceOraclePort;

/// Honest oracle: returns the real verdict for each HC case.
#[derive(Debug, Default)]
pub struct InMemoryConformanceOracle {
    cases: Vec<(String, CaseVerdict)>,
}

impl InMemoryConformanceOracle {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with(mut self, case_id: &str, verdict: CaseVerdict) -> Self {
        self.cases.push((case_id.to_owned(), verdict));
        self
    }
    pub fn all_pass(count: usize) -> Self {
        let mut oracle = Self::new();
        for i in 1..=count {
            oracle = oracle.with(&format!("HC-{i:02}"), CaseVerdict::Pass);
        }
        oracle
    }
}

impl ConformanceOraclePort for InMemoryConformanceOracle {
    fn case_verdict(&self, case_id: &str) -> CaseVerdict {
        self.cases
            .iter()
            .find(|(id, _)| id == case_id)
            .map(|(_, v)| *v)
            .unwrap_or(CaseVerdict::Unsupported)
    }
    fn all_case_ids(&self) -> Vec<String> {
        self.cases.iter().map(|(id, _)| id.clone()).collect()
    }
}

/// Hostile: inflates all unsupported cases to pass.
#[derive(Debug, Default)]
pub struct HostileVerdictInflator {
    real: InMemoryConformanceOracle,
}

impl HostileVerdictInflator {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with(mut self, case_id: &str, verdict: CaseVerdict) -> Self {
        self.real = self.real.with(case_id, verdict);
        self
    }
}

impl ConformanceOraclePort for HostileVerdictInflator {
    fn case_verdict(&self, case_id: &str) -> CaseVerdict {
        // Lie: return Pass for everything
        let _ = case_id;
        CaseVerdict::Pass
    }
    fn all_case_ids(&self) -> Vec<String> {
        self.real.all_case_ids()
    }
}
