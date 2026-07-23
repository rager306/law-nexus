use crate::domain::{
    fingerprint_bytes, AnchorId, CandidateId, DecodeCategory, DecodeRequest, DecoderEmission,
    EvidenceAnchor, SafeDiagnostic,
};
use crate::ports::{DecoderPort, DiagnosticPort};

#[derive(Debug, Default)]
pub struct InMemoryDiagnosticSink {
    events: Vec<SafeDiagnostic>,
}

impl DiagnosticPort for InMemoryDiagnosticSink {
    fn record(&mut self, event: SafeDiagnostic) {
        self.events.push(event);
    }

    fn events(&self) -> &[SafeDiagnostic] {
        &self.events
    }
}

/// Honest decoder: emits one structural candidate with an exact byte-range anchor.
#[derive(Debug, Default)]
pub struct HonestSyntheticDecoder;

impl DecoderPort for HonestSyntheticDecoder {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission> {
        let end = request.bytes.len().min(32);
        let slice = &request.bytes[..end];
        vec![DecoderEmission {
            category: DecodeCategory::StructuralCandidate,
            candidate_id: Some(CandidateId::parse("cand:1").expect("static id")),
            anchor: Some(EvidenceAnchor {
                anchor_id: AnchorId::parse("anchor:1").expect("static id"),
                start_offset: 0,
                end_offset: end,
                fingerprint: fingerprint_bytes(slice),
            }),
            raw_context: None,
        }]
    }
}

/// Malicious decoder: tries to emit gate-owned claims and raw failure context.
#[derive(Debug, Default)]
pub struct MaliciousSyntheticDecoder;

impl DecoderPort for MaliciousSyntheticDecoder {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission> {
        let canary = String::from_utf8_lossy(&request.bytes).into_owned();
        vec![
            DecoderEmission {
                category: DecodeCategory::VerifiedAssertion,
                candidate_id: Some(CandidateId::parse("cand:verified").expect("static id")),
                anchor: None,
                raw_context: Some(canary.clone()),
            },
            DecoderEmission {
                category: DecodeCategory::MergedIdentity,
                candidate_id: Some(CandidateId::parse("cand:merged").expect("static id")),
                anchor: None,
                raw_context: Some(canary.clone()),
            },
            DecoderEmission {
                category: DecodeCategory::UnregisteredRelation,
                candidate_id: Some(CandidateId::parse("cand:rel").expect("static id")),
                anchor: None,
                raw_context: Some(canary.clone()),
            },
            DecoderEmission {
                category: DecodeCategory::RawFailureContext,
                candidate_id: None,
                anchor: None,
                raw_context: Some(canary),
            },
        ]
    }
}
