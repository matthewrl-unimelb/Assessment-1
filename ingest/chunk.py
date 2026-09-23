import json

with open("data/paragraphs.json") as f:
    paragraphs = json.load(f)

print("Number of paragraphs:", len(paragraphs))

# Load my chunk plan (the LLM's suggestion, with my corrections)
with open("data/chunk_plan.json") as f:
    plan = json.load(f)["chunks"]

print("Number of chunks in plan:", len(plan))

# Check: every paragraph must appear in exactly one chunk
used = []
for chunk in plan:
    used += chunk["paragraphs"]

all_paragraph_numbers = [p["pid"] for p in paragraphs]

missing = [n for n in all_paragraph_numbers if n not in used]
repeated = [n for n in set(used) if used.count(n) > 1]

print("Missing paragraphs:", missing)
print("Repeated paragraphs:", repeated)


# Look up paragraphs by their number, e.g. by_number[12] gives paragraph 12
by_number = {}
for p in paragraphs:
    by_number[p["pid"]] = p

chunks = []
for i, item in enumerate(plan, start=1):
    texts = []
    pages = []
    for n in item["paragraphs"]:
        texts.append(by_number[n]["text"])
        pages += by_number[n]["pages"]

    chunks.append({
        "id": f"C{i:02d}",
        "title": item["title"],
        "paragraphs": item["paragraphs"],
        "pages": sorted(set(pages)),
        "text": "\n\n".join(texts),
    })

for c in chunks:
    print(c["id"], c["pages"], len(c["text"].split()), "words -", c["title"])


REPORTER_PARAGRAPHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 40, 41, 42]

for c in chunks:
    # Who wrote this chunk: the law reporter, or the Court?
    if c["paragraphs"][0] in REPORTER_PARAGRAPHS:
        c["voice"] = "Headnote - the law reporter's summary, not the Court's own words"
    else:
        c["voice"] = "Reasons of Martland J, for the Court"

    # Page label for citations, e.g. "p 1065" or "pp 1065-1066"
    if len(c["pages"]) == 1:
        c["page_label"] = f"p {c['pages'][0]}"
    else:
        c["page_label"] = f"pp {c['pages'][0]}-{c['pages'][-1]}"

    header = (
        f"MNR v Cameron [1974] SCR 1062 - {c['voice']}\n"
        f"Topic: {c['title']}\n"
        f"Pages: {c['page_label']}\n"
        "The appellant is the Minister of National Revenue; "
        "the respondent is James A. Cameron, the taxpayer."
    )
    c["embed_text"] = header + "\n\n" + c["text"]

with open("data/chunks.json", "w") as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)

print("\nSaved", len(chunks), "chunks to data/chunks.json")
print("\nExample of what gets embedded:\n")
print(chunks[5]["embed_text"][:600])