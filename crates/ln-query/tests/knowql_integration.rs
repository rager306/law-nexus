use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
    references::extract_reference_mentions,
};
use ln_query::knowql::{execute, KnowQLOp, KnowQLResult, ValidatedOp};
use ln_storage::{
    adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore},
    EmbeddingPort, EmbeddingRequest, EmbeddingResponse, GraphNode, GraphStorePort, StorageError,
    VectorRecord, VectorStorePort,
};

const CONSULTANT_FIXTURE: &str = "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";

fn fixture_path() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(CONSULTANT_FIXTURE)
}

fn request(bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:knowql-integration").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        bytes,
    )
}

struct StubEmbedding;
impl EmbeddingPort for StubEmbedding {
    fn embed(&self, req: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        Ok(
            EmbeddingResponse::try_new(req.model_id(), vec![0.0; req.expected_dimensions()])
                .unwrap(),
        )
    }
}

#[test]
fn knowql_composes_over_in_memory_adapters_with_real_parser_records() {
    let bytes = std::fs::read(fixture_path()).expect("tracked Consultant fixture");
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(&bytes))
        .expect("decode");

    let mut vector_store = InMemoryVectorStore::new();
    let mut graph_store = InMemoryGraphStore::new();

    let mut stored_count = 0;
    for (index, block) in blocks.iter().enumerate() {
        if let Some(node) = extract_hierarchy(block) {
            let label = format!("{:?}", node.level());
            let record =
                VectorRecord::try_new(&format!("block-{index}"), vec![0.5; 4], vec![]).unwrap();
            vector_store.store(&record).unwrap();

            let graph_node = GraphNode::try_new(&format!("block-{index}"), &label, vec![]).unwrap();
            graph_store.upsert_node(&graph_node).unwrap();
            stored_count += 1;
        }
    }
    assert!(stored_count > 0, "must have hierarchy annotations");

    let embedding = StubEmbedding;

    // FindSimilar
    let find_op = ValidatedOp::try_new(KnowQLOp::FindSimilar {
        vector: vec![0.5; 4],
        top_k: 10,
    })
    .unwrap();

    let result = execute(&find_op, &embedding, &vector_store, &graph_store).unwrap();
    match result {
        KnowQLResult::SimilarRecords { ids } => {
            assert!(!ids.is_empty());
            assert!(ids.len() <= 10);
        }
        _ => panic!("expected SimilarRecords"),
    }

    // FindByLabel: use the first stored label
    let first_label = blocks
        .iter()
        .find_map(extract_hierarchy)
        .map(|n| format!("{:?}", n.level()))
        .expect("at least one hierarchy node");
    let label_op = ValidatedOp::try_new(KnowQLOp::FindByLabel {
        label: first_label.clone(),
    })
    .unwrap();

    let label_result = execute(&label_op, &embedding, &vector_store, &graph_store).unwrap();
    match label_result {
        KnowQLResult::GraphNodes { labels } => {
            assert!(!labels.is_empty());
        }
        _ => panic!("expected GraphNodes"),
    }

    // Reference mentions composition
    let ref_count: usize = blocks
        .iter()
        .map(|b| extract_reference_mentions(b).len())
        .sum();
    assert!(ref_count > 0, "must have reference mentions");

    eprintln!(
        "M137_KNOWQL_INTEGRATION blocks={} hierarchy_stored={} references={}",
        blocks.len(),
        stored_count,
        ref_count
    );
}
