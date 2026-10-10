//! S04 declared-corpus acceptance battery for the cleaned projection:
//! Hold/TextOnly text safety, explicit incomplete marking, deterministic
//! export, atomic publication and S03 navigation resolvability on a declared
//! slice of the tracked `law-source/consultant` fixture vault.
//!
//! This battery is a handwritten oracle. It shares no code with the module
//! under test beyond its public API: it walks `Package.records()` itself to
//! rebuild the decoded-text channel and never derives its expectations from the
//! writer's private helpers. The bounded sub-slice is six explicitly named,
//! sha256-pinned tracked documents; the declared slice is the 82 top-level
//! `law-source/consultant/*.xml` fixtures.
//!
//! Non-claims: `[bounded]` to the declared slice. `law-source/consultant` is a
//! fixture vault, **not** the corpus (`consru_export/exports/`); this is not
//! corpus coverage, not source authenticity and not legal completeness. Seals
//! and counts are integrity, not coverage. R1000 stays active and its closure is
//! a milestone-level act. The full-82 runner is `#[ignore]`d out-of-band because
//! the sweep exceeds the 600 s evidence cap (MEM1488). Raw decoded legal text is
//! never logged.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::cleaned_completion::{ScopeDeclaration, classify_completion, completion_for};
use ln_decode::cleaned_nav::build_nav_index_from_wire;
use ln_decode::cleaned_nav_verifier::verify_nav_index;
use ln_decode::cleaned_publish::write_cleaned_projection_atomic;
use ln_decode::cleaned_verifier::verify_cleaned_wire;
use ln_decode::cleaned_wire::{
    CleanedProjection, IncompleteReason, WireCompletion, WireLimits, export_cleaned_projection,
    read_cleaned_wire,
};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::{ReaderProjection, build_projection};
use ln_decode::source_package::{ErrorKind, Limits, Package, Record, capture};
use sha2::{Digest, Sha256};

// ------------------------------------------------------- declared slice #

/// One explicitly named, sha256-pinned tracked fixture.
struct Pinned {
    file: &'static str,
    sha256: &'static str,
}

/// The bounded declared sub-slice: six documents drawn from the 62 top-level
/// fixtures that are at most 1 MiB. Every byte length is below the
/// `Limits::default().max_input_bytes` cap (64 MiB).
const PINNED: &[Pinned] = &[
    Pinned {
        file: "federalnyi-zakon-ot-06-04-2011-n-63-fz-red-ot-31-07-2025-ob-elektronnoi-podpisi--6caf7614.xml",
        sha256: "9608d06982dc1762844c6e0899b11dd3e53f9ced1a3813f940a33fc2153de3ed",
    },
    Pinned {
        file: "postanovlenie-arbitrazhnogo-suda-volgo-vyatskogo-okruga-ot-06-07-2026-n-f01-7581-2026-po-delu-n-a39-5259-2025-trebovanie-o-priznanii-ne--c6b081b3.xml",
        sha256: "f6ec7b1f41654c98509e0eb92fbacc6d73b04d9dce7e106e3fd3345b2a174691",
    },
    Pinned {
        file: "postanovlenie-pravitelstva-rf-ot-12-06-2026-n-737-o-tsentralizatsii-zakupok-otdelnykh-vidov-meditsinskikh-izdelii-dlya-obespecheniya-go--7486d25f.xml",
        sha256: "088e9438fb7059126f07d276aee0a1892e15688201546755ac68e83d51f1bd38",
    },
    Pinned {
        file: "prikaz-fsb-rossii-ot-08-04-2026-n-136-ob-utverzhdenii-perechnya-dokumentov-predstavlyaemykh-v-federalnuyu-sluzhbu-bezopasnosti-rossiisk--9a634157.xml",
        sha256: "eb1fda17132eeb525066d9fc9cfe379820b8228657334001a91ef37e0a7748bd",
    },
    Pinned {
        file: "rasporyazhenie-pravitelstva-rf-ot-16-01-2018-n-21-r-red-ot-27-03-2020-ob-utverzhdenii-perechnya-tovarov-i-uslug-v-otnoshenii-kotorykh-p--0db4e799.xml",
        sha256: "dffd33bcd838e71be62941358e5372f095c0ea1073786e1f002928aeacdd0b9c",
    },
    Pinned {
        file: "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml",
        sha256: "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d",
    },
];

/// The declared slice root: top-level tracked fixtures only.
fn corpus_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../law-source/consultant")
}

/// Every top-level `*.xml` file (non-recursive; `.deprecated/` is a directory
/// and therefore excluded), sorted for determinism.
fn top_level_xml(dir: &Path) -> Vec<PathBuf> {
    let mut files: Vec<PathBuf> = Vec::new();
    for entry in fs::read_dir(dir).unwrap_or_else(|error| panic!("{dir:?}: {error}")) {
        let entry = entry.expect("corpus entry must be readable");
        let path = entry.path();
        if path.is_file() && path.extension().map(|ext| ext == "xml").unwrap_or(false) {
            files.push(path);
        }
    }
    files.sort();
    files
}

// --------------------------------------------------------- preparation #

/// Reads, sha256-pins, captures and projects one pinned fixture. The sha256
/// oracle is computed here from the bytes on disk, not read back from the
/// package, so a content drift fails loud.
fn load_pinned(pin: &Pinned) -> (Package, ReaderProjection) {
    let path = corpus_dir().join(pin.file);
    let xml = fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", pin.file));
    assert!(
        xml.len() as u64 <= Limits::default().max_input_bytes,
        "{}: {} bytes exceeds max_input_bytes",
        pin.file,
        xml.len()
    );
    let digest = format!("{:x}", Sha256::digest(&xml));
    assert_eq!(
        digest, pin.sha256,
        "{}: content drift; re-pin the sha256 oracle",
        pin.file
    );
    let package = capture(&xml, &Limits::default())
        .unwrap_or_else(|error| panic!("{} must capture: {error:?}", pin.file));
    let projection = build_projection(package.records())
        .unwrap_or_else(|error| panic!("{} must project: {error:?}", pin.file));
    (package, projection)
}

/// Handwritten expectation for the three driven declarations. Never derived
/// from `completion_for`, so the two are cross-checked rather than assumed.
fn expected_completion(declaration: ScopeDeclaration) -> WireCompletion {
    match declaration {
        ScopeDeclaration::WholeProjection => WireCompletion::Complete,
        ScopeDeclaration::StructureHold => WireCompletion::Incomplete {
            basis: IncompleteReason::Hold,
            reasons: vec![IncompleteReason::Hold],
        },
        ScopeDeclaration::TextOnlyScope => WireCompletion::Incomplete {
            basis: IncompleteReason::TextOnly,
            reasons: vec![IncompleteReason::TextOnly],
        },
        other => panic!(
            "the declared-slice battery drives only WholeProjection/StructureHold/TextOnlyScope, got {other:?}"
        ),
    }
}

/// The independent decoded-text oracle: rebuilds `id -> value` from the frozen
/// package and proves the read-back carries every substrate text record exactly
/// once, with self-consistent declared counts. It never calls the writer's
/// private text-loss check.
fn assert_text_channel_is_total(package: &Package, readback: &CleanedProjection, file: &str) {
    let substrate: HashMap<&str, &str> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Text(text) => Some((text.id.as_str(), text.value.as_str())),
            Record::Element(_) => None,
        })
        .collect();

    let mut seen: HashMap<&str, ()> = HashMap::new();
    for inline in &readback.inline_texts {
        assert_eq!(
            inline.chars,
            inline.text.chars().count() as u64,
            "{file}: declared text_chars drift for segment {}",
            inline.segment_id
        );
        assert_eq!(
            inline.text_bytes,
            inline.text.len() as u64,
            "{file}: declared text_bytes drift for segment {}",
            inline.segment_id
        );
        let Some(fragment) = &inline.fragment_ref else {
            // Derived segments carry a generated literal, not substrate text.
            continue;
        };
        let expected = substrate.get(fragment.as_str()).unwrap_or_else(|| {
            panic!(
                "{file}: segment {} names fragment {fragment} absent from the substrate",
                inline.segment_id
            )
        });
        assert_eq!(
            inline.text.as_str(),
            *expected,
            "{file}: decoded text drift for fragment {fragment}"
        );
        assert!(
            seen.insert(fragment.as_str(), ()).is_none(),
            "{file}: fragment {fragment} appears more than once in the text channel"
        );
    }

    assert_eq!(
        seen.len(),
        substrate.len(),
        "{file}: the text channel must cover the substrate exactly once"
    );

    let all_chars: u64 = readback.inline_texts.iter().map(|text| text.chars).sum();
    let all_bytes: u64 = readback
        .inline_texts
        .iter()
        .map(|text| text.text_bytes)
        .sum();
    assert_eq!(
        readback.counts.text_chars, all_chars,
        "{file}: footer text_chars must equal the recomputed sum"
    );
    assert_eq!(
        readback.counts.text_bytes, all_bytes,
        "{file}: footer text_bytes must equal the recomputed sum"
    );
}

// ------------------------------------------------------------- slice shape #

#[test]
fn declared_slice_is_82_top_level_xml_within_the_input_cap() {
    let dir = corpus_dir();
    let files = top_level_xml(&dir);
    assert_eq!(
        files.len(),
        82,
        "the declared slice is exactly the 82 top-level law-source/consultant/*.xml fixtures"
    );
    for path in &files {
        let size = fs::metadata(path)
            .unwrap_or_else(|error| panic!("{path:?}: {error}"))
            .len();
        assert!(
            size <= Limits::default().max_input_bytes,
            "{path:?}: {size} bytes exceeds max_input_bytes"
        );
    }
}

// ------------------------------------------------- text safety + markers #

#[test]
fn hold_and_text_only_keep_decoded_text_on_the_declared_slice() {
    for pin in PINNED {
        let (package, projection) = load_pinned(pin);
        let class = gate_reader(package.records())
            .unwrap_or_else(|error| panic!("{} must gate as supported WordML: {error}", pin.file));
        assert_eq!(class, ReaderSourceClass::SupportedWordml, "{}", pin.file);

        for declaration in [
            ScopeDeclaration::WholeProjection,
            ScopeDeclaration::StructureHold,
            ScopeDeclaration::TextOnlyScope,
        ] {
            let expected = expected_completion(declaration);
            // T01 mapping and the honest source correction are both no-ops for a
            // supported WordML source that declares the whole projection.
            assert_eq!(completion_for(declaration), expected, "{}", pin.file);
            assert_eq!(
                classify_completion(class, declaration),
                expected,
                "{}: supported WordML must not be corrected for {declaration:?}",
                pin.file
            );

            let artifact =
                export_cleaned_projection(&package, &projection, &expected, &WireLimits::default())
                    .unwrap_or_else(|error| {
                        panic!("{} must export {declaration:?}: {error}", pin.file)
                    });

            // Determinism: equal inputs yield byte-identical output.
            let repeat =
                export_cleaned_projection(&package, &projection, &expected, &WireLimits::default())
                    .unwrap_or_else(|error| {
                        panic!("{} must re-export {declaration:?}: {error}", pin.file)
                    });
            assert_eq!(
                artifact, repeat,
                "{}: {declaration:?} export must be byte-identical",
                pin.file
            );

            let readback = read_cleaned_wire(&artifact).unwrap_or_else(|error| {
                panic!("{} must read back {declaration:?}: {error}", pin.file)
            });
            assert_eq!(
                readback.completion, expected,
                "{}: {declaration:?} completion marker must survive the round-trip",
                pin.file
            );
            if let WireCompletion::Incomplete { reasons, .. } = &readback.completion {
                assert!(
                    !reasons.is_empty(),
                    "{}: an incomplete export must carry non-empty reasons",
                    pin.file
                );
            }

            verify_cleaned_wire(&artifact, &package).unwrap_or_else(|findings| {
                panic!(
                    "{}: independent verification must accept the {declaration:?} artifact: {:?}",
                    pin.file,
                    findings
                        .iter()
                        .map(|finding| finding.code)
                        .collect::<Vec<_>>()
                )
            });

            // Independent text-channel traversal — the proof that Hold/TextOnly
            // do not lose decoded text even though the writer's text-loss check
            // runs on the `Complete` branch only.
            assert_text_channel_is_total(&package, &readback, pin.file);

            // S03 connection: navigation resolves on the incomplete artifact too.
            let index = build_nav_index_from_wire(&artifact, &package).unwrap_or_else(|error| {
                panic!("{}: must index {declaration:?}: {error}", pin.file)
            });
            verify_nav_index(&index, &readback, &package).unwrap_or_else(|findings| {
                panic!(
                    "{}: navigation verification must accept {declaration:?}: {:?}",
                    pin.file,
                    findings
                        .iter()
                        .map(|finding| finding.code)
                        .collect::<Vec<_>>()
                )
            });
        }
    }
}

// ------------------------------------------------------------- atomicity #

fn has_tmp(dir: &Path) -> bool {
    fs::read_dir(dir)
        .expect("temp dir must be readable")
        .filter_map(Result::ok)
        .any(|entry| entry.file_name().to_string_lossy().ends_with(".tmp"))
}

fn unique_temp_dir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "ln-decode-cleaned-corpus-t03-{}-{tag}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp corpus root must be creatable");
    dir
}

#[test]
fn atomic_publication_is_readable_and_leaves_no_tmp() {
    let pin = &PINNED[4];
    let (package, projection) = load_pinned(pin);
    let artifact = export_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .unwrap_or_else(|error| panic!("{} must export: {error}", pin.file));

    let dir = unique_temp_dir("atomic");
    let out = dir.join("cleaned.jsonl");
    write_cleaned_projection_atomic(&out, &artifact)
        .unwrap_or_else(|error| panic!("atomic publication must succeed: {}", error.detail()));

    let published = fs::read_to_string(&out).expect("published artifact must be readable");
    assert_eq!(published, artifact, "publication must be byte-faithful");
    assert!(
        read_cleaned_wire(&published).is_ok(),
        "the published artifact must read back"
    );
    assert!(
        !has_tmp(&dir),
        "no *.tmp may survive a successful publication"
    );

    // A second publication overwrites in place and still leaves no tmp.
    write_cleaned_projection_atomic(&out, &artifact).expect("overwrite must succeed");
    assert_eq!(
        fs::read_to_string(&out).expect("overwritten artifact must be readable"),
        artifact
    );
    assert!(!has_tmp(&dir), "no *.tmp may survive an overwrite");

    let _ = fs::remove_dir_all(&dir);
}

// ---------------------------------------------- out-of-band fresh sweep #

/// Full declared-slice runner: every one of the 82 top-level fixtures is
/// attempted. A fixture whose expanded package stays within the fail-closed
/// serialized-package cap (512 MiB) must capture, gate as supported WordML,
/// project and round-trip a `Complete` artifact; a fixture whose expanded
/// package exceeds that cap is recorded as a closed `PackageTooLarge` outcome
/// rather than silently accepted or skipped. This is `#[ignore]`d out-of-band:
/// the sweep does not fit the 600 s evidence cap (MEM1488). It logs counters and
/// file names only, never raw decoded text.
#[test]
#[ignore = "out-of-band full-82 sweep exceeds the 600s gsd_exec evidence cap (MEM1488)"]
fn full_declared_slice_captures_gates_projects_and_exports() {
    let dir = corpus_dir();
    let files = top_level_xml(&dir);
    assert_eq!(files.len(), 82);

    let mut captured = 0u64;
    let mut oversized = 0u64;
    let mut oversized_files: Vec<String> = Vec::new();
    let mut gated = 0u64;
    let mut projected = 0u64;
    let mut exported = 0u64;
    let mut elements = 0u64;
    let mut fragments = 0u64;

    for path in &files {
        let xml = fs::read(path).unwrap_or_else(|error| panic!("{path:?}: {error}"));
        assert!(xml.len() as u64 <= Limits::default().max_input_bytes);
        let package = match capture(&xml, &Limits::default()) {
            Ok(package) => package,
            // The declared slice is bounded by input bytes (64 MiB), but the
            // canonical serialized package has its own fail-closed cap
            // (512 MiB). A fixture above that cap is an honest boundary result,
            // not a panic: it is recorded and never accepted as captured.
            Err(error) if error.kind() == ErrorKind::PackageTooLarge => {
                oversized += 1;
                oversized_files.push(
                    path.file_name()
                        .map(|name| name.to_string_lossy().into_owned())
                        .unwrap_or_default(),
                );
                continue;
            }
            Err(error) => panic!("{path:?} must capture: {error:?}"),
        };
        captured += 1;
        let class = gate_reader(package.records())
            .unwrap_or_else(|error| panic!("{path:?} must gate: {error}"));
        assert_eq!(class, ReaderSourceClass::SupportedWordml, "{path:?}");
        gated += 1;
        let projection = build_projection(package.records())
            .unwrap_or_else(|error| panic!("{path:?} must project: {error:?}"));
        projected += 1;

        let artifact = export_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .unwrap_or_else(|error| panic!("{path:?} must export: {error}"));
        assert!(read_cleaned_wire(&artifact).is_ok(), "{path:?} read-back");
        verify_cleaned_wire(&artifact, &package)
            .unwrap_or_else(|findings| panic!("{path:?}: {:?}", findings.len()));
        exported += 1;

        for record in package.records() {
            match record {
                Record::Element(_) => elements += 1,
                Record::Text(_) => fragments += 1,
            }
        }
    }

    assert_eq!(
        captured + oversized,
        files.len() as u64,
        "every declared fixture is either captured or recorded as oversized"
    );
    println!(
        "cleaned_projection_corpus: files={} captured={} oversized={} gated={} projected={} exported={} elements={} fragments={}",
        files.len(),
        captured,
        oversized,
        gated,
        projected,
        exported,
        elements,
        fragments
    );
    if !oversized_files.is_empty() {
        println!(
            "cleaned_projection_corpus: oversized (declared package cap) = {oversized_files:?}"
        );
    }
}
