from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user, now
from app.models import Plate, User
from app.progress import award_xp
from app.tasks import bump

INCOME_SHARE = 0.01
INCOME_CAP_HOURS = 24
MAX_BATCH = 50

GARAGE_START = 22
GARAGE_STEP = 5
GARAGE_MAX = 50
SLOT_PRICE_GEMS = 200


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def garage_plates(session: AsyncSession, user_id: int) -> list[Plate]:
    rows = await session.scalars(
        select(Plate).where(Plate.owner_id == user_id).order_by(Plate.price.desc())
    )
    return list(rows)


def rate_for(total: int) -> int:
    return int(total * INCOME_SHARE)


async def ensure_space(session: AsyncSession, user_id: int, slots: int) -> None:
    used = await session.scalar(select(func.count(Plate.id)).where(Plate.owner_id == user_id))
    if int(used or 0) >= slots:
        raise GameError("гараж переполнен — продай номер или купи места")


async def buy_slots(session: AsyncSession, user_id: int) -> dict:
    user = await lock_user(session, user_id)
    if user.garage_slots >= GARAGE_MAX:
        raise GameError("больше мест не продаётся")
    if user.gems < SLOT_PRICE_GEMS:
        raise GameError(f"нужно {SLOT_PRICE_GEMS} ◆")

    await apply_delta(session, user, -SLOT_PRICE_GEMS, "garage_slots", currency="gems")
    user.garage_slots = min(GARAGE_MAX, user.garage_slots + GARAGE_STEP)
    return {"slots": user.garage_slots, "gems": user.gems}


async def income_state(session: AsyncSession, user: User) -> dict:
    plates = await garage_plates(session, user.id)
    total = sum(plate.price for plate in plates)
    rate = rate_for(total)

    since = user.garage_income_at or user.created_at
    hours = max(0.0, (now() - _aware(since)).total_seconds() / 3600)
    hours = min(hours, INCOME_CAP_HOURS)

    return {
        "rate": rate,
        "available": int(rate * hours),
        "total": total,
        "plates": len(plates),
        "cap_hours": INCOME_CAP_HOURS,
        "hours": round(hours, 2),
    }


async def claim_income(session: AsyncSession, user_id: int) -> dict:
    user = await lock_user(session, user_id)
    state = await income_state(session, user)
    if state["available"] <= 0:
        raise GameError("доход ещё не накопился")

    await apply_delta(session, user, state["available"], "garage_income")
    user.garage_income_at = now()
    return {
        "amount": state["available"],
        "coins": user.coins,
        "rate": state["rate"],
    }


async def sell_many(session: AsyncSession, user_id: int, plate_ids: list[int]) -> dict:
    ids = list(dict.fromkeys(plate_ids))
    if not ids:
        raise GameError("не выбрано ни одного номера")
    if len(ids) > MAX_BATCH:
        raise GameError(f"за раз можно продать не больше {MAX_BATCH} номеров")

    plates = list(
        await session.scalars(
            select(Plate)
            .where(Plate.owner_id == user_id, Plate.id.in_(ids))
            .with_for_update()
        )
    )
    if len(plates) != len(ids):
        raise GameError("часть номеров не найдена")
    if any(plate.is_paid for plate in plates):
        raise GameError("купленные за звёзды номера не продаются")

    user = await lock_user(session, user_id)
    amount = sum(plate.price for plate in plates)
    for plate in plates:
        plate.owner_id = None

    await apply_delta(session, user, amount, "sell", ref=f"batch:{len(plates)}")
    award_xp(user, min(30, 3 * len(plates)))
    await bump(session, user, "sell", len(plates))

    return {
        "amount": amount,
        "sold": len(plates),
        "coins": user.coins,
    }
