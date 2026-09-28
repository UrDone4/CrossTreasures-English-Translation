#!/usr/bin/env python3
"""Export the story script to a translation workspace, and reinsert it.

    scripttext.py export <out.tsv>
    scripttext.py check  <in.tsv>
    scripttext.py stats  <in.tsv>
    scripttext.py reflow <in.tsv>   show every line re-wrapped to fit the box

The script files in script/text/ are Shift-JIS, CRLF, structured as:

    *<id>            label starting a message block
    <line>           a displayed line; the hard break is the textbox line break
    *end             end of file

Control tags that must be preserved verbatim in the English:

    <c2< ... </c<    colour span (2,3,4,6,8 seen in this game)
    <pn>             player's name
    <item_0..2>      item name for the current event
    #insitem#        inline substitution (also #insnumber#, #inscook#,
                     #insequip#)

Each row carries the measured pixel width of the Japanese and a WRAP_PX budget
for the English, so overlong lines are caught before they reach the ROM.
"""

import csv
import glob
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nftr import Nftr, TAG_RE  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "extracted")
# Widest Japanese line in the original script measures 231px; stay just inside.
WRAP_PX = 232


def script_files():
    return sorted(glob.glob(os.path.join(ROOT, "script", "text", "*.txt")))


def rows_for(path, font):
    rel = os.path.relpath(path, ROOT)
    raw = open(path, "rb").read()
    label = ""
    for idx, line in enumerate(raw.split(b"\r\n")):
        text = line.decode("shift_jis", "replace")
        if text.startswith("*"):
            label = text
            continue
        if not text.strip():
            continue
        yield {
            "file": rel,
            "line": idx,
            "label": label,
            "px": font.measure(line, var_px=0),
            "wrap_px": WRAP_PX,
            "japanese": text,
            "english": "",
        }


def export(out_tsv):
    font = Nftr(os.path.join(ROOT, "LCFont.NFTR"))
    rows = [r for p in script_files() for r in rows_for(p, font)]
    with open(out_tsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return rows


def tags_of(text):
    return sorted(m.group(0) for m in TAG_RE.finditer(text.encode("shift_jis", "replace")))


def check(in_tsv):
    """Flag overlong lines, unencodable characters, and dropped control tags.

    Tags are compared per *label block*, not per line: a natural translation
    moves clauses between the lines of one message box, so a per-line
    comparison would reject correct work. Aggregating by block still catches a
    tag that was actually dropped or invented.
    """
    font = Nftr(os.path.join(ROOT, "LCFont.NFTR"))
    problems = []
    blocks = {}
    with open(in_tsv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            eng = row["english"]
            key = (row["file"], row["label"])
            acc = blocks.setdefault(key, {"jp": [], "en": [], "any": False})
            acc["jp"].append(row["japanese"])
            if eng.strip():
                acc["any"] = True
                acc["en"].append("" if eng.strip() == BLANK else eng)
            if not eng.strip() or eng.strip() == BLANK:
                continue
            try:
                blob = eng.encode("shift_jis")
            except UnicodeEncodeError as exc:
                problems.append((row["file"], row["line"], "UNENCODABLE",
                                 eng[exc.start:exc.end]))
                continue
            px = font.measure(blob, var_px=0)
            if px > int(row["wrap_px"]):
                problems.append((row["file"], row["line"], "TOO WIDE",
                                 "%dpx > %s" % (px, row["wrap_px"])))
    # the box itself: blocks re-wrapped to SAFE_PX must still carry their tags,
    # and blocks that cannot be re-wrapped need shorter wording
    rows, changed, failed = _reflowed_rows(in_tsv, font)
    for path, label, why in failed:
        if os.path.basename(path) not in DEBUG_SCRIPTS:
            problems.append((path, label, "TOO WIDE (box)", why))
    after = {}
    for r in rows:
        after.setdefault((r["file"], r["label"]), []).append(
            "" if r["english"].strip() == BLANK else r["english"])
    def ink(texts):     # what is drawn, and in which colour, spaces aside
        return [piece for t in texts for piece in _parse(t) if piece[1] != " "]
    for key in {(p, l) for p, l in ((r["file"], r["label"]) for r in rows
                                    if (r["file"], int(r["line"])) in changed)}:
        if ink(after[key]) != ink(blocks[key]["en"]):
            problems.append((key[0], key[1], "REFLOW TAGS", "re-wrap changed the tags"))
    for (path, label), acc in sorted(blocks.items()):
        if not acc["any"]:
            continue
        want = tags_of("\n".join(acc["jp"]))
        got = tags_of("\n".join(acc["en"]))
        if want != got:
            problems.append((path, label, "TAG MISMATCH",
                             "block expects %s, got %s" % (want, got)))
    return problems


BLANK = "<blank>"   # explicit "translate this line to nothing"

# ---- reflow ---------------------------------------------------------------
# The box, measured on hardware screenshots (2026-09-24): text starts at x 17
# and the box's inner edge is at x 245, so a line holds 228px; the third row
# also carries the "next" arrow from x 233, so it holds 216px. And the game
# draws every single-byte character at a fixed 6px (38 / 36 characters),
# whatever the font's own advance -- the proportional measure (font.measure)
# is right for Japanese but made "from the dungeon. Look forward to it." 188px
# when it covers 222px on screen and runs into the arrow.
# (An earlier pass used 209px from the widest shipped Japanese line, still in
# the proportional measure; the old WRAP_PX 232 came from a debug script.)
# A block with a line over its row's limit is re-wrapped, at load time, across
# the same number of lines -- the batch files keep the translator's own
# breaks, and check/build both see the reflowed text. Runtime substitutions
# are charged a realistic width (a 6-character kana name, the longest
# translated name of that kind) rather than 0.
ROW_PX = (228, 228, 216)     # rows 1-2, then the arrow's row
ASCII_PX = 6
SAFE_PX = ROW_PX[-1]         # the tightest row, for single-line reports


def row_limit(row):
    return ROW_PX[min(row, len(ROW_PX) - 1)]


# developer test scripts, never shown to a player (README "Text")
DEBUG_SCRIPTS = {"ev100099.txt", "ev100100.txt"}
VAR_PX = {"pn": 72, "host": 72, "friend": 72, "inspcname": 72,
          "insitem": 96, "insitem2": 96, "insequip": 96, "item": 96,
          "insmedal": 96, "inscook": 120, "insmemo": 96, "skill": 96,
          "insnumber": 24, "insnumber2": 24, "insmoney": 56, "insfloor": 18,
          "birthday": 24, "constel": 66}
_TOK = re.compile(r"<c(\d)<|</c<|>([a-z]+)(?:_\d+)?>|<(pn)>|<(item)_\d+>|#(ins[a-z0-9]+)#")
# forms the reflow does not model; blocks containing them are left alone
_ODD = re.compile(r"#[cz]|</c(?!<)|<c\d(?!<)")


def _var_px(name):
    return VAR_PX.get(name, 96)


def _parse(line):
    """[(colour, piece)] -- piece is one character, or a var tag string."""
    out, colour, i = [], None, 0
    for m in _TOK.finditer(line):
        out += [(colour, ch) for ch in line[i:m.start()]]
        if m.group(1):
            colour = m.group(1)
        elif m.group(0) == "</c<":
            colour = None
        else:
            out.append((colour, m.group(0)))
        i = m.end()
    out += [(colour, ch) for ch in line[i:]]
    return out


def _px(font, pieces):
    total = 0
    for _c, p in pieces:
        if len(p) > 1:
            m = _TOK.fullmatch(p)
            total += _var_px(next(g for g in m.groups() if g))
        elif ord(p) < 0x80:
            total += ASCII_PX
        else:
            total += font.measure(p.encode("shift_jis"), var_px=0)
    return total


def _render(pieces):
    out, cur = [], None
    for colour, p in pieces:
        if colour != cur:
            if cur is not None:
                out.append("</c<")
            if colour is not None:
                out.append("<c%s<" % colour)
            cur = colour
        out.append(p)
    if cur is not None:
        out.append("</c<")
    return "".join(out)


def line_px(font, line):
    return _px(font, _parse(line))


def reflow_block(font, lines, limits):
    """Re-wrap `lines` into as many lines, line i <= limits[i] px; None if
    impossible.

    A coloured term ("Magic Barrier") is kept on one line when that fits;
    otherwise it is split, closing and reopening its colour as the Japanese
    does."""
    return _wrap(font, lines, limits, True) or _wrap(font, lines, limits, False)


def _wrap(font, lines, limits, glue):
    words, word = [], []
    for line in lines:
        for colour, p in _parse(line) + [(None, " ")]:
            if p == " " and not (glue and colour is not None):
                if word:
                    words.append(word)
                word = []
            else:
                word.append((colour, p))
    # balanced: of all ways to break the words into len(lines) lines, take the
    # one whose widest line is narrowest (then the evenest), so a re-wrapped
    # block reads like a hand-broken one rather than leaving an orphan word
    def join(ws):
        line = []
        for w in ws:
            if line:
                line.append((line[-1][0] if line[-1][0] == w[0][0] else None, " "))
            line += w
        return line
    n, k = len(words), len(lines)
    if not n:
        return None
    width = {(i, j): _px(font, join(words[i:j]))
             for i in range(n) for j in range(i + 1, n + 1)}
    best = {(n, 0): (0, 0, [])}          # (i, lines left) -> (max, sumsq, breaks)

    def solve(i, left):
        if (i, left) in best:
            return best[(i, left)]
        res = None
        if left > 0:
            limit = limits[k - left]
            for j in range(i + 1, n + 1 - (left - 1)):
                w = width[(i, j)]
                if w > limit:
                    break
                sub = solve(j, left - 1)
                if sub is None:
                    continue
                cand = (max(w, sub[0]), w * w + sub[1], [j] + sub[2])
                if res is None or cand[:2] < res[:2]:
                    res = cand
        best[(i, left)] = res
        return res
    # every line of the block is used (rows are fixed by the file), so the
    # row a line lands on is k - left
    res = solve(0, k) if n >= k else None
    if res is None:
        return None
    out, start = [], 0
    for j in res[2]:
        out.append(join(words[start:j]))
        start = j
    out += [[]] * (k - len(out))
    return [_render(l) for l in out]


def reflow(font, rows):
    """{(file, line): english} for every block that needed re-wrapping, plus a
    list of (file, label, reason) for blocks that could not be re-wrapped.

    A block's rows are its lines in file order, blank English included (a
    blank line still takes its row); only the lines with text are re-wrapped,
    each against the limit of the row it sits on."""
    blocks = {}
    for r in rows:
        blocks.setdefault((r["file"], r["label"]), []).append(r)
    changed, failed = {}, []
    for (path, label), whole in blocks.items():
        block, limits = [], []
        for row, r in enumerate(whole):
            eng = r["english"]
            if eng.strip() and eng.strip() != BLANK:
                block.append(r)
                limits.append(row_limit(row))
        if not block:
            continue
        texts = [r["english"] for r in block]
        if all(line_px(font, t) <= lim for t, lim in zip(texts, limits)):
            continue
        if any(_ODD.search(t) for t in texts):
            failed.append((path, label, "unmodelled tag"))
            continue
        new = reflow_block(font, texts, limits)
        if new is None:
            failed.append((path, label, "does not fit in %d lines" % len(texts)))
            continue
        for r, t in zip(block, new):
            if t != r["english"]:
                changed[(r["file"], int(r["line"]))] = t if t else BLANK
    return changed, failed


def _reflowed_rows(in_tsv, font):
    with open(in_tsv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    changed, failed = reflow(font, rows)
    for r in rows:
        key = (r["file"], int(r["line"]))
        if key in changed:
            r["english"] = changed[key]
    return rows, changed, failed


def load(in_tsv):
    """{(file, line): english}; BLANK renders the line empty, "" leaves it alone.

    Over-wide blocks come back re-wrapped (see SAFE_PX)."""
    out = {}
    rows, _changed, _failed = _reflowed_rows(in_tsv, Nftr(os.path.join(ROOT, "LCFont.NFTR")))
    if True:
        for row in rows:
            value = row["english"]
            if value.strip() == BLANK:
                out[(row["file"], int(row["line"]))] = ""
            elif value.strip():
                out[(row["file"], int(row["line"]))] = value
    return out


def apply_to_file(rel, translations):
    path = os.path.join(ROOT, rel)
    lines = open(path, "rb").read().split(b"\r\n")
    changed = False
    for (r, idx), eng in translations.items():
        if r == rel:
            lines[idx] = eng.encode("shift_jis", "replace")
            changed = True
    return b"\r\n".join(lines) if changed else None


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    if argv[1] == "export":
        rows = export(argv[2])
        print("exported %d script lines from %d files -> %s"
              % (len(rows), len(script_files()), argv[2]))
    elif argv[1] == "check":
        problems = check(argv[2])
        for f, l, kind, detail in problems[:40]:
            print("%-12s %s:%s  %s" % (kind, f, l, detail))
        print("%d problems" % len(problems))
    elif argv[1] == "reflow":
        font = Nftr(os.path.join(ROOT, "LCFont.NFTR"))
        with open(argv[2], newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        changed, failed = reflow(font, rows)
        for r in rows:
            key = (r["file"], int(r["line"]))
            if key in changed:
                print("%s:%s\n    - %s\n    + %s" % (r["file"], r["line"], r["english"], changed[key]))
        print("%d lines re-wrapped, %d blocks could not be" % (len(changed), len(failed)))
    elif argv[1] == "stats":
        done = total = 0
        with open(argv[2], newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                total += 1
                done += bool(row["english"].strip())
        print("%d / %d lines translated (%.1f%%)"
              % (done, total, 100.0 * done / total if total else 0))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
