from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError
from app.models import Plate


async def insert_plate(
    session: AsyncSession,
    factory,
    *,
    owner_id: int | None,
    source: str,
    is_paid: bool = False,
    attempts: int = 30,
) -> Plate:
    """Создаёт номер, переживая гонку за одинаковый код.

    Код уникален в базе, поэтому параллельная вставка падает на IntegrityError:
    откатываем только этот savepoint и пробуем следующий номер.
    """
    for _ in range(attempts):
        value = factory()
        try:
            async with session.begin_nested():
                plate = Plate(
                    code=value.code,
                    digits=value.digits,
                    letters=value.letters,
                    region=value.region,
                    score=value.score,
                    price=value.price,
                    rarity=value.rarity,
                    stars=value.stars,
                    country=value.country,
                    owner_id=owner_id,
                    is_paid=is_paid,
                    source=source,
                )
                session.add(plate)
                await session.flush()
            return plate
        except IntegrityError:
            continue
    raise GameError("не удалось подобрать свободный номер, попробуй ещё раз")
