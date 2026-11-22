from __future__ import annotations

import random
import secrets
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import now
from app.models import Plate, Purchase, User
from app.plates import PlateValue, parse_code, pretty_plate


class ShopError(Exception):
    pass


SHOP_SIZE = 9

ENERGY_PACKS = {
    "small": {"energy": 10, "price": 5000, "title": "Пакет энергии"},
    "big": {"energy": 30, "price": 12000, "title": "Большой пакет энергии"},
}

TICKET_PRICES = {
    "rare": 15000,
    "epic": 60000,
    "legendary": 250000,
}


async def buy_energy(session: AsyncSession, user_id: int, pack: str) -> dict:
    from app.economy import GameError, apply_delta, lock_user
    from app.energy import add as add_energy

    item = ENERGY_PACKS.get(pack)
    if item is None:
        raise GameError("такого пакета нет")

    user = await lock_user(session, user_id)
    if user.coins < item["price"]:
        raise GameError("не хватает рублей")
    await apply_delta(session, user, -item["price"], "shop_energy", ref=pack)
    add_energy(user, item["energy"])
    return {"energy": user.energy, "coins": user.coins, "added": item["energy"]}


async def buy_ticket(session: AsyncSession, user_id: int, rarity: str) -> dict:
    from app.economy import GameError, apply_delta, lock_user
    from app.tickets import grant as grant_ticket

    price = TICKET_PRICES.get(rarity)
    if price is None:
        raise GameError("такого билета нет")

    user = await lock_user(session, user_id)
    if user.coins < price:
        raise GameError("не хватает рублей")
    await apply_delta(session, user, -price, "shop_ticket", ref=rarity)
    await grant_ticket(session, user.id, rarity)
    return {"coins": user.coins, "rarity": rarity}


def offers_for(user_id: int, day: date) -> list[PlateValue]:
    """Витрина на день: одинаковая для пользователя в течение суток, но разная у всех."""
    rng = random.Random(f"{user_id}:{day.isoformat()}")
    seen: dict[str, PlateValue] = {}
    for _ in range(400):
        if len(seen) >= SHOP_SIZE:
            break
        value = pretty_plate(rng)
        seen.setdefault(value.code, value)
    return sorted(seen.values(), key=lambda v: v.stars, reverse=True)


async def prepare_purchase(session: AsyncSession, user: User, code: str) -> Purchase:
    from app.garage import ensure_space

    offer = next((o for o in offers_for(user.id, date.today()) if o.code == code), None)
    if offer is None:
        raise ShopError("этого номера нет в витрине")

    if await session.scalar(select(Plate.id).where(Plate.code == code)):
        raise ShopError("номер уже занят другим игроком")

    try:
        await ensure_space(session, user.id, user.garage_slots)
    except Exception as error:
        if error.__class__.__name__ != "GameError":
            raise
        raise ShopError("гараж переполнен — освободи место") from None

    purchase = Purchase(
        user_id=user.id,
        code=offer.code,
        stars=offer.stars,
        payload=f"buy:{secrets.token_hex(12)}",
    )
    session.add(purchase)
    await session.flush()
    return purchase


async def fulfil_purchase(session: AsyncSession, payload: str) -> Plate | None:
    """Выдаёт номер по оплаченному счёту. Повторный вызов ничего не дублирует."""
    purchase = await session.scalar(
        select(Purchase).where(Purchase.payload == payload).with_for_update()
    )
    if purchase is None or purchase.status == "paid":
        return None

    if purchase.code == "pass":
        user = await session.scalar(select(User).where(User.id == purchase.user_id))
        if user is not None:
            user.pass_premium = True
        purchase.status = "paid"
        purchase.paid_at = now()
        return None

    if await session.scalar(select(Plate.id).where(Plate.code == purchase.code)):
        purchase.status = "failed"
        return None

    value = parse_code(purchase.code)
    plate = Plate(
        code=value.code,
        digits=value.digits,
        letters=value.letters,
        region=value.region,
        score=value.score,
        price=value.price,
        rarity=value.rarity,
        stars=value.stars,
        owner_id=purchase.user_id,
        is_paid=True,
        source="shop",
    )
    session.add(plate)
    await session.flush()

    purchase.status = "paid"
    purchase.paid_at = now()
    return plate
