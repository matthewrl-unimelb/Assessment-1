"""Diagrams on request: gpt-4o writes Graphviz code, Streamlit draws it.

gpt-4o can't draw pictures, but it can write Graphviz, a simple text
language for diagrams (e.g.  "Campbell Ltd" -> "Independent" [label="15% fee"]).
Streamlit's built-in st.graphviz_chart() turns that text into a picture.

To keep diagrams grounded like the text answers, gpt-4o only sees the chunks
retrieved from the vector database for the user's question, and is told to use
only facts from them.
"""

import re

from core.config import CHAT_MODEL
from core.rag import retrieve

# Words that suggest the user wants a picture rather than just text
DIAGRAM_WORDS = [
    "diagram", "draw", "chart", "graph", "picture", "visual", "illustrat",
    "flowchart", "flow chart", "map out", "sketch",
]


def wants_diagram(question):
    q = question.lower()
    return any(word in q for word in DIAGRAM_WORDS)


DIAGRAM_PROMPT = """You draw diagrams about one court judgment, MNR v Cameron [1974] SCR 1062, using Graphviz DOT code.

Rules:
- Use ONLY facts found in the passages provided. Do not invent parties, amounts or dates.
- In this case the appellant is the Minister of National Revenue and the respondent is James A. Cameron (the taxpayer).
- Draw what the user asked for, e.g. who the parties are and how money, shares, services or ownership flowed between them.
- Keep it readable: at most 10 boxes, short labels (under 8 words per line; use \\n for line breaks).
- Put key amounts and dates on the arrows where the passages give them.
- Reply with the DOT code ONLY, starting with "digraph" and nothing before or after it.

Use exactly this styling at the top of the graph so it matches the app:
    graph [rankdir=LR, bgcolor="transparent", fontname="Helvetica", fontcolor="#E6ECF4", nodesep=0.5, ranksep=0.9, pad=0.3];
    node  [shape=box, style="rounded,filled", fillcolor="#18293F", color="#C9A45C", fontname="Helvetica", fontcolor="#E6ECF4", fontsize=12];
    edge  [fontname="Helvetica", fontsize=10, fontcolor="#E6ECF4", color="#8FA3BF"];
Draw arrows that represent money with color="#C9A45C" and penwidth=2."""


def clean_dot(text):
    """Pull the DOT code out of gpt-4o's reply and check it looks complete."""
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())   # remove ``` fences if present
    start = text.find("digraph")
    if start == -1:
        return None
    text = text[start:]
    end = text.rfind("}")
    if end == -1:
        return None
    text = text[: end + 1]
    if text.count("{") != text.count("}"):                          # unbalanced braces = broken code
        return None
    return text


def make_diagram(client, question):
    """Return (dot_code or None, chunks used). Tries twice before giving up."""
    chunks = retrieve(client, question)
    passages = ""
    for c in chunks:
        passages += f"[{c['title']} - {c['page_label']}]\n{c['text']}\n\n"

    for _ in range(2):
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": DIAGRAM_PROMPT},
                {"role": "user", "content": f"Passages from the judgment:\n\n{passages}\nWhat to draw: {question}"},
            ],
        )
        dot = clean_dot(response.choices[0].message.content)
        if dot:
            return dot, chunks
    return None, chunks