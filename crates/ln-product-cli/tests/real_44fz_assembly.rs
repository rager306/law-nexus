//! Real-corpus 44-FZ assembly E2E (M169 S02 T02).
//!
//! Full assembly FSM on the tracked consru_export edition-0118:
//! decode → extract → bind (registry) → propose → admit → commit → fold →
//! oracle diff. Skip-capable when the export is absent.
//!
//! Bounded non-claim: one consolidated edition proves the pipeline mechanics
//! on real corpus bytes, not corpus completeness or legal correctness.

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};
use ln_kb_ontology::domain::{
    admit_membership_proposals, assemble_with_oracle_diff, marker_from_decode_token,
    propose_membership_from_markers,
};
use ln_kb_ontology::registry::{
    load_edition_day_for_path, load_expression_id_for_path, load_hierarchy_map_for_path,
};

fn edition_path() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz")
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    p.exists().then_some(p)
}

#[test]
fn real_44fz_edition_0118_full_assembly_zero_drift() {
    let Some(path) = edition_path() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path_str = path.to_string_lossy().to_string();
    let bytes = std::fs::read(&path).expect("read edition-0118");

    // S_decode
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m169-44fz-assembly").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("edition-0118 must decode");

    // S_extract → S_bind prep: decode tokens → HierarchyMarker
    let mut markers = Vec::new();
    for block in &blocks {
        if let Some(node) = extract_hierarchy(block) {
            if let Ok(marker) =
                marker_from_decode_token(None, node.level().as_str(), node.number(), node.title())
            {
                markers.push(marker);
            }
        }
    }
    assert!(
        markers.len() > 1500,
        "expected the full marker set, got {}",
        markers.len()
    );

    // S_identify: real minted expression (filename grounding, S01)
    let expression_id = load_expression_id_for_path(&path_str)
        .expect("edition-0118 must mint a real expression id");
    assert!(
        expression_id.contains("44-fz") && expression_id.contains("2025-12-28"),
        "real per-edition expression expected: {expression_id}"
    );

    // S_bind: registry map for the real corpus path
    let map = load_hierarchy_map_for_path(&path_str).expect("registry map");
    let binding_count = ln_kb_ontology::registry::embedded_binding_count_for_path(&path_str)
        .expect("binding count");
    assert_eq!(
        binding_count, 102,
        "44-FZ corpus bindings (8 glava + 94 statya)"
    );

    // S_propose → S_admit
    let propose = propose_membership_from_markers(&map, &markers).expect("propose");
    assert_eq!(propose.proposals.len(), 94, "94 statya attach drafts");
    let admit = admit_membership_proposals(&propose.proposals);
    assert_eq!(admit.admitted.len(), 94, "no conflicts expected on 44-FZ");

    // S_commit → S_fold → S_verify with real provenance
    let effect_day = load_edition_day_for_path(&path_str).expect("per-edition effect day");
    let report = assemble_with_oracle_diff(&admit, &map, effect_day, &expression_id)
        .expect("assembly with oracle diff");

    assert_eq!(report.root_count, 8, "8 glava roots");
    assert_eq!(report.node_count, 102, "8 glava + 94 statya nodes");
    assert_eq!(report.committed, 94, "94 attach events committed");
    assert_eq!(report.drift, 0, "zero oracle drift");
    assert_eq!(report.missing, 0, "no missing CCs");
    assert_eq!(report.phantom, 0, "no phantom CCs");

    eprintln!(
        "44-FZ edition-0118: blocks={} markers={} bindings={} roots={} nodes={} drift={}",
        blocks.len(),
        markers.len(),
        binding_count,
        report.root_count,
        report.node_count,
        report.drift
    );
}
