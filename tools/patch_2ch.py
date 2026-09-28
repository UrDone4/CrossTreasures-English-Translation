#!/usr/bin/env python3
"""Make a patch for the "2CH" dump of Cross Treasures (Japan).

    patch_2ch.py <clean.nds> <2ch.nds> <translated.nds> <out.xdelta>

The 2CH dump (SHA-1 87282a19f8e382b86b5a71714dc9d8dbc7a1126c, the one the
earlier partial translation patched) is the same game as the verified dump
(SHA-1 4048b18f...) with 188 header bytes blanked: the header's RSA signature
(0xF80-0xFFF) and two hash fields (0x33C, 0x378). Our normal patches are
built against the clean dump, so they refuse the 2CH one.

This builds the translated ROM as the 2CH dump would have it -- identical to
<translated.nds> except those header bytes, taken from the 2CH dump (zeros) --
and encodes a patch from the 2CH dump to it, then checks the round trip. The
patch therefore never carries Nintendo's signature bytes, and the game data is
byte for byte the normal release. Needs xdelta3.
"""

import hashlib
import os
import subprocess
import sys
import tempfile

CLEAN_SHA1 = "4048b18f3e589e70e58391927c82ca87117d1337"
TWO_CH_SHA1 = "87282a19f8e382b86b5a71714dc9d8dbc7a1126c"
HEADER_END = 0x1000     # every difference must lie in the ROM header


def runs(a, b):
    out, start = [], None
    for i in range(len(a)):
        if a[i] != b[i]:
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(a)))
    return out


def main(argv):
    if len(argv) != 5:
        print(__doc__)
        return 1
    clean, two_ch, built = (open(p, "rb").read() for p in argv[1:4])
    out = argv[4]
    for name, data, want in (("clean", clean, CLEAN_SHA1), ("2CH", two_ch, TWO_CH_SHA1)):
        got = hashlib.sha1(data).hexdigest()
        if got != want:
            raise SystemExit("%s dump: SHA-1 %s, expected %s" % (name, got, want))
    diff = runs(clean[:HEADER_END], two_ch[:HEADER_END])
    if clean[HEADER_END:] != two_ch[HEADER_END:] or len(clean) != len(built):
        raise SystemExit("the 2CH dump differs outside the header -- not the known 2CH dump")
    target = bytearray(built)
    for s, e in diff:
        target[s:e] = two_ch[s:e]
    tmp = tempfile.mkdtemp()
    tgt = os.path.join(tmp, "target.nds")
    with open(tgt, "wb") as fh:
        fh.write(target)
    subprocess.run(["xdelta3", "-e", "-9", "-S", "djw", "-f", "-s", argv[2], tgt, out], check=True)
    back = os.path.join(tmp, "back.nds")
    subprocess.run(["xdelta3", "-d", "-f", "-s", argv[2], out, back], check=True)
    if open(back, "rb").read() != bytes(target):
        raise SystemExit("round trip failed")
    import zlib
    print("%s: %d header ranges blanked (%s); patched ROM CRC32 %08X SHA-1 %s"
          % (out, len(diff), ", ".join("%#x-%#x" % (s, e - 1) for s, e in diff),
             zlib.crc32(target), hashlib.sha1(target).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
