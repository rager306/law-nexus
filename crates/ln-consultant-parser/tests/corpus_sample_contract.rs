use std::path::Path;

use std::collections::BTreeSet;

use ln_consultant_parser::corpus_sample::{
    classify_path, classify_relative, draw, draw_with_c3_families, CorpusRoot, DrawPlan,
    SampleCandidate, SourceRootKind, WorkFamilyProvenance,
};

#[test]
fn relocation_does_not_change_relative_metadata() {
    let relative = Path::new("npa/law_2013-04-05_44-fz/edition-0002_rev-2024-07-02_deadbeef.xml");
    let left = classify_path(
        &Path::new("/tmp/law-nexus-2099/export").join(relative),
        Path::new("/tmp/law-nexus-2099/export"),
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    let right = classify_path(
        &Path::new("/tmp/relocated/law-source").join(relative),
        Path::new("/tmp/relocated/law-source"),
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    assert_eq!(left, right);
    assert_eq!(left.year, Some(2013));
    assert_eq!(left.document_type, "law");
    assert_eq!(
        left.work_family.provenance,
        WorkFamilyProvenance::NpaDirectory
    );
}

#[test]
fn absolute_prefix_cannot_invent_year_or_document_type() {
    let meta = classify_path(
        Path::new("/root/law-nexus/2099/courts/acn/000166280-edition-c0c8875a.xml"),
        Path::new("/root/law-nexus/2099"),
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    assert_eq!(meta.year, None);
    assert_eq!(meta.document_type, "courts-unspecified");
    assert_eq!(meta.work_family.key, "acn/000166280");
}

#[test]
fn provider_comes_from_root_membership_not_filename_needles() {
    let consultant = classify_path(
        Path::new("/corpus/garant/courts/appeal/abc.xml"),
        Path::new("/corpus/garant"),
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    assert_eq!(consultant.provider, SourceRootKind::ConsultantExport);
    assert_eq!(consultant.document_type, "courts-unspecified");

    let garant = classify_path(
        Path::new("/corpus/garant/Постановление от 15 октября 2022 г.odt"),
        Path::new("/corpus/garant"),
        SourceRootKind::Garant,
    )
    .unwrap();
    assert_eq!(garant.provider, SourceRootKind::Garant);
    assert_eq!(garant.year, Some(2022));
    assert_eq!(garant.document_type, "resolution");
}

#[test]
fn documented_families_are_provider_qualified_and_unknown_is_unique() {
    let npa = classify_relative(
        "npa/law_2013-04-05_44-fz/edition-0001_rev-2013-07-02.xml",
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    let xml = classify_relative(
        "xml/law/act-44/edition-0001.xml",
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    let court = classify_relative(
        "courts/acn/000166280-edition-c0c8875a.xml",
        SourceRootKind::ConsultantExport,
    )
    .unwrap();
    assert_eq!(npa.work_family.key, "law_2013-04-05_44-fz");
    assert_eq!(xml.work_family.key, "act-44");
    assert_eq!(court.work_family.provenance, WorkFamilyProvenance::CourtId);
    assert_ne!(npa.work_family, xml.work_family);

    let first = classify_relative("misc/one.bin", SourceRootKind::ConsultantExport).unwrap();
    let second = classify_relative("misc/two.bin", SourceRootKind::ConsultantExport).unwrap();
    assert_eq!(first.document_type, "unknown");
    assert_eq!(
        first.work_family.provenance,
        WorkFamilyProvenance::UnknownRelativePath
    );
    assert_ne!(first.work_family, second.work_family);
}

#[test]
fn seeded_draw_is_reproducible_nested_and_seed_sensitive() {
    let inventory: Vec<_> = (0..1_000)
        .map(|i| {
            let relative_path = format!("courts/acn/{i:06}-edition-{i:064x}.xml");
            let meta = classify_relative(&relative_path, SourceRootKind::ConsultantExport).unwrap();
            SampleCandidate {
                relative_path,
                content_hash: format!("sha256:{i:064x}"),
                meta,
            }
        })
        .collect();
    let empty = BTreeSet::new();
    let a100 = draw(inventory.clone(), &empty, 100, 20308).unwrap();
    let a400 = draw(inventory.clone(), &empty, 400, 20308).unwrap();
    let a800 = draw(inventory.clone(), &empty, 800, 20308).unwrap();
    let hashes = |plan: &DrawPlan| {
        plan.candidates
            .iter()
            .map(|c| c.content_hash.clone())
            .collect::<Vec<_>>()
    };
    assert_eq!(hashes(&a100), hashes(&a400)[..100]);
    assert_eq!(hashes(&a400), hashes(&a800)[..400]);
    assert_ne!(
        a100.candidates
            .iter()
            .map(|c| &c.content_hash)
            .collect::<BTreeSet<_>>(),
        draw(inventory.clone(), &empty, 100, 1)
            .unwrap()
            .candidates
            .iter()
            .map(|c| &c.content_hash)
            .collect::<BTreeSet<_>>()
    );
    let reversed = inventory.into_iter().rev().collect::<Vec<_>>();
    assert_eq!(
        hashes(&a400),
        hashes(&draw(reversed, &empty, 400, 20308).unwrap())
    );
}

#[test]
fn draw_excludes_c3_hashes_and_reports_duplicates_and_family_leakage() {
    let mut inventory = Vec::new();
    for edition in 0..3 {
        let relative_path =
            format!("npa/law_2013-04-05_44-fz/edition-{edition:04}_rev-2013-07-02.xml");
        let meta = classify_relative(&relative_path, SourceRootKind::ConsultantExport).unwrap();
        inventory.push(SampleCandidate {
            relative_path,
            content_hash: format!("sha256:{:064x}", edition + 1),
            meta,
        });
    }
    let duplicate = inventory[0].clone();
    inventory.push(duplicate);
    let c3 = BTreeSet::from([inventory[1].content_hash.clone()]);
    let c3_family = vec![inventory[1].meta.work_family.clone()];
    let plan = draw_with_c3_families(inventory, &c3, &c3_family, 1, 20308).unwrap();
    assert_eq!(plan.candidates.len(), 1);
    assert_eq!(plan.leakage.exact_duplicate_hashes, 1);
    assert_eq!(plan.leakage.excluded_c3_hashes, 1);
    assert_eq!(plan.leakage.collapsed_editions, 1);
    assert_eq!(plan.leakage.collapsed_families, 1);
    assert_eq!(plan.leakage.c3_family_overlap, 2);
    assert!(plan.leakage.not_year_type_stratified);
}

#[test]
fn garant_cap_is_observed_and_shortage_is_fail_closed() {
    let mut inventory = Vec::new();
    for i in 0..8 {
        let relative_path = format!("Постановление от 15 октября 2022 г N {i}.odt");
        let meta = classify_relative(&relative_path, SourceRootKind::Garant).unwrap();
        inventory.push(SampleCandidate {
            relative_path,
            content_hash: format!("sha256:{:064x}", i + 10),
            meta,
        });
    }
    for i in 0..10 {
        let relative_path = format!("courts/acn/{i:06}-edition-{i:064x}.xml");
        let meta = classify_relative(&relative_path, SourceRootKind::ConsultantExport).unwrap();
        inventory.push(SampleCandidate {
            relative_path,
            content_hash: format!("sha256:{:064x}", i + 100),
            meta,
        });
    }
    let plan = draw(inventory, &BTreeSet::new(), 10, 20308).unwrap();
    assert_eq!(plan.leakage.garant_selected, 4);
    assert_eq!(plan.leakage.garant_cap, 4);
    assert!(draw(Vec::new(), &BTreeSet::new(), 1, 20308).is_err());
}

#[test]
fn malformed_hash_is_rejected_before_draw() {
    let relative_path = "courts/acn/1.xml".to_owned();
    let meta = classify_relative(&relative_path, SourceRootKind::ConsultantExport).unwrap();
    let candidate = SampleCandidate {
        relative_path,
        content_hash: "sha256:not-a-hash".into(),
        meta,
    };
    assert!(draw([candidate], &BTreeSet::new(), 1, 20308).is_err());
}

#[test]
fn hostile_roots_and_traversal_fail_closed() {
    assert!(CorpusRoot::new("law-source/consultant", SourceRootKind::ConsultantExport).is_err());
    assert!(classify_relative("../courts/abc.xml", SourceRootKind::ConsultantExport).is_err());
    assert!(classify_path(
        Path::new("/corpus/other/courts/abc.xml"),
        Path::new("/corpus/export"),
        SourceRootKind::ConsultantExport,
    )
    .is_err());
}
