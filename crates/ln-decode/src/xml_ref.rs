//! Shared fail-closed XML 1.0 general/character reference resolution for `quick-xml` 0.42.

use std::borrow::Cow;

use quick_xml::escape::resolve_xml_entity;
use quick_xml::events::BytesRef;

/// Resolves an XML 1.0 numeric character reference or one of the five
/// predefined XML entities (`lt`, `gt`, `amp`, `quot`, `apos`).
///
/// Returns `None` for invalid character references (including `&#0;`) and any
/// unknown or custom entity reference.
pub(crate) fn resolve_xml_general_ref(reference: &BytesRef<'_>) -> Option<Cow<'static, str>> {
    if let Some(ch) = reference.resolve_char_ref().ok()? {
        return Some(Cow::Owned(ch.to_string()));
    }
    resolve_xml_entity(reference.as_ref()).map(Cow::Borrowed)
}
