"""Seeds for tools/submenu_labels.py: (archive, first member of the NCCG/NCCL/NCSC
trio) -> [(seed box, English[, "left"])].

A seed is a rough box (screen pixels) somewhere inside the Japanese caption; the
tool measures the caption and the pill around it (see that module). Add "left"
for captions that start at the pill's left end instead of being centred.
"""

# The equipment detail panel repeats on three screens with the same geometry.
_EQUIP_PANEL = [
    ((196, 8, 220, 15), "Effect"),
    ((16, 74, 56, 80), "Made By", "left"),
    ((156, 74, 196, 80), "Quality", "left"),
    ((14, 101, 74, 107), "Usable By", "left"),
    ((48, 116, 72, 122), "or up", "left"),
]
# Dungeon panel on the map screens
_DUNGEON = [
    ((232, 62, 240, 69), "'s", "left"),
    ((178, 77, 238, 85), "Dungeon"),
]
_CLEARED = [((154, 108, 232, 114), "Floors Cleared")]
_TREASURE = [((150, 103, 236, 113), "Treasure Points")]
# Received-item panel on the present-equipment screens
_GIFT_INFO = [
    ((14, 66, 62, 72), "Made By", "left"),
    ((162, 66, 202, 72), "Quality", "left"),
    ((10, 88, 28, 95), "Eff."),
]

# Status-screen tabs: the white tab pill top right (beside the green R) is sized
# for the Japanese, so each takes {"grow": "left"} to widen it for the English.
_TAB = {"grow": "left"}
_TIMER_BAR = [
    # boxes by hand: the measured ones overlap, and the later label's clear would
    # erase the tail of the earlier word
    ((112, 150, 126, 156), "Left", "center", {"box": (107, 147, 130, 159)}),
    ((138, 150, 160, 156), "hr", "center", {"box": (131, 147, 172, 159)}),
    ((182, 150, 218, 156), "min", "center", {"box": (173, 147, 223, 159)}),
]

_NAME = ((174, 43, 202, 49), "Name")
_NEXT = [((162, 75, 214, 81), "Next Medal"), ((156, 122, 220, 128), "Best Record")]
# On the power screens the captions' glyphs touch the pill outline, so the
# measurement cannot separate them; the boxes are given (the pill interior).
_NAME_P = ((174, 43, 202, 49), "Name", "center", {"box": (134, 41, 242, 50)})
_DESC = [((178, 75, 202, 81), "Description", "center", {"box": (134, 72, 242, 83)})]
_HDR = (146, 21, 232, 31)
_P = {"private": True}      # header text differs per screen: own tiles
_MEDAL_SCREENS = {
    5: [((170, 21, 206, 31), "Medals", "center", _P), _NAME] + _NEXT,
    6: [(_HDR, "Bronze Medal", "center", _P), _NAME] + _NEXT,
    7: [(_HDR, "Silver Medal", "center", _P), _NAME] + _NEXT,
    8: [(_HDR, "Gold Medal", "center", _P), _NAME] + _NEXT,
    9: [(_HDR, "Master Power", "center", _P), _NAME_P] + _DESC,
    10: [(_HDR, "Bronze Power", "center", _P), _NAME_P] + _DESC,
    11: [(_HDR, "Silver Power", "center", _P), _NAME_P] + _DESC,
    12: [(_HDR, "Gold Power", "center", _P), _NAME_P] + _DESC,
}

# hint strip on the loose title/options layers (green strip, orange icons)
_INK = {"inpaint": True}      # the strip runs over a curve; erase row by row


def _hint(seed, word, box, indent, **over):
    """A left-aligned hint word: `box` reaches the Japanese's first pixel,
    `indent` puts the English where the Japanese started (the originals sit
    ~5px after their button icon; boxes flush against the icon read cramped).
    Give `ink` where the seed sits on transparency, which it cannot measure."""
    return (seed, word, "left", dict(_INK, box=box, indent=indent, **over))


# Areas of a screen whose tiles must not be merged with near-copies when the
# tile pool runs short (bg_labels' lossy step): art there must stay exact.
KEEP_EXACT = {
    # e.g. ("madu_equip", 30): [(160, 108, 256, 176)] -- used while the
    # Equipment screen was short of tiles (2026-09-26); not needed since
}

# the Options/Continue/save strip: icons end x 24 / 80 / 143, lettering starts
# 29 / 85 / 148 (it used to be centred in its box, drifting 10-19px off the icon)
_OPT_MOVE = _hint((30, 176, 55, 183), "Move", (27, 173, 60, 188), 2)
_OPT_BACK = _hint((149, 176, 178, 183), "Back", (145, 173, 181, 188), 3)
_HINT3 = [
    _OPT_MOVE,
    _hint((88, 176, 121, 183), "OK", (83, 173, 125, 188), 2),
    _OPT_BACK,
]
# the shop-family strip: icons end x 24 / 82 / 147, lettering starts 29 / 87 / 152
_SHOP_MOVE = _hint((28, 175, 52, 184), "Move", (27, 173, 60, 188), 2)
_SHOP_OK = _hint((84, 174, 124, 187), "OK", (84, 173, 125, 188), 4)
_SHOP_BACK = _hint((147, 174, 178, 187), "Back", (148, 173, 182, 188), 4)
_SHOP_HINT = [_SHOP_MOVE, _SHOP_OK, _SHOP_BACK]
# strip A (Present, Tailor confirm, cooking confirm): icons end x 24 / 83 / 148,
# lettering starts 29 / 87 / 151
_STRIP_A = [
    _hint((30, 176, 56, 184), "Move", (26, 168, 62, 190), 3),
    _hint((88, 176, 122, 184), "OK", (85, 168, 128, 190), 2),
    _hint((152, 176, 177, 184), "Back", (150, 168, 187, 190), 1),
]

_KB_BASE = [
    ((49, 30, 80, 41), "Hira", "center"),
    ((92, 30, 122, 41), "Kata", "center"),
    # face x 166-243, rows 150-161 only: the measured box took in the white
    # frame (rows 148 / 163) and its inner highlight (149 / 162), which
    # hardware showed missing (password screen, round 5)
    ((185, 152, 228, 161), "Done!", "center", {"box": (166, 150, 244, 162)}),
    ((26, 174, 82, 184), "Enter", "left", dict(_INK, box=(26, 173, 84, 186))),
    ((107, 174, 136, 184), "Back", "left", dict(_INK, box=(106, 173, 138, 186))),
    ((213, 174, 241, 184), "Next", "center"),
]
_KB_KEYS = [((218, 90, 250, 104), "Space", "center")]

# The R tab on the present-equipment screens (white pill x 186-231) names the
# view R switches to: こうか (Effect) on NCSC 25, リスト (List) on 26; 24 has
# none. Private: the two captions differ over tiles the screens share.
_PE_TAB = {
    25: [((196, 7, 222, 15), "Effect", "center", {"private": True})],
    26: [((196, 7, 222, 15), "List", "center", {"private": True})],
}

# The medal screens' hint strip. Painted on each of the eight screens with the
# same labels: the other seven have their own tiles above and below the shared
# text row, so a hint painted through NCSC 5 alone showed the English cut to one
# tile row with the Japanese beneath it. (Used to be a generated hint bar.) The
# box is a row taller than the Japanese so the English sits on its rows (175-184).
_MEDAL_HINT = [
    _hint((32, 177, 56, 183), "Move", (28, 174, 64, 187), 4, ink=(123, 74, 8)),
    _hint((88, 177, 112, 183), "Back", (84, 174, 120, 187), 4, ink=(123, 74, 8)),
]

SEEDS = {
    # ---- Options screens: loose files under extracted/info/title ---------
    ("loose", "info/title/tiop_top_bg"): [((98, 18, 158, 26), "Options")] + _HINT3,
    ("loose", "info/title/tiop_sys_bg"): [
        ((90, 31, 168, 37), "Message Speed"),
        # the grey pills' lettering is white on grey, and mostly lettering in the seed
        ((60, 50, 78, 55), "Slow", "center",
         {"bg": (123, 123, 123), "ink": (255, 255, 231), "box": (56, 45, 80, 57)}),
        ((180, 50, 198, 55), "Fast", "center",
         {"bg": (123, 123, 123), "ink": (255, 255, 231), "box": (177, 45, 200, 57)}),
        ((108, 75, 150, 81), "Volume"),
        _OPT_MOVE,
        _hint((88, 176, 121, 183), "Change", (83, 173, 125, 188), 2),
        _OPT_BACK,
    ],
    ("loose", "info/title/tiop_save_conf_bg"): _HINT3,

    # ---- Character Creator: loose files under extracted/info/title, chr_make ----
    ("loose", "info/title/tiin_make_seles_bg"): [
        ((80, 10, 176, 24), "Character Maker"),
        ((37, 42, 94, 54), "Class", "center"),
        ((37, 63, 94, 74), "Gender", "center"),
        ((37, 84, 94, 95), "Face", "center"),
        ((37, 105, 94, 117), "Hairstyle", "center"),
        ((37, 126, 94, 138), "Hair Color", "center"),
        ((37, 147, 94, 158), "Voice", "center"),
        # face rows 169-184 only: rows 168 and 185-186 are the white border
        ((106, 173, 158, 183), "Done!", "center", {"box": (100, 169, 164, 185)}),
    ],
    ("loose", "info/title/tiin_make_fixs_bg"): [
        ((28, 175, 52, 184), "Move", "left", _INK),
        ((84, 174, 124, 187), "OK", "left", dict(_INK, box=(84, 173, 125, 188))),
        ((147, 174, 178, 187), "Back", "left", dict(_INK, box=(147, 173, 180, 188))),
    ],
    ("loose", "info/chr_make/tiin_make_selem_bg"): [
        ((14, 147, 53, 158), "Done!", "center"),
        ((28, 174, 53, 185), "Move", "center",
         {"bg": (99, 99, 99), "ink": (255, 255, 255), "box": (27, 172, 54, 187)}),
        # icons end x 75 / 131: the words sat flush against them; 3px gap
        ((77, 174, 110, 185), "OK", "left",
         {"bg": (99, 99, 99), "ink": (255, 255, 255), "box": (76, 172, 111, 187),
          "indent": 3}),
        ((132, 174, 172, 185), "Camera", "left",
         {"bg": (99, 99, 99), "ink": (255, 255, 255), "box": (132, 172, 180, 187),
          "indent": 3}),
    ],

    ("loose", "info/keyboard/keyboard_base", "info/keyboard/keyboard_share"): _KB_BASE + [
        ((16, 152, 90, 161), "Random!", "center"),
    ],
    ("loose", "info/keyboard/keyboard_base2", "info/keyboard/keyboard_share"): _KB_BASE,
    ("loose", "info/keyboard/keyboard_01", "info/keyboard/keyboard_share"): _KB_KEYS + [((218, 68, 250, 80), "Small", "center")],
    ("loose", "info/keyboard/keyboard_02", "info/keyboard/keyboard_share"): _KB_KEYS + [((218, 68, 250, 80), "Small", "center")],
    ("loose", "info/keyboard/keyboard_03", "info/keyboard/keyboard_share"): _KB_KEYS,
    ("loose", "info/keyboard/keyboard_04", "info/keyboard/keyboard_share"): _KB_KEYS,

    # ---- Arton's Island Art screen: loose files under extracted/info/islet ----
    ("loose", "info/islet/maho_isart_sele_bg"): [
        ((2, 2, 90, 15), "Island Art"),
        # the hint row here sits on a transparent hole (the animated light-green
        # circle shows through from a lower layer) -- clear to real transparency
        # (bg=None), not a sampled flat colour, or a patch shows on hardware
        ((26, 170, 63, 189), "Move", "left",
         {"box": (26, 170, 63, 189), "ink": (123, 74, 0), "bg": None, "indent": 4}),
        # the A icon ends at x 80: the box must start past it
        ((80, 170, 127, 189), "OK", "left",
         {"box": (82, 170, 127, 189), "ink": (123, 74, 0), "bg": None, "indent": 2}),
        ((144, 170, 179, 189), "Back", "left",
         {"box": (144, 170, 179, 189), "ink": (123, 74, 0), "bg": None, "indent": 2}),
    ],
    ("loose", "info/islet/maho_isart_conf_bg"): [
        ((37, 86, 111, 113), "Yes"),
        ((146, 86, 220, 113), "No"),
        # a flat fill here lit a pale block over the two-tone strip
        _hint((30, 176, 55, 183), "Move", (27, 172, 60, 191), 2),
        _hint((88, 176, 121, 183), "OK", (83, 172, 125, 191), 2),
        _hint((149, 176, 178, 183), "Back", (145, 172, 181, 191), 3),
    ],

    ("loose", "info/title/time_mode_top_bg"): [
        ((78, 15, 178, 33), "Continue"),
        # two bottom tips of から survived on row 28 (their colours pass for
        # the glow's): that row is 8px blocks of (255,247,189) / (239,255,181)
        # (hardware 2026-09-26)
        ((126, 28, 130, 29), "", "left", {"box": (126, 28, 130, 29), "bg": (255, 247, 189)}),
        ((154, 28, 158, 29), "", "left", {"box": (154, 28, 158, 29), "bg": (239, 255, 181)}),
        _OPT_MOVE,
        _hint((92, 174, 122, 184), "OK", (83, 173, 125, 188), 2),
        _hint((156, 174, 190, 186), "Back", (145, 173, 181, 188), 3),
    ],

    # ---- Monster Almanac: loose files under extracted/info/islet ----
    # Box left/right edges below are tuned to the *pixel* extent of each JP
    # caption measured against extracted/info/islet/maho_dict_sele_bg (icons:
    # D-pad 8-25, A-badge 61-72, B-badge 112-127, L-badge 164-177, "+" 179-187,
    # D-pad(2) 189-206). submenu_labels.py's box-override path pins the drawn
    # text's left edge to the box's own left edge (`tight[0] = box[0]`), and
    # the *whole* box is cleared to `bg` first regardless of how much of it the
    # English actually fills -- so a box even a few px wider than the original
    # JP glyph run either leaves an uncleared sliver of the old glyph (if too
    # narrow) or, worse, reaches into a *neighbouring* icon's own tile column
    # and wipes it when cleared to transparent (if too wide). This is what
    # broke "Move" (touched the D-pad -- box started at 24, before the JP
    # glyph's real start at 28) and "Family"'s L-badge (Back's box reached to
    # 182, well past its own JP text's end at 155 and into the L-badge's tile
    # at 164-177) -- invisible under the old opaque `bg` fill, exposed once
    # `bg=None` made the same over/under-reach transparent instead of a wrong
    # colour. Re-measure against the *original* art before touching these.
    ("loose", "info/islet/maho_dict_sele_bg", "", "", "info/islet/maho_dict_sele_bg_scroll"): [
        ((3, 2, 95, 15), "Monster Almanac"),
        ((28, 169, 58, 189), "Move", "left",
         {"box": (28, 169, 58, 189), "ink": (123, 74, 0), "bg": None}),
        # the A icon and its shadow end at x 77 (Pose's old box began at 74 and
        # cut it); もどる begins at 129 (Back's began at 131, leaving a sliver)
        ((79, 169, 110, 189), "Pose", "left",
         {"box": (79, 169, 110, 189), "ink": (123, 74, 0), "bg": None, "indent": 2}),
        ((129, 169, 160, 189), "Back", "left",
         {"box": (129, 169, 160, 189), "ink": (123, 74, 0), "bg": None, "indent": 2}),
        ((210, 169, 245, 189), "Family", "left",
         {"box": (210, 169, 245, 189), "ink": (123, 74, 0), "bg": None}),
    ],
    ("loose", "info/islet/maho_dict_sele_bg", "", "info/islet/maho_dict_sele_bg_scroll", "info/islet/maho_dict_sele_bg"): [
        # たっせいりつ is x 25-85, rows 31-40, on plain (255,255,231); the
        # number frame the game draws "100" into is x 86-113. The old measured
        # box ran to x 109 -- over the frame -- and the centred word ran into
        # "100 %" (hardware 2026-09-26). Box and colours given by hand.
        ((28, 24, 109, 40), "Completion", "center",
         {"box": (24, 30, 86, 42), "bg": (255, 255, 231), "ink": (123, 74, 0)}),
    ],
    ("loose", "info/islet/maho_dict_exp_bg"): [
        ((5, 17, 105, 35), "Drops"),
        # seed must sit fully inside the white pill (184-230); straddling its
        # edge into the plain background made analyse() misjudge which side was
        # "background", clearing the pill *and* the neighbouring R icon to the
        # screen's backdrop colour instead of just the caption
        # face x 186-231, rows 3-19: the measured box spilled left of the face
        # and painted a jagged white notch onto the backdrop (hardware 2026-09-24)
        ((190, 10, 225, 23), "Details", "center", {"box": (186, 3, 232, 20)}),
    ],
    ("loose", "info/islet/maho_dict_pow_bg"): [
        ((5, 17, 88, 35), "Habitat"),
        ((190, 10, 225, 23), "Info", "center", {"box": (186, 3, 232, 20)}),
        ((5, 90, 90, 108), "Weakness"),
    ],

    # ---- Cook menu: loose files under extracted/info/cook ----
    # (category select confirm + recipe-detail confirm both use maho_cook_confs_bg)
    ("loose", "info/cook/maho_cook_confs_bg"): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
        _hint((24, 168, 60, 190), "Move", (26, 168, 62, 190), 3),
        _hint((80, 168, 128, 190), "OK", (84, 168, 130, 190), 3),
        _hint((148, 168, 185, 190), "Back", (148, 168, 187, 190), 3),
    ],
    ("loose", "info/cook/maho_cook_lv_bg"): [
        ((44, 84, 142, 96), "To Next Level"),
    ],
    # mostly a transparent hole, but "Back" sits on the opaque striped green:
    # bg=None cleared a transparent block there; the inpaint erase fills each
    # lettering pixel from its own neighbours instead (transparent or green)
    ("loose", "info/cook/maho_cook_selem_bg", "", "", "info/cook/maho_cook_confm_bg"): [
        _hint((28, 169, 57, 189), "Move", (28, 169, 62, 189), 0, ink=(123, 74, 0)),
        _hint((86, 169, 124, 189), "OK", (86, 169, 128, 189), 0, ink=(123, 74, 0)),
        _hint((151, 169, 181, 189), "Back", (151, 169, 184, 189), 0, ink=(123, 74, 0)),
    ],
    # (its greyed copy, maho_cook_confm_bg -- shown behind the cook confirm
    # pop-up -- is recoloured from this in bg_labels._cook_confm)
    ("loose", "info/cook/maho_cook_seles1_bg"): [
        ((188, 8, 226, 15), "Details"),
        # header pill's own inner edges run ~16-242; the three JP words fill
        # nearly the whole width edge to edge (ざいりょう ~19-97, もっているかず
        # ~103-166, ひつようなかず ~174-238) -- a box narrower than each word's
        # own span left visible fragments of the word's first/last character
        # outside it (this is what "Items" showing "ざItemsう" was)
        # the measurement isolates only いりょ (x 68-93) of ざいりょう (x 51-104,
        # y 40-50), so ざ and う survived beside "Items" (hardware 2026-09-24):
        # the box is given by hand
        # rowfill: the pills are shaded (light rim, darker centre); a flat fill
        # showed as a darker box round each word (hardware 2026-09-24). All
        # three share one vertical profile; it is sampled on the first pill,
        # left of its lettering: sampled across x 20-130, the Japanese
        # outline's redder shade (173,115,24) won most rows and the words sat
        # in an off-colour box (hardware, round 5). Plain face is (173,123,24).
        ((52, 42, 100, 50), "Items", "center", {"box": (46, 40, 105, 52), "rowfill": (20, 46)}),
        # the bar is three pills joined at notches x ~137 / ~188 (centres x 76,
        # 163, 214); the measured boxes centred Held and Needed over the notches
        # (hardware 2026-09-24). Each box is its pill's lettering span, so the
        # word centres on its own pill
        ((142, 42, 184, 50), "Held", "center", {"box": (141, 40, 186, 52), "rowfill": (20, 46)}),
        ((192, 42, 234, 50), "Needed", "center", {"box": (191, 40, 236, 52), "rowfill": (20, 46)}),
        # X-button pill: icon x 154-168 (its rim reaches 168 on some rows, which
        # a box from 168 clipped), face to x 233 on rows 131-140. The old
        # measured box began on the icon and ran over the pill's edges, erasing
        # the X and squaring the pill (hardware 2026-09-24)
        ((172, 132, 232, 140), "Source", "left",
         {"box": (169, 131, 234, 141), "indent": 3}),
    ],

    # the Details (R) pane: えいようボーナス and the five stat names, worded as
    # on the Equipment screen's stat table (maho_equi_pow_bg)
    ("loose", "info/cook/maho_cook_seles2_bg"): [
        ((30, 30, 130, 40), "Nutrition Bonus"),
        ((16, 60, 66, 70), "Vitality"),
        ((16, 81, 66, 91), "Spirit"),
        ((16, 102, 66, 112), "Strength"),
        ((16, 123, 66, 133), "Magic"),
        ((16, 144, 66, 154), "Speed"),
    ],

    # ---- Wireless multiplayer / merge screens (never painted until 2026-09-24) ----
    # Wording follows the menu text already in ui_text.tsv ("Invite a friend",
    # "Cross plaza", "Treasure Point"); スタイル is "Class" as on every other
    # screen. Most strips are the Options layout (_HINT3); the others give each
    # word 5px after its icon, as the Japanese does.
    ("loose", "info/connect/time_mode_mlt_bg"): _HINT3,
    ("loose", "info/connect/time_mode_mlt_go1_bg"): [
        ((95, 10, 165, 20), "Go Visit"),
    ] + _HINT3,
    ("loose", "info/connect/time_mode_mlt_sea_bg"): [
        ((95, 10, 165, 20), "Go Visit"),
    ],
    # A はじめる / B もどる: icons end x 23 / 86
    ("loose", "info/connect/time_mode_mlt_inv_bg"): [
        # しょうたいする starts at x 87, left of where the measurement began
        # background from the blank plate of time_mode_mlt_inv2_bg (the flat
        # box showed on hardware, 2026-09-26)
        ((95, 10, 165, 20), "Invite", "center",
         {"box": (80, 8, 172, 23), "fillfrom": "connect/time_mode_mlt_inv2_bg"}),
        # はじめる！ button: face x 88-169, rows 134-143, a vertical gradient
        ((106, 135, 152, 143), "Start!", "center",
         {"box": (90, 134, 167, 144), "rowfill": (90, 104),
          "bg": (255, 255, 231), "ink": (123, 74, 0)}),
        _hint((28, 176, 56, 184), "Start", (25, 168, 70, 190), 3),
        _hint((91, 176, 112, 184), "Back", (88, 168, 125, 190), 3),
    ],
    ("loose", "info/connect/time_mode_mlt_inv2_bg"): [
        # はじめる！ button: face x 88-169, rows 134-143, a vertical gradient
        ((106, 135, 152, 143), "Start!", "center",
         {"box": (90, 134, 167, 144), "rowfill": (90, 104),
          "bg": (255, 255, 231), "ink": (123, 74, 0)}),
        _hint((28, 176, 56, 184), "Start", (25, 168, 70, 190), 3),
        _hint((91, 176, 112, 184), "Back", (88, 168, 125, 190), 3),
    ],
    ("loose", "info/connect/time_mode_mrg_lob_bg"): [
        ((95, 22, 160, 32), "Merge Plaza"),
    ],
    # icons end x 24 / 74 / 134
    ("loose", "info/connect/time_mode_mrg_sele_bg"): [
        ((95, 22, 160, 32), "Merge Plaza"),
        _hint((29, 176, 56, 184), "Move", (26, 168, 60, 190), 3),
        _hint((79, 176, 112, 184), "OK", (76, 168, 119, 190), 3),
        _hint((139, 176, 165, 184), "Back", (136, 168, 175, 190), 3),
    ],
    # larger buttons than the other Yes/No screens: faces x 40-106 / 150-217,
    # rows 99-120, lettering rows 104-116
    ("loose", "info/merge/time_mode_mrg_alt_bg"): [
        ((58, 104, 88, 117), "Yes"),
        ((161, 104, 200, 117), "No"),
    ],
    ("loose", "info/merge/time_mode_mrg_bg"): _HINT3,
    # Move / A クロス / X かいそう / B もどる: icons end x 24 / 75 / 125 / 186.
    # かいそう is "Preview" (user, 2026-09-26: it shows which floors are open
    # and each floor's treasure points; nothing is edited). The boxes start
    # at row 170: from 168 they painted over the strip's dark line on row 169
    # (hardware: a broken line above the hints; this BG strip is the enabled one)
    ("loose", "info/merge/time_mode_mrg_mapm_bg"): [
        ((160, 26, 225, 36), "My World"),
        _hint((29, 176, 56, 184), "Move", (26, 170, 59, 190), 3, dy=1),
        _hint((80, 176, 108, 184), "Cross", (77, 170, 110, 190), 3, dy=1),
        _hint((130, 176, 170, 184), "Preview", (127, 170, 171, 190), 3, dy=1),
        _hint((191, 176, 215, 184), "Back", (188, 170, 230, 190), 3, dy=1),
    ],
    # Move / X ダンジョンせんたく: icons end x 24 / 75
    ("loose", "info/merge/time_mode_mrg_maps_bg"): [
        ((110, 12, 228, 24), "'s Dungeons", "left"),
        ((140, 72, 225, 84), "Treasure Points"),
        ((130, 142, 200, 154), "Open Floors", "left"),
        # from row 170, not 168: row 169 is the strip's dark line (see above).
        # dy 1: this BG layer is the ENABLED strip (orange icons, colour 9);
        # the sprite overlay is the greyed one. The icons span rows 171-187:
        # words on 175-184, as the Japanese, in both states (hardware
        # 2026-09-26: the old dy -1 put these 2px high and made toggling jump)
        _hint((29, 176, 56, 184), "Move", (26, 170, 59, 190), 3, dy=1),
        _hint((80, 176, 140, 184), "Pick Dungeon", (77, 170, 186, 190), 3, dy=1),
    ],
    ("loose", "info/title/time_mode_mlt_bg"): _HINT3,
    ("loose", "info/title/time_mode_mrg_bg"): _HINT3,
    ("loose", "info/title/time_mode_qst_bg"): [
        ((35, 46, 92, 56), "Quest 1"),
        # the four buttons are the same size as Quest 1's (the measurement
        # spilled past the others' right ends)
        ((160, 46, 218, 56), "Quest 2", "center", {"box": (154, 46, 224, 60)}),
        ((35, 101, 92, 111), "Quest 3", "center", {"box": (30, 102, 97, 116)}),
        ((160, 101, 218, 111), "Quest 4", "center", {"box": (154, 102, 224, 116)}),
    ] + _HINT3,
    ("loose", "info/title/time_mode_qst_s1_bg"): [
        ((23, 53, 63, 64), "Class"),
        ((148, 53, 186, 64), "Level"),
    ],

    # ---- Present / ending save / Tailor (never painted until 2026-09-24) ----
    # strip A (Present, Tailor confirm): icons end x 24 / 83 / 148, lettering
    # starts 29 / 87 / 151, rows 176-184 -- the same as the cooking confirm's
    ("loose", "info/present/maho_pre_topm_bg"): [
        # a shaded parchment label (face x 86-166): erase row by row
        ((97, 12, 154, 22), "Present", "center", {"box": (86, 11, 166, 23), "inpaint": True}),
    ],
    ("loose", "info/present/maho_pre_tops_bg"): [
        ((95, 44, 160, 56), "Items"),
        ((95, 100, 160, 112), "Equipment"),
    ] + _STRIP_A,
    ("loose", "info/present/maho_pre_rpt_bg"): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
    ] + _STRIP_A,
    ("loose", "info/save/end_save_m_bg"): [
        # the same parchment label as Present's; the seed alone caught a sliver
        ((106, 30, 146, 39), "Save", "center", {"box": (86, 28, 166, 40), "inpaint": True}),
    ],
    # Move + OK only: icons end x 23 / 80, lettering starts 29 / 88
    ("loose", "info/save/end_save_s_bg"): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
        # white lettering on an opaque black band: a flat black fill (the row
        # erase kept the grey antialiasing as specks)
        _hint((32, 176, 56, 184), "Move", (26, 168, 62, 190), 3,
              inpaint=False, bg=(0, 0, 0), ink=(255, 255, 255)),
        _hint((89, 176, 121, 184), "OK", (84, 168, 126, 190), 4,
              inpaint=False, bg=(0, 0, 0), ink=(255, 255, 255)),
    ],
    # Tailor main: icons end x 24 / 79 / 141, lettering starts 29 / 84 / 146
    ("loose", "info/tailor/maho_tail_m1_bg"): [
        ((10, 3, 80, 13), "Tailor"),
        _hint((29, 174, 56, 182), "Move", (26, 168, 60, 190), 3),
        _hint((85, 174, 119, 182), "OK", (82, 168, 124, 190), 2),
        _hint((147, 174, 171, 182), "Back", (144, 168, 178, 190), 2),
    ],
    # this strip sits on transparency: clear to transparent, as the Almanac's
    ("loose", "info/tailor/maho_tail_s1_bg"): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
    ] + [(seed, word, align, dict(over, bg=None, ink=(123, 82, 0)))
         for seed, word, align, over in _STRIP_A],

    # ---- Workshop (equipment crafting): loose files under extracted/info/product ----
    # (maat_ = "make atelier"?). Job-name pill boxes ("こうぼう"/つくる/きたえる,
    # the Attack/Defense stat pills, Source/Location toggle) are OBJ sprites --
    # see tools/options_obj.py's "product/maat_make_top_obj" and
    # "product/maat_make_rcp_obj" entries, not here.
    ("loose", "info/product/maat_make_top_bg"): [
        _hint((29, 170, 57, 190), "Move", (26, 170, 62, 190), 3),
        _hint((90, 170, 123, 190), "OK", (85, 170, 128, 190), 2),
        _hint((150, 170, 178, 190), "Back", (149, 170, 184, 190), 3),
    ],
    ("loose", "info/product/maat_make_conf_bg"): [
        ((37, 85, 110, 113), "Yes"),
        ((147, 85, 220, 113), "No"),
    ],
    ("loose", "info/product/maat_make_rcp_bg"): [
        ((10, 7, 103, 22), "Recipe"),
        ((3, 28, 77, 43), "Learned LV", "left"),
        ((188, 8, 226, 15), "Details"),
        # three pills joined at notches x ~138 / ~188, as on the cooking list;
        # each box is its pill's lettering span so the word centres on its pill
        # (Held/Needed sat off-centre, and ず's dakuten at x 235-237 was left
        # as a white tick -- hardware 2026-09-24)
        # text 1px lower than centred (it sat high, uncovering row 83) and each
        # row filled with its pill colour, as on the cooking list (sampled on
        # the first pill: the narrow ones are mostly lettering on some rows)
        ((63, 74, 96, 83), "Materials", "center",
         {"box": (22, 72, 134, 83), "rowfill": (24, 132), "dy": 1}),
        ((142, 74, 184, 83), "Held", "center",
         {"box": (141, 72, 186, 83), "rowfill": (24, 132), "dy": 1}),
        ((191, 74, 236, 83), "Needed", "center",
         {"box": (190, 72, 238, 83), "rowfill": (24, 132), "dy": 1}),
        # the pill's flat face is x 168-233, y 163-172; the measured box took in
        # its shaded top/bottom rows and rounded right end and squared them off
        ((167, 165, 237, 177), "Source", "center", {"box": (169, 163, 234, 173)}),
    ],
    ("loose", "info/product/maat_make_exp1_bg"): [
        ((128, 27, 222, 45), "'s Artisan Level", "left"),
        ((47, 90, 143, 103), "To Next Level"),
    ],
    ("loose", "info/product/maat_make_eff1_bg"): [
        ((8, 3, 107, 22), "Effect"),
        ((188, 3, 233, 17), "Recipe"),
    ],
    # the Create-side twins of eff1/exp1/itm1 (the "Create > Effects page
    # untranslated" hardware report of 2026-09-24): same wording
    ("loose", "info/product/maat_make_eff2_bg"): [
        ((8, 3, 107, 22), "Effect"),
    ],
    ("loose", "info/product/maat_make_exp2_bg"): [
        ((128, 27, 222, 45), "'s Artisan Level", "left"),
        ((47, 90, 143, 103), "To Next Level"),
    ],
    ("loose", "info/product/maat_make_itm2_bg"): [
        ((8, 3, 108, 22), "Details"),
        ((12, 74, 77, 84), "Made By", "left"),
        # face x 150-246, rows 69-87; クオリティ runs x 154-199 and the measured
        # box started at 164, leaving ク. The quality tag sprite (info/common/
        # icon_qua) is drawn over the right part of the face, so the word sits
        # left, where the Japanese did (centred, it read "Qua" on hardware
        # 2026-09-25): 34px from x 154, the old clear box kept.
        ((154, 74, 199, 84), "Quality", "left", {"box": (152, 70, 244, 86)}),
        ((12, 98, 77, 107), "Usable By", "left"),
        ((45, 114, 77, 123), "or up", "left"),
    ],
    ("loose", "info/product/maat_make_itm1_bg"): [
        ((8, 3, 108, 22), "Details"),
        ((188, 3, 250, 17), "Effect"),
        ((12, 80, 77, 90), "Usable By", "left"),
        ((45, 98, 77, 108), "or up", "left"),
    ],

    # ---- Equipment-slot list + stat-compare screens: loose files under
    # extracted/info/equip -- previously unfound because only
    # info/subgraphics/madu_equip.narc had been checked (that narc holds the
    # per-item Effect/Details/Stats detail pages; this separate loose set is
    # the そうびへんこう slot list itself and its stat-compare table) ----
    ("loose", "info/equip/maho_equi_sele_bg"): [
        ((2, 2, 98, 15), "Equipment Change"),
        ((28, 168, 60, 187), "Move", "left",
         {"box": (28, 168, 60, 187), "ink": (123, 74, 0), "bg": None}),
        ((83, 168, 122, 187), "OK", "left",
         {"box": (83, 168, 122, 187), "ink": (123, 74, 0), "bg": None}),
        ((145, 168, 176, 187), "Back", "left",
         {"box": (145, 168, 176, 187), "ink": (123, 74, 0), "bg": None}),
        ((197, 168, 238, 187), "Camera", "left",
         {"box": (197, 168, 238, 187), "ink": (123, 74, 0), "bg": None}),
    ],
    ("loose", "info/equip/maho_equi_pow_bg"): [
        ((188, 8, 226, 15), "Details"),
        ((108, 35, 152, 48), "Current"),
        ((178, 35, 223, 48), "After"),
        # boxes = the Japanese glyphs' measured extent: the old ones stopped 1-3
        # rows short, leaving each word's bottom row (seen on hardware 2026-09-24)
        ((37, 52, 96, 63), "Vitality", "left", {"box": (37, 52, 96, 63)}),
        ((37, 66, 96, 76), "Spirit", "left", {"box": (37, 66, 96, 76)}),
        ((37, 80, 96, 91), "Strength", "left", {"box": (37, 80, 96, 91)}),
        ((37, 94, 96, 105), "Magic", "left", {"box": (37, 94, 96, 105)}),
        ((37, 108, 96, 118), "Speed", "left", {"box": (37, 108, 96, 118)}),
        # rows 124 / 140 held one stray Japanese pixel each (hardware 2026-09-24):
        # the boxes start a row higher and end a row lower (text rows unchanged)
        ((27, 124, 105, 137), "Total Attack", "left", {"box": (27, 124, 105, 137)}),
        ((27, 140, 105, 153), "Total Defense", "left", {"box": (27, 140, 105, 153)}),
    ],

    ("madu_equip", 20): _EQUIP_PANEL,
    ("madu_equip", 33): _EQUIP_PANEL,
    ("madu_equip", 23): [((188, 8, 226, 15), "Details")],
    # the three tabs are rounded pills (white outline, white lettering); the
    # boxes are each tab's own rows (below them the colour runs on into the
    # value boxes) and `pillfill` repaints only the pill's inside
    ("madu_equip", 30): [
        ((144, 12, 210, 20), "Total Attack", "center",
         {"box": (136, 9, 216, 24), "pillfill": (255, 115, 148)}),
        ((160, 52, 228, 58), "Total Defense", "center",
         {"box": (155, 46, 234, 61), "pillfill": (49, 148, 206)}),
        # dy 2: "Resist" sat 2px higher than まもり (hardware 2026-09-26)
        ((172, 96, 200, 104), "Resist", "center",
         {"box": (150, 92, 222, 106), "pillfill": (156, 99, 206), "dy": 2}),
    ],
    ("madu_equip", 36): [((196, 8, 220, 15), "Stats")],
    ("madu_equip", 40, 42, 39): [((156, 35, 200, 42), "Defense", "left")],
    # the pink Attack tab is a second screen (NCSC 39) over the same tiles as the
    # blue Defense tab (NCSC 42): the tiles must not be freed or merged under it
    ("madu_equip", 40, 39, 42): [((156, 36, 200, 42), "Attack", "left")],

    ("madu_item", 7): [((122, 16, 186, 22), "Items Collected", "left")],
    ("madu_item", 14): [((70, 139, 186, 145), "Item After Soaking")],

    ("madu_map", 7): _DUNGEON + _CLEARED,
    ("madu_map", 13): _DUNGEON + _TREASURE,
    ("madu_map", 16): _TREASURE,
    ("madu_map", 23): _DUNGEON + _TREASURE,
    ("madu_map", 26): _DUNGEON + _CLEARED,

    # Medallion ("Medals") screen: eight screens -- medal / bronze / silver / gold
    # and master power / bronze / silver / gold -- over ONE tile set (NCCG 3), so
    # every spec protects the other seven. The shared labels (Name, Next Medal,
    # Best Record, Description) are the same tiles at the same cells on each
    # screen and are painted in place; each screen adds its own header pill.
    **{("madu_medal", 3, _n, tuple(m for m in range(5, 13) if m != _n)):
       _MEDAL_SCREENS[_n] + _MEDAL_HINT
       for _n in range(5, 13)},

    # Memo pages: two screens (first page / later pages) over one tile set (NCCG
    # 9); the D-pad and B hints read the same on both, so each protects the other.
    ("madu_memo", 9, 7, (8,)): [
        ((32, 177, 54, 183), "Next"),
        ((88, 177, 112, 183), "Back"),
    ],
    ("madu_memo", 9, 8, (7,)): [
        ((32, 177, 54, 183), "Next"),
        ((88, 177, 112, 183), "Back"),
    ],

    ("madu_quest", 7): [
        ((36, 30, 94, 37), "Client"),
        ((134, 30, 184, 37), "Friendship"),
    ],
    ("madu_quest", 14): [
        ((132, 29, 192, 37), "'s Quest", "left"),
        ((40, 137, 108, 143), "Quest Item"),
        ((146, 137, 188, 143), "Owned", "center", {"box": (142, 136, 193, 146)}),
        ((200, 137, 244, 143), "Needed", "center", {"box": (194, 136, 247, 146)}),
    ],

    # Jump menu: three screens over NCCG 8 -- the main list (NCSC 19: the two active
    # orange pills, hint bar), the friend variant (13) and the Yes/No confirm (14).
    # The disabled (grey) pills are a separate "board" layer, done just below.
    ("madu_jump", 8, 19, (13, 14)): [
        ((100, 53, 160, 61), "Island Jump"),
        ((100, 102, 160, 110), "Friend Jump"),
        ((30, 177, 54, 183), "Move"),
        ((88, 177, 122, 183), "OK"),
        # もどる sits past the strip's curve, on transparency: the measured fill
        # was the lettering's gold fringe, and lit a gold block
        ((152, 177, 178, 183), "Back", "left",
         {"box": (146, 173, 180, 188), "ink": (123, 74, 0), "bg": None, "indent": 3}),
    ],
    ("madu_jump", 8, 14, (13, 19)): [
        ((56, 89, 90, 99), "Yes"),
        ((166, 89, 200, 99), "No"),
        ((30, 177, 54, 183), "Move"),
        ((88, 177, 122, 183), "OK"),
        # もどる sits past the strip's curve, on transparency: the measured fill
        # was the lettering's gold fringe, and lit a gold block
        ((152, 177, 178, 183), "Back", "left",
         {"box": (146, 173, 180, 188), "ink": (123, 74, 0), "bg": None, "indent": 3}),
    ],
    ("madu_jump", 8, 13, (14, 19)): [
        ((30, 177, 54, 183), "Move"),
        ((88, 177, 122, 183), "OK"),
        # もどる sits past the strip's curve, on transparency: the measured fill
        # was the lettering's gold fringe, and lit a gold block
        ((152, 177, 178, 183), "Back", "left",
         {"box": (146, 173, 180, 188), "ink": (123, 74, 0), "bg": None, "indent": 3}),
    ],
    ("madu_jump", 10): [
        ((44, 14, 120, 24), "Island Jump"),
        ((30, 54, 132, 64), "Friend Jump"),
    ],

    ("madu_present", 9): [
        ((60, 39, 94, 45), "Item"),
        ((142, 39, 184, 45), "Gained", "center", {"box": (139, 38, 187, 47)}),
        ((198, 39, 232, 45), "Total"),
    ],
    # NCSC 8 is a second screen over the tiles of 14 (maho_pre_sele_bg) with its
    # own hint strip; 14's strip is the generated hint bar, which protects 8
    # The two strips differ (14 has Qty), yet some cells -- the plain row above
    # the words -- share a tile between the screens; each screen's hint words
    # take private tiles, or one screen's letters show on the other (the top of
    # 14's "Move" appeared 2px left of 8's). 14's strip used to be a generated
    # hint bar.
    ("madu_present", 12, 8, (14,)): [
        _hint((28, 175, 52, 184), "Move", (27, 173, 60, 188), 3, private=True),
        _hint((88, 175, 122, 184), "OK", (84, 173, 125, 188), 3, private=True),
        _hint((152, 175, 178, 184), "Back", (149, 173, 182, 188), 3, private=True),
        # the give-items confirm: わたすかず / のこり header and わたす / やめる
        # buttons were missed until 2026-09-26 (same words as present_equip 16)
        ((60, 13, 94, 19), "Item"),
        ((143, 11, 182, 20), "Give", "center", {"private": True}),
        ((202, 11, 226, 20), "Left", "center", {"private": True}),
        ((54, 130, 92, 141), "Give", "center", {"private": True}),
        ((164, 130, 202, 141), "Cancel", "center", {"private": True}),
    ],
    ("madu_present", 12, 14, (8,)): [
        # icons end x 24 / 82 / 141 / 205, lettering starts 30 / 87 / 145 / 210
        _hint((30, 176, 56, 184), "Move", (27, 173, 62, 188), 3, private=True),
        _hint((87, 176, 113, 184), "Qty", (84, 173, 118, 188), 3, private=True),
        _hint((145, 176, 181, 184), "OK", (143, 173, 186, 188), 2, private=True),
        _hint((210, 176, 238, 184), "Back", (207, 173, 243, 188), 3, private=True),
        ((60, 13, 94, 19), "Item"),
        ((142, 13, 176, 19), "Owned"),
        ((190, 13, 226, 19), "Give"),
    ],

    # Shop: four screens over one tile set (NCCG 9): NCSC 8 confirm (Yes/No), 11 the
    # buy list (Item/Price/Qty), 16 the empty board, 17 the two-column list (Smile
    # shop). Each carries the hint strip.
    ("madu_shop", 9, 11, (8, 16, 17)): [
        ((52, 33, 102, 39), "Item"),
        ((154, 33, 182, 39), "Price"),
        ((202, 33, 230, 39), "Qty"),
    ] + _SHOP_HINT,
    ("madu_shop", 9, 17, (8, 11, 16)): [
        ((50, 33, 104, 39), "Item"),
        ((165, 33, 205, 39), "Price"),
    ] + _SHOP_HINT,
    ("madu_shop", 9, 8, (11, 16, 17)): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
    ] + _SHOP_HINT,
    ("madu_shop", 9, 16, (8, 11, 17)): [
    ] + _SHOP_HINT,
    # Sell (equipment): 4 screens over one tile set (NCCG 17): NCSC 16 exit
    # confirm (Yes/No), 19 the bare list, 24 the sell-detail list (Item/Price,
    # Made By/Quality/Effect), 25 the R-toggled full description panel.
    ("madu_shop_equip", 17, 24, (16, 19, 25)): [
        ((5, 6, 60, 28), "Sell"),
        # the R-toggle tab: white face x 186-231, rows 5-19, then the orange R
        # box. The measured box took in both and cleared them to the green
        # (the "missing R hint" seen on hardware 2026-09-24)
        ((194, 7, 226, 16), "Effect", "center", {"box": (186, 5, 232, 20)}),
        ((55, 26, 140, 42), "Item"),
        ((142, 26, 215, 42), "Price"),
        # "Made By" is white text on its own solid-brown chip (5-66), directly
        # beside a blank white input field (67-144) that's part of the same
        # pill shape -- unlike Quality/Trait next to it, analyse()'s flood
        # fill from a plain seed here bridges into a neighbouring border
        # somewhere off-seed and returns a box spanning nearly the whole
        # screen width/height (0,110,146,145), which is what "blew up" into
        # a giant brown rectangle overlapping the maker-name text below.
        # Bypass analyse() with an explicit box tight to just the brown chip.
        ((5, 123, 66, 144), "Made By", "center",
         {"box": (5, 123, 66, 144), "bg": (156, 107, 16), "ink": (255, 255, 255)}),
        ((155, 122, 197, 142), "Quality"),
        ((3, 150, 38, 167), "Trait"),
    ] + _SHOP_HINT,
    ("madu_shop_equip", 17, 16, (19, 24, 25)): [
        ((58, 93, 90, 104), "Yes"),
        ((160, 93, 208, 104), "No"),
    ] + _SHOP_HINT,
    ("madu_shop_equip", 17, 19, (16, 24, 25)): [
        ((5, 6, 60, 28), "Sell"),
    ] + _SHOP_HINT,
    ("madu_shop_equip", 17, 25, (16, 19, 24)): [
        # the same R-toggle tab as NCSC 24's (face x 186-231, rows 5-19)
        ((194, 7, 226, 16), "Shop", "center", {"box": (186, 5, 232, 20)}),
        # this strip is Move + Back only: もどる sits where OK does on the others
        _SHOP_MOVE,
        _hint((84, 174, 124, 187), "Back", (84, 173, 125, 188), 4),
    ],

    ("madu_present_equip", 16): [
        ((196, 8, 220, 15), "Effect"),
    ] + _GIFT_INFO + [
        ((54, 130, 92, 141), "Give"),
        ((164, 130, 202, 141), "Cancel"),
    ],
    ("madu_present_equip", 19): [((196, 8, 220, 15), "Back")],
    # NCSC 24/25/26 show one hint strip over one tile set, but 25/26 have cells
    # pointing at duplicate tiles 24 does not use -- painted through 24 alone they
    # showed "UK" (part of the O missing). All three are painted here with the
    # *same* labels: a tile shared by the same cell on a sibling screen is painted
    # in place, so differing positions would overwrite each other. (This strip
    # used to be a generated hint bar.) Icons end 24 / 83 / 151.
    **{("madu_present_equip", 22, _n, tuple(m for m in (24, 25, 26) if m != _n)): [
        _hint((28, 175, 52, 184), "Move", (27, 173, 62, 188), 3),
        _hint((88, 175, 122, 184), "OK", (85, 173, 128, 188), 2),
        _hint((152, 175, 178, 184), "Back", (150, 173, 184, 188), 2),
    ] + _PE_TAB.get(_n, []) for _n in (24, 25, 26)},
    ("madu_present_equip", 27): [
        ((14, 104, 62, 110), "Made By", "left"),
        ((162, 104, 202, 110), "Quality", "left"),
        ((10, 129, 28, 135), "Eff."),
    ],

    # ---- Status screen (the old "Strength" menu): one page per tab --------
    ("madu_status", 13): [((194, 9, 224, 15), "Stats", "center", _TAB)],
    ("madu_status", 16): [
        ((194, 9, 224, 15), "Nutrition", "center", _TAB),
        ((112, 35, 150, 44), "Total"),
        ((168, 35, 216, 44), "Bonus"),
    ],
    ("madu_status", 19): [
        ((194, 9, 224, 15), "Hot Spring", "center", _TAB),
        # a two-line tab whose lettering fills it: boxes given by hand
        ((76, 32, 112, 38), "Diet", "center", {"box": (74, 28, 116, 41)}),
        ((76, 43, 112, 49), "Bonus", "center", {"box": (74, 41, 116, 52)}),
        ((200, 34, 238, 44), "To Next"),
    ],
    ("madu_status", 22): [
        ((194, 9, 224, 15), "Ramen", "center", _TAB),
        ((38, 150, 100, 156), "Spa Effect"),
    ] + _TIMER_BAR,
    ("madu_status", 25): [
        ((194, 9, 224, 15), "Artisan", "center", _TAB),
        ((38, 150, 100, 156), "Ramen Effect"),
    ] + _TIMER_BAR,
    ("madu_status", 28): [
        ((196, 9, 220, 15), "Level", "center", _TAB),
        ((88, 30, 164, 36), "Artisan's Path"),
        ((50, 84, 138, 90), "To Next Level", "left"),
        ((50, 149, 138, 155), "To Next Level", "left"),
    ],
}
