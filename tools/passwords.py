#!/usr/bin/env python3
"""English secret passwords (ひみつのじゅもん) for data_general/secret_pass.dat.

The game checks a password with a plain string compare (ARM9 0x2080208): each
of the three typed lines, trailing full-width spaces trimmed (0x2080144), must
equal the record's line at +0x34 / +0x4C / +0x64 byte for byte. The checker
copies only 18 bytes per typed line (0x2080084), so a line holds at most **9**
full-width characters. English passwords are therefore stored as full-width
capitals (Ａ = 0x8260), exactly what the ABC keyboard page types -- the
keyboard opens on ABC already (arm9text.CODE). Capitals only, no spaces, so
there is nothing to get wrong but the letters.

None of these passwords is shown by the game itself: they were published in
magazines, at events and on the Square Enix site. The English replaces the
kana outright (the file holds one password per record), so the Japanese
passwords no longer work in the patched game.

    python tools/passwords.py check     validate lengths, letters, uniqueness
    python tools/passwords.py list      print the table (PASSWORDS.md source)
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
REL = "data_general/secret_pass.dat"
SRC = os.path.join(BASE, "extracted", REL)
LINES = (0x34, 0x4C, 0x64)
LINE_BYTES = 24
MAX_CHARS = 9
ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?")

# record index -> three lines; each follows the Japanese password's idea
PASSWORDS = [
    ("DRINK", "LIFE", "POTIONS"),         # 1  Life Potion x20
    ("POCKET", "MONEY", "PLEASE"),        # 2  300G
    ("FORGE", "IRON", "ORE"),             # 3  Iron Ore x5
    ("MEAT", "FOR", "DINNER"),            # 4  Rib Meat x5
    ("SECRET", "TICKET", "ONE"),          # 5  Secret Ticket x1
    ("RED", "RUBY", "GEM"),               # 6  Ruby x1
    ("MANA", "POTION", "PLEASE"),         # 7  Mana Potion x20
    ("HARD", "WORKER", "BONUS"),          # 8  500G
    ("SMOOTH", "WHITE", "SILK"),          # 9  White Silk x5
    ("FLUFFY", "WHEAT", "BAKING"),        # 10 Fluffy Wheat x5
    ("SECRET", "TICKET", "TWO"),          # 11 Secret Ticket x2
    ("BLUE", "SAPPHIRE", "GEM"),          # 12 Sapphire x1
    ("KETCHUP", "ON", "OMELETS"),         # 13 Tomato Ketchup x5
    ("BIG", "POCKET", "MONEY"),           # 14 800G
    ("SOFT", "STURDY", "FUR"),            # 15 Sturdy Fur x5
    ("GOLDEN", "SHARDS", "PLEASE"),       # 16 Golden Shard x3
    ("SECRET", "TICKET", "THREE"),        # 17 Secret Ticket x3
    ("YELLOW", "TOPAZ", "GEM"),           # 18 Topaz x1
    ("TEA", "LEAVES", "HEALTHY"),         # 19 Tea Leaf x5
    ("SHINY", "SILVER", "ORE"),           # 20 Silver Ore x5
    ("JACKPOT", "THOUSAND", "GOLD"),      # 21 1000G
    ("WARM", "WHITE", "RICE"),            # 22 White Rice x10
    ("SECRET", "TICKET", "FOUR"),         # 23 Secret Ticket x4
    ("GREEN", "EMERALD", "GEM"),          # 24 Emerald x1
    ("LEGEND", "OF", "VJUMP"),            # 25 V Ticket x4 (V Jump)
    ("NEWEST", "VJUMP", "TICKET"),        # 26 V Ticket SP x4
    ("THIS", "WEEK", "JUMP"),             # 27 J Ticket x4 (Weekly Shonen Jump)
    ("NEXT", "WEEK", "JUMP"),             # 28 J Ticket SP x4
    ("FEAST", "JUMP", "FESTA"),           # 29 Santa Robe x4 (Jump Festa)
    ("EXCITING", "STRATEGY", "GUIDE"),    # 30 Gift Box x4 (official guide)
    ("SQUARE", "ENIX", "MEMBERS"),        # 31 Members Card x1
    ("MEMBERS", "BRING", "FRIENDS"),      # 32 Members Card x2
    ("MEMBERS", "MULTI", "PLAY"),         # 33 Members Card x3
    ("RAINBOW", "RIBBON", "MAGIC"),       # 34 Magic Ribbon x4 (Ribon)
    ("CHARUMERA", "RAMEN", "COIN"),       # 35 100-Yen Coin x1 (Charumera)
    ("THIS", "MONTH", "JUMPSQ"),          # 36 Diamond x1 (Jump SQ)
    ("EVERYONES", "POWER", "GOLD"),       # 37 Gold Stone x1
    ("ONE", "TWO", "THREE"),              # 38 Life Leaf x5
    ("ONE", "WEEK", "BONUS"),             # 39 1000G
    ("WITH", "FRIENDS", "PLATINUM"),      # 40 Platinum Ore x5
    ("TOUGH", "FOES", "AWAIT"),           # 41 Holy Leather x5
    ("ADVENTURE", "SOY", "SAUCE"),        # 42 Soy Sauce x5
    ("LINE", "THEM", "UP"),               # 43 Sushi Rice x5
    ("CROSS", "TREASURES", "TOGETHER"),   # 44 Aged Miso x5
    ("KEEP", "PLAYING", "CROTRE"),        # 45 Big Metal x5
]


def fullwidth(text):
    return "".join(chr(ord(c) + 0xFEE0) for c in text)


def check():
    problems = []
    if len(PASSWORDS) != 45:
        problems.append("expected 45 passwords, have %d" % len(PASSWORDS))
    seen = {}
    for i, lines in enumerate(PASSWORDS, 1):
        for line in lines:
            if not line or len(line) > MAX_CHARS:
                problems.append("#%d %r: 1-%d characters" % (i, line, MAX_CHARS))
            bad = set(line) - ALLOWED
            if bad:
                problems.append("#%d %r: not on the keyboard %r" % (i, line, bad))
        if lines in seen:
            problems.append("#%d duplicates #%d" % (i, seen[lines]))
        seen[lines] = i
    return problems


def build():
    """(rel_path, bytes) for build_patch.py."""
    problems = check()
    if problems:
        raise ValueError("passwords: " + "; ".join(problems))
    d = bytearray(open(SRC, "rb").read())
    count = struct.unpack_from("<I", d, 0)[0]
    size = (len(d) - 4) // count
    assert count == len(PASSWORDS) and size == 124, (count, size)
    for i, lines in enumerate(PASSWORDS):
        base = 4 + i * size
        for off, line in zip(LINES, lines):
            blob = fullwidth(line).encode("shift_jis")
            d[base + off:base + off + LINE_BYTES] = blob + b"\0" * (LINE_BYTES - len(blob))
    return REL, bytes(d)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "check":
        problems = check()
        for p in problems:
            print(p)
        print("%d problems" % len(problems))
        return 1 if problems else 0
    if cmd == "list":
        for i, lines in enumerate(PASSWORDS, 1):
            print("%2d  %s" % (i, " / ".join(lines)))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
