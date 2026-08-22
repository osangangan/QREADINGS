"""Parsing and representation of longitudinal QREADINGS translation history.

This module treats a translation-history document as a sequence of
reconstructions, not as a flat source document. It preserves provenance and
revision metadata without deciding which version is correct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable


ENTRY_RE = re.compile(
    r"^(?P<kind>QReading Day|SPECIAL READING|POSSIBLE READINGS)\s*(?P<number>\d+)?\s*$",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(
    r"^(Chapter\s+\d+\s+Vers(?:e|es)\s+[0-9–-]+(?:\s*\([^)]+\))?\s*(?:of the Qur.?an)?|\d+:\d+(?:[–-]\d+)?)\s*$",
    re.IGNORECASE,
)

STOP_MARKERS = (
    "QReading Day",
    "SPECIAL READING",
    "POSSIBLE READINGS",
    "ROUND ONE",
    "ROUND TWO",
)


@dataclass
class ReconstructionVersion:
    entry_id: str
    entry_type: str
    ordinal: int
    day_number: int | None
    title: str
    reference: str | None
    translation: str
    word_of_day: str | None = None
    translation_note: str | None = None
    theme: str | None = None
    raw_text: str = ""
    source_path: str = ""
    trajectory_key: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def _clean_lines(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        line = line.strip()
        if line in {"---", "_"}:
            continue
        if line and not line.startswith("#quran") and not line.startswith("#ProjectQ"):
            cleaned.append(line)
    return cleaned


def _find_reference(lines: list[str]) -> tuple[int | None, str | None]:
    for index, line in enumerate(lines):
        if REFERENCE_RE.match(line):
            return index, line
        if re.match(r"^Chapter\s+\d+\s+Vers", line, re.IGNORECASE):
            return index, line
    return None, None


def _extract_between(lines: list[str], start: int, markers: tuple[str, ...]) -> tuple[list[str], int]:
    result: list[str] = []
    index = start
    while index < len(lines):
        line = lines[index]
        if line.upper() in {marker.upper() for marker in markers}:
            break
        result.append(line)
        index += 1
    return result, index


def _normalise_reference(reference: str | None) -> str | None:
    if not reference:
        return None
    value = reference.strip()
    match = re.search(r"Chapter\s+(\d+)\s+Vers(?:e|es)\s+([0-9–-]+)", value, re.IGNORECASE)
    if match:
        return f"{match.group(1)}:{match.group(2).replace('-', '–')}"
    return value


def parse_translation_history(text: str, *, source_path: str = "") -> list[ReconstructionVersion]:
    """Parse the recurring entry structure found in the supplied history file."""
    lines = text.splitlines()
    starts: list[tuple[int, str, int | None]] = []
    for index, raw in enumerate(lines):
        match = ENTRY_RE.match(raw.strip())
        if not match:
            continue
        kind = match.group("kind").lower()
        number = int(match.group("number")) if match.group("number") else None
        starts.append((index, kind, number))

    versions: list[ReconstructionVersion] = []
    for ordinal, (start, kind, number) in enumerate(starts):
        end = starts[ordinal + 1][0] if ordinal + 1 < len(starts) else len(lines)
        raw_lines = _clean_lines(lines[start:end])
        if not raw_lines:
            continue

        reference_index, reference = _find_reference(raw_lines)
        if reference_index is None:
            continue

        body_start = reference_index + 1
        body = raw_lines[body_start:]

        note_index = next(
            (i for i, line in enumerate(body) if line.upper() == "NOTE ON TRANSLATION"),
            None,
        )
        word_index = next(
            (i for i, line in enumerate(body) if line.upper() in {"WORD OF THE DAY", "QUR'ANIC WORD OF THE DAY", "QUR’ANIC WORD OF THE DAY", "QURANIC WORD OF THE DAY"}),
            None,
        )
        outro_index = next((i for i, line in enumerate(body) if line.upper() in {"OUTRO", "INTRO"}), None)

        cut_points = [i for i in (note_index, word_index, outro_index) if i is not None]
        translation_end = min(cut_points) if cut_points else len(body)
        translation_lines = body[:translation_end]

        # Remove short social/greeting artefacts that may occur before the actual verse.
        translation_lines = [
            line for line in translation_lines
            if line.lower() not in {"this is a translation of the arabic qur’an.", "this is a translation of the arabic qur'an."}
        ]

        lexical_note = None
        if word_index is not None:
            next_index = min([i for i in (note_index, outro_index) if i is not None and i > word_index] or [len(body)])
            word_lines = body[word_index + 1:next_index]
            lexical_note = " ".join(word_lines).strip() or None

        translation_note = None
        if note_index is not None:
            next_index = min([i for i in (outro_index,) if i is not None and i > note_index] or [len(body)])
            note_lines = body[note_index + 1:next_index]
            translation_note = " ".join(note_lines).strip() or None

        theme = None
        pre_reference = raw_lines[:reference_index]
        theme_candidates = [
            line for line in pre_reference
            if "theme" in line.lower() or "next few days" in line.lower()
        ]
        if theme_candidates:
            theme = theme_candidates[-1]

        entry_type = {
            "qreading day": "qreading_day",
            "special reading": "special_reading",
            "possible readings": "possible_readings",
        }.get(kind, kind.replace(" ", "_"))

        trajectory_key = _normalise_reference(reference)
        entry_id = f"translation-history:{entry_type}:{number or 'x'}:{ordinal}"
        versions.append(
            ReconstructionVersion(
                entry_id=entry_id,
                entry_type=entry_type,
                ordinal=ordinal,
                day_number=number if entry_type == "qreading_day" else None,
                title=f"{kind.title()} {number}" if number is not None else kind.title(),
                reference=reference,
                translation="\n".join(translation_lines).strip(),
                word_of_day=lexical_note,
                translation_note=translation_note,
                theme=theme,
                raw_text="\n".join(raw_lines),
                source_path=source_path,
                trajectory_key=trajectory_key,
                metadata={"source_ordinal": str(ordinal)},
            )
        )

    return versions
