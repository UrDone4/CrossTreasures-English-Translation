#!/usr/bin/env python3
"""Built-in fake friends: the patched game fills empty friend slots by itself.

Some content is gated on friends met over local wireless: the stone monuments
open treasure rooms that lead into a friend's world, and a friend's world is
the only way to reach dungeon themes your own world did not roll. The DS's
local wireless can't be used over the internet, so the patch gives every save
eight friends (MULTIPLAYER.md has the whole investigation).

How the game keeps friends (ARM9):
  * world manager: +0 -> nine 0x58-byte records (slot 0 = you), +4 -> 450
    floors (9 worlds x 50) of 0x3C bytes.
  * 0x206CED8 occupied(mgr, slot): record +8..+17 not all zero.
  * 0x206ADB0 buildWorld(mgr, slot, seed_lo, seed_hi, [sp]=ctx): generates a
    whole world from a 64-bit seed (record +0..+7); seed 0 = only recompute
    the derived data from the floor seeds already there. ctx = the 0x3C-byte
    world_decide table object (ctor 0x208A3AC, load 0x208A410, free 0x208A440).
  * 0x206AD38 (end of loading a save, from 0x204E7B4): rebuild all 9 slots.
  * 0x206A794 (new game, from 0x206A784): make slot 0's ID and world.
  * 0x206CE4C canConnect: needs *your own* best floor >= the monument's floor,
    then an occupied slot whose best floor is too -- so friends at floor 50
    keep pace with you by themselves.

The patch adds FILL(mgr, ctx): for each empty slot 1-8 whose friend has
joined (your best floor, record 0 +0x44, >= their join floor), copy your
record, then that friend's world seed (+0..+7) and a 30-byte block over
+0x12..+0x2F -- name, Character Creator look, birthday, gear model keys --
then best floor 50, the friend marker bytes (+0x45..+0x4E = 3) and a distinct
ID byte (+0x10), and buildWorld with the seed. It runs after loading a save
(before the game's own rebuild) and after a new game's own world is made, so a
friend arrives on the first load after you pass their floor. Real friends are
never touched (occupied slots are skipped).

Names, birthdays, classes, looks, join floors and seeds: work/fake_friends.py;
gear: pick_gear() below. The seeds were chosen so the
eight worlds together cover every theme option of every 5-floor block
(`search` below re-derives them; `worlds` prints what each friend gets).

Space: the Download Play library's debug state-name strings and their pointer
table (0x20A8E00-0x20A90A7) are compiled-out debug data -- nothing in ARM9 or
any overlay points into them (checked), and they lie before the autoload/BSS
start (0x20A9260). The table goes at 0x20A8E00, the code at 0x20A8F04.

    python tools/fake_friends_rom.py check     assemble, verify the sites
    python tools/fake_friends_rom.py worlds    themes per friend and block
    python tools/fake_friends_rom.py search    re-run the seed search
"""

import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "work"))

ARM9_ROM, ARM9_RAM = 0x4000, 0x2000000
TABLE_AT = 0x20A8E00          # entries of friends 1-6 (the rest after the code)
ENTRY = 39                    # seed 8, record +0x12..+0x2F (30), join floor 1
AREA1_ENTRIES = 6
CODE_AT = 0x20A8F04           # up to 0x20A90A8
CAVE_END = 0x20A90A8
TABLE_END = 0x20A8EEC         # a live pointer table starts here

OCCUPIED = 0x206CED8
BUILD_WORLD = 0x206ADB0
REBUILD_ALL = 0x206AD38
NEWGAME_WORLD = 0x206A794
CTX_CTOR, CTX_LOAD, CTX_FREE = 0x208A3AC, 0x208A410, 0x208A440
COPY8 = 0x2008504             # (src, dst, len)
FILL8 = 0x2008448             # (dst, value, len)
HOOK_LOAD = 0x204E7B4         # bl 0x206AD38
HOOK_NEW = 0x206A784          # bl 0x206A794


# ---------------------------------------------------------------- assembler
def _imm(v):
    """ARM data-processing immediate (8 bits rotated right by an even amount)."""
    for rot in range(16):
        x = ((v << (2 * rot)) | (v >> (32 - 2 * rot))) & 0xFFFFFFFF
        if x < 256:
            return (rot << 8) | x
    raise ValueError("immediate %#x not encodable" % v)


class Asm:
    def __init__(self, org):
        self.org, self.words, self.labels, self.fix = org, [], {}, []

    @property
    def pc(self):
        return self.org + 4 * len(self.words)

    def label(self, name):
        self.labels[name] = self.pc

    def w(self, word):
        self.words.append(word & 0xFFFFFFFF)

    def push(self, *regs):
        self.w(0xE92D0000 | sum(1 << r for r in regs))

    def pop(self, *regs):
        self.w(0xE8BD0000 | sum(1 << r for r in regs))

    def mov(self, rd, imm=None, rm=None):
        if rm is not None:
            self.w(0xE1A00000 | rd << 12 | rm)
        else:
            self.w(0xE3A00000 | rd << 12 | _imm(imm))

    def add(self, rd, rn, imm=None, rm=None, lsl=0):
        if rm is not None:
            self.w(0xE0800000 | rn << 16 | rd << 12 | lsl << 7 | rm)
        else:
            self.w(0xE2800000 | rn << 16 | rd << 12 | _imm(imm))

    def sub(self, rd, rn, imm):
        self.w(0xE2400000 | rn << 16 | rd << 12 | _imm(imm))

    def cmp(self, rn, imm):
        self.w(0xE3500000 | rn << 16 | _imm(imm))

    def mla(self, rd, rm, rs, rn):
        self.w(0xE0200090 | rd << 16 | rn << 12 | rs << 8 | rm)

    def ldr(self, rd, rn, off=0):
        self.w(0xE5900000 | rn << 16 | rd << 12 | off)

    def str_(self, rd, rn, off=0):
        self.w(0xE5800000 | rn << 16 | rd << 12 | off)

    def strb(self, rd, rn, off=0, cond=0xE):
        self.w(cond << 28 | 0x05C00000 | rn << 16 | rd << 12 | off)

    def ldrb(self, rd, rn, off=0):
        self.w(0xE5D00000 | rn << 16 | rd << 12 | off)

    def ldrb_r(self, rd, rn, rm):
        self.w(0xE7D00000 | rn << 16 | rd << 12 | rm)

    def cmp_r(self, rn, rm):
        self.w(0xE1500000 | rn << 16 | rm)

    def mov_c(self, rd, rm, cond):
        self.w(cond << 28 | 0x01A00000 | rd << 12 | rm)

    def ldr_lit(self, rd, value):
        self.fix.append(("lit", len(self.words), rd, value))
        self.w(0)

    def branch(self, cond, target, link=False):
        self.fix.append(("b", len(self.words), cond, link, target))
        self.w(0)

    def bl(self, target):
        self.branch(0xE, target, link=True)

    def b(self, target, cond=0xE):
        self.branch(cond, target)

    def finish(self):
        lits = []
        for f in self.fix:
            if f[0] == "lit":
                lits.append(f)
        pool = {}
        for _, _, _, value in lits:
            if value not in pool:
                pool[value] = self.pc
                self.w(value)
        for f in self.fix:
            at = self.org + 4 * f[1]
            if f[0] == "lit":
                _, i, rd, value = f
                off = pool[value] - (at + 8)
                assert 0 <= off < 4096
                self.words[i] = 0xE59F0000 | rd << 12 | off
            else:
                _, i, cond, link, target = f
                t = self.labels[target] if isinstance(target, str) else target
                off = (t - (at + 8)) >> 2
                self.words[i] = cond << 28 | (0xB if link else 0xA) << 24 | (off & 0xFFFFFF)
        return b"".join(struct.pack("<I", x) for x in self.words)


def bl_word(at, target):
    return 0xEB000000 | (((target - (at + 8)) >> 2) & 0xFFFFFF)


# ------------------------------------------------------------------- code
R0, R1, R2, R3, R4, R5, R6, R7, R8, SP, LR, PC = 0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15
NE, GE, LT = 0x1, 0xA, 0xB


def assemble(floor, tail):
    a = Asm(CODE_AT)
    # WRAP_LOAD(mgr): fill, then the game's own rebuild of all nine slots
    a.label("wrap_load")
    a.push(R4, LR)
    a.mov(R4, rm=R0)
    a.bl("core")
    a.mov(R0, rm=R4)
    a.pop(R4, LR)
    a.b(REBUILD_ALL)
    # WRAP_NEW(mgr): the game's new-game world first, then fill
    a.label("wrap_new")
    a.push(R4, LR)
    a.mov(R4, rm=R0)
    a.bl(NEWGAME_WORLD)
    a.mov(R0, rm=R4)
    a.pop(R4, LR)
    a.b("core")
    # CORE(mgr): a world_decide table object on the stack around FILL
    a.label("core")
    a.push(R4, LR)
    a.sub(SP, SP, 0x40)
    a.mov(R4, rm=R0)
    a.mov(R0, rm=SP)
    a.bl(CTX_CTOR)
    a.mov(R0, rm=SP)
    a.bl(CTX_LOAD)
    a.mov(R0, rm=R4)
    a.mov(R1, rm=SP)
    a.bl("fill")
    a.mov(R0, rm=SP)
    a.bl(CTX_FREE)
    a.add(SP, SP, 0x40)
    a.pop(R4, PC)
    # FILL(mgr, ctx)
    a.label("fill")
    a.push(R4, R5, R6, R7, R8, LR)
    a.sub(SP, SP, 8)
    a.mov(R4, rm=R0)
    a.mov(R8, rm=R1)
    a.mov(R5, 1)
    a.label("loop")
    a.mov(R0, rm=R4)
    a.mov(R1, rm=R5)
    a.bl(OCCUPIED)
    a.cmp(R0, 0)
    a.b("next", NE)
    a.sub(R1, R5, 1)
    a.ldr_lit(R0, TABLE_AT)
    a.ldr_lit(R2, tail - AREA1_ENTRIES * ENTRY)
    a.cmp(R1, AREA1_ENTRIES)
    a.mov_c(R0, R2, GE)              # friends 7-8 sit after the code
    a.mov(R2, ENTRY)
    a.mla(R6, R1, R2, R0)            # this friend's entry
    a.ldrb(R0, R6, ENTRY - 1)        # the floor they join at
    a.ldr(R1, R4, 0)
    a.ldrb(R1, R1, 0x44)             # your best floor
    a.cmp_r(R1, R0)
    a.b("next", LT)                  # not joined yet
    a.ldr(R0, R4, 0)                 # record 0 = yours
    a.mov(R1, 0x58)
    a.mla(R7, R5, R1, R0)            # record[slot]
    a.mov(R1, rm=R7)
    a.mov(R2, 0x58)
    a.bl(COPY8)                      # start from your own record
    a.mov(R0, rm=R6)
    a.mov(R1, rm=R7)
    a.mov(R2, 8)
    a.bl(COPY8)                      # world seed -> +0..+7
    a.add(R0, R6, 8)
    a.add(R1, R7, 0x12)
    a.mov(R2, 30)
    a.bl(COPY8)                      # name, look, birthday, gear -> +0x12..+0x2F
    a.add(R0, R5, 0xA0)
    a.strb(R0, R7, 0x10)             # a distinct ID byte
    a.mov(R0, floor)
    a.strb(R0, R7, 0x44)             # best floor
    a.add(R0, R7, 0x45)
    a.mov(R1, 3)
    a.mov(R2, 10)
    a.bl(FILL8)                      # friend marker bytes
    a.ldr(R2, R7, 0)                 # the seed, from the (aligned) record
    a.ldr(R3, R7, 4)
    a.str_(R8, SP, 0)
    a.mov(R0, rm=R4)
    a.mov(R1, rm=R5)
    a.bl(BUILD_WORLD)                # the game builds the friend's world
    a.label("next")
    a.add(R5, R5, 1)
    a.cmp(R5, 9)
    a.b("loop", LT)
    a.add(SP, SP, 8)
    a.pop(R4, R5, R6, R7, R8, PC)
    code = a.finish()
    return code, a.labels


def table():
    """(area-1 bytes, the rest, best floor). One 39-byte entry per friend in
    join order: world seed (-> record +0..+7), 30 bytes written over record
    +0x12..+0x2F (name, Character Creator look, birthday, gear model keys) and
    the floor they join at. Friends 1-6 fill area 1; 7-8 go after the code."""
    import fake_friends as ff
    friends, seeds = list(ff.FRIENDS), list(ff.WORLD_SEEDS)
    assert len(seeds) == 8 and len(friends) == 8, "need 8 friends and 8 seeds"
    problems = ff.check()
    if problems:
        raise ValueError("work/fake_friends.py: " + "; ".join(problems))
    entries = []
    for f, join, gfl, (lo, hi) in zip(friends, ff.JOIN_FLOORS, ff.GEAR_FLOORS, seeds):
        enc = "".join(chr(ord(c) + 0xFEE0) for c in f["name"]).encode("shift_jis")
        month, day = f["birthday"]
        gear = pick_gear(f["cls"], gfl)
        blk = (enc + bytes(12 - len(enc))                       # +0x12 name
               + b"\0" + ff.look_bytes(f)                        # +0x1E, look +0x1F..+0x23
               + bytes([month, day])                            # +0x24 birthday
               + b"".join(struct.pack("<H", k) for k, _n in gear))  # +0x26 gear
        assert len(blk) == 30
        entries.append(struct.pack("<II", lo, hi) + blk + bytes([join]))
    return (b"".join(entries[:AREA1_ENTRIES]), b"".join(entries[AREA1_ENTRIES:]),
            ff.FLOOR)


# ------------------------------------------------------------------- gear
# A friend's look on their island comes from record +0x26..+0x2F: the model
# keys (equip_param.dat +8, = equip_model.narc entry keys) of weapon, body,
# head, feet and off-hand (MULTIPLAYER.md section 6). Each friend gets a set
# that suits their class, as strong as the floor they join at.
CLASS_WEAPON = {"Fighter": 0x10, "Thief": 0x10, "Mage": 0x20, "Priest": 0x30}
CLASS_WORDS = {   # armour series names that read as that class
    "Fighter": ("Fight", "Battle", "Knight", "General", "Nobunaga", "Hideyoshi",
                "Ieyasu", "War ", "Platinum", "Mithril", "Daitarn", "Dragon"),
    "Thief": ("Thief", "Ninja", "Jonin", "Leather", "Desert", "Wind", "Phantom",
              "Black", "Dark", "Bullseye", "Universe", "Adventure", "Quest"),
    "Mage": ("Mage", "Sorcer", "Onmyo", "Yellow", "Blue ", "Crystal", "Shaman",
             "Elder", "Star", "Moon"),
    "Priest": ("Healer", "Cleric", "Bishop", "Saint", "Holy", "Angel", "Healing"),
}
CLASS_AVOID = {   # series a class's words would catch by accident
    "Mage": ("Dragon",),      # "Blue " also matches Blue Dragon Mail / Helm / Legs
}
SWORD_WORDS = ("Sword", "Blade", "Saber", "Katana", "Flamberg", "Edge", "Cut")
KNIFE_WORDS = ("Knife", "Kodachi", "Katar", "Dusk", "Touch", "Kiss", "Edge")
BASE_RANK, RANK_PER_FLOOR = 10, 6      # target +4 rank: floor 0 -> 10, 35 -> 220


def equipment():
    """[(slot type, rank, model key, English name)] from equip_param.dat."""
    names = {}
    with open(os.path.join(BASE, "work", "data_text.tsv"), encoding="utf-8") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if f[0] == "data_item/equip_param.dat" and f[2] == "name":
                names[int(f[1])] = f[-1]
    d = open(os.path.join(BASE, "extracted", "data_item", "equip_param.dat"), "rb").read()
    out = []
    for i in range(struct.unpack_from("<I", d)[0]):
        r = d[4 + i * 132:4 + (i + 1) * 132]
        typ, rank, key = struct.unpack_from("<HIH", r, 2)[0], \
            struct.unpack_from("<I", r, 4)[0], struct.unpack_from("<H", r, 8)[0]
        out.append((typ & 0xF0, rank, key, names.get(i, "?"), typ >> 8))
    return out


def pick_gear(cls, floor):
    """(weapon, body, head, feet, off-hand) as [(key, name)] for one friend."""
    target = BASE_RANK + RANK_PER_FLOOR * floor
    eq = [e for e in equipment() if e[4] >= 0xC0]      # skip event / joke series

    def best(slot, words=None):
        pool = [e for e in eq if e[0] == slot
                and (words is None or any(w in e[3] for w in words))
                and not any(a in e[3] for a in CLASS_AVOID.get(cls, ()))]
        if not pool:
            pool = [e for e in eq if e[0] == slot]
        return min(pool, key=lambda e: (abs(e[1] - target), -e[1]))

    words = CLASS_WORDS[cls]
    wwords = {"Fighter": SWORD_WORDS, "Thief": KNIFE_WORDS}.get(cls)
    weapon = best(CLASS_WEAPON[cls], wwords)
    if cls == "Fighter":
        off = best(0x40)
    elif cls == "Thief":
        off = weapon                                   # a knife in each hand
    else:
        off = None
    parts = [weapon, best(0x60, words), best(0x50, words), best(0x70, words), off]
    return [(e[2], e[3]) if e else (0, "-") for e in parts]


def build(floor):
    """Assemble with the address of the entries placed right after the code."""
    code, _ = assemble(floor, CODE_AT)
    code, labels = assemble(floor, CODE_AT + len(code))
    return code, labels


def rom(addr):
    return ARM9_ROM + addr - ARM9_RAM


# original bytes at the patch sites, checked before writing
EXPECT = {
    HOOK_LOAD: bl_word(HOOK_LOAD, REBUILD_ALL),
    HOOK_NEW: bl_word(HOOK_NEW, NEWGAME_WORLD),
}
CAVE_STARTS = {TABLE_AT: b"MBP_STATE_IDLE", CODE_AT: struct.pack("<I", 0x20A8E10)}


def apply(data):
    """Patch a ROM image (bytearray) in place. Returns the number of edits."""
    tbl, tail, floor = table()
    code, labels = build(floor)
    code += tail
    assert TABLE_AT + len(tbl) <= TABLE_END and CODE_AT + len(code) <= CAVE_END
    for at, word in EXPECT.items():
        have = struct.unpack_from("<I", data, rom(at))[0]
        if have != word:
            raise SystemExit("fake_friends_rom: unexpected code at %#x (%#x)" % (at, have))
    for at, head in CAVE_STARTS.items():
        if bytes(data[rom(at):rom(at) + len(head)]) != head:
            raise SystemExit("fake_friends_rom: cave at %#x is not the expected data" % at)
    data[rom(TABLE_AT):rom(TABLE_AT) + len(tbl)] = tbl
    data[rom(CODE_AT):rom(CODE_AT) + len(code)] = code
    struct.pack_into("<I", data, rom(HOOK_LOAD), bl_word(HOOK_LOAD, labels["wrap_load"]))
    struct.pack_into("<I", data, rom(HOOK_NEW), bl_word(HOOK_NEW, labels["wrap_new"]))
    return 4


# ------------------------------------------------------ world generation model
M64 = (1 << 64) - 1
MUL, ADD = 0x5D588B656C078965, 0x269EC3


class Rng:
    """The game's MATH-style 64-bit LCG (0x2022114 seed, 0x20221A4 rand)."""

    def __init__(self, lo, hi):
        self.x = hi << 32 | lo

    def rand(self, mx=0):
        self.x = (self.x * MUL + ADD) & M64
        hi = self.x >> 32
        return (hi * mx) >> 32 if mx else hi


def floor_seeds(lo, hi):
    """The 50 floor seeds buildWorld derives from a world seed (verified 50/50
    against three real saves)."""
    r, out = Rng(lo, hi), []
    for _ in range(50):
        lo = (lo + r.rand()) & 0xFFFFFFFF
        hi = (hi + r.rand()) & 0xFFFFFFFF
        out.append((lo, hi))
    return out


def decide_table():
    d = open(os.path.join(BASE, "extracted", "data_general", "world_decide.dat"), "rb").read()
    n = struct.unpack_from("<I", d, 0)[0]
    t = {}
    for e in range(n):
        v = struct.unpack_from("<9I", d, 4 + e * 36)
        t[v[0]] = [(v[1 + 2 * i], v[2 + 2 * i]) for i in range(4) if v[2 + 2 * i]]
    return t


def themes(lo, hi, table=None):
    """Theme (BGList row) of each 5-floor block: the RNG reseeded with the
    block's first floor seed, rand(100)+1 against the block's weights
    (0x208A658)."""
    table = table or decide_table()
    fs, out = floor_seeds(lo, hi), []
    for b in range(10):
        x, cum, pick = Rng(*fs[5 * b]).rand(100) + 1, 0, None
        for val, w in table[b + 1]:
            cum += w
            if x <= cum:
                pick = val - 1
                break
        out.append(pick)
    return out


def search(seed=20260925):
    table = decide_table()
    opts = [[v - 1 for v, _ in table[b + 1]] for b in range(10)]
    rnd, found = random.Random(seed), []
    for k in range(8):
        want = [o[k % len(o)] for o in opts]
        while True:
            lo, hi = rnd.getrandbits(32), rnd.getrandbits(32)
            if lo and hi and themes(lo, hi, table) == want:
                found.append((lo, hi))
                break
    return found


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "check":
        tbl, tail, floor = table()
        code, labels = build(floor)
        rom_path = os.path.join(BASE, "Cross Treasures (Japan).nds")
        data = bytearray(open(rom_path, "rb").read())
        apply(data)
        print("table %d bytes at %#x (room %d); code %d + blocks %d bytes at %#x (room %d)"
              % (len(tbl), TABLE_AT, TABLE_END - TABLE_AT, len(code), len(tail),
                 CODE_AT, CAVE_END - CODE_AT))
        import fake_friends as ff
        for f, join, gfl in zip(ff.FRIENDS, ff.JOIN_FLOORS, ff.GEAR_FLOORS):
            print("  %-6s joins at floor %2d, %-7s %s" % (
                f["name"], join, f["cls"],
                " / ".join(n for _k, n in pick_gear(f["cls"], gfl))))
        print("entry points:", {k: hex(v) for k, v in labels.items()
                                if k in ("wrap_load", "wrap_new", "core", "fill")})
        return 0
    if cmd == "worlds":
        import fake_friends as ff
        rows = [l.split(",")[9] for l in open(os.path.join(BASE, "extracted", "bg", "BGList.csv"),
                                               encoding="shift_jis").read().split("\n")
                if l and not l.startswith("#")]
        for nm, (lo, hi) in zip(ff.NAMES, ff.WORLD_SEEDS):
            print("%-6s %s" % (nm, " / ".join(rows[t] for t in themes(lo, hi))))
        return 0
    if cmd == "search":
        for lo, hi in search():
            print("    (0x%08X, 0x%08X)," % (lo, hi))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
