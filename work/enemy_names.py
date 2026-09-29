#!/usr/bin/env python3
"""English names for the enemy tables (monster / boss / object param .dat).

Keyed by the exact Japanese string, applied to every record that uses it.
Hard limit is 16 bytes per name, which is 16 ASCII characters.

Naming conventions
    Invented creature families are transliterated so their relationships stay
    visible: Punion, Mooton, Oinkton, Rex, Tauros, Moena, Rockn.
    デカ / チビ / ミニ  ->  Big / Little / Mini
    Ｓ suffix on a boss marks the stronger rematch; rendered as a " S" suffix.
"""

MONSTERS = {
    # -- kana/kanji descriptive names ------------------------------------
    "あんこくのめ": "Dark Eye", "いだいなるもの": "Great One",
    "いちずなひとみ": "Devoted Eye", "おおぴよこ": "Big Chick",
    "からくりマドウ": "Clockwork Mage", "きれいなひとみ": "Pretty Eye",
    "くろぶたさん": "Mr. Black Pig", "こいするひとみ": "Loving Eye",
    "こぴよこ": "Baby Chick", "ごくじょうダケ": "Prime Mushroom",
    "しょきがた": "Early Model", "じゃしんのめ": "Evil God Eye",
    "すなのぬし": "Sand Lord", "どくかぶと": "Venom Beetle",
    "なぞダケ": "Mystery Shroom", "ひとくいボーン": "Maneater Bone",
    "ぴよこ": "Chick", "ふしぎなめ": "Strange Eye",
    "ふしぎダケ": "Odd Mushroom", "ふしぎラビット": "Odd Rabbit",
    "もうどくかぶと": "Deadly Beetle", "やみしいたけ": "Dark Shiitake",
    "やみのしんかん": "Dark Priest", "やみのていおう": "Dark Emperor",
    "ゆきやまさん": "Mt. Snowy",
    # -- A ---------------------------------------------------------------
    "アソザーン": "Asozan", "アックスバード": "Axe Bird",
    "アリスラビット": "Alice Rabbit", "イナズマブートン": "Bolt Oinkton",
    "イビルソーサラー": "Evil Sorcerer", "イビルボール": "Evil Ball",
    "イベリコぶたさん": "Iberico Pig", "エイリアン": "Alien",
    "エイリアンベビー": "Alien Baby", "エイリアンマザー": "Alien Mother",
    "エンコーダー": "Encoder", "オチムシャ": "Fallen Samurai",
    "オニ": "Ogre", "オークデーモン": "Orc Demon",
    # -- K ---------------------------------------------------------------
    "カッチーナ": "Katchina", "ガイアロックン": "Gaia Rockn",
    "ガイコツけんし": "Bone Swordsman", "ガイコツキッド": "Skeleton Kid",
    "ガイコツロード": "Skeleton Lord", "ガッチリーナ": "Gatchirina",
    "キノコーン": "Mushcorn", "キュオーン": "Mini Mooton",
    "キリマンジャーロ": "Kilimanjaro", "キングデーモン": "King Demon",
    "キングプニオン": "King Punion", "ギャオーン": "Big Mooton",
    "ギャラクシャーク": "Galaxy Shark", "ギュオガール": "Moo Girl",
    "ギュオクイーン": "Moo Queen", "ギュオマーマ": "Moo Mama",
    "ギュオーン": "Mooton", "ギュオーンシック": "Sickly Mooton",
    "ギュオーンセイジ": "Mooton Sage", "ギュオーンベノム": "Mooton Venom",
    "ギュオーンペイン": "Mooton Pain", "ギュオーンメイジ": "Mooton Mage",
    "ギュオーンワイズ": "Mooton Wise", "ギュンギュオーン": "Zoom Mooton",
    "クサリカケックス": "Rotting Rex", "クッキングメカ": "Cooking Mech",
    "クロブターＸ": "Black Pig X", "クールタウロス": "Cool Tauros",
    "グレートドラゴン": "Great Dragon", "ケンゴウ": "Swordmaster",
    "ケンシン": "Kenshin", "ケンセイ": "Sword Saint",
    "コスモドラゴン": "Cosmo Dragon", "コトリバード": "Little Bird",
    "コーカサス": "Caucasus", "ゴッドタウロス": "God Tauros",
    "ゴージャスバグ": "Gorgeous Bug",
    # -- S ---------------------------------------------------------------
    "サイクロプス": "Cyclops", "サクラダイコーン": "Sakura Daicorn",
    "サメッポ": "Sharkie", "サメッポグレート": "Great Sharkie",
    "サメッポベビー": "Baby Sharkie", "サンダーウッシー": "Thunder Cow",
    "サンダーカツオ": "Thunder Bonito", "サンダーバグ": "Thunder Bug",
    "サンダーブートン": "Thunder Oinkton", "サンダーホエール": "Thunder Whale",
    "サンダーマグロ": "Thunder Tuna", "サンダーリュウ": "Thunder Dragon",
    "サンドサーモン": "Sand Salmon", "シェイプパケット": "Shape Packet",
    "シソバード": "Archaeobird", "シルバープニオン": "Silver Punion",
    "シルバーラビット": "Silver Rabbit", "ジェネラルクロー": "General Claw",
    "ジェノサイダー": "Genocider", "ジェラシーボール": "Jealousy Ball",
    "ジャガオウ": "Spud King", "ジャガダンシャク": "Spud Baron",
    "ジャガプリンス": "Spud Prince", "ジャリー": "Gritty",
    "ジュウハチキング": "18K King", "ジュンキング": "24K King",
    "スクワイヤ": "Squire", "スゴイやつ": "Amazing One",
    "スタードラゴン": "Star Dragon", "スペースシャーク": "Space Shark",
    "スモールアイ": "Small Eye", "スーパーマッシュ": "Super Mush",
    "セーフティメカ": "Safety Mech", "ゾッコンダー": "Crushgon",
    "ゾンビレックス": "Zombie Rex",
    # -- T ---------------------------------------------------------------
    "タイヨウチョウ": "Sun Bird", "ターミネーター": "Terminator",
    "ダイコーン": "Daicorn", "ダークドラゴン": "Dark Dragon",
    "ダークプリンス": "Dark Prince", "ダークボール": "Dark Ball",
    "ダークロード": "Dark Lord", "チトカチーナ": "Chitokachina",
    "チビオニ": "Little Ogre", "チビオン": "Chibion",
    "チビキング": "Tiny King", "チョットタウロス": "Warm Tauros",
    "チョパチーナ": "Chopachina", "チリトマトン": "Chili Tomaton",
    "チールタウロス": "Chill Tauros", "テラモエーナ": "Tera Moena",
    "デカしいたけ": "Big Shiitake", "デカオニ": "Big Ogre",
    "デカキノコーン": "Big Mushcorn", "デカデカボーン": "Huge Bone",
    "デカトマトン": "Big Tomaton", "デカブートン": "Big Oinkton",
    "デカプニオン": "Big Punion", "デカムシャ": "Big Samurai",
    "デコーダー": "Decoder", "デスエンジェル": "Death Angel",
    "デスホワイト": "Death White", "デビルボーイ": "Devil Boy",
    "デビルリーパー": "Devil Reaper", "デリシャスバグ": "Delicious Bug",
    "デンジリュウ": "Electric Dragon", "トマトン": "Tomaton",
    "トールタウロス": "Tall Tauros", "ドックンギョ": "Toxic Fish",
    "ドックンシャーク": "Toxic Shark", "ドックンメダカ": "Toxic Minnow",
    "ドラゴンキッド": "Dragon Kid", "ドラゴンバルジ": "Dragon Bulge",
    # -- N ---------------------------------------------------------------
    "ナイトドラゴン": "Knight Dragon", "ナイフバード": "Knife Bird",
    "ヌクヌク": "Snug", "ヌクヌクベビー": "Snug Baby",
    "ヌックヌク": "Snuggy", "ネオプニオン": "Neo Punion",
    "ネリマダイコーン": "Nerima Daicorn",
    # -- H ---------------------------------------------------------------
    "ハックパケット": "Hack Packet", "ハッピーバグ": "Happy Bug",
    "バイオレックス": "Bio Rex", "バッチーナ": "Batchina",
    "バトルマッシュ": "Battle Mush", "パッチーナ": "Patchina",
    "パティシエメカ": "Pastry Mech", "ヒヨコさむらい": "Chick Samurai",
    "ヒヨコししょー": "Chick Master", "ヒヨコしょうぐん": "Chick Shogun",
    "ビッグアイ": "Big Eye", "ビッググレイ": "Big Grey",
    "ビッグバード": "Big Bird", "ビッグフェイス": "Big Face",
    "ビッグマッシュ": "Big Mush", "ピュアデーモン": "Pure Demon",
    "ピュアラブゴン": "Pure Lovegon", "ピュンピュオーン": "Zip Mooton",
    "ピラニクス": "Piranix", "ピラニート": "Piranito",
    "ピラニードル": "Piraneedle", "フェイスバグ": "Face Bug",
    "フェニックス": "Phoenix", "フエールキノコン": "Multi Mushcorn",
    "フジヤーマ": "Fujiyama", "フワッフワ": "Fluffy",
    "フワフワ": "Fluff", "フワフワベビー": "Fluff Baby",
    "ブックカッター": "Book Cutter", "ブックガーダー": "Book Guarder",
    "ブックリーダー": "Book Reader", "ブラッドエビル": "Blood Evil",
    "ブラッドドラゴン": "Blood Dragon", "ブラッドワン": "Blood One",
    "ブレードバード": "Blade Bird", "ブートン": "Oinkton",
    "プチウッシー": "Petit Cow", "プチファング": "Petit Fang",
    "プチモエーナ": "Petit Moena", "プチロックン": "Petit Rockn",
    "プニオン": "Punion", "プニオンエリート": "Punion Elite",
    "プニオンリーダー": "Punion Leader", "プニンペラー": "Punimperor",
    "プラチナプニオン": "Platinum Punion", "プリプリベビー": "Plop Baby",
    "プリプリンス": "Plop Prince", "プリプリンセス": "Plop Princess",
    "プロトレックス": "Proto Rex", "ヘラクレス": "Hercules",
    "ヘルデビル": "Hell Devil", "ヘルバーナー": "Hell Burner",
    "ヘルファング": "Hell Fang", "ヘルフレア": "Hell Flare",
    "ベノムレックス": "Venom Rex", "ホットタウロス": "Hot Tauros",
    "ホットレックス": "Hot Rex", "ホネさむらい": "Bone Samurai",
    "ホネしょうぐん": "Bone Shogun", "ホネぶしょう": "Bone General",
    "ホラーファング": "Horror Fang", "ボルトリュウ": "Bolt Dragon",
    "ボーンベビー": "Bone Baby",
    # -- M ---------------------------------------------------------------
    "マウントエベ": "Mt. Everest", "マウントチョモ": "Mt. Chomo",
    "マグマレックス": "Magma Rex", "マジカルウィング": "Magical Wing",
    "マジカルスカイ": "Magical Sky", "マジカルフェザー": "Magical Feather",
    "マジカルブートン": "Magical Oinkton", "マッハギュオーン": "Mach Mooton",
    "マドウジンキ": "Magic Golem", "マドウヘイキ": "Magic Weapon",
    "ミニックス": "Minix", "ミニブートン": "Mini Oinkton",
    "ミニマムグレイ": "Minimum Grey", "ミニムシャ": "Mini Samurai",
    "ミュータレックス": "Mutant Rex", "ミラクルブートン": "Miracle Oinkton",
    "ミラクルマタンゴ": "Miracle Matango", "メカコック": "Mecha Cook",
    "メガレックス": "Mega Rex", "メギドフレイム": "Megido Flame",
    "メタルプニオン": "Metal Punion", "メッキング": "Gold-Plated King",
    "メテオレックス": "Meteo Rex", "モエーナ": "Moena",
    # -- Y/R -------------------------------------------------------------
    "ヤバイやつ": "Nasty One", "ユニバスシャーク": "Universe Shark",
    "ライジンウッシー": "Raijin Cow", "ライトニングバグ": "Lightning Bug",
    "ライトブートン": "Light Oinkton", "ラジカルブートン": "Radical Oinkton",
    "ラブゴン": "Lovegon", "リトルグレイ": "Little Grey",
    "レアなやつ": "Rare One", "レアバグ": "Rare Bug",
    "レックス": "Rex", "レックスベビー": "Rex Baby",
    "レッドドラゴン": "Red Dragon", "ロストパケット": "Lost Packet",
    "ロックン": "Rockn", "ロボットさま": "Lord Robot",
    "ロボットさん": "Mr. Robot", "ロボットちゃん": "Robo-chan",
    "Ｒ１−Ｔ": "R1-T", "Ｒ２−Ｔ": "R2-T", "Ｒ３−Ｔ": "R3-T",
}

# Boss base names; the Ｓ-suffixed rematch variants are generated below.
BOSS_BASE = {
    "こがねまる": "Koganemaru", "ちからをえしもの": "Power Bearer",
    "まおう": "Demon King", "アンタレス": "Antares", "エスラ": "Esra",
    "エヌラ": "Enura", "キングリッチ": "King Lich", "クッキー": "Cookie",
    "ケルベロス": "Cerberus", "コロッサス": "Colossus",
    "ゴッドドラゴン": "God Dragon", "ゴルド": "Gold", "シルバ": "Silva",
    "スパイウェア": "Spyware", "スーパーノヴァ": "Supernova",
    "ダイターン": "Daitarn", "ダイダロス": "Daedalus",
    "ダークワンダー": "Dark Wonder", "ティアマット": "Tiamat",
    "デスロキア": "Deathrokia", "ドリルマーリン": "Drill Marlin",
    "ナイトン": "Nighton", "ナガト": "Nagato", "ネストクイーン": "Nest Queen",
    "ハイドラス": "Hydras", "ビッグバーン": "Big Burn", "フラワ": "Flora",
    "ベリアルス": "Belials", "ベルゼブブ": "Beelzebub",
    "マッドランダー": "Mad Lander", "ムサシ": "Musashi", "ヤマト": "Yamato",
    "ライトン": "Lighton", "リフラ": "Leafla",
}

OBJECTS = {
    "おたからボックス": "Treasure Box", "ばくだん": "Bomb",
    "ウッドチェスト": "Wood Chest", "ウッドボックス": "Wood Box",
    "ゴールドチェスト": "Gold Chest", "ゴールドボックス": "Gold Box",
    "タル": "Barrel",
}


def build():
    """Japanese name -> English, covering Ｓ variants and stray whitespace."""
    out = {}
    out.update(MONSTERS)
    out.update(OBJECTS)
    for jp, en in BOSS_BASE.items():
        out[jp] = en
        out[jp + "Ｓ"] = en + " S"
    # some records carry a trailing full-width space
    for jp, en in list(out.items()):
        out.setdefault(jp + "　", en)
    return out


NAMES = build()
