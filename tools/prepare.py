#!/usr/bin/env python3
"""One-time setup for building the patch from the public repository.

The repository holds no game data: the translation tables carry the English
only, and the battle art only the artist's own pixels. This script takes your
own dump of the Japanese game and restores what was left out:

  1. checks the ROM is the expected dump (SHA-1),
  2. extracts its files to extracted/,
  3. fills the Japanese (and context) columns of work/*_text.tsv back in from
     those files -- the build compares them with the English (control tags),
  4. rebuilds work/redraw/ and work/redraw_done/ from art/ + the game's art.

    python tools/prepare.py "Cross Treasures (Japan).nds"

Then build as described in BUILDING.md.
"""

import csv
import hashlib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

SHA1 = "4048b18f3e589e70e58391927c82ca87117d1337"
EXTRACTED = os.path.join(BASE, "extracted")
# table: (key columns, columns restored from the ROM)
TABLES = {
    "script_text": (("file", "line"), ("japanese",)),
    "data_text": (("file", "record", "field"), ("japanese",)),
    "narc_text": (("archive", "member", "line"), ("context", "japanese")),
    "ui_text": (("file", "line"), ("context", "japanese")),
}


def export(name, out):
    import scripttext, datatext, narctext, uitext  # noqa: E401
    if name == "script_text":
        scripttext.export(out)
    elif name == "data_text":
        datatext.export(out)
    elif name == "narc_text":
        narctext.export(out)
    else:
        uitext.export(EXTRACTED, out)


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh, delimiter="\t")
        return rdr.fieldnames, list(rdr)


def hydrate():
    csv.field_size_limit(10 ** 9)
    tmp = tempfile.mkdtemp()
    for name, (key, cols) in TABLES.items():
        path = os.path.join(BASE, "work", name + ".tsv")
        fields, rows = read(path)
        fresh_path = os.path.join(tmp, name + ".tsv")
        export(name, fresh_path)
        fresh = {tuple(r[k] for k in key): r for r in read(fresh_path)[1]}
        missing = 0
        for r in rows:
            f = fresh.get(tuple(r[k] for k in key))
            if f is None:
                # a few UI rows (data_general/cook_type_name.txt) are outside the
                # UI export: read the line straight from the game file
                src = os.path.join(EXTRACTED, r.get("file", ""))
                if name == "ui_text" and os.path.isfile(src):
                    lines = open(src, "rb").read().decode("shift_jis").splitlines()
                    r["japanese"] = lines[int(r["line"])]
                    continue
                missing += 1
                continue
            for c in cols:
                r[c] = f[c]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\r\n")
            w.writeheader()
            w.writerows(rows)
        print("  %-12s %6d rows restored%s" % (name, len(rows) - missing,
                                            ", %d not found" % missing if missing else ""))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    rom = argv[1]
    digest = hashlib.sha1(open(rom, "rb").read()).hexdigest()
    if digest != SHA1:
        print("This is not the expected dump (SHA-1 %s, want %s).\n"
              "The patch needs 'Cross Treasures (Japan)', 67,108,864 bytes, CRC32 44109EE3."
              % (digest, SHA1))
        return 1
    print("1. ROM ok")
    subprocess.check_call([sys.executable, os.path.join(HERE, "ndsfs.py"), "dump", rom, EXTRACTED])
    print("2. extracted")
    print("3. restoring the Japanese columns from the game files")
    hydrate()
    print("4. rebuilding the battle art")
    import redraw_art
    redraw_art.rebuild()
    os.makedirs(os.path.join(BASE, "work", "gfx"), exist_ok=True)
    print("done -- now build (BUILDING.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
