//! reference-layer CLI: derive the ADR-0031 reference artifacts and byte-check
//! them against the committed Python-reference outputs.
//!
//! Exit codes (ADR-0031 D6): 0 ok, 2 argv, 3 unreadable inputs, 6 byte drift.
//! Exit 5 (schema violation) is reserved by the contract but is **not emitted
//! here**: Draft-2020-12 subset validation lives in the Python reference
//! (`scripts/m217_reference_jsonld.py --check`), which gates the artifacts this
//! bin only compares byte for byte.

use ln_consultant_parser::reference_layer::{
    DeriveOptions, EXIT_ARGV, EXIT_INPUT, EXIT_OK, artifact_paths, artifacts_dir, catalog_path,
    corpus_dir, derive, filename_day, run_check,
};
use std::path::Path;
use std::process::ExitCode;

fn main() -> ExitCode {
    // The module helpers resolve repo paths relative to the crate manifest dir
    // (`<repo>/crates/ln-consultant-parser`), so they get the manifest, not the
    // already-canonicalized repo root.
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let corpus = corpus_dir(manifest);
    let catalog = catalog_path(manifest);
    let out_dir = artifacts_dir(manifest);

    let mut args = std::env::args().skip(1);
    let mut check = false;
    let mut g_layer: Option<u32> = None;
    let mut out: Option<String> = None;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--check" => check = true,
            "--g-layer" => match args.next().and_then(|v| v.parse::<u32>().ok()) {
                Some(n) => g_layer = Some(n),
                None => return fail("--g-layer requires an edition number", EXIT_ARGV),
            },
            "--out" => match args.next() {
                Some(v) => out = Some(v),
                None => return fail("--out requires a path", EXIT_ARGV),
            },
            other => return fail(&format!("unexpected argument: {other}"), EXIT_ARGV),
        }
    }

    if let Some(edition_no) = g_layer {
        let Some(out_path) = out else {
            return fail("--g-layer requires --out", EXIT_ARGV);
        };
        if !corpus.is_dir() {
            return fail(
                &format!("unreadable corpus: {}", corpus.display()),
                EXIT_INPUT,
            );
        }
        // Deterministic pick, mirroring the Python reference `sorted(glob_files(...))`.
        let mut files: Vec<_> = std::fs::read_dir(&corpus)
            .expect("corpus dir readable")
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| {
                p.file_name()
                    .and_then(|n| n.to_str())
                    .is_some_and(|n| n.starts_with(&format!("edition-{edition_no:04}_")))
            })
            .collect();
        files.sort();
        let Some(path) = files.first() else {
            return fail(&format!("edition {edition_no} not found"), EXIT_INPUT);
        };
        let day = path
            .file_name()
            .and_then(|n| n.to_str())
            .and_then(filename_day)
            .unwrap_or_else(|| "9999-12-31".into());
        let bytes =
            ln_consultant_parser::reference_layer::edition_layer_document(path, edition_no, &day);
        if let Err(err) = std::fs::write(&out_path, &bytes) {
            return fail(&format!("cannot write {out_path}: {err}"), EXIT_INPUT);
        }
        println!("wrote {out_path} ({} bytes)", bytes.len());
        return ExitCode::from(EXIT_OK as u8);
    }

    if !corpus.is_dir() || !catalog.exists() {
        return fail(
            &format!(
                "unreadable inputs: corpus={} catalog={}",
                corpus.display(),
                catalog.display()
            ),
            EXIT_INPUT,
        );
    }

    if check {
        return ExitCode::from(run_check(&corpus, &catalog, &out_dir) as u8);
    }

    let opts = DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus,
        catalog,
    };
    let reference = derive(&opts);
    for (path, body) in artifact_paths(&out_dir).iter().zip([
        reference.timeline.as_bytes(),
        reference.digests.as_bytes(),
        reference.named_graphs.as_bytes(),
        reference.amend.as_bytes(),
    ]) {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).expect("mkdir");
        }
        std::fs::write(path, body).expect("write artifact");
        println!("wrote {} ({} bytes)", path.display(), body.len());
    }
    ExitCode::from(EXIT_OK as u8)
}

fn fail(msg: &str, code: i32) -> ExitCode {
    eprintln!("{msg}");
    ExitCode::from(code as u8)
}
