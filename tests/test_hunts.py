from types import SimpleNamespace

from app.hunts import matches


def plate(digits: str = "777", letters: str = "АВС", region: str = "50", rarity: str = "common"):
    return SimpleNamespace(digits=digits, letters=letters, region=region, rarity=rarity)


def test_triple_hunt():
    assert matches("triple", "777", plate(digits="777"))
    assert not matches("triple", "777", plate(digits="778"))


def test_region_hunt():
    assert matches("region", "77", plate(region="77"))
    assert not matches("region", "77", plate(region="78"))


def test_letters_hunt():
    assert matches("letters", "АМР", plate(letters="АМР"))
    assert not matches("letters", "АМР", plate(letters="АВС"))


def test_mirror_hunt():
    assert matches("mirror", "", plate(digits="121"))
    assert not matches("mirror", "", plate(digits="123"))


def test_rarity_hunt():
    assert matches("rarity", "epic", plate(rarity="legendary"))
    assert matches("rarity", "epic", plate(rarity="epic"))
    assert not matches("rarity", "epic", plate(rarity="rare"))


def test_unknown_kind_never_matches():
    assert not matches("nope", "", plate())
