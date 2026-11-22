from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import lock_user, now
from app.models import Purchase, User
from app.style import FRAMES
from app.vip import apply_vip

PRODUCTS: dict[str, dict] = {
    "vip": {"stars": 99, "title": "VIP на 30 дней", "kind": "vip"},
    **{
        f"style:{code}": {
            "stars": max(9, int(item["price"] / 4)),
            "title": f"Рамка «{item['title']}»",
            "kind": "style",
            "frame": code,
        }
        for code, item in FRAMES.items()
    },
}


def catalog() -> list[dict]:
    return [
        {
            "code": code,
            "title": item["title"],
            "stars": item["stars"],
            "kind": item["kind"],
            "color": FRAMES[item["frame"]]["color"] if item["kind"] == "style" else None,
        }
        for code, item in PRODUCTS.items()
    ]


async def prepare(session: AsyncSession, user: User, code: str) -> Purchase:
    from app.shop import ShopError

    product = PRODUCTS.get(code)
    if product is None:
        raise ShopError("такого товара нет")

    purchase = Purchase(
        user_id=user.id,
        code=code,
        stars=product["stars"],
        payload=f"buy:{secrets.token_hex(12)}",
    )
    session.add(purchase)
    await session.flush()
    return purchase


async def fulfil(session: AsyncSession, purchase: Purchase) -> bool:
    """Выдаёт купленный товар. Возвращает True, если покупка была товаром."""
    product = PRODUCTS.get(purchase.code)
    if product is None:
        return False

    user = await lock_user(session, purchase.user_id)
    if product["kind"] == "vip":
        apply_vip(user)
    elif product["kind"] == "style":
        user.frame = product["frame"]

    purchase.status = "paid"
    purchase.paid_at = now()
    return True
