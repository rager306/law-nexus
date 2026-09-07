//! Library orchestration for the `hierarchy-registry-generator` binary
//! (M202-9qf3ta S03 T04, D427).
//!
//! Cross-crate flow: the tracked S02 candidate artifact is parsed by
//! ln-decode ([`parse_candidate_artifact_view`]), normalized into
//! ln-kb-ontology candidate evidence, admitted against the closed tracked
//! admission source, and rendered as the deterministic complete registry
//! projection; the preserved `editions:` / `works:` tables of the current
//! tracked registry travel through verbatim. Admission binds only the
//! already-existing CC identifiers named by the admission rows (D426); no
//! ComponentConcept is derived or minted, `punkt` rows stay unadmitted, and
//! the projection stays `[proposed]` with `authoritative: false`.
//!
//! Failure surface is typed ([`GeneratorError`]) with pinned CLI exit
//! codes; diagnostics are count-only `key=value` lines without raw legal
//! text. [`parse_candidate_artifact_view`]: ln_decode::hierarchy_artifact::parse_candidate_artifact_view

use std::fmt;
use std::fs;
use std::path::{Component, Path, PathBuf};

use ln_decode::hierarchy_artifact::parse_candidate_artifact_view;
use ln_kb_ontology::registry_admission::{
    admit_candidates, parse_admission_source, parse_registry_tables, render_complete_registry,
    AdmissionSource, CandidateEvidence, CandidateIdentity, CompleteRegistryRenderInput,
};

/// Canonical production write target: the only tracked-tree `--out` that
/// `--write` may touch. T05 owns regeneration of this path.
pub const CANONICAL_REGISTRY_PATH: &str = "prd/architecture/kb-hierarchy-registry.yaml";
/// Tracked admission sources live next to the registry projection.
const ADMISSIONS_PREFIX: &str = "prd/architecture/";
/// Tracked candidate artifacts live under the migration evidence tree.
const CANDIDATE_ARTIFACT_PREFIX: &str = "prd/migration/rust-evidence/";
/// Test contract: repository-relative Cargo target temp outputs.
const TARGET_TMP_PREFIX: &str = "target/tmp/";

/// Parsed CLI invocation for the generator binary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GeneratorCli {
    pub candidate_artifact: PathBuf,
    pub admissions: PathBuf,
    pub out: PathBuf,
    pub mode: GeneratorMode,
}

/// What the generator does with the rendered projection.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GeneratorMode {
    /// Render in memory, byte-compare against `--out`, never write.
    Check,
    /// Atomically replace `--out` via a sibling temp file plus rename.
    Write,
}

/// Typed generator failure modes. Usage/path refusals exit 2, missing
/// inputs exit 4, and every validated-content rejection (drift, conflict,
/// stale output) exits 6. `stderr_line` is always count-only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GeneratorError {
    Usage { detail: String },
    PathRefused { path: String },
    InputMissing { path: String },
    Admission { detail: String },
    Stale { detail: String },
}

impl GeneratorError {
    /// Pinned CLI exit code per failure class.
    pub fn exit_code(&self) -> i32 {
        match self {
            Self::Usage { .. } | Self::PathRefused { .. } => 2,
            Self::InputMissing { .. } => 4,
            Self::Admission { .. } | Self::Stale { .. } => 6,
        }
    }

    /// Single count-only stderr line. Content rejections use the pinned
    /// `drift=...` shape; operational refusals use `error=...`. Values are
    /// single tokens (dashes, never spaces) so every token carries `=`.
    pub fn stderr_line(&self) -> String {
        match self {
            Self::Usage { detail } => format!("error=usage detail={detail}"),
            Self::PathRefused { path } => format!("error=path-refused path={path}"),
            Self::InputMissing { path } => format!("error=input-missing path={path}"),
            Self::Admission { detail } => format!("drift=admission detail={detail}"),
            Self::Stale { detail } => format!("drift=stale detail={detail}"),
        }
    }
}

impl fmt::Display for GeneratorError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Usage { detail } => write!(formatter, "usage error: {detail}"),
            Self::PathRefused { path } => write!(formatter, "path refused: {path}"),
            Self::InputMissing { path } => write!(formatter, "input missing: {path}"),
            Self::Admission { detail } => write!(formatter, "admission drift: {detail}"),
            Self::Stale { detail } => write!(formatter, "stale output: {detail}"),
        }
    }
}

impl std::error::Error for GeneratorError {}

fn usage(detail: impl fmt::Display) -> GeneratorError {
    GeneratorError::Usage {
        detail: detail.to_string(),
    }
}

fn single_token(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join("-")
}

fn take_value(
    flags: &mut impl Iterator<Item = String>,
    flag: &str,
) -> Result<String, GeneratorError> {
    flags
        .next()
        .ok_or_else(|| usage(format!("{flag} requires a value")))
}

/// Validate a CLI path argument: ASCII-only, no backslashes/quotes, no
/// parent escapes. Absolute paths are refused outright: every generator
/// input and output travels as a repository-relative path. Returns the path
/// in the lexical form the repo-root resolver expects.
fn validate_cli_path(raw: &str) -> Result<PathBuf, GeneratorError> {
    if raw.is_empty()
        || raw.contains('\\')
        || raw.contains('"')
        || !raw.bytes().all(|byte| (0x20..0x7f).contains(&byte))
    {
        return Err(GeneratorError::PathRefused {
            path: single_token(raw),
        });
    }
    let path = PathBuf::from(raw);
    if path.is_absolute()
        || !path
            .components()
            .all(|component| matches!(component, Component::Normal(_)))
    {
        return Err(GeneratorError::PathRefused {
            path: single_token(raw),
        });
    }
    Ok(path)
}

/// Parse the thin generator surface: `--candidate-artifact <path>`
/// `--admissions <path>` `--out <path>` plus exactly one of `--check` /
/// `--write`. Every usage or path refusal happens before any filesystem
/// access or mutation.
pub fn parse_generator_args(args: Vec<String>) -> Result<GeneratorCli, GeneratorError> {
    let mut candidate_artifact: Option<PathBuf> = None;
    let mut admissions: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut check = false;
    let mut write = false;

    let mut flags = args.into_iter();
    while let Some(flag) = flags.next() {
        match flag.as_str() {
            "--candidate-artifact" => {
                candidate_artifact = Some(validate_cli_path(&take_value(
                    &mut flags,
                    "--candidate-artifact",
                )?)?);
            }
            "--admissions" => {
                admissions = Some(validate_cli_path(&take_value(&mut flags, "--admissions")?)?);
            }
            "--out" => {
                out = Some(validate_cli_path(&take_value(&mut flags, "--out")?)?);
            }
            "--check" => check = true,
            "--write" => write = true,
            other => return Err(usage(format!("unknown flag {other:?}"))),
        }
    }

    let mode = match (check, write) {
        (true, true) => return Err(usage("--check and --write are mutually exclusive")),
        (true, false) => GeneratorMode::Check,
        (false, true) => GeneratorMode::Write,
        (false, false) => return Err(usage("one of --check or --write is required")),
    };
    let candidate_artifact =
        candidate_artifact.ok_or_else(|| usage("missing --candidate-artifact"))?;
    let admissions = admissions.ok_or_else(|| usage("missing --admissions"))?;
    let out = out.ok_or_else(|| usage("missing --out"))?;

    Ok(GeneratorCli {
        candidate_artifact,
        admissions,
        out,
        mode,
    })
}

/// Walk up from the working directory to the repository root so that
/// repo-relative CLI paths resolve both from the repo root (subprocess) and
/// from the crate directory (cargo test).
fn find_repo_root() -> Option<PathBuf> {
    let mut dir = std::env::current_dir().ok()?;
    loop {
        if dir.join(".git").exists() {
            return Some(dir);
        }
        if !dir.pop() {
            return None;
        }
    }
}

fn resolve_repo_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        return path.to_path_buf();
    }
    match find_repo_root() {
        Some(root) => root.join(path),
        None => path.to_path_buf(),
    }
}

/// Classify the `--out` target. `--check` never writes, so it accepts any
/// lexically safe path; `--write` accepts only the canonical registry
/// projection in production or a repository-relative Cargo target temp path
/// in the test contract.
fn check_out_target(cli: &GeneratorCli) -> Result<(), GeneratorError> {
    let text = cli.out.to_string_lossy().into_owned();
    match cli.mode {
        GeneratorMode::Check => Ok(()),
        GeneratorMode::Write => {
            if text == CANONICAL_REGISTRY_PATH || text.starts_with(TARGET_TMP_PREFIX) {
                Ok(())
            } else {
                Err(GeneratorError::PathRefused {
                    path: single_token(&text),
                })
            }
        }
    }
}

/// Classify the generator inputs: the candidate artifact must be tracked
/// S02 evidence JSON and the admission source must be a tracked admission
/// file next to the registry projection, or a repository-relative Cargo
/// target temp file (test contract: fixtures carry no `.yaml` suffix).
/// Registry YAML is never an input.
fn check_input_paths(cli: &GeneratorCli) -> Result<(), GeneratorError> {
    let candidate = cli.candidate_artifact.to_string_lossy().into_owned();
    let admissions = cli.admissions.to_string_lossy().into_owned();
    let candidate_ok = candidate.starts_with(CANDIDATE_ARTIFACT_PREFIX)
        && candidate.ends_with(".json")
        && candidate != CANONICAL_REGISTRY_PATH;
    let admissions_ok = (admissions.starts_with(ADMISSIONS_PREFIX)
        && (admissions.ends_with(".yaml") || admissions.ends_with(".yml"))
        || admissions.starts_with(TARGET_TMP_PREFIX))
        && admissions != CANONICAL_REGISTRY_PATH;
    if !candidate_ok {
        return Err(GeneratorError::PathRefused {
            path: single_token(&candidate),
        });
    }
    if !admissions_ok {
        return Err(GeneratorError::PathRefused {
            path: single_token(&admissions),
        });
    }
    Ok(())
}

fn read_input(path: &Path) -> Result<String, GeneratorError> {
    let resolved = resolve_repo_path(path);
    let bytes = fs::read(&resolved).map_err(|_| GeneratorError::InputMissing {
        path: single_token(&path.to_string_lossy()),
    })?;
    String::from_utf8(bytes).map_err(|_| GeneratorError::Admission {
        detail: single_token(&format!("input is not utf-8: {}", path.to_string_lossy())),
    })
}

/// Portable SHA-256 over bytes (FIPS 180-4). `ln-decode` pins FNV-1a
/// digests for closed artifact identity; the generator additionally binds
/// the exact S02 artifact file bytes, so the admission source pins the
/// file SHA-256 as its tamper-visible seal.
pub fn sha256_hex(bytes: &[u8]) -> String {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let mut padded = bytes.to_vec();
    let bit_len = (bytes.len() as u64).wrapping_mul(8);
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    for block in padded.as_chunks::<64>().0 {
        let mut schedule = [0u32; 64];
        for (index, word) in schedule.iter_mut().take(16).enumerate() {
            let base = index * 4;
            *word = u32::from_be_bytes([
                block[base],
                block[base + 1],
                block[base + 2],
                block[base + 3],
            ]);
        }
        for index in 16..64 {
            let small_sigma_0 = schedule[index - 15].rotate_right(7)
                ^ schedule[index - 15].rotate_right(18)
                ^ (schedule[index - 15] >> 3);
            let small_sigma_1 = schedule[index - 2].rotate_right(17)
                ^ schedule[index - 2].rotate_right(19)
                ^ (schedule[index - 2] >> 10);
            schedule[index] = schedule[index - 16]
                .wrapping_add(small_sigma_0)
                .wrapping_add(schedule[index - 7])
                .wrapping_add(small_sigma_1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) = (
            state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7],
        );
        for index in 0..64 {
            let big_sigma_1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choice = (e & f) ^ ((!e) & g);
            let temp_1 = h
                .wrapping_add(big_sigma_1)
                .wrapping_add(choice)
                .wrapping_add(K[index])
                .wrapping_add(schedule[index]);
            let big_sigma_0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let temp_2 = big_sigma_0.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp_1);
            d = c;
            c = b;
            b = a;
            a = temp_1.wrapping_add(temp_2);
        }
        state[0] = state[0].wrapping_add(a);
        state[1] = state[1].wrapping_add(b);
        state[2] = state[2].wrapping_add(c);
        state[3] = state[3].wrapping_add(d);
        state[4] = state[4].wrapping_add(e);
        state[5] = state[5].wrapping_add(f);
        state[6] = state[6].wrapping_add(g);
        state[7] = state[7].wrapping_add(h);
    }
    let mut hex = String::with_capacity(64);
    for word in state {
        hex.push_str(&format!("{word:08x}"));
    }
    hex
}

/// Build caller-supplied admission evidence from the decoded artifact view
/// plus the SHA-256 over the exact artifact file bytes. The file SHA is
/// computed by the caller (which owns the file read), never read from the
/// artifact itself, so the digest pin is tamper-visible (D185).
fn evidence_from_view(
    view: &ln_decode::hierarchy_artifact::CandidateArtifactView,
    artifact_sha256: &str,
    artifact_path: &str,
) -> CandidateEvidence {
    CandidateEvidence {
        artifact_schema: view.artifact_schema.clone(),
        lifecycle: view.lifecycle.clone(),
        authoritative: view.authoritative,
        artifact_path: artifact_path.to_owned(),
        artifact_sha256: artifact_sha256.to_owned(),
        source_digest: view.source_digest.clone(),
        identity_digest: view.identity_digest.clone(),
        candidates: view
            .candidates
            .iter()
            .map(|identity| CandidateIdentity {
                catalog_token: identity.catalog_token.clone(),
                number: identity.number.clone(),
                path: identity.path.clone(),
                key_path: identity.key_path.clone(),
            })
            .collect(),
    }
}

/// Render the complete registry projection for one parsed CLI invocation.
/// Every rejection happens before any write: input gates, file reads,
/// closed admission-source parse, artifact view parse, SHA-256 binding,
/// admission, preserved-table extraction. Returns the rendered bytes plus
/// admitted/legacy/candidate row counts for the count-only heartbeat.
pub fn render_projection(
    cli: &GeneratorCli,
) -> Result<(String, usize, usize, usize), GeneratorError> {
    check_out_target(cli)?;
    check_input_paths(cli)?;

    let artifact_text = read_input(&cli.candidate_artifact)?;
    if !artifact_text.is_ascii() {
        return Err(GeneratorError::Admission {
            detail: "candidate-artifact-must-be-ascii".to_owned(),
        });
    }
    let artifact_sha256 = sha256_hex(artifact_text.as_bytes());
    let view = parse_candidate_artifact_view(&artifact_text).map_err(|error| {
        GeneratorError::Admission {
            detail: single_token(&error.to_string()),
        }
    })?;

    let admissions_text = read_input(&cli.admissions)?;
    if !admissions_text.is_ascii() {
        return Err(GeneratorError::Admission {
            detail: "admissions-must-be-ascii".to_owned(),
        });
    }
    let source: AdmissionSource =
        parse_admission_source(&admissions_text).map_err(|error| GeneratorError::Admission {
            detail: single_token(&error.to_string()),
        })?;

    let evidence = evidence_from_view(
        &view,
        &artifact_sha256,
        &cli.candidate_artifact.to_string_lossy(),
    );
    let admitted =
        admit_candidates(&evidence, &source).map_err(|error| GeneratorError::Admission {
            detail: single_token(&error.to_string()),
        })?;

    // The preserved tables travel from the current tracked registry so
    // `editions:` / `works:` identity grounding survives regeneration. The
    // production registry is the table source; a test-temp `--out` that
    // already exists still falls back to it, and a missing temp file is not
    // an error (the binding render is authoritative for bindings).
    let tables_text = match cli.mode {
        GeneratorMode::Write if cli.out.to_string_lossy() == CANONICAL_REGISTRY_PATH => {
            read_input(&cli.out)?
        }
        _ => {
            let canonical = PathBuf::from(CANONICAL_REGISTRY_PATH);
            match read_input(&canonical) {
                Ok(text) => text,
                Err(_) => read_input(&cli.out).unwrap_or_default(),
            }
        }
    };
    let (sections, interlude) = if tables_text.is_empty() {
        (Vec::new(), None)
    } else {
        parse_registry_tables(&tables_text).map_err(|error| GeneratorError::Admission {
            detail: single_token(&error.to_string()),
        })?
    };
    let rendered = render_complete_registry(&CompleteRegistryRenderInput {
        admitted: &admitted,
        sections: &sections,
        interlude_comment: interlude.as_deref(),
    });

    let candidate_backed = admitted
        .bindings
        .iter()
        .filter(|row| {
            row.provenance
                == ln_kb_ontology::registry_admission::AdmissionProvenance::CandidateBackedM202
        })
        .count();
    let legacy = admitted.bindings.len() - candidate_backed;
    Ok((rendered, admitted.bindings.len(), legacy, candidate_backed))
}

/// Pinned count-only heartbeat: row counts and drift, never content.
fn heartbeat_line(admitted: usize, legacy: usize, candidate_backed: usize) -> String {
    format!("admitted={admitted} legacy={legacy} candidate-backed={candidate_backed} drift=0")
}

/// Run one parsed CLI invocation. `--check` renders in memory and
/// byte-compares without creating, writing, or truncating `--out`;
/// `--write` atomically replaces `--out` via a sibling temp file plus
/// rename. The heartbeat goes to stderr; stdout stays empty.
pub fn run_generator(cli: &GeneratorCli) -> Result<(), GeneratorError> {
    let (rendered, admitted, legacy, candidate_backed) = render_projection(cli)?;
    eprintln!("{}", heartbeat_line(admitted, legacy, candidate_backed));
    let out_path = resolve_repo_path(&cli.out);
    match cli.mode {
        GeneratorMode::Check => {
            let expected_bytes = fs::read(&out_path).map_err(|_| GeneratorError::Admission {
                detail: single_token(&format!(
                    "expected output is missing: {}",
                    cli.out.to_string_lossy()
                )),
            })?;
            if expected_bytes != rendered.as_bytes() {
                return Err(GeneratorError::Stale {
                    detail: single_token(&format!(
                        "output differs from render: {}",
                        cli.out.to_string_lossy()
                    )),
                });
            }
            Ok(())
        }
        GeneratorMode::Write => {
            if let Some(parent) = out_path.parent() {
                fs::create_dir_all(parent).map_err(|_| GeneratorError::InputMissing {
                    path: single_token(&cli.out.to_string_lossy()),
                })?;
            }
            let sibling = out_path.with_extension("tmp-m202-s03");
            fs::write(&sibling, rendered.as_bytes()).map_err(|_| GeneratorError::InputMissing {
                path: single_token(&cli.out.to_string_lossy()),
            })?;
            fs::rename(&sibling, &out_path).map_err(|_| GeneratorError::InputMissing {
                path: single_token(&cli.out.to_string_lossy()),
            })?;
            Ok(())
        }
    }
}
