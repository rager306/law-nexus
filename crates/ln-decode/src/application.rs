use crate::domain::{
    fingerprint_bytes, BlockDecodeError, DecodeCategory, DecodeRequest, DecodeResult, DiagnosticId,
    ParsedBlock, SafeDiagnostic, StructuralCandidate,
};
use crate::ports::{BlockDecoderPort, DecoderPort, DiagnosticPort};

/// Atomic provider-block decoding use case.
pub struct DecodeBlocks<D> {
    decoder: D,
}

impl<D> DecodeBlocks<D>
where
    D: BlockDecoderPort,
{
    pub fn new(decoder: D) -> Self {
        Self { decoder }
    }

    pub fn execute(&self, request: &DecodeRequest) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
        self.decoder.decode_blocks(request)
    }
}

/// Outward decode boundary. Accepts only structural candidates with anchors.
/// Gate-owned claims and raw payload context are rejected by policy.
pub struct DecodeAndAnchor<D, G> {
    decoder: D,
    diagnostics: G,
}

impl<D, G> DecodeAndAnchor<D, G>
where
    D: DecoderPort,
    G: DiagnosticPort,
{
    pub fn new(decoder: D, diagnostics: G) -> Self {
        Self {
            decoder,
            diagnostics,
        }
    }

    pub fn execute(&mut self, request: DecodeRequest) -> DecodeResult {
        let emissions = self.decoder.decode(&request);
        let mut candidates = Vec::new();
        let mut rejected = Vec::new();

        for emission in emissions {
            if emission.category.is_structural() {
                if let (Some(candidate_id), Some(anchor)) = (emission.candidate_id, emission.anchor)
                {
                    candidates.push(StructuralCandidate {
                        candidate_id,
                        category: DecodeCategory::StructuralCandidate,
                        anchor,
                    });
                } else {
                    rejected.push(DecodeCategory::StructuralCandidate);
                }
            } else {
                rejected.push(emission.category);
            }
            // Never accept raw_context into diagnostics.
            let _ = emission.raw_context;
        }

        let fingerprint = fingerprint_bytes(&request.bytes);
        let positive = SafeDiagnostic {
            diagnostic_id: DiagnosticId::parse("diag:positive-control").expect("static id"),
            category: "decode-positive-control".to_owned(),
            positive_control: true,
            byte_count: request.bytes.len(),
            fingerprint: fingerprint.clone(),
        };
        self.diagnostics.record(positive.clone());

        if !rejected.is_empty() {
            let reject = SafeDiagnostic {
                diagnostic_id: DiagnosticId::parse("diag:rejected-emission").expect("static id"),
                category: "decode-rejected-non-structural".to_owned(),
                positive_control: false,
                byte_count: request.bytes.len(),
                fingerprint,
            };
            self.diagnostics.record(reject);
        }

        let diagnostics = self.diagnostics.events().to_vec();
        // Input may intentionally contain a canary. Leak check is output-only.
        let debug_blob = format!("{candidates:?}{diagnostics:?}");
        let raw_payload_absent = !debug_blob.contains("CANARY::")
            && !debug_blob.contains("SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK");

        DecodeResult {
            payload_ref: request.payload_ref,
            candidates,
            rejected_categories: rejected,
            diagnostics,
            verified_assertion_absent: true,
            merged_identity_absent: true,
            unregistered_relation_absent: true,
            raw_payload_absent,
        }
    }

    pub fn diagnostics(&self) -> &[SafeDiagnostic] {
        self.diagnostics.events()
    }
}
