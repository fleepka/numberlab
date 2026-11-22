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
from datetime import date

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

COUNTRIES: dict[str, dict] = {
    "RU": {
        "flag": "RUS",
        "title": "Россия",
        "regions": REGIONS,
        "mult": 1.0,
    },
    "KZ": {
        "flag": "KZ",
        "title": "Казахстан",
        "regions": [f"{i:02d}" for i in range(1, 21)],
        "mult": 0.85,
    },
    "BY": {
        "flag": "BY",
        "title": "Беларусь",
        "regions": [str(i) for i in range(1, 8)],
        "mult": 0.8,
    },
    "UZ": {
        "flag": "UZ",
        "title": "Узбекистан",
        "regions": [f"{i:02d}" for i in range(1, 15)],
        "mult": 0.75,
    },
    "AE": {
        "flag": "UAE",
        "title": "ОАЭ",
        "regions": [],
        "mult": 0.5,
    },
}

# Реальные форматы: сколько цифр и букв, какой длины код региона, как собирается строка.
FORMATS: dict[str, dict] = {
    "RU": {"tpl": "ru", "digits": 3, "letters": 3, "region": (2, 3)},
    "KZ": {"tpl": "kz", "digits": 3, "letters": 3, "region": (2, 2)},
    "BY": {"tpl": "by", "digits": 4, "letters": 2, "region": (1, 1)},
    "UZ": {"tpl": "uz", "digits": 3, "letters": 3, "region": (2, 2)},
    "AE": {"tpl": "ae", "digits": (1, 5), "letters": (1, 2), "region": (0, 0)},
}

LATIN_LETTERS = "ABCDEFGHIJKLMNPQRSTUVWXYZ"
# Потолок рынка: в ОАЭ короткие номера дорогие, но не уходят в сотни миллионов.
PRICE_CAP = {"AE": 2_000_000}
DIVINE_MIN = 50_000_000

# «Мода»: раз в неделю один регион стоит дороже — как хайп вокруг серий на рынке.
HYPE_ROTATION = ["77", "97", "99", "50", "01", "23", "66", "78"]
HYPE_MULT = 1.4


def hype_region(day: date | None = None) -> str:
    week = (day or date.today()).isocalendar()[1]
    return HYPE_ROTATION[week % len(HYPE_ROTATION)]


# Официальная казахстанская сетка «повышенного спроса», сжатая до множителей к базе.
KZ_PREMIUM = {
    "777": 3.0,
    "001": 3.0,
    "002": 3.0,
    "003": 3.0,
    "004": 3.0,
    "005": 3.0,
    "006": 3.0,
    "007": 3.0,
    "008": 3.0,
    "009": 3.0,
    "111": 2.2,
    "999": 2.2,
    "707": 1.5,
}


def premium_multiplier(digits: str, country: str) -> float:
    if country in ("KZ", "UZ"):
        return KZ_PREMIUM.get(digits, 1.0)
    return 1.0

COUNTRY_CODES = tuple(COUNTRIES)

PRESTIGE_LETTERS = {"АМР", "АУЕ", "ЕКХ", "СВР", "МОС", "КАМ"}

SPECIAL_DIGITS: dict[str, tuple[str, int]] = {
    "007": ("Агент 007", 6),
    "911": ("Экстренный", 6),
    "666": ("Дьявольский", 5),
    "100": ("Сотка", 4),
    "001": ("Первый", 4),
    "777": ("Три семёрки", 0),
    "999": ("Три девятки", 0),
    "888": ("Три восьмёрки", 0),
}

TIERS: tuple[str, ...] = ("common", "rare", "epic", "legendary", "mythic", "divine")

RARITY_LABELS = {
    "common": "Обычный",
    "rare": "Редкий",
    "epic": "Эпический",
    "legendary": "Легендарный",
    "mythic": "Мифический",
    "divine": "Божественный",
}

TIER_BASE = {
    "common": 15_000,
    "rare": 90_000,
    "epic": 320_000,
    "legendary": 1_500_000,
    "mythic": 3_500_000,
    "divine": 52_000_000,
}

SCORE_STEP = {
    "common": 1_500,
    "rare": 10_000,
    "epic": 35_000,
    "legendary": 200_000,
    "mythic": 350_000,
    "divine": 800_000,
}

STARS_PRICE = {
    "common": 1,
    "rare": 5,
    "epic": 25,
    "legendary": 100,
    "mythic": 400,
    "divine": 1_500,
}

# Ставка платной прокрутки за номер выбранной редкости.
STAKES = {
    "common": 18_000,
    "rare": 140_000,
    "epic": 560_000,
    "legendary": 2_700_000,
    "mythic": 6_800_000,
    "divine": 63_000_000,
}

# Сколько энергии стоит прокрутка выбранной редкости.
ENERGY_COST = {
    "common": 1,
    "rare": 8,
    "epic": 16,
    "legendary": 64,
    "mythic": 256,
    "divine": 512,
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
    country: str = "RU"

    @property
    def rarity_label(self) -> str:
        return RARITY_LABELS[self.rarity]


def is_triple(digits: str) -> bool:
    return len(digits) >= 3 and len(set(digits)) == 1


def is_mirror(digits: str) -> bool:
    return len(digits) >= 3 and digits == digits[::-1] and len(set(digits)) > 1


def is_pair(digits: str) -> bool:
    if len(digits) < 2 or len(set(digits)) == 1:
        return False
    return any(digits[i] == digits[i + 1] for i in range(len(digits) - 1))


def is_sequence(digits: str) -> bool:
    values = [int(char) for char in digits]
    if len(values) < 3:
        return False
    up = all(values[i + 1] - values[i] == 1 for i in range(len(values) - 1))
    down = all(values[i] - values[i + 1] == 1 for i in range(len(values) - 1))
    return up or down


is_palindrome = is_mirror


def is_round(digits: str) -> bool:
    return digits.endswith("00") or digits.startswith("00")


def explain(digits: str, letters: str, region: str) -> tuple[Factor, ...]:
    factors: list[Factor] = []
    d = digits

    if is_triple(d):
        factors.append(Factor("Три одинаковые цифры", 9))
    elif d in SPECIAL_DIGITS and SPECIAL_DIGITS[d][1]:
        factors.append(Factor(SPECIAL_DIGITS[d][0], SPECIAL_DIGITS[d][1]))
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
    elif len(letters) >= 2 and letters[0] == letters[1]:
        factors.append(Factor("Повтор букв", 2))

    if region in PREMIUM_REGIONS:
        factors.append(Factor("Премиальный регион", 3))
    elif region in MAJOR_REGIONS:
        factors.append(Factor("Крупный регион", 2))

    return tuple(factors)


def score(digits: str, letters: str, region: str) -> int:
    return sum(factor.points for factor in explain(digits, letters, region))


def rarity_of(digits: str, letters: str, region: str, country: str = "RU") -> str:
    if country == "AE":
        return {1: "mythic", 2: "legendary", 3: "epic", 4: "rare"}.get(len(digits), "common")

    prestige = letters in PRESTIGE_LETTERS
    if is_triple(digits) and prestige and region in PREMIUM_REGIONS:
        return "divine"
    if is_triple(digits):
        return "mythic"
    if prestige and region in PREMIUM_REGIONS:
        return "mythic"
    if prestige:
        return "legendary"
    if country in ("KZ", "UZ") and digits in SPECIAL_DIGITS:
        return "legendary"
    if country == "BY" and len(digits) >= 4 and is_sequence(digits):
        return "legendary"
    if digits in SPECIAL_DIGITS:
        return "epic"
    if is_mirror(digits):
        return "rare"
    if is_pair(digits) or is_sequence(digits) or is_round(digits):
        return "epic"
    return "common"


def tier_of(digits: str, letters: str, region: str) -> str:
    return rarity_of(digits, letters, region)


def tier_index(rarity: str) -> int:
    return TIERS.index(rarity)


def price_of(
    total: int, rarity: str, country: str = "RU", digits: str = "", region: str = ""
) -> int:
    base = TIER_BASE[rarity] + SCORE_STEP[rarity] * total
    mult = COUNTRIES.get(country, COUNTRIES["RU"])["mult"]
    if country == "RU" and region and region == hype_region():
        mult *= HYPE_MULT
    mult *= premium_multiplier(digits, country)
    value = base * mult
    cap = PRICE_CAP.get(country)
    if cap is not None:
        value = min(value, cap)
    return max(100, int(round(value / 100) * 100))


_ALLOWED_LETTERS = {
    "RU": "АВЕКМНОРСТУХ",
    "BY": "АВЕІКМНОРСТХ",
    "KZ": LATIN_LETTERS,
    "UZ": LATIN_LETTERS,
    "AE": LATIN_LETTERS,
}


def _check_length(value: str, spec, label: str) -> None:
    if isinstance(spec, tuple):
        low, high = spec
        if not low <= len(value) <= high:
            raise ValueError(f"{label} length must be {low}..{high}")
    elif len(value) != spec:
        raise ValueError(f"{label} length must be {spec}")


def _code_of(letters: str, digits: str, region: str, template: str) -> str:
    if template == "ru":
        return f"{letters[0]}{digits}{letters[1:]}{region}"
    if template == "uz":
        return f"{region}{letters[0]}{digits}{letters[1:]}"
    if template == "ae":
        return f"{letters}{digits}"
    return f"{digits}{letters}{region}"


def build(letters: str, digits: str, region: str = "", country: str = "RU") -> PlateValue:
    data = COUNTRIES.get(country)
    spec = FORMATS.get(country)
    if data is None or spec is None:
        raise ValueError("unknown country")

    digits = digits.strip()
    letters = letters.strip().upper()
    region = region.strip()

    _check_length(digits, spec["digits"], "digits")
    _check_length(letters, spec["letters"], "letters")
    if not digits.isdigit():
        raise ValueError("digits must be numeric")
    allowed = _ALLOWED_LETTERS[country]
    if any(char not in allowed for char in letters):
        raise ValueError("letters must be allowed")

    low, high = spec["region"]
    if low == 0 and high == 0:
        if region:
            raise ValueError("region must be empty")
    else:
        if low <= len(region) <= high and region not in data["regions"]:
            raise ValueError("unknown region")
        if not low <= len(region) <= high:
            raise ValueError("bad region length")

    factors = explain(digits, letters, region)
    total = sum(factor.points for factor in factors)
    rarity = rarity_of(digits, letters, region, country)
    price = price_of(total, rarity, country, digits, region)

    if price > DIVINE_MIN and rarity != "divine":
        rarity = "divine"
        price = price_of(total, rarity, country, digits, region)

    return PlateValue(
        code=_code_of(letters, digits, region, spec["tpl"]),
        digits=digits,
        letters=letters,
        region=region,
        score=total,
        price=price,
        rarity=rarity,
        stars=STARS_PRICE[rarity],
        factors=factors,
        country=country,
    )


_PATTERNS = {
    "RU": re.compile(r"^([АВЕКМНОРСТУХ])(\d{3})([АВЕКМНОРСТУХ]{2})(\d{2,3})$"),
    "KZ": re.compile(r"^(\d{3})([A-Z]{3})(\d{2})$"),
    "BY": re.compile(r"^(\d{4})([АВЕІКМНОРСТХ]{2})(\d)$"),
    "UZ": re.compile(r"^(\d{2})([A-Z])(\d{3})([A-Z]{2})$"),
    "AE": re.compile(r"^([A-Z]{1,2})(\d{1,5})$"),
}


def parse_code(code: str, country: str | None = None) -> PlateValue:
    clean = code.replace(" ", "").replace("-", "").upper()
    candidates = [country] if country else list(FORMATS)

    for candidate in candidates:
        pattern = _PATTERNS.get(candidate)
        match = pattern.match(clean) if pattern else None
        if not match:
            continue
        groups = match.groups()
        if candidate == "RU":
            head, digits, tail, region = groups
            return build(head + tail, digits, region, candidate)
        if candidate == "UZ":
            region, head, digits, tail = groups
            return build(head + tail, digits, region, candidate)
        if candidate == "AE":
            letters, digits = groups
            return build(letters, digits, "", candidate)
        digits, letters, region = groups
        return build(letters, digits, region, candidate)

    raise ValueError(f"bad plate code: {code}")


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


def _letters_for(country: str, rng: random.Random | None) -> str:
    spec = FORMATS[country]["letters"]
    length = _randint(spec[0], spec[1], rng) if isinstance(spec, tuple) else spec
    allowed = _ALLOWED_LETTERS[country]
    return "".join(_choice(allowed, rng) for _ in range(length))


def _digits_for(country: str, tier: str, rng: random.Random | None) -> str:
    spec = FORMATS[country]["digits"]
    if country == "AE":
        length = {"common": 5, "rare": 4, "epic": 3, "legendary": 2, "mythic": 1}.get(tier, 5)
        return str(_randint(1, 9, rng)) + "".join(
            str(_randint(0, 9, rng)) for _ in range(length - 1)
        )

    length = _randint(spec[0], spec[1], rng) if isinstance(spec, tuple) else spec

    if tier == "mythic":
        return str(_randint(0, 9, rng)) * length

    if tier == "legendary":
        if country in ("KZ", "UZ"):
            pool = [value for value in SPECIAL_DIGITS if len(value) == length and value[0] != "0"]
            if pool:
                return _choice(pool, rng)
        start = _randint(1, max(1, 10 - length), rng)
        return "".join(str(start + index) for index in range(length))

    if tier == "epic":
        kind = _randint(0, 2, rng)
        if kind == 0 and length >= 3:
            head = str(_randint(1, 9, rng))
            tail = "".join(str(_randint(0, 9, rng)) for _ in range(length - 2))
            tail = tail.replace(head, str((int(head) + 1) % 10)) if tail else tail
            return head + head + tail
        if kind == 1:
            start = _randint(1, max(1, 10 - length), rng)
            return "".join(str(start + index) for index in range(length))
        return str(_randint(1, 9, rng)) + "0" * (length - 1)

    if tier == "rare":
        half = length // 2
        left = str(_randint(1, 9, rng)) + "".join(
            str(_randint(0, 9, rng)) for _ in range(half - 1)
        )
        if length % 2 == 0:
            return left + left[::-1]
        return left + str(_randint(0, 9, rng)) + left[::-1]

    return f"{_randint(1, 10 ** length - 1, rng):0{length}d}"


def plate_for_tier(
    tier: str, rng: random.Random | None = None, country: str = "RU"
) -> PlateValue:
    """Возвращает номер ровно запрошенной редкости в реальном формате страны."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier: {tier}")
    data = COUNTRIES.get(country)
    if data is None:
        raise ValueError(f"unknown country: {country}")

    if tier == "divine":
        if country != "RU":
            raise ValueError("Божественные номера доступны только для России")
        for _ in range(80):
            digits = str(_randint(0, 9, rng)) * 3
            letters = _prestige_letters(rng)
            region = _choice(sorted(PREMIUM_REGIONS), rng)
            plate = build(letters, digits, region, country)
            if plate.rarity == "divine":
                return plate
        raise RuntimeError("не удалось собрать номер редкости divine")

    regions = list(data["regions"])
    premium = [code for code in regions if code in PREMIUM_REGIONS]

    for _ in range(300):
        digits = _digits_for(country, tier, rng)
        letters = _letters_for(country, rng)
        region = _choice(regions, rng) if regions else ""

        if tier == "mythic" and premium and country == "RU" and _randint(0, 1, rng):
            digits = f"{_randint(0, 999, rng):03d}"
            letters = _prestige_letters(rng)
            region = _choice(premium, rng)

        if tier == "legendary" and country == "RU":
            digits = f"{_randint(0, 999, rng):03d}"
            letters = _prestige_letters(rng)
            region = _choice(regions, rng)

        try:
            plate = build(letters, digits, region, country)
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


def spin_plate(
    tier: str, rng: random.Random | None = None, country: str = "RU"
) -> PlateValue:
    """Номер выбранной редкости с ценой, скорректированной под ставку."""
    plate = plate_for_tier(tier, rng, country)
    multiplier = value_multiplier(rng)
    price = max(100, int(round(plate.price * multiplier / 100) * 100))
    if plate.rarity == "divine":
        price = max(price, DIVINE_MIN + 100_000)
    return replace(plate, price=price)


def priced(value: PlateValue, price: int) -> PlateValue:
    return replace(value, price=max(100, int(round(price / 100) * 100)))


def pretty_plate(rng: random.Random | None = None) -> PlateValue:
    """Бесплатная прокрутка: редкость выпадает по естественным правилам."""
    r = rng or random.Random(secrets.randbits(64))
    kind = r.choices(
        ["triple", "prestige", "pair", "sequence", "mirror", "plain"],
        weights=[6, 7, 16, 12, 16, 43],
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
