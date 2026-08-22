"""Conservative ingestion of the QREADINGS repository into structured memory.

The ingester does not ask an LLM to interpret the corpus. It stores source
material as evidence and only creates concepts/relations from fields or
headings that are explicitly present in the source. Longitudinal translation
history is handled separately as reconstruction trajectories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .memory import Memory
from .state import Evidence
from .trajectory import parse_translation_history

INCLUDE_DIRS = (
    "specification",
    "algorithms",
    "research_log",
    "references",
    "corpora",
    "case_studies",
    "conceptual_library",
)


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()
    return f"ingest:{digest[:24]}"


def chunk_markdown(text: str, max_chars: int = 6000) -> list[str]:
    """Split Markdown primarily at headings, then by size."""
    sections = re.split(r"(?=^#{1,6}\s+)", text, flags=re.MULTILINE)
    chunks: list[str] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(section)
            continue
        for start in range(0, len(section), max_chars):
            piece = section[start:start + max_chars].strip()
            if piece:
                chunks.append(piece)
    return chunks


def ingest_markdown(path: Path, memory: Memory, root: Path) -> int:
    text = path.read_text(encoding="utf-8")
    source = path.relative_to(root).as_posix()
    chunks = chunk_markdown(text)
    for index, chunk in enumerate(chunks):
        evidence = Evidence(
            id=stable_id(source, str(index)),
            source=source,
            content=chunk,
            strength=1.0,
        )
        memory.add_evidence(f"corpus:{source}", evidence)
        memory.add_passage(
            source,
            f"chunk:{index}",
            chunk,
            evidence_type="source",
            metadata={"chunk_index": str(index)},
            passage_id=stable_id("passage", source, str(index)),
        )

    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE):
        name = heading.strip()
        if not name or name.lower() in {"readme", "contents"}:
            continue
        memory.upsert_concept(
            name,
            description=f"Explicit heading from {source}",
            confidence=0.35,
            payload={"source": source, "kind": "heading"},
        )
    return len(chunks)


def _record_evidence(record: dict[str, Any], source: str, index: int, memory: Memory) -> None:
    content = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)
    evidence = Evidence(
        id=stable_id(source, str(index)),
        source=source,
        content=content,
        strength=1.0,
    )
    memory.add_evidence(f"corpus:{source}", evidence)
    memory.add_passage(
        source,
        f"record:{index}",
        content,
        evidence_type="corpus_record",
        metadata={"record_index": str(index)},
        passage_id=stable_id("passage", source, str(index)),
    )


def ingest_json(path: Path, memory: Memory, root: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    source = path.relative_to(root).as_posix()
    records = data if isinstance(data, list) else [data]

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _record_evidence({"value": record}, source, index, memory)
            continue

        _record_evidence(record, source, index, memory)

        designation = record.get("designation")
        if isinstance(designation, str) and designation.strip():
            description = ""
            for field in ("morphology", "syntax", "immediate_context", "observational_notes"):
                value = record.get(field)
                if value:
                    description += f"{field}: {value}\n"
            designation_id = memory.upsert_concept(
                designation.strip(),
                description=description.strip(),
                confidence=0.55,
                payload={"source": source, "record_index": index, "verse": record.get("verse")},
            )

            context = record.get("immediate_context")
            if isinstance(context, str) and context.strip():
                context_id = memory.upsert_concept(
                    context.strip(),
                    description=f"Explicit immediate_context in {source}",
                    confidence=0.45,
                    payload={"source": source, "record_index": index, "kind": "context"},
                )
                memory.add_relation(
                    designation_id,
                    "occurs_in_context",
                    context_id,
                    payload={"source": source, "record_index": index},
                )

            pairing = record.get("pairing")
            if isinstance(pairing, list):
                for paired in pairing:
                    if not isinstance(paired, str) or not paired.strip():
                        continue
                    paired_id = memory.upsert_concept(
                        paired.strip(),
                        description=f"Explicit pairing in {source}",
                        confidence=0.4,
                        payload={"source": source, "record_index": index, "kind": "pairing"},
                    )
                    memory.add_relation(
                        designation_id,
                        "paired_with",
                        paired_id,
                        payload={"source": source, "record_index": index},
                    )
    return len(records)


def ingest_translation_history(
    path: str | Path,
    memory: Memory,
    *,
    source_label: str | None = None,
) -> int:
    """Ingest a longitudinal QREADINGS translation-history document."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    source = source_label or path.name
    versions = parse_translation_history(text, source_path=source)
    for version in versions:
        memory.add_reconstruction_version(version)
        memory.add_passage(
            source,
            version.title,
            version.raw_text,
            evidence_type="reconstruction_version",
            metadata={
                "entry_id": version.entry_id,
                "entry_type": version.entry_type,
                "day_number": str(version.day_number) if version.day_number is not None else "",
                "reference": version.reference or "",
                "trajectory_key": version.trajectory_key or "",
            },
            passage_id=stable_id("translation-history", version.entry_id),
        )
    return len(versions)


def ingest_repository(
    root: str | Path,
    db_path: str | Path = "qreadings_ai.db",
    *,
    translation_history: str | Path | None = None,
) -> dict[str, int]:
    root = Path(root).resolve()
    memory = Memory(db_path)
    stats = {
        "markdown_files": 0,
        "json_files": 0,
        "evidence_chunks": 0,
        "json_records": 0,
        "translation_history_entries": 0,
    }
    try:
        for directory in INCLUDE_DIRS:
            base = root / directory
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                if path.suffix.lower() == ".md":
                    stats["markdown_files"] += 1
                    stats["evidence_chunks"] += ingest_markdown(path, memory, root)
                elif path.suffix.lower() == ".json":
                    stats["json_files"] += 1
                    stats["json_records"] += ingest_json(path, memory, root)

        if translation_history is not None:
            stats["translation_history_entries"] = ingest_translation_history(
                translation_history,
                memory,
            )
    finally:
        memory.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a QREADINGS checkout into SQLite memory.")
    parser.add_argument("root", nargs="?", default=".", help="Path to the QREADINGS repository")
    parser.add_argument("--db", default="qreadings_ai.db", help="SQLite database path")
    parser.add_argument(
        "--translation-history",
        help="Optional path to a longitudinal QREADINGS translation-history text file",
    )
    args = parser.parse_args()
    stats = ingest_repository(args.root, args.db, translation_history=args.translation_history)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
