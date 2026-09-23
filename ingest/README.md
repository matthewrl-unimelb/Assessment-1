# Ingestion pipeline

Turns the scanned judgment into the vector database the app queries. Run once, offline, by the developer. Every output is committed to the repo, so the deployed app never re-runs any of this.

| Step | Script | Input → output | What happens |
|---|---|---|---|
| 1. OCR | `ocr.py` | `cameron_1974_scr_1062.pdf` → `ocr_pages.json` | The PDF is a scanned image with no text layer. Each page is OCR'd with Tesseract; only the English column is read, and running headers are dropped. |
| 2. Clean | `clean.py` | `ocr_pages.json` → `paragraphs.json`, `cameron_clean.md` | Rebuilds the 42 paragraphs (with page numbers), undoes line-end hyphenation, separates the footnote, and applies a listed set of OCR corrections. |
| 3a. Suggest chunks | `suggest_chunks.py` | `paragraphs.json` → `chunk_plan_llm.json` | gpt-4o proposes a grouping of paragraphs into chunks, following my chunking rules (in the prompt). |
| 3b. Review | *(manual)* | `chunk_plan_llm.json` → `chunk_plan.json` | I checked the AI's plan against my rules and corrected it. Corrections are marked "Manual Edit" in `chunk_plan.json`. |
| 3c. Build chunks | `chunk.py` | `chunk_plan.json` → `chunks.json` | Checks every paragraph is used exactly once, joins the paragraphs, and adds a context header (case, speaker, topic, pages, who the parties are) to each chunk. |
| 4. Embed and store | `build_db.py` | `chunks.json` → `chroma_db/` | Embeds each chunk with `text-embedding-3-large` and stores it in a persistent Chroma collection. |
| 5. Evaluate | `evaluate.py` | chunks + `test_questions.json` → `eval_results.md` | Compares naive fixed-size chunking with my chunks, with and without context headers, on 18 test questions. |

## Re-running

Steps 1 and 2 need `tesseract` and `pdftoppm` installed. Their outputs are already in `data/`, so they don't need re-running. Steps 3c to 5 can be re-run from the repo root:

```bash
python ingest/chunk.py
python ingest/build_db.py
python ingest/evaluate.py
```

Only re-run `suggest_chunks.py` to regenerate the AI's suggestion. It writes to `chunk_plan_llm.json` and never touches the reviewed `chunk_plan.json`.

## Files worth reading

- `data/cameron_clean.md`: the cleaned judgment, plus the list of every OCR correction applied.
- `data/chunk_plan_llm.json` vs `data/chunk_plan.json`: what the AI suggested vs the final plan.
- `data/eval_results.md`: the retrieval evaluation.