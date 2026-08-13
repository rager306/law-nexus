//! Contract tests for NormRule IR (RC11-F04a / ADR-0023 design spine).
//!
//! Lifecycle [proposed]: IR is structural design only. Presence of a valid IR
//! must never mint Applicable/NotApplicable.

use ln_applicability::domain::{
    Defeater, Exception, NormRule, NormRuleCondition, NormRuleId, NormRuleIrError,
    NormRuleRevision, TemporalScope,
};

fn rule_id() -> NormRuleId {
    NormRuleId::parse("rule:44fz:art-31").expect("id")
}

fn revision() -> NormRuleRevision {
    NormRuleRevision::parse("normrule:rev:v0-design").expect("rev")
}

fn condition(id: &str) -> NormRuleCondition {
    NormRuleCondition::try_new(id, "fact_required").expect("condition")
}

#[test]
fn valid_norm_rule_ir_requires_conditions_exceptions_defeaters_and_temporal_scope() {
    let scope = TemporalScope::try_new(Some("2024-01-01"), Some("2025-12-31")).expect("scope");
    let rule = NormRule::try_new(
        rule_id(),
        revision(),
        vec![condition("cond:subject-kind")],
        vec![Exception::try_new("exc:small-purchase", "exception_clause").expect("exc")],
        vec![Defeater::try_new("def:special-norm", "special_norm_defeats").expect("def")],
        scope,
    )
    .expect("valid IR");

    assert_eq!(rule.id().as_str(), "rule:44fz:art-31");
    assert_eq!(rule.revision().as_str(), "normrule:rev:v0-design");
    assert_eq!(rule.conditions().len(), 1);
    assert_eq!(rule.exceptions().len(), 1);
    assert_eq!(rule.defeaters().len(), 1);
    assert_eq!(rule.temporal_scope().effective_from(), Some("2024-01-01"));
    assert_eq!(rule.temporal_scope().effective_to(), Some("2025-12-31"));
}

#[test]
fn empty_conditions_fail_closed() {
    let scope = TemporalScope::unbounded();
    let err = NormRule::try_new(rule_id(), revision(), vec![], vec![], vec![], scope)
        .expect_err("empty conditions");
    assert!(matches!(err, NormRuleIrError::EmptyConditions));
}

#[test]
fn inverted_temporal_scope_fails_closed() {
    let err =
        TemporalScope::try_new(Some("2025-01-01"), Some("2024-01-01")).expect_err("inverted range");
    assert!(matches!(err, NormRuleIrError::InvertedTemporalScope));
}

#[test]
fn blank_condition_id_fails_closed() {
    let err = NormRuleCondition::try_new("", "fact_required").expect_err("blank id");
    assert!(matches!(err, NormRuleIrError::InvalidId(_)));
}

#[test]
fn unsupported_condition_kind_fails_closed() {
    let err = NormRuleCondition::try_new("cond:x", "llm_prose_guess").expect_err("kind");
    assert!(matches!(err, NormRuleIrError::UnsupportedConditionKind));
}

#[test]
fn open_ended_temporal_scope_is_allowed() {
    let from_only = TemporalScope::try_new(Some("2024-01-01"), None).expect("from");
    assert_eq!(from_only.effective_from(), Some("2024-01-01"));
    assert_eq!(from_only.effective_to(), None);

    let to_only = TemporalScope::try_new(None, Some("2025-12-31")).expect("to");
    assert_eq!(to_only.effective_from(), None);
    assert_eq!(to_only.effective_to(), Some("2025-12-31"));

    let unbounded = TemporalScope::unbounded();
    assert_eq!(unbounded.effective_from(), None);
    assert_eq!(unbounded.effective_to(), None);
}

#[test]
fn invalid_date_shape_fails_closed() {
    let err = TemporalScope::try_new(Some("01-01-2024"), None).expect_err("date shape");
    assert!(matches!(err, NormRuleIrError::InvalidTemporalDate));
}
