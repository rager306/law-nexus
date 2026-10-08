//! Standard-library-only HTTP transport for the TEI embedding service.
//!
//! This module provides a real, live `EmbeddingTransport` implementation built
//! entirely on `std` (`TcpStream`, bounded reads, explicit timeouts). It performs
//! no external service calls by itself — callers decide whether to point it at a
//! real endpoint or an in-process test server.
//!
//! Lifecycle: `[bounded]` transport surface. The presence of an HTTP surface does
//! not assert that a live TEI endpoint was contacted or validated.
//!
//! Fail-closed discipline: every failure maps to a closed `TransportError`
//! category (`Unavailable`, `Timeout`, `BadResponse`). Error messages never carry
//! raw server payloads or legal text.

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;

use super::tei::{EmbeddingTransport, TransportError};

/// Hard cap on the number of response bytes accepted from the server.
const MAX_RESPONSE_BYTES: usize = 8 * 1024 * 1024;

/// Live HTTP transport for a TEI-compatible `/embed`-style endpoint.
///
/// The transport is deliberately synchronous and timeout-bounded. It sends a
/// single `POST` request with a JSON `{"inputs":"..."}` body and parses the
/// first inner numeric array of the TEI response (`[[f32, ...]]`).
#[derive(Debug, Clone)]
pub struct HttpEmbeddingTransport {
    host: String,
    port: u16,
    path: String,
    timeout: Duration,
}

impl HttpEmbeddingTransport {
    /// Build a transport for `host:port` at `path`, using `timeout` for the
    /// connect, read, and write operations.
    ///
    /// Rejects an empty host, an empty path, a path without a leading `/`, and a
    /// zero timeout. No panic path.
    pub fn try_new(
        host: &str,
        port: u16,
        path: &str,
        timeout: Duration,
    ) -> Result<Self, TransportError> {
        if host.trim().is_empty() {
            return Err(TransportError::BadResponse("empty host".to_owned()));
        }
        if path.trim().is_empty() {
            return Err(TransportError::BadResponse("empty path".to_owned()));
        }
        if !path.starts_with('/') {
            return Err(TransportError::BadResponse(
                "path must start with slash".to_owned(),
            ));
        }
        if timeout.is_zero() {
            return Err(TransportError::BadResponse("zero timeout".to_owned()));
        }
        Ok(Self {
            host: host.to_owned(),
            port,
            path: path.to_owned(),
            timeout,
        })
    }
}

impl EmbeddingTransport for HttpEmbeddingTransport {
    fn embed_text(&self, text: &str) -> Result<Vec<f32>, TransportError> {
        let body = format!("{{\"inputs\":\"{}\"}}", json_escape(text));
        let request = format!(
            "POST {path} HTTP/1.1\r\nHost: {host}:{port}\r\nContent-Type: application/json\r\nContent-Length: {length}\r\nConnection: close\r\n\r\n{body}",
            path = self.path,
            host = self.host,
            port = self.port,
            length = body.len(),
            body = body,
        );

        let address = resolve_address(&self.host, self.port)?;
        let mut stream =
            TcpStream::connect_timeout(&address, self.timeout).map_err(map_io_error)?;
        stream
            .set_read_timeout(Some(self.timeout))
            .map_err(map_io_error)?;
        stream
            .set_write_timeout(Some(self.timeout))
            .map_err(map_io_error)?;

        stream.write_all(request.as_bytes()).map_err(map_io_error)?;
        stream.flush().map_err(map_io_error)?;

        let response = read_bounded(&mut stream)?;
        parse_response(&response)
    }
}

/// Resolve `host:port` to a socket address. Any resolution failure is treated as
/// an unreachable service.
fn resolve_address(host: &str, port: u16) -> Result<SocketAddr, TransportError> {
    (host, port)
        .to_socket_addrs()
        .map_err(|_| TransportError::Unavailable)?
        .next()
        .ok_or(TransportError::Unavailable)
}

/// Read the response body/headers until EOF, refusing anything larger than the
/// bounded cap.
fn read_bounded(stream: &mut TcpStream) -> Result<Vec<u8>, TransportError> {
    let mut buffer: Vec<u8> = Vec::new();
    let mut chunk = [0u8; 8192];
    loop {
        match stream.read(&mut chunk) {
            Ok(0) => break,
            Ok(read) => {
                if buffer.len() + read > MAX_RESPONSE_BYTES {
                    return Err(TransportError::BadResponse("response too large".to_owned()));
                }
                buffer.extend_from_slice(&chunk[..read]);
            }
            Err(error) => return Err(map_io_error(error)),
        }
    }
    if buffer.is_empty() {
        return Err(TransportError::BadResponse("empty response".to_owned()));
    }
    Ok(buffer)
}

/// Parse a full HTTP/1.1 response into the first TEI embedding vector.
fn parse_response(response: &[u8]) -> Result<Vec<f32>, TransportError> {
    let text = std::str::from_utf8(response)
        .map_err(|_| TransportError::BadResponse("non utf8 response".to_owned()))?;
    let (headers, body) = text
        .split_once("\r\n\r\n")
        .ok_or_else(|| TransportError::BadResponse("malformed http response".to_owned()))?;
    let status_line = headers
        .lines()
        .next()
        .ok_or_else(|| TransportError::BadResponse("missing status line".to_owned()))?;
    let status = parse_status_code(status_line)?;
    if !(200..300).contains(&status) {
        return Err(TransportError::BadResponse(format!("http status {status}")));
    }
    parse_tei_vector(body)
}

/// Extract the status code from an HTTP status line (`HTTP/1.1 200 OK`).
fn parse_status_code(status_line: &str) -> Result<u16, TransportError> {
    let mut parts = status_line.split_whitespace();
    let _version = parts
        .next()
        .ok_or_else(|| TransportError::BadResponse("missing status line".to_owned()))?;
    let code = parts
        .next()
        .ok_or_else(|| TransportError::BadResponse("missing status code".to_owned()))?;
    code.parse::<u16>()
        .map_err(|_| TransportError::BadResponse("invalid status code".to_owned()))
}

/// Parse the first inner numeric array of a TEI-style JSON response
/// (`[[f32, ...], ...]`) without a JSON dependency.
fn parse_tei_vector(body: &str) -> Result<Vec<f32>, TransportError> {
    let bytes = body.as_bytes();
    let len = bytes.len();
    let mut index = 0;

    skip_whitespace(bytes, &mut index);
    if index >= len || bytes[index] != b'[' {
        return Err(TransportError::BadResponse(
            "expected json array".to_owned(),
        ));
    }
    index += 1;

    skip_whitespace(bytes, &mut index);
    if index >= len || bytes[index] != b'[' {
        return Err(TransportError::BadResponse(
            "expected inner array".to_owned(),
        ));
    }
    index += 1;

    let mut vector: Vec<f32> = Vec::new();
    loop {
        skip_whitespace(bytes, &mut index);
        if index >= len {
            return Err(TransportError::BadResponse("truncated array".to_owned()));
        }
        if bytes[index] == b']' {
            break;
        }

        let start = index;
        while index < len && is_float_byte(bytes[index]) {
            index += 1;
        }
        if index == start {
            return Err(TransportError::BadResponse(
                "invalid numeric token".to_owned(),
            ));
        }
        let token = &body[start..index];
        let value = token
            .parse::<f32>()
            .map_err(|_| TransportError::BadResponse("invalid float".to_owned()))?;
        vector.push(value);

        skip_whitespace(bytes, &mut index);
        if index >= len {
            return Err(TransportError::BadResponse("truncated array".to_owned()));
        }
        match bytes[index] {
            b',' => index += 1,
            b']' => break,
            _ => {
                return Err(TransportError::BadResponse(
                    "unexpected numeric separator".to_owned(),
                ))
            }
        }
    }

    if vector.is_empty() {
        return Err(TransportError::BadResponse("empty vector".to_owned()));
    }
    Ok(vector)
}

fn skip_whitespace(bytes: &[u8], index: &mut usize) {
    while *index < bytes.len() && bytes[*index].is_ascii_whitespace() {
        *index += 1;
    }
}

fn is_float_byte(byte: u8) -> bool {
    byte.is_ascii_digit() || matches!(byte, b'-' | b'+' | b'.' | b'e' | b'E')
}

/// Minimal JSON string escaping: quotes, backslash, and control characters.
fn json_escape(text: &str) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut escaped = String::with_capacity(text.len());
    for ch in text.chars() {
        match ch {
            '"' => escaped.push_str("\\\""),
            '\\' => escaped.push_str("\\\\"),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            control if (control as u32) < 0x20 => {
                let value = control as u32;
                escaped.push('\\');
                escaped.push('u');
                escaped.push('0');
                escaped.push('0');
                escaped.push(HEX[((value >> 4) & 0x0f) as usize] as char);
                escaped.push(HEX[(value & 0x0f) as usize] as char);
            }
            other => escaped.push(other),
        }
    }
    escaped
}

/// Map an `io::Error` to a closed transport category.
fn map_io_error(error: std::io::Error) -> TransportError {
    match error.kind() {
        std::io::ErrorKind::ConnectionRefused
        | std::io::ErrorKind::NotConnected
        | std::io::ErrorKind::AddrNotAvailable => TransportError::Unavailable,
        std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut => TransportError::Timeout,
        _ => TransportError::BadResponse("io failure".to_owned()),
    }
}
