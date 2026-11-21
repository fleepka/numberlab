"""Генерация, классификация и оценка номерных знаков.

Модуль без внешних зависимостей. Редкость и цена — детерминированная функция
от самого номера, поэтому их можно объяснить игроку и проверить тестами.
"""

from __future__ import annotations

import random
import re
import secrets
from dataclasses import dataclass

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

TIERS: tuple[str, ...] = (
    "common",
    "uncommon",
    "rare",
    "epic",
    "legendary",
    "mythic",
    "unique",
)

RARITY_LABELS = {
    "common": "Обычный",
    "uncommon": "Необычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
    "unique": "Уникальный",
}

TIER_BASE = {
    "common": 100,
    "uncommon": 250,
    "rare": 600,
    "epic": 1500,
    "legendary": 3500,
    "mythic": 8000,
    "unique": 20000,
}

STARS_PRICE = {
    "common": 1,
    "uncommon": 2,
    "rare": 5,
    "epic": 10,
    "legendary": 25,
    "mythic": 60,
    "unique": 150,
}

SCORE_STEP = 50

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


def explain(digits: str, letters: str, region: str) -> tuple[Factor, ...]:
    factors: list[Factor] = []
    d = digits

    if d[0] == d[1] == d[2]:
        factors.append(Factor("Три одинаковые цифры", 9))
    elif d in _ASC:
        factors.append(Factor("Возрастающая последовательность", 5))
    elif d in _DESC:
        factors.append(Factor("Убывающая последовательность", 4))
    elif d[0] == d[2]:
        factors.append(Factor("Палиндром", 4))
    elif d.endswith("00"):
        factors.append(Factor("Круглое число", 4))
    elif d.startswith("00"):
        factors.append(Factor("Ведущие нули", 3))
    elif d[0] == d[1] or d[1] == d[2]:
        factors.append(Factor("Пара одинаковых цифр", 3))

    if letters[0] == letters[1]:
        factors.append(Factor("Повтор букв", 2))

    if region in PREMIUM_REGIONS:
        factors.append(Factor("Премиальный регион", 3))
    elif region in MAJOR_REGIONS:
        factors.append(Factor("Крупный регион", 2))

    return tuple(factors)


def score(digits: str, letters: str, region: str) -> int:
    return sum(factor.points for factor in explain(digits, letters, region))


def tier_of(total: int) -> str:
    if total >= 14:
        return "unique"
    if total >= 12:
        return "mythic"
    if total >= 9:
        return "legendary"
    if total >= 6:
        return "epic"
    if total >= 4:
        return "rare"
    if total >= 2:
        return "uncommon"
    return "common"


def tier_index(rarity: str) -> int:
    return TIERS.index(rarity)


def is_triple(digits: str) -> bool:
    return digits[0] == digits[1] == digits[2]


def is_pair(digits: str) -> bool:
    return not is_triple(digits) and (digits[0] == digits[1] or digits[1] == digits[2])


def is_palindrome(digits: str) -> bool:
    return not is_triple(digits) and digits[0] == digits[2]


def is_sequence(digits: str) -> bool:
    return digits in _ASC or digits in _DESC


def price_of(total: int, rarity: str) -> int:
    return TIER_BASE[rarity] + SCORE_STEP * total


def build(letters: str, digits: str, region: str) -> PlateValue:
    if len(digits) != 3 or not digits.isdigit():
        raise ValueError("digits must be 3 digits")
    if len(letters) != 3 or any(char not in LETTERS for char in letters):
        raise ValueError("letters must be 3 allowed cyrillic letters")
    if region not in REGIONS:
        raise ValueError("unknown region")

    factors = explain(digits, letters, region)
    total = sum(factor.points for factor in factors)
    rarity = tier_of(total)

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


def _random_letters(rng: random.Random | None = None, repeat: bool = False) -> str:
    if rng is None:
        if repeat:
            head = secrets.choice(LETTERS)
            return head + head + secrets.choice(LETTERS)
        return "".join(secrets.choice(LETTERS) for _ in range(3))
    if repeat:
        head = rng.choice(LETTERS)
        return head + head + rng.choice(LETTERS)
    return "".join(rng.choice(LETTERS) for _ in range(3))


def _random_region(rng: random.Random | None = None, biased: bool = False) -> str:
    if rng is None:
        if biased and secrets.randbelow(100) < 15:
            return secrets.choice(sorted(PREMIUM_REGIONS))
        return secrets.choice(REGIONS)
    roll = rng.random()
    if biased and roll < 0.12:
        return rng.choice(sorted(PREMIUM_REGIONS))
    if biased and roll < 0.40:
        return rng.choice(sorted(MAJOR_REGIONS))
    return rng.choice(REGIONS)


def random_plate(rng: random.Random | None = None) -> PlateValue:
    digits = f"{(rng.randrange(1000) if rng else secrets.randbelow(1000)):03d}"
    return build(_random_letters(rng), digits, _random_region(rng, biased=True))


def pretty_plate(rng: random.Random | None = None) -> PlateValue:
    r = rng or random.Random(secrets.randbits(64))
    kind = r.choices(
        ["triple", "asc", "pal", "round", "pair", "plain"],
        weights=[4, 7, 9, 8, 20, 52],
    )[0]

    if kind == "triple":
        digits = str(r.randint(0, 9)) * 3
    elif kind == "asc":
        start = r.randint(1, 7)
        digits = "".join(str(start + i) for i in range(3))
    elif kind == "pal":
        digits = f"{r.randint(1, 9)}{r.randint(0, 9)}{r.randint(1, 9)}"
        digits = digits[0] + digits[1] + digits[0]
    elif kind == "round":
        digits = f"{r.randint(1, 9)}00"
    elif kind == "pair":
        a, b = str(r.randint(0, 9)), str(r.randint(0, 9))
        while b == a:
            b = str(r.randint(0, 9))
        digits = a + a + b if r.random() < 0.5 else a + b + b
    else:
        digits = f"{r.randint(0, 999):03d}"

    return build(_random_letters(r, repeat=r.random() < 0.25), digits, _random_region(r, biased=True))
