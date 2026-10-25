//! Contract suite for the export-bank → normativity closed vocabulary
//! (ADR-0030 D2, D667).
//!
//! Pins the closed bank set, the fail-closed `Unknown` class, the CTV barrier
//! table, `bank_of` behaviour on real manifest paths, and the corpus accounting
//! invariant on a bounded fixture count — no corpus read, no I/O, no SQLite.
//!
//! Negative surface (Q7): an unrecognized bank (`unknown`, `""`, whitespace,
//! catalog-only `ARB`) must classify as `Unknown` rather than silently folding
//! into `NonNormative`; `Unknown` must not block CTV; and the four known banks
//! must partition the fixture total exactly.

use ln_kb_ontology::bank_normativity::{
    BankNormativity, KNOWN_BANKS, bank_normativity, bank_of, ctv_blocked_by_bank,
};

/// Per-bank entry counts from the S02 corpus manifest header
/// (`m223-s02-corpus-inventory/v1.subdirs`): bounded fixture, not a corpus read.
const COURTS: u64 = 5667;
const FAS: u64 = 30399;
const NPA: u64 = 916;
const XML: u64 = 6803;
const TOTAL: u64 = 43785;

#[test]
fn known_banks_is_a_closed_four_bank_set() {
    assert_eq!(KNOWN_BANKS, ["courts", "fas", "npa", "xml"]);
    // Every member is classified and none is Unknown.
    for bank in KNOWN_BANKS {
        assert_ne!(bank_normativity(bank), BankNormativity::Unknown);
    }
}

#[test]
fn closed_set_over_four_known_banks() {
    // normative == {npa, xml}
    assert_eq!(bank_normativity("npa"), BankNormativity::Normative);
    assert_eq!(bank_normativity("xml"), BankNormativity::Normative);
    assert_eq!(bank_normativity("NPA"), BankNormativity::Normative);
    assert_eq!(bank_normativity(" XML "), BankNormativity::Normative);
    // non-normative == {courts, fas}
    assert_eq!(bank_normativity("courts"), BankNormativity::NonNormative);
    assert_eq!(bank_normativity("fas"), BankNormativity::NonNormative);
    assert_eq!(bank_normativity("FAS"), BankNormativity::NonNormative);
    assert_eq!(
        bank_normativity("  Courts  "),
        BankNormativity::NonNormative
    );
}

#[test]
fn unknown_is_fail_closed_not_a_silent_default() {
    for candidate in ["unknown", "", "   ", "ARB", "consultant", "npa2", "xmls"] {
        assert_eq!(
            bank_normativity(candidate),
            BankNormativity::Unknown,
            "bank {:?} must fail closed to Unknown",
            candidate
        );
    }
}

#[test]
fn as_str_is_the_stable_artifact_contract() {
    assert_eq!(BankNormativity::Normative.as_str(), "normative");
    assert_eq!(BankNormativity::NonNormative.as_str(), "non-normative");
    assert_eq!(BankNormativity::Unknown.as_str(), "unknown");
    // Display mirrors as_str.
    assert_eq!(BankNormativity::NonNormative.to_string(), "non-normative");
}

#[test]
fn ctv_barrier_table_only_blocks_non_normative() {
    assert!(ctv_blocked_by_bank(BankNormativity::NonNormative));
    assert!(!ctv_blocked_by_bank(BankNormativity::Normative));
    // DP2/D667: a structural Unknown is not legal non-normativity, so it must
    // NOT block CTV (protects normative fixture paths like law-source/...).
    assert!(!ctv_blocked_by_bank(BankNormativity::Unknown));
}

#[test]
fn bank_of_reads_the_export_bucket_from_real_manifest_paths() {
    assert_eq!(
        bank_of("fas/decision_2025-01-09_04-10-18-1-17-2025_rev-unknown_d9958419.xml"),
        "fas"
    );
    assert_eq!(
        bank_of("xml/law/100074/edition-9d2bae8b54bef059d81de10e.xml"),
        "xml"
    );
    assert_eq!(
        bank_of("courts/acn/000166280-edition-84232bdf5e80b4c2d012dbae.xml"),
        "courts"
    );
    assert_eq!(
        bank_of("npa/decree_2020-09-14_558_rev-2024-07-08_a6d600ea.xml"),
        "npa"
    );
    // Slash-less / empty paths are returned as-is (never a default bank).
    assert_eq!(bank_of("bare.xml"), "bare.xml");
    assert_eq!(bank_of(""), "");
}

#[test]
fn fixture_counts_partition_the_total_and_split_normativity() {
    assert_eq!(COURTS + FAS + NPA + XML, TOTAL);

    let normative = [NPA, XML].iter().sum::<u64>();
    let non_normative = [COURTS, FAS].iter().sum::<u64>();
    assert_eq!(normative, 7719);
    assert_eq!(non_normative, 36066);
    assert_eq!(normative + non_normative, TOTAL);

    // Each bank's fixture bucket maps to its class, and the class totals match
    // the per-bank sums — the coverage invariant S04 builds on.
    let by_class = |bank: BankNormativity| -> u64 {
        [(COURTS, "courts"), (FAS, "fas"), (NPA, "npa"), (XML, "xml")]
            .iter()
            .filter(|(_, id)| bank_normativity(id) == bank)
            .map(|(n, _)| *n)
            .sum()
    };
    assert_eq!(by_class(BankNormativity::Normative), normative);
    assert_eq!(by_class(BankNormativity::NonNormative), non_normative);
    assert_eq!(by_class(BankNormativity::Unknown), 0);
}

#[test]
fn every_known_bank_round_trips_through_bank_of() {
    for bank in KNOWN_BANKS {
        let path = format!("{bank}/some/doc.xml");
        assert_eq!(bank_of(&path), bank);
        assert_ne!(bank_normativity(bank_of(&path)), BankNormativity::Unknown);
    }
}
