//! Fail-closed publication of text artifacts.
//!
//! Small, stdlib-only helper shared by the S04 corpus CLIs. It refuses to
//! publish through a symlinked parent or onto a symlinked target, refuses to
//! replace an existing regular file unless the caller explicitly opts in with
//! `force`, and writes atomically when replacement is allowed. Typed errors
//! name the offending path and the closed reason.
//!
//! Invariants:
//!
//! - the parent is created with `create_dir_all` when the lexical parent is
//!   non-empty, then canonicalised and rejected if any component is a symlink;
//! - the target is stat'ed with `symlink_metadata`, so a symlink is refused,
//!   never followed;
//! - a non-regular target (directory, fifo, device, ...) is refused;
//! - the default publication mode opens the canonical target with
//!   `create_new(true)`, so an existing regular file is refused atomically;
//! - the explicit `force` mode writes a `create_new(true)` temp file in the
//!   same canonical directory and `rename`s it over the target, so the link
//!   itself is replaced and no symlink is followed.

use std::fmt;
use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// Closed failure reasons for fail-closed artifact publication.
#[derive(Debug)]
pub enum ArtifactOutputError {
    /// The path has no final file-name component (for example `/` or `..`).
    MissingFileName { path: PathBuf },
    /// The parent directory could not be created.
    CreateParent { path: PathBuf, reason: String },
    /// A component of the parent path is a symlink.
    ParentSymlink { path: PathBuf, component: PathBuf },
    /// The parent path could not be canonicalised.
    ParentUnresolved { path: PathBuf, reason: String },
    /// The target exists and is a symlink; it is never followed.
    TargetSymlink { path: PathBuf },
    /// The target exists and is not a regular file.
    TargetNotRegularFile { path: PathBuf, kind: &'static str },
    /// The target already exists as a regular file and `force` was not set.
    TargetExists { path: PathBuf },
    /// The target metadata could not be read.
    TargetMetadata { path: PathBuf, reason: String },
    /// The target resolves somewhere other than the canonical parent join.
    TargetResolvedElsewhere {
        path: PathBuf,
        resolved: PathBuf,
        expected: PathBuf,
    },
    /// Writing the artifact failed.
    Write { path: PathBuf, reason: String },
    /// Atomically replacing an existing artifact failed.
    Replace { path: PathBuf, reason: String },
}

impl fmt::Display for ArtifactOutputError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingFileName { path } => write!(
                f,
                "refusing {}: output path has no file name",
                path.display()
            ),
            Self::CreateParent { path, reason } => write!(
                f,
                "refusing output: cannot create parent {}: {reason}",
                path.display()
            ),
            Self::ParentSymlink { path, component } => write!(
                f,
                "refusing output: parent {} has symlinked component {}",
                path.display(),
                component.display()
            ),
            Self::ParentUnresolved { path, reason } => write!(
                f,
                "refusing output: cannot resolve parent {}: {reason}",
                path.display()
            ),
            Self::TargetSymlink { path } => write!(
                f,
                "refusing {}: existing target is a symlink and is never followed",
                path.display()
            ),
            Self::TargetNotRegularFile { path, kind } => write!(
                f,
                "refusing {}: existing target is a {kind}, not a regular file",
                path.display()
            ),
            Self::TargetExists { path } => write!(
                f,
                "refusing {}: target already exists; pass --force to replace it",
                path.display()
            ),
            Self::TargetMetadata { path, reason } => write!(
                f,
                "refusing {}: cannot read target metadata: {reason}",
                path.display()
            ),
            Self::TargetResolvedElsewhere {
                path,
                resolved,
                expected,
            } => write!(
                f,
                "refusing {}: target resolves to {} instead of {}",
                path.display(),
                resolved.display(),
                expected.display()
            ),
            Self::Write { path, reason } => {
                write!(
                    f,
                    "refusing output: cannot write {}: {reason}",
                    path.display()
                )
            }
            Self::Replace { path, reason } => write!(
                f,
                "refusing output: cannot atomically replace {}: {reason}",
                path.display()
            ),
        }
    }
}

impl std::error::Error for ArtifactOutputError {}

/// Resolve a path to a comparison identity used for `--out`/`--sample`/sibling
/// collision checks. An existing target is canonicalised (so symlinks are
/// resolved to their destination); otherwise the canonical parent is joined
/// with the file name, and only a parent that does not exist falls back to the
/// absolute lexical path.
pub fn output_identity(path: &Path) -> Result<PathBuf, ArtifactOutputError> {
    let file_name = path
        .file_name()
        .ok_or_else(|| ArtifactOutputError::MissingFileName {
            path: path.to_path_buf(),
        })?;
    if fs::symlink_metadata(path).is_ok() {
        if let Ok(canonical) = fs::canonicalize(path) {
            return Ok(canonical);
        }
    }
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty());
    if let Some(parent) = parent {
        if let Ok(canonical_parent) = fs::canonicalize(parent) {
            return Ok(canonical_parent.join(file_name));
        }
    }
    if path.is_absolute() {
        return Ok(path.to_path_buf());
    }
    let current =
        std::env::current_dir().map_err(|error| ArtifactOutputError::ParentUnresolved {
            path: path.to_path_buf(),
            reason: error.to_string(),
        })?;
    Ok(current.join(path))
}

/// Verify that the target can be published with the given replacement policy
/// and return the canonical target path to write into. The parent is created
/// when the lexical parent is non-empty, every parent component is rejected
/// when it is a symlink, and an existing target is checked with
/// `symlink_metadata` so a symlink is refused rather than followed.
pub fn preflight_publish_target(path: &Path, force: bool) -> Result<PathBuf, ArtifactOutputError> {
    let file_name = path
        .file_name()
        .ok_or_else(|| ArtifactOutputError::MissingFileName {
            path: path.to_path_buf(),
        })?;
    let lexical_parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty());
    let parent = lexical_parent.unwrap_or_else(|| Path::new("."));
    if lexical_parent.is_some() {
        fs::create_dir_all(parent).map_err(|error| ArtifactOutputError::CreateParent {
            path: parent.to_path_buf(),
            reason: error.to_string(),
        })?;
    }
    ensure_parent_has_no_symlink(parent)?;
    let canonical_parent =
        fs::canonicalize(parent).map_err(|error| ArtifactOutputError::ParentUnresolved {
            path: parent.to_path_buf(),
            reason: error.to_string(),
        })?;
    let resolved = canonical_parent.join(file_name);
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err(ArtifactOutputError::TargetSymlink {
                path: path.to_path_buf(),
            });
        }
        Ok(metadata) if !metadata.is_file() => {
            return Err(ArtifactOutputError::TargetNotRegularFile {
                path: path.to_path_buf(),
                kind: file_kind(&metadata),
            });
        }
        Ok(_) => {
            if !force {
                return Err(ArtifactOutputError::TargetExists {
                    path: path.to_path_buf(),
                });
            }
            let canonical_target =
                fs::canonicalize(path).map_err(|error| ArtifactOutputError::TargetMetadata {
                    path: path.to_path_buf(),
                    reason: error.to_string(),
                })?;
            if canonical_target != resolved {
                return Err(ArtifactOutputError::TargetResolvedElsewhere {
                    path: path.to_path_buf(),
                    resolved: canonical_target,
                    expected: resolved,
                });
            }
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => {
            return Err(ArtifactOutputError::TargetMetadata {
                path: path.to_path_buf(),
                reason: error.to_string(),
            });
        }
    }
    Ok(resolved)
}

/// Publish `text` to `path` fail-closed. See the module docs for the refused
/// cases and the replacement policy selected by `force`.
pub fn publish_text_artifact(
    path: &Path,
    text: &str,
    force: bool,
) -> Result<(), ArtifactOutputError> {
    let resolved = preflight_publish_target(path, force)?;
    if force {
        replace_text(&resolved, text)
    } else {
        create_text(&resolved, text)
    }
}

fn create_text(resolved: &Path, text: &str) -> Result<(), ArtifactOutputError> {
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(resolved)
        .map_err(|error| ArtifactOutputError::Write {
            path: resolved.to_path_buf(),
            reason: error.to_string(),
        })?;
    file.write_all(text.as_bytes())
        .map_err(|error| ArtifactOutputError::Write {
            path: resolved.to_path_buf(),
            reason: error.to_string(),
        })?;
    file.flush().map_err(|error| ArtifactOutputError::Write {
        path: resolved.to_path_buf(),
        reason: error.to_string(),
    })
}

fn replace_text(resolved: &Path, text: &str) -> Result<(), ArtifactOutputError> {
    let temp = temporary_sibling(resolved);
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(|error| ArtifactOutputError::Write {
            path: temp.clone(),
            reason: error.to_string(),
        })?;
    let write_result = file.write_all(text.as_bytes());
    drop(file);
    if let Err(error) = write_result {
        let _ = fs::remove_file(&temp);
        return Err(ArtifactOutputError::Write {
            path: temp,
            reason: error.to_string(),
        });
    }
    fs::rename(&temp, resolved).map_err(|error| {
        let _ = fs::remove_file(&temp);
        ArtifactOutputError::Replace {
            path: resolved.to_path_buf(),
            reason: error.to_string(),
        }
    })
}

fn temporary_sibling(resolved: &Path) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or(0);
    let name = resolved
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_else(|| "artifact".to_owned());
    resolved.with_file_name(format!(".{name}.tmp-{}-{nonce}", std::process::id()))
}

fn ensure_parent_has_no_symlink(parent: &Path) -> Result<(), ArtifactOutputError> {
    let mut prefix = PathBuf::new();
    for component in parent.components() {
        prefix.push(component.as_os_str());
        match fs::symlink_metadata(&prefix) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err(ArtifactOutputError::ParentSymlink {
                    path: parent.to_path_buf(),
                    component: prefix,
                });
            }
            Ok(_) | Err(_) => {}
        }
    }
    Ok(())
}

fn file_kind(metadata: &fs::Metadata) -> &'static str {
    let file_type = metadata.file_type();
    if file_type.is_dir() {
        "directory"
    } else if file_type.is_symlink() {
        "symlink"
    } else if file_type.is_file() {
        "regular file"
    } else {
        "special file"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock is after the epoch")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!(
            "ln-artifact-output-{tag}-{}-{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&dir).expect("temp dir is creatable");
        dir
    }

    #[test]
    fn creates_missing_parent_and_writes_regular_file() {
        let dir = temp_dir("create");
        let target = dir.join("nested/deeper/report.json");
        publish_text_artifact(&target, "payload", false).expect("publication succeeds");
        assert_eq!(fs::read_to_string(&target).expect("readable"), "payload");
        assert!(fs::symlink_metadata(&target).expect("metadata").is_file());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn refuses_existing_target_without_force() {
        let dir = temp_dir("existing");
        let target = dir.join("report.json");
        fs::write(&target, b"original").expect("seed");
        let error = publish_text_artifact(&target, "replacement", false)
            .expect_err("existing target must be refused");
        assert!(matches!(error, ArtifactOutputError::TargetExists { .. }));
        assert_eq!(fs::read(&target).expect("readable"), b"original");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn replaces_existing_target_with_force() {
        let dir = temp_dir("force");
        let target = dir.join("report.json");
        fs::write(&target, b"original").expect("seed");
        publish_text_artifact(&target, "replacement", true).expect("forced publication succeeds");
        assert_eq!(
            fs::read_to_string(&target).expect("readable"),
            "replacement"
        );
        assert!(fs::symlink_metadata(&target).expect("metadata").is_file());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn refuses_non_regular_target() {
        let dir = temp_dir("directory-target");
        let target = dir.join("a-directory");
        fs::create_dir_all(&target).expect("directory");
        let error = publish_text_artifact(&target, "payload", true)
            .expect_err("a directory target must be refused");
        assert!(matches!(
            error,
            ArtifactOutputError::TargetNotRegularFile { .. }
        ));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn output_identity_matches_canonical_target() {
        let dir = temp_dir("identity");
        let target = dir.join("report.json");
        fs::write(&target, b"x").expect("seed");
        assert_eq!(
            output_identity(&target).expect("identity"),
            fs::canonicalize(&target).expect("canonical")
        );
        let _ = fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[test]
    fn refuses_symlink_target_and_preserves_destination() {
        use std::os::unix::fs::symlink;
        let dir = temp_dir("symlink-target");
        let destination = dir.join("destination.json");
        fs::write(&destination, b"untouched").expect("destination");
        let link = dir.join("report.json");
        symlink(&destination, &link).expect("symlink");
        let error = publish_text_artifact(&link, "payload", true)
            .expect_err("a symlink target must be refused even with force");
        assert!(matches!(error, ArtifactOutputError::TargetSymlink { .. }));
        assert_eq!(fs::read(&destination).expect("readable"), b"untouched");
        assert!(fs::symlink_metadata(&link)
            .expect("metadata")
            .file_type()
            .is_symlink());
        let _ = fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[test]
    fn refuses_symlinked_parent_and_writes_nothing() {
        use std::os::unix::fs::symlink;
        let dir = temp_dir("symlink-parent");
        let real = dir.join("real");
        fs::create_dir_all(&real).expect("real dir");
        let link = dir.join("linkdir");
        symlink(&real, &link).expect("symlink");
        let target = link.join("report.json");
        let error = publish_text_artifact(&target, "payload", false)
            .expect_err("a symlinked parent must be refused");
        assert!(matches!(error, ArtifactOutputError::ParentSymlink { .. }));
        assert!(!real.join("report.json").exists());
        let _ = fs::remove_dir_all(&dir);
    }
}
