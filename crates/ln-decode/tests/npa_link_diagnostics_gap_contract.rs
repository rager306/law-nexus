//! M211 S04 T04: emission of the S03-declared gap diagnostics.
//!
//! `LinkDiagnostic::TypeNotInherited` and `LinkedRelationKind::HeadFamilyCarry`
//! were declared in S03 but never emitted (D619); this suite pins their
//! observable emission from the single assembly point `build_linked_document`:
//!
//! - a cross-block tail that keeps its own empty TYPE yields exactly one
//!   `TypeNotInherited` beside its `ContinuesSeries` edge;
//! - a tail that carries its own TYPE yields none;
//! - a typeless quoted requisite inside the narrow context-carry cliché yields
//!   a `HeadFamilyCarry` relation with two valid source-local anchors;
//! - a carry whose target already has a locally written TYPE yields none;
//! - replay is structurally stable.

use ln_decode::npa_anchor;
use ln_decode::npa_link::{self, LinkDiagnostic, LinkedRelationKind};

/// The narrow context-carry cliché from ADR-0029 §4 / the Python differential
/// reference (`CTX_CARRY`). The quoted requisite is deliberately left without a
/// local TYPE by the typed stream, so the carry is the only family source.
const CLICHE: &str = "В соответствии с правовой позицией Конституционного Суда Российской Федерации, изложенной в Постановлении от 23.12.2019 N 44-П, суды должны учитывать";

fn count(linked: &npa_link::LinkedDocument, diagnostic: LinkDiagnostic) -> usize {
    linked
        .diagnostics
        .iter()
        .filter(|found| **found == diagnostic)
        .count()
}

#[test]
fn typeless_cross_block_tail_emits_exactly_one_type_not_inherited() {
    let paras = vec![
        "Федерального закона от 01.01.2020 N 1-ФЗ,".to_string(),
        "от 02.02.2021 N 2-ФЗ".to_string(),
    ];
    let linked = npa_link::build_linked_document(&paras);
    assert_eq!(
        count(&linked, LinkDiagnostic::TypeNotInherited),
        1,
        "exactly one refusal of cross-block TYPE inheritance: {:?}",
        linked.diagnostics
    );

    // The refusal sits beside the continuation whose second anchor is the tail
    // member (a `LinkDiagnostic` carries no span payload).
    let edge = linked
        .relations
        .iter()
        .find(|relation| relation.kind == LinkedRelationKind::ContinuesSeries)
        .expect("the open head must continue into the bare tail");
    assert_eq!(edge.evidence.len(), 2);
    assert_eq!(edge.evidence[1].block, 1);
    assert_eq!(
        linked.members[edge.to_id].type_name, "",
        "the tail keeps its own empty TYPE"
    );
    assert!(
        !linked.members[edge.from_id].type_name.is_empty(),
        "the head TYPE is written locally"
    );
}

#[test]
fn tail_with_its_own_type_emits_no_type_not_inherited() {
    // The second citation carries its own TYPE, so nothing is inherited.
    let paras = vec![
        "Федерального закона от 01.01.2020 N 1-ФЗ,".to_string(),
        "Федеральный закон от 02.02.2021 N 2-ФЗ".to_string(),
    ];
    let linked = npa_link::build_linked_document(&paras);
    assert_eq!(
        count(&linked, LinkDiagnostic::TypeNotInherited),
        0,
        "{:?}",
        linked.diagnostics
    );
}

#[test]
fn typeless_quoted_requisite_emits_head_family_carry_relation() {
    let paras = vec![CLICHE.to_string()];
    let linked = npa_link::build_linked_document(&paras);
    let carries: Vec<_> = linked
        .relations
        .iter()
        .filter(|relation| relation.kind == LinkedRelationKind::HeadFamilyCarry)
        .collect();
    assert_eq!(carries.len(), 1, "{:?}", linked.relations);
    let relation = carries[0];
    assert_eq!(
        relation.evidence.len(),
        2,
        "the carry carries two separate source-local anchors"
    );
    assert_ne!(
        relation.evidence[0], relation.evidence[1],
        "the issuer phrase and the requisite are distinct anchors"
    );
    for span in &relation.evidence {
        npa_anchor::check_span(&paras[span.block], *span)
            .unwrap_or_else(|e| panic!("invalid carry anchor {span:?}: {e:?}"));
    }
    assert!(relation.from_id < linked.members.len());
    assert!(relation.to_id < linked.members.len());
    assert_eq!(
        linked.members[relation.to_id].type_name, "",
        "the quoted requisite stays typeless; the family is carried, not written"
    );
}

#[test]
fn carry_without_a_typeless_target_emits_no_relation() {
    // The same cliché, but a preceding citation in the same block makes the
    // quoted requisite carry a locally written TYPE; the carry must not
    // override it.
    let paras = vec![
        "Федеральный закон от 01.01.2020 N 1-ФЗ; в соответствии с правовой позицией Конституционного Суда Российской Федерации, изложенной в Постановлении от 23.12.2019 N 44-П, суды должны учитывать".to_string(),
    ];
    let linked = npa_link::build_linked_document(&paras);
    let typed_target = linked
        .members
        .iter()
        .any(|member| member.date == "23.12.2019" && !member.type_name.is_empty());
    assert!(
        typed_target,
        "the negative case needs a locally typed target: {:?}",
        linked.members
    );
    assert!(
        !linked
            .relations
            .iter()
            .any(|relation| relation.kind == LinkedRelationKind::HeadFamilyCarry),
        "a locally written TYPE must not be overridden by a carry: {:?}",
        linked.relations
    );
}

#[test]
fn diagnostics_gap_emission_is_deterministic() {
    for paras in [
        vec![
            "Федерального закона от 01.01.2020 N 1-ФЗ,".to_string(),
            "от 02.02.2021 N 2-ФЗ".to_string(),
        ],
        vec![CLICHE.to_string()],
    ] {
        let first = npa_link::build_linked_document(&paras);
        let second = npa_link::build_linked_document(&paras);
        assert_eq!(first, second, "replay must be structurally stable");
    }
}
