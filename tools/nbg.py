#!/usr/bin/env python3
"""NCCG / NCCL / NCSC codec -- the early background-layer graphics format.

These are the precursors to NCGR/NCLR/NSCR and, unlike them, their magics are
not byte-reversed. Cross Treasures uses them for background layers inside the
info/subgraphics/*.narc archives, which is where the lower-screen HUD labels and
the character-creator text live.

Verified layout (offsets are from the start of each block):

    NCCG -> CHAR  +8  u32 width in tiles
                  +12 u32 height in tiles
                  +16 u32 (unused here)
                  +20 tile data, 8x8 tiles, 32 bytes each at 4bpp
            ATTR  per-tile attribute byte (one per tile)
            LINK  filename of the .ncl this graphic pairs with
            CMNT  developer comment

    NCCL -> PALT  +8  u32 colours per palette (16)
                  +12 u32 palette count
                  +16 BGR555 colour data

    NCSC -> SCRN  +8  u32 width in tiles
                  +12 u32 height in tiles
                  +24 screen data, u16 per cell
            ESCR  same geometry, u32 per cell (extended form)
            LINK  filename of the .ncg this layout pairs with

Rather than hardcoding the data offsets, they are derived from the geometry
(data size must equal w*h*bytes_per_unit), which both locates the data and
validates the parse.

Screen cell bits: 0-9 tile index, 10 H-flip, 11 V-flip, 12-15 palette bank.

    nbg.py info   <file>
    nbg.py render <dir> <index> <out.png>   render a NARC member set
"""

import os
import struct
import sys

TILE = 8


def blocks(data):
    """{tag: (offset, size)} for every block after the 16-byte header."""
    out = {}
    header_size = struct.unpack_from("<H", data, 12)[0]
    p = header_size
    while p + 8 <= len(data):
        tag = bytes(data[p:p + 4])
        size = struct.unpack_from("<I", data, p + 4)[0]
        if size == 0 or not tag.isalnum():
            break
        out[tag] = (p, size)
        p += size
    return out


def link_target(data):
    """The filename recorded in the LINK block, if present."""
    b = blocks(data)
    if b"LINK" not in b:
        return None
    off, size = b[b"LINK"]
    return data[off + 8:off + size].split(b"\0")[0].decode("latin1")


# ----------------------------------------------------------------- NCCL --
def read_nccl(path):
    """Return a flat list of RGBA tuples (16 per palette bank)."""
    d = open(path, "rb").read()
    assert d[:4] == b"NCCL", "not an NCCL"
    off, size = blocks(d)[b"PALT"]
    data_off = off + 16
    count = (size - 16) // 2
    out = []
    for i in range(count):
        v = struct.unpack_from("<H", d, data_off + i * 2)[0]
        r = (v & 0x1F) << 3
        g = ((v >> 5) & 0x1F) << 3
        b = ((v >> 10) & 0x1F) << 3
        out.append((r | r >> 5, g | g >> 5, b | b >> 5, 255))
    return out


# ----------------------------------------------------------------- NCCG --
def read_nccg(path):
    """Return (tiles, width_tiles, height_tiles, bpp)."""
    d = open(path, "rb").read()
    assert d[:4] == b"NCCG", "not an NCCG"
    off, size = blocks(d)[b"CHAR"]
    w, h = struct.unpack_from("<II", d, off + 8)
    n = w * h
    # derive bpp from the data size; this also validates the geometry
    for bpp, per in ((4, 32), (8, 64)):
        data_off = off + size - n * per
        if data_off >= off + 16:
            return bytes(d[data_off:off + size]), w, h, bpp
    raise ValueError("%s: cannot reconcile %dx%d tiles with block size %d"
                     % (path, w, h, size))


def tile_pixels(tiles, index, bpp):
    """64 palette indices for one 8x8 tile."""
    per = 32 if bpp == 4 else 64
    base = index * per
    out = []
    for i in range(64):
        if bpp == 4:
            byte = tiles[base + (i >> 1)] if base + (i >> 1) < len(tiles) else 0
            out.append(byte & 0x0F if i % 2 == 0 else byte >> 4)
        else:
            out.append(tiles[base + i] if base + i < len(tiles) else 0)
    return out


# ----------------------------------------------------------------- NCSC --
def read_ncsc(path):
    """Return (cells, width_tiles, height_tiles) where each cell is a dict."""
    d = open(path, "rb").read()
    assert d[:4] == b"NCSC", "not an NCSC"
    b = blocks(d)
    off, size = b[b"SCRN"]
    w, h = struct.unpack_from("<II", d, off + 8)
    n = w * h
    data_off = off + size - n * 2
    cells = []
    for i in range(n):
        v = struct.unpack_from("<H", d, data_off + i * 2)[0]
        cells.append({"tile": v & 0x3FF, "flip_h": bool(v & 0x400),
                      "flip_v": bool(v & 0x800), "palette": (v >> 12) & 0xF})
    return cells, w, h


def write_ncsc(path, out_path, cells):
    """Write cell entries back, keeping SCRN and ESCR in agreement.

    SCRN packs one u16 per cell: tile | hflip<<10 | vflip<<11 | palette<<12.
    ESCR packs one u32: tile in the low word, and in the high word the palette
    in its *low* bits plus the same 0x400/0x800 flip flags -- not the bit-12
    palette position SCRN uses. Writing only one of the two would leave the
    layer inconsistent.
    """
    d = bytearray(open(path, "rb").read())
    b = blocks(d)
    off, size = b[b"SCRN"]
    w, h = struct.unpack_from("<II", d, off + 8)
    n = w * h
    assert len(cells) == n, "cell count changed"

    scrn = off + size - n * 2
    for i, c in enumerate(cells):
        v = (c["tile"] & 0x3FF) | (c["flip_h"] << 10) | (c["flip_v"] << 11) \
            | ((c["palette"] & 0xF) << 12)
        struct.pack_into("<H", d, scrn + i * 2, v)

    if b"ESCR" in b:
        eoff, esize = b[b"ESCR"]
        escr = eoff + esize - n * 4
        for i, c in enumerate(cells):
            attr = (c["palette"] & 0xF) | (c["flip_h"] << 10) | (c["flip_v"] << 11)
            struct.pack_into("<I", d, escr + i * 4, (c["tile"] & 0xFFFF)
                             | (attr << 16))
    with open(out_path, "wb") as fh:
        fh.write(d)


def grow_nccg(src_bytes, extra_tiles):
    """Return a new NCCG with room for `extra_tiles` more tiles.

    Tiles are added as whole rows (the CHAR block is described in tile rows and
    columns), and the per-tile ATTR block is extended to match. Growing the
    graphic is what makes it possible to give a repainted background cell its
    own private tile: background layers routinely share one tile across many
    cells, and there are rarely spare tiles to steal.
    """
    d = bytearray(src_bytes)
    b = blocks(d)
    coff, csize = b[b"CHAR"]
    w, h = struct.unpack_from("<II", d, coff + 8)
    n = w * h
    per = None
    for size_per in (32, 64):
        if csize - n * size_per >= 16:
            per = size_per
            break
    if per is None:
        raise ValueError("cannot determine bit depth of CHAR block")
    rows = -(-extra_tiles // w)             # ceil
    new_h = h + rows
    new_n = w * new_h
    added = (new_n - n) * per

    out = bytearray(d[:coff])               # 16-byte file header
    # --- CHAR, extended
    char = bytearray(d[coff:coff + csize])
    struct.pack_into("<I", char, 12, new_h)
    struct.pack_into("<I", char, 4, csize + added)
    char += b"\0" * added
    out += char
    # --- remaining blocks, with ATTR extended to one byte per tile
    p = coff + csize
    while p + 8 <= len(d):
        tag = bytes(d[p:p + 4])
        size = struct.unpack_from("<I", d, p + 4)[0]
        if size == 0 or not tag.isalnum():
            break
        block = bytearray(d[p:p + size])
        if tag == b"ATTR":
            struct.pack_into("<I", block, 12, new_h)
            struct.pack_into("<I", block, 4, size + (new_n - n))
            block += b"\0" * (new_n - n)
        out += block
        p += size
    struct.pack_into("<I", out, 8, len(out))     # file size
    return bytes(out)


def write_nccg(path, out_path, tiles):
    """Write tile data back into a copy of an NCCG, preserving every block.

    The tile count and bit depth are unchanged, so ATTR/LINK/CMNT and the file
    size stay valid -- which is what lets a repainted layer drop straight back
    into its NARC member without the archive growing.
    """
    d = bytearray(open(path, "rb").read())
    off, size = blocks(d)[b"CHAR"]
    w, h = struct.unpack_from("<II", d, off + 8)
    n = w * h
    for bpp, per in ((4, 32), (8, 64)):
        data_off = off + size - n * per
        if data_off >= off + 16:
            break
    if len(tiles) != n * per:
        raise ValueError("expected %d bytes of tile data, got %d"
                         % (n * per, len(tiles)))
    d[data_off:data_off + len(tiles)] = tiles
    with open(out_path, "wb") as fh:
        fh.write(d)


def set_tile_pixels(tiles, index, bpp, pixels):
    """Write 64 palette indices into one 8x8 tile of a mutable tile buffer."""
    per = 32 if bpp == 4 else 64
    base = index * per
    for i, v in enumerate(pixels):
        if bpp == 4:
            o = base + (i >> 1)
            if o >= len(tiles):
                return
            if i % 2 == 0:
                tiles[o] = (tiles[o] & 0xF0) | (v & 0x0F)
            else:
                tiles[o] = (tiles[o] & 0x0F) | ((v & 0x0F) << 4)
        else:
            if base + i < len(tiles):
                tiles[base + i] = v & 0xFF


# --------------------------------------------------------------- render --
def compose(nccg, nccl, ncsc):
    """Render a background layer to (width, height, rgba_rows)."""
    tiles, tw, th, bpp = read_nccg(nccg)
    palette = read_nccl(nccl)
    cells, sw, sh = read_ncsc(ncsc)
    width, height = sw * TILE, sh * TILE
    rows = [bytearray(width * 4) for _ in range(height)]
    for i, cell in enumerate(cells):
        cx, cy = (i % sw) * TILE, (i // sw) * TILE
        px = tile_pixels(tiles, cell["tile"], bpp)
        bank = cell["palette"] * 16
        for row in range(TILE):
            for col in range(TILE):
                sr = TILE - 1 - row if cell["flip_v"] else row
                sc = TILE - 1 - col if cell["flip_h"] else col
                idx = px[sr * TILE + sc]
                if idx == 0:
                    continue
                colour = palette[bank + idx] if bank + idx < len(palette) \
                    else (255, 0, 255, 255)
                o = (cx + col) * 4
                rows[cy + row][o:o + 4] = bytes(colour)
    return width, height, rows


def main(argv):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ngfx import write_png

    if len(argv) < 3:
        print(__doc__)
        return 1
    if argv[1] == "info":
        d = open(argv[2], "rb").read()
        print("%s  %d bytes  magic=%s" % (argv[2], len(d), d[:4].decode()))
        for tag, (off, size) in blocks(d).items():
            print("   %s @0x%-6X %d" % (tag.decode("latin1"), off, size))
        tgt = link_target(d)
        if tgt:
            print("   LINK -> %s" % tgt)
        if d[:4] == b"NCCG":
            _, w, h, bpp = read_nccg(argv[2])
            print("   %dx%d tiles, %dbpp" % (w, h, bpp))
        elif d[:4] == b"NCSC":
            _, w, h = read_ncsc(argv[2])
            print("   %dx%d tiles (%dx%d px)" % (w, h, w * TILE, h * TILE))
    elif argv[1] == "render":
        nccg, nccl, ncsc, out = argv[2], argv[3], argv[4], argv[5]
        w, h, rows = compose(nccg, nccl, ncsc)
        write_png(out, w, h, rows)
        print("rendered %dx%d -> %s" % (w, h, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
