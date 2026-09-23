import chromadb
from openai import OpenAI

from core.config import CHAT_MODEL, CHROMA_PATH, COLLECTION, EMBED_MODEL, TOP_K


def retrieve(client, question, k=TOP_K):
    """Find the k chunks most similar to the question."""
    # 1. Turn the question into a vector (list of numbers), using the SAME model as the chunks
    vector = client.embeddings.create(model=EMBED_MODEL, input=question).data[0].embedding

    # 2. Open the database and search it
    db = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = db.get_collection(COLLECTION)
    results = collection.query(query_embeddings=[vector], n_results=k)

    # 3. Tidy the results into a simple list
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "title": results["metadatas"][0][i]["title"],
            "voice": results["metadatas"][0][i]["voice"],
            "page_label": results["metadatas"][0][i]["page_label"],
            "similarity": round(1 - results["distances"][0][i], 3),
        })
    return chunks


# The four levels a user can choose, and how gpt-4o should pitch the answer for each
LEVELS = {
    "New to tax": (
        "The reader has no tax or legal background. Up to about 220 words. "
        "Write as if explaining to a smart friend: plain everyday words, no legal jargon "
        "(say 'company' not 'corporate entity', 'the tax office' not 'the Minister'). "
        "If an idea is abstract, one short everyday analogy can help, but only if it genuinely makes it clearer."
    ),
    "Familiar, no formal training": (
        "The reader understands everyday tax ideas (income, tax returns, companies) but has no formal training. "
        "Around 250-300 words. Explain any legal term briefly the first time it appears. "
        "Focus on what happened and why it mattered to the tax outcome."
    ),
    "Law or tax student": (
        "The reader is a law or tax student. Around 300-400 words. Use correct legal terminology. "
        "Where the question involves the Court's reasoning, show how the legal test was applied to the facts and name any authority relied on. "
        "Always be precise about whose words you are relying on: the Court, the trial judge, or the headnote."
    ),
    "Tax professional (CPA / tax lawyer)": (
        "The reader is a tax professional. Up to about 250 words. Dense and technical; don't explain basic concepts. "
        "Prioritise the ratio, the precise test, the evidence the outcome turned on, and practical significance for structuring, "
        "but only as far as they are relevant to the question and supported by this judgment."
    ),
}

SYSTEM_PROMPT = """You answer questions about one Supreme Court of Canada judgment: MNR v Cameron [1974] SCR 1062.

Rules:
- Answer ONLY from the passages provided below. Do not use outside knowledge about the case or later law.
- If the passages do not contain the answer, say clearly that the judgment does not address it. Do not guess.
- Fit the shape of your answer to the question: answer factual questions directly; give analysis only when the question asks about reasoning. Use headings or bullet points only if the question genuinely has several parts.
- In this case the appellant is the Minister of National Revenue and the respondent is James A. Cameron (the taxpayer).
- Some passages are the law reporter's headnote, not the Court's words. If you rely on one, say so.
- In the trial judge's findings (pp 1068-1069), "I" is the trial judge, not Martland J.
- Cite pinpoint pages in brackets, e.g. (p 1065).
- Fit the shape of your answer to the question: answer factual questions directly; give analysis only when the question asks about reasoning. Use headings or bullet points only if the question genuinely has several parts.

How to pitch your answer: {level_instruction}"""


def answer(client, question, level, history=None):
    """Retrieve the best chunks, then ask gpt-4o to answer at the chosen level."""
    chunks = retrieve(client, question)

    # Put the retrieved passages into one block of text, each labelled with its source
    passages = ""
    for c in chunks:
        passages += f"[{c['title']} - {c['voice']} - {c['page_label']}]\n{c['text']}\n\n"

    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(level_instruction=LEVELS[level])}]
    if history:
        messages += history  # earlier questions and answers in this chat
    reminder = f"Remember who you are writing for: {LEVELS[level]}"
    messages.append({"role": "user", "content": f"Passages from the judgment:\n\n{passages}\nQuestion: {question}\n\n{reminder}"})
    

    response = client.chat.completions.create(model=CHAT_MODEL, messages=messages, temperature=0.2)
    return response.choices[0].message.content, chunks


# This part only runs when you run this file directly, for testing
if __name__ == "__main__":
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as f:
        key = tomllib.load(f)["OPENAI_API_KEY"]
    client = OpenAI(api_key=key)

    question = "Why wasn't the agreement a sham?"
    for level in LEVELS:
        reply, sources = answer(client, question, level)
        print("=====", level, "=====")
        print(reply, "\n")