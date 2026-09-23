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