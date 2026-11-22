from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, lock_user
from app.models import Plate, Ticket, User
from app.plate_store import insert_plate
from app.plates import RARITY_LABELS, TIERS, plate_for_tier, tier_index
from app.progress import award_xp


async def grant(session: AsyncSession, user_id: int, rarity: str, amount: int = 1) -> None:
    if rarity not in RARITY_LABELS or amount <= 0:
        return
    row = await session.scalar(
        select(Ticket)
        .where(Ticket.user_id == user_id, Ticket.rarity == rarity)
        .with_for_update()
    )
    if row is None:
        session.add(Ticket(user_id=user_id, rarity=rarity, count=amount))
    else:
        row.count += amount


async def list_for(session: AsyncSession, user_id: int) -> list[dict]:
    rows = await session.scalars(select(Ticket).where(Ticket.user_id == user_id))
    counts = {row.rarity: row.count for row in rows}
    return [
        {"rarity": tier, "label": RARITY_LABELS[tier], "count": counts.get(tier, 0)}
        for tier in TIERS
    ]


async def _new_plate(session: AsyncSession, user_id: int, rarity: str) -> Plate:
    return await insert_plate(
        session, lambda: plate_for_tier(rarity), owner_id=user_id, source="ticket"
    )


async def use(session: AsyncSession, user_id: int, rarity: str) -> dict:
    if rarity not in RARITY_LABELS:
        raise GameError("неизвестная редкость")

    row = await session.scalar(
        select(Ticket)
        .where(Ticket.user_id == user_id, Ticket.rarity == rarity)
        .with_for_update()
    )
    if row is None or row.count < 1:
        raise GameError("такого билета нет")

    row.count -= 1

    from app.garage import ensure_space

    user = await lock_user(session, user_id)
    await ensure_space(session, user.id, user.garage_slots)
    plate = await _new_plate(session, user_id, rarity)

    user.spins += 1
    user.best_score = max(user.best_score, plate.score)
    award_xp(user, 5)

    from app.hunts import register as register_hunt
    from app.tasks import bump

    await bump(session, user, "spin")
    if tier_index(plate.rarity) >= tier_index("rare"):
        await bump(session, user, "rare")
    await register_hunt(session, user, plate)

    from app.friends import pay_share

    await pay_share(session, user, plate)

    return {"plate": plate, "left": row.count, "coins": user.coins}
