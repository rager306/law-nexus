//! Honest, source-root-relative corpus metadata for bounded sampling.
//!
//! This module deliberately does not inspect document contents.  A path is
//! evidence only for the bounded filename/export-family vocabulary below;
//! unknown shapes stay unknown rather than being guessed from hashes or the
//! absolute checkout path.
use std::path::{Component, Path, PathBuf};

pub const DEFAULT_DRAW_SEED: u64 = 20_308;
pub const MIN_CALENDAR_YEAR: u16 = 1991;
pub const MAX_CALENDAR_YEAR: u16 = 2027;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SourceRootKind {
    ConsultantExport,
    Garant,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorpusRoot {
    root: PathBuf,
    kind: SourceRootKind,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SampleMeta {
    pub relative_path: String,
    pub provider: SourceRootKind,
    pub year: Option<u16>,
    pub document_type: String,
    pub work_family: WorkFamilyKey,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct WorkFamilyKey {
    pub provider: SourceRootKind,
    pub key: String,
    pub provenance: WorkFamilyProvenance,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WorkFamilyProvenance {
    NpaDirectory,
    NpaFilename,
    XmlId,
    CourtId,
    FasFilename,
    GarantFilename,
    UnknownRelativePath,
}

impl CorpusRoot {
    /// Construct a root used for membership checks. `law-source/consultant`
    /// is intentionally not representable as a ConsultantExport root.
    pub fn new(root: impl Into<PathBuf>, kind: SourceRootKind) -> Result<Self, String> {
        let root = root.into();
        if root.as_os_str().is_empty() {
            return Err("source root must not be empty".into());
        }
        if kind == SourceRootKind::ConsultantExport
            && root
                .components()
                .any(|c| matches!(c, Component::Normal(s) if s == "consultant"))
            && root
                .components()
                .any(|c| matches!(c, Component::Normal(s) if s == "law-source"))
        {
            return Err("law-source/consultant is a forbidden source root".into());
        }
        Ok(Self { root, kind })
    }

    pub fn kind(&self) -> SourceRootKind {
        self.kind
    }

    pub fn classify(&self, path: &Path) -> Result<SampleMeta, String> {
        let relative = path
            .strip_prefix(&self.root)
            .map_err(|_| "path is outside the declared source root".to_owned())?;
        let relative_path = normalized_relative(relative)?;
        classify_relative(&relative_path, self.kind)
    }
}

/// Classify an absolute path against an explicit root without canonicalizing
/// it. Canonicalization would make metadata depend on the checkout location.
pub fn classify_path(
    path: &Path,
    source_root: &Path,
    kind: SourceRootKind,
) -> Result<SampleMeta, String> {
    CorpusRoot::new(source_root, kind)?.classify(path)
}

pub fn classify_relative(
    relative_path: &str,
    provider: SourceRootKind,
) -> Result<SampleMeta, String> {
    let path = Path::new(relative_path);
    let normalized = normalized_relative(path)?;
    let parts: Vec<&str> = normalized.split('/').collect();
    let filename = parts.last().copied().ok_or("empty relative path")?;
    let parent_work_year = (provider == SourceRootKind::ConsultantExport
        && parts.first() == Some(&"npa"))
    .then(|| parts.get(1).copied().and_then(filename_year))
    .flatten();
    let year = parent_work_year
        .or_else(|| filename_year(filename))
        .or_else(|| {
            if provider == SourceRootKind::Garant {
                garant_year(filename)
            } else {
                None
            }
        });
    let document_type = document_type(&parts, filename, provider);
    let work_family = work_family(&parts, filename, provider);
    Ok(SampleMeta {
        relative_path: normalized,
        provider,
        year,
        document_type,
        work_family,
    })
}

fn normalized_relative(path: &Path) -> Result<String, String> {
    let mut out = Vec::new();
    for component in path.components() {
        match component {
            Component::Normal(value) => out.push(value.to_string_lossy().into_owned()),
            Component::CurDir => {}
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                return Err("path must be relative and must not traverse outside its root".into())
            }
        }
    }
    if out.is_empty() {
        return Err("relative path must not be empty".into());
    }
    Ok(out.join("/"))
}

fn valid_year(year: u16) -> Option<u16> {
    (MIN_CALENDAR_YEAR..=MAX_CALENDAR_YEAR)
        .contains(&year)
        .then_some(year)
}

fn valid_date(year: u16, month: u8, day: u8) -> bool {
    if !(1..=12).contains(&month) || day == 0 {
        return false;
    }
    let leap = year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let days = match month {
        2 if leap => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    };
    day <= days
}

fn filename_year(filename: &str) -> Option<u16> {
    let bytes = filename.as_bytes();
    if bytes.len() < 10 {
        return None;
    }
    for i in 0..=bytes.len() - 10 {
        if i > 0 && bytes[i - 1].is_ascii_digit() {
            continue;
        }
        if !bytes[i..i + 4].iter().all(|b| b.is_ascii_digit())
            || bytes[i + 4] != b'-'
            || !bytes[i + 5..i + 7].iter().all(|b| b.is_ascii_digit())
            || bytes[i + 7] != b'-'
            || !bytes[i + 8..i + 10].iter().all(|b| b.is_ascii_digit())
        {
            continue;
        }
        let year = std::str::from_utf8(&bytes[i..i + 4]).ok()?.parse().ok()?;
        let month = std::str::from_utf8(&bytes[i + 5..i + 7])
            .ok()?
            .parse()
            .ok()?;
        let day = std::str::from_utf8(&bytes[i + 8..i + 10])
            .ok()?
            .parse()
            .ok()?;
        if valid_year(year).is_some() && valid_date(year, month, day) {
            return Some(year);
        }
    }
    None
}

fn garant_year(filename: &str) -> Option<u16> {
    let marker = filename.find(" г")?;
    let before = &filename[..marker];
    let digits: String = before
        .chars()
        .rev()
        .take_while(|c| c.is_ascii_digit())
        .take(4)
        .collect::<String>()
        .chars()
        .rev()
        .collect();
    if digits.len() == 4 {
        digits.parse::<u16>().ok().and_then(valid_year)
    } else {
        None
    }
}

fn document_type(parts: &[&str], filename: &str, provider: SourceRootKind) -> String {
    if provider == SourceRootKind::Garant {
        let lower = filename.to_lowercase();
        if lower.contains("постановлен") {
            return "resolution".into();
        }
        if lower.contains("федеральн") || lower.contains("44-fz") {
            return "law".into();
        }
        return "unknown".into();
    }
    match parts.first().copied() {
        Some("courts") => "courts-unspecified".into(),
        Some("fas") => "fas-unspecified".into(),
        Some("xml") => "xml-unspecified".into(),
        Some("npa") => {
            let label = parts.get(1).copied().unwrap_or(filename);
            label
                .split('_')
                .next()
                .map(|s| match s {
                    "law" => "law",
                    "order" => "order",
                    "resolution" => "resolution",
                    "directive" => "directive",
                    "decree" => "decree",
                    "document" => "document",
                    _ => "unknown",
                })
                .unwrap_or("unknown")
                .into()
        }
        _ => "unknown".into(),
    }
}

fn work_family(parts: &[&str], filename: &str, provider: SourceRootKind) -> WorkFamilyKey {
    let (key, provenance) = if provider == SourceRootKind::Garant {
        (filename.to_owned(), WorkFamilyProvenance::GarantFilename)
    } else if parts.first() == Some(&"npa") {
        if parts.len() > 2 && parts[1].starts_with("law_") {
            (parts[1].to_owned(), WorkFamilyProvenance::NpaDirectory)
        } else if let Some(stem) = filename.split("_rev-").next() {
            (stem.to_owned(), WorkFamilyProvenance::NpaFilename)
        } else {
            (
                filename.to_owned(),
                WorkFamilyProvenance::UnknownRelativePath,
            )
        }
    } else if parts.first() == Some(&"xml") && parts.get(1) == Some(&"law") && parts.len() > 2 {
        (parts[2].to_owned(), WorkFamilyProvenance::XmlId)
    } else if parts.first() == Some(&"courts") && parts.len() > 2 {
        let id = filename.split("-edition-").next().unwrap_or(filename);
        (
            format!("{}/{}", parts[1], id),
            WorkFamilyProvenance::CourtId,
        )
    } else if parts.first() == Some(&"fas") {
        (
            filename.split('_').next().unwrap_or(filename).to_owned(),
            WorkFamilyProvenance::FasFilename,
        )
    } else {
        (parts.join("/"), WorkFamilyProvenance::UnknownRelativePath)
    };
    WorkFamilyKey {
        provider,
        key,
        provenance,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn invalid_dates_and_hash_digits_are_unknown() {
        assert_eq!(
            classify_relative(
                "courts/acn/edition-c0c8875a.xml",
                SourceRootKind::ConsultantExport
            )
            .unwrap()
            .year,
            None
        );
        assert_eq!(
            classify_relative(
                "npa/law_2021-02-29_1-fz.xml",
                SourceRootKind::ConsultantExport
            )
            .unwrap()
            .year,
            None
        );
    }
}
