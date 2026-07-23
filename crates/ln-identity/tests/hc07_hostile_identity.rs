use ln_identity::{
    adapters::ErasingMergerHostileStore,
    application::AssertIdentity,
    domain::{
        AssertRequest, ContributionId, EvidenceContribution, EvidenceSide, FamilyId, IdentityId,
        IdentityOutcome, IdentityReason,
    },
};

fn seeded_hostile() -> (AssertIdentity<ErasingMergerHostileStore>, IdentityId, IdentityId) {
    let right = IdentityId::parse("ID-B").expect("valid");
    let mut use_case = AssertIdentity::new(ErasingMergerHostileStore::targeting_right(&right));
    let left = IdentityId::parse("ID-A").expect("valid");
    use_case.seed(left.clone(), "left");
    use_case.seed(right.clone(), "right");
    (use_case, left, right)
}

#[test]
fn hostile_store_cannot_erase_right_identity_on_seed() {
    let (use_case, left, right) = seeded_hostile();
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}

#[test]
fn hostile_store_cannot_erase_on_one_sided_claim() {
    let (mut use_case, left, right) = seeded_hostile();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![EvidenceContribution {
            contribution_id: ContributionId::parse("contrib:L").expect("valid"),
            family_id: FamilyId::parse("family:consultant").expect("valid"),
            side: EvidenceSide::Left,
            evidence_ceiling: "family-local".to_owned(),
        }],
        claim_same: true,
        similarity_score: Some(95),
        method: "hostile-one-sided".to_owned(),
        scope: "global".to_owned(),
    });
    assert_eq!(result.outcome, IdentityOutcome::Candidate);
    assert_eq!(result.reason, IdentityReason::OneSidedEvidence);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(!result.merge_performed);
    assert!(result.no_merge_observation);
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}

#[test]
fn hostile_store_cannot_erase_on_similarity_only_claim() {
    let (mut use_case, left, right) = seeded_hostile();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: Vec::new(),
        claim_same: true,
        similarity_score: Some(99),
        method: "hostile-similarity".to_owned(),
        scope: "global".to_owned(),
    });
    assert_eq!(result.outcome, IdentityOutcome::Ambiguous);
    assert_eq!(result.reason, IdentityReason::SimilarityOnly);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(!result.merge_performed);
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}

#[test]
fn hostile_store_cannot_erase_on_bilateral_same_assertion() {
    let (mut use_case, left, right) = seeded_hostile();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:L").expect("valid"),
                family_id: FamilyId::parse("family:official").expect("valid"),
                side: EvidenceSide::Left,
                evidence_ceiling: "official".to_owned(),
            },
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:R").expect("valid"),
                family_id: FamilyId::parse("family:official").expect("valid"),
                side: EvidenceSide::Right,
                evidence_ceiling: "official".to_owned(),
            },
        ],
        claim_same: true,
        similarity_score: Some(80),
        method: "hostile-bilateral".to_owned(),
        scope: "official-family".to_owned(),
    });
    assert_eq!(result.outcome, IdentityOutcome::Same);
    assert!(!result.merge_performed);
    assert!(result.no_merge_observation);
    assert!(result.left_survives);
    assert!(result.right_survives);
    assert!(use_case.contains(&left));
    assert!(use_case.contains(&right));
}
