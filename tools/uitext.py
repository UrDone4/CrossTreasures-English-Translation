#!/usr/bin/env python3
"""Extract and reinsert the menu/UI text files (info/**.txt, text/*.txt).

Format, as used by the Cross Treasures tools:
  ##  ... ##   developer comment line, never displayed. Frequently documents
               the field's limits, e.g. "1行（18文字）" = one line of 18 chars.
  *            record separator
  <other>      a displayed line

Extraction writes a TSV workspace with one row per displayed line, carrying the
nearest preceding comment as context plus a pixel budget derived from any
documented character limit. Reinsertion rewrites the original files byte-for-
byte apart from the translated lines, so comments and separators survive.
"""

import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nftr import Nftr  # noqa: E402

COMMENT_RE = re.compile(r"^\s*##.*##\s*$")
# "18文字" / "6文字" -- a documented per-line character limit
LIMIT_RE = re.compile(r"(\d+)\s*文字")
FULLWIDTH_PX = 12  # advance of a full-width glyph; limits are quoted in these


def iter_files(root):
    paths = sorted(glob.glob(os.path.join(root, "info", "**", "*.txt"), recursive=True))
    paths += sorted(glob.glob(os.path.join(root, "text", "*.txt")))
    # developer readmes are not game-facing
    return [p for p in paths if os.path.basename(p) != "readme.txt"]


def parse(path):
    """Yield (line_index, kind, text) where kind is comment/sep/text."""
    raw = open(path, "rb").read()
    for idx, line in enumerate(raw.split(b"\r\n")):
        text = line.decode("shift_jis", "replace")
        if COMMENT_RE.match(text):
            kind = "comment"
        elif text.strip() == "*":
            kind = "sep"
        elif text.strip() == "":
            kind = "blank"
        else:
            kind = "text"
        yield idx, kind, text


def export(root, out_tsv):
    font = Nftr(os.path.join(root, "LCFont.NFTR"))
    rows = []
    for path in iter_files(root):
        rel = os.path.relpath(path, root)
        context, budget = "", ""
        for idx, kind, text in parse(path):
            if kind == "comment":
                context = text.strip().strip("#").strip()
                m = LIMIT_RE.search(context)
                budget = str(int(m.group(1)) * FULLWIDTH_PX) if m else ""
            elif kind == "text":
                rows.append({
                    "file": rel,
                    "line": idx,
                    "px": font.measure(text.encode("shift_jis", "replace"), var_px=0),
                    "budget_px": budget,
                    "context": context,
                    "japanese": text,
                    "english": "",
                })
    with open(out_tsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    return rows


BLANK = "<blank>"   # explicit "translate this line to nothing"


def load_translations(tsv):
    """{(file, line): english} for rows that have been filled in.

    An empty cell means "not translated yet" and leaves the Japanese in place;
    the BLANK sentinel means "this line should render as empty", which is how
    a two-line Japanese field collapses to one line of English.
    """
    out = {}
    with open(tsv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            value = row["english"]
            if value.strip() == BLANK:
                out[(row["file"], int(row["line"]))] = ""
            elif value.strip():
                out[(row["file"], int(row["line"]))] = value
    return out


def apply_to_file(root, rel, translations):
    """Return the rebuilt Shift-JIS bytes for one file, or None if unchanged."""
    path = os.path.join(root, rel)
    raw = open(path, "rb").read()
    lines = raw.split(b"\r\n")
    changed = False
    for idx, _kind, _text in parse(path):
        eng = translations.get((rel, idx))
        if eng is None:
            continue
        lines[idx] = eng.encode("shift_jis", "replace")
        changed = True
    return b"\r\n".join(lines) if changed else None


def check(root, tsv):
    """Report translated lines that overrun their documented budget."""
    font = Nftr(os.path.join(root, "LCFont.NFTR"))
    problems = []
    with open(tsv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            eng = row["english"].strip()
            if not eng or not row["budget_px"]:
                continue
            px = font.measure(eng.encode("shift_jis", "replace"), var_px=0)
            if px > int(row["budget_px"]):
                problems.append((row["file"], row["line"], px,
                                 int(row["budget_px"]), eng))
    return problems


def main(argv):
    root = "extracted"
    if argv[1] == "export":
        rows = export(root, argv[2])
        todo = sum(1 for r in rows if not r["english"])
        print("exported %d lines (%d untranslated) -> %s" % (len(rows), todo, argv[2]))
    elif argv[1] == "check":
        bad = check(root, argv[2])
        for f, l, px, b, e in bad:
            print("OVER %s:%s  %dpx > %dpx  %r" % (f, l, px, b, e))
        print("%d overruns" % len(bad))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
