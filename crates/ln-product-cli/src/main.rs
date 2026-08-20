use std::env;
use std::fs;
use std::process;
use std::time::Instant;

use ln_decode::{
    adapters::{
        garant_odt::GarantOdtBlockDecoder, garant_odt_package::read_odt_content_xml,
        ConsultantWordMlBlockDecoder,
    },
    article_body::collect_article_texts,
    deontic::extract_deontic_lexemes,
    domain::{
        fingerprint_bytes, DecodeRequest, FamilyFormat, HierarchyNode, ParagraphStyle, PayloadRef,
    },
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
    references::extract_reference_mentions,
    structural_profile::{DetectionFactor, GroupDetection, StructuralProfile, UnknownReason},
    temporal::extract_temporal_phrases,
    unknown_forms::census_unknown_forms,
};
use ln_kb_ontology::domain::{
    admit_membership_proposals, assemble_with_oracle_diff, build_text_log_from_articles,
    diff_marker_sets, drafts_from_marker_diff, edition_ast_at, map_hierarchy_marker,
    marker_from_decode_token, propose_membership_from_markers, resolve_ctv, AmendmentDraftOp,
    ComponentInExpressionEvent, ComponentInExpressionLog, CtvResolution, ExpressionId,
    HierarchyBinding, HierarchyMap, HierarchyMapOutcome, HierarchyMarker, WriteSetError,
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

    // M171 S01 T03: two-factor document group detection (system_observation
    // heuristic, never legal classification — ADR-0020). The report exposes
    // the bound group, the detection factor, and explicit Unknown/Conflict
    // quarantine counters: an absent group is a visible Unknown, not silence.
    let embedded_profile = StructuralProfile::embedded();
    let detection = embedded_profile
        .as_ref()
        .map(|profile| profile.detect(Some(path), None, None, &blocks));
    let (
        document_group,
        detection_factor,
        detection_unknown_reason,
        detection_unknown,
        detection_conflict,
    ) = match &detection {
        Ok(GroupDetection::Bound { group, factor }) => {
            let factor_str = match factor {
                DetectionFactor::Needle => "needle",
                DetectionFactor::NeedleAndProbe => "needle_and_probe",
            };
            (
                group.clone(),
                factor_str.to_owned(),
                String::new(),
                0u64,
                0u64,
            )
        }
        Ok(GroupDetection::Unknown { reason }) => {
            let reason_str = match reason {
                UnknownReason::NoMetadata => "no_metadata",
                UnknownReason::ProbeConflict { .. } => "probe_conflict",
            };
            (
                "Unknown".to_owned(),
                "none".to_owned(),
                reason_str.to_owned(),
                1u64,
                0u64,
            )
        }
        Ok(GroupDetection::Conflict { .. }) => (
            "Conflict".to_owned(),
            "none".to_owned(),
            String::new(),
            0u64,
            1u64,
        ),
        Err(_) => (
            "Unknown".to_owned(),
            "none".to_owned(),
            "catalog_unavailable".to_owned(),
            1u64,
            0u64,
        ),
    };

    // S_verify text CTV: build TextVersionLog from unit bodies, count
    // resolved. Honest Resolved count per unique CC (not event count): a CC
    // whose latest same-day events disagree is a Conflict, not Resolved.
    // Fail-closed: no bound group (Unknown/Conflict) means no unit bodies —
    // an absent group is a visible Unknown, not a silent statya default.
    //
    // Punkt-as-unit text-CTV (S02): the mint level comes from the YAML
    // catalog group granularity (R086), the CC map for punctuation-grade
    // (subordinate) groups is a local fixture map deliberately separate from
    // the membership registry (invariant: fixture CCs never enter
    // S_bind/S_propose/S_fold — membership_committed stays 0 for PP), and
    // the effect day falls back to the filename document date only in the
    // CTV branch and only for punkt groups. Registry-bound law/code groups
    // keep the existing membership hierarchy_map and registry day unchanged.
    let ctv_resolved = (|| -> usize {
        // Mint level from the YAML catalog granularity (R086); fail-closed:
        // a bound group with no declared granularity yields zero resolved.
        let bound_group = match &detection {
            Ok(GroupDetection::Bound { group, .. }) => group,
            _ => return 0usize,
        };
        let mint_level = match ln_kb_ontology::catalog::OntologyCatalog::embedded() {
            Ok(catalog) => catalog
                .document_group(bound_group)
                .and_then(|profile| profile.granularity.clone()),
            Err(_) => None,
        };
        let Some(mint_level) = mint_level else {
            return 0usize;
        };
        let is_punkt_group = mint_level == "punkt";
        // Effect day: registry first; punkt groups fall back to the filename
        // document date (subordinate fixtures have no registry day).
        let effect_day = load_edition_day_for_path(path).or_else(|| {
            if is_punkt_group {
                subordinate_effect_day_from_filename(path)
            } else {
                None
            }
        });
        let Some(effect_day) = effect_day else {
            return 0usize;
        };
        let units: Vec<ln_decode::article_body::ArticleText> = embedded_profile
            .as_ref()
            .ok()
            .and_then(|profile| profile.group(bound_group))
            .map(|group_profile| {
                ln_decode::article_body::collect_article_texts(group_profile, &blocks)
            })
            .unwrap_or_default();
        // CTV mint map: fixture CCs for punkt groups (local, not the
        // membership registry), else the registry hierarchy_map (law/code).
        let (mint_map, ctv_provenance) = if is_punkt_group {
            let act = subordinate_work_id(path);
            let mut map = HierarchyMap::empty();
            for unit in &units {
                let Ok(cc) =
                    ComponentConceptId::parse(&format!("cc:{act}:punkt-{}", unit.number()))
                else {
                    continue;
                };
                let Ok(binding) = HierarchyBinding::try_new(None, "punkt", unit.number(), cc)
                else {
                    continue;
                };
                let _ = map.register(binding);
            }
            (map, format!("fixture:subordinate:{act}"))
        } else {
            (hierarchy_map, provenance.to_owned())
        };
        let text_log = build_text_log_from_articles(
            &mint_map,
            units
                .iter()
                .map(|a| (mint_level.as_str(), a.number(), a.title(), a.text() as &str)),
            effect_day,
            &ctv_provenance,
        );
        let mut seen = std::collections::HashSet::new();
        let mut resolved = 0usize;
        for event in text_log.events() {
            if !seen.insert(event.component().as_str()) {
                continue;
            }
            if matches!(
                resolve_ctv(&text_log, event.component(), effect_day),
                CtvResolution::Resolved { .. }
            ) {
                resolved += 1;
            }
        }
        resolved
    })();

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
    let document_group_esc = json_escape(&document_group);
    let detection_factor_esc = json_escape(&detection_factor);
    let detection_unknown_reason_esc = json_escape(&detection_unknown_reason);

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
         \"document_group\":\"{document_group_esc}\",\
         \"detection_factor\":\"{detection_factor_esc}\",\
         \"detection_unknown\":{detection_unknown},\
         \"detection_unknown_reason\":\"{detection_unknown_reason_esc}\",\
         \"detection_conflict\":{detection_conflict},\
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
         \"ast_root_count and ast_node_count are structural AST projections, not legal hierarchy or CTV text\",\
         \"punct-grade (punkt) text-CTV uses a local fixture CC map, not the membership registry; fixture CCs are not registry identity and membership_committed stays unaffected\",\
         \"document group binding is a system_observation heuristic (ADR-0020), not legal classification; Unknown/Conflict are explicit quarantine outcomes, never silence\"]}}",
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
        Some("subordinates") => {
            let kind = args.get(1).cloned().unwrap_or_default();
            let path = args.get(2).cloned().unwrap_or_default();
            if kind.is_empty() || path.is_empty() {
                eprintln!("usage: law-nexus-inspect subordinates <resolution|order> <path>");
                process::exit(2);
            }
            subordinates(&kind, &path);
        }
        _ => {
            eprintln!(
                "usage: law-nexus-inspect <health|inspect <path>|replay <seed> <target>|subordinates <resolution|order> <path>>"
            );
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
        // M171 S01 T03: unit bodies come from the detected structural profile.
        // Fail-closed: no bound group (Unknown/Conflict) means no unit bodies
        // — never fall back to a silent statya default.
        let embedded = StructuralProfile::embedded().map_err(|e| e.to_string())?;
        let articles = match embedded.detect(Some(path), None, None, &blocks) {
            GroupDetection::Bound { group, .. } => embedded
                .group(&group)
                .map(|profile| ln_decode::article_body::collect_article_texts(profile, &blocks))
                .unwrap_or_default(),
            _ => Vec::new(),
        };
        Ok(articles)
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

    // Text facet (M170 S02 T02): full article texts compared between editions.
    let text_draft_count = (|| -> Option<usize> {
        let seed_articles = read_articles(seed_path).ok()?;
        let target_articles = read_articles(target_path).ok()?;
        let text_drafts = ln_kb_ontology::domain::changed_article_texts(
            seed_articles
                .iter()
                .map(|a| ("statya", a.number(), None, a.text() as &str)),
            target_articles
                .iter()
                .map(|a| ("statya", a.number(), None, a.text() as &str)),
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

    // Presence channel (M174 S02): make edition_ast_at visible in the CLI.
    // Membership fold from seed markers + include-events for the target
    // oracle CCs → edition AST = membership ∩ expression presence.
    // Bounded: offline synthetic presence log from the oracle snapshot;
    // not expression inheritance, not CTV, not force.
    let presence_report = (|| -> Option<(usize, usize)> {
        let day = edition_effect_day(target_path)
            .or_else(|| load_edition_day_for_path(target_path))
            .or_else(|| load_edition_day_for_path(seed_path))?;
        let expression = ExpressionId::parse(&target_expr).ok()?;
        let prov = AmendingActId::parse(&target_expr).ok()?;
        let mut map =
            load_hierarchy_map_for_path(seed_path).unwrap_or_else(|_| HierarchyMap::empty());
        for m in diff.removed.iter().chain(diff.added.iter()) {
            if m.level() != "statya" {
                continue;
            }
            if let Ok(cc) = ComponentConceptId::parse(&format!("cc:44-fz:statya-{}", m.number())) {
                if let Ok(binding) = ln_kb_ontology::domain::HierarchyBinding::try_new(
                    None,
                    m.level(),
                    m.number(),
                    cc,
                ) {
                    let _ = map.register(binding);
                }
            }
        }
        let propose = propose_membership_from_markers(&map, &target_markers).ok()?;
        let admit = admit_membership_proposals(&propose.proposals);
        let mut mlog = VersionedMembershipLog::empty();
        for edge in &admit.admitted {
            mlog.append(
                VersionedMembershipEvent::try_new(
                    MembershipChangeKind::Attach,
                    edge.parent.clone(),
                    edge.child.clone(),
                    day,
                    prov.clone(),
                )
                .ok()?,
            )
            .ok()?;
        }
        let mut plog = ComponentInExpressionLog::empty();
        for edge in &admit.admitted {
            plog.append(
                ComponentInExpressionEvent::try_new(
                    "include",
                    expression.clone(),
                    edge.child.clone(),
                    day,
                    target_expr.as_str(),
                )
                .ok()?,
            )
            .ok()?;
        }
        let edition = edition_ast_at(&mlog, &plog, &expression, day).ok()?;
        let mut visible: Vec<ComponentConceptId> = Vec::new();
        for root in edition.roots() {
            collect_ccs(root, &mut visible);
        }
        let mut membership: Vec<ComponentConceptId> = Vec::new();
        let composition = fold_membership_at(&mlog, day).ok()?;
        for root in composition.roots() {
            collect_ccs(root, &mut membership);
        }
        let hidden = membership
            .iter()
            .filter(|cc| !visible.iter().any(|v| v == *cc))
            .count();
        Some((visible.len(), hidden))
    })();
    let presence_label = if presence_report.is_some() {
        "ok"
    } else {
        "unavailable"
    };
    let (presence_visible, presence_hidden) = presence_report.unwrap_or((0, 0));
    let seed_esc = json_escape(&seed_expr);
    let target_esc = json_escape(&target_expr);
    let drift_label = if drift < 0 { "unavailable" } else { "ok" };
    println!(
        "{{\"phase\":\"Replay\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\"duration_ms\":{},\"seed\":{{\"path\":\"{}\",\"blocks\":{},\"markers\":{},\"expression_id\":\"{seed_esc}\"}},\"target\":{{\"path\":\"{}\",\"blocks\":{},\"markers\":{},\"expression_id\":\"{target_esc}\"}},\"diff\":{{\"added\":{},\"removed\":{}}},\"drafts\":{{\"total\":{},\"attach\":{},\"detach\":{}}},\"applied\":{{\"attach\":{},\"detach\":{}}},\"text\":{{\"facet_drafts\":{}}},\"presence\":{{\"visible\":{},\"hidden\":{},\"status\":\"{presence_label}\"}},\"verify\":{{\"drift\":{},\"missing\":{},\"phantom\":{},\"status\":\"{drift_label}\"}},\"non_claims\":[\"Two editions prove replay mechanics, not corpus history\",\"Drafts are hypothesized_from_oracle_diff, not legislative events\",\"Historical layer rebinding is a fixture decision\",\"Presence log is oracle-synthesized, not expression inheritance\"]}}",
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
        presence_visible,
        presence_hidden,
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

/// Bounded subordinate-acts report (M171 S03 T02).
///
/// `kind` is the document-kind metadata input for group detection
/// (`resolution` → government_resolution, `order` → departmental_order);
/// the Cyrillic corpus filenames carry no Latin path needle, so the kind
/// needle is passed explicitly. The report proves the punkt-atom groups
/// applied on the real Garant ODT corpus:
///
/// - punkt units per the bound group's ladder (group number styles are
///   authoritative, R8-04 — PP "1." points decode as Chast but collect as
///   punkt units for government_resolution);
/// - fixture-minted CCs for punkt units (explicitly NOT registry identity —
///   the hierarchy registry has no subordinate-act bindings, only ФЗ);
/// - a TextVersionLog + resolve_ctv on a synthetic effect day derived from
///   the document date in the filename (NOT the edition-day registry, which
///   parses only law_* paths);
/// - an explicit `skip_reason` when the effect day cannot be derived
///   (fail-closed: no day means no text-CTV, visibly reported).
///
/// Bounded non-claim: single-snapshot text-CTV; fixture CCs are test-local;
/// duplicate punkt numbers across sections collide on the flat key and are
/// reported as honest Conflicts (fail-closed), never silently merged.
fn subordinates(kind: &str, path: &str) {
    let start = Instant::now();

    let bytes = match fs::read(path) {
        Ok(b) => b,
        Err(e) => print_failure("Io", "ReadFailure", &e.to_string(), start),
    };
    let byte_count = bytes.len();
    let fingerprint = fingerprint_bytes(&bytes);

    let family = FamilyFormat::parse("family:garant-odt").unwrap();
    let payload = PayloadRef::parse("payload:law-nexus-subordinates").unwrap();
    let request = DecodeRequest::new(payload, family, &bytes);
    read_odt_content_xml(&request)
        .unwrap_or_else(|e| print_failure("Parse", "MalformedInput", &format!("ODT: {e}"), start));
    let blocks = GarantOdtBlockDecoder
        .decode_blocks(&request)
        .unwrap_or_else(|e| {
            print_failure(
                "Parse",
                "MalformedInput",
                &format!("{:?}: offset={:?}", e.kind(), e.byte_offset()),
                start,
            )
        });

    let embedded = StructuralProfile::embedded()
        .unwrap_or_else(|e| print_failure("Catalog", "Unavailable", e, start));
    let detection = embedded.detect(Some(path), Some(kind), None, &blocks);
    let (document_group, detection_factor, detection_unknown, detection_conflict) = match &detection
    {
        GroupDetection::Bound { group, factor } => {
            let factor_str = match factor {
                DetectionFactor::Needle => "needle",
                DetectionFactor::NeedleAndProbe => "needle_and_probe",
            };
            (group.clone(), factor_str.to_owned(), 0u64, 0u64)
        }
        GroupDetection::Unknown { .. } => ("Unknown".to_owned(), "none".to_owned(), 1u64, 0u64),
        GroupDetection::Conflict { .. } => ("Conflict".to_owned(), "none".to_owned(), 0u64, 1u64),
    };

    // Punkt units via the bound group's ladder (fail-closed: no bound group
    // means no unit bodies — an absent group is a visible Unknown).
    let units: Vec<ln_decode::article_body::ArticleText> = match &detection {
        GroupDetection::Bound { group, .. } => embedded
            .group(group)
            .map(|profile| collect_article_texts(profile, &blocks))
            .unwrap_or_default(),
        _ => Vec::new(),
    };

    // Fixture CC minting: flat `cc:<work>:punkt-<number>`. Duplicate numbers
    // (PP punkt and an appended regulation punkt sharing "1") collide on the
    // flat key and surface as resolve_ctv Conflicts — honest, not silent.
    let act = subordinate_work_id(path);
    let mut map = HierarchyMap::empty();
    let mut cc_punkts = 0usize;
    for unit in &units {
        let Ok(cc) = ComponentConceptId::parse(&format!("cc:{act}:punkt-{}", unit.number())) else {
            continue;
        };
        let Ok(binding) = HierarchyBinding::try_new(None, "punkt", unit.number(), cc) else {
            continue;
        };
        if map.register(binding).is_ok() {
            cc_punkts += 1;
        }
    }

    // Synthetic effect day from the document date in the filename (bounded
    // Russian-date extractor). NOT the edition-day registry — subordinate
    // acts have no registry entries (the registry holds only ФЗ).
    let effect_day = subordinate_effect_day_from_filename(path);
    let skip_reason = if effect_day.is_some() {
        String::new()
    } else {
        "no_document_date".to_owned()
    };

    let provenance = format!("fixture:subordinate:{act}");
    let (text_log_events, ctv_resolved, ctv_conflict) = if let Some(day) = effect_day {
        let log = build_text_log_from_articles(
            &map,
            units
                .iter()
                .map(|u| ("punkt", u.number(), u.title(), u.text() as &str)),
            day,
            &provenance,
        );
        let events = log.events().len();
        let mut seen = std::collections::HashSet::new();
        let mut resolved = 0usize;
        let mut conflict = 0usize;
        for event in log.events() {
            if !seen.insert(event.component().as_str()) {
                continue;
            }
            match resolve_ctv(&log, event.component(), day) {
                CtvResolution::Resolved { .. } => resolved += 1,
                CtvResolution::Conflict { .. } => conflict += 1,
                _ => {}
            }
        }
        (events, resolved, conflict)
    } else {
        (0, 0, 0)
    };

    let duration_ms = start.elapsed().as_millis();
    let document_group_esc = json_escape(&document_group);
    let skip_reason_esc = json_escape(&skip_reason);
    println!(
        "{{\"phase\":\"Subordinates\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\
         \"duration_ms\":{duration_ms},\
         \"source\":{{\"path\":\"{}\",\"bytes\":{byte_count},\"fingerprint\":\"{fingerprint}\"}},\
         \"family\":\"family:garant-odt\",\
         \"result\":{{\
         \"document_group\":\"{document_group_esc}\",\
         \"detection_factor\":\"{detection_factor}\",\
         \"detection_unknown\":{detection_unknown},\
         \"detection_conflict\":{detection_conflict},\
         \"punkt_units\":{},\
         \"cc_punkts\":{cc_punkts},\
         \"text_log_events\":{text_log_events},\
         \"ctv_resolved\":{ctv_resolved},\
         \"ctv_conflict\":{ctv_conflict},\
         \"effect_day\":{},\
         \"skip_reason\":\"{skip_reason_esc}\",\
         \"expression_id\":\"{provenance}\"\
         }},\
         \"non_claims\":[\"Fixture-minted CCs are test-local, not registry identity\",\
         \"Synthetic effect day from document date; edition-day registry is federal_law-only\",\
         \"Single-snapshot text-CTV; no corpus history claims\",\
         \"Duplicate punkt numbers collide on flat fixture keys and surface as Conflicts, never silent merge\",\
         \"document group binding is a system_observation heuristic (ADR-0020), not legal classification\"]}}",
        json_escape(path),
        units.len(),
        effect_day.unwrap_or(0),
    );
}

/// Bounded fixture work id for a subordinate act filename: `pp-<act number>`
/// when the number is extractable (`PP_60_…`, `№ 60`, `N 1875`), else
/// `subordinate` (documented fixture fallback). Deterministic per path.
fn subordinate_work_id(path: &str) -> String {
    let name = path.rsplit('/').next().unwrap_or(path);
    let lower = name.to_lowercase();
    // Prefer the act number after `N ` / `№` (Latin/№ markers) or `PP_`.
    // The day/date runs come earlier in Cyrillic filenames and are NOT the
    // act number, so the marker-anchored scan runs first.
    for marker in ["n ", "№", "pp_"] {
        if let Some(rel) = lower.find(marker) {
            let after = &name[rel + marker.len()..];
            let digits: String = after
                .chars()
                .skip_while(|c| !c.is_ascii_digit())
                .take_while(|c| c.is_ascii_digit())
                .take(5)
                .collect();
            if !digits.is_empty() {
                return format!("pp-{digits}");
            }
        }
    }
    // Fallback: first short digit run (act-number heuristic).
    let digits: Vec<&str> = name
        .split(|c: char| !c.is_ascii_digit())
        .filter(|part| !part.is_empty())
        .collect();
    if let Some(first) = digits.first() {
        if first.len() <= 4 {
            return format!("pp-{first}");
        }
    }
    "subordinate".to_owned()
}

/// Bounded Russian-document-date extractor (fixture, M171 S03 T02).
///
/// Accepts `от <ДД> <месяц> <ГГГГ>` (Cyrillic month names) and
/// `ДД-ММ-ГГГГ` / `ДД.ММ.ГГГГ` patterns in the basename; normalizes to
/// ISO `ГГГГ-ММ-ДД` and converts via the temporal calendar. Returns None
/// when no date is derivable — the caller reports a visible `skip_reason`.
fn subordinate_effect_day_from_filename(path: &str) -> Option<i64> {
    let name = path.rsplit('/').next().unwrap_or(path);
    let iso = russian_date_to_iso(name)?;
    ln_temporal::calendar::legal_act_effect_day_to_ordinal(&iso).ok()
}

/// Normalize a Russian document date found in `name` to `ГГГГ-ММ-ДД`.
///
/// Two bounded patterns, tried in order: `от <ДД> <месяц> <ГГГГ>` with
/// Cyrillic month names, then any `ДД<sep>ММ<sep>ГГГГ` numeric triple
/// (`-` or `.` separators) scanned anywhere in the basename.
fn russian_date_to_iso(name: &str) -> Option<String> {
    const MONTHS: [(&str, &str); 12] = [
        ("января", "01"),
        ("февраля", "02"),
        ("марта", "03"),
        ("апреля", "04"),
        ("мая", "05"),
        ("июня", "06"),
        ("июля", "07"),
        ("августа", "08"),
        ("сентября", "09"),
        ("октября", "10"),
        ("ноября", "11"),
        ("декабря", "12"),
    ];
    let lower = name.to_lowercase();
    // `от 27 января 2022 г` → DD month YYYY.
    for (month_ru, month_num) in MONTHS {
        if let Some(rel) = lower.find(month_ru) {
            let before = &lower[..rel];
            let day: String = before
                .trim_end()
                .chars()
                .rev()
                .take_while(|c| c.is_ascii_digit())
                .collect::<String>()
                .chars()
                .rev()
                .collect();
            let after = &lower[rel + month_ru.len()..];
            let year: String = after
                .chars()
                .skip_while(|c| !c.is_ascii_digit())
                .take_while(|c| c.is_ascii_digit())
                .take(4)
                .collect();
            if day.len() == 2 && year.len() == 4 {
                return Some(format!("{year}-{month_num}-{day}"));
            }
            if day.len() == 1 && year.len() == 4 {
                return Some(format!("{year}-{month_num}-0{day}"));
            }
        }
    }
    // `27-01-2022` / `27.01.2022` — scan for a DD<sep>MM<sep>YYYY triple
    // anywhere in the basename (the stem may carry `PP_60_`-style prefixes).
    let bytes = name.as_bytes();
    let mut i = 0usize;
    while i < bytes.len() {
        if !bytes[i].is_ascii_digit() {
            i += 1;
            continue;
        }
        let day_start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        let day_len = i - day_start;
        if !(1..=2).contains(&day_len) || i >= bytes.len() || !matches!(bytes[i], b'-' | b'.') {
            continue;
        }
        let sep = bytes[i];
        i += 1;
        let month_start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        let month_len = i - month_start;
        if !(1..=2).contains(&month_len) || i >= bytes.len() || bytes[i] != sep {
            continue;
        }
        i += 1;
        let year_start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        let year_len = i - year_start;
        if year_len != 4 {
            continue;
        }
        let day = &name[day_start..day_start + day_len];
        let month = &name[month_start..month_start + month_len];
        let year = &name[year_start..year_start + 4];
        let dayn: u32 = day.parse().ok()?;
        let monthn: u32 = month.parse().ok()?;
        if (1..=31).contains(&dayn) && (1..=12).contains(&monthn) {
            return Some(format!("{year}-{month:0>2}-{day:0>2}"));
        }
    }
    None
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

    // --- M171 S03 T02: bounded subordinate-act fixture helpers ---

    #[test]
    fn subordinate_work_id_prefers_act_number() {
        assert_eq!(
            subordinate_work_id("law-source/garant/PP_60_27-01-2022.odt"),
            "pp-60"
        );
        assert_eq!(
            subordinate_work_id(
                "law-source/garant/Постановление Правительства РФ от 23 декабря 2024 г N 1875 О м.odt"
            ),
            "pp-1875"
        );
    }

    #[test]
    fn subordinate_work_id_falls_back_to_subordinate() {
        assert_eq!(subordinate_work_id("some/path/unknown.odt"), "subordinate");
    }

    #[test]
    fn russian_date_to_iso_parses_cyrillic_month() {
        assert_eq!(
            russian_date_to_iso("Постановление Правительства РФ от 27 января 2022 г. № 60"),
            Some("2022-01-27".to_owned())
        );
        assert_eq!(
            russian_date_to_iso(
                "Постановление Правительства Российской Федерации от 23 декабря 2024 г N 1875"
            ),
            Some("2024-12-23".to_owned())
        );
    }

    #[test]
    fn russian_date_to_iso_parses_dash_and_dot_dates() {
        assert_eq!(
            russian_date_to_iso("PP_60_27-01-2022.odt"),
            Some("2022-01-27".to_owned())
        );
        assert_eq!(
            russian_date_to_iso("PP_60_27.01.2022.odt"),
            Some("2022-01-27".to_owned())
        );
    }

    #[test]
    fn russian_date_to_iso_rejects_missing_date() {
        assert_eq!(russian_date_to_iso("44-fz.odt"), None);
        assert_eq!(russian_date_to_iso("PP_60.odt"), None);
    }

    #[test]
    fn subordinate_effect_day_converts_via_temporal_calendar() {
        // PP_60 (27-01-2022) must map to a valid civil-day ordinal.
        let day = subordinate_effect_day_from_filename("law-source/garant/PP_60_27-01-2022.odt");
        assert!(day.is_some(), "PP_60 must yield an effect day");
        // A path with no derivable date must be None -> visible skip_reason.
        assert_eq!(
            subordinate_effect_day_from_filename("law-source/garant/44-fz.odt"),
            None
        );
    }
}
