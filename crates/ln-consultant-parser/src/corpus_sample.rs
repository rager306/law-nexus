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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
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

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct WorkFamilyKey {
    pub provider: SourceRootKind,
    pub key: String,
    pub provenance: WorkFamilyProvenance,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
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

/// One inventory row after path metadata and content hashing have been validated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SampleCandidate {
    pub relative_path: String,
    pub content_hash: String,
    pub meta: SampleMeta,
}

/// A bounded, reproducible draw. `candidates` is in the canonical draw order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DrawPlan {
    pub seed: u64,
    pub requested: usize,
    pub candidates: Vec<SampleCandidate>,
    pub leakage: LeakageReport,
}

/// Diagnostics are observations, not a Work-family holdout claim.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct LeakageReport {
    pub input_candidates: usize,
    pub exact_duplicate_hashes: usize,
    pub excluded_c3_hashes: usize,
    pub collapsed_editions: usize,
    pub collapsed_families: usize,
    pub c3_family_overlap: usize,
    pub garant_available: usize,
    pub garant_selected: usize,
    pub consultant_available: usize,
    pub consultant_selected: usize,
    pub garant_cap: usize,
    pub not_year_type_stratified: bool,
}

const GARANT_CAP: usize = 4;

/// Select a canonical prefix after removing exact duplicates, C3 hashes, and
/// additional editions of the same provider-qualified family.
pub fn draw(
    inventory: impl IntoIterator<Item = SampleCandidate>,
    c3_hashes: &std::collections::BTreeSet<String>,
    requested: usize,
    seed: u64,
) -> Result<DrawPlan, String> {
    draw_with_c3_families(inventory, c3_hashes, &[], requested, seed)
}

/// Variant used by leakage diagnostics when frozen C3 metadata is available.
/// Family overlap is deliberately reported, not treated as a family holdout.
pub fn draw_with_c3_families(
    inventory: impl IntoIterator<Item = SampleCandidate>,
    c3_hashes: &std::collections::BTreeSet<String>,
    c3_families: &[WorkFamilyKey],
    requested: usize,
    seed: u64,
) -> Result<DrawPlan, String> {
    if requested == 0 {
        return Err("requested draw size must be positive".into());
    }
    let input: Vec<_> = inventory.into_iter().collect();
    let mut report = LeakageReport {
        input_candidates: input.len(),
        garant_cap: GARANT_CAP,
        not_year_type_stratified: true,
        ..LeakageReport::default()
    };
    let mut seen = std::collections::BTreeSet::new();
    let mut rows = Vec::new();
    for candidate in input {
        validate_candidate(&candidate)?;
        if !seen.insert(candidate.content_hash.clone()) {
            report.exact_duplicate_hashes += 1;
            continue;
        }
        if c3_hashes.contains(&candidate.content_hash) {
            report.excluded_c3_hashes += 1;
            continue;
        }
        rows.push(candidate);
    }
    report.garant_available = rows
        .iter()
        .filter(|c| c.meta.provider == SourceRootKind::Garant)
        .count();
    report.consultant_available = rows
        .iter()
        .filter(|c| c.meta.provider == SourceRootKind::ConsultantExport)
        .count();
    report.c3_family_overlap = rows
        .iter()
        .filter(|c| c3_families.iter().any(|f| f == &c.meta.work_family))
        .count();

    rows.sort_by_key(|candidate| {
        (
            mixed_rank(seed, &candidate.content_hash).unwrap_or(u64::MAX),
            candidate.content_hash.clone(),
            candidate.relative_path.clone(),
        )
    });

    // Pick one deterministic winner for every known family. Unknown families
    // use their unique relative-path fallback and therefore never merge.
    let mut families = std::collections::BTreeSet::new();
    let mut collapsed_family_keys = std::collections::BTreeSet::new();
    let mut collapsed = Vec::new();
    for candidate in rows {
        if !families.insert(candidate.meta.work_family.clone()) {
            report.collapsed_editions += 1;
            collapsed_family_keys.insert(candidate.meta.work_family.clone());
            continue;
        }
        collapsed.push(candidate);
    }
    report.collapsed_families = collapsed_family_keys.len();

    // Provider ordering is part of the canonical order: at most four Garant
    // rows lead the draw, while consultant rows fill the remaining prefix.
    let (mut garant, mut consultant): (Vec<_>, Vec<_>) = collapsed
        .into_iter()
        .partition(|c| c.meta.provider == SourceRootKind::Garant);
    garant.truncate(GARANT_CAP);
    let garant_exhausted = garant.len();
    consultant.extend(garant);
    // The partition order above is intentionally normalized below: Garant is
    // capped, then placed first, and consultant rows retain their rank order.
    let mut ordered = consultant;
    ordered.sort_by_key(|candidate| {
        (
            if candidate.meta.provider == SourceRootKind::Garant {
                0u8
            } else {
                1
            },
            mixed_rank(seed, &candidate.content_hash).unwrap_or(u64::MAX),
            candidate.content_hash.clone(),
            candidate.relative_path.clone(),
        )
    });
    if ordered.len() < requested {
        return Err(format!(
            "insufficient inventory after exclusions/dedup/collapse: requested={requested}, available={}, c3_excluded={}, exact_duplicates={}, collapsed_editions={}",
            ordered.len(), report.excluded_c3_hashes, report.exact_duplicate_hashes, report.collapsed_editions
        ));
    }
    ordered.truncate(requested);
    report.garant_selected = ordered
        .iter()
        .filter(|c| c.meta.provider == SourceRootKind::Garant)
        .count();
    report.consultant_selected = ordered.len() - report.garant_selected;
    let _ = garant_exhausted;
    Ok(DrawPlan {
        seed,
        requested,
        candidates: ordered,
        leakage: report,
    })
}

fn validate_candidate(candidate: &SampleCandidate) -> Result<(), String> {
    let normalized = normalized_relative(Path::new(&candidate.relative_path))?;
    if normalized != candidate.relative_path || normalized != candidate.meta.relative_path {
        return Err("candidate relative path is not normalized or disagrees with metadata".into());
    }
    let hash = candidate
        .content_hash
        .strip_prefix("sha256:")
        .unwrap_or(&candidate.content_hash);
    if hash.len() != 64 || !hash.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(format!(
            "invalid content hash for {}",
            candidate.relative_path
        ));
    }
    Ok(())
}

fn mixed_rank(seed: u64, hash: &str) -> Result<u64, String> {
    let bytes = hash.strip_prefix("sha256:").unwrap_or(hash).as_bytes();
    if bytes.len() != 64 || !bytes.iter().all(u8::is_ascii_hexdigit) {
        return Err("content hash must be 64 hexadecimal digits".into());
    }
    let mut value = seed ^ 0x9e3779b97f4a7c15;
    let (pairs, _) = bytes.as_chunks::<2>();
    for pair in pairs {
        let byte = u64::from(u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap());
        value = value.rotate_left(7) ^ byte;
        value = value.wrapping_mul(0x100000001b3);
    }
    // SplitMix-style integer mixing is stable, dependency-free, and does not
    // use path order, process state, DefaultHasher, or a random generator.
    let mut z = value;
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    Ok(z ^ (z >> 31))
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
