from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user
from app.energy import add as add_energy
from app.models import PassClaim, User
from app.tickets import grant as grant_ticket

POINTS_PER_LEVEL = 1000
MAX_LEVEL = 30
PREMIUM_STARS = 149

POINTS_SPIN = 5
POINTS_TASK = 30
POINTS_HUNT = 30
POINTS_COLLECTION = 50


def level_for(points: int) -> int:
    return max(0, min(MAX_LEVEL, points // POINTS_PER_LEVEL))


def rewards_for(level: int, premium: bool) -> dict:
    if premium:
        return {
            "coins": 2000 + level * 400,
            "gems": 5 if level % 5 == 0 else 0,
            "energy": 0,
            "ticket": "legendary" if level in (5, 15) else "mythic" if level == 30 else "",
        }
    return {
        "coins": 800 + level * 200,
        "gems": 0,
        "energy": 5 if level % 3 == 0 else 0,
        "ticket": "rare" if level in (10, 25) else "",
    }


async def view(session: AsyncSession, user: User) -> dict:
    claims = set(
        await session.scalars(
            select(PassClaim.level.concat(":").concat(PassClaim.track)).where(
                PassClaim.user_id == user.id
            )
        )
    )
    level = level_for(user.season_points)

    levels = []
    for current in range(1, MAX_LEVEL + 1):
        free = rewards_for(current, False)
        premium = rewards_for(current, True)
        free["claimed"] = f"{current}:free" in claims
        premium["claimed"] = f"{current}:premium" in claims
        levels.append(
            {
                "level": current,
                "unlocked": current <= level,
                "free": free,
                "premium": premium,
            }
        )

    return {
        "points": user.season_points,
        "level": level,
        "max_level": MAX_LEVEL,
        "points_per_level": POINTS_PER_LEVEL,
        "premium": user.pass_premium,
        "price_stars": PREMIUM_STARS,
        "levels": levels,
    }


async def claim(session: AsyncSession, user_id: int, level: int, track: str) -> dict:
    if track not in ("free", "premium"):
        raise GameError("неизвестная ветка наград")

    user = await lock_user(session, user_id)
    if level < 1 or level > MAX_LEVEL:
        raise GameError("такого уровня нет")
    if level > level_for(user.season_points):
        raise GameError("уровень ещё не открыт")
    if track == "premium" and not user.pass_premium:
        raise GameError("нужен премиум-пропуск")

    exists = await session.scalar(
        select(PassClaim.id).where(
            PassClaim.user_id == user.id,
            PassClaim.level == level,
            PassClaim.track == track,
        )
    )
    if exists:
        raise GameError("награда уже получена")

    session.add(PassClaim(user_id=user.id, level=level, track=track))
    try:
        await session.flush()
    except IntegrityError:
        raise GameError("награда уже получена") from None

    reward = rewards_for(level, track == "premium")

    if reward["coins"]:
        await apply_delta(session, user, reward["coins"], "pass", ref=f"{level}:{track}")
    if reward["gems"]:
        await apply_delta(
            session, user, reward["gems"], "pass", currency="gems", ref=f"{level}:{track}"
        )
    add_energy(user, reward["energy"])
    if reward["ticket"]:
        await grant_ticket(session, user.id, reward["ticket"])

    return {"level": level, "track": track, "rewards": reward}


async def unlock(session: AsyncSession, user_id: int) -> None:
    user = await lock_user(session, user_id)
    user.pass_premium = True
