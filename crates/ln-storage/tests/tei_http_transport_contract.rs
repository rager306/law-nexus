//! Live transport contract for `HttpEmbeddingTransport` (ADR-0015 / M215 S02).
//!
//! Uses an in-process `TcpListener` on an ephemeral loopback port. No external
//! service is contacted. Lifecycle: `[bounded]` transport contract.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

use ln_storage::adapters::tei::{EmbeddingTransport, TransportError};
use ln_storage::adapters::tei_http::HttpEmbeddingTransport;

const READ_TIMEOUT: Duration = Duration::from_secs(2);

fn transport(port: u16) -> HttpEmbeddingTransport {
    HttpEmbeddingTransport::try_new("127.0.0.1", port, "/embed", Duration::from_secs(2))
        .expect("valid transport config")
}

fn http_response(status: &str, body: &str) -> Vec<u8> {
    format!(
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )
    .into_bytes()
}

fn spawn_server<F>(handler: F) -> u16
where
    F: FnOnce(TcpStream) + Send + 'static,
{
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
    let port = listener.local_addr().expect("local addr").port();
    thread::spawn(move || {
        if let Ok((stream, _)) = listener.accept() {
            handler(stream);
        }
    });
    port
}

fn spawn_response_server(response: Vec<u8>) -> u16 {
    spawn_server(move |mut stream| {
        let _ = read_http_request(&mut stream);
        let _ = stream.write_all(&response);
        let _ = stream.flush();
    })
}

fn spawn_capture_server(response: Vec<u8>) -> (u16, mpsc::Receiver<String>) {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
    let port = listener.local_addr().expect("local addr").port();
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        if let Ok((mut stream, _)) = listener.accept() {
            let request = read_http_request(&mut stream);
            let _ = sender.send(request);
            let _ = stream.write_all(&response);
            let _ = stream.flush();
        }
    });
    (port, receiver)
}

/// Read one HTTP request, headers plus the full declared body.
fn read_http_request(stream: &mut TcpStream) -> String {
    let _ = stream.set_read_timeout(Some(READ_TIMEOUT));
    let mut buffer: Vec<u8> = Vec::new();
    let mut chunk = [0u8; 1024];
    loop {
        match stream.read(&mut chunk) {
            Ok(0) => break,
            Ok(read) => {
                buffer.extend_from_slice(&chunk[..read]);
                if let Some(header_end) = find_header_end(&buffer) {
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

fn find_header_end(buffer: &[u8]) -> Option<usize> {
    buffer.windows(4).position(|window| window == b"\r\n\r\n")
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

#[test]
fn happy_path_parses_first_vector() {
    let port = spawn_response_server(http_response("200 OK", "[[0.1, 0.2, 0.3]]"));
    let vector = transport(port)
        .embed_text("legal text")
        .expect("happy path vector");
    assert_eq!(vector.len(), 3);
    assert!((vector[0] - 0.1).abs() < 1e-6);
    assert!((vector[1] - 0.2).abs() < 1e-6);
    assert!((vector[2] - 0.3).abs() < 1e-6);
}

#[test]
fn parses_only_first_inner_array() {
    let port = spawn_response_server(http_response("200 OK", "[[1.0, 2.0], [3.0, 4.0]]"));
    let vector = transport(port).embed_text("text").expect("first array");
    assert_eq!(vector, vec![1.0, 2.0]);
}

#[test]
fn non_2xx_status_is_bad_response() {
    let port = spawn_response_server(http_response("500 Internal Server Error", "{}"));
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn malformed_http_is_bad_response() {
    let port = spawn_response_server(b"this is not an http response".to_vec());
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn non_utf8_response_is_bad_response() {
    let mut response = b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n".to_vec();
    response.extend_from_slice(&[0xff, 0xfe, 0xfd]);
    let port = spawn_response_server(response);
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn empty_response_is_bad_response() {
    let port = spawn_server(|mut stream| {
        let _ = read_http_request(&mut stream);
    });
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn truncated_body_is_bad_response() {
    let port =
        spawn_response_server(b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n[[0.1, 0.2".to_vec());
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn empty_vector_is_bad_response() {
    let port = spawn_response_server(http_response("200 OK", "[[]]"));
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn oversized_response_is_bad_response() {
    let port = spawn_server(move |mut stream| {
        let _ = read_http_request(&mut stream);
        let header = b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(header);
        // Stream well past the 8 MiB cap so the client refuses the response.
        let block = vec![b'a'; 64 * 1024];
        for _ in 0..140 {
            if stream.write_all(&block).is_err() {
                break;
            }
        }
        let _ = stream.flush();
    });
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::BadResponse(_))
    ));
}

#[test]
fn refused_connection_is_unavailable() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral loopback");
    let port = listener.local_addr().expect("local addr").port();
    drop(listener);
    assert!(matches!(
        transport(port).embed_text("text"),
        Err(TransportError::Unavailable)
    ));
}

#[test]
fn silent_server_is_timeout() {
    let port = spawn_server(|mut stream| {
        let _ = read_http_request(&mut stream);
        thread::sleep(Duration::from_secs(2));
    });
    let short =
        HttpEmbeddingTransport::try_new("127.0.0.1", port, "/embed", Duration::from_millis(200))
            .expect("valid transport config");
    assert!(matches!(
        short.embed_text("text"),
        Err(TransportError::Timeout)
    ));
}

#[test]
fn request_body_escapes_quotes_and_newlines() {
    let port_response = http_response("200 OK", "[[0.5]]");
    let (port, receiver) = spawn_capture_server(port_response);
    let text = "line1\nline2 \"quoted\" back\\slash";
    transport(port).embed_text(text).expect("happy path");
    let request = receiver
        .recv_timeout(Duration::from_secs(2))
        .expect("request captured");
    assert!(request.contains(r#"{"inputs":"line1\nline2 \"quoted\" back\\slash"}"#));
}

#[test]
fn constructor_rejects_invalid_config() {
    let timeout = Duration::from_secs(1);
    assert!(HttpEmbeddingTransport::try_new("", 80, "/embed", timeout).is_err());
    assert!(HttpEmbeddingTransport::try_new("   ", 80, "/embed", timeout).is_err());
    assert!(HttpEmbeddingTransport::try_new("127.0.0.1", 80, "", timeout).is_err());
    assert!(HttpEmbeddingTransport::try_new("127.0.0.1", 80, "embed", timeout).is_err());
    assert!(HttpEmbeddingTransport::try_new("127.0.0.1", 80, "/embed", Duration::ZERO).is_err());
}
