#!/usr/bin/env python3
"""NARC archive reader/writer (Nintendo Archive).

Layout: a 16-byte Nitro header followed by three blocks --
  BTAF  file allocation table: u32 count, then count x (u32 start, u32 end)
        offsets relative to the start of the GMIF image data
  BTNF  filename table (often just a stub, so files are addressed by index)
  GMIF  u32 block size, then the raw file data

Several of the in-game HUD archives under info/subgraphics/ hold plain
Shift-JIS text files alongside their graphics, so unpacking them is how the
lower-screen labels are reached.

    narc.py list    <archive.narc>
    narc.py unpack  <archive.narc> <outdir>
    narc.py replace <archive.narc> <index> <file> <out.narc>
"""

import os
import struct
import sys


def sections(d):
    out, p = {}, 16
    while p < len(d) - 8:
        tag = bytes(d[p:p + 4])
        size = struct.unpack_from("<I", d, p + 4)[0]
        if size == 0:
            break
        out[tag] = (p, size)
        p += size
    return out


class Narc:
    def __init__(self, path):
        self.path = path
        self.data = bytearray(open(path, "rb").read())
        assert self.data[:4] == b"NARC", "not a NARC archive"
        blocks = sections(self.data)
        self.fat_off, _ = blocks[b"BTAF"]
        self.img_off, self.img_size = blocks[b"GMIF"]
        self.count = struct.unpack_from("<I", self.data, self.fat_off + 8)[0]
        self.img_base = self.img_off + 8       # past tag + size

    def entry(self, i):
        start, end = struct.unpack_from("<II", self.data, self.fat_off + 12 + i * 8)
        return start, end

    def file(self, i):
        start, end = self.entry(i)
        return bytes(self.data[self.img_base + start:self.img_base + end])

    def kind(self, i):
        blob = self.file(i)
        if len(blob) >= 4 and blob[:4].isalpha():
            return blob[:4].decode("ascii", "replace")
        return "raw"

    def unpack(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        written = []
        for i in range(self.count):
            blob = self.file(i)
            tag = self.kind(i)
            ext = {"RGCN": "NCGR", "RLCN": "NCLR", "RECN": "NCER",
                   "RNAN": "NANR", "RCSN": "NSCR", "NFTR": "NFTR",
                   # the early background formats keep their magic unreversed
                   "NCCG": "NCCG", "NCCL": "NCCL", "NCSC": "NCSC"}.get(tag, "bin")
            name = os.path.join(outdir, "%03d.%s" % (i, ext))
            with open(name, "wb") as fh:
                fh.write(blob)
            written.append((i, tag, len(blob), name))
        return written

    def replace(self, index, blob, out_path=None):
        """Replace one member with same-or-smaller data.

        Shrinking is allowed: the member's FAT end pointer is moved back and the
        slack zeroed. Following members keep their offsets, so only this entry
        changes. Text members shrink naturally -- ASCII is half the width of
        Shift-JIS -- so English fits without growing the archive.
        """
        start, end = self.entry(index)
        if len(blob) > end - start:
            raise ValueError("member %d: %d bytes exceeds %d"
                             % (index, len(blob), end - start))
        base = self.img_base + start
        self.data[base:base + len(blob)] = blob
        if len(blob) < end - start:
            self.data[base + len(blob):self.img_base + end] = \
                b"\0" * (end - start - len(blob))
            struct.pack_into("<I", self.data, self.fat_off + 12 + index * 8 + 4,
                             start + len(blob))
        if out_path:
            with open(out_path, "wb") as fh:
                fh.write(self.data)
        return bytes(self.data)


    def rebuild(self, overrides):
        """Rebuild the archive with some members replaced, allowing growth.

        `overrides` is {index: new_bytes}. The FAT is recomputed and the image
        block resized, so a member may become larger -- which `replace` cannot
        do. The containing .narc file then grows, and RomBuilder relocates it
        inside the ROM.
        """
        members = [overrides.get(i, self.file(i)) for i in range(self.count)]

        fat = bytearray()
        offset = 0
        for blob in members:
            fat += struct.pack("<II", offset, offset + len(blob))
            offset += len(blob)
            offset = (offset + 3) & ~3              # members stay 4-byte aligned
        fat_block = b"BTAF" + struct.pack("<II", 12 + len(fat), self.count) + bytes(fat)

        # keep the original filename table verbatim
        fnt_off, fnt_size = sections(self.data)[b"BTNF"]
        fnt_block = bytes(self.data[fnt_off:fnt_off + fnt_size])

        image = bytearray()
        for blob in members:
            image += blob
            while len(image) % 4:
                image += b"\0"
        img_block = b"GMIF" + struct.pack("<I", 8 + len(image)) + bytes(image)

        total = 16 + len(fat_block) + len(fnt_block) + len(img_block)
        header = bytearray(self.data[:16])
        struct.pack_into("<I", header, 8, total)
        struct.pack_into("<H", header, 14, 3)        # three blocks
        return bytes(header) + fat_block + fnt_block + img_block


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    narc = Narc(argv[2])
    if argv[1] == "list":
        print("%d members" % narc.count)
        for i in range(narc.count):
            blob = narc.file(i)
            note = ""
            if narc.kind(i) == "raw":
                try:
                    txt = blob[:40].decode("shift_jis").replace("\r\n", " / ")
                    note = "  " + repr(txt)
                except UnicodeDecodeError:
                    pass
            print("  %3d  %-6s %7d%s" % (i, narc.kind(i), len(blob), note))
    elif argv[1] == "unpack":
        for i, tag, size, name in narc.unpack(argv[3]):
            print("  %3d  %-6s %7d -> %s" % (i, tag, size, name))
    elif argv[1] == "replace":
        idx, src, out = int(argv[3]), argv[4], argv[5]
        narc.replace(idx, open(src, "rb").read(), out)
        print("replaced member %d -> %s" % (idx, out))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
