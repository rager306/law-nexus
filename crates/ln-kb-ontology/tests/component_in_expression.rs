//! ComponentConcept presence in a FRBR Expression (KBO component_in_expression).
//!
//! CC identity is stable across editions. Presence in a dated Expression is a
//! separate event-sourced projection. Not CTV text, not force, not decode lift.

use ln_identity::domain::{mint_expression, mint_work};
use ln_kb_ontology::domain::{
    expression_contains, filter_ast_to_expression, fold_expression_presence,
    project_expression_presence, ComponentInExpressionEvent, ComponentInExpressionLog,
    WriteSetError,
};
use ln_temporal::domain::{
    fold_membership_at, ComponentConceptId, MembershipChangeKind, VersionedMembershipEvent,
    VersionedMembershipLog,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn expr_2014() -> ln_identity::domain::FrbrExpression {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("work");
    mint_expression(&work, "2014-01-01").expect("expr")
}

fn expr_2022() -> ln_identity::domain::FrbrExpression {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("work");
    mint_expression(&work, "2022-07-01").expect("expr")
}

fn include(
    expr: &ln_identity::domain::FrbrExpression,
    component: &str,
    day: i64,
) -> ComponentInExpressionEvent {
    ComponentInExpressionEvent::try_new(
        "include",
        expr.expression_id.clone(),
        cc(component),
        day,
        "act:p",
    )
    .expect("include")
}

fn exclude(
    expr: &ln_identity::domain::FrbrExpression,
    component: &str,
    day: i64,
) -> ComponentInExpressionEvent {
    ComponentInExpressionEvent::try_new(
        "exclude",
        expr.expression_id.clone(),
        cc(component),
        day,
        "act:p",
    )
    .expect("exclude")
}

#[test]
fn missing_component_is_not_in_expression() {
    let expr = expr_2014();
    let log = ComponentInExpressionLog::empty();
    let set = fold_expression_presence(&log, &expr.expression_id, 10).expect("fold");
    assert!(!expression_contains(&set, &cc("cc:art-93-3")));
    assert!(set.is_projection());
}

#[test]
fn include_makes_component_present() {
    let expr = expr_2014();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93", 1)).expect("a");
    let set = fold_expression_presence(&log, &expr.expression_id, 1).expect("fold");
    assert!(expression_contains(&set, &cc("cc:art-93")));
}

#[test]
fn later_expression_does_not_inherit_silently() {
    let e2014 = expr_2014();
    let e2022 = expr_2022();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&e2014, "cc:art-93", 1)).expect("a");
    let set_2022 = fold_expression_presence(&log, &e2022.expression_id, 10).expect("fold");
    assert!(!expression_contains(&set_2022, &cc("cc:art-93")));
}

#[test]
fn exclude_removes_presence_after_day() {
    let expr = expr_2014();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93", 1)).expect("i");
    log.append(exclude(&expr, "cc:art-93", 8)).expect("x");
    assert!(expression_contains(
        &fold_expression_presence(&log, &expr.expression_id, 7).expect("t7"),
        &cc("cc:art-93")
    ));
    assert!(!expression_contains(
        &fold_expression_presence(&log, &expr.expression_id, 8).expect("t8"),
        &cc("cc:art-93")
    ));
}

#[test]
fn future_include_is_invisible() {
    let expr = expr_2014();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93-3", 20)).expect("i");
    let set = fold_expression_presence(&log, &expr.expression_id, 5).expect("fold");
    assert!(!expression_contains(&set, &cc("cc:art-93-3")));
}

#[test]
fn same_day_include_and_exclude_is_conflict() {
    let expr = expr_2014();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93", 3)).expect("i");
    log.append(exclude(&expr, "cc:art-93", 3)).expect("x");
    let err = fold_expression_presence(&log, &expr.expression_id, 3).expect_err("conflict");
    assert!(matches!(
        err,
        ln_kb_ontology::domain::WriteSetError::PresenceConflict
    ));
}

#[test]
fn filter_ast_drops_components_not_in_expression() {
    let expr = expr_2014();
    let mut membership = VersionedMembershipLog::empty();
    membership
        .append(
            VersionedMembershipEvent::try_new(
                MembershipChangeKind::Attach,
                cc("cc:ch-3"),
                cc("cc:art-93"),
                1,
                ln_temporal::domain::AmendingActId::parse("act:p").expect("act"),
            )
            .expect("e1"),
        )
        .expect("a1");
    membership
        .append(
            VersionedMembershipEvent::try_new(
                MembershipChangeKind::Attach,
                cc("cc:ch-3"),
                cc("cc:art-93-3"),
                1,
                ln_temporal::domain::AmendingActId::parse("act:p").expect("act"),
            )
            .expect("e2"),
        )
        .expect("a2");
    let ast = fold_membership_at(&membership, 1).expect("ast");

    let mut presence = ComponentInExpressionLog::empty();
    presence.append(include(&expr, "cc:ch-3", 1)).expect("p1");
    presence.append(include(&expr, "cc:art-93", 1)).expect("p2");
    // art-93-3 exists in membership tree but not in this Expression
    let present = fold_expression_presence(&presence, &expr.expression_id, 1).expect("pres");
    let edition = filter_ast_to_expression(&ast, &present).expect("filter");
    let kids: Vec<&str> = edition.roots()[0]
        .children()
        .iter()
        .map(|n| n.component().as_str())
        .collect();
    assert_eq!(kids, vec!["cc:art-93"]);
}

#[test]
fn project_presence_emits_component_in_expression_edge() {
    let expr = expr_2014();
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93", 1)).expect("i");
    let set = fold_expression_presence(&log, &expr.expression_id, 1).expect("fold");
    let ws = project_expression_presence(&expr, &set).expect("ws");
    assert!(ws.edges.iter().any(|e| e.kind == "component_in_expression"));
    assert!(!ws.performs_io);
    assert!(!ws.claims_applicability);
}

#[test]
fn unknown_presence_kind_is_rejected() {
    let expr = expr_2014();
    let err = ComponentInExpressionEvent::try_new(
        "upsert",
        expr.expression_id.clone(),
        cc("cc:art-93"),
        1,
        "act:p",
    )
    .expect_err("unknown");
    assert!(matches!(err, WriteSetError::UnknownPresenceKind));
}

#[test]
fn calendar_day_of_expression_is_fold_as_of() {
    use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
    let expr = expr_2014();
    let as_of = legal_act_effect_day_to_ordinal(&expr.legal_act_effect_day).expect("iso");
    let mut log = ComponentInExpressionLog::empty();
    log.append(include(&expr, "cc:art-93", as_of)).expect("i");
    let set = fold_expression_presence(&log, &expr.expression_id, as_of).expect("fold");
    assert!(expression_contains(&set, &cc("cc:art-93")));
    assert!(
        fold_expression_presence(&log, &expr.expression_id, as_of - 1)
            .expect("before")
            .components()
            .is_empty()
    );
}
