//! Atomic filesystem publication for a rendered cleaned-projection artifact.
//!
//! `cleaned_wire::write_cleaned_projection` writes to a caller-supplied writer
//! and never touches the filesystem; this module adds the named publication
//! surface the S04 demo needs. It mirrors the established
//! `npa_bounds::write_out_atomic` pattern: the payload lands in `<path>.tmp`
//! in the same directory and a single `rename` replaces the published file, so
//! a reader sees either the previous artifact or the new one, never a
//! half-written document.
//!
//! Only atomic **visibility** is claimed. No `fsync` is issued and no
//! durability guarantee is made: after a crash the rename may or may not have
//! reached stable storage. The success path removes nothing it did not create;
//! on any failure the temporary file is removed.
//!
//! This module is dependency-free: `std` plus the frozen
//! [`crate::cleaned_wire`] error vocabulary only.

use std::fs;
use std::path::{Path, PathBuf};

use crate::cleaned_wire::{WireError, WireErrorKind};

/// Atomically publishes `artifact` at `path`.
///
/// The rendered bytes are written to a sibling `<path>.tmp`, then `rename`d
/// onto `path`. On any write or rename failure the temporary file is removed
/// and a closed [`WireErrorKind::WriteFailed`] refusal is returned; no partial
/// document is ever left at `path`.
///
/// `artifact` is an already-rendered cleaned-projection document (for example
/// the output of [`crate::cleaned_wire::export_cleaned_projection`]); this
/// function does not re-validate it, so callers that need a read-back guarantee
/// should export and verify first.
pub fn write_cleaned_projection_atomic(path: &Path, artifact: &str) -> Result<(), WireError> {
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
    let result = fs::write(&tmp, artifact).and_then(|()| fs::rename(&tmp, path));
    match result {
        Ok(()) => Ok(()),
        Err(error) => {
            let _ = fs::remove_file(&tmp);
            Err(WireError::new(
                WireErrorKind::WriteFailed,
                format!("atomic publish to {} failed: {error}", path.display()),
            ))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cleaned_wire::{
        export_cleaned_projection, read_cleaned_wire, IncompleteReason, WireCompletion, WireLimits,
    };
    use crate::reader_projection::build_projection;
    use crate::source_package::{capture, Limits};

    const FIXTURE: &str = "<w:wordDocument \
        xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\">\
        <w:body><w:p><w:r><w:t>Alpha</w:t></w:r></w:p></w:body></w:wordDocument>";

    fn artifact(completion: WireCompletion) -> String {
        let package =
            capture(FIXTURE.as_bytes(), &Limits::default()).expect("fixture must capture");
        let projection = build_projection(package.records()).expect("fixture must project");
        export_cleaned_projection(&package, &projection, &completion, &WireLimits::default())
            .expect("fixture must export")
    }

    fn complete() -> String {
        artifact(WireCompletion::Complete)
    }

    fn hold() -> String {
        artifact(WireCompletion::Incomplete {
            basis: IncompleteReason::Hold,
            reasons: vec![IncompleteReason::Hold],
        })
    }

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "ln-decode-cleaned-publish-{}-{tag}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).expect("temp dir must be creatable");
        dir
    }

    fn has_tmp(dir: &Path) -> bool {
        fs::read_dir(dir)
            .expect("read dir")
            .filter_map(Result::ok)
            .any(|entry| entry.file_name().to_string_lossy().ends_with(".tmp"))
    }

    #[test]
    fn publish_creates_a_readable_file() {
        let dir = temp_dir("create");
        let path = dir.join("artifact.jsonl");
        write_cleaned_projection_atomic(&path, &complete()).expect("publish must succeed");
        let text = fs::read_to_string(&path).expect("published file must be readable");
        let readback = read_cleaned_wire(&text).expect("published artifact must read back");
        assert_eq!(readback.completion, WireCompletion::Complete);
        assert!(!has_tmp(&dir), "successful publish must leave no *.tmp");
    }

    #[test]
    fn republish_replaces_the_previous_artifact() {
        let dir = temp_dir("replace");
        let path = dir.join("artifact.jsonl");
        write_cleaned_projection_atomic(&path, &complete()).expect("first publish");
        write_cleaned_projection_atomic(&path, &hold()).expect("second publish");
        let text = fs::read_to_string(&path).expect("published file must be readable");
        let readback = read_cleaned_wire(&text).expect("published artifact must read back");
        assert_eq!(
            readback.completion,
            WireCompletion::Incomplete {
                basis: IncompleteReason::Hold,
                reasons: vec![IncompleteReason::Hold],
            },
            "republish must replace the previous artifact"
        );
        assert!(!has_tmp(&dir), "successful republish must leave no *.tmp");
    }

    #[test]
    fn missing_parent_directory_is_write_failed_without_tmp() {
        let dir = temp_dir("missing-parent");
        let missing = dir.join("absent");
        let path = missing.join("artifact.jsonl");
        let error = write_cleaned_projection_atomic(&path, &complete())
            .expect_err("a missing parent must refuse");
        assert_eq!(error.kind(), WireErrorKind::WriteFailed);
        let tmp = PathBuf::from(format!("{}.tmp", path.display()));
        assert!(!tmp.exists(), "a refused publish must leave no *.tmp");
        assert!(!path.exists(), "a refused publish must publish nothing");
    }
}
