from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user, now
from app.energy import add as add_energy
from app.models import Hunt, Plate, User, UserHunt
from app.plates import is_mirror, tier_index

ROTATION: list[dict] = [
    {"kind": "triple", "value": "777", "title": "Выбей 777", "coins": 4000, "energy": 10, "ticket": ""},
    {"kind": "region", "value": "77", "title": "Московский регион 77", "coins": 3000, "energy": 8, "ticket": ""},
    {"kind": "letters", "value": "АМР", "title": "Буквы АМР", "coins": 3500, "energy": 8, "ticket": "rare"},
    {"kind": "mirror", "value": "", "title": "Зеркальный номер", "coins": 2500, "energy": 6, "ticket": ""},
    {"kind": "triple", "value": "999", "title": "Выбей 999", "coins": 4000, "energy": 10, "ticket": ""},
    {"kind": "rarity", "value": "epic", "title": "Эпический номер или выше", "coins": 3000, "energy": 8, "ticket": "rare"},
    {"kind": "region", "value": "97", "title": "Регион 97", "coins": 3000, "energy": 8, "ticket": ""},
]


def matches(kind: str, value: str, plate: Plate) -> bool:
    if kind == "triple":
        return plate.digits == value
    if kind == "region":
        return plate.region == value
    if kind == "letters":
        return plate.letters == value
    if kind == "mirror":
        return is_mirror(plate.digits)
    if kind == "rarity":
        return tier_index(plate.rarity) >= tier_index(value)
    return False


def _spec(day: date) -> dict:
    return ROTATION[day.toordinal() % len(ROTATION)]


async def today(session: AsyncSession) -> Hunt:
    day = date.today()
    spec = _spec(day)
    code = f"{day.isoformat()}:{spec['kind']}:{spec['value']}"
    hunt = await session.scalar(select(Hunt).where(Hunt.code == code))
    if hunt is not None:
        return hunt

    hunt = Hunt(
        code=code,
        day=day,
        title=spec["title"],
        kind=spec["kind"],
        value=spec["value"],
        reward_coins=spec["coins"],
        reward_energy=spec["energy"],
        reward_ticket=spec["ticket"],
    )
    session.add(hunt)
    await session.flush()
    return hunt


async def register(session: AsyncSession, user: User, plate: Plate) -> None:
    hunt = await today(session)
    if not matches(hunt.kind, hunt.value, plate):
        return

    row = await session.scalar(
        select(UserHunt).where(UserHunt.user_id == user.id, UserHunt.hunt_id == hunt.id)
    )
    if row is None:
        session.add(UserHunt(user_id=user.id, hunt_id=hunt.id, done_at=now()))
    elif row.done_at is None:
        row.done_at = now()


async def view(session: AsyncSession, user: User) -> dict:
    hunt = await today(session)
    row = await session.scalar(
        select(UserHunt).where(UserHunt.user_id == user.id, UserHunt.hunt_id == hunt.id)
    )
    return {
        "title": hunt.title,
        "kind": hunt.kind,
        "value": hunt.value,
        "day": hunt.day.isoformat(),
        "done": bool(row and row.done_at),
        "claimed": bool(row and row.claimed_at),
        "reward_coins": hunt.reward_coins,
        "reward_energy": hunt.reward_energy,
        "reward_ticket": hunt.reward_ticket or None,
    }


async def claim(session: AsyncSession, user_id: int) -> dict:
    from app.tickets import grant as grant_ticket

    hunt = await today(session)
    row = await session.scalar(
        select(UserHunt)
        .where(UserHunt.user_id == user_id, UserHunt.hunt_id == hunt.id)
        .with_for_update()
    )
    if row is None or row.done_at is None:
        raise GameError("охота ещё не выполнена")
    if row.claimed_at is not None:
        raise GameError("награда уже получена")

    user = await lock_user(session, user_id)
    row.claimed_at = now()

    if hunt.reward_coins:
        await apply_delta(session, user, hunt.reward_coins, "hunt", ref=hunt.code)
    add_energy(user, hunt.reward_energy)
    if hunt.reward_ticket:
        await grant_ticket(session, user.id, hunt.reward_ticket)

    return {
        "coins": user.coins,
        "energy": user.energy,
        "rewards": {
            "coins": hunt.reward_coins,
            "energy": hunt.reward_energy,
            "ticket": hunt.reward_ticket or None,
        },
    }
