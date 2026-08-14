//! Extract `w:hlink` elements from Consultant WordML XML bytes.
//! Zero-dependency: uses simple string scanning, not an XML parser.

use crate::raw_link::RawLink;

/// Extract all hyperlinks from WordML XML bytes.
/// Returns a vector of `RawLink` with dest and visible text.
pub fn extract_hyperlinks(xml: &[u8]) -> Vec<RawLink> {
    let text = std::str::from_utf8(xml).unwrap_or("");
    let mut links = Vec::new();
    let mut search_from = 0;

    while let Some(hlink_start) = text[search_from..].find("<w:hlink") {
        let abs_start = search_from + hlink_start;

        // Find w:dest attribute
        let dest = extract_attr(text, abs_start, "w:dest");

        // Find closing </w:hlink>
        if let Some(close_pos) = text[abs_start..].find("</w:hlink>") {
            let inner = &text[abs_start..abs_start + close_pos];
            // Extract visible text from <w:t> elements
            let link_text = extract_text_content(inner);

            if let Some(dest) = dest {
                links.push(RawLink {
                    dest,
                    text: link_text,
                });
            }
            search_from = abs_start + close_pos + 10; // length of "</w:hlink>"
        } else {
            break;
        }
    }

    links
}

fn extract_attr(xml: &str, start: usize, attr_name: &str) -> Option<String> {
    let pattern = format!("{attr_name}=\"");
    let attr_start = xml[start..].find(&pattern)? + start;
    let value_start = attr_start + pattern.len();
    let value_end = xml[value_start..].find('"')? + value_start;
    Some(xml[value_start..value_end].to_owned())
}

fn extract_text_content(xml: &str) -> String {
    let mut result = String::new();
    let mut search = 0;
    while let Some(open) = xml[search..].find("<w:t") {
        let abs_open = search + open;
        if let Some(gt) = xml[abs_open..].find('>') {
            let text_start = abs_open + gt + 1;
            if let Some(close) = xml[text_start..].find("</w:t>") {
                result.push_str(&xml[text_start..text_start + close]);
                search = text_start + close + 6;
            } else {
                break;
            }
        } else {
            break;
        }
    }
    result
}
