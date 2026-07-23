use ln_identity::{
    adapters::InMemoryIdentityStore,
    application::AssertIdentity,
    domain::{
        AssertRequest, ContributionId, EvidenceContribution, EvidenceSide, FamilyId, IdentityId,
        IdentityOutcome, IdentityReason, C12_GATE_VERSION,
    },
};

fn seeded() -> (AssertIdentity<InMemoryIdentityStore>, IdentityId, IdentityId) {
    let mut use_case = AssertIdentity::new(InMemoryIdentityStore::default());
    let left = IdentityId::parse("ID-A").expect("valid");
    let right = IdentityId::parse("ID-B").expect("valid");
    use_case.seed(left.clone(), "Act 44-FZ edition A");
    use_case.seed(right.clone(), "Act 44-FZ edition B similar");
    (use_case, left, right)
}

#[test]
fn one_sided_claim_same_cannot_merge_or_assert_same() {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![EvidenceContribution {
            contribution_id: ContributionId::parse("contrib:left-1").expect("valid"),
            family_id: FamilyId::parse("family:consultant").expect("valid"),
            side: EvidenceSide::Left,
            evidence_ceiling: "family-local".to_owned(),
        }],
        claim_same: true,
        similarity_score: Some(95),
        method: "one-sided-family-claim".to_owned(),
        scope: "cross-family".to_owned(),
    });

    assert_ne!(result.outcome, IdentityOutcome::Same);
    assert_eq!(result.outcome, IdentityOutcome::Candidate);
    assert_eq!(result.reason, IdentityReason::OneSidedEvidence);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(!result.merge_performed);
    assert!(result.no_merge_observation);
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
    assert_eq!(result.c12_version.as_str(), C12_GATE_VERSION);
    assert!(result.evidence_ceiling_visible);
    assert!(!result.method.is_empty());
    assert!(!result.scope.is_empty());
}

#[test]
fn similarity_only_cannot_authorize_same_or_merge() {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: Vec::new(),
        claim_same: true,
        similarity_score: Some(99),
        method: "filename-number-similarity".to_owned(),
        scope: "global".to_owned(),
    });

    assert_eq!(result.outcome, IdentityOutcome::Ambiguous);
    assert_eq!(result.reason, IdentityReason::SimilarityOnly);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(!result.merge_performed);
    assert!(result.no_merge_observation);
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}

#[test]
fn bilateral_evidence_may_assert_same_but_never_merges() {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:L").expect("valid"),
                family_id: FamilyId::parse("family:official").expect("valid"),
                side: EvidenceSide::Left,
                evidence_ceiling: "official-bilateral".to_owned(),
            },
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:R").expect("valid"),
                family_id: FamilyId::parse("family:official").expect("valid"),
                side: EvidenceSide::Right,
                evidence_ceiling: "official-bilateral".to_owned(),
            },
        ],
        claim_same: true,
        similarity_score: Some(80),
        method: "bilateral-official".to_owned(),
        scope: "official-family".to_owned(),
    });

    assert_eq!(result.outcome, IdentityOutcome::Same);
    assert_eq!(result.reason, IdentityReason::BilateralSameEvidence);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(!result.merge_performed);
    assert!(result.no_merge_observation);
    assert_eq!(result.contribution_ids.len(), 2);
    assert!(result.input_chain_digest.as_str().starts_with("fnv1a64:"));
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}
