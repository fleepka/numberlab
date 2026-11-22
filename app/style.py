from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user

FRAMES = {
    "neon": {"title": "Неон", "price": 99, "color": "#35e0c0"},
    "gold": {"title": "Золото", "price": 149, "color": "#ffc247"},
    "ice": {"title": "Лёд", "price": 129, "color": "#6c8cff"},
}


async def buy(session: AsyncSession, user_id: int, code: str) -> dict:
    frame = FRAMES.get(code)
    if frame is None:
        raise GameError("такой рамки нет")

    user = await lock_user(session, user_id)
    if user.frame == code:
        raise GameError("рамка уже стоит")
    if user.gems < frame["price"]:
        raise GameError(f"нужно {frame['price']} ◆")

    await apply_delta(session, user, -frame["price"], "style", currency="gems", ref=code)
    user.frame = code
    return {"frame": code, "gems": user.gems, "color": frame["color"]}
