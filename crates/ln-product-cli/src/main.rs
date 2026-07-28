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
    domain::{fingerprint_bytes, DecodeRequest, FamilyFormat, ParagraphStyle, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
    references::extract_reference_mentions,
    temporal::extract_temporal_phrases,
    unknown_forms::census_unknown_forms,
};
use ln_query::knowql::{execute, KnowQLOp, KnowQLResult, ValidatedOp};
use ln_storage::{
    adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore},
    EmbeddingPort, EmbeddingRequest, EmbeddingResponse, GraphNode, GraphStorePort, StorageError,
    VectorRecord, VectorStorePort,
};

const BINARY: &str = "law-nexus-inspect";

struct StubEmbedding;
impl EmbeddingPort for StubEmbedding {
    fn embed(&self, req: &EmbeddingRequest) -> Result<EmbeddingResponse, StorageError> {
        Ok(
            EmbeddingResponse::try_new(req.model_id(), vec![0.5; req.expected_dimensions()])
                .unwrap(),
        )
    }
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn print_failure(phase: &str, kind: &str, message: &str) -> ! {
    println!(
        "{{\"phase\":\"{phase}\",\"status\":\"failed\",\"kind\":\"{kind}\",\"message\":\"{}\"}}",
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
        Err(e) => print_failure("Io", "ReadFailure", &e.to_string()),
    };
    let byte_count = bytes.len();
    let fingerprint = fingerprint_bytes(&bytes);

    let family = if path.to_lowercase().ends_with(".xml") {
        FamilyFormat::parse("family:consultant-wordml").unwrap()
    } else if path.to_lowercase().ends_with(".odt") {
        FamilyFormat::parse("family:garant-odt").unwrap()
    } else {
        print_failure("Parse", "UnsupportedFamily", path);
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
                )
            })
    } else {
        read_odt_content_xml(&request)
            .unwrap_or_else(|e| print_failure("Parse", "MalformedInput", &format!("ODT: {e}")));
        GarantOdtBlockDecoder
            .decode_blocks(&request)
            .unwrap_or_else(|e| {
                print_failure(
                    "Parse",
                    "MalformedInput",
                    &format!("{:?}: offset={:?}", e.kind(), e.byte_offset()),
                )
            })
    };

    let mut hierarchy_markers = 0usize;
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
        if extract_hierarchy(block).is_some() {
            hierarchy_markers += 1;
            let id = format!("block-{i}");
            let _ =
                vector_store.store(&VectorRecord::try_new(&id, vec![0.5; 4], Vec::new()).unwrap());
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
        vector: vec![0.5; 4],
        top_k: 5,
    })
    .unwrap();
    let retrieval_count = match execute(&op, &StubEmbedding, &vector_store, &graph_store) {
        Ok(KnowQLResult::SimilarRecords { ids }) => ids.len(),
        _ => 0,
    };

    let duration_ms = start.elapsed().as_millis();

    println!(
        "{{\"phase\":\"Inspect\",\"status\":\"ok\",\"binary\":\"{BINARY}\",\"runtime\":\"rust\",\
         \"duration_ms\":{duration_ms},\
         \"source\":{{\"path\":\"{}\",\"bytes\":{byte_count},\"fingerprint\":\"{fingerprint}\"}},\
         \"family\":\"{fid}\",\
         \"result\":{{\
         \"blocks\":{},\"hierarchy_markers\":{hierarchy_markers},\
         \"reference_mentions\":{reference_mentions},\
         \"temporal_phrases\":{temporal_phrases},\"deontic_lexemes\":{deontic_lexemes},\
         \"unknown_forms\":{unknown_forms},\"provider_comment_candidates\":{provider_comments},\
         \"retrieval_count\":{retrieval_count}\
         }},\
         \"non_claims\":[\"No legal correctness claim\",\"No citation authority claim\",\
         \"No corpus completeness claim\",\"No five-clock assignment claim\"]}}",
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
        _ => {
            eprintln!("usage: law-nexus-inspect <health|inspect <path>>");
            process::exit(2);
        }
    }
}
