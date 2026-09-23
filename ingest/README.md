# Ingestion pipeline

Turns the scanned judgment into the vector database the app queries. Run once, offline, by the developer. Every output is committed, so the deployed app never re-runs any of this.

| Step | Script | Input → output | Needs |
|---|---|---|---|
| 1. OCR | `ocr.py` | `cameron_1974_scr_1062.pdf` → `ocr_pages.json` | `tesseract`, `pdftoppm` (`brew install tesseract poppler`) |
| 2. Clean | `clean.py` | `ocr_pages.json` → `paragraphs.json`, `cameron_clean.md` | – |
| 3. Chunk | `chunk.py` | `paragraphs.json` → `chunks.json`, `chunks_preview.md` | `tiktoken` |
| 4. Embed + store | `build_db.py` | `chunks.json` → `chroma_db/` | OpenAI key |
| 5. Evaluate | `evaluate.py` | chunks + `test_questions.json` → `eval_results.md` | OpenAI key |

Steps 1–3 are already done, and their outputs are in `data/`. To rebuild the database and evaluation, from the repo root:

```bash
python ingest/build_db.py
python ingest/evaluate.py
```

Proof-reading files: `data/cameron_clean.md` (the cleaned text plus the list of every OCR correction) and `data/chunks_preview.md` (exactly what gets embedded, chunk by chunk).
