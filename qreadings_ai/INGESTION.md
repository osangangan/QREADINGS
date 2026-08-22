# QREADINGS corpus ingestion

The ingestion layer treats the repository as a source corpus rather than as a ready-made truth set.

## First-pass rules

1. Markdown is stored as evidence, split primarily by headings.
2. Markdown headings become low-confidence concepts because they are explicit labels.
3. JSON records are stored as evidence.
4. Explicit fields such as `designation`, `immediate_context`, and `pairing` become concepts or relations.
5. The ingester does not ask an LLM to infer meanings, merge concepts, or resolve hypotheses.
6. Provenance is retained through source paths and record indexes.

Run it locally from the repository root:

```bash
python -m qreadings_ai.ingest . --db qreadings_ai.db
```

The resulting SQLite database is disposable derived state. The source corpus in Git remains authoritative for the project's current documents.

## Intended next step

Add evidence retrieval to the cognitive prompt so a query can retrieve both explicit concept relations and the most relevant source passages. Only after that retrieval path is stable should embeddings or model-assisted concept extraction be introduced.
