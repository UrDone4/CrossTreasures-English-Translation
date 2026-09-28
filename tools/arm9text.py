#!/usr/bin/env python3
"""Strings that live in the ARM9 binary rather than in a data file.

Most text is in the filesystem, but a handful of short strings are literals in
the ARM9 image (uncompressed here, at ROM offset 0x4000). They are edited in
place: the English must fit the original slot, and the original bytes are checked
first so a wrong offset or a different ROM revision is refused, not corrupted.

Found so far (all display-only -- traced in the disassembly):

* The skill screen's *Target* names, a 3-entry pointer table at RAM 0x20A56B0:
  じぶん / なかま / モンスター. `ldr r0,=0x20A56B0 ; ldr r0,[r0,r2,lsl #2]` feeds a
  draw-string call.
* The basic-action names, a class x 2 pointer table at RAM 0x20A56BC read by the
  skill-name getter at 0x2070130: for indices 0-1 it returns the table entry (the
  action, then its power version) and for 2+ it falls through to skill_name.txt.
  Per class: soldier アタック / パワーアタック, magic アタック / マナトール, thief
  アタック / クイックアクト, priest アタック / パワースタンプ.

* The Character Creator's value names (style, gender, voice, face, hairstyle, hair
  colour): three pointer tables at RAM 0x20A2E94 / 0x20A2ED8 / 0x20A30E4.

* The Island Art screen's (Arton) category tabs and status messages: overlay 11,
  loaded at RAM 0x20CC5E0 (ROM offset = 0xDC000 + (ram - 0x20CC5E0)). The tabs sit
  in tiny fixed slots (4/8/12 bytes: `ceil((original_JP_bytes + 1) / 4) * 4`), too
  small for some English words -- see REPOINTS below for how き (Tree) was fixed
  properly instead of abbreviated.

## When a slot is too small: repoint instead of abbreviating

Some of these strings are read through a **pointer table**, not at a fixed
address: a 4-byte RAM pointer elsewhere in the same file is dereferenced to find
the text. き's tab label on the Island Art screen was the first case found --
its own slot only had 3 usable bytes (too small for "Tree"/"Trees"), but the two
pointers that lead to it (found by searching the file for the little-endian
encoding of its RAM address, which turned up exactly once each, sitting in an
obvious consecutive array of similar pointers -- a strong sign it *is* a pointer
table and not a coincidental byte match) can be redirected anywhere else in the
same loaded region. That "anywhere else" doesn't need new space: this file
already has strings sitting in slots much bigger than they use (round up to the
next 4 bytes doesn't happen for a *dynamic* max-length field the way it does for
a single fixed string), and the tail of one of those is free, zeroed, and
unread once the shorter string's own NUL is hit. `REPOINTS` below reuses 16 of
the ~99 spare bytes at the end of the "You don't own a Monster Pet" message's
128-byte slot this way.

To find whether a too-small string is repointable:

1. Compute its RAM address: `region_ram_base + (rom_offset - region_rom_base)`
   (the region's own base pair -- ARM9 is RAM 0x2000000 = ROM 0x4000; an
   overlay's pair is in the overlay table, ROM header 0x50, 32 bytes/entry:
   `id, ram, size, bss, sinit_start, sinit_end, file_id, compressed_size_and_flag`).
2. `struct.pack("<I", that_address)` and search the whole ROM for it. One hit
   (or a few, if the string is shown more than once) sitting next to other
   4-byte values that also decode to plausible nearby RAM addresses --
   pointer table, repointable. No hits -- the string is read at a fixed
   address instead (inline, not a pointer); a repoint isn't possible, and the
   English has to fit the original slot or a shorter/approximate word is used.
3. Find spare bytes to repoint *into*: look for a string whose slot capacity
   is well beyond `len(english)+1` elsewhere in the *same loaded region*
   (repointing across regions doesn't work -- the pointer is a plain RAM
   address, and another region may not even be loaded at the same time).
   Verify the tail is all zero before writing into it (`REPOINTS` checks this
   at build time, the same way `STRINGS` checks its own original bytes), and
   that nothing else already points there (a stray reference would mean it is
   not actually free).

    arm9text.py check <rom>      verify every original string is where expected
"""

import os
import struct
import sys

ARM9_ROM_OFFSET = 0x4000

# (rom file offset, original text, English, slot bytes incl. NUL)
STRINGS = [
    (0xA96E0, "なかま",           "Allies",      8),
    (0xA96E8, "じぶん",           "Self",        8),
    (0xA9750, "モンスター",       "Monster",     12),
    (0xA96F0, "アタック",         "Attack",      12),   # priest
    (0xA96FC, "アタック",         "Attack",      12),   # soldier
    (0xA9720, "アタック",         "Attack",      12),   # magic
    (0xA9738, "アタック",         "Attack",      12),   # thief
    (0xA9744, "マナトール",       "Mana Drain",  12),
    (0xA9778, "クイックアクト",   "Quick Act",   16),
    (0xA9788, "パワーアタック",   "Power Attack", 16),
    (0xA9798, "パワースタンプ",   "Power Stamp", 16),
    # Character Creator confirm message (in overlay 8; stored uncompressed in the ROM)
    (0xD8F58, "このキャラクターでいいですか？", "Is this character OK?", 32),
    (0xD8EE0, "データをセーブしています", "Saving data...", 28),
    (0xD8EFC, "セーブがかんりょうしました", "Save complete!", 28),
    # character creator values (pointer tables 0x20A2E94 / 0x20A2ED8 / 0x20A30E4)
    (0xA6F68, "おとこ", "Male", 8),
    (0xA6F40, "おんな", "Female", 8),
    (0xA6F70, "クール", "Cool", 8),
    (0xA700C, "ワイルド", "Wild", 12),
    (0xA7054, "キュート", "Cute", 12),
    (0xA70C4, "ビューティー", "Beauty", 24),
    (0xA70A8, "ファイター", "Fighter", 12),
    (0xA6F50, "メイジ", "Mage", 8),
    (0xA6F90, "シーフ", "Thief", 8),
    (0xA709C, "プリースト", "Priest", 12),
    (0xA7078, "さわやか", "Fresh", 12),
    (0xA6F28, "クール", "Cool", 8),
    (0xA7084, "むじゃき", "Innocent", 12),
    (0xA6FD0, "やんわり", "Gentle", 12),
    (0xA6FE8, "キュート", "Cute", 12),
    (0xA70B4, "ビューティー", "Beauty", 16),
    (0xA6FF4, "にっこり", "Smiling", 12),
    (0xA7000, "おいろけ", "Sexy", 12),
    (0xA7090, "さっぱり", "Neat", 12),
    (0xA7018, "さらさら", "Silky", 12),
    (0xA7024, "つんつん", "Spiky", 12),
    (0xA706C, "ぐりぐり", "Curly", 12),
    (0xA7060, "ふんわり", "Fluffy", 12),
    (0xA703C, "ぱっつん", "Bangs", 12),
    (0xA6F38, "おさげ", "Braids", 8),
    (0xA6F78, "しっぽ", "Tail", 8),
    (0xA6F48, "ダーク", "Dark", 8),
    (0xA6F18, "チョコ", "Choco", 8),
    (0xA6F30, "マロン", "Marron", 8),
    (0xA6FA0, "ゴールド", "Gold", 12),
    (0xA6F20, "レモン", "Lemon", 8),
    (0xA6FAC, "オレンジ", "Orange", 12),
    (0xA6FB8, "アップル", "Apple", 12),
    (0xA6F80, "ピーチ", "Peach", 8),
    (0xA6FC4, "グレープ", "Grape", 12),
    (0xA6FDC, "コスモス", "Cosmos", 12),
    (0xA6F98, "マリン", "Marine", 8),
    (0xA6F58, "ブルー", "Blue", 8),
    (0xA6F60, "ライム", "Lime", 8),
    (0xA6F88, "リーフ", "Leaf", 8),
    (0xA7030, "オリーブ", "Olive", 12),
    (0xA7048, "シルバー", "Silver", 12),
    # Island Art screen (Arton), overlay 11 -- category tabs (each appears twice)
    # and three status/confirm messages. き (Tree) is not here -- its slot was too
    # small, see REPOINTS.
    (0x10690C, "ふね", "Ship", 8),
    (0x106914, "はな", "Flower", 8),
    (0x10691C, "はな", "Flower", 8),
    (0x106924, "ふね", "Ship", 8),
    (0x10692C, "デッキ", "Deck", 8),
    (0x106934, "みなと", "Port", 8),
    (0x10693C, "みなと", "Port", 8),
    (0x106944, "デッキ", "Deck", 8),
    (0x10694C, "ポスト", "Mailbox", 8),
    (0x106954, "ポスト", "Mailbox", 8),
    (0x10695C, "モンペット", "Monster Pet", 12),
    (0x106968, "モンペット", "Monster Pet", 12),
    (0x106974, "アートを　いらいします", "Request the art", 24),
    (0x1069A8, "いらいせず　しゅうりょうします", "Finish without a request", 40),
    (0x106A00, "なし", "None", 32),
    (0x106A20, "モンペットを　かっていません", "You don't own a Monster Pet", 128),
    (0x106C04, "よろしいですか　？", "Is this OK?", 28),
    # The generic dungeon-floor pickup HUD notice (icon + item name/gold amount,
    # e.g. "Cozy Feather obtained!" / "40G obtained!") is assembled at runtime
    # from a printf-style template, not a script/text/ event -- found by
    # searching the raw ARM9 image for "てにいれた" outright after every
    # script file containing it turned out to be an unrelated one-off event
    # (quest rewards, a specific boss's dialogue, a secret-password minigame).
    # Two neighbouring entries share this table: "%s%s" + this suffix (icon-tag
    # substitution followed by an amount/name, e.g. item pickups and gold), and
    # "%s" + a generic all-purpose "アイテムをてにいれた！" (used when no specific
    # name is substituted). English keeps the same trailing-suffix shape --
    # "%s%s"/"%s" prepend the substituted text, so " obtained!"/"Item obtained!"
    # reads correctly without reordering.
    (0xACCFC, "をてにいれた！", " obtained!", 16),
    (0xACD10, "アイテムをてにいれた！", "Item obtained!", 24),
    # Cook menu category names, overlay 11 (the SAME overlay as the Island
    # Art section above -- island-activity screens apparently share one
    # module). The Cook category-name pill kept showing Japanese even after
    # translating the seemingly-matching loose file
    # data_general/cook_type_name.txt -- confirmed on hardware, twice, that
    # that file's translation has no effect. Root cause found by repeating
    # the same "search the raw overlay/ARM9 image directly" method used for
    # the item/gold pickup notice above: found a plain fixed-8-byte-stride
    # array of these exact words sitting in overlay 11's own decompressed
    # data (ROM offset 0xDC000 + relative offset; a 4-entry RAM-pointer table
    # immediately precedes it in the file, one per some subset of these
    # words, not fully mapped out). This array -- not the loose text file --
    # is what's actually read for the pill. すいーつ (Sweets) fills its own
    # 8 bytes exactly with no in-slot NUL; the verification's "text + one
    # trailing NUL" check still passes because the next byte (start of
    # unused trailing padding) happens to be zero already.
    (0x1067EC, "にく", "Meat", 8),
    (0x1067F4, "なし", "None", 8),
    (0x1067FC, "さかな", "Fish", 8),
    (0x106804, "サラダ", "Salad", 8),
    (0x10680C, "パスタ", "Pasta", 8),
    (0x106814, "スイーツ", "Sweets", 8),
    # Cooking taste ratings: 4 records of {id, char name[12], chance, bonus%}
    # at RAM 0x20A7090, registered as {table, 4} by 0x207F1F4. The names
    # are read inline, so 11 bytes max. Same ladder as ev100006's results.
    (0xAB094, "げきウマ", "Delicious!", 12),
    (0xAB0AC, "ウマウマ", "Tasty!", 12),
    (0xAB0C4, "マズマズ", "Not great", 12),
    (0xAB0DC, "げきマズ", "Awful...", 12),

    # --- 2026-09-24 pointer-reference scan (see arm9_scan in README's
    # Outstanding item 1) -- 78 confirmed-live strings across ARM9 and
    # overlays 0/3/6/8/10/11, found the way this docstring describes:
    # scan every region for a NUL-terminated Shift-JIS run, then keep only
    # the ones whose RAM address appears as a 4-byte-aligned pointer literal
    # somewhere in the ROM. Of 84 raw hits, 1 was code misdecoding as valid
    # Shift-JIS by coincidence (discarded) and 6 are fragments a separate
    # draw call splices an item/skill name into (the exact concatenation
    # order isn't confirmed yet -- see README, left untranslated on purpose
    # rather than guessed at and risking garbled output); the rest are here.
    # Birthday zodiac signs (Status/profile screen). Read through a 12-entry
    # month-ordered pointer table at RAM 0x209C2C0 (ROM 0xA02C0) by the
    # birthday formatter at 0x204A1A4, which appends "%sざ" (0xA56DC, below).
    # Full names: all fit their own slot except Capricorn and Sagittarius,
    # which are repointed (see REPOINTS); their slots keep a short form only
    # so no Japanese is left behind. うお (Pisces) was missed by the scan --
    # the 4 bytes before it are a pointer with no separating NUL.
    (0xA54F4, "うお", "Pisces", 8),
    (0xA54FC, "しし", "Leo", 8),
    (0xA5504, "やぎ", "Cap", 8),       # repointed -> "Capricorn"
    (0xA550C, "いて", "Sag", 8),       # repointed -> "Sagittarius"
    (0xA5514, "かに", "Cancer", 8),
    (0xA551C, "おとめ", "Virgo", 8),
    (0xA5524, "おうし", "Taurus", 8),
    (0xA552C, "ふたご", "Gemini", 8),
    (0xA5534, "さそり", "Scorpio", 8),
    (0xA553C, "みずがめ", "Aquarius", 12),
    (0xA5548, "おひつじ", "Aries", 12),
    (0xA5554, "てんびん", "Libra", 20),
    # Birthday line, same formatter: sprintf(a, "%sがつ", month) then
    # sprintf(b, "%s　%sにち", a, day), then sprintf(c, "%sざ", sign). The
    # digits come from a full-width table (0x20A08C8), so this reads "３／１４".
    (0xA56C8, "%sがつ", "%s／", 8),
    (0xA56D0, "%s　%sにち", "%s%s", 12),
    (0xA56DC, "%sざ", "%s", 8),
    # Memo / Medallion number labels
    (0xA56EC, "メモ%s", "Memo %s", 8),
    (0xA56F4, "メダリオン%s", "Medallion %s", 16),
    # Island-activity hub menu labels (Secret Spell appears twice, once for
    # the hub icon and once for the submenu header)
    (0xA5708, "りょうり", "Cooking", 12),
    (0xA5D78, "つけものや", "Pickle Shop", 12),
    (0xA5D90, "しまのおみせ", "Island Shop", 16),
    (0xA5DF0, "ひみつのじゅもん", "Secret Spell", 20),
    (0xA5E2C, "いろいろなせかい", "Various Worlds", 20),
    (0xA5E7C, "いっしょにクエスト", "Quest Together", 20),
    (0xACD28, "ひみつのじゅもん", "Secret Spell", 28),
    # Yes / No / Start
    (0xA6578, "はい", "Yes", 8),
    (0xA6580, "いいえ", "No", 8),
    (0xA6588, "スタート ！", "Start!", 12),
    # Item-pickup HUD suffix -- a SECOND, separately-addressed copy of the
    # already-translated 0xACCFC/0xACD10 pair above; almost certainly the
    # actual code path behind the long-open item-pickup issue (see README).
    # The pickup HUD (ARM9 0x205BE48) draws, from the message table at RAM
    # 0x20A2818: item name + table[1] "を" + ("%dこ" if more than one) +
    # table[2] "てにいれた ！"; gold is "%dＧ" + table[7]. "を" and "%dこ"
    # were the Japanese still showing after the item name.
    (0xA6574, "を", "", 4),
    (0xA6880, "%dこ", " x%d", 8),
    (0xA6594, "てにいれた！", " obtained!", 16),
    (0xA65A4, "てにいれた ！", " obtained!", 16),
    (0xA65B4, "をてにいれた！", " obtained!", 16),
    # Skill-teaching popup (ARM9-level, separate from the dojo script text)
    (0xA65D4, "すでにならっている！", "Already learned!", 24),
    (0xA6634, "おしえてもらえなかった！", "Couldn't be taught it!", 28),
    (0xA6650, "がつかえるようになった！", " can now be used!", 28),  # skill name precedes
    # Ally-defeated messages (fragment: ally name precedes, so English's
    # name-first word order lines up the same way)
    (0xA65EC, "は　ちからつきた…。", " has fallen...", 24),
    (0xA666C, "たちは　ちからつきた…。", " and friends have fallen...", 28),
    # Dungeon time-limit / Treasure Defense goal messages
    (0xA6688, "ざんねん　じかんぎれ・・・", "Too bad... Time's up...", 28),
    (0xA66C0, "じかんないに　てきをたおし", "Defeat enemies in time,", 28),
    (0xA66DC, "すべての　ボスを　たおせ ！", "and defeat every boss!", 28),
    (0xA66F8, "なにもみつからなかった・・・", "Nothing was found...", 32),
    (0xA6718, "たからばこ　を　まもりきれ ！", "Protect the treasure chest!", 32),
    (0xA6738, "ざんねん　たおせなかった・・・", "Too bad, couldn't defeat it...", 32),
    (0xA6758, "もくてきを　たっせい　しました ！", "Objective achieved!", 36),
    (0xA677C, "ざんねん　まもりきれなかった・・・", "Too bad... couldn't protect it...", 36),
    (0xA67A0, "トレジャーディフェンス　せいこう ！", "Treasure Defense success!", 36),
    # Same HUD, id 0x253: a name (RAM 0x20B4002) + table[11] or table[12]
    # (chosen by 0x2024D2C), so English must read name-first. table[10]
    # "このとびらは" is not drawn by this routine; translated for completeness.
    (0xA65C4, "このとびらは　", "This door", 16),
    (0xA6604, "　にしか　ひらけない", " alone can open it.", 24),
    (0xA661C, "　ひとりで　きてくれ", ", come alone.", 24),
    # ids 0x242-0x250: buff name (0x205D3CC) + table[25]; ids 0x201-0x241
    # draw table[25] on its own.
    (0xA66A4, "　の　こうかがなくなった。", " wore off.", 28),
    # Shop / gift messages
    (0xAAE4C, "ほんとうにうりますか？", "Really sell it?", 32),
    (0xAB238, "ほんとうにうりますか？", "Really sell it?", 24),
    (0xAB250, "このアイテムは　わたせません！", "You can't give this item!", 32),
    (0xAB270, "これいじょうは　わたせません！", "You can't give any more!", 40),
    # Ending credits thank-you message (four consecutive fragments read as
    # one flowing message, not independently)
    (0xAD1C4, "あそんでくれて　ありがとう ！", "Thank you for playing!", 32),
    (0xAD1E4, "みなさんの　すばらしい", "We hope you all find", 24),
    (0xAD1FC, "たからものが　みつかりますように ！", "a wonderful treasure of your own!", 36),
    (0xAD220, "クロストレジャーズ　スタッフ　いちどう", "- The whole Cross Treasures staff", 64),
    # Download-play "communicating" messages, overlay 10
    (0xDBDCC, "データをつうしんちゅうです。", "Communicating data...", 32),
    (0xDBDEC, "しばらくおまちください。", "Please wait a moment.", 28),
    # Workshop (overlay 11) -- item name precedes both, same as the skill-
    # learned message above
    # Workshop confirm (overlay 11, 0x20D4134): sprintf("%s%s", item name,
    # table[mode]) with the pointer table at RAM 0x20F6474 = {つくります,
    # きたえます}, then table[-1] (the save question) on the second line.
    (0x105E9C, "を　つくります", " will be made.", 16),
    (0x105EAC, "に　きたえます", " will be upgraded.", 24),
    (0x105EE0, " セーブされますが　よろしいですか　？", "The game will be saved. OK?", 40),
    (0x105FB0, "しょくにんＥＸＰ\n%d　をゲットした　！", "Artisan EXP\nGot %d!", 40),
    # Equipment restyle confirm messages, overlay 11 -- category names match
    # the established Equipment-screen slot names (work/ui_translations.py)
    (0x1061F4, "盾を\n変更します", "Change\nShield", 16),
    (0x106204, "鎧を\n変更します", "Change\nArmor", 16),
    (0x106214, "指輪を\n変更します", "Change\nRing", 20),
    (0x106228, "武器を\n変更します", "Change\nWeapon", 20),
    (0x10623C, "首飾りを\n変更します", "Change\nNecklace", 20),
    (0x106250, "足防具を\n変更します", "Change\nBoots", 20),
    (0x106264, "耳飾りを\n変更します", "Change\nEarring", 20),
    (0x106278, "頭部防具を\n変更します", "Change\nHead", 28),
    (0x106294, "なし", "None", 24),
    (0x1062AC, "このアイテムは\n装備できます", "This item\ncan be equipped.", 28),
    (0x1062C8, "このアイテムは\n装備できません", "This item\ncan't be equipped.", 32),
    (0x1062E8, "この部位には\n何も装備しません", "Leave this\nslot empty.", 40),
    (0xFF1B4, "そうびなし", "No Equipment", 32),
    # Class names, overlays 3/6/8 -- three separate copies, same as the
    # skill-name triangle labels elsewhere in this project
    (0xC3BD4, "メイジ", "Mage", 8),
    (0xC3BDC, "シーフ", "Thief", 8),
    (0xC3BEC, "ファイター", "Fighter", 12),
    (0xC3BF8, "プリースト", "Priest", 12),
    (0xCBDEC, "メイジ", "Mage", 8),
    (0xCBDF4, "シーフ", "Thief", 8),
    (0xCBDFC, "ファイター", "Fighter", 12),
    (0xCBE20, "プリースト", "Priest", 12),
    (0xCBECC, "なまえ：%s", "Name: %s", 12),
    (0xD942C, "メイジ", "Mage", 8),
    (0xD9434, "シーフ", "Thief", 8),
    (0xD9444, "プリースト", "Priest", 12),
    (0xD9450, "ファイター", "Fighter", 12),
]


# A too-small inline slot's own text is read through a pointer elsewhere in the
# same loaded region (RAM base pairs are ARM9 = (0x4000, 0x2000000); overlay 11
# used here is (0xDC000, 0x20CC5E0), see the overlay table at ROM header 0x50).
# Each entry: the pointer locations and the RAM address each must currently
# hold (one pointer per place the string is shown -- found by searching the ROM
# for that address's little-endian bytes, see "When a slot is too small" above),
# the new English text, where to put it (spare, unread padding at the tail of
# some other string's oversized slot in the *same* region), and how many bytes
# there must be free from that point (a safety margin, checked as all-zero
# before writing -- keep this comfortably above len(text)+1).
REPOINTS = [
    {
        "region": (0xDC000, 0x20CC5E0),   # overlay 11
        "pointers": [(0x1003E4, 0x20F6EE4), (0x100400, 0x20F6EE8)],  # き, both copies
        "text": "Trees",
        "home": 0x106A50,   # spare tail of the "You don't own a Monster Pet" slot
        "reserve": 16,
    },
    # Zodiac names too long for their 8-byte slots; the only pointer to each
    # is its entry in the month table at RAM 0x209C2C0 (ROM 0xA02C0).
    {
        "region": (0x4000, 0x2000000),    # ARM9
        "pointers": [(0xA02C0, 0x20A1504)],   # やぎ, January entry
        "text": "Capricorn",
        "home": 0xAAE5C,    # spare tail of the 32-byte "Really sell it?" slot
        "reserve": 16,
    },
    {
        "region": (0x4000, 0x2000000),    # ARM9
        "pointers": [(0xA02EC, 0x20A150C)],   # いて, December entry
        "text": "Sagittarius",
        "home": 0xA70CC,    # spare tail of the 24-byte "Beauty" slot
        "reserve": 16,
    },
]


# Instruction patches: (ROM offset, original bytes, new bytes, why). Each is
# checked against the original before it is written, like STRINGS.
CODE = [
    # The name-entry keyboard opens on page 0 (hiragana). Its constructor
    # (ARM9 0x2074E54..) does `mov r0, #0; str r0, [r5, #0x58]` -- +0x58 is the
    # current page (0 hiragana, 1 katakana, 2 ABC, 3 symbols; the switch at
    # 0x2075130 builds the page object from it, L/R step it through 0x2075238).
    # `mov r0, #2` opens it on ABC instead.
    (0x78EC0, bytes.fromhex("0000a0e3"), bytes.fromhex("0200a0e3"),
     "name keyboard opens on the ABC page"),
    # The Password screen (overlay 8, ROM 0xCC400 = RAM 0x20CC5E0) has its own
    # keyboard copy, page at +0x54 (switch 0x20D7B1C over pages 0-3; L/R via
    # 0x20D7C28). Constructor 0x20D76xx:  mov r1,#0 / str r1,[r5,#0x54] /
    # mov r0,#1 / str r0,[r5,#0x48] / add r0,r5,#0x98 / mov r2,#0x13 /
    # str r1,[r5,#0x88] / bl memset(r0, r1, r2) ... then memset(+0x8C, 0, 12).
    # r1 is also the first memset's fill value, so: r1 = 2 for the page store,
    # the +0x88 store becomes `mov r1,#0` (fill back to 0), and the last
    # memset starts at +0x88 (16 bytes) so +0x88 is still zeroed.
    (0xD756C, bytes.fromhex("0010a0e3"), bytes.fromhex("0210a0e3"),
     "password keyboard: constructor page = 2 (ABC)"),
    (0xD7584, bytes.fromhex("881085e5"), bytes.fromhex("0010a0e3"),
     "password keyboard: r1 back to 0 for the memsets (+0x88 zeroed below)"),
    (0xD75DC, bytes.fromhex("8c0085e2"), bytes.fromhex("880085e2"),
     "password keyboard: memset from +0x88 ..."),
    (0xD75E4, bytes.fromhex("0c20a0e3"), bytes.fromhex("1020a0e3"),
     "password keyboard: ... 16 bytes (+0x88..+0x97)"),
    # its reset (0x20D7A08; the r1 there is reloaded right after the store)
    (0xD78E4, bytes.fromhex("0010a0e3"), bytes.fromhex("0210a0e3"),
     "password keyboard: reset page = 2 (ABC)"),
]


def apply_code(data):
    for off, old, new, _why in CODE:
        have = bytes(data[off:off + len(old)])
        if have != old:
            raise SystemExit("ARM9 code at 0x%X is %s, not %s -- wrong ROM "
                             "revision?" % (off, have.hex(), old.hex()))
        data[off:off + len(new)] = new
    return len(CODE)


def apply(data):
    """Patch `data` (a bytearray of the whole ROM) in place; returns the count."""
    n = 0
    for off, jp, en, slot in STRINGS:
        want = jp.encode("shift_jis") + b"\0"
        have = bytes(data[off:off + len(want)])
        if have != want:
            raise SystemExit("ARM9 string at 0x%X is not %r (found %r) -- wrong "
                             "ROM revision?" % (off, jp, have))
        blob = en.encode("shift_jis")
        if len(blob) + 1 > slot:
            raise SystemExit("%r does not fit its %d-byte slot" % (en, slot))
        data[off:off + slot] = blob + b"\0" * (slot - len(blob))
        n += 1
    n += apply_repoints(data)
    n += apply_code(data)
    return n


def apply_repoints(data):
    n = 0
    for r in REPOINTS:
        rom_base, ram_base = r["region"]
        home, reserve = r["home"], r["reserve"]
        blob = r["text"].encode("shift_jis") + b"\0"
        if len(blob) > reserve:
            raise SystemExit("%r (%d bytes) does not fit its %d-byte reserve"
                             % (r["text"], len(blob), reserve))
        have = bytes(data[home:home + reserve])
        if have != b"\0" * reserve:
            raise SystemExit("repoint target 0x%X is not all zero (found %r) -- "
                             "not actually free, or already patched?" % (home, have))
        new_ram = ram_base + (home - rom_base)
        for ptr_off, old_ram in r["pointers"]:
            have_ptr = struct.unpack_from("<I", data, ptr_off)[0]
            if have_ptr != old_ram:
                raise SystemExit("pointer at 0x%X is 0x%X, not 0x%X -- wrong ROM "
                                 "revision?" % (ptr_off, have_ptr, old_ram))
            struct.pack_into("<I", data, ptr_off, new_ram)
        data[home:home + len(blob)] = blob
        n += 1
    return n


def main(argv):
    if len(argv) < 3 or argv[1] != "check":
        print(__doc__)
        return 1
    data = bytearray(open(argv[2], "rb").read())
    print("%d strings verified and patched in memory" % apply(data))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
