#!/usr/bin/env python3
"""Repaint Japanese labels in NCCG/NCSC background layers as English.

Pipeline, in this order for a reason:

 1. Clear the Japanese glyphs, but only in cells that already own their tile.
 2. Work out exactly which cells the English text will occupy, and protect them.
 3. Deduplicate every *other* tile that is now byte-identical (the cleared
    glyph tiles collapse into one flat background) to harvest a pool of free
    tile slots.
 4. Spend that pool giving any still-shared text cell a private tile.
 5. Clear again and draw.

Why not simply grow the graphic: this game uploads only the original tile count
to VRAM, so cells pointing past it render whatever else occupies that VRAM --
in-game that showed up as coloured blocks and other layers' animation bleeding
through the HUD. Everything here stays within the original tile budget, so the
NCCG keeps its exact size and the archive is patched in place.

Colours are RGB, not palette indices: cells in one region may use different
palette banks, so the index is resolved per cell.

    bg_labels.py preview           render each patched layer to work/gfx/bg_en/
    bg_labels.py apply <outdir>    write patched .narc / .ncg files to outdir
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bgtext import BgLayer, load_font  # noqa: E402
from narc import Narc  # noqa: E402
import narctext  # noqa: E402

BASE = os.path.dirname(HERE)
ROOT = os.path.join(BASE, "extracted")
NARC_TSV = os.path.join(BASE, "work", "narc_text.tsv")

_TEXT_PATCHED = None


def text_patched_archives():
    """{archive_rel: bytes} for archives whose embedded text is translated.

    Some archives hold both a text member and BG layers -- madu_topmenu.narc is
    one. Repainting must start from the text-patched bytes, or inserting the
    result would silently revert the translated text.
    """
    global _TEXT_PATCHED
    if _TEXT_PATCHED is None:
        _TEXT_PATCHED = {}
        if os.path.exists(NARC_TSV):
            _TEXT_PATCHED = narctext.apply_all(narctext.load(NARC_TSV))
    return _TEXT_PATCHED


# Colours sampled from the original art.
BAR_GREEN = (82, 156, 82)
WHITE = (255, 255, 255)
CREAM = (255, 255, 231)
CREAM2 = (255, 255, 222)
PINK = (231, 156, 189)
BLUE = (90, 165, 255)
GREEN = (132, 222, 115)
BROWN = (132, 82, 8)

def _repalette(layer, cells, bank, want):
    """Move 8x8 cells to another palette bank, keeping every pixel's colour
    (nearest in the new bank); pixels whose colour is a key of `want` become
    its value. For lettering that crosses into a cell whose bank lacks the ink
    (the nearest colour there is a different hue). Only for cells that own
    their tile, so nothing else on screen changes."""
    for cx, cy in cells:
        ci = cy * layer.sw + cx
        if not layer.exclusive(ci):
            print("    !! cell %d,%d shares its tile -- palette left as is" % (cx, cy))
            continue
        px = {}
        for y in range(cy * 8, cy * 8 + 8):
            for x in range(cx * 8, cx * 8 + 8):
                c = layer.rgb_at(x, y)
                px[(x, y)] = None if c is None else want.get(tuple(c), tuple(c))
        layer.cells[ci]["palette"] = bank
        for (x, y), c in px.items():
            layer.put(x, y, 0 if c is None else layer.nearest(bank, c))


def _paint_home(layer, font):
    out = paint_layer(layer, HOME_LABELS, font)
    # "Mana Potion", right-aligned, starts at x 190: its M crosses cell 23,10,
    # whose palette (bank 0) has no blue, so it came out green. Bank 3 (its
    # neighbours') has the blue and the cream.
    green = tuple(layer.palette[layer.nearest(0, BLUE)][:3])
    _repalette(layer, [(23, 10)], 3, {green: BLUE})
    # the Japanese Life Potion label's lowest row is y 55, one below its box
    # (which cannot grow: 40 is the border, and 56 moves the text down); its
    # faint pixels showed between the label and the pill (user, melonDS,
    # 2026-09-28). Row 55 is plain cream there, so they go to cream.
    for x in range(168, 248):
        ci = (55 // 8) * layer.sw + x // 8
        if layer.rgb_at(x, 55) != CREAM and layer.exclusive(ci):
            layer.put(x, 55, layer.nearest(layer.cells[ci]["palette"], CREAM))
    # left of "Gold": two blank cells (25,15) and (27,16) use a blank tile in
    # bank 3, whose nearest cream is (255,255,231) against the panel's
    # (255,255,222) -- two faint squares once the Japanese beside them was
    # gone (seen in the README comparison shot, 2026-09-28). Point them at
    # their neighbours' plain panel tile.
    plain = layer.cells[15 * layer.sw + 24]
    for cx, cy in ((25, 15), (27, 16)):
        c = layer.cells[cy * layer.sw + cx]
        if all(layer.rgb_at(x, y) == layer.rgb_at(cx * 8, cy * 8)
               for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 8, cx * 8 + 8)):
            c.update(tile=plain["tile"], palette=plain["palette"],
                     flip_h=plain["flip_h"], flip_v=plain["flip_v"])
    return out


LAYERS = [
    {
        "archive": "info/subgraphics/madu_home.narc",
        "members": {"nccg": 0, "nccl": 1, "ncsc": 2},
        "note": "madi_is_map_bg -- the island HUD on the lower screen",
        "paint": _paint_home,
        "labels": [
            # from row 41: rows 39-40 are the panel's dark green border (the
            # box from 40 painted over its lower row -- seen 2026-09-26).
            # Right-aligned, as the Japanese: all three end at x 246 (user,
            # 2026-09-27: centred, they started and ended at different places)
            ((168, 41, 248, 55),   "Life Potion",  CREAM,     PINK,  1, "right"),
            ((160, 80, 248, 96),   "Mana Potion", CREAM,     BLUE,  1, "right"),
            ((200, 120, 248, 136), "Gold",         CREAM2,    GREEN, 1, "right"),
            # the white pill beside START is x 200-244, y 173-187: the old box ran over
            # its top and right edges
            ((206, 174, 242, 186), "Menu",         WHITE,     BROWN, 1),
        ],
    },
]
HOME_LABELS = LAYERS[0]["labels"]

# Screen-header words in the original's circled-letter style (tools/banner_circles.py).
import banner_circles as _banner  # noqa: E402


def _banner_spec(archive, members, note, **kw):
    return {"archive": archive, "members": members, "note": note,
            "paint": (lambda layer, font, _kw=kw: _banner.paint(layer, **_kw)),
            "labels": []}


LAYERS.append(_banner_spec(
    "info/subgraphics/madu_home.narc", {"nccg": 0, "nccl": 1, "ncsc": 2},
    "Island header (circled letters)",
    word="ISLAND", x0=62, x1=194, style="green", d=23, pitch=21, caps=_banner.CAPS))

# madu_ba_top_bg -- the lower-screen HUD inside a dungeon. Byte-identical
# across the four class archives, and again across their four "_c"
# (download-play) copies, so one design is applied eight times. Only the member
# indices differ between the two variants.
BATTLE_LABELS = [
    ((205, 174, 243, 186), "Menu",   WHITE,     (123, 66, 0), 1),
]
# the "Battle" header is the circled-letter banner (six letters between the
# Skill 1 / Skill 2 pills, which are OBJ sprites at x ~4-69 and ~186-250)
_BATTLE_BANNER = dict(word="BATTLE", x0=70, x1=186, style="green", d=21,
                      pitch=19, caps=_banner.CAPS_S)
for _cls in ("magic", "priest", "soldier", "thief"):
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s.narc" % _cls,
        "members": {"nccg": 13, "nccl": 14, "ncsc": 15},
        "note": "madu_ba_top_bg -- dungeon HUD (%s)" % _cls,
        "labels": BATTLE_LABELS,
    })
    LAYERS.append(_banner_spec(
        "info/subgraphics/madu_battle_%s.narc" % _cls,
        {"nccg": 13, "nccl": 14, "ncsc": 15},
        "Battle header (%s)" % _cls, **_BATTLE_BANNER))
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s_c.narc" % _cls,
        "members": {"nccg": 4, "nccl": 5, "ncsc": 6},
        "note": "madu_ba_top_bg -- dungeon HUD (%s, download play)" % _cls,
        # no START/Menu pill on the download-play HUD (that corner is plain
        # strip): painting "Menu" there added a white box the original lacks;
        # its only label is the header banner
        "paint": (lambda layer, font: _banner.paint(layer, **_BATTLE_BANNER)),
        "labels": [],
    })

# Battle-screen triangles (Attack / Power Attack / Life & Mana Potion and the two skill
# pages), painted by tools/battle_panels.py. Members 0-2 / 3-5 / 6-8 are the three pages
# in the normal archives; the download-play "_c" archives keep page 0 at 7-9.
from battle_panels import paint_battle, PAGES as _BP_PAGES  # noqa: E402


def PAGES_NAME(cls, page, btn):
    return _BP_PAGES[cls][page][btn]

for _cls in ("magic", "priest", "soldier", "thief"):
    for _page in range(3):
        LAYERS.append({
            "archive": "info/subgraphics/madu_battle_%s.narc" % _cls,
            "members": {"nccg": _page * 3, "nccl": _page * 3 + 1, "ncsc": _page * 3 + 2},
            "note": "battle triangles (%s, page %d)" % (_cls, _page),
            "paint": (lambda layer, font, _c=_cls, _p=_page: paint_battle(layer, font, _c, _p)),
            "labels": [],
        })
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s_c.narc" % _cls,
        "members": {"nccg": 7, "nccl": 8, "ncsc": 9},
        "note": "battle triangles (%s, download play)" % _cls,
        "paint": (lambda layer, font, _c=_cls: paint_battle(layer, font, _c, 0)),
        "labels": [],
    })

# The download-play archives' extra layers: one skill triangle each (spread and
# assembled), pixel for pixel the same art as that skill on the normal pages --
# so the user's redraw for that page applies. (member base, page, button)
_BATTLE_C_EXTRA = {"magic": (13, 2, "X"), "priest": (10, 1, "X"),
                   "soldier": (13, 2, "A"), "thief": (13, 2, "Y")}
for _cls, (_m, _page, _btn) in _BATTLE_C_EXTRA.items():
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s_c.narc" % _cls,
        "members": {"nccg": _m, "nccl": _m + 1, "ncsc": _m + 2},
        "note": "battle triangle (%s, download play, %s)" % (_cls, PAGES_NAME(_cls, _page, _btn)),
        "paint": (lambda layer, font, _c=_cls, _p=_page, _b=_btn:
                  paint_battle(layer, font, _c, _p, single=_b)),
        "labels": [],
    })

# The L / R skill-page pills are an OBJ bank in each battle archive (tools/battle_obj.py).
import battle_obj as _battle_obj  # noqa: E402

for _cls in ("magic", "priest", "soldier", "thief"):
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s.narc" % _cls,
        "note": "battle skill-page pills (%s)" % _cls,
        "obj": (lambda narc, workdir: _battle_obj.paint(narc, workdir)),
    })
    LAYERS.append({
        "archive": "info/subgraphics/madu_battle_%s_c.narc" % _cls,
        "note": "battle skill-page pills (%s, download play)" % _cls,
        "obj": (lambda narc, workdir: _battle_obj.paint(narc, workdir,
                                                        _battle_obj.MEMBERS_C)),
    })

# Shop title pills (Buy / Sell / Exchange / Needed): OBJ bank in madu_shop.narc.
import shop_obj as _shop_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_shop.narc",
    "note": "shop title pills",
    "obj": (lambda narc, workdir: _shop_obj.paint(narc, workdir)),
})

# The in-game main menu. This archive also holds the description text member,
# so build_layer sources it from the text-patched bytes.
MENU_BROWN = (123, 74, 0)

# The nine items sit on white buttons in a strict 3x3 grid (buttons at
# x 8-82 / 91-165 / 174-248, y 45-69 / 78-102 / 111-135). The boxes below are
# centred on each button and sized to cover the widest Japanese label
# (メダリオン reaches x16-77), while staying clear of the rounded border.
_MENU_ITEMS = [
    "Map", "Status", "Equipment",
    "Skills", "Items", "Jump",
    "Medals", "Memos", "Quest",
]
_menu_labels = []
for _r, (_y0, _y1) in enumerate(((50, 66), (82, 98), (115, 131))):
    # column 1 is 10-80 (same centre as 12-78): ン of メダリオン reaches x78
    for _c, (_x0, _x1) in enumerate(((10, 80), (95, 161), (178, 244))):
        _menu_labels.append(((_x0, _y0, _x1, _y1),
                             _MENU_ITEMS[_r * 3 + _c], WHITE, MENU_BROWN, 1))

LAYERS.append({
    "archive": "info/subgraphics/madu_topmenu.narc",
    "members": {"nccg": 0, "nccl": 1, "ncsc": 2},
    "note": "madu_menu_top2_bg -- the nine main-menu item buttons",
    "labels": _menu_labels,
})
LAYERS.append({
    "archive": "info/subgraphics/madu_topmenu.narc",
    "members": {"nccg": 3, "nccl": 4, "ncsc": 5},
    "note": "madu_menu_top_bg -- menu frame header (hint bar: hint_bars.py)",
    "paint": (lambda layer, font: _banner.paint(
        layer, word="MENU", x0=60, x1=196, style="brown", d=25, pitch=23,
        caps=_banner.CAPS)),
    "labels": [],
})

# ---------------------------------------------------------------- Strength --
# The six status pages. Geometry was measured from the ink bands rather than
# eyeballed: the "To Next Level" row is the one *below* the EXP progress bar,
# whose dark border also shows up as ink and must not be painted over.
FIELD = (255, 255, 231)     # pale field inside a label box
BAR = (255, 214, 115)       # the EXP bar's surround
HINT = (255, 239, 181)      # the bottom hint strip
STAT_INK = (123, 74, 0)
TAB_ORANGE = (255, 132, 0)   # the caption bar above the stat table

_STATS = ("Stamina", "Spirit", "Power", "Magic", "Speed")
_STAT_ROWS = ((64, 78), (85, 99), (106, 120), (127, 141), (148, 162))


def _stat_labels(x0, x1):
    return [((x0, y0, x1, y1), name, FIELD, STAT_INK, 1)
            for name, (y0, y1) in zip(_STATS, _STAT_ROWS)]


LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 13, "nccl": 14, "ncsc": 15},
    "note": "madu_menu_pow1_bg -- Strength: style, class, next level",
    "labels": [
        ((36, 70, 86, 82),   "Style",         FIELD, STAT_INK, 1),
        ((36, 96, 86, 108),  "Class",         FIELD, STAT_INK, 1),
        ((38, 138, 118, 149), "To Next Level", BAR,  STAT_INK, 1),
        ((26, 174, 60, 186), "Back",          HINT,  STAT_INK, 1),
    ],
})
LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 16, "nccl": 17, "ncsc": 18},
    "note": "madu_menu_pow2_bg -- Nutrition totals",
    # R tab, Total and Bonus are measured from seeds (work/submenu_seeds.py)
    "labels": _stat_labels(36, 102)
              + [((26, 174, 60, 186), "Back", HINT, STAT_INK, 1)],
})
LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 19, "nccl": 20, "ncsc": 21},
    "note": "madu_menu_pow3_bg -- hot spring bonuses",
    # the header stops short of x232: the green [R] button icon lives there
    # R tab and the Diet/Bonus and To Next tabs are measured from seeds
    "labels": _stat_labels(14, 70)
              + [((26, 174, 60, 186), "Back", HINT, STAT_INK, 1)],
})
LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 22, "nccl": 23, "ncsc": 24},
    "note": "madu_menu_pow4_bg -- hot spring (Spa Effect) timer",
    "labels": [
        ((26, 174, 60, 186), "Move", HINT, STAT_INK, 1),
        ((86, 174, 124, 186), "Back",  HINT, STAT_INK, 1),
    ],
})
LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 25, "nccl": 26, "ncsc": 27},
    "note": "madu_menu_pow5_bg -- Ramen Effect timer (header: seeds)",
    "labels": [
        ((26, 174, 60, 186), "Move", HINT, STAT_INK, 1),
        ((86, 174, 124, 186), "Back",  HINT, STAT_INK, 1),
    ],
})
LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "members": {"nccg": 28, "nccl": 29, "ncsc": 30},
    "note": "madu_menu_pow6_bg",
    "labels": [((26, 174, 60, 186), "Back", HINT, STAT_INK, 1)],
})

# Skill screen: the たいしょう ("Target") tag above the target box. Cream lettering
# on the brown header bar; identical layout for all four classes. The hint bar
# on the same trio is a separate spec below and composes with this one.
for _cls in ("magic", "priest", "soldier", "thief"):
    LAYERS.append({
        "archive": "info/subgraphics/madu_skill_%s.narc" % _cls,
        "members": {"nccg": 16, "nccl": 17, "ncsc": 18},
        "note": "skill screen -- Target tag (%s)" % _cls,
        "labels": [((188, 51, 244, 61), "Target", (156, 107, 16),
                    (247, 239, 222), 1)],
    })

# Skill screen: the ten skill-name triangles per class. Measured and drawn by
# tools/skill_panels.py (vertical names are stacked letter by letter), so these
# specs carry a `paint` callable instead of a label list.
from skill_panels import paint_panels  # noqa: E402

for _cls in ("magic", "priest", "soldier", "thief"):
    LAYERS.append({
        "archive": "info/subgraphics/madu_skill_%s.narc" % _cls,
        "members": {"nccg": 26, "nccl": 27, "ncsc": 28},
        "note": "skill triangles (%s)" % _cls,
        "paint": (lambda layer, font, _c=_cls: paint_panels(layer, font, _c)),
        "labels": [],
    })

# Skill screen sprite labels (title, skill-type pills, info-box headers): an OBJ
# bank in members 23-25 of each skill archive, painted by tools/skill_obj.py.
from skill_obj import paint as _paint_skill_obj  # noqa: E402

for _cls in ("magic", "priest", "soldier", "thief"):
    LAYERS.append({
        "archive": "info/subgraphics/madu_skill_%s.narc" % _cls,
        "note": "skill sprite labels (%s)" % _cls,
        "obj": (lambda narc, workdir: _paint_skill_obj(narc, workdir)),
    })

# Map screen sprite labels (title, World Change, and the greyed-out A hints):
# an OBJ bank in madu_map.narc members 20-22, painted by tools/map_obj.py.
from map_obj import paint as _paint_map_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_map.narc",
    "note": "map sprite labels",
    "obj": (lambda narc, workdir: _paint_map_obj(narc, workdir)),
})

# Status screen title bar (formerly "Strength"): an OBJ bank in madu_status.narc
# members 32-34, painted by tools/status_obj.py.
from status_obj import paint as _paint_status_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_status.narc",
    "note": "status sprite labels",
    "obj": (lambda narc, workdir: _paint_status_obj(narc, workdir)),
})

# Equipment screen sprite banks (title, quality tags, effect tags): OBJ banks in
# madu_equip.narc, painted by tools/equip_obj.py.
from equip_obj import paint as _paint_equip_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_equip.narc",
    "note": "equipment sprite labels",
    "obj": (lambda narc, workdir: _paint_equip_obj(narc, workdir)),
})

# Tika's Equipment Sell screen's own copy of the quality/stat sprite banks
# above (a separate narc, so translating madu_equip.narc's didn't cover it):
# OBJ banks in madu_shop_equip.narc, painted by tools/shop_equip_obj.py.
from shop_equip_obj import paint as _paint_shop_equip_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_shop_equip.narc",
    "note": "shop equipment sprite labels",
    "obj": (lambda narc, workdir: _paint_shop_equip_obj(narc, workdir)),
})

# Present's own copies of sprite banks painted elsewhere (byte-identical, so
# the same painters apply; never painted until 2026-09-24):
# madu_present_equip members 5/6/4 = madu_equip's effect tags (6/7/5), 14/15/13
# = its quality tags (18/19/17); madu_present 17/18/16 = madu_shop's title and
# tag bank (14/15/13: Buy / Sell / Exchange / Needed).
import equip_obj as _equip_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_present_equip.narc",
    "note": "present equipment tags",
    "obj": (lambda narc, workdir: (
        _equip_obj.paint_bank(narc, workdir + "_fx", (5, 6, 4), _equip_obj._effects),
        _equip_obj.paint_bank(narc, workdir + "_q", (14, 15, 13), _equip_obj._quality),
        narc.replace(4, _equip_obj.single_long(narc.file(4))))),
})
LAYERS.append({
    "archive": "info/subgraphics/madu_present.narc",
    "note": "present tag labels",
    "obj": (lambda narc, workdir: (
        _skill_obj_paint(narc, workdir, (17, 18, 16), _shop_obj.LABELS),
        # the same quantity-counter コ as the shop's cell 6
        _shop_obj._blank_tiles(narc, 17, _shop_obj.BLANK_TILES))[0]),
})
from skill_obj import paint as _skill_obj_paint  # noqa: E402

# The Ship menu's buttons: an OBJ bank in madu_ship.narc (members 8-10),
# painted by tools/ship_obj.py. The archive's BG layers are sub-menu seeds.
from ship_obj import paint as _paint_ship_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_ship.narc",
    "note": "ship menu sprite labels",
    "obj": (lambda narc, workdir: _paint_ship_obj(narc, workdir)),
})

# Items screen title bars (Items, Soaking): an OBJ bank in madu_item.narc members
# 11-13, painted by tools/item_obj.py.
from item_obj import paint as _paint_item_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_item.narc",
    "note": "item sprite labels",
    "obj": (lambda narc, workdir: _paint_item_obj(narc, workdir)),
})

# Medals screen title bar (was Medallion): an OBJ bank in madu_medal.narc members
# 17-19, painted by tools/medal_obj.py.
from medal_obj import paint as _paint_medal_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_medal.narc",
    "note": "medal sprite labels",
    "obj": (lambda narc, workdir: _paint_medal_obj(narc, workdir)),
})

# Memo screen title bar: an OBJ bank in madu_memo.narc members 12-14, painted by
# tools/memo_obj.py.
from memo_obj import paint as _paint_memo_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_memo.narc",
    "note": "memo sprite labels",
    "obj": (lambda narc, workdir: _paint_memo_obj(narc, workdir)),
})

# Quest and Jump title bars: OBJ banks painted by tools/quest_obj.py and
# tools/jump_obj.py.
from quest_obj import paint as _paint_quest_obj  # noqa: E402
from jump_obj import paint as _paint_jump_obj  # noqa: E402

LAYERS.append({
    "archive": "info/subgraphics/madu_quest.narc",
    "note": "quest sprite labels",
    "obj": (lambda narc, workdir: _paint_quest_obj(narc, workdir)),
})
LAYERS.append({
    "archive": "info/subgraphics/madu_jump.narc",
    "note": "jump sprite labels",
    "obj": (lambda narc, workdir: _paint_jump_obj(narc, workdir)),
})

# Sub-menu captions (Equipment, Items, Map, Medallion, Quest, Jump, shops ...):
# flat pills, measured from the seeds in work/submenu_seeds.py by
# tools/submenu_labels.py.
sys.path.insert(0, os.path.join(BASE, "work"))
from submenu_seeds import SEEDS as _SUBMENU_SEEDS  # noqa: E402
from submenu_labels import paint as _paint_submenu  # noqa: E402
from submenu_labels import prepare as _prepare_submenu  # noqa: E402

for _key, _seeds in sorted(_SUBMENU_SEEDS.items()):
    # (archive, nccg) -- the nccl/ncsc follow it; or (archive, nccg, ncsc, also)
    # for a screen whose NCSC is not the third member of its trio and whose tile
    # set another screen (`also`) shares
    _arc, _mem = _key[0], _key[1]
    if _arc == "loose":
        # ("loose", "info/title/tiop_top_bg") -- loose .ncg/.ncl/.nsc under extracted/
        # an optional third element names the palette when it is not <base>.ncl; an
        # optional fourth names an alternate .nsc base when a second screen shares
        # the same .ncg/.ncl but is laid out in its own loose .nsc file (not a
        # narc's "also" tuple -- there's no shared archive to protect siblings in,
        # just a second, unrelated-looking file that happens to share tiles)
        _members = {"nccg": _mem + ".ncg",
                    "nccl": (_key[2] if len(_key) > 2 and _key[2] else _mem) + ".ncl",
                    "ncsc": (_key[3] if len(_key) > 3 and _key[3] else _mem) + ".nsc"}
        _archive = "loose"
    else:
        _members = {"nccg": _mem, "nccl": _mem + 1,
                    "ncsc": _key[2] if len(_key) > 2 else _mem + 2}
        _archive = "info/subgraphics/%s.narc" % _arc
    _spec = {
        "archive": _archive,
        "members": _members,
        "note": "sub-menu captions %s:%s" % (_arc.replace("madu_", ""),
                                             "/".join(os.path.basename(str(k))
                                                      for k in _key[1:])),
        "prepare": (lambda layer, font, _k=_key: _prepare_submenu(layer, font, _k)),
        "paint": (lambda layer, font, labels=None, _k=_key:
                  _paint_submenu(layer, font, _k, labels)),
        "labels": [],
    }
    if _arc == "loose":
        # a 5th element, if given, lists sibling loose .nsc bases (without the
        # extension) that share this .ncg/.ncl and must be protected too --
        # key[3] here is the ncsc override above, not an "also" list
        if len(_key) > 4 and _key[4]:
            also = _key[4] if isinstance(_key[4], (tuple, list)) else [_key[4]]
            _spec["also"] = [a + ".nsc" for a in also]
    elif len(_key) > 3:
        _spec["also"] = (list(_key[3]) if isinstance(_key[3], (tuple, list))
                         else [_key[3]])
    LAYERS.append(_spec)


def _cook_confm(narc, workdir):
    """The greyed recipe list behind the cook confirm pop-up.

    maho_cook_confm_bg is a loose .nsc only: it draws the recipe list's
    (maho_cook_selem_bg's) tile set, with private grey copies of the hint row
    (grey ink, lime halo). The seed erase is tuned for brown ink and left the
    grey Japanese half-erased, so instead the hint row is derived from selem's
    finished English: every pixel is recoloured through the colour
    correspondence of the two original screens (selem colour -> confm colour at
    the same pixel), which yields the game's own grey rendering of it.
    Runs after the selem seed spec (which lists confm as `also`, so its private
    tiles survive) -- the order in LAYERS matters.
    """
    import collections
    base = "info/cook/maho_cook_"
    os.makedirs(workdir, exist_ok=True)
    paths = {}
    for name, rel in (("ncg", base + "selem_bg.ncg"), ("ncl", base + "selem_bg.ncl"),
                      ("selem", base + "selem_bg.nsc"), ("confm", base + "confm_bg.nsc")):
        paths[name] = os.path.join(workdir, name + ".bin")
        with open(paths[name], "wb") as fh:
            fh.write(narc.file(rel))
    orig = lambda rel: os.path.join(ROOT, base + rel)  # noqa: E731
    o_selem = BgLayer(orig("selem_bg.ncg"), orig("selem_bg.ncl"), orig("selem_bg.nsc"))
    o_confm = BgLayer(orig("selem_bg.ncg"), orig("selem_bg.ncl"), orig("confm_bg.nsc"))
    selem = BgLayer(paths["ncg"], paths["ncl"], paths["selem"])
    confm = BgLayer(paths["ncg"], paths["ncl"], paths["confm"], also=[paths["selem"]])
    # a tile selem also uses (even at the same spot) must not turn grey there
    confm.force_private = set(range(len(confm.cells)))
    x0, y0, x1, y1 = 16, 168, 192, 192          # the hint row, cell rows 21-23
    votes = collections.defaultdict(collections.Counter)
    for y in range(y0, y1):
        for x in range(x0, x1):
            votes[o_selem.rgb_at(x, y)][o_confm.rgb_at(x, y)] += 1
    cmap = {k: v.most_common(1)[0][0] for k, v in votes.items()}
    want = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            src = selem.rgb_at(x, y)
            rgb = cmap.get(src, src)
            if rgb != confm.rgb_at(x, y):
                want[(x, y)] = rgb
    # a cell confm draws with a shared tile (the blank tile 0 where selem's
    # English runs past the Japanese -- the top of "OK"'s K) gets its own
    need = {(y // 8) * confm.sw + x // 8 for x, y in want}
    shared = {ci for ci in need if not confm.exclusive(ci)}
    if shared:
        row = {(y // 8) * confm.sw + x // 8
               for y in range(y0, y1, 8) for x in range(x0, x1, 8)}
        confm.free_by_dedupe(protect=row)
        confm.privatise_cells(shared)
    blocked = 0
    for (x, y), rgb in want.items():
        ci = (y // 8) * confm.sw + x // 8
        if not confm.exclusive(ci):
            blocked += 1
            continue
        confm.put(x, y, confm.nearest(confm.cells[ci]["palette"], rgb),
                  allow_shared=True)
    if blocked:
        print("    !! cook confm: %d pixels sit on shared tiles" % blocked)
    changed = len(want) - blocked
    confm.save(paths["ncg"], paths["confm"])
    narc.replace(base + "selem_bg.ncg", open(paths["ncg"], "rb").read())
    narc.replace(base + "confm_bg.nsc", open(paths["confm"], "rb").read())
    if shared:
        # the dedupe may have merged tiles under selem too
        confm.save_others([paths["selem"]])
        narc.replace(base + "selem_bg.nsc", open(paths["selem"], "rb").read())
    print("  %-30s %-34s %d px" % ("loose", "cook confirm (greyed list) hints", changed))


LAYERS.append({"archive": "loose", "note": "cook confirm greyed hints",
               "obj": _cook_confm})

# ------------------------------------------------------------- hint bars --
# The icon+word strip along the bottom of most menus. Measured and generated by
# tools/hint_bars.py into work/hint_labels.py; regenerate that after editing its
# WORDS table. Where a trio already has a spec above (the top-menu frame), this
# adds a second spec for the same members -- build_archive applies specs in
# order against the same archive, so they compose.
# Set CTRES_NO_HINT_BARS=1 to build without them.
sys.path.insert(0, os.path.join(BASE, "work"))
_HINTS = {}
if not os.environ.get("CTRES_NO_HINT_BARS"):
    try:
        from hint_labels import HINTS as _HINTS
    except ImportError:
        _HINTS = {}

# other screens over a hint bar's tile set, which must not lose tiles under it
_HINT_ALSO = {
}

for (_arc, _mem), _labels in sorted(_HINTS.items()):
    _hs = {
        "archive": "info/subgraphics/%s.narc" % _arc,
        "members": {"nccg": _mem, "nccl": _mem + 1, "ncsc": _mem + 2},
        "note": "hint bar",
        "snap": True,
        "labels": _labels,
    }
    if (_arc, _mem) in _HINT_ALSO:
        _hs["also"] = _HINT_ALSO[(_arc, _mem)]
    LAYERS.append(_hs)






def paint_layer(layer, labels, font, snap=False, lossy=False):
    """Run the pipeline. Returns (starved, total_cells_claimed).

    A cell must be claimed if the English will be drawn on it, or if it still
    carries Japanese ink that has to be cleared. Claiming only the text cells
    leaves fragments of the original lettering wherever a background cell was
    shared; claiming the entire box exhausts the free tile pool. The union of
    the two is both correct and affordable.

    The pool is re-harvested between labels. Painting one label flattens its
    background into identical tiles, which can then be deduplicated to pay for
    the next -- without this, small layers (some are only 96 tiles) run out
    part-way and leave the last hint sitting on uncleared Japanese.
    """
    layer.snap = snap
    # a label may carry a 6th item, the alignment ("center" by default, "right")
    labels = [tuple(l) if len(l) == 6 else tuple(l) + ("center",) for l in labels]
    # ("auto", keep) fills: resolve against the untouched art before any label
    # is cleared, or the first clear changes what the second one sees.
    labels = [(box, text,
               layer.inpaint_targets(box, bg[1], only_ink=True)
               if isinstance(bg, tuple) and bg and bg[0] == "auto" else bg,
               ink, scale, align)
              for box, text, bg, ink, scale, align in labels]
    for box, _text, bg, _ink, _scale, _align in labels:
        layer.clear_private(box, bg)

    skipped = []
    claims = []
    for box, text, bg, _ink, scale, align in labels:
        claims.append(layer.text_cells(font, text, box, scale, align)
                      | layer.dirty_cells(box, bg))

    for i, ((box, text, bg, ink, scale, align), claim) in enumerate(zip(labels, claims)):
        remaining = set().union(*claims[i:]) if claims[i:] else set()
        layer.free_by_dedupe(protect=remaining)
        # A partially-claimed label is worse than an untouched one: the English
        # gets drawn over Japanese that could not be cleared. If the pool cannot
        # cover the whole claim, leave this label alone.
        need = sum(1 for ci in claim if not layer.exclusive(ci))
        if need > len(layer.free_pool) and (snap or lossy):
            # near-copy merges, least visible first: tiles whose differing
            # pixels are close colours, this screen's own then (away from any
            # label) a sibling's; only then any <= 2px difference
            labelled = set().union(*(layer.cells_in(l[0]) for l in labels))
            for perceptual in (True, False):
                for shared in (False, True):
                    if need <= len(layer.free_pool):
                        break
                    # sibling screens share this layout, so their cells inside
                    # any of these label boxes carry their own painted text
                    layer.free_by_dedupe(protect=set().union(*claims)
                                         | getattr(layer, "keep_exact", set()), tol=2,
                                         shared=shared, keep_other=labelled,
                                         perceptual=perceptual)
                    need = sum(1 for ci in claim if not layer.exclusive(ci))
        if need > len(layer.free_pool):
            skipped.append((text, need, len(layer.free_pool)))
            continue
        layer.privatise_cells(claim)
        layer.clear_private(box, bg)
        if not layer.draw_text_rgb(font, text, box, ink, scale=scale, align=align):
            if not layer.draw_text_rgb(font, text, box, ink, scale=1, align=align):
                print("    !! %r does not fit in %dpx" % (text, box[2] - box[0]))
    for text, need, have in skipped:
        print("    -- left in Japanese: %r needs %d free tiles, %d available"
              % (text, need, have))
    return layer.starved, len(set().union(*claims)) if claims else 0


class LooseFiles:
    """Stands in for a Narc when the graphics are loose files under extracted/.

    Members are ROM-relative paths ("info/title/tiop_top_bg.ncg") instead of
    indexes; `changed` collects what was replaced, for build_patch to install.
    """

    def __init__(self, root):
        self.root = root
        self.changed = {}

    def file(self, rel):
        if rel in self.changed:
            return self.changed[rel]
        with open(os.path.join(self.root, rel), "rb") as fh:
            return fh.read()

    def replace(self, rel, data):
        self.changed[rel] = bytes(data)


def _tag(idx):
    """A filename-safe tag for a member (an index or a relative path)."""
    return os.path.basename(str(idx)).replace(".", "_")


def build_archive(archive, specs, workdir):
    """Apply every layer belonging to one archive, returning the patched bytes.

    An archive can hold more than one background layer -- madu_topmenu.narc has
    the menu frame and the item buttons as separate trios -- so all of its
    layers are applied to a single Narc instance and written once. Handling
    them independently would make the last one written win.
    """
    loose = archive == "loose"
    patched = None if loose else text_patched_archives().get(archive)
    os.makedirs(workdir, exist_ok=True)
    if loose:
        narc = LooseFiles(ROOT)
    elif patched is not None:
        src_path = os.path.join(workdir, "source.narc")
        with open(src_path, "wb") as fh:
            fh.write(patched)
    else:
        src_path = os.path.join(ROOT, archive)
    if not loose:
        narc = Narc(src_path)
    font = load_font()
    rendered = []

    # Measure first, paint later: specs that share tiles must all read the
    # original art, not what an earlier spec left behind.
    measured = {}
    for n, spec in enumerate(specs):
        if "prepare" in spec:
            mm = spec["members"]
            pp = {}
            for key_, idx_ in mm.items():
                pth = os.path.join(workdir, "m%d_%s_%s.bin" % (n, key_, _tag(idx_)))
                with open(pth, "wb") as fh:
                    fh.write(narc.file(idx_))
                pp[key_] = pth
            measured[n] = spec["prepare"](BgLayer(pp["nccg"], pp["nccl"], pp["ncsc"]),
                                          font)

    for n, spec in enumerate(specs):
        if "obj" in spec:
            # a sprite bank inside the archive, not a background layer
            spec["obj"](narc, os.path.join(workdir, "obj%d" % n))
            print("  %-30s %-34s" % (archive.split("/")[-1], spec["note"][:34]))
            continue
        m = spec["members"]
        paths = {}
        for key, idx in m.items():
            p = os.path.join(workdir, "%d_%s_%s.bin" % (n, key, _tag(idx)))
            with open(p, "wb") as fh:
                fh.write(narc.file(idx))
            paths[key] = p
        also = []
        for j, idx in enumerate(spec.get("also", [])):
            p = os.path.join(workdir, "%d_also_%s.bin" % (n, _tag(idx)))
            with open(p, "wb") as fh:
                fh.write(narc.file(idx))
            also.append(p)
        layer = BgLayer(paths["nccg"], paths["nccl"], paths["ncsc"], also=also)
        # tiles past the last one the original screens use: off-limits only
        # where hardware showed them broken (TRAILING_UNSAFE)
        layer.use_never_used = archive not in TRAILING_UNSAFE
        before = layer.tw * layer.th
        if "paint" in spec:
            starved, cells = (spec["paint"](layer, font, measured[n])
                              if n in measured else spec["paint"](layer, font))
        else:
            starved, cells = paint_layer(layer, spec["labels"], font,
                                         spec.get("snap", False))
        out_nccg = os.path.join(workdir, "%d_out.ncg" % n)
        out_ncsc = os.path.join(workdir, "%d_out.nsc" % n)
        layer.save(out_nccg, out_ncsc)
        if also:
            # screens sharing the tile set may have had tiles merged under them
            outs = [os.path.join(workdir, "%d_also_out_%s.nsc" % (n, _tag(idx)))
                    for idx in spec["also"]]
            layer.save_others(outs)
            for idx, path_out in zip(spec["also"], outs):
                narc.replace(idx, open(path_out, "rb").read())
        nccg_new = open(out_nccg, "rb").read()
        ncsc_new = open(out_ncsc, "rb").read()
        same = len(nccg_new) == len(narc.file(m["nccg"]))
        print("  %-30s %-34s tiles %d->%d cells %d starved %d size-ok %s%s"
              % (archive.split("/")[-1], spec["note"][:34], before,
                 layer.n_tiles, cells, starved, same,
                 "  [text-patched src]" if patched is not None and n == 0 else ""))
        if starved:
            print("    !! %d cells could not be given a private tile" % starved)
        if not same:
            print("    !! NCCG size changed -- refusing, this game cannot grow it")
            continue
        narc.replace(m["nccg"], nccg_new)
        narc.replace(m["ncsc"], ncsc_new)
        rendered.append((spec, layer))
    return rendered, (narc if loose else bytes(narc.data))


# Archives whose tiles past the last originally-used one must not be spent.
# Medals (2026-09-25, hardware): Bronze Medal's header drew on tiles 346-348
# and they showed as a transparent square. Blocking them everywhere left a
# dozen labels in Japanese, and the battle screens use them fine on hardware,
# so this is per archive. Screens still using such tiles, not yet checked on
# hardware: equip, memo, present_equip, skill (magic/priest/soldier/thief),
# status (README Outstanding).
TRAILING_UNSAFE = {
    "info/subgraphics/madu_medal.narc",
    # (madu_equip was added for a grey strip under "Total Defense", then taken
    # out again 2026-09-26: blocked, the pool ran short and near-copy merges
    # put stray pixels by the fire icon and a new grey (99,99,99) pixel at
    # (135,64) -- the strip was most likely such a merge, not trailing tiles.
    # Unblocked, nothing outside the labels changes; the Resist tab's top row
    # uses tiles 291-295 -- if that row ever shows garbage, revisit.)
}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    mode = argv[1]
    text_sourced = []
    by_archive = {}
    for spec in LAYERS:
        by_archive.setdefault(spec["archive"], []).append(spec)

    for i, (archive, specs) in enumerate(sorted(by_archive.items())):
        work = os.path.join(BASE, "work", "bg_work", "%02d" % i)
        rendered, data = build_archive(archive, specs, work)
        if mode == "preview":
            out = os.path.join(BASE, "work", "gfx", "bg_en")
            os.makedirs(out, exist_ok=True)
            base = os.path.basename(archive).replace(".narc", "")
            for n, (_spec, layer) in enumerate(rendered):
                layer.render(os.path.join(out, "%s_%d.png" % (base, n)))
        elif mode == "apply" and archive == "loose":
            # loose graphics: mirror each changed file under <outdir>/loose/
            for rel, blob in sorted(data.changed.items()):
                dest = os.path.join(argv[2], "loose", rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(blob)
                orig = os.path.getsize(os.path.join(ROOT, rel))
                if len(blob) != orig:
                    print("    !! %s size %d != original %d" % (rel, len(blob), orig))
        elif mode == "apply":
            outdir = argv[2]
            os.makedirs(outdir, exist_ok=True)
            dest = os.path.join(outdir, os.path.basename(archive))
            with open(dest, "wb") as fh:
                fh.write(data)
            orig = os.path.getsize(os.path.join(ROOT, archive))
            if len(data) != orig:
                print("    !! %s size %d != original %d"
                      % (dest, len(data), orig))
            if text_patched_archives().get(archive) is not None:
                text_sourced.append(os.path.basename(archive))
        else:
            print(__doc__)
            return 1

    if mode == "apply" and text_sourced:
        # Tells build_patch that these BG archives already contain the
        # translated text members, so the BG copy supersedes the text-only one
        # instead of colliding with it.
        with open(os.path.join(argv[2], "_text_sourced.txt"), "w") as fh:
            fh.write("\n".join(sorted(set(text_sourced))) + "\n")
        print("  text-sourced archives recorded: %s"
              % ", ".join(sorted(set(text_sourced))))
    return 0



if __name__ == "__main__":
    sys.exit(main(sys.argv))
