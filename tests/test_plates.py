from app.plates import (
    COUNTRIES,
    SCORE_STEP,
    STAKES,
    TIER_BASE,
    build,
    hype_region,
    parse_code,
    plate_for_tier,
    pretty_plate,
    price_of,
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
    raw = TIER_BASE[plate.rarity] + SCORE_STEP[plate.rarity] * plate.score
    assert plate.price == round(raw / 100) * 100


def test_kz_premium_grid_boosts_777():
    lucky = build("ABC", "777", "01", "KZ")
    other = build("ABC", "888", "01", "KZ")
    assert lucky.rarity == other.rarity == "mythic"
    assert lucky.price > other.price


def test_hype_region_costs_more():
    hot = hype_region()
    other = next(code for code in ("75", "76", "74") if code != hot)
    boosted = build("АВС", PLAIN, hot, "RU")
    plain = build("АВС", PLAIN, other, "RU")
    assert boosted.price > plain.price


def test_special_numbers_are_epic():
    assert rarity_of("007", "АВС", "50") == "epic"
    assert rarity_of("911", "АВС", "50") == "epic"
    plate = build("АВС", "007", "50")
    assert any(factor.title == "Агент 007" for factor in plate.factors)


def test_country_changes_price_and_keeps_code():
    ru = build("АВС", PLAIN, "01", "RU")
    kz = build("ABC", PLAIN, "01", "KZ")
    assert ru.country == "RU"
    assert kz.country == "KZ"
    assert kz.price < ru.price


def test_real_formats_per_country():
    assert build("ABC", "123", "02", "KZ").code == "123ABC02"
    assert build("АВ", "1234", "5", "BY").code == "1234АВ5"
    assert build("ABC", "123", "01", "UZ").code == "01A123BC"
    assert build("AA", "12345", "", "AE").code == "AA12345"


def test_ae_short_numbers_are_mythic_and_costly():
    short = build("A", "7", "", "AE")
    long = build("Q", "12345", "", "AE")
    assert short.rarity == "mythic"
    assert long.rarity == "rare"
    assert short.price > long.price


def test_generated_plate_uses_country_regions():
    plate = plate_for_tier("epic", country="KZ")
    assert plate.country == "KZ"
    assert plate.region in COUNTRIES["KZ"]["regions"]

    ae = plate_for_tier("epic", country="AE")
    assert ae.country == "AE"
    assert ae.region == ""
    assert len(ae.digits) == 4


def test_parse_code_with_country():
    plate = build("ABC", PLAIN, "14", "UZ")
    parsed = parse_code(plate.code, "UZ")
    assert parsed.country == "UZ"
    assert parsed.code == plate.code
    assert parsed.price == plate.price



    for code in ("А777АА77", "В121ОР199", "К001МН750"):
        assert parse_code(code).code == code


def test_generated_plate_is_consistent():
    for _ in range(80):
        plate = pretty_plate()
        assert plate.price == price_of(plate.score, plate.rarity, "RU", plate.digits, plate.region)
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
