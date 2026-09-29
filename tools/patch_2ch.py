#!/usr/bin/env python3
"""Make a patch for the "2CH" dump of Cross Treasures (Japan).

    patch_2ch.py <clean.nds> <2ch.nds> <translated.nds> <out.xdelta>
    patch_2ch.py <clean.nds> -       <translated.nds> <out.xdelta>

With "-" for the 2CH dump, it is recreated from the clean one (see
make_2ch_dump) -- no copy of it needs to be kept.

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
# the header bytes the 2CH dump has blanked (RSA signature, two hash fields)
BLANKED = ((0x33C, 0x350), (0x378, 0x3A0), (0xF80, 0x1000))


def make_2ch_dump(clean):
    """The 2CH dump, from the clean one: the same bytes with BLANKED zeroed
    (checked: gives SHA-1 87282a19..., user's dump, 2026-09-28)."""
    data = bytearray(clean)
    for s, e in BLANKED:
        data[s:e] = bytes(e - s)
    if hashlib.sha1(data).hexdigest() != TWO_CH_SHA1:
        raise SystemExit("recreated 2CH dump does not match its SHA-1")
    return bytes(data)


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
    clean = open(argv[1], "rb").read()
    built = open(argv[3], "rb").read()
    out = argv[4]
    src_2ch = argv[2]
    if src_2ch == "-":
        two_ch = make_2ch_dump(clean)
        src_2ch = os.path.join(tempfile.mkdtemp(), "2ch.nds")
        with open(src_2ch, "wb") as fh:
            fh.write(two_ch)
    else:
        two_ch = open(src_2ch, "rb").read()
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
    subprocess.run(["xdelta3", "-e", "-9", "-S", "djw", "-f", "-s", src_2ch, tgt, out], check=True)
    back = os.path.join(tmp, "back.nds")
    subprocess.run(["xdelta3", "-d", "-f", "-s", src_2ch, out, back], check=True)
    if open(back, "rb").read() != bytes(target):
        raise SystemExit("round trip failed")
    import zlib
    print("%s: %d header ranges blanked (%s); patched ROM CRC32 %08X SHA-1 %s"
          % (out, len(diff), ", ".join("%#x-%#x" % (s, e - 1) for s, e in diff),
             zlib.crc32(target), hashlib.sha1(target).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
