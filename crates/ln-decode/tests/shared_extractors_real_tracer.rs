use std::{fs, path::PathBuf};

use ln_decode::{
    adapters::{garant_odt::GarantOdtBlockDecoder, ConsultantWordMlBlockDecoder},
    deontic::{extract_deontic_lexemes, DeonticLexemeKind},
    domain::{
        fingerprint_bytes, DecodeRequest, FamilyFormat, ParagraphStyle, ParsedBlock, PayloadRef,
    },
    ports::BlockDecoderPort,
    references::{extract_reference_mentions, ReferenceMentionKind},
    temporal::{extract_temporal_phrases, TemporalPhraseKind},
};

const CONSULTANT_FIXTURE: &str = "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
const GARANT_FIXTURE: &str = "law-source/garant/44-fz.odt";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Census {
    blocks: usize,
    provider_comments: usize,
    article_mentions: usize,
    point_mentions: usize,
    enters_force_phrases: usize,
    loses_force_phrases: usize,
    obligation_lexemes: usize,
    permission_lexemes: usize,
    prohibition_lexemes: usize,
    negated_deontic_lexemes: usize,
}

fn fixture_path(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(relative)
}

fn census(blocks: &[ParsedBlock]) -> Census {
    let mut result = Census {
        blocks: blocks.len(),
        provider_comments: 0,
        article_mentions: 0,
        point_mentions: 0,
        enters_force_phrases: 0,
        loses_force_phrases: 0,
        obligation_lexemes: 0,
        permission_lexemes: 0,
        prohibition_lexemes: 0,
        negated_deontic_lexemes: 0,
    };
    for block in blocks {
        result.provider_comments += usize::from(block.style() == ParagraphStyle::ProviderComment);
        for mention in extract_reference_mentions(block) {
            match mention.kind() {
                ReferenceMentionKind::Article => result.article_mentions += 1,
                ReferenceMentionKind::Point => result.point_mentions += 1,
            }
        }
        for phrase in extract_temporal_phrases(block) {
            match phrase.kind() {
                TemporalPhraseKind::EntersIntoForce => result.enters_force_phrases += 1,
                TemporalPhraseKind::LosesForce => result.loses_force_phrases += 1,
            }
        }
        for lexeme in extract_deontic_lexemes(block) {
            match lexeme.kind() {
                DeonticLexemeKind::Obligation => result.obligation_lexemes += 1,
                DeonticLexemeKind::Permission => result.permission_lexemes += 1,
                DeonticLexemeKind::Prohibition => result.prohibition_lexemes += 1,
            }
            result.negated_deontic_lexemes += usize::from(lexeme.negated());
        }
    }
    result
}

fn request(payload: &str, family: &str, bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse(payload).unwrap(),
        FamilyFormat::parse(family).unwrap(),
        bytes,
    )
}

#[test]
fn tracked_real_sources_have_repeat_deterministic_bounded_censuses() {
    let consultant_bytes = fs::read(fixture_path(CONSULTANT_FIXTURE)).unwrap();
    let consultant_request = request(
        "payload:m134-consultant-census",
        "family:consultant-wordml",
        &consultant_bytes,
    );
    let consultant_first = ConsultantWordMlBlockDecoder
        .decode_blocks(&consultant_request)
        .unwrap();
    let consultant_second = ConsultantWordMlBlockDecoder
        .decode_blocks(&consultant_request)
        .unwrap();
    let consultant_census = census(&consultant_first);
    assert_eq!(consultant_first, consultant_second);
    assert_eq!(consultant_census, census(&consultant_second));
    assert_eq!(
        consultant_census,
        Census {
            blocks: 167,
            provider_comments: 0,
            article_mentions: 53,
            point_mentions: 16,
            enters_force_phrases: 1,
            loses_force_phrases: 0,
            obligation_lexemes: 0,
            permission_lexemes: 4,
            prohibition_lexemes: 0,
            negated_deontic_lexemes: 1,
        }
    );

    let garant_bytes = fs::read(fixture_path(GARANT_FIXTURE)).unwrap();
    let garant_request = request(
        "payload:m134-garant-census",
        "family:garant-odt",
        &garant_bytes,
    );
    let garant_first = GarantOdtBlockDecoder
        .decode_blocks(&garant_request)
        .unwrap();
    let garant_second = GarantOdtBlockDecoder
        .decode_blocks(&garant_request)
        .unwrap();
    let garant_census = census(&garant_first);
    assert_eq!(garant_first, garant_second);
    assert_eq!(garant_census, census(&garant_second));
    assert_eq!(
        garant_census,
        Census {
            blocks: 5_124,
            provider_comments: 355,
            article_mentions: 976,
            point_mentions: 906,
            enters_force_phrases: 9,
            loses_force_phrases: 27,
            obligation_lexemes: 50,
            permission_lexemes: 176,
            prohibition_lexemes: 2,
            negated_deontic_lexemes: 10,
        }
    );

    eprintln!(
        "M134_CENSUS consultant_bytes={} consultant_fingerprint={} consultant={consultant_census:?} garant_bytes={} garant_fingerprint={} garant={garant_census:?}",
        consultant_bytes.len(),
        fingerprint_bytes(&consultant_bytes),
        garant_bytes.len(),
        fingerprint_bytes(&garant_bytes),
    );
}
