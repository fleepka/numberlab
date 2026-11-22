from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import apply_delta, lock_user
from app.models import Gift, User

DAILY_LIMIT = 3
MAX_GEMS = 50


class GiftError(Exception):
    pass


def _start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def friends(session: AsyncSession, user: User) -> dict:
    rows = await session.scalars(
        select(User)
        .where(or_(User.invited_by == user.id, User.id == user.invited_by))
        .order_by(User.id.desc())
        .limit(50)
    )
    used = int(
        await session.scalar(
            select(func.count(Gift.id)).where(
                Gift.from_id == user.id, Gift.created_at >= _start()
            )
        )
        or 0
    )
    return {
        "items": [
            {
                "user_id": item.id,
                "name": item.username or item.first_name or "Игрок",
                "level": item.level,
            }
            for item in rows
        ],
        "left": max(0, DAILY_LIMIT - used),
        "max": MAX_GEMS,
    }


async def send(session: AsyncSession, user: User, to_id: int, amount: int) -> dict:
    if to_id == user.id:
        raise GiftError("себе дарить нельзя")
    if not 1 <= amount <= MAX_GEMS:
        raise GiftError(f"можно дарить от 1 до {MAX_GEMS} ◆")
    if user.gems < amount:
        raise GiftError("не хватает кристаллов")

    recipient = await lock_user(session, to_id)
    if recipient.invited_by != user.id and user.invited_by != recipient.id:
        raise GiftError("дарить можно только друзьям")

    used = int(
        await session.scalar(
            select(func.count(Gift.id)).where(
                Gift.from_id == user.id, Gift.created_at >= _start()
            )
        )
        or 0
    )
    if used >= DAILY_LIMIT:
        raise GiftError("на сегодня подарки закончились")

    await apply_delta(session, user, -amount, "gift", currency="gems", ref=str(to_id))
    await apply_delta(session, recipient, amount, "gift_in", currency="gems", ref=str(user.id))
    session.add(Gift(from_id=user.id, to_id=to_id, amount=amount))
    return {"amount": amount, "gems": user.gems, "left": DAILY_LIMIT - used - 1}
