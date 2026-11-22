from __future__ import annotations

from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user
from app.energy import ENERGY_MAX
from app.models import Plate, Transaction, User
from app.plate_store import insert_plate
from app.plates import COUNTRIES, RARITY_LABELS, TIERS, plate_for_tier

CURRENCIES = ("coins", "gems", "energy")


def _user_view(user: User) -> dict:
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "name": user.first_name or "Игрок",
        "username": user.username,
        "coins": user.coins,
        "gems": user.gems,
        "energy": user.energy,
        "level": user.level,
        "spins": user.spins,
        "invites": user.invites,
        "is_banned": user.is_banned,
        "is_admin": user.is_admin,
        "garage_slots": user.garage_slots,
        "vip_until": user.vip_until.isoformat() if user.vip_until else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


async def list_users(session: AsyncSession, query: str = "", limit: int = 50) -> list[dict]:
    stmt = select(User)
    if query.strip():
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(like),
                User.first_name.ilike(like),
                cast(User.tg_id, String).like(like),
            )
        )
    rows = await session.scalars(stmt.order_by(User.id.desc()).limit(min(limit, 100)))
    return [_user_view(user) for user in rows]


async def detail(session: AsyncSession, user_id: int) -> dict:
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise GameError("пользователь не найден")

    count = await session.scalar(select(func.count(Plate.id)).where(Plate.owner_id == user_id))
    total = await session.scalar(
        select(func.coalesce(func.sum(Plate.price), 0)).where(Plate.owner_id == user_id)
    )
    history = list(
        await session.scalars(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.id.desc())
            .limit(15)
        )
    )

    return {
        **_user_view(user),
        "garage_count": int(count or 0),
        "garage_value": int(total or 0),
        "history": [
            {
                "delta": tx.delta,
                "currency": tx.currency,
                "reason": tx.reason,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in history
        ],
    }


async def grant(
    session: AsyncSession, user_id: int, currency: str, amount: int
) -> dict:
    if currency not in CURRENCIES:
        raise GameError("неизвестная валюта")
    if amount == 0:
        raise GameError("сумма ноль")

    user = await lock_user(session, user_id)
    if currency == "energy":
        user.energy = max(0, min(ENERGY_MAX, user.energy + amount))
        return {"energy": user.energy}
    if currency == "coins":
        if amount < 0 and user.coins + amount < 0:
            raise GameError("нельзя увести баланс в минус")
    if currency == "gems":
        if amount < 0 and user.gems + amount < 0:
            raise GameError("нельзя увести баланс в минус")
    await apply_delta(session, user, amount, "admin", currency=currency)
    return {"coins": user.coins, "gems": user.gems, "energy": user.energy}


async def give_plate(
    session: AsyncSession, user_id: int, rarity: str, country: str = "RU"
) -> Plate:
    if rarity not in RARITY_LABELS:
        raise GameError("неизвестная редкость")
    if country not in COUNTRIES:
        raise GameError("неизвестная страна")

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise GameError("пользователь не найден")

    return await insert_plate(
        session,
        lambda: plate_for_tier(rarity, country=country),
        owner_id=user_id,
        source="admin",
    )


async def set_ban(session: AsyncSession, user_id: int, banned: bool) -> dict:
    user = await lock_user(session, user_id)
    user.is_banned = banned
    return {"is_banned": user.is_banned}


async def cleanup_legacy(session: AsyncSession) -> int:
    """Удаляет номера со старыми редкостями (uncommon, unique и прочие вне TIERS)."""
    result = await session.execute(
        delete(Plate).where(Plate.rarity.notin_(list(TIERS)))
    )
    return int(result.rowcount or 0)


def rarities() -> list[dict]:
    return [{"code": tier, "label": RARITY_LABELS[tier]} for tier in TIERS]
