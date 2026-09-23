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