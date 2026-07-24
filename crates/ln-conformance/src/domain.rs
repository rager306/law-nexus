pub const CONFORMANCE_POLICY_VERSION: &str = "hc20:evaluate-conformance:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CaseVerdict {
    Pass,
    Fail,
    Unsupported,
}

impl CaseVerdict {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "pass",
            Self::Fail => "fail",
            Self::Unsupported => "unsupported",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CaseResult {
    pub case_id: String,
    pub verdict: CaseVerdict,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConformanceResult {
    pub schema: String,
    pub total_cases: usize,
    pub pass_count: usize,
    pub fail_count: usize,
    pub unsupported_count: usize,
    pub cases: Vec<CaseResult>,
    pub overall_verdict: CaseVerdict,
    pub policy_version: String,
}
