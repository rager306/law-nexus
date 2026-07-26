use crate::domain::{
    BlockDecodeError, DecodeRequest, DecoderEmission, ParsedBlock, SafeDiagnostic,
};

/// Fallible provider adapter boundary for atomic block decoding.
pub trait BlockDecoderPort {
    fn decode_blocks(&self, request: &DecodeRequest) -> Result<Vec<ParsedBlock>, BlockDecodeError>;
}

pub trait DecoderPort {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission>;
}

pub trait DiagnosticPort {
    fn record(&mut self, event: SafeDiagnostic);
    fn events(&self) -> &[SafeDiagnostic];
}
