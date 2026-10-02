#!/usr/bin/env python3
"""The Map screen's dungeon-name tab (ARM9 code patch).

View Map lists a player's floors (1F-5F, 6F-10F ...). Each 5-floor block is a
dungeon theme -- Royal Graves, Limestone Cave ... -- rolled from that player's
world seed, so it differs per friend and changes when your own dungeon is
reset. The screen never said which dungeon a floor belongs to; this patch adds
a tab in the empty strip right of the "Map" title (a mirror of the Map tab,
tools/map_obj.py cell 34) with the highlighted floor's dungeon name in it,
read live from the game's own data:

    world manager 0x20C5994: +4 -> 450 floor records (9 worlds x 50), 0x3C
    bytes each; record +0x28 = the floor's theme (a BGList row, 0-based,
    written by buildWorld 0x206ADB0). +0x2C -> the BGList table (0x1C-byte
    entries, name at +5, 16 bytes, NUL-padded): loaded by 0x206D5A0 (a no-op
    when already loaded) and freed by 0x206D81C. The dungeon loads it; on the
    island it may not be, so the Map screen loads it itself and frees it on
    exit if it was the one that loaded it.

The Map screen object (vtable 0x20A2BA0; `this` below):
    +0x04 OBJ layer    +0x14 next free OBJ tile    +0x28 sprite sets (cells)
    +0x2C text windows, an array of 0x4C-byte objects (4 in the original):
          +0x00 world-change name, +0x4C floor-view name (145,56),
          +0x98 single-floor dungeon line, +0xE4 Treasure Points (164,124)
    +0x20 "floor changed, redraw" flag    +0x5C highlighted floor (1-based)
    +0x60 world slot

Text windows are sprites (tiles from +0x14 onward, not the BG budget):
    0x2042EBC(win, w_tiles, h_tiles, first_tile, [sp] x, y, palette, layer)
              -> tiles used
    0x2042D1C(win, 0) clear    0x2042F54(win, prio) commit, every frame
    0x2042D7C(win, x, y, colour, [sp] flags, str)  flags 0x10 = centre on x
Colour is a font_color.ncl index (sub OBJ palette 15): 1 black, 15 white.
Windows draw with 1px between letters (ctor 0x2042CF4, +0x44 = 1): measure
names as the font's advances + 1 per gap (longest, "Reaper's House", 90px).

Patch sites (original words checked first):
    0x2060284  mov r0,#4        -> #5      a fifth text window (+0x130)
    0x20603DC  pop {r3-r7,pc}   -> b INIT  set it up (12x2 tiles at 152,5)
    0x2060E00  bl clear(TP)     -> bl REDRAW  floor changed: redraw the name,
                                           or "?????" past your own best floor
                                           (record 0 +0x44) -- on every world,
                                           so neither map spoils a dungeon
    0x2060CAC  bl commit(name)  -> bl FRAME   commit it, draw the tab cell
    0x205F748  cmp r6,#4        -> #5      teardown clears it too
    0x205F764  bl array_delete  -> bl EXIT    free BGList if we loaded it

The code lives in ITCM (tools/itcm.py).

    python tools/map_floor_name.py check    assemble and verify the sites
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import itcm  # noqa: E402
from fake_friends_rom import Asm, bl_word, rom, R0, R1, R2, R3, R4, R5, R6, R8, SP, PC, LR  # noqa: E402

SL = 10
MGR = 0x20C5994
BG_LOAD, BG_FREE = 0x206D5A0, 0x206D81C
WIN_INIT, WIN_CLEAR, WIN_DRAW, WIN_COMMIT = 0x2042EBC, 0x2042D1C, 0x2042D7C, 0x2042F54
DRAW_CELL = 0x204FEFC
ARRAY_DELETE = 0x201E60C
N_THEMES = 0x1D            # BGList rows 0-28 are the dungeon themes

WIN = 0x130                # the fifth window: 4 * 0x4C
TAB_CELL = 34              # tools/map_obj.py
TAB_X, TAB_Y = 136, 2      # the tab: flush right, level with the Map tab
TEXT_W = 12                # window 12x2 tiles = 96px: the window draws with
                           # 1px between letters, so "Reaper's House" is 90
TEXT_X = 152               # window left; text centred at +48 -> x 200,
TEXT_Y = 5                 #   the middle of the tab body (144-255)
INK = 15                   # white, like the Map title
UNKNOWN = b"?????"         # floors past your own best floor: no spoilers

SITE_COUNT = 0x2060284
SITE_INIT = 0x20603DC
SITE_REDRAW = 0x2060E00
SITE_FRAME = 0x2060CAC
SITE_EXIT_LOOP = 0x205F748
SITE_EXIT = 0x205F764

EXPECT = {
    SITE_COUNT: 0xE3A00004,                       # mov r0, #4
    SITE_INIT: 0xE8BD80F8,                        # pop {r3-r7, pc}
    SITE_REDRAW: bl_word(SITE_REDRAW, WIN_CLEAR),
    SITE_FRAME: bl_word(SITE_FRAME, WIN_COMMIT),
    SITE_EXIT_LOOP: 0xE3560004,                   # cmp r6, #4
    SITE_EXIT: bl_word(SITE_EXIT, ARRAY_DELETE),
}

EQ, HS, GT = 0x0, 0x2, 0xC
SB = 9


def win(a, dst, this):
    """dst = this->windows + WIN"""
    a.ldr(dst, this, 0x2C)
    a.add(dst, dst, WIN)


def assemble(org):
    a = Asm(org)
    # INIT: end of the window setup (0x206026C); r4 = this, the caller's
    # {r3-r7, lr} still on the stack.
    a.label("init")
    a.sub(SP, SP, 0x10)
    a.mov(R0, TEXT_X)
    a.str_(R0, SP, 0)
    a.mov(R0, TEXT_Y)
    a.str_(R0, SP, 4)
    a.mov(R0, 0xF)
    a.str_(R0, SP, 8)
    a.ldr(R0, R4, 4)
    a.str_(R0, SP, 0xC)
    win(a, R0, R4)
    a.mov(R1, TEXT_W)
    a.mov(R2, 2)
    a.ldr(R3, R4, 0x14)
    a.bl(WIN_INIT)
    a.ldr(R1, R4, 0x14)
    a.add(R0, R1, rm=R0)
    a.str_(R0, R4, 0x14)                 # tiles used
    win(a, R0, R4)
    a.mov(R1, 0)
    a.bl(WIN_CLEAR)
    a.ldr_lit(R5, MGR)
    a.ldr(R0, R5, 0x2C)
    a.cmp(R0, 0)
    a.mov(R6, 0)
    a.b("init_flag", 0x1)                # NE: already loaded, not ours
    a.mov(R0, rm=R5)
    a.bl(BG_LOAD)
    a.mov(R6, 1)
    a.label("init_flag")
    a.ldr_lit(R0, "flag")
    a.str_(R6, R0, 0)
    a.add(SP, SP, 0x10)
    a.pop(R3, R4, R5, R6, 7, PC)
    # REDRAW: in 0x2060D98 (Treasure Points), when the floor changed.
    # r0/r1 = the TP window clear's args; r4 = this, r8 = the floor record.
    a.label("redraw")
    a.push(R3, R4, R5, LR)
    a.bl(WIN_CLEAR)
    win(a, R0, R4)
    a.mov(R1, 0)
    a.bl(WIN_CLEAR)
    a.ldr_lit(R0, MGR)
    a.ldr(R1, R0, 0)
    a.ldrb(R1, R1, 0x44)                 # your own best floor (record 0)
    a.ldr_lit(R5, "unknown")
    a.cmp_r(SB, R1)                      # sb = the highlighted floor
    a.b("redraw_draw", GT)               # not reached yet: "?????"
    a.ldr(R0, R0, 0x2C)                  # the name table (INIT loaded it)
    a.ldrb(R1, R8, 0x28)
    a.cmp(R1, N_THEMES)
    a.b("redraw_done", HS)
    a.mov(R2, 0x1C)
    a.mla(R5, R1, R2, R0)
    a.add(R5, R5, 5)                     # the name
    a.label("redraw_draw")
    a.mov(R0, 0x11)                      # centred on x
    a.sub(SP, SP, 8)
    a.str_(R0, SP, 0)
    a.str_(R5, SP, 4)
    win(a, R0, R4)
    a.mov(R1, TEXT_W * 4)
    a.mov(R2, 0)
    a.mov(R3, INK)
    a.bl(WIN_DRAW)
    a.add(SP, SP, 8)
    a.label("redraw_done")
    a.pop(R3, R4, R5, PC)
    # FRAME: end of the floor view's per-frame draw (0x20609B8);
    # r0/r1 = the name window commit's args, sl = this.
    a.label("frame")
    a.push(R4, LR)
    a.bl(WIN_COMMIT)
    win(a, R0, SL)
    a.mov(R1, 0)
    a.bl(WIN_COMMIT)
    a.ldr(R0, SL, 0x28)
    a.mov(R1, TAB_CELL)
    a.mov(R2, TAB_X)
    a.mov(R3, TAB_Y)
    a.bl(DRAW_CELL)
    a.pop(R4, PC)
    # EXIT: teardown (0x205F618) deletes the window array; then free the
    # name table if INIT loaded it.
    a.label("exit")
    a.push(R4, LR)
    a.bl(ARRAY_DELETE)
    a.ldr_lit(R4, "flag")
    a.ldr(R0, R4, 0)
    a.cmp(R0, 0)
    a.b("exit_done", EQ)
    a.mov(R0, 0)
    a.str_(R0, R4, 0)
    a.ldr_lit(R0, MGR)
    a.bl(BG_FREE)
    a.label("exit_done")
    a.pop(R4, PC)
    return a


def build(org):
    """Code, then the flag word, then the "?????" string. Their addresses
    are literals in the code, so assemble twice: once to learn the size."""
    a = assemble(org)
    size = len(_finish(a, {"flag": 0, "unknown": 4}))
    a = assemble(org)
    code = _finish(a, {"flag": org + size, "unknown": org + size + 4})
    assert len(code) == size
    text = UNKNOWN + bytes(4 - len(UNKNOWN) % 4)
    return code + bytes(4) + text, a.labels


def _finish(a, data_at):
    for i, f in enumerate(a.fix):
        if f[0] == "lit" and f[3] in data_at:
            a.fix[i] = (f[0], f[1], f[2], data_at[f[3]])
    return a.finish()


def code_size():
    return len(build(itcm.ITCM_BASE)[0])


def apply(data):
    """Patch a ROM image (bytearray) in place. Returns the number of edits."""
    for at, word in EXPECT.items():
        have = struct.unpack_from("<I", data, rom(at))[0]
        if have != word:
            raise SystemExit("map_floor_name: unexpected code at %#x (%#x)" % (at, have))
    org = itcm.grow(data, code_size())
    code, labels = build(org)
    itcm.put(data, org, code)
    put = lambda at, word: struct.pack_into("<I", data, rom(at), word)  # noqa: E731
    put(SITE_COUNT, 0xE3A00005)
    put(SITE_EXIT_LOOP, 0xE3560005)
    put(SITE_INIT, 0xEA000000 | (((labels["init"] - (SITE_INIT + 8)) >> 2) & 0xFFFFFF))
    put(SITE_REDRAW, bl_word(SITE_REDRAW, labels["redraw"]))
    put(SITE_FRAME, bl_word(SITE_FRAME, labels["frame"]))
    put(SITE_EXIT, bl_word(SITE_EXIT, labels["exit"]))
    return 6


def main(argv):
    if len(argv) > 1 and argv[1] == "check":
        path = os.path.join(BASE, "Cross Treasures (Japan).nds")
        data = bytearray(open(path, "rb").read())
        n = apply(data)
        code, labels = build(itcm.ITCM_BASE + 0x5C0)
        print("%d sites; %d bytes of code in ITCM at %#x; entry points %s"
              % (n, len(code), itcm.ITCM_BASE + 0x5C0,
                 {k: hex(v) for k, v in labels.items() if "_" not in k}))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
