//! End-to-end live TEI path with provenance (ADR-0015 / M215 S02).
//!
//! Composes the real transport chain
//! `HttpEmbeddingTransport -> TeiEmbeddingAdapter -> ProvenancedEmbedding`
//! against an in-process TEI-shaped HTTP server on ephemeral loopback and runs
//! the shared `assert_embedding_artifact_port_contract` suite. Then proves the
//! fail-closed demo: with no reachable endpoint the live path returns a closed
//! `StorageError::TransportUnavailable` and yields no artifact rather than
//! panicking or inventing a vector.
//!
//! No external service is contacted. Lifecycle: `[bounded]` live-path contract.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;

use ln_storage::adapters::tei::TeiEmbeddingAdapter;
use ln_storage::adapters::tei_http::HttpEmbeddingTransport;
use ln_storage::{
    EmbeddingArtifactPort, EmbeddingArtifactRequest, ModelProvenance, ProvenancedEmbedding,
    StorageError,
};
use ln_testkit::assert_embedding_artifact_port_contract;

const MODEL_ID: &str = "tei-live-contract-model";
const DIMENSIONS: usize = 4;
const READ_TIMEOUT: Duration = Duration::from_secs(2);

/// Deterministic finite vector of `DIMENSIONS` values used by the fake server.
fn server_vector() -> Vec<f32> {
    (0..DIMENSIONS).map(|i| (i as f32) * 0.25).collect()
}

/// Provenance bound to the live path, dimensions aligned with `DIMENSIONS`.
fn provenance() -> ModelProvenance {
    ModelProvenance::try_new(
        "https://example.invalid/tei-live-contract",
        "Apache-2.0",
        &format!("sha256:{}", "b".repeat(64)),
        DIMENSIONS,
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ],
    )
    .expect("valid provenance")
}

/// Build the full live composition pointing at `port`.
fn live_port(port: u16) -> ProvenancedEmbedding<TeiEmbeddingAdapter<HttpEmbeddingTransport>> {
    let transport =
        HttpEmbeddingTransport::try_new("127.0.0.1", port, "/embed", Duration::from_secs(2))
            .expect("valid transport config");
    let adapter =
        TeiEmbeddingAdapter::try_new(transport, MODEL_ID, DIMENSIONS).expect("valid tei adapter");
    ProvenancedEmbedding::try_new(adapter, MODEL_ID, provenance()).expect("valid composition")
}

fn artifact_request() -> EmbeddingArtifactRequest {
    EmbeddingArtifactRequest::try_new("doc-live-1", "live legal text").expect("valid request")
}

/// Read one HTTP request (headers plus declared body) from the server side.
fn read_http_request(stream: &mut TcpStream) -> String {
    let _ = stream.set_read_timeout(Some(READ_TIMEOUT));
    let mut buffer: Vec<u8> = Vec::new();
    let mut chunk = [0u8; 1024];
    loop {
        match stream.read(&mut chunk) {
            Ok(0) => break,
            Ok(read) => {
                buffer.extend_from_slice(&chunk[..read]);
                if let Some(header_end) = buffer.windows(4).position(|w| w == b"\r\n\r\n") {
                    let header_text = String::from_utf8_lossy(&buffer[..header_end]).to_string();
                    if buffer.len() >= header_end + 4 + content_length_of(&header_text) {
                        break;
                    }
                }
            }
            Err(_) => break,
        }
    }
    String::from_utf8_lossy(&buffer).to_string()
}

fn content_length_of(headers: &str) -> usize {
    headers
        .lines()
        .find_map(|line| {
            let (name, value) = line.split_once(':')?;
            if name.eq_ignore_ascii_case("content-length") {
                value.trim().parse::<usize>().ok()
            } else {
                None
            }
        })
        .unwrap_or(0)
}

fn http_response(status: &str, body: &str) -> Vec<u8> {
    format!(
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )
    .into_bytes()
}

/// Spawn an in-process server answering a single connection with `response`.
fn spawn_response_server(response: Vec<u8>) -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
    let port = listener.local_addr().expect("local addr").port();
    thread::spawn(move || {
        if let Ok((mut stream, _)) = listener.accept() {
            let _ = read_http_request(&mut stream);
            let _ = stream.write_all(&response);
            let _ = stream.flush();
        }
    });
    port
}

/// Spawn an in-process TEI-shaped server returning a `[[...]]` vector body.
fn spawn_vector_server() -> u16 {
    let body = format!(
        "[[{}]]",
        server_vector()
            .iter()
            .map(|value| value.to_string())
            .collect::<Vec<_>>()
            .join(", ")
    );
    spawn_response_server(http_response("200 OK", &body))
}

/// Reserve and immediately release an ephemeral port so nothing is listening.
fn unused_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
    let port = listener.local_addr().expect("local addr").port();
    drop(listener);
    port
}

#[test]
fn live_tei_path_satisfies_shared_artifact_contract() {
    let port = spawn_vector_server();
    let live = live_port(port);
    assert_embedding_artifact_port_contract(&live, MODEL_ID, DIMENSIONS);
}

#[test]
fn live_tei_path_yields_populated_provenance() {
    let port = spawn_vector_server();
    let artifact = live_port(port)
        .embed_artifact(&artifact_request())
        .expect("live server must yield an artifact");
    assert_eq!(artifact.subject_ref(), "doc-live-1");
    assert_eq!(artifact.dimensions(), DIMENSIONS);
    assert_eq!(artifact.vector(), server_vector().as_slice());
    assert_eq!(artifact.provenance().license(), "Apache-2.0");
    assert!(artifact
        .provenance()
        .weights_sha256()
        .starts_with("sha256:"));
    assert_eq!(artifact.provenance().dimensions(), DIMENSIONS);
    assert!(!artifact.provenance().parameters().is_empty());
}

#[test]
fn live_tei_path_without_endpoint_fails_closed_unavailable() {
    let live = live_port(unused_port());
    let result = live.embed_artifact(&artifact_request());
    assert!(
        matches!(result, Err(StorageError::TransportUnavailable)),
        "unreachable endpoint must fail closed as TransportUnavailable, got {result:?}"
    );
}

#[test]
fn live_tei_path_non_2xx_fails_closed_bad_response() {
    let port = spawn_response_server(http_response("503 Service Unavailable", "{}"));
    let result = live_port(port).embed_artifact(&artifact_request());
    assert!(
        matches!(result, Err(StorageError::TransportBadResponse)),
        "non-2xx response must fail closed as TransportBadResponse, got {result:?}"
    );
}

#[test]
fn live_tei_path_wrong_dimension_fails_closed() {
    let port = spawn_response_server(http_response("200 OK", "[[0.5]]"));
    let result = live_port(port).embed_artifact(&artifact_request());
    assert!(
        matches!(result, Err(StorageError::DimensionMismatch { .. })),
        "declared-dimension drift must fail closed, got {result:?}"
    );
}
