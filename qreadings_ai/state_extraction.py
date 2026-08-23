"""Conservative extraction of explicit QREADINGS research-state labels.

This module does not infer new claims. It only recognises labels already
present in source structure and records them as metadata for retrieval.
"""

from __future__ import annotations

import re
from typing import Any


LABEL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hypothesis_a", ("hypothesis a",)),
    ("hypothesis_b", ("hypothesis b",)),
    ("current_decision", ("current decision",)),
    ("future_validation", ("future validation",)),
    ("preserve_ambiguity", ("preserve ambiguity",)),
    ("competing_evidence", ("competing evidence",)),
    ("provisional", ("provisional",)),
    ("falsifiable", ("falsifiable",)),
)


def explicit_state_labels(text: str) -> set[str]:
    lowered = text.lower()
    labels: set[str] = set()
    for label, phrases in LABEL_PATTERNS:
        if any(phrase in lowered for phrase in phrases):
            labels.add(label)
    return labels


def section_evidence_type(section: str, content: str) -> str:
    lowered = f"{section}\n{content}".lower()
    if "hypothesis a" in lowered or "hypothesis b" in lowered:
        return "hypothesis"
    if "current decision" in lowered:
        return "current_decision"
    if "future validation" in lowered:
        return "future_validation"
    if "preserve ambiguity" in lowered:
        return "methodological_rule"
    if "translation note" in lowered:
        return "translation_note"
    if "word of the day" in lowered:
        return "lexical_note"
    return "source"


def passage_metadata(section: str, content: str) -> dict[str, Any]:
    labels = explicit_state_labels(f"{section}\n{content}")
    return {
        "state_labels": sorted(labels),
        "section_label": section,
        "has_hypothesis_a": "hypothesis_a" in labels,
        "has_hypothesis_b": "hypothesis_b" in labels,
        "has_current_decision": "current_decision" in labels,
        "has_future_validation": "future_validation" in labels,
        "has_translation_note": "translation note" in content.lower(),
        "has_lexical_note": "word of the day" in content.lower()
        or "qur'anic word of the day" in content.lower(),
    }
