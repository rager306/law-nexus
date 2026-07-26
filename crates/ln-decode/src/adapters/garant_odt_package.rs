//! Bounded in-memory package intake for Garant ODT artifacts.
//!
//! This module does not parse XML and never extracts archive entries to the
//! filesystem. It returns only the unique bounded `content.xml` payload.

use std::io::{Cursor, Read};

use zip::ZipArchive;

use crate::domain::{BlockDecodeError, BlockDecodeErrorKind, DecodePhase, DecodeRequest};

pub const MAX_ODT_PACKAGE_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_ODT_ENTRIES: usize = 16;
pub const MAX_CONTENT_XML_BYTES: usize = 8 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OdtPackageContent {
    bytes: Vec<u8>,
    entry_count: usize,
}

impl OdtPackageContent {
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }

    pub const fn entry_count(&self) -> usize {
        self.entry_count
    }
}

pub fn read_odt_content_xml(
    request: &DecodeRequest,
) -> Result<OdtPackageContent, BlockDecodeError> {
    if request.family_format.as_str() != "family:garant-odt" {
        return Err(error(
            DecodePhase::Input,
            BlockDecodeErrorKind::UnsupportedFormat,
        ));
    }
    if request.bytes.len() > MAX_ODT_PACKAGE_BYTES {
        return Err(package_error(BlockDecodeErrorKind::PackageLimitExceeded));
    }

    let declared_entry_count = declared_entry_count(&request.bytes)?;
    if declared_entry_count > MAX_ODT_ENTRIES {
        return Err(package_error(BlockDecodeErrorKind::PackageLimitExceeded));
    }

    let mut archive = ZipArchive::new(Cursor::new(request.bytes.as_slice()))
        .map_err(|_| package_error(BlockDecodeErrorKind::InvalidPackage))?;
    let entry_count = archive.len();
    if entry_count != declared_entry_count {
        return Err(package_error(BlockDecodeErrorKind::DuplicatePackageEntry));
    }

    let mut content = None;
    for index in 0..entry_count {
        let mut entry = archive
            .by_index(index)
            .map_err(|_| package_error(BlockDecodeErrorKind::InvalidPackage))?;
        if entry.enclosed_name().is_none() {
            return Err(package_error(BlockDecodeErrorKind::UnsafePackageEntry));
        }
        if entry.name() != "content.xml" {
            continue;
        }
        if content.is_some() {
            return Err(package_error(BlockDecodeErrorKind::DuplicatePackageEntry));
        }
        if entry.is_dir() {
            return Err(package_error(BlockDecodeErrorKind::InvalidPackage));
        }
        if entry.size() > MAX_CONTENT_XML_BYTES as u64 {
            return Err(package_error(BlockDecodeErrorKind::PackageLimitExceeded));
        }

        let mut bytes = Vec::with_capacity(entry.size() as usize);
        (&mut entry)
            .take((MAX_CONTENT_XML_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|_| package_error(BlockDecodeErrorKind::InvalidPackage))?;
        if bytes.len() > MAX_CONTENT_XML_BYTES {
            return Err(package_error(BlockDecodeErrorKind::PackageLimitExceeded));
        }
        content = Some(bytes);
    }

    let bytes = content.ok_or_else(|| package_error(BlockDecodeErrorKind::MissingContentXml))?;
    Ok(OdtPackageContent { bytes, entry_count })
}

fn declared_entry_count(bytes: &[u8]) -> Result<usize, BlockDecodeError> {
    const EOCD_SIGNATURE: [u8; 4] = [0x50, 0x4b, 0x05, 0x06];
    const EOCD_LEN: usize = 22;
    const MAX_COMMENT_LEN: usize = u16::MAX as usize;

    let search_start = bytes.len().saturating_sub(EOCD_LEN + MAX_COMMENT_LEN);
    for (relative, window) in bytes[search_start..]
        .windows(EOCD_SIGNATURE.len())
        .enumerate()
        .rev()
    {
        if window != EOCD_SIGNATURE {
            continue;
        }
        let start = search_start + relative;
        let Some(record) = bytes.get(start..start + EOCD_LEN) else {
            continue;
        };
        let comment_len = u16::from_le_bytes([record[20], record[21]]) as usize;
        if start + EOCD_LEN + comment_len != bytes.len() {
            continue;
        }

        let disk = u16::from_le_bytes([record[4], record[5]]);
        let central_disk = u16::from_le_bytes([record[6], record[7]]);
        let entries_on_disk = u16::from_le_bytes([record[8], record[9]]);
        let entries_total = u16::from_le_bytes([record[10], record[11]]);
        if disk != 0
            || central_disk != 0
            || entries_on_disk != entries_total
            || entries_total == u16::MAX
        {
            return Err(package_error(BlockDecodeErrorKind::InvalidPackage));
        }
        return Ok(entries_total as usize);
    }
    Err(package_error(BlockDecodeErrorKind::InvalidPackage))
}

const fn package_error(kind: BlockDecodeErrorKind) -> BlockDecodeError {
    error(DecodePhase::Package, kind)
}

const fn error(phase: DecodePhase, kind: BlockDecodeErrorKind) -> BlockDecodeError {
    BlockDecodeError::new(phase, kind, None)
}
