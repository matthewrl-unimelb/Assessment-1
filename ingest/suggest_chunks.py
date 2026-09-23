import json
import tomllib
from openai import OpenAI

# 1. Get your API key from the secrets file
with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)
client = OpenAI(api_key=secrets["OPENAI_API_KEY"])

# 2. Load the 42 paragraphs
with open("data/paragraphs.json") as f:
    paragraphs = json.load(f)

# 3. Turn them into one block of text, each labelled with its number
numbered = ""
for p in paragraphs:
    numbered += f"[{p['pid']}] {p['text']}\n\n"

# 4. The instructions to OpenAI
instructions = """You are helping prepare a court judgment for a question-answering system.
Group the numbered paragraphs into chunks.

WHAT YOU NEED TO KNOW ABOUT THIS DOCUMENT
- Paragraphs 1-10 and 40-42 are written by the law reporter (headnote, case details, formal result), not the court.
- Paragraphs 11-39 are the judge's reasons.
- Paragraphs 16-22 are one agreement: paragraph 16 introduces it and 17-22 are its numbered terms.

RULES
1. Every paragraph from 1 to 42 must appear in exactly one chunk. Check this before replying.
2. Never put the reporter's paragraphs in the same chunk as the judge's reasons.
3. Gather case details (parties, judges, counsel, solicitors, formal outcome) into one chunk, even if they are spread out.
4. Keep a numbered list together with the sentence that introduces it.
5. Keep each quotation with the sentence that introduces it, and never put two different quotations in the same chunk.
6. Split the judge's reasons so that each chunk is one step: a set of facts, one party's argument, one step of the court's reasoning, or the conclusion. Never combine two steps in one chunk.
7. Aim for roughly 100 to 400 words per chunk.

Reply in JSON only, in this format:
{"chunks": [{"title": "short topic title", "paragraphs": [1, 2], "reason": "why these belong together"}]}"""

# 5. Send it to OpenAI
response = client.chat.completions.create(
    model="gpt-4o",
    temperature=0,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": instructions},
        {"role": "user", "content": numbered},
    ],
)

# 6. Save OpenAI's suggestion to a file, and print it
plan = json.loads(response.choices[0].message.content)
with open("data/chunk_plan.json", "w") as f:
    json.dump(plan, f, indent=2)

for chunk in plan["chunks"]:
    print(chunk["paragraphs"], "-", chunk["title"])