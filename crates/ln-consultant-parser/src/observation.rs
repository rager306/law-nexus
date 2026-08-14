//! Observation store: collect unknown links as learning backlog.
//! Unknown links (no template matched) are grouped by link text and
//! recorded for agent review. The agent proposes new YAML templates.

use crate::classifier::ClassifiedLink;
use std::collections::HashMap;

/// An observation of an unresolvable link pattern.
#[derive(Debug, Clone, PartialEq)]
pub struct Observation {
    pub link_text: String,
    pub occurrences: usize,
    pub context_sample: String,
    pub unique_dests: usize,
    pub status: String,
}

/// Collect unknown-classified links into grouped observations.
/// Links with the same text are merged; context sample from first occurrence.
pub fn collect_observations(classified: &[ClassifiedLink]) -> Vec<Observation> {
    let mut groups: HashMap<String, (usize, String, std::collections::HashSet<String>)> =
        HashMap::new();

    for c in classified.iter().filter(|c| c.kind == "unknown") {
        let entry = groups
            .entry(c.text.clone())
            .or_insert_with(|| (0, c.context.clone(), std::collections::HashSet::new()));
        entry.0 += 1;
        entry.2.insert(c.dest.clone());
    }

    let mut observations: Vec<Observation> = groups
        .into_iter()
        .map(|(text, (count, sample, dests))| Observation {
            link_text: text,
            occurrences: count,
            context_sample: sample,
            unique_dests: dests.len(),
            status: "candidate".to_owned(),
        })
        .collect();

    // Sort by occurrences descending — most frequent first
    observations.sort_by(|a, b| b.occurrences.cmp(&a.occurrences));
    observations
}

/// Format observations as YAML for the observation store file.
pub fn format_observations_yaml(observations: &[Observation]) -> String {
    let mut out = String::from("# Parser observations — auto-generated learning backlog\n");
    out.push_str("# Agent reviews these and proposes new classifier_templates\n\n");
    for obs in observations.iter().take(50) {
        out.push_str(&format!(
            "- link_text: \"{}\"\n  occurrences: {}\n  unique_dests: {}\n  status: {}\n\n",
            obs.link_text, obs.occurrences, obs.unique_dests, obs.status
        ));
    }
    if observations.len() > 50 {
        out.push_str(&format!(
            "# ... {} more observations omitted\n",
            observations.len() - 50
        ));
    }
    out
}
