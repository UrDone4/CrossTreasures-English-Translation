"""The built-in friends: names, birthdays, classes and join order.

Used by tools/fake_friends_rom.py (the patched game) and `savefile.py
fakefriends`. Names: 1-6 letters each, A-Z / a-z only (what the ABC page of the
name keyboard can type). A save's real friends are kept and skip their slot.

FLOOR is each fake's best floor. The game already requires *your own* best
floor to reach a monument's floor before any friend counts (0x206CE4C), so
friends at the top floor (50) never hold you back -- each monument opens when
you get there yourself.
"""

# ---- THE USER'S CHOICES: fill in, in the order the friends should join ----
# One entry per friend, listed in JOIN ORDER (first joins at the start, the
# next at JOIN_FLOORS[1], ...).
#   birthday  (month, day) -- shown on their island; the star sign follows.
#             Placeholders picked 2026-09-25 (spread ~6 weeks apart, one per
#             sign); the user will finalise names and dates.
#   cls       "Fighter" / "Mage" / "Thief" / "Priest": friends 1-4 one of each,
#             friends 5-8 one of each (picked by Claude 2026-09-25 at the
#             user's request; the island shows class only through the gear)
#   look      (gender, face, hairstyle, hair colour, voice) -- the Character
#             Creator's choices, by name from the lists below (record
#             +0x1F..+0x23; decoded from the user's six test characters,
#             saves/New Character Saves). Placeholders, varied.
# Gear is not set here: each friend gets gear matching the floor they join at
# (fixed; it does not change later). None = not chosen yet (the friend then
# copies yours, as before).
FRIENDS = [
    # the user's list (2026-09-26): names, join order, gender, hair, class,
    # and six birthdays (Jon: Oct 29, user 2026-09-27). Hannah / Jess's dates
    # are Claude's picks for star-sign coverage (Aquarius / Gemini). Face and
    # voice: random, per the user.
    # Hair: Brown = Marron, Dark Brown = Choco, Black = Dark, Blonde = Gold;
    # Straight = Silky (さらさら), Short = Neat (さっぱり; the Creator has no
    # balding option), Curly = Curly.
    # Faces, hairstyles and voices are per gender (user, 2026-09-28: Hannah had
    # a beard -- 'Gentle' is a male face): see MALE / FEMALE below. The women
    # have no "curly" or "straight": curly -> Fluffy, straight -> Bangs.
    dict(name="Hannah", birthday=(2, 8), cls="Priest",
         look=('Female', 'Beauty', 'Fluffy', 'Marron', 'Beauty')),
    dict(name="Jess",   birthday=(6, 2), cls="Thief",
         look=('Female', 'Smiling', 'Bangs', 'Dark', 'Cute')),
    dict(name="Jon",    birthday=(10, 29), cls="Mage",
         look=('Male', 'Fresh', 'Neat', 'Marron', 'Wild')),
    dict(name="Grant",  birthday=(11, 21), cls="Fighter",
         look=('Male', 'Fresh', 'Silky', 'Choco', 'Cool')),
    dict(name="Tyson",  birthday=(4, 4), cls="Mage",
         look=('Male', 'Innocent', 'Silky', 'Marron', 'Wild')),
    dict(name="Landon", birthday=(7, 10), cls="Thief",
         look=('Male', 'Cool', 'Silky', 'Gold', 'Cool')),
    dict(name="Jason",  birthday=(7, 19), cls="Priest",
         look=('Male', 'Gentle', 'Silky', 'Marron', 'Wild')),
    dict(name="Tab",    birthday=(7, 20), cls="Fighter",
         look=('Female', 'Cute', 'Fluffy', 'Gold', 'Cute')),
]
# your own best floor at which friend 1..8 joins (Cross Medal: 1 / 4 / 8)
JOIN_FLOORS = [0, 5, 10, 15, 20, 25, 30, 35]
# the floor whose gear each friend wears: the first two start in basic
# (floor 0) gear, the rest progressively better by join floor (user)
GEAR_FLOORS = [0, 0] + JOIN_FLOORS[2:]
# ---------------------------------------------------------------------------

CLASSES = ("Fighter", "Mage", "Thief", "Priest")   # text/job_name.txt order
# Character Creator options, in the game's order (index = the record byte)
GENDERS = ("Male", "Female")
FACES = ("Fresh", "Cool", "Innocent", "Gentle", "Cute", "Beauty", "Smiling", "Sexy")
HAIRSTYLES = ("Neat", "Silky", "Spiky", "Curly", "Fluffy", "Bangs", "Braids", "Tail")
HAIR_COLOURS = ("Dark", "Choco", "Marron", "Gold", "Lemon", "Orange", "Apple",
                "Peach", "Grape", "Cosmos", "Marine", "Blue", "Lime", "Leaf",
                "Olive", "Silver")
VOICES = ("Cool", "Wild", "Cute", "Beauty")
LOOK_LISTS = (GENDERS, FACES, HAIRSTYLES, HAIR_COLOURS, VOICES)
# the Character Creator offers each gender only its half of these lists
# (a male face on a woman gives her a beard)
BY_GENDER = {
    "Male": {"face": FACES[:4], "hairstyle": HAIRSTYLES[:4], "voice": VOICES[:2]},
    "Female": {"face": FACES[4:], "hairstyle": HAIRSTYLES[4:], "voice": VOICES[2:]},
}


def look_bytes(f):
    """Record +0x1F..+0x23 for a friend (all 0 = the Creator's male default)."""
    lk = f.get("look")
    return bytes(lst.index(v) for lst, v in zip(LOOK_LISTS, lk)) if lk else bytes(5)
NAMES = [f["name"] for f in FRIENDS]
FLOOR = 50


def check():
    """Problems with FRIENDS, as a list of strings (empty = fine)."""
    out = []
    days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    for i, f in enumerate(FRIENDS):
        n = f["name"]
        if not (1 <= len(n) <= 6 and n.isascii() and n.isalpha()):
            out.append("%s: names are 1-6 letters A-Z" % n)
        b = f["birthday"]
        if b is not None and not (1 <= b[0] <= 12 and 1 <= b[1] <= days[b[0] - 1]):
            out.append("%s: no such date %r" % (n, b))
        lk = f.get("look")
        if lk is not None and (len(lk) != 5 or any(v not in lst for lst, v in zip(LOOK_LISTS, lk))):
            out.append("%s: look is (gender, face, hairstyle, hair colour, voice) "
                       "from GENDERS / FACES / HAIRSTYLES / HAIR_COLOURS / VOICES" % n)
        if lk is not None and len(lk) == 5 and lk[0] in BY_GENDER:
            allowed = BY_GENDER[lk[0]]
            for field, value in (("face", lk[1]), ("hairstyle", lk[2]), ("voice", lk[4])):
                if value not in allowed[field]:
                    out.append("%s: %s %r is not a %s option (%s)"
                               % (n, field, value, lk[0], ", ".join(allowed[field])))
        if f["cls"] is not None and f["cls"] not in CLASSES:
            out.append("%s: class must be one of %s" % (n, ", ".join(CLASSES)))
    if len(JOIN_FLOORS) != 8 or any(not 0 <= j <= 50 for j in JOIN_FLOORS):
        out.append("JOIN_FLOORS: eight floors, 0-50")
    for half in (FRIENDS[:4], FRIENDS[4:]):
        got = [f["cls"] for f in half]
        if None not in got and sorted(got) != sorted(CLASSES):
            out.append("%s: need one of each class" % "/".join(f["name"] for f in half))
    return out

# World seeds (record +0..+7, lo/hi words): the game builds a friend's whole
# world from this (0x206ADB0). These eight were searched (seeded search,
# reproducible: tools/fake_friends_rom.py search) so that between them the
# friends' worlds cover every theme option of every 5-floor block in
# world_decide.dat -- all 28 dungeon themes, so every item source is on some
# friend's world. Themes per block (BGList row) are listed beside each seed.
# Order (2026-09-28, user: "move the worlds so the quests progress naturally"):
# the six companion arcs name 15 dungeons by floor band ("the Limestone Cave
# that appears on 1F-5F"...); the seeds are ordered so every one of them is
# on a friend who has joined by floor 15, and the two first-job dungeons on
# floors 1-5 (Royal Graves: Mint; Limestone Cave: Yomogi, Saffron) by
# floor 5. Same eight seeds, so the 28-theme coverage is unchanged.
WORLD_SEEDS = [
    (0xEBC08B9E, 0x17FCEE3D),   # 22 8 18 13 10 23 15  1  7 11  Hannah: Royal Graves 1-5, Robo Factory, Magic Library, Rusty Prison, Black Hole
    (0xE4F9B0D5, 0x102690B2),   # 25 14 16 20 10 12 17 27 21 11  Jess:   Limestone Cave 1-5, Candy House, Weird Space, Dark Nest, Reverse Space
    (0xEB828726, 0xCDB99178),   # 2  0  6 26 10 24 19  5  3 11  Jon:    Cosmo World, Dot Field
    (0x9D25DA53, 0x605EAA8B),   # 4 14 16 20 10  9 17 27 21 11  Grant:  Poison Swamp (a 2nd Candy House, Weird Space...)
    (0x636E8A6D, 0x14E0D539),   # 25 0  6 26 10 12 19  5  3 11
    (0x45BF8875, 0xA11C0859),   # 2 14 16 20 10 24 17 27 21 11
    (0xA66B2B92, 0xA62F12D0),   # 4  8 18 13 10  9 15  1  7 11
    (0xA6B8CBA5, 0xDDAA04A9),   # 22 0  6 26 10 23 19  5  3 11
]
