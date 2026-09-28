#!/usr/bin/env python3
"""Extract and reinsert the menu text embedded inside NARC archives.

Several in-game menus keep their descriptions as plain Shift-JIS text files
*inside* their graphics archive under info/subgraphics/, so a scan of loose
.txt files misses them entirely. The format is the same one uitext.py handles:
`##...##` developer comments, `*` record separators, and displayed lines.

    narctext.py export <out.tsv>
    narctext.py check  <in.tsv>
    narctext.py stats  <in.tsv>
"""

import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from narc import Narc  # noqa: E402
from nftr import Nftr  # noqa: E402

BASE = os.path.dirname(HERE)
ROOT = os.path.join(BASE, "extracted")
FONT = os.path.join(ROOT, "LCFont.NFTR")

BLANK = "<blank>"
# These menu strips are about as wide as the dialogue box.
WRAP_PX = 232


def text_members():
    """[(rom_relative_archive, member_index)] for every embedded text member."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.narc"), recursive=True)):
        try:
            narc = Narc(path)
        except Exception:
            continue
        for i in range(narc.count):
            blob = narc.file(i)
            if len(blob) < 8 or blob[:4].isalpha():
                continue
            try:
                txt = blob.decode("shift_jis")
            except UnicodeDecodeError:
                continue
            if "##" in txt and "\r\n" in txt:
                out.append((os.path.relpath(path, ROOT), i))
    return out


def parse(blob):
    """Yield (line_index, kind, text)."""
    for idx, line in enumerate(blob.split(b"\r\n")):
        txt = line.decode("shift_jis", "replace")
        stripped = txt.strip()
        if stripped.startswith("##") and stripped.endswith("##"):
            kind = "comment"
        elif stripped == "*":
            kind = "sep"
        elif not stripped:
            kind = "blank"
        else:
            kind = "text"
        yield idx, kind, txt


def export(out_tsv):
    font = Nftr(FONT)
    rows = []
    for rel, member in text_members():
        narc = Narc(os.path.join(ROOT, rel))
        blob = narc.file(member)
        context = ""
        for idx, kind, txt in parse(blob):
            if kind == "comment":
                context = txt.strip().strip("#").strip()
            elif kind == "text":
                rows.append({
                    "archive": rel, "member": member, "line": idx,
                    "px": font.measure(txt.encode("shift_jis", "replace"), var_px=0),
                    "wrap_px": WRAP_PX,
                    "context": context,
                    "japanese": txt,
                    "english": "",
                })
    with open(out_tsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return rows


def load(in_tsv):
    out = {}
    with open(in_tsv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            val = row["english"]
            key = (row["archive"], int(row["member"]), int(row["line"]))
            if val.strip() == BLANK:
                out[key] = ""
            elif val.strip():
                out[key] = val
    return out


def check(in_tsv):
    font = Nftr(FONT)
    problems = []
    for key, eng in load(in_tsv).items():
        if not eng:
            continue
        try:
            blob = eng.encode("shift_jis")
        except UnicodeEncodeError as exc:
            problems.append((key, "UNENCODABLE", eng[exc.start:exc.end]))
            continue
        px = font.measure(blob, var_px=0)
        if px > WRAP_PX:
            problems.append((key, "TOO WIDE", "%dpx > %d" % (px, WRAP_PX)))
    # also confirm each rebuilt member still fits its slot
    for (rel, member), blob in build_members(load(in_tsv)).items():
        narc = Narc(os.path.join(ROOT, rel))
        start, end = narc.entry(member)
        if len(blob) > end - start:
            problems.append(((rel, member), "MEMBER TOO BIG",
                             "%d > %d bytes" % (len(blob), end - start)))
    return problems


def build_members(translations):
    """{(archive, member): rebuilt bytes} for every touched member."""
    by_member = {}
    for (rel, member, line), eng in translations.items():
        by_member.setdefault((rel, member), {})[line] = eng
    out = {}
    for (rel, member), lines in by_member.items():
        narc = Narc(os.path.join(ROOT, rel))
        parts = narc.file(member).split(b"\r\n")
        for line, eng in lines.items():
            parts[line] = eng.encode("shift_jis", "replace")
        out[(rel, member)] = b"\r\n".join(parts)
    return out


def apply_all(translations):
    """{archive_rel: rebuilt archive bytes} with every member replaced."""
    members = build_members(translations)
    by_archive = {}
    for (rel, member), blob in members.items():
        by_archive.setdefault(rel, []).append((member, blob))
    out = {}
    for rel, items in by_archive.items():
        narc = Narc(os.path.join(ROOT, rel))
        for member, blob in items:
            narc.replace(member, blob)
        out[rel] = bytes(narc.data)
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    if argv[1] == "export":
        rows = export(argv[2])
        archives = len({r["archive"] for r in rows})
        print("exported %d lines from %d archives -> %s"
              % (len(rows), archives, argv[2]))
    elif argv[1] == "check":
        problems = check(argv[2])
        for p in problems[:40]:
            print("  %s  %s  %s" % p)
        print("%d problems" % len(problems))
    elif argv[1] == "stats":
        done = total = 0
        with open(argv[2], newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                total += 1
                done += bool(row["english"].strip())
        print("%d / %d lines translated" % (done, total))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
