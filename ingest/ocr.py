"""
Step 1 of the ingestion pipeline: OCR the English column of the scanned judgment.

Why this step exists
--------------------
The SCR PDF of MNR v Cameron [1974] SCR 1062 is a scanned image with no text
layer, so there is nothing for a normal PDF text extractor to read. Each page is
laid out in two columns: the English text on the left and the official French
translation on the right. We only index the English, so we:

  1. render each page to a 300 dpi image (poppler's `pdftoppm`),
  2. find the vertical gutter between the two columns by looking for the widest
     band of blank pixels near the middle of the page (the gutter moves between
     odd and even pages, so it can't be a fixed crop),
  3. crop the left (English) column and OCR it with Tesseract,
  4. drop the running header (page number, "M.N.R. v. CAMERON", "Martland J.")
     by ignoring any text above the header rule.

This script is run ONCE, offline, by the developer. Its output
(data/ocr_pages.json) is committed, so the deployed app never needs Tesseract.

Requirements (developer machine only): `tesseract` and `pdftoppm` on PATH
(macOS: `brew install tesseract poppler`), plus numpy and Pillow.

Usage:  python ingest/ocr.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "cameron_1974_scr_1062.pdf"
OUT = ROOT / "data" / "ocr_pages.json"

FIRST_SCR_PAGE = 1062      # the report starts at [1974] SCR 1062
DPI = 300
HEADER_FRACTION = 0.075    # running header sits in the top ~7.5% of each page


def render_pages(pdf: Path, workdir: Path) -> list[Path]:
    subprocess.run(
        ["pdftoppm", "-r", str(DPI), "-gray", "-png", str(pdf), str(workdir / "p")],
        check=True,
    )
    return sorted(workdir.glob("p-*.png"))


def find_gutter(img: np.ndarray) -> int:
    """Return the x-coordinate in the middle of the column gutter."""
    h, w = img.shape
    ink = img < 128
    body = ink[int(h * 0.10): int(h * 0.90)]          # ignore header/footer
    col_ink = body.sum(axis=0)
    lo, hi = int(w * 0.35), int(w * 0.65)             # gutter is near the middle
    blank = np.where(col_ink[lo:hi] == 0)[0] + lo
    runs = np.split(blank, np.where(np.diff(blank) != 1)[0] + 1)
    widest = max(runs, key=len)
    return int((widest[0] + widest[-1]) / 2)


def ocr_lines(image_path: Path) -> list[dict]:
    """OCR an image and return its text lines with their vertical position."""
    tsv = subprocess.run(
        ["tesseract", str(image_path), "-", "--psm", "4", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout
    lines: dict[tuple, dict] = {}
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or cols[0] != "5" or not cols[11].strip():
            continue  # level 5 = individual word
        key = (int(cols[2]), int(cols[3]), int(cols[4]))   # block, paragraph, line
        top, left = int(cols[7]), int(cols[6])
        entry = lines.setdefault(key, {"top": top, "left": left, "words": []})
        entry["top"] = min(entry["top"], top)
        entry["left"] = min(entry["left"], left)
        entry["words"].append(cols[11])
    ordered = sorted(lines.values(), key=lambda l: l["top"])
    return [{"top": l["top"], "left": l["left"], "text": " ".join(l["words"])} for l in ordered]


def main() -> None:
    pages = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, png in enumerate(render_pages(PDF, tmp)):
            img = np.array(Image.open(png).convert("L"))
            h, w = img.shape
            gutter = find_gutter(img)
            english = Image.fromarray(img[:, :gutter])
            crop_path = tmp / f"en-{i}.png"
            english.save(crop_path)

            lines = [l for l in ocr_lines(crop_path) if l["top"] > h * HEADER_FRACTION]
            # left margin of the column, used later to spot indented quotations
            margin = min((l["left"] for l in lines), default=0)
            for l in lines:
                l["indent"] = l["left"] - margin
            pages.append({
                "pdf_page": i + 1,
                "scr_page": FIRST_SCR_PAGE + i,
                "gutter_x": gutter,
                "lines": lines,
            })
            print(f"page {i + 1} (SCR {FIRST_SCR_PAGE + i}): {len(lines)} lines, gutter at x={gutter}")

    OUT.write_text(json.dumps(pages, indent=2, ensure_ascii=False))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
