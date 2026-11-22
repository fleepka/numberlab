from __future__ import annotations

import random
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, lock_user, now
from app.models import Plate, User
from app.plates import RARITY_LABELS, plate_for_tier, priced
from app.plate_store import insert_plate
from app.progress import award_xp

CRAFT_MIN = 3
CRAFT_MAX = 7

TARGET_TIER = {
    "common": "rare",
    "rare": "epic",
    "epic": "legendary",
    "legendary": "mythic",
    "mythic": "mythic",
}


def craft_multiplier(rng: random.Random | None = None) -> float:
    """50% дешевле, 30% около суммы, 20% дороже."""
    roll = rng.random() if rng else secrets.randbelow(1000) / 1000
    if roll < 0.50:
        return 0.88 + (roll / 0.50) * 0.09
    if roll < 0.80:
        return 0.97 + ((roll - 0.50) / 0.30) * 0.06
    return 1.03 + ((roll - 0.80) / 0.20) * 0.09


async def craft(session: AsyncSession, user_id: int, plate_ids: list[int]) -> dict:
    ids = list(dict.fromkeys(plate_ids))
    if len(ids) < CRAFT_MIN:
        raise GameError(f"нужно минимум {CRAFT_MIN} номера")
    if len(ids) > CRAFT_MAX:
        raise GameError(f"не больше {CRAFT_MAX} номеров")

    plates = list(
        await session.scalars(
            select(Plate).where(Plate.owner_id == user_id, Plate.id.in_(ids)).with_for_update()
        )
    )
    if len(plates) != len(ids):
        raise GameError("часть номеров не найдена")
    if any(plate.is_paid for plate in plates):
        raise GameError("купленные за звёзды номера не участвуют в крафте")

    rarities = {plate.rarity for plate in plates}
    if len(rarities) != 1:
        raise GameError("нужны номера одной редкости")

    rarity = rarities.pop()
    if rarity not in TARGET_TIER:
        raise GameError("такую редкость не скрафтить")
    target = TARGET_TIER[rarity]

    total = sum(plate.price for plate in plates)
    value = max(100, int(round(total * craft_multiplier() / 100) * 100))

    made = await insert_plate(
        session,
        lambda: priced(plate_for_tier(target), value),
        owner_id=user_id,
        source="craft",
    )

    for plate in plates:
        plate.owner_id = None

    user = await lock_user(session, user_id)
    award_xp(user, 15)
    if user.garage_income_at is None:
        user.garage_income_at = now()
    await session.flush()

    return {
        "plate": made,
        "spent": len(plates),
        "value": made.price,
        "total": total,
        "target": target,
        "target_label": RARITY_LABELS[target],
    }
