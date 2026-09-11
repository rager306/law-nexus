use std::path::Path;

use ln_consultant_parser::corpus_sample::{
    classify_path, classify_relative, CorpusRoot, SourceRootKind, WorkFamilyProvenance,
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
