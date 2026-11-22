from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import apply_delta
from app.models import Clan, Plate, User

COST = 5_000
MAX_MEMBERS = 30


class ClanError(Exception):
    pass


def _clean(name: str) -> str:
    value = " ".join(name.split())
    if not 3 <= len(value) <= 20:
        raise ClanError("название от 3 до 20 символов")
    return value


async def _code(session: AsyncSession) -> str:
    for _ in range(5):
        code = secrets.token_hex(3).upper()
        if not await session.scalar(select(Clan.id).where(Clan.code == code)):
            return code
    raise ClanError("не удалось создать код, попробуй ещё")


async def create(session: AsyncSession, user: User, name: str) -> Clan:
    if user.clan_id:
        raise ClanError("ты уже в клане")
    value = _clean(name)
    if await session.scalar(select(Clan.id).where(func.lower(Clan.name) == value.lower())):
        raise ClanError("такое название занято")
    if user.coins < COST:
        raise ClanError(f"нужно {COST:,} ₽".replace(",", " "))

    await apply_delta(session, user, -COST, "clan_create")
    clan = Clan(name=value, code=await _code(session), owner_id=user.id)
    session.add(clan)
    await session.flush()
    user.clan_id = clan.id
    return clan


async def join(session: AsyncSession, user: User, code: str) -> Clan:
    if user.clan_id:
        raise ClanError("сначала выйди из своего клана")
    clan = await session.scalar(select(Clan).where(Clan.code == code.strip().upper()))
    if clan is None:
        raise ClanError("клан не найден")
    count = await session.scalar(select(func.count(User.id)).where(User.clan_id == clan.id))
    if int(count or 0) >= MAX_MEMBERS:
        raise ClanError("в клане нет мест")
    user.clan_id = clan.id
    return clan


async def leave(session: AsyncSession, user: User) -> None:
    if not user.clan_id:
        raise ClanError("ты не в клане")
    clan_id = user.clan_id
    user.clan_id = None
    clan = await session.get(Clan, clan_id)
    if clan is None:
        return
    if clan.owner_id == user.id:
        heir = await session.scalar(
            select(User).where(User.clan_id == clan_id, User.id != user.id).order_by(User.id)
        )
        if heir is None:
            await session.delete(clan)
        else:
            clan.owner_id = heir.id


async def view(session: AsyncSession, user: User) -> dict | None:
    if not user.clan_id:
        return None
    clan = await session.get(Clan, user.clan_id)
    if clan is None:
        user.clan_id = None
        return None

    rows = await session.execute(
        select(
            User.id,
            User.username,
            User.first_name,
            User.level,
            func.coalesce(func.sum(Plate.price), 0).label("value"),
        )
        .outerjoin(Plate, Plate.owner_id == User.id)
        .where(User.clan_id == clan.id)
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(Plate.price), 0).desc(), User.id)
    )
    members = [
        {
            "user_id": user_id,
            "name": username or first_name or "Игрок",
            "level": level,
            "value": int(value or 0),
            "owner": user_id == clan.owner_id,
        }
        for user_id, username, first_name, level, value in rows
    ]
    return {
        "name": clan.name,
        "code": clan.code,
        "owner_id": clan.owner_id,
        "cost": COST,
        "max": MAX_MEMBERS,
        "total": sum(item["value"] for item in members),
        "members": members,
    }
