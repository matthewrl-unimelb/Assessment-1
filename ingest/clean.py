"""
Step 2 of the ingestion pipeline: turn OCR lines into clean paragraphs.

Input : data/ocr_pages.json   (from ingest/ocr.py)
Output: data/paragraphs.json  (machine-readable, used by chunk.py)
        data/cameron_clean.md (human-readable, for proof-reading against the PDF)

What this does, and why
-----------------------
1. Rebuild paragraphs. The SCR indents the first line of every paragraph, so a
   line that starts noticeably further right than the column's normal left
   margin opens a new paragraph. Paragraphs that run over a page break are
   joined, and every paragraph remembers which SCR page(s) it came from so
   the app can cite pinpoint pages.
2. Undo end-of-line hyphenation ("judg-" + "ment" -> "judgment") while keeping
   genuine compounds ("vice-president", "secretary-treasurer").
3. Pull out the single footnote (the citation for Snook) so it doesn't get
   glued into the middle of the trial judge's findings, and re-attach it to
   the Snook paragraph as a bracketed citation.
4. Fix the handful of OCR errors found by proof-reading the output against the
   scan. Every correction is listed in OCR_CORRECTIONS so it can be checked;
   nothing is "fixed" silently. Spellings that are genuinely in the report
   (e.g. "Steel" for "Steele" at p 1068) are deliberately left alone.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "ocr_pages.json"
OUT_JSON = ROOT / "data" / "paragraphs.json"
OUT_MD = ROOT / "data" / "cameron_clean.md"

# A first line indented this many pixels (at 300 dpi) beyond the column's
# normal margin is treated as the start of a new paragraph. Body lines vary
# by up to ~55px because of scan skew; paragraph indents are 75px or more.
PARA_INDENT_PX = 70

# Lines that sit on their own and are part of a table (e.g. "1965 — $37,745").
TABLE_LINE = re.compile(r"^19\d\d\s+[—-]\s+\$")

# Footnote text at the foot of p 1068.
FOOTNOTE_LINE = re.compile(r"^['‘’`]?\s*\[1967\] 1 All E\.R\. 518")

# Numbered terms of the 10 August 1964 agreement ("1. Independent would ...").
LIST_ITEM = re.compile(r"^\d\.\s+[A-Z]")

# The agreement's six terms are printed as an indented block, at the same depth
# as a normal paragraph indent. That means the paragraph immediately after the
# list cannot be told apart from a continuation of term 6 by layout alone.
# After proof-reading, we mark that one paragraph start by hand:
FORCE_BREAK_BEFORE = ["On August 19, 1964, Steele"]

# Genuine hyphenated compounds that happen to break at the hyphen.
KEEP_HYPHEN = {"vice-president", "secretary-treasurer", "non-cumulative"}

# (wrong, right, reason) — found by proof-reading data/cameron_clean.md
# against the PDF. Applied after paragraphs are rebuilt.
OCR_CORRECTIONS = [
    ("Eamonton", "Edmonton", "OCR misread (p 1064)"),
    ("Campbeil", "Campbell", "OCR misread (p 1064)"),
    ("an_ oral", "an oral", "stray underscore (p 1065)"),
    ("was_ that", "was that", "stray underscore (p 1067)"),
    ("_ the money", "the money", "stray underscore (p 1068)"),
    ("On august 10", "On August 10", "OCR case error (p 1065)"),
    ("in.all cities", "in all cities", "stray full stop (p 1066)"),
    ("L.J.in", "L.J. in", "missing space (p 1068)"),
    ("If a Saving", "If a saving", "OCR case error (p 1063)"),
    ("June 29,", "June 29.", "OCR punctuation (p 1062)"),
    ("$ 37,745", "$37,745", "stray space in figure (p 1066)"),
    ("Riding Investments, Ltd.':", "Riding Investments, Ltd.:", "footnote marker read as a quote mark (p 1068)"),
]

# Curly-quote debris from OCR (e.g. ‘‘“Campbell Limited’’) -> plain “ ”.
QUOTE_FIXES = [
    (re.compile(r"[‘“]{2,3}"), "“"),
    (re.compile(r"[’”]{2,3}"), "”"),
    (re.compile(r"‘““|‘“‘"), "“"),
    (re.compile(r"(\w)’(?=[\s,.:;]|$)(?<!s’)"), r"\1’"),  # leave apostrophes alone
]


def join_lines(lines: list[str]) -> str:
    """Join a paragraph's lines, undoing end-of-line hyphenation."""
    text = ""
    for line in lines:
        if line.startswith("\n"):                     # table row keeps its own line
            text = text + "\n" + line.strip()
            continue
        line = line.strip()
        if not text:
            text = line
            continue
        if text.endswith("-") and line[:1].islower():
            head = text.rsplit(" ", 1)[-1]           # e.g. "vice-"
            tail = line.split(" ", 1)[0]             # e.g. "president"
            compound = (head + tail).lower().strip(".,;:")
            if compound in KEEP_HYPHEN:
                text = text + line                   # keep the hyphen
            else:
                text = text[:-1] + line              # drop the hyphen
        else:
            text = text + " " + line
    return text


def normalise_quotes(text: str) -> str:
    for pattern, repl in QUOTE_FIXES:
        text = pattern.sub(repl, text)
    # a closing ’ that should be ” after a quoted name, e.g. “Independent.’
    text = re.sub(r"(“[^”’]{2,40}?)’", r"\1”", text)
    return text


def main() -> None:
    pages = json.loads(IN.read_text())
    paragraphs: list[dict] = []
    footnote = None
    current = None  # paragraph being built

    def close():
        nonlocal current
        if current:
            paragraphs.append(current)
            current = None

    for page in pages:
        lines = page["lines"]
        # The column's normal left margin: the median of the lowest cluster of
        # indents (within 45px of the smallest). Scan skew moves it a little
        # from page to page, and indented lists/quotes must not distort it.
        indents = sorted(l["indent"] for l in lines)
        low = [x for x in indents if x <= indents[0] + 45]
        base = low[len(low) // 2]
        in_list = False
        for i, line in enumerate(lines):
            text = line["text"].strip()
            if FOOTNOTE_LINE.match(text):
                footnote = "[1967] 1 All E.R. 518, p. 528"
                continue
            is_table = bool(TABLE_LINE.match(text))
            forced = any(text.startswith(f) for f in FORCE_BREAK_BEFORE)
            is_item = bool(LIST_ITEM.match(text))
            if is_item:
                in_list = True
            if forced:
                in_list = False
            if in_list:
                starts_para = is_item          # inside the list only a new number starts a new unit
            else:
                starts_para = forced or ((line["indent"] - base) >= PARA_INDENT_PX and not is_table)
            if is_table:
                # table rows attach to the paragraph that introduces them
                current["lines"].append("\n" + text)
                current["pages"].add(page["scr_page"])
                continue
            if starts_para or current is None:
                close()
                current = {"lines": [], "pages": set(), "kind": "list_item" if is_item else "paragraph"}
            current["lines"].append(text)
            current["pages"].add(page["scr_page"])
    close()

    out = []
    for n, p in enumerate(paragraphs, start=1):
        text = join_lines(p["lines"]).replace(" \n", "\n")
        text = normalise_quotes(text)
        for wrong, right, _ in OCR_CORRECTIONS:
            text = text.replace(wrong, right)
        if footnote and "Snook v. London" in text:
            text = text.rstrip(":") + f" [{footnote}]:"
        pages_sorted = sorted(p["pages"])
        out.append({
            "pid": n,
            "pages": pages_sorted,
            "kind": p["kind"],
            "text": text,
        })

    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    md = ["# MNR v Cameron [1974] SCR 1062 — cleaned English text\n",
          "_Generated by ingest/clean.py from the OCR output. Proof-read against the PDF._\n"]
    for p in out:
        pg = "–".join(str(x) for x in (p["pages"][0], p["pages"][-1])) if len(p["pages"]) > 1 else str(p["pages"][0])
        md.append(f"**[¶{p['pid']} · p {pg}]** {p['text']}\n")
    md.append("\n## OCR corrections applied\n")
    md += [f"- `{w}` → `{r}` — {why}" for w, r, why in OCR_CORRECTIONS]
    OUT_MD.write_text("\n".join(md))
    print(f"{len(out)} paragraphs -> {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
