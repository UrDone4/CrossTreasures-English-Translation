# Building the patch from source

Most people should just download a patch from the Releases page. This is
for anyone who wants to change the translation or check the build.

## You need

* Python 3.8 or newer -- no extra packages.
* `xdelta3`, only to make an `.xdelta` file at the end.
* Your own dump of **Cross Treasures (Japan)**: 67,108,864 bytes, CRC32
  `44109EE3`, SHA-1 `4048b18f3e589e70e58391927c82ca87117d1337`.

The repository has no game data in it. The translation tables hold only the
English, and `art/` holds only the redrawn pixels of the battle art. The first
step restores the rest from your ROM.

## Steps

```sh
# 1. once: extract the ROM, restore the Japanese columns and the battle art
python tools/prepare.py "Cross Treasures (Japan).nds"

# 2. build (the second step takes 15-20 minutes)
python tools/gfx_labels.py apply work/gfx_out
python tools/bg_labels.py apply work/bg_out
python tools/build_patch.py "Cross Treasures (Japan).nds" CrossTreasures_T+En.nds

# 3. optional: the version without the built-in friends
CTRES_NO_FRIENDS=1 python tools/build_patch.py "Cross Treasures (Japan).nds" CrossTreasures_T+En_NoFriends.nds

# 4. optional: make patches
xdelta3 -e -9 -S djw -s "Cross Treasures (Japan).nds" CrossTreasures_T+En.nds my.xdelta
# ... and one for the "2CH" dump (SHA-1 87282a19...), if you have it too
python tools/patch_2ch.py "Cross Treasures (Japan).nds" "<2CH dump>.nds" CrossTreasures_T+En.nds my_2CH.xdelta
```

On Windows use `set CTRES_NO_FRIENDS=1` on its own line first.

## Where things are

| Path | What |
|---|---|
| `work/script_text.tsv` | the story and NPC dialogue |
| `work/ui_text.tsv`, `work/narc_text.tsv` | menu and screen text |
| `work/data_text.tsv` | items, equipment, monsters, skills, recipes, credits |
| `work/*.py` | names and lists the build reads (enemy names, world names, built-in friends ...) |
| `art/` | the hand-redrawn battle-triangle art (mask + painted pixels) |
| `tools/` | the build: extract, text fitting, background / sprite repainting, code patches |

Change the `english` column of a table and rebuild. To check your text fits,
run `python tools/scripttext.py check work/script_text.tsv` (and likewise
`uitext`, `narctext`, `datatext` with their tables) -- each must report 0
problems. Control tags such as `<c2<` ... `</c<` and `#insnumber#` must be kept.

More detail -- formats, engine notes, how each screen was repainted -- is on
the wiki.
