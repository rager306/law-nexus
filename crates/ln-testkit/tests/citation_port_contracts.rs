//! Shared CitationSourcePort contracts (ADR-0015 / M146).

use ln_citation::adapters::{HostileMirrorRelabeler, InMemoryCitationSource};
use ln_citation::domain::SourceAuthority;
use ln_testkit::{
    assert_citation_source_contract, assert_hostile_mirror_fails_honest_citation_contract,
};

fn honest_fixture() -> InMemoryCitationSource {
    InMemoryCitationSource::new()
        .with(
            "src:contract-known",
            "anchor:contract-1",
            SourceAuthority::Official,
        )
        .with(
            "src:contract-mirror",
            "anchor:contract-2",
            SourceAuthority::Mirror,
        )
}

#[test]
fn in_memory_citation_source_satisfies_shared_port_contract() {
    let source = honest_fixture();
    assert_citation_source_contract(&source);
}

#[test]
fn hostile_mirror_relabeler_fails_honest_authority_preservation() {
    let hostile = HostileMirrorRelabeler::new().with("src:contract-mirror", "anchor:contract-2");
    assert_hostile_mirror_fails_honest_citation_contract(&hostile);
}
