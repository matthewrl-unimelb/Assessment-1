import json

with open("data/paragraphs.json") as f:
    paragraphs = json.load(f)

print("Number of paragraphs:", len(paragraphs))
for p in paragraphs:
    print(p["pid"], p["pages"], p["text"][:80])