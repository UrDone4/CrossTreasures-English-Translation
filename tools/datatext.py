#!/usr/bin/env python3
"""Extract and reinsert text held in the fixed-record .dat tables.

Every .dat in data_*/ is a u32 record count followed by fixed-size records.
Strings sit at fixed offsets inside a record, NUL-terminated, and are padded
out to the next field.

IMPORTANT -- the bytes between a string's terminator and the next real field
are stale garbage left by the developers' exporter (they are fragments of
longer strings written into the same buffer earlier). The game stops at the
terminator and never reads them, so reinsertion zero-fills the whole field.
Each capacity below was verified by checking that every record is NUL from the
longest observed string end up to the first byte of the next populated field.

Capacity is in BYTES and includes the terminator, so a 17-byte name field holds
16 bytes of text: eight Shift-JIS characters, but sixteen ASCII ones. English
therefore fits without needing to enlarge any record.

    datatext.py export <out.tsv>
    datatext.py check  <in.tsv>
    datatext.py stats  <in.tsv>
"""

import csv
import os
import struct
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "extracted")

# (path, field name, offset, capacity-in-bytes-including-terminator)
SCHEMA = [
    # Tika's Smile Shop list (5 tiers): name, then a two-line description
    ("data_treasure/shop_smile.dat",        "name",  8, 21),
    ("data_treasure/shop_smile.dat",        "desc", 29, 123),
    # Island Art decorations/monster pets (Arton, the wandering artist)
    ("data_general/island_art.dat",         "name", 20, 32),
    ("data_general/island_art.dat",         "desc", 52, 128),
    ("data_item/item_param.dat",            "name", 14, 17),
    ("data_item/item_param.dat",            "desc", 31, 77),
    ("data_item/equip_param.dat",           "name", 18, 17),
    ("data_item/equip_param.dat",           "desc", 35, 77),
    ("data_monster/monster_param.dat",      "name", 56, 17),
    ("data_monster/monster_boss_param.dat", "name", 56, 17),
    ("data_monster/monster_object_param.dat", "name", 56, 17),
    ("data_monster/monster_text.dat",       "desc",  8, 124),
    ("data_monster/monster_boss_text.dat",  "desc",  8, 124),
    # equipment effect descriptions (the 32 onomatopoeia traits). The name field
    # (offset 48) is padded with 0x01 and is shown as a sprite tag instead --
    # see tools/equip_tags.py -- so only the description is translated here.
    ("data_item/equip_effect.dat",          "desc", 69, 39),
    # the starter equipment's "Made By" name: five (u16 + 14-byte string) slots
    # per record, all the same maker (Bockdarn), one per quality/variant
    ("data_item/equipment_default.dat",     "maker0",  6, 14),
    ("data_item/equipment_default.dat",     "maker1", 22, 14),
    ("data_item/equipment_default.dat",     "maker2", 38, 14),
    ("data_item/equipment_default.dat",     "maker3", 54, 14),
    ("data_item/equipment_default.dat",     "maker4", 70, 14),
    # the Medals screen: 25 medal types x 3 tiers, then 11 master powers x 3
    ("data_general/medalion.dat",           "name",  4, 24),
    ("data_general/medalion.dat",           "cond", 36, 64),
    ("data_general/master_power.dat",       "name",  4, 24),
    ("data_general/master_power.dat",       "desc", 32, 124),
    # the Memo screen: 57 memos -- list title, opened-memo heading, and a fixed
    # 40-line body (see merge_memo_text.py)
    ("data_item/memo.dat",                  "title",   4, 21),
    ("data_item/memo.dat",                  "heading", 25, 21),
    ("data_item/memo.dat",                  "body",    46, 1478),
    # the Cook menu: 80 recipes (name + flavour-text description); ingredients
    # (cook_foodstuff.dat) are numeric only -- item names come from
    # item_param.dat via ID reference, already translated
    ("data_general/cook_param.dat",         "name",   68, 24),
    ("data_general/cook_param.dat",         "desc",   92, 128),
    # the staff credits (Options > Credits): 58 x 262-byte records, five
    # 48-byte text slots, then numbers (their character's look) from +240.
    # English from work/staff_roll.py via merge_staff_roll.py
    ("data_general/staff_roll_text.dat",    "role",       0, 48),
    ("data_general/staff_roll_text.dat",    "nickname",  48, 48),
    ("data_general/staff_roll_text.dat",    "realname",  96, 48),
    ("data_general/staff_roll_text.dat",    "msg1",     144, 48),
    ("data_general/staff_roll_text.dat",    "msg2",     192, 48),
    # the Quest menu's list: 6 companions x 8 steps, 0x5C-byte records (id,
    # step, EXP, wanted item / count, reward item / count, then the title).
    # The title is the record's last field, so its capacity runs to the end.
    ("data_treasure/quest_data.dat",        "title",   28, 64),
    # Status > Ramen / Spa: 16 x 120-byte records (8 distinct entries, each
    # stored twice): u32 id, name at +4 (20 bytes only: +24..+39 hold the
    # effect type / value / duration, which a longer name field would zero and
    # freeze the page whenever a status is active), effect text at +40 to the end
    ("data_treasure/ramen_onsen.dat",       "name",    4, 20),
    ("data_treasure/ramen_onsen.dat",       "desc",   40, 80),
]


def read_table(rel):
    d = open(os.path.join(ROOT, rel), "rb").read()
    count = struct.unpack_from("<I", d, 0)[0]
    rec_size = (len(d) - 4) // count
    return bytearray(d), count, rec_size


def get_string(data, rec_size, index, off, cap):
    base = 4 + index * rec_size + off
    end = data.find(b"\0", base, base + cap)
    if end == -1:
        end = base + cap
    return data[base:end].decode("shift_jis", "replace")


def set_string(data, rec_size, index, off, cap, text):
    """Write text into the field and zero the remainder (clearing stale bytes)."""
    blob = text.encode("shift_jis")
    if len(blob) > cap - 1:
        raise ValueError("%d bytes exceeds %d usable" % (len(blob), cap - 1))
    base = 4 + index * rec_size + off
    data[base:base + cap] = blob + b"\0" * (cap - len(blob))


def export(out_tsv):
    rows = []
    for rel, field, off, cap in SCHEMA:
        data, count, rec_size = read_table(rel)
        for i in range(count):
            jp = get_string(data, rec_size, i, off, cap)
            if not jp.strip():
                continue
            rows.append({
                "file": rel, "record": i, "field": field,
                "cap_bytes": cap - 1,
                "jp_bytes": len(jp.encode("shift_jis", "replace")),
                "japanese": jp.replace("\n", "\\n"),
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
            eng = row["english"].strip()
            if eng:
                out[(row["file"], int(row["record"]), row["field"])] = \
                    row["english"].replace("\\n", "\n")
    return out


def check(in_tsv):
    problems = []
    with open(in_tsv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            eng = row["english"].strip()
            if not eng:
                continue
            text = row["english"].replace("\\n", "\n")
            try:
                blob = text.encode("shift_jis")
            except UnicodeEncodeError as exc:
                problems.append((row["file"], row["record"], row["field"],
                                 "UNENCODABLE", text[exc.start:exc.end]))
                continue
            if len(blob) > int(row["cap_bytes"]):
                problems.append((row["file"], row["record"], row["field"],
                                 "TOO LONG",
                                 "%d > %s bytes" % (len(blob), row["cap_bytes"])))
    return problems


def apply_all(translations):
    """Return {rel: rebuilt bytes} for every table that has translations."""
    out = {}
    by_file = {}
    for (rel, idx, field), eng in translations.items():
        by_file.setdefault(rel, []).append((idx, field, eng))
    caps = {(r, f): (o, c) for r, f, o, c in SCHEMA}
    for rel, items in by_file.items():
        data, count, rec_size = read_table(rel)
        for idx, field, eng in items:
            off, cap = caps[(rel, field)]
            set_string(data, rec_size, idx, off, cap, eng)
        out[rel] = bytes(data)
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    if argv[1] == "export":
        rows = export(argv[2])
        print("exported %d strings -> %s" % (len(rows), argv[2]))
    elif argv[1] == "check":
        problems = check(argv[2])
        for p in problems[:40]:
            print("%-34s rec %-5s %-5s %-12s %s" % p)
        print("%d problems" % len(problems))
    elif argv[1] == "stats":
        import collections
        done = collections.Counter()
        total = collections.Counter()
        with open(argv[2], newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                key = "%s %s" % (os.path.basename(row["file"]), row["field"])
                total[key] += 1
                if row["english"].strip():
                    done[key] += 1
        for k in sorted(total):
            print("  %-34s %5d / %5d" % (k, done[k], total[k]))
        print("  %-34s %5d / %5d" % ("TOTAL", sum(done.values()), sum(total.values())))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
