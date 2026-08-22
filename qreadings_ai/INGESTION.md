# QREADINGS corpus ingestion

The ingestion layer treats the repository as a source corpus rather than as a ready-made truth set.

## First-pass rules

1. Markdown is stored as evidence, split primarily by headings.
2. Markdown headings become low-confidence concepts because they are explicit labels.
3. JSON records are stored as evidence.
4. Explicit fields such as `designation`, `immediate_context`, and `pairing` become concepts or relations.
5. The ingester does not ask an LLM to infer meanings, merge concepts, or resolve hypotheses.
6. Provenance is retained through source paths and record indexes.
7. Evidence passages preserve an explicit type such as `specification`, `hypothesis`, `case_study`, or `corpus`.

## Retrieval

The cognitive engine can retrieve source passages as well as concepts and graph relations. Retrieval is deliberately lexical in this phase, keeping the system small and deterministic enough to inspect on an 8 GB laptop.

Each retrieved passage carries:

- source path;
- section or record location;
- evidence type;
- matched relevance score;
- source metadata where available.

The model is instructed to treat retrieved material as supporting context rather than unquestionable authority. This preserves the QREADINGS distinction between source evidence, hypotheses, working principles, and specifications.

## Local ingestion

Run it from the repository root:

```bash
python -m qreadings_ai.ingest . --db qreadings_ai.db
```

The resulting SQLite database is disposable derived state. The source corpus in Git remains authoritative for the project's current documents.

## Intended next step

Once retrieval is stable, we can add a small embedding index as an optional accelerator. That should improve semantic recall without replacing provenance-aware lexical retrieval or making embeddings the source of truth.
