"""
Step 4 of the ingestion pipeline: embed the chunks and store them in Chroma.

Input : data/chunks.json (from ingest/chunk.py)
Output: chroma_db/       (a persistent Chroma vector database, committed to git)

Each chunk's `embed_text` (context header + text) is embedded with OpenAI's
text-embedding-3-small. The chunk's plain `text` is stored as the document
(that is what the app shows users and passes to the LLM), and everything else
(title, voice, pages...) is stored as metadata so the app can label sources.

The database is built once, here, with the developer's key. The deployed app
only embeds each user question (with the same model) and queries this DB.

Usage:  python ingest/build_db.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from openai import OpenAI

from core.config import CHROMA_PATH, CHUNKS_PATH, COLLECTION, EMBED_MODEL, get_api_key


def main() -> None:
    key = get_api_key()
    if not key:
        sys.exit("No OPENAI_API_KEY found (env var, .env or .streamlit/secrets.toml).")
    client = OpenAI(api_key=key)

    chunks = json.loads(CHUNKS_PATH.read_text())
    print(f"embedding {len(chunks)} chunks with {EMBED_MODEL} ...")
    resp = client.embeddings.create(model=EMBED_MODEL, input=[c["embed_text"] for c in chunks])
    vectors = [d.embedding for d in resp.data]

    # rebuild from scratch so the DB always matches chunks.json exactly
    if CHROMA_PATH.exists():
        shutil.rmtree(CHROMA_PATH)
    db = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = db.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine", "embed_model": EMBED_MODEL},
    )
    col.add(
        ids=[c["id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[{
            "title": c["title"],
            "voice": c["voice"],
            "voice_label": c["voice_label"],
            "page_label": c["page_label"],
            "pages": ",".join(str(p) for p in c["pages"]),
            "order": c["order"],
            "has_quotation": c["has_quotation"],
            "tokens": c["tokens"],
        } for c in chunks],
    )
    print(f"stored {col.count()} chunks in {CHROMA_PATH.name}/ (collection '{COLLECTION}')")


if __name__ == "__main__":
    main()
