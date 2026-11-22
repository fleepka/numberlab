"""Генерация, классификация и оценка номерных знаков.

Редкость определяется правилами по самому номеру: три одинаковые цифры и
престижные буквы в премиальном регионе — мифические, палиндромы — редкие и так далее.
Цена — детерминированная функция от редкости и набора факторов.
"""

from __future__ import annotations

import random
import re
import secrets
from dataclasses import dataclass, replace

LETTERS = "АВЕКМНОРСТУХ"

REGIONS = [
    "01", "02", "03", "05", "06", "07", "10", "11", "12", "13", "16", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
    "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51",
    "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65",
    "66", "67", "68", "69", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
    "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "90", "91", "92", "93",
    "94", "95", "96", "97", "98", "99", "102", "116", "123", "125", "126", "136", "138",
    "142", "150", "152", "154", "159", "161", "163", "164", "166", "173", "174", "177",
    "178", "190", "193", "196", "197", "198", "199", "702", "716", "750", "761", "777",
    "797", "799", "977",
]

PREMIUM_REGIONS = {"77", "97", "99"}
MAJOR_REGIONS = {
    "01", "02", "03", "50", "90", "102", "116", "150", "190", "199", "777", "797", "799", "977",
}

PRESTIGE_LETTERS = {"АМР", "АУЕ", "ЕКХ", "СВР", "МОС"}

TIERS: tuple[str, ...] = ("common", "rare", "epic", "legendary", "mythic")

RARITY_LABELS = {
    "common": "Обычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
}

TIER_BASE = {
    "common": 700,
    "rare": 4200,
    "epic": 26000,
    "legendary": 150000,
    "mythic": 700000,
}

SCORE_STEP = {
    "common": 120,
    "rare": 350,
    "epic": 1200,
    "legendary": 5000,
    "mythic": 15000,
}

STARS_PRICE = {
    "common": 1,
    "rare": 5,
    "epic": 25,
    "legendary": 100,
    "mythic": 400,
}

# Ставка платной прокрутки за номер выбранной редкости.
STAKES = {
    "common": 2000,
    "rare": 8000,
    "epic": 40000,
    "legendary": 250000,
    "mythic": 1000000,
}

_ASC = {f"{i}{i + 1}{i + 2}" for i in range(1, 8)}
_DESC = {f"{i}{i - 1}{i - 2}" for i in range(3, 10)}


@dataclass(frozen=True, slots=True)
class Factor:
    title: str
    points: int


@dataclass(frozen=True, slots=True)
class PlateValue:
    code: str
    digits: str
    letters: str
    region: str
    score: int
    price: int
    rarity: str
    stars: int
    factors: tuple[Factor, ...]

    @property
    def rarity_label(self) -> str:
        return RARITY_LABELS[self.rarity]


def is_triple(digits: str) -> bool:
    return digits[0] == digits[1] == digits[2]


def is_pair(digits: str) -> bool:
    return not is_triple(digits) and (digits[0] == digits[1] or digits[1] == digits[2])


def is_mirror(digits: str) -> bool:
    return not is_triple(digits) and digits[0] == digits[2]


def is_sequence(digits: str) -> bool:
    return digits in _ASC or digits in _DESC


is_palindrome = is_mirror


def is_round(digits: str) -> bool:
    return digits.endswith("00") or digits.startswith("00")


def explain(digits: str, letters: str, region: str) -> tuple[Factor, ...]:
    factors: list[Factor] = []
    d = digits

    if is_triple(d):
        factors.append(Factor("Три одинаковые цифры", 9))
    elif is_mirror(d):
        factors.append(Factor("Зеркало", 5))
    elif is_pair(d):
        factors.append(Factor("Пара одинаковых цифр", 4))
    elif is_sequence(d):
        factors.append(Factor("Последовательность", 4))
    elif is_round(d):
        factors.append(Factor("Круглое число", 3))

    if letters in PRESTIGE_LETTERS:
        factors.append(Factor("Престижные буквы", 6))
    elif letters[0] == letters[1]:
        factors.append(Factor("Повтор букв", 2))

    if region in PREMIUM_REGIONS:
        factors.append(Factor("Премиальный регион", 3))
    elif region in MAJOR_REGIONS:
        factors.append(Factor("Крупный регион", 2))

    return tuple(factors)


def score(digits: str, letters: str, region: str) -> int:
    return sum(factor.points for factor in explain(digits, letters, region))


def rarity_of(digits: str, letters: str, region: str) -> str:
    prestige = letters in PRESTIGE_LETTERS
    if is_triple(digits):
        return "mythic"
    if prestige and region in PREMIUM_REGIONS:
        return "mythic"
    if prestige:
        return "legendary"
    if is_pair(digits) or is_sequence(digits) or is_round(digits):
        return "epic"
    if is_mirror(digits):
        return "rare"
    return "common"


def tier_of(digits: str, letters: str, region: str) -> str:
    return rarity_of(digits, letters, region)


def tier_index(rarity: str) -> int:
    return TIERS.index(rarity)


def price_of(total: int, rarity: str) -> int:
    return TIER_BASE[rarity] + SCORE_STEP[rarity] * total


def build(letters: str, digits: str, region: str) -> PlateValue:
    if len(digits) != 3 or not digits.isdigit():
        raise ValueError("digits must be 3 digits")
    if len(letters) != 3 or any(char not in LETTERS for char in letters):
        raise ValueError("letters must be 3 allowed cyrillic letters")
    if region not in REGIONS:
        raise ValueError("unknown region")

    factors = explain(digits, letters, region)
    total = sum(factor.points for factor in factors)
    rarity = rarity_of(digits, letters, region)

    return PlateValue(
        code=f"{letters[0]}{digits}{letters[1:]}{region}",
        digits=digits,
        letters=letters,
        region=region,
        score=total,
        price=price_of(total, rarity),
        rarity=rarity,
        stars=STARS_PRICE[rarity],
        factors=factors,
    )


_CODE_RE = re.compile(r"^([АВЕКМНОРСТУХ])(\d{3})([АВЕКМНОРСТУХ]{2})(\d{2,3})$")


def parse_code(code: str) -> PlateValue:
    match = _CODE_RE.match(code.replace(" ", "").upper())
    if not match:
        raise ValueError(f"bad plate code: {code}")
    head, digits, tail, region = match.groups()
    return build(head + tail, digits, region)


def _choice(source, rng: random.Random | None):
    if rng is None:
        return secrets.choice(list(source))
    return rng.choice(list(source))


def _randint(low: int, high: int, rng: random.Random | None) -> int:
    if rng is None:
        return low + secrets.randbelow(high - low + 1)
    return rng.randint(low, high)


def _random_letters(rng: random.Random | None = None, repeat: bool = False) -> str:
    if repeat:
        head = _choice(LETTERS, rng)
        return head + head + _choice(LETTERS, rng)
    return "".join(_choice(LETTERS, rng) for _ in range(3))


def _random_region(rng: random.Random | None = None, biased: bool = False) -> str:
    if not biased:
        return _choice(REGIONS, rng)
    roll = _randint(0, 99, rng)
    if roll < 12:
        return _choice(sorted(PREMIUM_REGIONS), rng)
    if roll < 40:
        return _choice(sorted(MAJOR_REGIONS), rng)
    return _choice(REGIONS, rng)


def random_plate(rng: random.Random | None = None) -> PlateValue:
    digits = f"{_randint(0, 999, rng):03d}"
    return build(_random_letters(rng), digits, _random_region(rng, biased=True))


def _mirror_digits(rng: random.Random | None) -> str:
    head = str(_randint(1, 9, rng))
    return head + str(_randint(0, 9, rng)) + head


def _pair_digits(rng: random.Random | None) -> str:
    a = str(_randint(1, 9, rng))
    b = str(_randint(0, 9, rng))
    while b == a:
        b = str(_randint(0, 9, rng))
    return a + a + b if _randint(0, 1, rng) else a + b + b


def _sequence_digits(rng: random.Random | None) -> str:
    if _randint(0, 1, rng):
        start = _randint(1, 7, rng)
        return "".join(str(start + i) for i in range(3))
    start = _randint(3, 9, rng)
    return "".join(str(start - i) for i in range(3))


def _epic_digits(rng: random.Random | None) -> str:
    kind = _randint(0, 2, rng)
    if kind == 0:
        return _pair_digits(rng)
    if kind == 1:
        return _sequence_digits(rng)
    return f"{_randint(1, 9, rng)}00"


def _prestige_letters(rng: random.Random | None) -> str:
    return _choice(sorted(PRESTIGE_LETTERS), rng)


def plate_for_tier(tier: str, rng: random.Random | None = None) -> PlateValue:
    """Возвращает номер ровно запрошенной редкости."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier: {tier}")

    for _ in range(200):
        if tier == "mythic":
            if _randint(0, 1, rng):
                digits = str(_randint(0, 9, rng)) * 3
                letters = _random_letters(rng, repeat=_randint(0, 1, rng) == 1)
            else:
                digits = f"{_randint(0, 999, rng):03d}"
                letters = _prestige_letters(rng)
            region = _choice(sorted(PREMIUM_REGIONS), rng)
        elif tier == "legendary":
            letters = _prestige_letters(rng)
            digits = f"{_randint(0, 999, rng):03d}"
            region = _random_region(rng)
        elif tier == "epic":
            letters = _random_letters(rng)
            digits = _epic_digits(rng)
            region = _random_region(rng, biased=True)
        elif tier == "rare":
            letters = _random_letters(rng)
            digits = _mirror_digits(rng)
            region = _random_region(rng, biased=True)
        else:
            letters = _random_letters(rng)
            digits = f"{_randint(0, 999, rng):03d}"
            region = _random_region(rng)

        try:
            plate = build(letters, digits, region)
        except ValueError:
            continue
        if plate.rarity == tier:
            return plate

    raise RuntimeError(f"не удалось собрать номер редкости {tier}")


def value_multiplier(rng: random.Random | None = None) -> float:
    """Множитель выплаты платной прокрутки: чаще всего номер дешевле ставки."""
    roll = rng.random() if rng else secrets.randbelow(1000) / 1000
    if roll < 0.58:
        return 1 - (0.03 + (roll / 0.58) * 0.25)
    if roll < 0.85:
        return 1 + ((roll - 0.58) / 0.27) * 0.06 - 0.03
    return 1.05 + ((roll - 0.85) / 0.15) * 0.15


def spin_plate(tier: str, rng: random.Random | None = None) -> PlateValue:
    """Номер выбранной редкости с ценой, скорректированной под ставку."""
    plate = plate_for_tier(tier, rng)
    multiplier = value_multiplier(rng)
    price = max(100, int(round(plate.price * multiplier / 100) * 100))
    return replace(plate, price=price)


def priced(value: PlateValue, price: int) -> PlateValue:
    return replace(value, price=max(100, int(round(price / 100) * 100)))


def pretty_plate(rng: random.Random | None = None) -> PlateValue:
    """Бесплатная прокрутка: редкость выпадает по естественным правилам."""
    r = rng or random.Random(secrets.randbits(64))
    kind = r.choices(
        ["triple", "prestige", "pair", "sequence", "mirror", "plain"],
        weights=[2, 2, 14, 10, 14, 58],
    )[0]

    if kind == "triple":
        return plate_for_tier("mythic", r) if r.random() < 0.08 else build(
            _random_letters(r), f"{r.randint(0, 9)}" * 3, _random_region(r, biased=True)
        )
    if kind == "prestige":
        return build(_prestige_letters(r), f"{r.randint(0, 999):03d}", _random_region(r, biased=True))
    if kind == "pair":
        digits = _pair_digits(r)
    elif kind == "sequence":
        digits = _sequence_digits(r)
    elif kind == "mirror":
        digits = _mirror_digits(r)
    else:
        digits = f"{r.randint(0, 999):03d}"

    return build(_random_letters(r, repeat=r.random() < 0.25), digits, _random_region(r, biased=True))
