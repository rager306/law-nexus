use crate::domain::{DecodeRequest, DecoderEmission, SafeDiagnostic};

pub trait DecoderPort {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission>;
}

pub trait DiagnosticPort {
    fn record(&mut self, event: SafeDiagnostic);
    fn events(&self) -> &[SafeDiagnostic];
}
