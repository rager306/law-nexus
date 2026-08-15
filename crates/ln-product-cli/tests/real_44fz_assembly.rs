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
    propose_membership_from_markers, HierarchyBinding, HierarchyMarker,
};
use ln_kb_ontology::domain::{diff_marker_sets, drafts_from_marker_diff, AmendmentDraftOp};
use ln_kb_ontology::registry::{
    load_edition_day_for_path, load_expression_id_for_path, load_hierarchy_map_for_path,
};
use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    fold_membership_at, AmendingActId, ComponentConceptId, MembershipChangeKind,
    VersionedMembershipEvent, VersionedMembershipLog,
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

#[test]
fn real_44fz_edition_0001_to_0002_replay_drafts() {
    let Some(dir) = edition_path().and_then(|p| p.parent().map(|d| d.to_owned())) else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let read_markers = |file: &str| -> Vec<ln_kb_ontology::domain::HierarchyMarker> {
        let bytes = std::fs::read(dir.join(file)).expect("read edition");
        let request = DecodeRequest::new(
            PayloadRef::parse("payload:m169-replay").unwrap(),
            FamilyFormat::parse("family:consultant-wordml").unwrap(),
            &bytes,
        );
        let blocks = ConsultantWordMlBlockDecoder
            .decode_blocks(&request)
            .expect("decode");
        let mut markers = Vec::new();
        for block in &blocks {
            if let Some(node) = extract_hierarchy(block) {
                if let Ok(m) = marker_from_decode_token(
                    None,
                    node.level().as_str(),
                    node.number(),
                    node.title(),
                ) {
                    markers.push(m);
                }
            }
        }
        markers
    };
    let seed = read_markers("edition-0001_rev-initial_from-unknown_19d3c051.xml");
    let next = read_markers("edition-0002_rev-2013-07-02_from-unknown_f4bfa020.xml");
    eprintln!("seed markers={} next markers={}", seed.len(), next.len());
    let prov = load_expression_id_for_path(
        &dir.join("edition-0002_rev-2013-07-02_from-unknown_f4bfa020.xml")
            .to_string_lossy(),
    )
    .expect("edition-0002 expression");
    let drafts =
        ln_kb_ontology::domain::drafts_from_marker_diff(&seed, &next, &prov).expect("drafts");
    eprintln!(
        "drafts={} attach={} detach={}",
        drafts.len(),
        drafts
            .iter()
            .filter(|d| d.op == ln_kb_ontology::domain::AmendmentDraftOp::Attach)
            .count(),
        drafts
            .iter()
            .filter(|d| d.op == ln_kb_ontology::domain::AmendmentDraftOp::Detach)
            .count()
    );
    assert!(!seed.is_empty() && !next.is_empty());

    // Honest bounded finding: the 2013-07-02 revision changed article TEXT,
    // not structure — the marker-level diff is empty. Text-facet amendments
    // (CTV wording) are out of scope for the structural replay bridge.
    assert!(
        drafts.is_empty(),
        "0001->0002 must be text-only at marker level, got {drafts:?}"
    );
}

fn read_markers(dir: &std::path::Path, file: &str) -> Vec<HierarchyMarker> {
    let bytes = std::fs::read(dir.join(file)).expect("read edition");
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m169-replay").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("decode");
    let mut markers = Vec::new();
    for block in &blocks {
        if let Some(node) = extract_hierarchy(block) {
            if let Ok(m) =
                marker_from_decode_token(None, node.level().as_str(), node.number(), node.title())
            {
                markers.push(m);
            }
        }
    }
    markers
}

// T02: first structural replay on the real 44-FZ corpus.
// Pair edition-0080 (2021-12-30) -> edition-0081 (in force 2022-01-01,
// Federal Law 476-FZ): the "paper" procedures (statya 53-59, 63-69, 78-92)
// are removed. The registry only knows the edition-0118 snapshot, so the
// removed articles are re-bound locally as a historical layer; this is a
// fixture decision for the replay test, not a registry change.
#[test]
fn real_44fz_edition_0080_to_0081_replay_chain() {
    let Some(dir) = edition_path().and_then(|p| p.parent().map(|d| d.to_owned())) else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let seed_file = "edition-0080_rev-2021-12-30_from-unknown_6f39db7c.xml";
    let target_file = "edition-0081_rev-2021-12-30_from-2022-01-01_fd3945d5.xml";
    let seed_path = dir.join(seed_file);
    let target_path = dir.join(target_file);
    if !seed_path.exists() || !target_path.exists() {
        eprintln!("SKIP: editions 0080/0081 not present");
        return;
    }
    let seed_markers = read_markers(&dir, seed_file);
    let target_markers = read_markers(&dir, target_file);
    assert!(seed_markers.len() > 1500);
    assert!(target_markers.len() > 1500);

    // Diff markers -> drafts (the S03 bridge under test).
    let prov_seed =
        load_expression_id_for_path(&seed_path.to_string_lossy()).expect("seed expression");
    let prov_target =
        load_expression_id_for_path(&target_path.to_string_lossy()).expect("target expression");
    let drafts =
        drafts_from_marker_diff(&seed_markers, &target_markers, &prov_target).expect("drafts");
    let attach_drafts = drafts
        .iter()
        .filter(|d| d.op == AmendmentDraftOp::Attach)
        .count();
    let detach_drafts = drafts
        .iter()
        .filter(|d| d.op == AmendmentDraftOp::Detach)
        .count();
    eprintln!(
        "0080->0081 marker diff: added={} removed={} drafts={} attach={} detach={}",
        attach_drafts,
        detach_drafts,
        drafts.len(),
        attach_drafts,
        detach_drafts
    );
    assert!(detach_drafts > 0, "476-FZ must remove paper procedures");

    // Historical layer: re-bind statya removed before edition-0118 so the
    // seed (0080) can attach them and the replay can detach them.
    let mut map = load_hierarchy_map_for_path(&seed_path.to_string_lossy()).expect("registry");
    let diff = diff_marker_sets(&seed_markers, &target_markers);
    for m in diff.removed.iter().chain(diff.added.iter()) {
        if m.level() != "statya" {
            continue;
        }
        let cc = ComponentConceptId::parse(&format!("cc:44-fz:statya-{}", m.number()))
            .expect("cc parse");
        map.register(HierarchyBinding::try_new(None, m.level(), m.number(), cc).expect("binding"))
            .expect("register");
    }

    // Seed commit: fold edition-0080 structure into the log at its day.
    // rev-дата обеих редакций 2021-12-30 (476-ФЗ подписан 30.12.2021), но
    // структурное изменение вступает в силу 01.01.2022 (from-дата 0081).
    // target_day берём из from-даты целевой редакции (filename grounding).
    let seed_day = load_edition_day_for_path(&seed_path.to_string_lossy()).expect("seed day");
    let target_day = legal_act_effect_day_to_ordinal("2022-01-01").expect("target day");
    assert!(target_day > seed_day);
    let seed_propose = propose_membership_from_markers(&map, &seed_markers).expect("propose");
    let seed_admit = admit_membership_proposals(&seed_propose.proposals);
    assert!(!seed_admit.admitted.is_empty());
    let seed_prov = AmendingActId::parse(&prov_seed).expect("seed prov");
    let mut log = VersionedMembershipLog::empty();
    for edge in &seed_admit.admitted {
        log.append(
            VersionedMembershipEvent::try_new(
                MembershipChangeKind::Attach,
                edge.parent.clone(),
                edge.child.clone(),
                seed_day,
                seed_prov.clone(),
            )
            .expect("seed event"),
        )
        .expect("append");
    }
    let target_prov = AmendingActId::parse(&prov_target).expect("target prov");

    // Apply drafts: Attach for added statya, Detach for removed statya.
    let mut committed_attach = 0usize;
    let mut committed_detach = 0usize;
    let mut quarantined = 0usize;
    for draft in &drafts {
        let probe = HierarchyMarker::try_new(None, &draft.level, &draft.number, None)
            .expect("draft marker");
        let bound = ln_kb_ontology::domain::map_hierarchy_marker(&map, &probe);
        let ln_kb_ontology::domain::HierarchyMapOutcome::Bound { component } = bound else {
            quarantined += 1;
            continue;
        };
        // Parent comes from the structural proposal of the target snapshot
        // (attach) or the seed snapshot (detach).
        let parent = match draft.op {
            AmendmentDraftOp::Attach => {
                let t = propose_membership_from_markers(&map, &target_markers).expect("t");
                t.proposals
                    .iter()
                    .find(|p| p.child.as_str() == component.as_str())
                    .map(|p| p.parent.clone())
            }
            AmendmentDraftOp::Detach => seed_admit
                .admitted
                .iter()
                .find(|e| e.child.as_str() == component.as_str())
                .map(|e| e.parent.clone()),
        };
        let Some(parent) = parent else {
            quarantined += 1;
            continue;
        };
        let kind = match draft.op {
            AmendmentDraftOp::Attach => MembershipChangeKind::Attach,
            AmendmentDraftOp::Detach => MembershipChangeKind::Detach,
        };
        log.append(
            VersionedMembershipEvent::try_new(
                kind,
                parent,
                component,
                target_day,
                target_prov.clone(),
            )
            .expect("draft event"),
        )
        .expect("append");
        match draft.op {
            AmendmentDraftOp::Attach => committed_attach += 1,
            AmendmentDraftOp::Detach => committed_detach += 1,
        }
    }
    eprintln!(
        "replay applied: attach={} detach={} quarantined={}",
        committed_attach, committed_detach, quarantined
    );

    // Fold at the target edition date and compare with a direct snapshot
    // assembly of edition-0081 (same map, same day): controlled drift.
    let replay_ast = fold_membership_at(&log, target_day).expect("replay fold");
    let target_propose = propose_membership_from_markers(&map, &target_markers).expect("propose");
    let target_admit = admit_membership_proposals(&target_propose.proposals);
    let mut oracle_log = VersionedMembershipLog::empty();
    for edge in &target_admit.admitted {
        oracle_log
            .append(
                VersionedMembershipEvent::try_new(
                    MembershipChangeKind::Attach,
                    edge.parent.clone(),
                    edge.child.clone(),
                    target_day,
                    target_prov.clone(),
                )
                .expect("oracle event"),
            )
            .expect("append");
    }
    let oracle_ast = fold_membership_at(&oracle_log, target_day).expect("oracle fold");
    let oracle_ccs: Vec<ComponentConceptId> =
        oracle_ast.roots().iter().flat_map(collect_ccs).collect();
    let drift = ln_kb_ontology::domain::oracle_diff(&replay_ast, &oracle_ccs);
    eprintln!(
        "replay drift: expected={} actual={} missing={} phantom={} drift={}",
        drift.expected, drift.actual, drift.missing, drift.phantom, drift.drift
    );
    assert_eq!(
        drift.drift, 0,
        "seed+diff chain must reproduce edition-0081 snapshot"
    );
}

fn collect_ccs(node: &ln_temporal::domain::StructuralAstNode) -> Vec<ComponentConceptId> {
    let mut result = vec![node.component().clone()];
    for child in node.children() {
        result.extend(collect_ccs(child));
    }
    result
}
