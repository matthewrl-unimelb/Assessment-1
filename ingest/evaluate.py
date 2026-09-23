"""
Step 5 (evidence): does structure-aware chunking actually retrieve better?

Compares three chunking strategies on the same test questions
(data/test_questions.json), using the same embedding model and the same
number of retrieved chunks (TOP_K):

  A. naive       - fixed windows of 150 words with a 30-word overlap, cut
                   straight through the cleaned text (the tutorial default:
                   ignores paragraphs, quotations and the headnote).
  B. structured  - our CHUNK_MAP chunks, embedding the chunk text only.
  C. structured + context headers - our chunks, embedding header + text
                   (this is what the app actually uses).

A question counts as a "hit" if any of the top-K retrieved chunks contains
one of the answer phrases listed for it. Out-of-scope questions are listed
separately with the best similarity score, which should be noticeably lower.

Output: data/eval_results.md (paste into the README) and a printed table.
Cost: a few thousand embedding tokens - well under one US cent.

Usage:  python ingest/evaluate.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from openai import OpenAI

from core.config import CHUNKS_PATH, EMBED_MODEL, ROOT, TOP_K, get_api_key

PARAGRAPHS = ROOT / "data" / "paragraphs.json"
QUESTIONS = ROOT / "data" / "test_questions.json"
OUT = ROOT / "data" / "eval_results.md"

NAIVE_WORDS, NAIVE_OVERLAP = 150, 30


def norm(s: str) -> str:
    return " ".join(s.replace("’", "'").replace("‘", "'").lower().split())


def naive_chunks() -> list[dict]:
    words = " ".join(p["text"] for p in json.loads(PARAGRAPHS.read_text())).split()
    out, start, n = [], 0, 0
    while start < len(words):
        n += 1
        text = " ".join(words[start:start + NAIVE_WORDS])
        out.append({"id": f"N{n:02d}", "text": text, "embed": text})
        start += NAIVE_WORDS - NAIVE_OVERLAP
    return out


def structured_chunks(with_headers: bool) -> list[dict]:
    return [{"id": c["id"], "text": c["text"], "embed": c["embed_text"] if with_headers else c["text"]}
            for c in json.loads(CHUNKS_PATH.read_text())]


def embed(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def run_strategy(name, chunks, questions, q_vecs, client, db):
    col = db.create_collection(name=name, metadata={"hnsw:space": "cosine"})
    col.add(ids=[c["id"] for c in chunks], embeddings=embed(client, [c["embed"] for c in chunks]),
            documents=[c["text"] for c in chunks])
    rows = []
    for q, vec in zip(questions, q_vecs):
        res = col.query(query_embeddings=[vec], n_results=TOP_K)
        docs, dists = res["documents"][0], res["distances"][0]
        rank = next((i + 1 for i, d in enumerate(docs)
                     if any(norm(a) in norm(d) for a in q["answer_any"])), None)
        rows.append({"id": q["id"], "rank": rank, "best_sim": round(1 - dists[0], 3),
                     "top_ids": res["ids"][0]})
    return rows


def main() -> None:
    key = get_api_key()
    if not key:
        sys.exit("No OPENAI_API_KEY found (env var, .env or .streamlit/secrets.toml).")
    client = OpenAI(api_key=key)
    questions = json.loads(QUESTIONS.read_text())
    q_vecs = embed(client, [q["question"] for q in questions])
    db = chromadb.EphemeralClient()

    strategies = {
        "A. Naive (150-word windows)": naive_chunks(),
        "B. Structured, text only": structured_chunks(with_headers=False),
        "C. Structured + context headers": structured_chunks(with_headers=True),
    }
    results = {}
    for i, (name, chunks) in enumerate(strategies.items()):
        results[name] = run_strategy(f"strategy_{i}", chunks, questions, q_vecs, client, db)

    answerable = [q for q in questions if q["answerable"]]
    lines = ["# Retrieval evaluation\n",
             f"Embedding model `{EMBED_MODEL}`, top-{TOP_K} retrieval, {len(answerable)} answerable "
             f"test questions + {len(questions) - len(answerable)} out-of-scope questions.\n",
             "| Strategy | Chunks | Hit@1 | Hit@" + str(TOP_K) + " | Mean rank of first hit |",
             "|---|---|---|---|---|"]
    for name, rows in results.items():
        ans = [r for r, q in zip(rows, questions) if q["answerable"]]
        hit1 = sum(1 for r in ans if r["rank"] == 1)
        hitk = sum(1 for r in ans if r["rank"])
        ranks = [r["rank"] for r in ans if r["rank"]]
        mean = f"{sum(ranks) / len(ranks):.2f}" if ranks else "–"
        lines.append(f"| {name} | {len(strategies[name])} | {hit1}/{len(ans)} | {hitk}/{len(ans)} | {mean} |")

    lines += ["\n## Per-question results (rank of first chunk containing the answer; – = missed)\n",
              "| Q | Question | " + " | ".join(n.split('.')[0] for n in results) + " |",
              "|---|---|" + "---|" * len(results)]
    for i, q in enumerate(questions):
        cells = []
        for rows in results.values():
            r = rows[i]
            cells.append(f"sim {r['best_sim']}" if not q["answerable"] else (str(r["rank"]) if r["rank"] else "–"))
        tag = "" if q["answerable"] else " *(out of scope)*"
        lines.append(f"| {q['id']} | {q['question']}{tag} | " + " | ".join(cells) + " |")

    ans_sims = [r["best_sim"] for r, q in zip(results["C. Structured + context headers"], questions) if q["answerable"]]
    oos_sims = [r["best_sim"] for r, q in zip(results["C. Structured + context headers"], questions) if not q["answerable"]]
    lines.append(f"\nFor strategy C, the best similarity averaged {sum(ans_sims) / len(ans_sims):.3f} on answerable "
                 f"questions vs {sum(oos_sims) / len(oos_sims):.3f} on out-of-scope ones.")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
