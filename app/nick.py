from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, lock_user
from app.models import User
from app.tickets import grant as grant_ticket

THRESHOLDS = {7: "mythic", 14: "legendary"}


def days_held(user: User) -> int:
    if user.nick_since is None:
        return 0
    return max(0, (date.today() - user.nick_since).days)


def view(user: User) -> dict:
    days = days_held(user)
    return {
        "holding": user.nick_since is not None,
        "days": days,
        "claimed7": user.nick7,
        "claimed14": user.nick14,
        "next": 7 if not user.nick7 else (14 if not user.nick14 else None),
    }


async def claim(session: AsyncSession, user_id: int, threshold: int) -> dict:
    if threshold not in THRESHOLDS:
        raise GameError("такой награды нет")

    user = await lock_user(session, user_id)
    days = days_held(user)
    if days < threshold:
        raise GameError(f"нужно продержать {threshold} дней, сейчас {days}")

    if threshold == 7:
        if user.nick7:
            raise GameError("награда уже получена")
        user.nick7 = True
    else:
        if user.nick14:
            raise GameError("награда уже получена")
        user.nick14 = True

    ticket = THRESHOLDS[threshold]
    await grant_ticket(session, user.id, ticket)
    return {"days": days, "ticket": ticket}
