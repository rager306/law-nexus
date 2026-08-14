//! Raw hyperlink extracted from Consultant WordML XML.
//! Not yet classified — just the dest token and visible text.

/// A raw hyperlink from a `w:hlink` element in WordML.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawLink {
    /// Full `w:dest` value, e.g. `consultantplus://offline/ref=E0A0...`
    pub dest: String,
    /// Visible text inside the hyperlink element.
    pub text: String,
}

impl RawLink {
    /// Returns true if this is an internal ConsultantPlus reference.
    pub fn is_internal(&self) -> bool {
        self.dest.starts_with("consultantplus://")
    }

    /// Returns true if this is an external web link.
    pub fn is_external(&self) -> bool {
        self.dest.starts_with("http")
    }

    /// Extract the consid token from an internal link.
    pub fn consid(&self) -> Option<&str> {
        self.dest.strip_prefix("consultantplus://offline/ref=")
    }
}
