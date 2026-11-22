from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user
from app.garage import GARAGE_MAX, GARAGE_STEP
from app.models import User

PRICE = 149_000
DAYS = 30
INCOME_BONUS = 1.5


def is_active(user: User) -> bool:
    return user.vip_until is not None and user.vip_until >= date.today()


async def buy(session: AsyncSession, user_id: int) -> dict:
    user = await lock_user(session, user_id)
    if user.coins < PRICE:
        raise GameError(f"нужно {PRICE} ₽")

    await apply_delta(session, user, -PRICE, "vip")
    today = date.today()
    base = user.vip_until if user.vip_until and user.vip_until > today else today
    user.vip_until = base + timedelta(days=DAYS)
    user.garage_slots = min(GARAGE_MAX, user.garage_slots + 2)

    return {
        "vip_until": user.vip_until.isoformat(),
        "coins": user.coins,
        "slots": user.garage_slots,
        "active": True,
    }
