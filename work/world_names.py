"""English world (dungeon) names for bg/BGList.csv, keyed by the Japanese name.

The CSV's 10th column is the name shown on the dungeon prompt, the battle screen
and wherever #insfloor# is used. Applied by tools/build_patch.py. Keep names short
(the battle-screen name plate is ~90px wide).
"""

WORLDS = {
    "ほんまるじょう": "Main Keep", "かねまるじょう": "Bell Keep",
    "わくわくこうざん": "Thrill Mine", "デビルケイブ": "Devil Cave",
    "もりのいせき": "Forest Ruins", "てんくうのいせき": "Sky Ruins",
    "コスモワールド": "Cosmo World", "ブラックホール": "Black Hole",
    "もえもえかざん": "Fiery Volcano", "もうどくのぬま": "Poison Swamp",
    "ナイトキャッスル": "Night Castle", "まおうのしろ": "Demon's Castle",
    "ひみつとしょかん": "Secret Library", "まほうとしょかん": "Magic Library",
    "おかしのいえ": "Candy House", "こんがりハウス": "Toasty House",
    "ヘンテコくうかん": "Weird Space", "アベコベくうかん": "Reverse Space",
    "ロボファクトリー": "Robo Factory", "ネットフィールド": "Net Field",
    "ダークネスト": "Dark Nest", "しにがみのいえ": "Reaper's House",
    "おうけのはかば": "Royal Graves", "さびたろうごく": "Rusty Prison",
    "アイスワールド": "Ice World", "しょうにゅうどう": "Limestone Cave",
    "ドットフィールド": "Dot Field", "ヨルノセカイ": "Night World",
    "おためしテスト": "Trial Test",
    "おおきなねっこ": "Giant Roots", "しんぴのたき": "Mystic Falls",
    "ぐつぐつマグマ": "Bubbling Magma", "きょうさんのほり": "Acid Moat",
    "すんだみずたまり": "Clear Puddle", "いのちのたいぼく": "Tree of Life",
    "たそがれこおり": "Twilight Ice", "クリスタルランド": "Crystal Land",
    "まおうのへや": "Demon Lair",
}
