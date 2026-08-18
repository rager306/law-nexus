//! parsed_as binding: `Work ──(parsed_as)──▶ DocumentGroupRef{group, catalog_version}`.
//!
//! (M171 S04 T01) The binding is a pure write-set projection (no I/O). The
//! catalog version is the hash of the `document_groups:` YAML section (FNV-1a
//! 64, `fnv1a64-<16 hex>`) so downstream process checks (Governor, T02) can
//! detect catalog drift: a binding minted against an older catalog is a
//! visible warning, never a silent skip.
//!
//! Hostile contract (review R8-10): the binding never writes ForceStatusEvent,
//! never mints ApplicableDecision-class nodes, and never claims applicability.
//! DocumentProfileAsAuthority-class kinds are forbidden vocabulary; the
//! vocabulary itself stays in the YAML catalog and never transfers to the
//! graph — only the binding (group + catalog version) does.

use ln_identity::domain::{mint_work, FrbrWork};
use ln_kb_ontology::catalog::OntologyCatalog;
use ln_kb_ontology::domain::{
    project_document_group_binding, reject_forbidden_kind, GraphEdge, WriteSet, WriteSetError,
};

fn work() -> FrbrWork {
    mint_work("federal", "2013-04-05", "44-fz").expect("mint work")
}

fn current_version() -> String {
    ln_kb_ontology::catalog::document_groups_version()
}

fn ref_node_id(set: &WriteSet) -> &str {
    set.nodes
        .iter()
        .find(|n| n.kind == "DocumentGroupRef")
        .expect("DocumentGroupRef node")
        .id
        .as_str()
}

fn parsed_as_edge(set: &WriteSet) -> &GraphEdge {
    set.edges
        .iter()
        .find(|e| e.kind == "parsed_as")
        .expect("parsed_as edge")
}

// ─── hostile: DocumentProfileAsAuthority class is forbidden vocabulary ─────

#[test]
fn document_profile_as_authority_class_is_forbidden() {
    for kind in [
        "DocumentProfileAsAuthority",
        "ProfileBindingAsForce",
        "DocumentProfileAsClock",
    ] {
        let err = reject_forbidden_kind(kind).expect_err(kind);
        assert!(matches!(err, WriteSetError::ForbiddenKind(_)), "{kind}");
        let err = WriteSet::empty().try_push_node(kind, "x").expect_err(kind);
        assert!(matches!(err, WriteSetError::ForbiddenKind(_)), "{kind}");
    }
}

#[test]
fn binding_never_writes_force_or_applicable_nodes() {
    let w = work();
    let set =
        project_document_group_binding(&w, "federal_law@v1", &current_version()).expect("binding");
    assert!(
        !set.nodes.iter().any(|n| n.kind == "ForceStatusEvent"),
        "parsed_as must not write force"
    );
    assert!(
        !set.nodes.iter().any(|n| n.kind == "ApplicableDecision"),
        "parsed_as must not mint ApplicableDecision-class nodes"
    );
    assert!(
        !set.nodes
            .iter()
            .any(|n| n.kind == "DocumentProfileAsAuthority" || n.kind == "ProfileBindingAsForce"),
        "parsed_as must not mint profile-authority nodes"
    );
    assert!(
        !set.claims_applicability,
        "binding must not claim applicability"
    );
}

#[test]
fn binding_cannot_be_reprojected_as_authority() {
    let w = work();
    let mut set =
        project_document_group_binding(&w, "federal_law@v1", &current_version()).expect("binding");
    let err = set
        .try_push_node("DocumentProfileAsAuthority", "profile:as:law")
        .expect_err("hostile push of a profile-authority kind must fail closed");
    assert!(matches!(err, WriteSetError::ForbiddenKind(_)));
}

// ─── positive: parsed_as edge carries group + catalog version ──────────────

#[test]
fn binding_emits_parsed_as_edge_with_catalog_version() {
    let w = work();
    let version = current_version();
    let set = project_document_group_binding(&w, "federal_law@v1", &version).expect("binding");
    assert!(
        set.nodes.iter().any(|n| n.kind == "Work"),
        "binding must reference the Work node"
    );
    let ref_id = ref_node_id(&set);
    assert!(
        ref_id.starts_with("docgroupref:federal_law@v1:"),
        "ref id must embed the group: {ref_id}"
    );
    assert!(
        ref_id.ends_with(&version),
        "ref id must carry the catalog version: {ref_id}"
    );
    let edge = parsed_as_edge(&set);
    assert_eq!(edge.from_id, w.work_id.as_str(), "parsed_as from Work");
    assert_eq!(edge.to_id, ref_id, "parsed_as to DocumentGroupRef");
}

#[test]
fn ref_id_embeds_group_and_version_separately() {
    let version = current_version();
    let set = project_document_group_binding(&work(), "federal_law@v1", &version).expect("binding");
    let (group, carried) = ref_node_id(&set)
        .strip_prefix("docgroupref:")
        .and_then(|rest| rest.rsplit_once(':'))
        .expect("ref id format docgroupref:<group>:<version>");
    assert_eq!(group, "federal_law@v1");
    assert_eq!(carried, version);
}

#[test]
fn every_embedded_group_binds() {
    let catalog = OntologyCatalog::embedded().expect("yaml");
    let w = work();
    let version = current_version();
    for group in &catalog.document_groups {
        let set = project_document_group_binding(&w, &group.id, &version)
            .unwrap_or_else(|e| panic!("group {} failed to bind: {e}", group.id));
        assert!(
            set.edges.iter().any(|e| e.kind == "parsed_as"),
            "group {} must bind via parsed_as",
            group.id
        );
    }
}

#[test]
fn binding_is_pure_system_observation_projection() {
    let w = work();
    let set =
        project_document_group_binding(&w, "federal_law@v1", &current_version()).expect("binding");
    assert!(!set.performs_io, "pure projection, no I/O");
    assert!(
        set.non_claims
            .iter()
            .any(|c| c.contains("system_observation")),
        "binding must be framed as a system_observation heuristic"
    );
}

// ─── catalog version: deterministic FNV-1a 64 hash of the section ──────────

#[test]
fn catalog_version_is_deterministic_fnv1a64() {
    let v1 = ln_kb_ontology::catalog::document_groups_version();
    let v2 = ln_kb_ontology::catalog::document_groups_version();
    assert_eq!(v1, v2, "version must be deterministic");
    assert!(
        v1.starts_with("fnv1a64-"),
        "unexpected version format: {v1}"
    );
    assert_eq!(v1.len(), "fnv1a64-".len() + 16, "16 lowercase hex digits");
    assert!(v1["fnv1a64-".len()..]
        .chars()
        .all(|c| c.is_ascii_hexdigit()));
}

#[test]
fn section_hash_is_sensitive_to_section_edits() {
    let base = fixture_yaml();
    assert_eq!(
        ln_kb_ontology::catalog::document_groups_section_hash(&base),
        ln_kb_ontology::catalog::document_groups_section_hash(&base),
        "hash must be deterministic"
    );
    let changed = base.replace("needle: federalnyi-zakon", "needle: federalnyi-zakon-2");
    assert_ne!(
        ln_kb_ontology::catalog::document_groups_section_hash(&base),
        ln_kb_ontology::catalog::document_groups_section_hash(&changed),
        "any section edit must change the hash"
    );
    let without = base.replace("\ndocument_groups:", "");
    assert_eq!(
        ln_kb_ontology::catalog::document_groups_section_hash(&without),
        "",
        "absent section yields an empty version (fail-closed)"
    );
}

// ─── negative tests (Q7) ───────────────────────────────────────────────────

#[test]
fn binding_rejects_unknown_group() {
    let err = project_document_group_binding(&work(), "no-such-group", &current_version())
        .expect_err("unknown group must fail closed");
    assert!(matches!(err, WriteSetError::UnknownDocumentGroup));
}

#[test]
fn binding_rejects_empty_catalog_version() {
    let err = project_document_group_binding(&work(), "federal_law@v1", "  ")
        .expect_err("empty version must fail closed");
    assert!(matches!(err, WriteSetError::MissingIdentity));
}

#[test]
fn binding_rejects_empty_group() {
    let err = project_document_group_binding(&work(), "", &current_version())
        .expect_err("empty group must fail closed");
    assert!(matches!(err, WriteSetError::MissingIdentity));
}

#[test]
fn undeclared_edge_kind_is_rejected() {
    let err = WriteSet::empty()
        .try_push_edge("parsed_as_profile", "a", "b")
        .expect_err("undeclared edge kind must fail closed");
    assert!(matches!(err, WriteSetError::UnknownEdgeKind));
}

// ─── vocabulary + non-claims are declared in the YAML catalog ──────────────

#[test]
fn vocabulary_is_catalog_declared() {
    let catalog = OntologyCatalog::embedded().expect("yaml");
    assert!(catalog.is_node_kind("DocumentGroupRef"));
    assert!(catalog.is_edge_kind("parsed_as"));
    assert!(catalog.is_forbidden_kind("DocumentProfileAsAuthority"));
    assert!(catalog.is_forbidden_kind("ProfileBindingAsForce"));
    assert!(catalog.is_forbidden_kind("DocumentProfileAsClock"));
}

#[test]
fn yaml_non_claims_frame_binding_heuristic() {
    let catalog = OntologyCatalog::embedded().expect("yaml");
    let joined = catalog.document_group_non_claims.join("\n");
    assert!(
        joined.contains("system_observation"),
        "non_claims must frame the binding as a system_observation heuristic"
    );
    assert!(
        joined.contains("stays in the YAML catalog"),
        "non_claims must state the vocabulary stays in YAML; only the binding transfers"
    );
}

// ─── fixture: minimal YAML with a document_groups section ──────────────────

fn fixture_yaml() -> String {
    r#"schema_version: test/v1
fsm:
  current: O0
  states:
    O0:
  transitions:
    - {from: O0, to: O0, when: x}
vocabulary:
  hierarchy_levels:
    - statya
  node_kinds:
    - Work
  edge_kinds:
    - expression_of
  forbidden_node_kinds:
    - ApplicableDecision
  presence_change_kinds:
    - include
  membership_change_kinds:
    - attach
  industrial_op_kinds:
    - split
  force_status_values:
    - unknown
  decode_level_aliases:
    Statya: statya
document_groups:
  structural_roles:
    - unit
  groups:
    - id: federal_law@v1
      needles:
        - {field: path, needle: federalnyi-zakon, rank: 10}
      ladder:
        - {token: statya, role: unit}
"#
    .to_owned()
}
