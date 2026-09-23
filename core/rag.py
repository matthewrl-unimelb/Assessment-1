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
        "The user has NO tax or legal background. "
        "Maximum 250 words. No legal jargon at all: say 'company' not 'corporate entity', 'ownership' not 'equity interest', 'the tax office' not 'the Minister'. "
        "Start with a one-sentence plain answer, then ONE everyday analogy (e.g. family, sport, a small shop). "
        "Only one page citation, at the end."
    ),
    "Familiar, no formal training": (
        "The user knows everyday tax ideas (income, tax returns, companies) but has no formal training. "
        "250-300 words. Explain any legal term the first time you use it, in brackets. "
        "Structure: what happened, then why it mattered for the tax outcome."
    ),
    "Law or tax student": (
        "The user is a law or tax student. 300-400 words. Use correct legal terminology. "
        "Use these headings: Issue, Rule, Application, Conclusion. "
        "Name the authority relied on (e.g. Snook v London & West Riding Investments) and distinguish the Court's words from the trial judge's findings and the headnote."
    ),
    "Tax professional (CPA / tax lawyer)": (
        "The user is a tax professional. Maximum 250 words, dense and technical, no explanations of basic terms. "
        "Use short bullet points under these labels: Ratio, Test applied, Evidentiary basis, Planning significance. "
        "Planning significance must be limited to what this judgment itself supports; do not cite later law."
    ),
}

SYSTEM_PROMPT = """You answer questions about one Supreme Court of Canada judgment: MNR v Cameron [1974] SCR 1062.

Rules:
- Answer ONLY from the passages provided below. Do not use outside knowledge about the case or later law.
- If the passages do not contain the answer, say clearly that the judgment does not address it. Do not guess.
- In this case the appellant is the Minister of National Revenue and the respondent is James A. Cameron (the taxpayer).
- Some passages are the law reporter's headnote, not the Court's words. If you rely on one, say so.
- In the trial judge's findings (pp 1068-1069), "I" is the trial judge, not Martland J.
- Cite pinpoint pages in brackets, e.g. (p 1065).

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
    messages.append({"role": "user", "content": f"Passages from the judgment:\n\n{passages}\nQuestion: {question}"})

    response = client.chat.completions.create(model=CHAT_MODEL, messages=messages, temperature=0.2)
    return response.choices[0].message.content, chunks


# This part only runs when you run this file directly, for testing
if __name__ == "__main__":
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as f:
        key = tomllib.load(f)["OPENAI_API_KEY"]
    client = OpenAI(api_key=key)

    question = "Why did Campbell want to deal with a company?"
    for level in LEVELS:
        reply, sources = answer(client, question, level)
        print("=====", level, "=====")
        print(reply, "\n")