#!/usr/bin/env python3
"""The Character Creator's Random! (おまかせ) names.

`info/keyboard/entrust_name_binary.dat` does not hold text. It holds key
presses on the name-entry keyboard: u32 total size (1056), u32 count (11),
then count x 6 records of four u32s -- (column, row, page, modifier) -- one per
character, padded with (0, 0, 0, 5) = no key. The page and modifier pick one of
the keyboard_*.dat grids (12 columns x 6 rows, Shift-JIS) through the ARM9
table at 0x20A6424, indexed page * 4 + modifier: page 0 hiragana, 1 katakana,
2 alphabet (modifier 0 only); modifier 1 half-voiced, 2 voiced, 3 small.

English names are therefore typed on the ABC grid (page 2), so they come out
exactly as a player typing them would -- full-width letters, 6 at most.

    keyboard_names.py list          the names in the ROM file, decoded
    keyboard_names.py check         encode work/random_names.py and report
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
KB = os.path.join(BASE, "extracted", "info", "keyboard")
REL = "info/keyboard/entrust_name_binary.dat"

PAGES = {0: "hiragana", 1: "katakana", 2: "alphabet"}
MODS = {0: "", 1: "_halfvoiced", 2: "_voiced", 3: "_small"}
EMPTY = (0, 0, 0, 5)
SLOTS = 6


def grid(page, mod):
    data = open(os.path.join(KB, "keyboard_%s%s.dat" % (PAGES[page], MODS[mod])),
                "rb").read()[4:].decode("shift_jis")
    return [data[r * 12:(r + 1) * 12] for r in range(6)]


def decode(blob):
    size, count = struct.unpack_from("<II", blob, 0)
    names = []
    for n in range(count):
        s = ""
        for k in range(SLOTS):
            c, r, p, m = struct.unpack_from("<4I", blob, 8 + 16 * (n * SLOTS + k))
            if m != 5:
                s += grid(p, m)[r][c]
        names.append(s)
    return names


def encode(names, count):
    """Key presses on the ABC grid for each name (ASCII in, full-width out)."""
    if len(names) != count:
        raise SystemExit("need exactly %d names, got %d" % (count, len(names)))
    abc = grid(2, 0)
    where = {}
    for r, row in enumerate(abc):
        for c, ch in enumerate(row):
            if ch != "　":
                where[chr(ord(ch) - 0xFEE0)] = (c, r)
    out = struct.pack("<II", 8 + 16 * SLOTS * count, count)
    for name in names:
        if not 1 <= len(name) <= SLOTS:
            raise SystemExit("%r: 1-%d letters" % (name, SLOTS))
        keys = []
        for ch in name:
            if ch not in where:
                raise SystemExit("%r: %r is not on the ABC keyboard" % (name, ch))
            keys.append(where[ch] + (2, 0))
        keys += [EMPTY] * (SLOTS - len(keys))
        for k in keys:
            out += struct.pack("<4I", *k)
    return out


def build():
    """(rel path, new bytes) for build_patch."""
    sys.path.insert(0, os.path.join(BASE, "work"))
    import random_names
    orig = open(os.path.join(BASE, "extracted", REL), "rb").read()
    count = struct.unpack_from("<I", orig, 4)[0]
    blob = encode(random_names.NAMES, count)
    if len(blob) != len(orig):
        raise SystemExit("entrust_name_binary.dat size changed")
    return REL, blob


def main(argv):
    if len(argv) >= 2 and argv[1] == "list":
        for n in decode(open(os.path.join(BASE, "extracted", REL), "rb").read()):
            print(n)
    elif len(argv) >= 2 and argv[1] == "check":
        _rel, blob = build()
        for n in decode(blob):
            print(n)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
