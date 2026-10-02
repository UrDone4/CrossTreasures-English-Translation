#!/usr/bin/env python3
"""Room for new ARM9 code: grow the ITCM autoload block.

ARM9 has no free space left for code (the Download Play debug strings that
tools/fake_friends_rom.py uses were the last dead block found; main RAM from
the end of the static image to the overlay area, 0x20A9260-0x20CC5E0, is all
BSS). ITCM is different: 32 KB of fast RAM at 0x1FF8000 of which the game's
autoload block uses only 0x5C0 bytes. crt0's autoload (0x2000A1C) copies each
block from the image, back to back from `autoload_start` (0x20A9260), using
the sizes in the autoload list; the static BSS is cleared only afterwards. So
bytes appended to the ITCM block's data land in ITCM at boot and stay there,
reachable by BL from anywhere in main RAM.

Growing it means inserting bytes after the ITCM block's data: the DTCM
block's data and the autoload list move up, the module params (list start /
end) and the header's ARM9 size follow, and the SDK footer (0xDEC00621,
params offset, 0) moves to the new end of the image. The SDK's ITCM arena
(OS_GetInitArenaLo, literal at 0x2006FD0) begins at the block's end, so it is
moved up too -- an ITCM allocation must never land on the new code.

In the ROM the image is followed by padding up to the ARM9 overlay table
(0xADA00, 0x180 bytes; 348 bytes of room in the original), then padding up to
overlay 0 (0xADC00). When the image needs more, `grow` slides the overlay
table up into its own trailing padding (only header 0x50 points at it; up to
0xADA80), which gives 128 bytes more in all. The Map dungeon-name patch uses
376 (table at 0xADA20, 96 bytes of slide left). Beyond that the table would
have to move to the end of the ROM. `grow` refuses to overwrite anything that
is not padding (0x00 / 0xFF).

    code_at = itcm.grow(rom_bytearray, n)   # returns the RAM address (in ITCM)
    itcm.put(rom_bytearray, code_at, blob)  # write it there
"""

import struct

ARM9_ROM_HDR = 0x20        # header: ARM9 rom offset, entry, ram address, size
ITCM_BASE = 0x1FF8000
ITCM_END = 0x2000000
FOOTER_MAGIC = 0xDEC00621
ARENA_ITCM_LO = 0x2006FD0  # literal: OS_GetInitArenaLo(OS_ARENA_ITCM), 0x2006F38 case 3


def _layout(data):
    rom_off, _entry, ram, size = struct.unpack_from("<IIII", data, ARM9_ROM_HDR)
    magic, params_off, _z = struct.unpack_from("<III", data, rom_off + size)
    assert magic == FOOTER_MAGIC, "ARM9 footer not found"
    p = rom_off + params_off
    al_start_list, al_end_list, al_data = struct.unpack_from("<III", data, p)
    blocks = []
    for a in range(al_start_list, al_end_list, 12):
        blocks.append(struct.unpack_from("<III", data, rom_off + a - ram))
    return rom_off, ram, size, p, al_start_list, al_end_list, al_data, blocks


def _next_item(data, after):
    """ROM offset of the first header-listed item or file past `after`."""
    offs = [struct.unpack_from("<I", data, o)[0] for o in (0x30, 0x40, 0x48, 0x50, 0x58, 0x68)]
    fat, fat_size = struct.unpack_from("<II", data, 0x48)
    for i in range(0, fat_size, 8):
        start, end = struct.unpack_from("<II", data, fat + i)
        if end > start:
            offs.append(start)
    return min(o for o in offs if o > after)


def _is_padding(blob):
    return not blob.translate(None, b"\0\xff")


def _slide_overlay_table(data, limit, want):
    """If the item right after the image is the ARM9 overlay table, move it
    up into the padding after it (at most to the next item) so the image can
    end at `want`. Returns the new limit. Only header 0x50 points at it."""
    ot, ot_size = struct.unpack_from("<II", data, 0x50)
    if ot != limit:
        return limit
    after = _next_item(data, ot)
    new = (want + 0x1F) & ~0x1F                     # keep it 32-byte aligned
    if new + ot_size > after or not _is_padding(bytes(data[ot + ot_size:new + ot_size])):
        return limit
    table = bytes(data[ot:ot + ot_size])
    data[ot:new + ot_size] = bytes(new - ot) + table
    struct.pack_into("<I", data, 0x50, new)
    return new


def itcm_size(data):
    blocks = _layout(data)[7]
    dst, size, _bss = blocks[0]
    assert dst == ITCM_BASE, "first autoload block is not ITCM"
    return size


def grow(data, n):
    """Append `n` zero bytes (multiple of 4) to the ITCM block; return their
    RAM address. `data` is the whole ROM (bytearray), edited in place."""
    assert n > 0 and n % 4 == 0
    rom_off, ram, size, p, l0, l1, al_data, blocks = _layout(data)
    dst, isize, ibss = blocks[0]
    assert dst == ITCM_BASE and ibss == 0, "unexpected ITCM autoload block"
    assert ITCM_BASE + isize + n <= ITCM_END, "ITCM full"
    at = rom_off + (al_data - ram) + isize          # end of the ITCM data
    end = rom_off + size + 12                       # end of image + footer
    limit = _next_item(data, rom_off)
    if end + n > limit:
        limit = _slide_overlay_table(data, limit, end + n)
    if end + n > limit:
        raise SystemExit("itcm: no ROM room after ARM9 (%d bytes, need %d)"
                         % (limit - end, n))
    pad = bytes(data[end:end + n])
    if not _is_padding(pad):
        raise SystemExit("itcm: the bytes after ARM9 are not padding")
    tail = bytes(data[at:end])
    data[at:at + n] = bytes(n)
    data[at + n:end + n] = tail
    # the ITCM block's size in the (moved) autoload list
    struct.pack_into("<I", data, rom_off + (l0 + n - ram) + 4, isize + n)
    # module params: autoload list start / end
    struct.pack_into("<II", data, p, l0 + n, l1 + n)
    struct.pack_into("<I", data, ARM9_ROM_HDR + 12, size + n)
    # the SDK's ITCM arena starts where the block ends (the literal the
    # linker put in OS_GetInitArenaLo); move it past the new bytes so an
    # ITCM allocation can never land on them
    lit = rom_off + ARENA_ITCM_LO - ram
    have = struct.unpack_from("<I", data, lit)[0]
    assert have == ITCM_BASE + isize, "ITCM arena start %#x, expected %#x" % (
        have, ITCM_BASE + isize)
    struct.pack_into("<I", data, lit, ITCM_BASE + isize + n)
    return ITCM_BASE + isize


def put(data, addr, blob):
    """Write `blob` at ITCM RAM address `addr` (inside the ITCM block data)."""
    rom_off, ram, _size, _p, _l0, _l1, al_data, blocks = _layout(data)
    dst, isize, _ = blocks[0]
    assert ITCM_BASE <= addr and addr + len(blob) <= ITCM_BASE + isize
    o = rom_off + (al_data - ram) + (addr - ITCM_BASE)
    data[o:o + len(blob)] = blob


def main(argv):
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = argv[1] if len(argv) > 1 else os.path.join(base, "Cross Treasures (Japan).nds")
    data = bytearray(open(path, "rb").read())
    rom_off, ram, size, p, l0, l1, al_data, blocks = _layout(data)
    print("ARM9 rom %#x ram %#x size %#x; autoload data %#x, list %#x-%#x"
          % (rom_off, ram, size, al_data, l0, l1))
    for b in blocks:
        print("  block -> %#x size %#x bss %#x" % b)
    end = rom_off + size + 12
    print("room after the image: %d bytes" % (_next_item(data, rom_off) - end))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
