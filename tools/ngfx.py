#!/usr/bin/env python3
"""Nitro graphics codec: NCLR palettes + NCGR tilesheets <-> PNG.

Cross Treasures draws its title screen, HUD labels and button prompts as
graphics rather than font text, so those have to be repainted rather than
translated. This converts a tilesheet to a PNG a artist can edit, and converts
it back with the original palette.

    ngfx.py decode <base.NCGR> <base.NCLR> <out.png> [--width N]
    ngfx.py encode <in.png> <base.NCLR> <out.NCGR> --like <orig.NCGR>

PNG I/O is implemented directly against zlib so no imaging library is needed.
"""

import os
import struct
import sys
import zlib

TILE = 8


# --------------------------------------------------------------- PNG I/O --
def write_png(path, width, height, rgba_rows):
    raw = b"".join(b"\0" + bytes(row) for row in rgba_rows)

    def chunk(tag, payload):
        body = tag + payload
        return (struct.pack(">I", len(payload)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def read_png(path):
    """Minimal reader for the 8-bit RGBA, non-interlaced PNGs we emit."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat, width = 8, b"", None
    while pos < len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        tag = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color = struct.unpack_from(">IIBB", payload, 0)
            assert depth == 8 and color == 6, "expected 8-bit RGBA PNG"
        elif tag == b"IDAT":
            idat += payload
        elif tag == b"IEND":
            break
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    rows, prev, p = [], bytearray(stride), 0
    for _ in range(height):
        filt = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        _unfilter(filt, line, prev, 4)
        rows.append(bytes(line))
        prev = line
    return width, height, rows


def _unfilter(filt, line, prev, bpp):
    if filt == 0:
        return
    for i in range(len(line)):
        a = line[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        if filt == 1:
            line[i] = (line[i] + a) & 0xFF
        elif filt == 2:
            line[i] = (line[i] + b) & 0xFF
        elif filt == 3:
            line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
        elif filt == 4:
            pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
            pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            line[i] = (line[i] + pred) & 0xFF


# ------------------------------------------------------- Nitro containers --
def sections(data):
    """{tag: (offset, size)} for the blocks after the 16-byte Nitro header."""
    out, pos = {}, 16
    while pos < len(data) - 8:
        tag = bytes(data[pos:pos + 4])
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if size == 0:
            break
        out[tag] = (pos, size)
        pos += size
    return out


def read_nclr(path):
    """Return a list of RGBA tuples (the first palette in the file)."""
    d = open(path, "rb").read()
    off, size = sections(d)[b"TTLP"]
    bit_depth = struct.unpack_from("<I", d, off + 8)[0]   # 3=4bpp, 4=8bpp
    data_size = struct.unpack_from("<I", d, off + 16)[0]
    data_off = off + 8 + struct.unpack_from("<I", d, off + 20)[0]
    count = min(data_size, size - (data_off - off)) // 2
    palette = []
    for i in range(count):
        v = struct.unpack_from("<H", d, data_off + i * 2)[0]
        r = (v & 0x1F) << 3
        g = ((v >> 5) & 0x1F) << 3
        b = ((v >> 10) & 0x1F) << 3
        palette.append((r | r >> 5, g | g >> 5, b | b >> 5, 255))
    if palette:
        palette[0] = (palette[0][0], palette[0][1], palette[0][2], 0)  # index 0 = clear
    return palette, (8 if bit_depth == 4 else 4)


def read_ncgr(path):
    """Return (indices, width, height, bpp) with tiles unswizzled to a sheet."""
    d = open(path, "rb").read()
    off, size = sections(d)[b"RAHC"]
    tiles_y, tiles_x = struct.unpack_from("<HH", d, off + 8)
    bpp = 4 if struct.unpack_from("<I", d, off + 12)[0] == 3 else 8
    data_size = struct.unpack_from("<I", d, off + 24)[0]
    data_off = off + 8 + struct.unpack_from("<I", d, off + 28)[0]
    blob = d[data_off:data_off + data_size]

    px_per_tile = TILE * TILE
    n_tiles = len(blob) * (2 if bpp == 4 else 1) // px_per_tile
    if tiles_x in (0, 0xFFFF):        # unsized sheet: lay out 32 tiles wide
        tiles_x = 32
        tiles_y = (n_tiles + tiles_x - 1) // tiles_x
    width, height = tiles_x * TILE, tiles_y * TILE

    flat = bytearray(width * height)
    for t in range(min(n_tiles, tiles_x * tiles_y)):
        tx, ty = (t % tiles_x) * TILE, (t // tiles_x) * TILE
        for i in range(px_per_tile):
            if bpp == 4:
                byte = blob[(t * px_per_tile + i) >> 1]
                val = (byte & 0x0F) if i % 2 == 0 else (byte >> 4)
            else:
                val = blob[t * px_per_tile + i]
            flat[(ty + i // TILE) * width + tx + i % TILE] = val
    return flat, width, height, bpp


def write_ncgr_like(orig_path, out_path, indices, width, height):
    """Re-swizzle a sheet of palette indices into a copy of the original NCGR."""
    d = bytearray(open(orig_path, "rb").read())
    off, _ = sections(d)[b"RAHC"]
    bpp = 4 if struct.unpack_from("<I", d, off + 12)[0] == 3 else 8
    data_size = struct.unpack_from("<I", d, off + 24)[0]
    data_off = off + 8 + struct.unpack_from("<I", d, off + 28)[0]

    tiles_x = width // TILE
    px_per_tile = TILE * TILE
    n_tiles = (width // TILE) * (height // TILE)
    blob = bytearray(data_size)
    for t in range(n_tiles):
        tx, ty = (t % tiles_x) * TILE, (t // tiles_x) * TILE
        for i in range(px_per_tile):
            val = indices[(ty + i // TILE) * width + tx + i % TILE]
            if bpp == 4:
                idx = (t * px_per_tile + i) >> 1
                if idx >= len(blob):
                    break
                if i % 2 == 0:
                    blob[idx] = (blob[idx] & 0xF0) | (val & 0x0F)
                else:
                    blob[idx] = (blob[idx] & 0x0F) | ((val & 0x0F) << 4)
            else:
                if t * px_per_tile + i < len(blob):
                    blob[t * px_per_tile + i] = val & 0xFF
    d[data_off:data_off + data_size] = blob
    with open(out_path, "wb") as fh:
        fh.write(d)


# ------------------------------------------------------------- NCER cells --
# OAM shape/size -> (width, height) in pixels.
OBJ_SIZE = {
    (0, 0): (8, 8),   (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
    (1, 0): (16, 8),  (1, 1): (32, 8),  (1, 2): (32, 16), (1, 3): (64, 32),
    (2, 0): (8, 16),  (2, 1): (8, 32),  (2, 2): (16, 32), (2, 3): (32, 64),
}
SHEET_TILES_W = 32          # 2D mapping lays char data out 32 tiles wide


def read_ncer(path):
    """Return a list of cells; each cell is a list of OAM dicts.

    Each OAM records where the sprite sits on screen (x, y) and, because the
    bank uses 2D mapping, the rectangle of the tilesheet it is taken from
    (sheet_x, sheet_y, w, h). That rectangle is what has to be repainted to
    translate a label.
    """
    d = open(path, "rb").read()
    assert d[:4] == b"RECN", "not an NCER file"
    blocks = sections(d)
    off, _ = blocks[b"KBEC"]
    n_cells, bank_type = struct.unpack_from("<HH", d, off + 8)
    data_off = struct.unpack_from("<I", d, off + 12)[0]
    base = off + 8 + data_off
    step = 16 if bank_type == 1 else 8
    oam_base = base + n_cells * step

    cells = []
    for i in range(n_cells):
        n_oam, _attr, oam_off = struct.unpack_from("<HHI", d, base + i * step)
        entries = []
        for k in range(n_oam):
            a0, a1, a2 = struct.unpack_from("<HHH", d, oam_base + oam_off + k * 6)
            y = a0 & 0xFF
            if y >= 128:
                y -= 256
            x = a1 & 0x1FF
            if x >= 256:
                x -= 512
            shape, size = (a0 >> 14) & 3, (a1 >> 14) & 3
            w, h = OBJ_SIZE.get((shape, size), (8, 8))
            tile = a2 & 0x3FF
            entries.append({
                "x": x, "y": y, "w": w, "h": h, "tile": tile,
                "palette": (a2 >> 12) & 0xF,
                "flip_h": bool((a1 >> 12) & 1), "flip_v": bool((a1 >> 13) & 1),
                "sheet_x": (tile % SHEET_TILES_W) * TILE,
                "sheet_y": (tile // SHEET_TILES_W) * TILE,
            })
        cells.append(entries)
    return cells


def render_cell(flat, sheet_w, palette, entries, mapping="1d", bpp=4):
    """Compose one cell into (width, height, rgba_rows).

    Cross Treasures' OBJ banks use 1D mapping: a sprite's tiles are stored
    consecutively from its base tile index, read left-to-right then top-to-
    bottom. (2D mapping, where the sprite is a rectangle cut out of a
    32-tile-wide grid, produces overlapping garbage here -- the give-away is
    OAM source rectangles that overlap each other.)

    Each OAM entry also selects a 16-colour sub-palette. At 4bpp the tile's
    index must be read against that bank, not the first one: banks whose cells
    use bank 1 or 2 decode to noise otherwise.
    """
    if not entries:
        return 0, 0, []
    min_x = min(e["x"] for e in entries)
    min_y = min(e["y"] for e in entries)
    w = max(e["x"] + e["w"] for e in entries) - min_x
    h = max(e["y"] + e["h"] for e in entries) - min_y
    tiles_w = sheet_w // TILE
    canvas = [[(0, 0, 0, 0)] * w for _ in range(h)]
    for e in entries:
        span = e["w"] // TILE
        base = e["palette"] * 16 if bpp == 4 else 0
        for row in range(e["h"]):
            for col in range(e["w"]):
                sc = e["w"] - 1 - col if e["flip_h"] else col
                sr = e["h"] - 1 - row if e["flip_v"] else row
                if mapping == "1d":
                    t = e["tile"] + (sr // TILE) * span + (sc // TILE)
                    sx = (t % tiles_w) * TILE + sc % TILE
                    sy = (t // tiles_w) * TILE + sr % TILE
                else:
                    sx, sy = e["sheet_x"] + sc, e["sheet_y"] + sr
                pos = sy * sheet_w + sx
                if pos >= len(flat):
                    continue
                idx = flat[pos]
                if idx == 0:
                    continue
                dx, dy = e["x"] - min_x + col, e["y"] - min_y + row
                if 0 <= dx < w and 0 <= dy < h:
                    canvas[dy][dx] = palette[(base + idx) % len(palette)]
    rows = [bytearray(b"".join(bytes(px) for px in line)) for line in canvas]
    return w, h, rows


def cell_tiles(entries):
    """Tile indices used by a cell, as {oam_index: [tile, ...]}."""
    out = {}
    for i, e in enumerate(entries):
        span, rows = e["w"] // TILE, e["h"] // TILE
        out[i] = [e["tile"] + r * span + c for r in range(rows) for c in range(span)]
    return out


def decode(ncgr, nclr, out_png):
    palette, _ = read_nclr(nclr)
    flat, w, h, bpp = read_ncgr(ncgr)
    if not palette:
        palette = [(0, 0, 0, 0)] + [(255, 255, 255, 255)] * 255
    while len(palette) < (16 if bpp == 4 else 256):
        palette.append((255, 0, 255, 255))
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            row += bytes(palette[flat[y * w + x] % len(palette)])
        rows.append(row)
    write_png(out_png, w, h, rows)
    return w, h, bpp


def encode(in_png, nclr, orig_ncgr, out_ncgr):
    palette, _ = read_nclr(nclr)
    lookup = {}
    for i, c in enumerate(palette):
        lookup.setdefault((c[0], c[1], c[2], c[3] if i == 0 else 255), i)
    w, h, rows = read_png(in_png)
    flat = bytearray(w * h)
    unmatched = 0
    for y in range(h):
        row = rows[y]
        for x in range(w):
            r, g, b, a = row[x * 4:x * 4 + 4]
            if a < 128:
                flat[y * w + x] = 0
                continue
            key = (r, g, b, 255)
            if key in lookup:
                flat[y * w + x] = lookup[key]
            else:                       # nearest colour in the palette
                unmatched += 1
                best, bd = 0, 1 << 30
                for i, c in enumerate(palette):
                    dist = (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2
                    if dist < bd:
                        best, bd = i, dist
                flat[y * w + x] = best
    write_ncgr_like(orig_ncgr, out_ncgr, flat, w, h)
    return unmatched


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[1] == "decode":
        w, h, bpp = decode(argv[2], argv[3], argv[4])
        print("decoded %dx%d %dbpp -> %s" % (w, h, bpp, argv[4]))
    elif argv[1] == "encode":
        if "--like" not in argv:
            print("encode requires --like <orig.NCGR>")
            return 1
        orig = argv[argv.index("--like") + 1]
        n = encode(argv[2], argv[3], orig, argv[4])
        print("encoded -> %s (%d pixels colour-matched)" % (argv[4], n))
    elif argv[1] == "cells":
        ncgr, nclr, ncer, outdir = argv[2], argv[3], argv[4], argv[5]
        palette, _ = read_nclr(nclr)
        flat, sw, sh, _bpp = read_ncgr(ncgr)
        while len(palette) < 256:
            palette.append((255, 0, 255, 255))
        os.makedirs(outdir, exist_ok=True)
        for i, entries in enumerate(read_ncer(ncer)):
            w, h, rows = render_cell(flat, sw, palette, entries)
            if not w:
                print("  cell %d: empty" % i)
                continue
            write_png(os.path.join(outdir, "cell%02d.png" % i), w, h, rows)
            rects = ", ".join("(%d,%d %dx%d)" % (e["sheet_x"], e["sheet_y"],
                                                 e["w"], e["h"]) for e in entries)
            print("  cell %d: %dx%d  %d OAM  rects: %s" % (i, w, h, len(entries), rects))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


def ncer_raw(data):
    """[[ (a0, a1, a2), ... ] per cell] -- the raw OAM words of an NCER."""
    blocks = sections(data)
    off, _ = blocks[b"KBEC"]
    n_cells, bank_type = struct.unpack_from("<HH", data, off + 8)
    base = off + 8 + struct.unpack_from("<I", data, off + 12)[0]
    step = 16 if bank_type == 1 else 8
    oam_base = base + n_cells * step
    out = []
    for i in range(n_cells):
        n_oam, _attr, oam_off = struct.unpack_from("<HHI", data, base + i * step)
        out.append([struct.unpack_from("<HHH", data, oam_base + oam_off + k * 6)
                    for k in range(n_oam)])
    return out


def oam_words(template, x, y, w, h, tile):
    """OAM words for a new entry: the template's other bits (palette,
    priority, mode) kept, position / shape / size / tile replaced."""
    shape, size = next(k for k, v in OBJ_SIZE.items() if v == (w, h))
    a0, a1, a2 = template
    a0 = (a0 & ~(0xFF | 0xC000)) | (y & 0xFF) | (shape << 14)
    a1 = (a1 & ~(0x1FF | 0xC000 | 0x3000)) | (x & 0x1FF) | (size << 14)
    a2 = (a2 & ~0x3FF) | (tile & 0x3FF)
    return (a0, a1, a2)


def rebuild_ncer(data, cells_raw, new_attrs=()):
    """A copy of NCER `data` with its OAM lists replaced by `cells_raw`.
    The cell table, OAM data, KBEC size and file size are rewritten; the
    header fields and the LBAL / TXEU blocks are kept. Cells past the
    original count are new: `new_attrs` gives each one's attribute word
    (bank type 0 only -- its 8-byte record has no bounding box)."""
    data = bytes(data)
    blocks = sections(data)
    off, ksize = blocks[b"KBEC"]
    n_cells, bank_type = struct.unpack_from("<HH", data, off + 8)
    assert len(cells_raw) == n_cells + len(new_attrs)
    assert not new_attrs or bank_type == 0
    base = off + 8 + struct.unpack_from("<I", data, off + 12)[0]
    step = 16 if bank_type == 1 else 8
    table, oam = bytearray(), bytearray()
    for i, entries in enumerate(cells_raw):
        if i >= n_cells:
            rec = bytearray(struct.pack("<HHI", 0, new_attrs[i - n_cells], 0))
        else:
            rec = bytearray(data[base + i * step:base + (i + 1) * step])
        struct.pack_into("<HHI", rec, 0, len(entries), struct.unpack_from("<H", rec, 2)[0],
                         len(oam))
        table += rec
        for a in entries:
            oam += struct.pack("<HHH", *a)
    kbec = bytearray(data[off:base]) + table + oam
    while len(kbec) % 4:
        kbec += b"\0"
    struct.pack_into("<I", kbec, 4, len(kbec))
    struct.pack_into("<H", kbec, 8, len(cells_raw))
    rest = data[off + ksize:]
    out = bytearray(data[:off]) + kbec + rest
    struct.pack_into("<I", out, 8, len(out))
    return bytes(out)
