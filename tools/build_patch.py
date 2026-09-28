#!/usr/bin/env python3
"""Build the patched ROM: reinsert translated UI text into a copy of the ROM.

    build_patch.py <source.nds> <output.nds>
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ndsfs import Rom              # noqa: E402
from rombuild import RomBuilder    # noqa: E402
import arm9text                    # noqa: E402
import uitext                      # noqa: E402
import scripttext                  # noqa: E402
import datatext                    # noqa: E402
import narctext                    # noqa: E402

BASE = os.path.dirname(HERE)
ROOT = os.path.join(BASE, "extracted")
UI_TSV = os.path.join(BASE, "work", "ui_text.tsv")
SCRIPT_TSV = os.path.join(BASE, "work", "script_text.tsv")
DATA_TSV = os.path.join(BASE, "work", "data_text.tsv")
NARC_TSV = os.path.join(BASE, "work", "narc_text.tsv")
# Overridable so a review build can read pre-built graphics from elsewhere
# without replacing the standing work/ outputs.
GFX_DIR = os.environ.get("CTRES_GFX_DIR", os.path.join(BASE, "work", "gfx_out"))
BG_DIR = os.environ.get("CTRES_BG_DIR", os.path.join(BASE, "work", "bg_out"))


def main(argv):
    src, dst = argv[1], argv[2]
    rom = Rom(src)
    by_path = {path: fid for fid, path, _, _ in rom.entries()}
    builder = RomBuilder(rom)

    # (rebuilt bytes for a file) keyed by ROM-relative path
    pending = {}

    ui = uitext.load_translations(UI_TSV)
    for rel in sorted({r for r, _ in ui}):
        blob = uitext.apply_to_file(ROOT, rel, ui)
        if blob is not None:
            pending[rel] = blob

    # speaker-name plate list: line N = name N (English from work/name_list.py)
    sys.path.insert(0, os.path.join(BASE, "work"))
    import name_list
    import enemy_names
    monsters = {}
    for _d in (enemy_names.MONSTERS, enemy_names.NAMES, enemy_names.OBJECTS):
        monsters.update(_d)
    CRLF = chr(13) + chr(10)
    nl_rel = "script/name_list.txt"
    with open(os.path.join(ROOT, nl_rel), "rb") as fh:
        nl_lines = fh.read().decode("shift_jis").split(CRLF)
    for i, jp in enumerate(nl_lines):
        en = name_list.HAND.get(i) or (monsters.get(jp) if i > 50 else None)
        if en:
            nl_lines[i] = en
    pending[nl_rel] = CRLF.join(nl_lines).encode("shift_jis")

    # world names: 10th column of bg/BGList.csv (English from work/world_names.py)
    import world_names
    bg_rel = "bg/BGList.csv"
    with open(os.path.join(ROOT, bg_rel), "rb") as fh:
        bg_lines = fh.read().decode("shift_jis").split(CRLF)
    for i, ln in enumerate(bg_lines):
        cols = ln.split(",")
        if not ln.startswith("#") and len(cols) > 9:
            en = world_names.WORLDS.get(cols[9].strip())
            if en:
                cols[9] = en
                bg_lines[i] = ",".join(cols)
    pending[bg_rel] = CRLF.join(bg_lines).encode("shift_jis")

    # ending monster viewer (overlay 6): column 2 is the monster's name, from
    # the same tables as the speaker plates; かめんのまどうし is the masked
    # dungeon lord, "Masked Sorcerer" (his description: a masked sorcerer)
    mv_rel = "general/monster_u_viewer.csv"
    with open(os.path.join(ROOT, mv_rel), "rb") as fh:
        mv_lines = fh.read().decode("shift_jis").split(CRLF)
    mv_extra = {"かめんのまどうし": "Masked Sorcerer"}
    for i, ln in enumerate(mv_lines):
        cols = ln.split(",")
        if i and len(cols) > 2:
            en = monsters.get(cols[1]) or mv_extra.get(cols[1])
            if en:
                cols[1] = en
                mv_lines[i] = ",".join(cols)
    pending[mv_rel] = CRLF.join(mv_lines).encode("shift_jis")

    # Random! names: key presses on the name keyboard (see keyboard_names.py)
    import keyboard_names
    kb_rel, kb_blob = keyboard_names.build()
    pending[kb_rel] = kb_blob

    script_rows = 0
    if os.path.exists(SCRIPT_TSV):
        sc = scripttext.load(SCRIPT_TSV)
        script_rows = len(sc)
        for rel in sorted({r for r, _ in sc}):
            blob = scripttext.apply_to_file(rel, sc)
            if blob is not None:
                pending[rel] = blob

    data_rows = 0
    if os.path.exists(DATA_TSV):
        dt = datatext.load(DATA_TSV)
        data_rows = len(dt)
        for rel, blob in datatext.apply_all(dt).items():
            pending[rel] = blob

    narc_rows = 0
    if os.path.exists(NARC_TSV):
        nt = narctext.load(NARC_TSV)
        narc_rows = len(nt)
        for rel, blob in narctext.apply_all(nt).items():
            pending[rel] = blob

    # Repainted background layers: rebuilt .narc archives (these may have grown,
    # so the ROM file gets relocated). If an archive was also text-patched above,
    # one of the two edits would be lost -- so that is caught loudly.
    bg_files = 0
    # bg_labels records which archives it built on top of the text-patched
    # bytes; for those the BG copy is a superset and supersedes the text one.
    text_sourced = set()
    marker = os.path.join(BG_DIR, "_text_sourced.txt")
    if os.path.exists(marker):
        text_sourced = {ln.strip() for ln in open(marker) if ln.strip()}
    if os.path.isdir(BG_DIR):
        for fname in sorted(os.listdir(BG_DIR)):
            if not fname.endswith(".narc"):
                continue
            rel = os.path.join("info", "subgraphics", fname)
            if rel in pending and fname not in text_sourced:
                print("  !! CONFLICT: %s was text-patched and BG-patched, and "
                      "the BG copy was NOT built from the text-patched source; "
                      "applying it would discard the text edit" % rel)
                continue
            with open(os.path.join(BG_DIR, fname), "rb") as fh:
                pending[rel] = fh.read()
            bg_files += 1

    # Repainted loose background layers (info/title/*.ncg etc.): work/bg_out/loose
    # mirrors the ROM paths of every file bg_labels changed.
    loose_dir = os.path.join(BG_DIR, "loose")
    loose_files = 0
    if os.path.isdir(loose_dir):
        for dirpath, _dn, fns in os.walk(loose_dir):
            for fname in sorted(fns):
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, loose_dir)
                with open(full, "rb") as fh:
                    pending[rel] = fh.read()
                loose_files += 1

    # Boss-intro nameplates (info/bossname, tools/bossname.py)
    import bossname
    for bn_rel, bn_blob in bossname.build().items():
        pending[bn_rel] = bn_blob

    # English secret passwords (tools/passwords.py)
    import passwords
    pw_rel, pw_blob = passwords.build()
    pending[pw_rel] = pw_blob

    # The title's "START to begin!" pill, baked into the 8bpp logo layer
    import title_logo
    tl_rel, tl_blob = title_logo.build()
    pending[tl_rel] = tl_blob

    # Repainted sprite banks: any .NCGR in work/gfx_out/ replaces the bank of
    # the same name under info/title/.
    gfx_files = 0
    if os.path.isdir(GFX_DIR):
        found = [(fn, os.path.join(GFX_DIR, fn), os.path.join("info", "title", fn))
                 for fn in sorted(os.listdir(GFX_DIR))]
        # a subdirectory (chr_make/...) maps to info/<subdir>/
        for sub in sorted(fn for fn in os.listdir(GFX_DIR)
                          if os.path.isdir(os.path.join(GFX_DIR, fn))):
            found += [(fn, os.path.join(GFX_DIR, sub, fn),
                       os.path.join("info", sub, fn))
                      for fn in sorted(os.listdir(os.path.join(GFX_DIR, sub)))]
        for fname, path, rel in found:
            if not fname.endswith((".NCGR", ".NCER")):
                continue
            with open(path, "rb") as fh:
                pending[rel] = fh.read()
            gfx_files += 1

    relocated = 0
    for rel, blob in sorted(pending.items()):
        fid = by_path.get("/" + rel.replace(os.sep, "/"))
        if fid is None:
            print("  !! no ROM entry for %s" % rel)
            continue
        before = len(builder.grown)
        builder.replace(fid, blob)
        if len(builder.grown) > before:
            relocated += 1

    arm9 = arm9text.apply(builder.data)
    # built-in fake friends (tools/fake_friends_rom.py, work/fake_friends.py):
    # in the main build; CTRES_NO_FRIENDS=1 builds the no-friends variant
    if os.environ.get("CTRES_NO_FRIENDS"):
        print("built-in friends: OFF (CTRES_NO_FRIENDS)")
    else:
        import fake_friends_rom
        arm9 += fake_friends_rom.apply(builder.data)
        print("built-in friends: on")
    patch_banner(builder.data)
    size = builder.save(dst)
    print("UI %d | script %d | tables %d | narc-text %d | sprites %d | bg %d"
          % (len(ui), script_rows, data_rows, narc_rows, gfx_files, bg_files))
    print("patched %d files (%d relocated for growth) + %d ARM9 strings"
          % (len(pending), relocated, arm9))
    print("wrote %s (%d bytes)" % (dst, size))
    return 0


BANNER_TITLE = "Cross Treasures\nSQUARE ENIX"


def patch_banner(data):
    """The banner title shown by the DS menu / flashcart file info: all six
    language slots (UTF-16, 0x100 bytes each at banner+0x240) say
    クロストレジャーズ / SQUARE ENIX. Rewritten in English; the version-1 CRC16
    over banner[0x20:0x840] (stored at banner+2) is recomputed."""
    from rombuild import crc16
    base = struct.unpack_from("<I", data, 0x68)[0]
    assert struct.unpack_from("<H", data, base)[0] == 1, "banner version"
    blob = BANNER_TITLE.encode("utf-16-le")
    for k in range(6):
        off = base + 0x240 + k * 0x100
        data[off:off + 0x100] = blob + bytes(0x100 - len(blob))
    struct.pack_into("<H", data, base + 2, crc16(bytes(data[base + 0x20:base + 0x840])))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
