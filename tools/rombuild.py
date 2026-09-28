#!/usr/bin/env python3
"""Rebuild an NDS ROM with replaced files, allowing files to grow.

In-place overwrite only works when the replacement is no larger than the
original. English text is routinely longer than the Japanese it replaces, so
oversized files are appended to free space past the end of the ROM image and
their FAT entries are repointed. The FNT is untouched, so paths are stable.
"""

import struct
import sys

ALIGN = 0x200                    # NDS files are 512-byte aligned
CAPACITY_BASE = 0x20000          # chip size = 128KB << capacity_byte


def crc16(data, initial=0xFFFF):
    """Nintendo header CRC-16 (reversed polynomial 0xA001)."""
    crc = initial
    for byte in data:
        crc ^= byte
        for _ in range(8):
            carry = crc & 1
            crc >>= 1
            if carry:
                crc ^= 0xA001
    return crc & 0xFFFF


class RomBuilder:
    def __init__(self, rom):
        self.rom = rom
        self.data = bytearray(rom.data)
        self.fat_off = rom.fat_off
        # append point: end of used image, aligned
        self.tail = (rom.u32(0x80) + ALIGN - 1) & ~(ALIGN - 1)
        if self.tail < len(self.data):
            self.tail = max(self.tail, self._highest_file_end())
        self.tail = (self.tail + ALIGN - 1) & ~(ALIGN - 1)
        self.grown = []

    def _highest_file_end(self):
        top = 0
        for fid in range(self.rom.num_files):
            _, end = struct.unpack_from("<II", self.data, self.fat_off + fid * 8)
            top = max(top, end)
        return top

    def set_fat(self, fid, start, end):
        struct.pack_into("<II", self.data, self.fat_off + fid * 8, start, end)

    def replace(self, fid, blob):
        """Replace file `fid`, relocating to the tail if it no longer fits."""
        start, end = struct.unpack_from("<II", self.data, self.fat_off + fid * 8)
        if len(blob) <= end - start:
            self.data[start:start + len(blob)] = blob
            new_end = start + len(blob)
            if new_end < end:
                self.data[new_end:end] = b"\0" * (end - new_end)
            self.set_fat(fid, start, new_end)
            return start

        new_start = self.tail
        if new_start > len(self.data):
            self.data.extend(b"\0" * (new_start - len(self.data)))
        self.data[new_start:new_start + len(blob)] = blob
        new_end = new_start + len(blob)
        self.set_fat(fid, new_start, new_end)
        self.tail = (new_end + ALIGN - 1) & ~(ALIGN - 1)
        if len(self.data) < self.tail:
            self.data.extend(b"\0" * (self.tail - len(self.data)))
        self.grown.append((fid, len(blob) - (end - start)))
        return new_start

    def finalize(self):
        """Update used-size, chip capacity and header CRC."""
        used = self._highest_file_end()
        struct.pack_into("<I", self.data, 0x80, used)

        # capacity byte: smallest power-of-two chip that holds the image
        cap, size = 0, CAPACITY_BASE
        while size < len(self.data):
            size <<= 1
            cap += 1
        self.data[0x14] = cap
        if len(self.data) < size:
            self.data.extend(b"\xff" * (size - len(self.data)))

        struct.pack_into("<H", self.data, 0x15E, crc16(self.data[0:0x15E]))

    def save(self, path):
        self.finalize()
        with open(path, "wb") as fh:
            fh.write(self.data)
        return len(self.data)


def main(argv):
    """Self-test: rebuild with no changes and diff against the source."""
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from ndsfs import Rom

    src = argv[1]
    rom = Rom(src)
    b = RomBuilder(rom)
    out = "/tmp/_rebuild_test.nds"
    b.save(out)
    original = open(src, "rb").read()
    rebuilt = open(out, "rb").read()
    diffs = [i for i in range(min(len(original), len(rebuilt)))
             if original[i] != rebuilt[i]]
    print("source %d bytes, rebuilt %d bytes" % (len(original), len(rebuilt)))
    print("differing bytes: %d %s"
          % (len(diffs), ("at " + ", ".join("%X" % d for d in diffs[:8])) if diffs else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
