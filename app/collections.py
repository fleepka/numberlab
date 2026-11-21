from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user, now
from app.models import Collection, Plate, UserCollection
from app.plates import is_pair, is_palindrome, is_sequence, is_triple, tier_index
from app.progress import award_xp

DEFAULT_COLLECTIONS: list[dict] = [
    {
        "code": "triple_three",
        "title": "Три в ряд",
        "description": "Три номера с одинаковыми цифрами",
        "rule_kind": "triple",
        "rule_value": None,
        "target": 3,
        "reward_coins": 900,
        "reward_gems": 0,
        "reward_xp": 150,
        "sort": 10,
    },
    {
        "code": "lucky_777",
        "title": "Счастливые семёрки",
        "description": "Номер 777 в любой буквенной части",
        "rule_kind": "digits_exact",
        "rule_value": "777",
        "target": 1,
        "reward_coins": 2500,
        "reward_gems": 1,
        "reward_xp": 300,
        "sort": 20,
    },
    {
        "code": "agent_007",
        "title": "Агент 007",
        "description": "Номер 007",
        "rule_kind": "digits_exact",
        "rule_value": "007",
        "target": 1,
        "reward_coins": 1800,
        "reward_gems": 0,
        "reward_xp": 200,
        "sort": 30,
    },
    {
        "code": "mirror",
        "title": "Зеркала",
        "description": "Три палиндрома вида 121",
        "rule_kind": "palindrome",
        "rule_value": None,
        "target": 3,
        "reward_coins": 800,
        "reward_gems": 0,
        "reward_xp": 120,
        "sort": 40,
    },
    {
        "code": "sequence",
        "title": "Последовательности",
        "description": "Три номера с шагом 1: 123, 456, 987",
        "rule_kind": "sequence",
        "rule_value": None,
        "target": 3,
        "reward_coins": 1000,
        "reward_gems": 0,
        "reward_xp": 150,
        "sort": 50,
    },
    {
        "code": "pairs",
        "title": "Парочки",
        "description": "Пять номеров с парой одинаковых цифр",
        "rule_kind": "pair",
        "rule_value": None,
        "target": 5,
        "reward_coins": 700,
        "reward_gems": 0,
        "reward_xp": 100,
        "sort": 60,
    },
    {
        "code": "capital",
        "title": "Столица",
        "description": "Три номера региона 77",
        "rule_kind": "region",
        "rule_value": "77",
        "target": 3,
        "reward_coins": 900,
        "reward_gems": 0,
        "reward_xp": 120,
        "sort": 70,
    },
    {
        "code": "south",
        "title": "Юг",
        "description": "Два номера региона 23",
        "rule_kind": "region",
        "rule_value": "23",
        "target": 2,
        "reward_coins": 600,
        "reward_gems": 0,
        "reward_xp": 80,
        "sort": 80,
    },
    {
        "code": "seven_inside",
        "title": "Семёрка внутри",
        "description": "Пять номеров, где встречается цифра 7",
        "rule_kind": "contains",
        "rule_value": "7",
        "target": 5,
        "reward_coins": 500,
        "reward_gems": 0,
        "reward_xp": 60,
        "sort": 90,
    },
    {
        "code": "leading_zero",
        "title": "С нуля",
        "description": "Два номера, начинающихся с 00",
        "rule_kind": "prefix",
        "rule_value": "00",
        "target": 2,
        "reward_coins": 800,
        "reward_gems": 0,
        "reward_xp": 100,
        "sort": 100,
    },
    {
        "code": "epic_hunt",
        "title": "Охота на эпик",
        "description": "Два номера редкости не ниже эпической",
        "rule_kind": "rarity_min",
        "rule_value": "epic",
        "target": 2,
        "reward_coins": 2000,
        "reward_gems": 1,
        "reward_xp": 250,
        "sort": 110,
    },
    {
        "code": "legend",
        "title": "Легенда",
        "description": "Один номер редкости не ниже легендарной",
        "rule_kind": "rarity_min",
        "rule_value": "legendary",
        "target": 1,
        "reward_coins": 5000,
        "reward_gems": 2,
        "reward_xp": 400,
        "sort": 120,
    },
]


def matches(rule_kind: str, rule_value: str | None, plate: Plate) -> bool:
    digits = plate.digits
    if rule_kind == "digits_exact":
        return digits == rule_value
    if rule_kind == "triple":
        return is_triple(digits)
    if rule_kind == "pair":
        return is_pair(digits)
    if rule_kind == "palindrome":
        return is_palindrome(digits)
    if rule_kind == "sequence":
        return is_sequence(digits)
    if rule_kind == "contains":
        return bool(rule_value) and rule_value in digits
    if rule_kind == "prefix":
        return bool(rule_value) and digits.startswith(rule_value)
    if rule_kind == "region":
        return plate.region == rule_value
    if rule_kind == "rarity_min":
        return bool(rule_value) and tier_index(plate.rarity) >= tier_index(rule_value)
    return False


def progress_of(collection: Collection, plates: list[Plate]) -> int:
    matched = sum(1 for plate in plates if matches(collection.rule_kind, collection.rule_value, plate))
    return min(collection.target, matched)


async def seed(session: AsyncSession) -> int:
    existing = set(await session.scalars(select(Collection.code)))
    added = 0
    for item in DEFAULT_COLLECTIONS:
        if item["code"] in existing:
            continue
        session.add(Collection(**item))
        added += 1
    return added


async def catalog(session: AsyncSession, user_id: int) -> list[dict]:
    collections = await session.scalars(
        select(Collection).where(Collection.is_active).order_by(Collection.sort, Collection.id)
    )
    plates = list(await session.scalars(select(Plate).where(Plate.owner_id == user_id)))
    claimed = set(
        await session.scalars(
            select(UserCollection.collection_id).where(
                UserCollection.user_id == user_id,
                UserCollection.claimed_at.is_not(None),
            )
        )
    )

    result = []
    for collection in collections:
        progress = progress_of(collection, plates)
        result.append(
            {
                "id": collection.id,
                "code": collection.code,
                "title": collection.title,
                "description": collection.description,
                "target": collection.target,
                "progress": progress,
                "done": progress >= collection.target,
                "claimed": collection.id in claimed,
                "reward_coins": collection.reward_coins,
                "reward_gems": collection.reward_gems,
                "reward_xp": collection.reward_xp,
            }
        )
    return result


async def claim(session: AsyncSession, user_id: int, collection_id: int) -> dict:
    collection = await session.get(Collection, collection_id)
    if collection is None or not collection.is_active:
        raise GameError("коллекция не найдена")

    existing = await session.scalar(
        select(UserCollection)
        .where(
            UserCollection.user_id == user_id,
            UserCollection.collection_id == collection_id,
        )
        .with_for_update()
    )
    if existing is not None and existing.claimed_at is not None:
        raise GameError("награда уже получена")

    plates = list(await session.scalars(select(Plate).where(Plate.owner_id == user_id)))
    if progress_of(collection, plates) < collection.target:
        raise GameError("коллекция ещё не собрана")

    user = await lock_user(session, user_id)

    if existing is None:
        session.add(UserCollection(user_id=user_id, collection_id=collection_id, claimed_at=now()))
        try:
            await session.flush()
        except IntegrityError:
            raise GameError("награда уже получена") from None
    else:
        existing.claimed_at = now()

    if collection.reward_coins:
        await apply_delta(session, user, collection.reward_coins, "collection", ref=collection.code)
    if collection.reward_gems:
        await apply_delta(
            session, user, collection.reward_gems, "collection", currency="gems", ref=collection.code
        )
    award_xp(user, collection.reward_xp)

    return {
        "code": collection.code,
        "coins": user.coins,
        "gems": user.gems,
        "xp": user.xp,
        "level": user.level,
        "rewards": {
            "coins": collection.reward_coins,
            "gems": collection.reward_gems,
            "xp": collection.reward_xp,
        },
    }
