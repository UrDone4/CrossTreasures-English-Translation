#!/usr/bin/env python3
"""Minimal NDS ROM filesystem reader/writer.

Parses the FNT (filename table) + FAT (file allocation table) of a Nintendo DS
ROM so files can be listed, extracted, and replaced in place.

Usage:
    ndsfs.py list   <rom>
    ndsfs.py info   <rom>
    ndsfs.py dump   <rom> <outdir>
    ndsfs.py get    <rom> <fsPath> <outfile>
"""

import os
import struct
import sys

HDR_ARM9_OFF, HDR_ARM9_LEN = 0x20, 0x2C
HDR_ARM7_OFF, HDR_ARM7_LEN = 0x30, 0x3C
HDR_FNT_OFF, HDR_FNT_LEN = 0x40, 0x44
HDR_FAT_OFF, HDR_FAT_LEN = 0x48, 0x4C
HDR_OVL9_OFF, HDR_OVL9_LEN = 0x50, 0x54
HDR_OVL7_OFF, HDR_OVL7_LEN = 0x58, 0x5C


class Rom:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.data = bytearray(fh.read())
        self.fat_off = self.u32(HDR_FAT_OFF)
        self.fat_len = self.u32(HDR_FAT_LEN)
        self.fnt_off = self.u32(HDR_FNT_OFF)
        self.fnt_len = self.u32(HDR_FNT_LEN)
        self.num_files = self.fat_len // 8
        self._names = None

    # ---- primitive accessors -------------------------------------------
    def u16(self, off):
        return struct.unpack_from("<H", self.data, off)[0]

    def u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def fat_entry(self, fid):
        start, end = struct.unpack_from("<II", self.data, self.fat_off + fid * 8)
        return start, end

    def file_data(self, fid):
        start, end = self.fat_entry(fid)
        return bytes(self.data[start:end])

    # ---- filename table -------------------------------------------------
    def names(self):
        """Return {file_id: '/full/path'} built by walking the FNT."""
        if self._names is not None:
            return self._names
        names = {}

        def walk(dir_id, prefix):
            base = self.fnt_off + (dir_id & 0xFFF) * 8
            sub_off = self.fnt_off + self.u32(base)
            fid = self.u16(base + 4)
            p = sub_off
            while True:
                kind = self.data[p]
                p += 1
                if kind == 0:
                    break
                length = kind & 0x7F
                name = self.data[p:p + length].decode("shift_jis", "replace")
                p += length
                if kind & 0x80:  # subdirectory
                    sub_id = self.u16(p)
                    p += 2
                    walk(sub_id, prefix + "/" + name)
                else:
                    names[fid] = prefix + "/" + name
                    fid += 1

        walk(0xF000, "")
        self._names = names
        return names

    def entries(self):
        """Yield (file_id, path, start, end) for every file, named or not."""
        names = self.names()
        for fid in range(self.num_files):
            start, end = self.fat_entry(fid)
            yield fid, names.get(fid, "/_unnamed/%04d.bin" % fid), start, end

    # ---- mutation -------------------------------------------------------
    def replace(self, fid, blob):
        """Overwrite a file in place. Only safe when len(blob) <= original."""
        start, end = self.fat_entry(fid)
        if len(blob) > end - start:
            raise ValueError(
                "file %d: %d bytes exceeds original %d" % (fid, len(blob), end - start)
            )
        self.data[start:start + len(blob)] = blob
        # shrink: update FAT end pointer, leave slack zeroed
        new_end = start + len(blob)
        if new_end < end:
            self.data[new_end:end] = b"\0" * (end - new_end)
            struct.pack_into("<I", self.data, self.fat_off + fid * 8 + 4, new_end)

    def save(self, path):
        with open(path, "wb") as fh:
            fh.write(self.data)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, rom_path = argv[1], argv[2]
    rom = Rom(rom_path)

    if cmd == "info":
        print("files      : %d" % rom.num_files)
        print("named      : %d" % len(rom.names()))
        print("FNT %08X+%08X  FAT %08X+%08X"
              % (rom.fnt_off, rom.fnt_len, rom.fat_off, rom.fat_len))
    elif cmd == "list":
        for fid, path, start, end in rom.entries():
            print("%5d  %08X  %9d  %s" % (fid, start, end - start, path))
    elif cmd == "dump":
        outdir = argv[3]
        for fid, path, start, end in rom.entries():
            dest = os.path.join(outdir, path.lstrip("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(rom.data[start:end])
        print("extracted %d files to %s" % (rom.num_files, outdir))
    elif cmd == "get":
        want, out = argv[3], argv[4]
        for fid, path, start, end in rom.entries():
            if path == want:
                with open(out, "wb") as fh:
                    fh.write(rom.data[start:end])
                return 0
        print("not found: %s" % want)
        return 1
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
