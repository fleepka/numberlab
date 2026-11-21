from app.plates import TIER_BASE, build, parse_code, pretty_plate, tier_of

PLAIN = "475"
SEQ = "123"
TRIPLE = "777"


def test_price_is_deterministic():
    assert build("ААА", TRIPLE, "77") == build("ААА", TRIPLE, "77")


def test_rare_beats_plain():
    rare = build("АВС", TRIPLE, "50")
    seq = build("АВС", SEQ, "50")
    plain = build("АВС", PLAIN, "50")
    assert rare.price > seq.price > plain.price
    assert rare.rarity == "legendary"
    assert seq.rarity == "epic"
    assert plain.rarity == "uncommon"


def test_premium_region_adds_value():
    moscow = build("АВС", PLAIN, "77")
    common = build("АВС", PLAIN, "75")
    assert moscow.price > common.price


def test_tier_thresholds():
    assert tier_of(0) == "common"
    assert tier_of(2) == "uncommon"
    assert tier_of(4) == "rare"
    assert tier_of(6) == "epic"
    assert tier_of(9) == "legendary"
    assert tier_of(12) == "mythic"
    assert tier_of(14) == "unique"


def test_parse_code_roundtrip():
    for code in ("А777АА77", "В123ОР199", "К001МН750"):
        assert parse_code(code).code == code


def test_generated_plate_is_consistent():
    for _ in range(80):
        plate = pretty_plate()
        assert plate.price == TIER_BASE[plate.rarity] + 50 * plate.score
        assert plate.stars >= 1
        assert parse_code(plate.code) == plate


def test_factors_explain_price():
    plate = build("ААА", TRIPLE, "77")
    assert plate.score == sum(factor.points for factor in plate.factors)
    assert plate.rarity == "unique"
    assert any(factor.title == "Три одинаковые цифры" for factor in plate.factors)
    assert any(factor.title == "Премиальный регион" for factor in plate.factors)
    assert any(factor.title == "Повтор букв" for factor in plate.factors)
