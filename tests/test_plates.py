from app.plates import (
    SCORE_STEP,
    STAKES,
    TIER_BASE,
    build,
    parse_code,
    plate_for_tier,
    pretty_plate,
    rarity_of,
    spin_plate,
    tier_index,
)

PLAIN = "475"
SEQ = "123"
TRIPLE = "777"


def test_price_is_deterministic():
    assert build("ААА", TRIPLE, "77") == build("ААА", TRIPLE, "77")


def test_rarity_rules():
    assert rarity_of("777", "АВС", "50") == "mythic"
    assert rarity_of("121", "АВС", "50") == "rare"
    assert rarity_of("112", "АВС", "50") == "epic"
    assert rarity_of("123", "АВС", "50") == "epic"
    assert rarity_of("700", "АВС", "50") == "epic"
    assert rarity_of("475", "АВС", "50") == "common"


def test_prestige_letters():
    assert rarity_of("475", "АМР", "77") == "mythic"
    assert rarity_of("475", "ЕКХ", "50") == "legendary"
    assert rarity_of("475", "АВС", "77") == "common"


def test_tiers_are_ordered_by_price():
    common = build("АВС", PLAIN, "50")
    rare = build("АВС", "121", "50")
    epic = build("АВС", SEQ, "50")
    legendary = build("ЕКХ", PLAIN, "50")
    mythic = build("АВС", TRIPLE, "50")
    prices = [common.price, rare.price, epic.price, legendary.price, mythic.price]
    assert prices == sorted(prices)
    assert mythic.rarity == "mythic"
    assert tier_index(mythic.rarity) > tier_index(common.rarity)


def test_premium_region_adds_value():
    moscow = build("АВС", PLAIN, "77")
    region = build("АВС", PLAIN, "75")
    assert moscow.price > region.price


def test_price_formula_matches_tier():
    plate = build("АВС", SEQ, "50")
    assert plate.price == TIER_BASE[plate.rarity] + SCORE_STEP[plate.rarity] * plate.score


def test_parse_code_roundtrip():
    for code in ("А777АА77", "В121ОР199", "К001МН750"):
        assert parse_code(code).code == code


def test_generated_plate_is_consistent():
    for _ in range(80):
        plate = pretty_plate()
        assert plate.price == TIER_BASE[plate.rarity] + SCORE_STEP[plate.rarity] * plate.score
        assert plate.stars >= 1
        assert parse_code(plate.code) == plate


def test_plate_for_tier_matches_request():
    for tier in STAKES:
        for _ in range(20):
            assert plate_for_tier(tier).rarity == tier


def test_paid_plate_is_mostly_below_stake():
    below = 0
    total = 200
    for _ in range(total):
        plate = spin_plate("epic")
        assert plate.rarity == "epic"
        if plate.price < STAKES["epic"]:
            below += 1
    assert below > total // 2


def test_factors_explain_price():
    plate = build("АМР", TRIPLE, "77")
    assert plate.score == sum(factor.points for factor in plate.factors)
    assert plate.rarity == "mythic"
    assert any(factor.title == "Три одинаковые цифры" for factor in plate.factors)
    assert any(factor.title == "Престижные буквы" for factor in plate.factors)
    assert any(factor.title == "Премиальный регион" for factor in plate.factors)
