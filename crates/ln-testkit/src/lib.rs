//! Shared port-contract helpers for law-nexus (ADR-0015).
//!
//! These helpers encode semantic expectations that every adapter of a port
//! must satisfy. InMemory adapters must pass the same suite intended for
//! future real adapters (TEI/RuVector/redb).
//!
//! Lifecycle: foundation is `[bounded]`. Real-infrastructure validation is not
//! claimed by the existence of this crate.

use ln_citation::domain::{SourceAuthority, SourceRef};
use ln_citation::ports::CitationSourcePort;
use ln_decode::domain::{
    DecodeCategory, DecodeRequest, DiagnosticId, FamilyFormat, PayloadRef, SafeDiagnostic,
};
use ln_decode::ports::{DecoderPort, DiagnosticPort as DecodeDiagnosticPort};
use ln_diagnostic::domain::SinkId;
use ln_diagnostic::ports::DiagnosticSinkPort;
use ln_gate::domain::{CandidateId, CandidateRecord, LifecycleType};
use ln_gate::ports::CandidateStorePort;
use ln_identity::domain::{IdentityId, IdentityRecord};
use ln_identity::ports::IdentityStorePort;
use ln_inventory::domain::{
    DropReference, InventoryItemId, InventoryRequestId, ObservationAttempt, ObservationAttemptId,
};
use ln_inventory::ports::{InventoryStorePort, VisibilityPort};
use ln_observe::domain::{
    DiagnosticCode, DiagnosticEvent, DiagnosticId as ObserveDiagnosticId, ObservationId,
    ObservationRequestId, SourceChannelId, WorkPhase, WorkTransition,
};
use ln_observe::ports::{DiagnosticPort as ObserveDiagnosticPort, WorkStatePort};
use ln_promote::domain::{
    AcceptedSetId, InputDigest, PromotionAttemptState, PromotionOpId, PromotionRecord,
};
use ln_promote::ports::PromotionStorePort;
use ln_publish::domain::{
    AuthoritySurface, CompletenessEvidence, CutoffId, H1UnitId, InputDigest as PubInputDigest,
    OperationId as PubOperationId, PublicationAuthority, PublicationRecord, RuleVersion, ScopeId,
    WriterId,
};
use ln_publish::ports::PublicationLedgerPort;
use ln_query::domain::EvidenceId;
use ln_query::ports::QueryStatePort;
use ln_storage::{
    GraphEdge, GraphNode, GraphStorePort, StorageError, VectorQuery, VectorRecord, VectorStorePort,
};
use ln_temporal::domain::ClockKind;
use ln_temporal::ports::ClockEvidencePort;

fn vector_record(id: &str, dims: &[f32]) -> VectorRecord {
    VectorRecord::try_new(id, dims.to_vec(), Vec::new()).expect("valid vector record")
}

fn vector_query(dims: &[f32], top_k: usize) -> VectorQuery {
    VectorQuery::try_new(dims.to_vec(), top_k).expect("valid vector query")
}

fn graph_node(id: &str, label: &str) -> GraphNode {
    GraphNode::try_new(id, label, Vec::new()).expect("valid graph node")
}

fn graph_edge(source: &str, target: &str, label: &str) -> GraphEdge {
    GraphEdge::try_new(source, target, label).expect("valid graph edge")
}

/// Shared semantic contract for [`VectorStorePort`].
pub fn assert_vector_store_contract<S: VectorStorePort>(store: &mut S) {
    let dims = [0.5_f32, 0.3, 0.2];
    let first = vector_record("contract-v1", &dims);
    let second = vector_record("contract-v2", &dims);

    store
        .store(&first)
        .expect("store accepts a validated vector record");
    store
        .store(&second)
        .expect("store accepts a second validated vector record");

    let results = store
        .query(&vector_query(&dims, 10))
        .expect("query returns stored records");
    let ids: Vec<&str> = results.iter().map(VectorRecord::id).collect();
    assert!(
        ids.contains(&"contract-v1") && ids.contains(&"contract-v2"),
        "query must return both stored ids, got {ids:?}"
    );

    // Idempotent upsert by id: second store of same id does not create a duplicate.
    store
        .store(&first)
        .expect("upsert of existing id must succeed");
    let after_upsert = store
        .query(&vector_query(&dims, 10))
        .expect("query after upsert");
    let count_v1 = after_upsert
        .iter()
        .filter(|record| record.id() == "contract-v1")
        .count();
    assert_eq!(count_v1, 1, "vector id upsert must be idempotent");

    // top_k bounds result cardinality.
    let limited = store
        .query(&vector_query(&dims, 1))
        .expect("top_k=1 query succeeds");
    assert!(
        limited.len() <= 1,
        "top_k must bound returned cardinality, got {}",
        limited.len()
    );

    // Empty id is rejected by validated record construction; adapter must still
    // reject empty top-level misuse if it re-validates — covered by type boundary.
    let _ = StorageError::EmptyInput;
}

/// Shared semantic contract for [`GraphStorePort`].
pub fn assert_graph_store_contract<S: GraphStorePort>(store: &mut S) {
    let article = graph_node("contract-n1", "Statya");
    let point = graph_node("contract-n2", "Punkt");
    let edge = graph_edge("contract-n1", "contract-n2", "CONTAINS");

    store
        .upsert_node(&article)
        .expect("upsert accepts validated node");
    store
        .upsert_node(&point)
        .expect("upsert accepts second validated node");
    store
        .upsert_edge(&edge)
        .expect("upsert accepts validated edge");

    let articles = store
        .query_nodes("Statya")
        .expect("label query returns nodes");
    assert_eq!(
        articles.len(),
        1,
        "exact label query returns one Statya node"
    );
    assert_eq!(articles[0].id(), "contract-n1");

    let points = store
        .query_nodes("Punkt")
        .expect("label query returns Punkt nodes");
    assert_eq!(points.len(), 1);
    assert_eq!(points[0].id(), "contract-n2");

    // Idempotent node upsert by id.
    store
        .upsert_node(&article)
        .expect("node upsert by id is idempotent");
    let articles_after = store
        .query_nodes("Statya")
        .expect("label query after upsert");
    assert_eq!(
        articles_after.len(),
        1,
        "node id upsert must not create duplicates"
    );

    // Unknown label returns empty, not error.
    let missing = store
        .query_nodes("MissingLabel")
        .expect("unknown label is empty success");
    assert!(
        missing.is_empty(),
        "unknown label must return empty set, got {}",
        missing.len()
    );
}

/// Shared semantic contract for honest [`CitationSourcePort`] adapters.
///
/// Expects resolve/missing semantics and authority preservation. Hostile
/// adapters that invent Official authority from Mirror data must fail this
/// suite (see [`assert_hostile_mirror_fails_honest_citation_contract`]).
pub fn assert_citation_source_contract<S: CitationSourcePort>(source: &S) {
    let known = SourceRef::parse("src:contract-known").expect("source ref");
    let missing = SourceRef::parse("src:contract-missing").expect("source ref");

    let resolved = source.resolve(&known).expect("known source must resolve");
    assert_eq!(resolved.0.as_str(), "anchor:contract-1");
    assert_eq!(resolved.1, SourceAuthority::Official);

    assert!(
        source.resolve(&missing).is_none(),
        "unknown source must return None, not invented anchor"
    );

    let mirror = SourceRef::parse("src:contract-mirror").expect("source ref");
    let mirror_resolved = source
        .resolve(&mirror)
        .expect("mirror source must resolve with honest authority");
    assert_eq!(mirror_resolved.0.as_str(), "anchor:contract-2");
    assert_eq!(
        mirror_resolved.1,
        SourceAuthority::Mirror,
        "honest adapter must not relabel Mirror as Official"
    );
}

/// Negative contract: hostile mirror relabeler must not pass the honest suite.
pub fn assert_hostile_mirror_fails_honest_citation_contract<S: CitationSourcePort>(source: &S) {
    let mirror = SourceRef::parse("src:contract-mirror").expect("source ref");
    let resolved = source
        .resolve(&mirror)
        .expect("hostile fixture must still resolve the mirror source");
    assert_eq!(
        resolved.1,
        SourceAuthority::Official,
        "hostile fixture expected to invent Official authority"
    );
    // The honest contract requires Mirror authority for this source key.
    assert_ne!(
        resolved.1,
        SourceAuthority::Mirror,
        "hostile adapter must fail honest authority preservation"
    );
}

/// Shared semantic contract for [`PromotionStorePort`].
pub fn assert_promotion_store_contract<S: PromotionStorePort>(store: &mut S) {
    let op = PromotionOpId::parse("P-contract-1").expect("op id");
    let set = AcceptedSetId::parse("I-contract-1").expect("set id");
    let digest = InputDigest::parse("D-contract-1").expect("digest");

    assert!(store.get(&op).is_none(), "empty store has no record");
    assert_eq!(store.committed_count(), 0);
    assert!(!store.has_curated_effect_for(&op));

    let commit_id = store.next_commit_id();
    let record = PromotionRecord {
        op_id: op.clone(),
        accepted_set_id: set,
        input_digest: digest.clone(),
        state: PromotionAttemptState::Committed,
        commit_id: Some(commit_id.clone()),
        commit_digest: Some(digest.clone()),
        publication_authority: None,
    };
    store.put(record);

    let loaded = store.get(&op).expect("committed record is readable");
    assert_eq!(loaded.state, PromotionAttemptState::Committed);
    assert_eq!(loaded.commit_id.as_ref(), Some(&commit_id));
    assert_eq!(store.committed_count(), 1);
    assert!(store.has_curated_commit(&commit_id));
    assert!(store.has_curated_effect_for(&op));
    assert_eq!(
        store
            .commit_digest_for(&commit_id)
            .as_ref()
            .map(|d| d.as_str()),
        Some(digest.as_str())
    );

    // Idempotent put of same committed identity must not create a second commit effect.
    store.put(loaded.clone());
    assert_eq!(store.committed_count(), 1);

    // Cancel/incomplete replacement removes curated effect for the op.
    let cancelled = PromotionRecord {
        state: PromotionAttemptState::Cancelled,
        commit_id: None,
        commit_digest: None,
        publication_authority: None,
        ..loaded
    };
    store.put(cancelled);
    assert_eq!(store.committed_count(), 0);
    assert!(!store.has_curated_effect_for(&op));
}

/// Shared semantic contract for honest [`QueryStatePort`] adapters.
///
/// Expects known evidence to resolve, unknown evidence to remain missing, and
/// `evidence_ids` to list only stored identities. Hostile gap inventors that
/// claim missing evidence exists must fail this suite (see
/// [`assert_hostile_gap_inventor_fails_honest_query_contract`]).
pub fn assert_query_state_contract<S: QueryStatePort>(state: &S) {
    let known = EvidenceId::parse("ev:contract-known").expect("evidence id");
    let missing = EvidenceId::parse("ev:contract-missing").expect("evidence id");

    assert!(
        state.has_evidence(&known),
        "honest state must report known evidence present"
    );
    assert!(
        !state.has_evidence(&missing),
        "honest state must not invent missing evidence"
    );

    let listed = state.evidence_ids();
    let ids: Vec<&str> = listed.iter().map(EvidenceId::as_str).collect();
    assert!(
        ids.contains(&"ev:contract-known"),
        "evidence_ids must include known evidence, got {ids:?}"
    );
    assert!(
        !ids.contains(&"ev:contract-missing"),
        "evidence_ids must not invent missing evidence, got {ids:?}"
    );
}

/// Negative contract: hostile gap inventor must invent presence for missing ids.
pub fn assert_hostile_gap_inventor_fails_honest_query_contract<S: QueryStatePort>(state: &S) {
    let missing = EvidenceId::parse("ev:contract-missing").expect("evidence id");
    assert!(
        state.has_evidence(&missing),
        "hostile gap inventor expected to invent missing evidence"
    );
    let listed = state.evidence_ids();
    let ids: Vec<&str> = listed.iter().map(EvidenceId::as_str).collect();
    assert!(
        !ids.contains(&"ev:contract-missing"),
        "hostile inventor still lists only real evidence_ids, got {ids:?}"
    );
}

/// Shared semantic contract for honest [`PublicationLedgerPort`] adapters.
///
/// Covers store-level put/get/writer/unit/count semantics. Application-owned
/// exclusivity policy remains in `ln-publish` use-case tests.
pub fn assert_publication_ledger_contract<S: PublicationLedgerPort>(ledger: &mut S) {
    let op = PubOperationId::parse("op:contract-1").expect("op");
    let writer = WriterId::parse("writer:contract-A").expect("writer");
    let scope = ScopeId::parse("scope:contract-S1").expect("scope");
    let unit = H1UnitId::parse("h1:contract-1").expect("unit");
    let digest = PubInputDigest::parse("digest:contract-1").expect("digest");

    assert!(
        ledger.get_by_operation(&op).is_none(),
        "empty ledger has no operation record"
    );
    assert_eq!(ledger.authoritative_count(), 0);
    assert!(!ledger.has_unit(&unit));
    assert!(ledger.writer_for_scope(&scope).is_none());

    let record = PublicationRecord {
        operation_id: op.clone(),
        writer_id: writer.clone(),
        scope_id: scope.clone(),
        cutoff_id: CutoffId::parse("cutoff:contract").expect("cutoff"),
        rule_version: RuleVersion::parse("rules:contract-v1").expect("rules"),
        input_digest: digest,
        h1_unit_id: unit.clone(),
        completeness: CompletenessEvidence::Complete,
        authoritative: true,
        publication_authority: Some(PublicationAuthority::default()),
        authority_surface: AuthoritySurface::Publication,
    };
    ledger.put(record.clone());

    let loaded = ledger
        .get_by_operation(&op)
        .expect("operation record is readable");
    assert_eq!(loaded.h1_unit_id.as_str(), unit.as_str());
    assert!(loaded.authoritative);

    let auth = ledger
        .get_authoritative_for_scope(&scope)
        .expect("authoritative scope record");
    assert_eq!(auth.operation_id.as_str(), op.as_str());
    assert_eq!(
        ledger
            .writer_for_scope(&scope)
            .as_ref()
            .map(WriterId::as_str),
        Some(writer.as_str())
    );
    assert_eq!(ledger.authoritative_count(), 1);
    assert!(ledger.has_unit(&unit));

    // Non-authoritative put must not displace authoritative scope/writer maps.
    let non_auth_op = PubOperationId::parse("op:contract-partial").expect("op");
    let non_auth_unit = H1UnitId::parse("h1:contract-partial").expect("unit");
    let non_auth = PublicationRecord {
        operation_id: non_auth_op.clone(),
        writer_id: WriterId::parse("writer:contract-B").expect("writer"),
        scope_id: scope.clone(),
        cutoff_id: CutoffId::parse("cutoff:contract").expect("cutoff"),
        rule_version: RuleVersion::parse("rules:contract-v1").expect("rules"),
        input_digest: PubInputDigest::parse("digest:contract-partial").expect("digest"),
        h1_unit_id: non_auth_unit.clone(),
        completeness: CompletenessEvidence::Partial,
        authoritative: false,
        publication_authority: None,
        authority_surface: AuthoritySurface::Publication,
    };
    ledger.put(non_auth);

    assert!(
        ledger.get_by_operation(&non_auth_op).is_some(),
        "non-authoritative operation remains readable"
    );
    assert!(ledger.has_unit(&non_auth_unit));
    let still_auth = ledger
        .get_authoritative_for_scope(&scope)
        .expect("authoritative scope must remain first unit");
    assert_eq!(still_auth.operation_id.as_str(), op.as_str());
    assert_eq!(
        ledger
            .writer_for_scope(&scope)
            .as_ref()
            .map(WriterId::as_str),
        Some(writer.as_str()),
        "non-authoritative put must not replace exclusive writer"
    );
    assert_eq!(ledger.authoritative_count(), 1);
}

/// Shared semantic contract for honest [`DecoderPort`] adapters.
///
/// Expects structural emissions with anchors and no gate-owned categories or
/// raw payload leakage. Malicious adapters that emit VerifiedAssertion /
/// MergedIdentity / UnregisteredRelation / RawFailureContext or canary raw
/// context must fail this suite (see
/// [`assert_malicious_decoder_fails_honest_contract`]).
pub fn assert_decoder_port_contract<D: DecoderPort>(decoder: &D) {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:contract-decode").expect("payload"),
        FamilyFormat::parse("family:synthetic").expect("family"),
        b"contract decode bytes",
    );
    let emissions = decoder.decode(&request);
    assert!(
        !emissions.is_empty(),
        "honest decoder must emit at least one structural candidate"
    );
    for emission in &emissions {
        assert_eq!(
            emission.category,
            DecodeCategory::StructuralCandidate,
            "honest decoder must only emit structural candidates"
        );
        assert!(
            emission.anchor.is_some(),
            "honest structural emission must carry an evidence anchor"
        );
        assert!(
            emission.raw_context.is_none(),
            "honest decoder must not leak raw context"
        );
        if let Some(anchor) = &emission.anchor {
            assert_eq!(anchor.start_offset, 0);
            assert_eq!(anchor.end_offset, request.bytes.len());
            assert!(
                !anchor.fingerprint.is_empty(),
                "anchor fingerprint must be present"
            );
        }
    }
}

/// Negative contract: malicious decoder emits gate-owned categories and raw canaries.
pub fn assert_malicious_decoder_fails_honest_contract<D: DecoderPort>(decoder: &D) {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:contract-hostile").expect("payload"),
        FamilyFormat::parse("family:synthetic").expect("family"),
        b"CANARY::SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK",
    );
    let emissions = decoder.decode(&request);
    assert!(
        !emissions.is_empty(),
        "malicious fixture must still emit something"
    );
    let categories: Vec<DecodeCategory> = emissions.iter().map(|e| e.category).collect();
    assert!(
        categories
            .iter()
            .any(|c| *c != DecodeCategory::StructuralCandidate),
        "malicious decoder expected to emit non-structural categories, got {categories:?}"
    );
    assert!(
        emissions.iter().any(|e| e.raw_context.is_some()),
        "malicious decoder expected to leak raw_context"
    );
}

/// Shared semantic contract for decode-crate [`DecodeDiagnosticPort`].
pub fn assert_decode_diagnostic_port_contract<S: DecodeDiagnosticPort>(sink: &mut S) {
    assert!(
        sink.events().is_empty(),
        "empty diagnostic sink has no events"
    );
    let event = SafeDiagnostic {
        diagnostic_id: DiagnosticId::parse("diag:contract-1").expect("diagnostic id"),
        category: "contract".to_owned(),
        positive_control: false,
        byte_count: 12,
        fingerprint: "fp-contract-1".to_owned(),
    };
    sink.record(event.clone());
    let events = sink.events();
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].diagnostic_id.as_str(), "diag:contract-1");
    assert_eq!(events[0].category, "contract");
    assert_eq!(events[0].byte_count, 12);
    assert_eq!(events[0].fingerprint, "fp-contract-1");
    assert!(!events[0].positive_control);
}

/// Shared semantic contract for honest [`WorkStatePort`] adapters.
pub fn assert_work_state_contract<S: WorkStatePort>(state: &mut S) {
    assert!(
        state.transitions().is_empty(),
        "empty work state has no transitions"
    );
    let request_id = ObservationRequestId::parse("req:contract-1").expect("request id");
    state.record_transition(WorkTransition {
        request_id: request_id.clone(),
        phase: WorkPhase::Started,
    });
    state.record_transition(WorkTransition {
        request_id: request_id.clone(),
        phase: WorkPhase::ObservationCompleted,
    });
    let transitions = state.transitions();
    assert_eq!(transitions.len(), 2);
    assert_eq!(transitions[0].request_id.as_str(), "req:contract-1");
    assert_eq!(transitions[0].phase, WorkPhase::Started);
    assert_eq!(transitions[1].phase, WorkPhase::ObservationCompleted);
}

/// Shared semantic contract for observe-crate [`ObserveDiagnosticPort`].
pub fn assert_observe_diagnostic_port_contract<S: ObserveDiagnosticPort>(sink: &mut S) {
    assert!(sink.events().is_empty(), "empty observe diagnostic sink");
    let event = DiagnosticEvent {
        diagnostic_id: ObserveDiagnosticId::parse("diag:observe-contract-1").expect("diag id"),
        observation_id: ObservationId::parse("obs:contract-1").expect("obs id"),
        source_channel_id: SourceChannelId::parse("channel:contract").expect("channel"),
        phase: DiagnosticCode::new("observe-source"),
        category: DiagnosticCode::new("timeout"),
        retryable: true,
        partial_byte_count: 4,
        partial_fingerprint: "fp-partial".to_owned(),
    };
    sink.emit(event);
    let events = sink.events();
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].diagnostic_id.as_str(), "diag:observe-contract-1");
    assert_eq!(events[0].phase.as_str(), "observe-source");
    assert_eq!(events[0].category.as_str(), "timeout");
    assert!(events[0].retryable);
    assert_eq!(events[0].partial_byte_count, 4);
}

/// Shared semantic contract for honest [`DiagnosticSinkPort`] adapters.
///
/// Expects allowlist gating: only allowed sinks accept emit, disallowed sinks
/// remain blocked. Hostile adapters that allow every sink must fail this suite
/// (see [`assert_hostile_canary_fails_honest_diagnostic_sink_contract`]).
pub fn assert_diagnostic_sink_port_contract<S: DiagnosticSinkPort>(sink: &mut S) {
    let allowed = SinkId::parse("sink:contract-allowed").expect("sink");
    let blocked = SinkId::parse("sink:contract-blocked").expect("sink");

    assert!(
        sink.is_allowed(&allowed),
        "honest sink must allow configured sink"
    );
    assert!(
        !sink.is_allowed(&blocked),
        "honest sink must not allow unconfigured sink"
    );
    sink.emit(&allowed, "contract-safe-content");
}

/// Negative contract: hostile canary sink allows every sink id.
pub fn assert_hostile_canary_fails_honest_diagnostic_sink_contract<S: DiagnosticSinkPort>(
    sink: &S,
) {
    let blocked = SinkId::parse("sink:contract-blocked").expect("sink");
    assert!(
        sink.is_allowed(&blocked),
        "hostile canary expected to allow unconfigured sink"
    );
}

/// Shared semantic contract for honest [`InventoryStorePort`] adapters.
///
/// Expects append-only observation history: re-inventory appends without
/// destroying prior attempts, and unknown items return empty history.
pub fn assert_inventory_store_contract<S: InventoryStorePort>(store: &mut S) {
    let item = InventoryItemId::parse("item:contract-D1:digest").expect("item id");
    let missing = InventoryItemId::parse("item:contract-missing").expect("item id");
    assert!(
        store.attempts_for(&item).is_empty(),
        "empty inventory store has no attempts"
    );
    assert!(
        store.attempts_for(&missing).is_empty(),
        "unknown item must return empty attempts"
    );

    let first = ObservationAttempt {
        attempt_id: ObservationAttemptId::parse("attempt:1").expect("attempt id"),
        request_id: InventoryRequestId::parse("INV-contract-1").expect("request id"),
        drop_reference: DropReference::parse("D1").expect("drop"),
        input_digest: "fnv1a64:contract-1".to_owned(),
    };
    let history = store.append_attempt(&item, first.clone());
    assert_eq!(history.len(), 1);
    assert_eq!(history[0].attempt_id.as_str(), "attempt:1");

    let second = ObservationAttempt {
        attempt_id: ObservationAttemptId::parse("attempt:2").expect("attempt id"),
        request_id: InventoryRequestId::parse("INV-contract-2").expect("request id"),
        drop_reference: DropReference::parse("D1").expect("drop"),
        input_digest: "fnv1a64:contract-1".to_owned(),
    };
    let history = store.append_attempt(&item, second);
    assert_eq!(
        history.len(),
        2,
        "re-inventory must append, not rewrite prior attempts"
    );
    assert_eq!(history[0].attempt_id.as_str(), "attempt:1");
    assert_eq!(history[1].attempt_id.as_str(), "attempt:2");

    let listed = store.attempts_for(&item);
    assert_eq!(listed.len(), 2);
    assert_eq!(listed[0].input_digest, first.input_digest);
}

/// Shared semantic contract for honest [`VisibilityPort`] adapters.
pub fn assert_visibility_port_contract<V: VisibilityPort>(view: &V) {
    let item = InventoryItemId::parse("item:contract-D1:digest").expect("item id");
    assert!(
        view.inventory_review_visible(&item),
        "honest inventory visibility view must expose inventory/review surface"
    );
}

/// Shared semantic contract for honest [`CandidateStorePort`] adapters.
///
/// Expects put/get/missing semantics and lifecycle_type preservation. Hostile
/// stores that rewrite lifecycle on put must fail this suite (see
/// [`assert_inplace_mutating_hostile_fails_honest_candidate_contract`]).
pub fn assert_candidate_store_contract<S: CandidateStorePort>(store: &mut S) {
    let id = CandidateId::parse("C-contract-1").expect("candidate id");
    let missing = CandidateId::parse("C-contract-missing").expect("candidate id");
    assert!(
        store.get(&id).is_none(),
        "empty candidate store has no record"
    );
    assert!(
        store.get(&missing).is_none(),
        "unknown candidate must return None"
    );

    let record = CandidateRecord {
        candidate_id: id.clone(),
        lifecycle_type: LifecycleType::ExtractedCandidate,
        evidence_refs: Vec::new(),
        predecessor: None,
    };
    store.put(record);

    let loaded = store.get(&id).expect("stored candidate is readable");
    assert_eq!(loaded.candidate_id.as_str(), "C-contract-1");
    assert_eq!(
        loaded.lifecycle_type,
        LifecycleType::ExtractedCandidate,
        "honest store must preserve lifecycle type"
    );
    assert!(loaded.predecessor.is_none());

    // Idempotent put of same extracted identity must not invent verified lifecycle.
    store.put(loaded.clone());
    let again = store.get(&id).expect("candidate still present");
    assert_eq!(again.lifecycle_type, LifecycleType::ExtractedCandidate);
}

/// Negative contract: in-place mutating hostile rewrites lifecycle to VerifiedAssertion.
pub fn assert_inplace_mutating_hostile_fails_honest_candidate_contract<S: CandidateStorePort>(
    store: &mut S,
) {
    let id = CandidateId::parse("C-contract-hostile").expect("candidate id");
    store.put(CandidateRecord {
        candidate_id: id.clone(),
        lifecycle_type: LifecycleType::ExtractedCandidate,
        evidence_refs: Vec::new(),
        predecessor: None,
    });
    let loaded = store.get(&id).expect("hostile store still stores record");
    assert_eq!(
        loaded.lifecycle_type,
        LifecycleType::VerifiedAssertion,
        "hostile store expected to rewrite lifecycle on put"
    );
}

/// Shared semantic contract for honest [`IdentityStorePort`] adapters.
///
/// Expects put/get/contains/remove and does not erase unrelated identities on put.
pub fn assert_identity_store_contract<S: IdentityStorePort>(store: &mut S) {
    let left = IdentityId::parse("ID-contract-A").expect("identity id");
    let right = IdentityId::parse("ID-contract-B").expect("identity id");
    assert!(!store.contains(&left));
    assert!(store.get(&left).is_none());

    store.put(IdentityRecord {
        identity_id: left.clone(),
        label: "Act edition A".to_owned(),
    });
    store.put(IdentityRecord {
        identity_id: right.clone(),
        label: "Act edition B".to_owned(),
    });

    assert!(store.contains(&left));
    assert!(store.contains(&right));
    let loaded = store.get(&left).expect("left identity readable");
    assert_eq!(loaded.label, "Act edition A");
    assert_eq!(
        store.get(&right).expect("right identity readable").label,
        "Act edition B"
    );

    // Put of left again must not erase right.
    store.put(IdentityRecord {
        identity_id: left.clone(),
        label: "Act edition A updated".to_owned(),
    });
    assert!(
        store.contains(&right),
        "honest identity store must not erase unrelated identities on put"
    );
    assert_eq!(
        store.get(&left).expect("left still present").label,
        "Act edition A updated"
    );

    assert!(store.remove(&right));
    assert!(!store.contains(&right));
    assert!(store.get(&right).is_none());
    assert!(store.contains(&left));
}

/// Negative contract: erasing merger hostile deletes a targeted right identity on put.
pub fn assert_erasing_merger_hostile_fails_honest_identity_contract<S: IdentityStorePort>(
    store: &mut S,
    right_id: &IdentityId,
) {
    let left = IdentityId::parse("ID-contract-hostile-left").expect("identity id");
    store.put(IdentityRecord {
        identity_id: right_id.clone(),
        label: "right".to_owned(),
    });
    store.put(IdentityRecord {
        identity_id: left,
        label: "left".to_owned(),
    });
    assert!(
        !store.contains(right_id),
        "hostile erasing merger expected to erase targeted right identity on put"
    );
}

/// Shared semantic contract for honest [`ClockEvidencePort`] adapters.
///
/// Expects present anchors to resolve and a missing governing clock to remain
/// None. Application substitution policy remains in `ln-temporal` use-case tests.
pub fn assert_clock_evidence_port_contract<E: ClockEvidencePort>(evidence: &E) {
    // Fixture should include all clocks except SystemObservation.
    let present = ClockKind::FactualEvent;
    let missing = ClockKind::SystemObservation;

    let anchor = evidence
        .anchor_for(present)
        .expect("present clock must resolve to an anchor");
    assert!(!anchor.as_str().is_empty(), "anchor id must be non-empty");
    assert!(
        evidence.anchor_for(missing).is_none(),
        "missing governing clock must return None, not a substitute anchor"
    );
}
