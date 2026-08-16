use std::env;
use std::fs;
use std::process;
use std::time::Instant;

use ln_decode::{
    adapters::{
        garant_odt::GarantOdtBlockDecoder, garant_odt_package::read_odt_content_xml,
        ConsultantWordMlBlockDecoder,
    },
    deontic::extract_deontic_lexemes,
    domain::{
        fingerprint_bytes, DecodeRequest, FamilyFormat, HierarchyNode, ParagraphStyle, PayloadRef,
    },
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
    references::extract_reference_mentions,
    temporal::extract_temporal_phrases,
    unknown_forms::census_unknown_forms,
};
use ln_kb_ontology::domain::{
    admit_membership_proposals, assemble_with_oracle_diff, build_text_log_from_markers,
    diff_marker_sets, drafts_from_marker_diff, map_hierarchy_marker, marker_from_decode_token,
    propose_membership_from_markers, AmendmentDraftOp, HierarchyMap, HierarchyMapOutcome,
    HierarchyMarker, WriteSetError,
};
use ln_kb_ontology::registry::{
    load_edition_day_for_path, load_expression_id_for_path, load_hierarchy_map_for_path,
};
use ln_query::knowql::{execute, KnowQLOp, KnowQLResult, ValidatedOp};
use ln_storage::{
    adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore},
    EmbeddingPort, EmbeddingRequest, EmbeddingResponse, GraphNode, GraphStorePort, StorageError,
    VectorRecord, VectorStorePort,
};
use ln_temporal::domain::{
    fold_membership_at, AmendingActId, ComponentConceptId, MembershipChangeKind,
    VersionedMembershipEvent, VersionedMembershipLog,
};

const BINARY: &str = "law-nexus-inspect";

/// Composition adapter: decode HierarchyNode → YAML catalog token → registry map.
/// Empty registry is Unknown. Number+level never mints a ComponentConcept.
fn lift_extracted_hierarchy(
    node: &HierarchyNode,
    map: &HierarchyMap,
) -> Result<HierarchyMapOutcome, WriteSetError> {
    let marker =
        marker_from_decode_token(None, node.level().as_str(), node.number(), node.title())?;
    Ok(map_hierarchy_marker(map, &marker))
}

struct StubEmbedding;
impl EmbeddingPort for StubEmbedding {
    fn embed(&self, req: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        Ok(EmbeddingResponse::try_new(
            req.model_id(),
            deterministic_vector(req.text(), req.expected_dimensions()),
        )
        .unwrap_or_else(|_| {
            EmbeddingResponse::try_new(req.model_id(), vec![0.0; req.expected_dimensions()])
                .unwrap()
        }))
    }
}

/// Derive a deterministic f32 vector from `text`. Same text + dims -> identical
/// vector; different text -> different vector; deterministic across runs.
///
/// Bounded, NOT semantic: this is a DefaultHasher-seeded pseudo-random mapping
/// used only so the CLI retrieval pipeline exercises real ranking over
/// distinct document vectors instead of a hardcoded constant. Real semantic
/// embedding requires TEI infrastructure (not available). Lifecycle [bounded].
fn deterministic_vector(text: &str, dims: usize) -> Vec<f32> {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut out = Vec::with_capacity(dims);
    for index in 0..dims {
        let mut hasher = DefaultHasher::new();
        text.hash(&mut hasher);
        index.hash(&mut hasher);
        // Map the 64-bit hash to a deterministic f32 in [0.0, 1.0).
        let bits = hasher.finish();
        let scaled = (bits % 1_000_003) as f32 / 1_000_003.0_f32;
        out.push(scaled);
    }
    out
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn print_failure(phase: &str, kind: &str, message: &str, start: std::time::Instant) -> ! {
    let duration_ms = start.elapsed().as_millis();
    let fp = fingerprint_bytes(message.as_bytes());
    println!(
        "{{\"phase\":\"{phase}\",\"status\":\"failed\",\"kind\":\"{kind}\",\"message\":\"{}\",\"attempt_count\":1,\"fingerprint\":\"{fp}\",\"duration_ms\":{duration_ms}}}",
        json_escape(message)
    );
    process::exit(1);
}

fn print_health() {
    println!(
        "{{\"phase\":\"Health\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\"duration_ms\":0}}"
    );
}

fn inspect(path: &str) {
    let start = Instant::now();

    let bytes = match fs::read(path) {
        Ok(b) => b,
        Err(e) => print_failure("Io", "ReadFailure", &e.to_string(), start),
    };
    let byte_count = bytes.len();
    let fingerprint = fingerprint_bytes(&bytes);

    let family = if path.to_lowercase().ends_with(".xml") {
        FamilyFormat::parse("family:consultant-wordml").unwrap()
    } else if path.to_lowercase().ends_with(".odt") {
        FamilyFormat::parse("family:garant-odt").unwrap()
    } else {
        print_failure("Parse", "UnsupportedFamily", path, start);
    };
    let fid = family.as_str().to_owned();

    let payload = PayloadRef::parse("payload:law-nexus-inspect").unwrap();
    let request = DecodeRequest::new(payload, family, &bytes);

    let blocks = if fid.as_str() == "family:consultant-wordml" {
        ConsultantWordMlBlockDecoder
            .decode_blocks(&request)
            .unwrap_or_else(|e| {
                print_failure(
                    "Parse",
                    "MalformedInput",
                    &format!("{:?}: offset={:?}", e.kind(), e.byte_offset()),
                    start,
                )
            })
    } else {
        read_odt_content_xml(&request).unwrap_or_else(|e| {
            print_failure("Parse", "MalformedInput", &format!("ODT: {e}"), start)
        });
        GarantOdtBlockDecoder
            .decode_blocks(&request)
            .unwrap_or_else(|e| {
                print_failure(
                    "Parse",
                    "MalformedInput",
                    &format!("{:?}: offset={:?}", e.kind(), e.byte_offset()),
                    start,
                )
            })
    };

    let mut hierarchy_markers = 0usize;
    let mut hierarchy_lifts_unknown = 0usize;
    let mut hierarchy_lifts_bound = 0usize;
    let mut hierarchy_lifts_rejected = 0usize;
    let hierarchy_map = load_hierarchy_map_for_path(path).unwrap_or_else(|_| HierarchyMap::empty());
    let mut hierarchy_markers_seq: Vec<HierarchyMarker> = Vec::new();
    let mut reference_mentions = 0usize;
    let mut temporal_phrases = 0usize;
    let mut deontic_lexemes = 0usize;
    let mut unknown_forms = 0usize;
    let mut provider_comments = 0usize;

    let mut vector_store = InMemoryVectorStore::new();
    let mut graph_store = InMemoryGraphStore::new();

    for (i, block) in blocks.iter().enumerate() {
        if block.style() == ParagraphStyle::ProviderComment {
            provider_comments += 1;
            continue;
        }
        if let Some(node) = extract_hierarchy(block) {
            hierarchy_markers += 1;
            match lift_extracted_hierarchy(&node, &hierarchy_map) {
                Ok(HierarchyMapOutcome::Unknown) => hierarchy_lifts_unknown += 1,
                Ok(HierarchyMapOutcome::Bound { .. }) => hierarchy_lifts_bound += 1,
                Err(_) => hierarchy_lifts_rejected += 1,
            }
            if let Ok(marker) =
                marker_from_decode_token(None, node.level().as_str(), node.number(), node.title())
            {
                hierarchy_markers_seq.push(marker);
            }
            let id = format!("block-{i}");
            // Deterministic, content-derived vector (bounded, not semantic)
            // replaces the prior hardcoded vec![0.5; 4] (M163).
            let _ = vector_store.store(
                &VectorRecord::try_new(&id, deterministic_vector(block.text(), 4), Vec::new())
                    .unwrap(),
            );
            let _ =
                graph_store.upsert_node(&GraphNode::try_new(&id, "hierarchy", Vec::new()).unwrap());
        }
        reference_mentions += extract_reference_mentions(block).len();
        temporal_phrases += extract_temporal_phrases(block).len();
        deontic_lexemes += extract_deontic_lexemes(block).len();
        let c = census_unknown_forms(block);
        unknown_forms +=
            c.temporal_unsupported() + c.deontic_unsupported() + c.hierarchy_prefix_unsupported();
    }

    let op = ValidatedOp::try_new(KnowQLOp::FindSimilar {
        // Deterministic query vector derived from a representative inspector
        // query (bounded, not semantic) replaces the prior hardcoded
        // vec![0.5; 4] (M163).
        vector: deterministic_vector("law-nexus-inspect:find-similar-hierarchy", 4),
        top_k: 5,
    })
    .unwrap();
    let retrieval_count = match execute(&op, &StubEmbedding, &vector_store, &graph_store) {
        Ok(KnowQLResult::SimilarRecords { ids }) => ids.len(),
        _ => 0,
    };

    let propose = propose_membership_from_markers(&hierarchy_map, &hierarchy_markers_seq)
        .unwrap_or_else(|_| ln_kb_ontology::domain::MembershipProposeReport {
            proposals: Vec::new(),
            quarantined: hierarchy_markers_seq.len(),
            forest_roots: 0,
        });
    let membership_proposals = propose.proposals.len();
    let membership_quarantined = propose.quarantined;
    let membership_forest_roots = propose.forest_roots;

    let admit = admit_membership_proposals(&propose.proposals);
    let membership_admitted = admit.admitted.len();
    let membership_conflict_quarantined = admit.quarantined.len();

    // S_identify → S_commit → S_fold → S_verify: mint identity, commit, fold, diff.
    let expression_id = load_expression_id_for_path(path);
    let provenance = expression_id
        .as_deref()
        .unwrap_or("amendingact:c2-oracle-edition");
    let (
        membership_committed,
        ast_root_count,
        ast_node_count,
        oracle_drift,
        oracle_missing,
        oracle_phantom,
    ) = if let Some(effect_day) = load_edition_day_for_path(path) {
        match assemble_with_oracle_diff(&admit, &hierarchy_map, effect_day, provenance) {
            Ok(r) => (
                r.committed,
                r.root_count,
                r.node_count,
                r.drift,
                r.missing,
                r.phantom,
            ),
            Err(_) => (0, 0, 0, 0, 0, 0),
        }
    } else {
        (0, 0, 0, 0, 0, 0)
    };

    // S_verify text CTV: build TextVersionLog from marker titles, count resolved.
    let ctv_resolved = if let Some(effect_day) = load_edition_day_for_path(path) {
        let text_log = build_text_log_from_markers(
            &hierarchy_map,
            &hierarchy_markers_seq,
            effect_day,
            provenance,
        );
        text_log.events().len()
    } else {
        0
    };

    // Consultant parser pipeline: hyperlinks → classify → edges → observations
    let (hyperlink_count, edge_amends, edge_cites, edge_implements, obs_patterns) = {
        let links = ln_consultant_parser::extract_hyperlinks(&bytes);
        let classified = ln_consultant_parser::classify_all_scored_for_path(&links, path);
        let source_consider = expression_id
            .as_deref()
            .unwrap_or("consultantplus://offline/ref=unknown");
        let edges = ln_consultant_parser::derive_edges(&classified, source_consider);
        let obs = ln_consultant_parser::collect_observations(&classified);
        let amends = edges.iter().filter(|e| e.kind == "amends").count();
        let cites = edges.iter().filter(|e| e.kind == "cites").count();
        let implements = edges.iter().filter(|e| e.kind == "implements").count();
        (links.len(), amends, cites, implements, obs.len())
    };

    let duration_ms = start.elapsed().as_millis();
    let expression_id_str = json_escape(&expression_id.clone().unwrap_or_default());

    println!(
        "{{\"phase\":\"Inspect\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\
         \"duration_ms\":{duration_ms},\
         \"source\":{{\"path\":\"{}\",\"bytes\":{byte_count},\"fingerprint\":\"{fingerprint}\"}},\
         \"family\":\"{fid}\",\
         \"result\":{{\
         \"blocks\":{},\"hierarchy_markers\":{hierarchy_markers},\
         \"hierarchy_lifts_unknown\":{hierarchy_lifts_unknown},\
         \"hierarchy_lifts_bound\":{hierarchy_lifts_bound},\
         \"hierarchy_lifts_rejected\":{hierarchy_lifts_rejected},\
         \"membership_proposals\":{membership_proposals},\
         \"membership_quarantined\":{membership_quarantined},\
         \"membership_forest_roots\":{membership_forest_roots},\
         \"membership_admitted\":{membership_admitted},\
         \"membership_conflict_quarantined\":{membership_conflict_quarantined},\
         \"membership_committed\":{membership_committed},\
         \"ast_root_count\":{ast_root_count},\
         \"ast_node_count\":{ast_node_count},\
         \"oracle_drift\":{oracle_drift},\
         \"oracle_missing\":{oracle_missing},\
         \"oracle_phantom\":{oracle_phantom},\
         \"ctv_resolved\":{ctv_resolved},\
         \"expression_id\":\"{expression_id_str}\",\
         \"reference_mentions\":{reference_mentions},\
         \"temporal_phrases\":{temporal_phrases},\"deontic_lexemes\":{deontic_lexemes},\
         \"unknown_forms\":{unknown_forms},\"provider_comment_candidates\":{provider_comments},\
         \"hyperlink_count\":{hyperlink_count},\
         \"edge_amends\":{edge_amends},\
         \"edge_cites\":{edge_cites},\
         \"edge_implements\":{edge_implements},\
         \"observation_patterns\":{obs_patterns},\
         \"retrieval_count\":{retrieval_count}\
         }},\
         \"non_claims\":[\"No legal correctness claim\",\"No citation authority claim\",\
         \"No corpus completeness claim\",\"No five-clock assignment claim\",\
         \"Empty hierarchy registry yields Unknown; lift does not mint ComponentConcept\",\
         \"Membership committed events are synthetic-provenance C2 drafts; fold is structural, not legal document tree\",\
         \"retrieval_count is deterministic-non-semantic: hash-derived vectors, not TEI semantic embedding\",\
         \"ast_root_count and ast_node_count are structural AST projections, not legal hierarchy or CTV text\"]}}",
        json_escape(path),
        blocks.len(),
    );
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("health") => print_health(),
        Some("inspect") => {
            let path = args.get(1).cloned().unwrap_or_default();
            if path.is_empty() {
                eprintln!("usage: law-nexus-inspect inspect <path>");
                process::exit(2);
            }
            inspect(&path);
        }
        Some("replay") => {
            let seed = args.get(1).cloned().unwrap_or_default();
            let target = args.get(2).cloned().unwrap_or_default();
            if seed.is_empty() || target.is_empty() {
                eprintln!("usage: law-nexus-inspect replay <seed-edition> <target-edition>");
                process::exit(2);
            }
            replay(&seed, &target);
        }
        _ => {
            eprintln!("usage: law-nexus-inspect <health|inspect <path>|replay <seed> <target>>");
            process::exit(2);
        }
    }
}

/// Replay report between two editions (M169 S03 T03).
///
/// Mirrors `real_44fz_edition_0080_to_0081_replay_chain`: seed commit plus
/// diff drafts must reproduce the target snapshot (drift).
///
/// Bounded non-claim: two editions prove the replay mechanics, not corpus
/// history.
fn replay(seed_path: &str, target_path: &str) {
    let start = Instant::now();
    let read_markers = |path: &str| -> Result<(Vec<HierarchyMarker>, usize), String> {
        let bytes = fs::read(path).map_err(|e| e.to_string())?;
        let family = FamilyFormat::parse("family:consultant-wordml").map_err(|e| e.to_string())?;
        let payload = PayloadRef::parse("payload:law-nexus-replay").map_err(|e| e.to_string())?;
        let request = DecodeRequest::new(payload, family, &bytes);
        let blocks = ConsultantWordMlBlockDecoder
            .decode_blocks(&request)
            .map_err(|e| format!("{:?}: offset={:?}", e.kind(), e.byte_offset()))?;
        let block_count = blocks.len();
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
        Ok((markers, block_count))
    };
    let read_articles = |path: &str| -> Result<Vec<ln_decode::article_body::ArticleText>, String> {
        let bytes = fs::read(path).map_err(|e| e.to_string())?;
        let family = FamilyFormat::parse("family:consultant-wordml").map_err(|e| e.to_string())?;
        let payload = PayloadRef::parse("payload:law-nexus-replay").map_err(|e| e.to_string())?;
        let request = DecodeRequest::new(payload, family, &bytes);
        let blocks = ConsultantWordMlBlockDecoder
            .decode_blocks(&request)
            .map_err(|e| format!("{:?}: offset={:?}", e.kind(), e.byte_offset()))?;
        Ok(ln_decode::article_body::collect_article_texts(&blocks))
    };
    let (seed_markers, seed_blocks) = match read_markers(seed_path) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("{{\"phase\":\"Replay\",\"status\":\"error\",\"error\":\"{e}\"}}");
            process::exit(1);
        }
    };
    let (target_markers, target_blocks) = match read_markers(target_path) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("{{\"phase\":\"Replay\",\"status\":\"error\",\"error\":\"{e}\"}}");
            process::exit(1);
        }
    };

    let seed_expr = load_expression_id_for_path(seed_path).unwrap_or_default();
    let target_expr = load_expression_id_for_path(target_path).unwrap_or_default();
    let diff = diff_marker_sets(&seed_markers, &target_markers);
    let drafts =
        drafts_from_marker_diff(&seed_markers, &target_markers, &target_expr).unwrap_or_default();
    let attach = drafts
        .iter()
        .filter(|d| d.op == AmendmentDraftOp::Attach)
        .count();
    let detach = drafts
        .iter()
        .filter(|d| d.op == AmendmentDraftOp::Detach)
        .count();

    // Text facet (M170 S02 T03): full article texts compared between editions.
    let text_draft_count = (|| -> Option<usize> {
        let seed_articles = read_articles(seed_path).ok()?;
        let target_articles = read_articles(target_path).ok()?;
        let text_drafts = ln_kb_ontology::domain::changed_article_texts(
            seed_articles
                .iter()
                .map(|a| ("statya", a.number(), a.title(), a.text() as &str)),
            target_articles
                .iter()
                .map(|a| ("statya", a.number(), a.title(), a.text() as &str)),
            &target_expr,
        )
        .ok()?;
        eprintln!("text facet: drafts={} (facet=text)", text_drafts.len());
        Some(text_drafts.len())
    })()
    .unwrap_or(0);

    // Historical layer: re-bind diff statya locally (fixture decision).
    let mut map = load_hierarchy_map_for_path(seed_path).unwrap_or_else(|_| HierarchyMap::empty());
    for m in diff.removed.iter().chain(diff.added.iter()) {
        if m.level() != "statya" {
            continue;
        }
        if let Ok(cc) = ComponentConceptId::parse(&format!("cc:44-fz:statya-{}", m.number())) {
            if let Ok(binding) =
                ln_kb_ontology::domain::HierarchyBinding::try_new(None, m.level(), m.number(), cc)
            {
                let _ = map.register(binding);
            }
        }
    }

    // Structural change takes effect at the target edition's from-date
    // (in force), not its rev-date (signing). Both editions of a pair can
    // share one rev-date; the test chain uses the same rule.
    let edition_effect_day = |path: &str| -> Option<i64> {
        let from_date = path
            .rsplit('/')
            .next()
            .and_then(|name| name.find("from-").map(|i| (name, i)))
            .and_then(|(name, i)| {
                let rest = &name[i + 5..];
                if rest.len() >= 10 && rest.as_bytes()[4] == b'-' {
                    Some(rest[..10].to_owned())
                } else {
                    None
                }
            });
        match from_date {
            Some(day) => ln_temporal::calendar::legal_act_effect_day_to_ordinal(&day).ok(),
            None => load_edition_day_for_path(path),
        }
    };
    let drift_report = (|| -> Option<(usize, usize, i64, usize, usize)> {
        let seed_day = load_edition_day_for_path(seed_path)?;
        let target_day = edition_effect_day(target_path)?;
        if target_day <= seed_day {
            return None;
        }
        let seed_propose = propose_membership_from_markers(&map, &seed_markers).ok()?;
        let seed_admit = admit_membership_proposals(&seed_propose.proposals);
        let seed_prov = AmendingActId::parse(&seed_expr).ok()?;
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
                .ok()?,
            )
            .ok()?;
        }
        let target_prov = AmendingActId::parse(&target_expr).ok()?;
        let seed_parents: std::collections::HashMap<String, String> = seed_admit
            .admitted
            .iter()
            .map(|e| (e.child.as_str().to_owned(), e.parent.as_str().to_owned()))
            .collect();
        let target_propose = propose_membership_from_markers(&map, &target_markers).ok()?;
        let target_parents: std::collections::HashMap<String, String> = target_propose
            .proposals
            .iter()
            .map(|p| (p.child.as_str().to_owned(), p.parent.as_str().to_owned()))
            .collect();
        let mut committed_attach = 0usize;
        let mut committed_detach = 0usize;
        for draft in &drafts {
            let probe = HierarchyMarker::try_new(None, &draft.level, &draft.number, None).ok()?;
            let HierarchyMapOutcome::Bound { component } = map_hierarchy_marker(&map, &probe)
            else {
                continue;
            };
            let parent_str = match draft.op {
                AmendmentDraftOp::Attach => target_parents.get(component.as_str()),
                AmendmentDraftOp::Detach => seed_parents.get(component.as_str()),
            }?;
            let parent = ComponentConceptId::parse(parent_str).ok()?;
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
                .ok()?,
            )
            .ok()?;
            match draft.op {
                AmendmentDraftOp::Attach => committed_attach += 1,
                AmendmentDraftOp::Detach => committed_detach += 1,
            }
        }
        let replay_ast = fold_membership_at(&log, target_day).ok()?;
        let mut oracle_log = VersionedMembershipLog::empty();
        let target_admit = admit_membership_proposals(&target_propose.proposals);
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
                    .ok()?,
                )
                .ok()?;
        }
        let oracle_ast = fold_membership_at(&oracle_log, target_day).ok()?;
        let mut oracle_ccs: Vec<ComponentConceptId> = Vec::new();
        for root in oracle_ast.roots() {
            collect_ccs(root, &mut oracle_ccs);
        }
        let drift = ln_kb_ontology::domain::oracle_diff(&replay_ast, &oracle_ccs);
        Some((
            committed_attach,
            committed_detach,
            drift.drift as i64,
            drift.missing,
            drift.phantom,
        ))
    })();

    let (committed_attach, committed_detach, drift, missing, phantom) =
        drift_report.unwrap_or((0, 0, -1, 0, 0));
    let seed_esc = json_escape(&seed_expr);
    let target_esc = json_escape(&target_expr);
    let drift_label = if drift < 0 { "unavailable" } else { "ok" };
    println!(
        "{{\"phase\":\"Replay\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\"duration_ms\":{},\"seed\":{{\"path\":\"{}\",\"blocks\":{},\"markers\":{},\"expression_id\":\"{seed_esc}\"}},\"target\":{{\"path\":\"{}\",\"blocks\":{},\"markers\":{},\"expression_id\":\"{target_esc}\"}},\"diff\":{{\"added\":{},\"removed\":{}}},\"drafts\":{{\"total\":{},\"attach\":{},\"detach\":{}}},\"applied\":{{\"attach\":{},\"detach\":{}}},\"text\":{{\"facet_drafts\":{}}},\"verify\":{{\"drift\":{},\"missing\":{},\"phantom\":{},\"status\":\"{drift_label}\"}},\"non_claims\":[\"Two editions prove replay mechanics, not corpus history\",\"Drafts are hypothesized_from_oracle_diff, not legislative events\",\"Historical layer rebinding is a fixture decision\"]}}",
        start.elapsed().as_millis(),
        json_escape(seed_path),
        seed_blocks,
        seed_markers.len(),
        json_escape(target_path),
        target_blocks,
        target_markers.len(),
        diff.added.len(),
        diff.removed.len(),
        drafts.len(),
        attach,
        detach,
        committed_attach,
        committed_detach,
        text_draft_count,
        drift,
        missing,
        phantom,
    );
}

fn collect_ccs(node: &ln_temporal::domain::StructuralAstNode, out: &mut Vec<ComponentConceptId>) {
    out.push(node.component().clone());
    for child in node.children() {
        collect_ccs(child, out);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- M163: deterministic embedding contracts ---
    // The CLI retrieval pipeline must derive a deterministic vector from input
    // text (replacing the prior hardcoded vec![0.5; dims] that made every
    // document and query identical and retrieval a no-op). Bounded: hash-based,
    // NOT semantic. Lifecycle [bounded].

    #[test]
    fn same_text_produces_identical_vector() {
        let a = deterministic_vector("вступает в силу", 4);
        let b = deterministic_vector("вступает в силу", 4);
        assert_eq!(a, b, "same text must produce identical vector");
        assert_eq!(a.len(), 4);
    }

    #[test]
    fn different_text_produces_different_vector() {
        let a = deterministic_vector("вступает в силу", 4);
        let b = deterministic_vector("утрачивает силу", 4);
        assert_ne!(a, b, "different text must produce a different vector");
    }

    #[test]
    fn deterministic_across_repeated_calls() {
        let text = "law-nexus inspector query";
        let first = deterministic_vector(text, 8);
        for _ in 0..10 {
            assert_eq!(
                deterministic_vector(text, 8),
                first,
                "must be deterministic"
            );
        }
    }

    #[test]
    fn all_values_finite_and_in_unit_range() {
        let v = deterministic_vector("sample block text", 16);
        assert_eq!(v.len(), 16);
        for x in &v {
            assert!(x.is_finite(), "values must be finite: {v:?}");
            assert!(*x >= 0.0 && *x <= 1.0, "values must be in [0,1]: {v:?}");
        }
    }

    #[test]
    fn dimension_is_respected() {
        assert_eq!(deterministic_vector("x", 1).len(), 1);
        assert_eq!(deterministic_vector("x", 7).len(), 7);
        assert_eq!(deterministic_vector("x", 1024).len(), 1024);
    }

    fn sample_node(level: ln_decode::domain::HierarchyLevel, number: &str) -> HierarchyNode {
        HierarchyNode::try_new(
            level,
            number.to_owned(),
            Some("title".to_owned()),
            format!("marker {number} title"),
            ln_decode::domain::TextSpan::try_new(0, 6).expect("span"),
        )
        .expect("node")
    }

    #[test]
    fn empty_registry_lifts_statya_as_unknown() {
        let map = HierarchyMap::empty();
        let outcome = lift_extracted_hierarchy(
            &sample_node(ln_decode::domain::HierarchyLevel::Statya, "93"),
            &map,
        )
        .expect("alias");
        assert_eq!(outcome, HierarchyMapOutcome::Unknown);
        assert!(outcome
            .non_claims()
            .iter()
            .any(|claim| claim.contains("Unknown") || claim.contains("ComponentConcept")));
    }
}
