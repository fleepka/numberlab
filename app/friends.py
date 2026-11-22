from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.economy import apply_delta, lock_user
from app.energy import add as add_energy
from app.models import Plate, Transaction, User

SHARE_RATE = 0.01
SHARE_DAILY_CAP = 30_000
SHARE_RARITIES = {"epic", "legendary", "mythic"}

LADDER: list[dict] = [
    {"need": 1, "title": "Первый друг", "coins": 300, "gems": 0, "energy": 25},
    {"need": 3, "title": "Три друга", "coins": 500, "gems": 1, "energy": 0},
    {"need": 5, "title": "Пять друзей", "coins": 1000, "gems": 2, "energy": 0},
    {"need": 10, "title": "Десять друзей", "coins": 2500, "gems": 5, "energy": 0},
]


def invite_link(tg_id: int) -> str:
    return f"https://t.me/{settings.bot_username}/app?startapp={tg_id}"


def ladder_view(invites: int) -> list[dict]:
    return [
        {
            "need": step["need"],
            "title": step["title"],
            "coins": step["coins"],
            "gems": step["gems"],
            "energy": step["energy"],
            "done": invites >= step["need"],
        }
        for step in LADDER
    ]


async def register_invite(session: AsyncSession, inviter_tg_id: int, newcomer: User) -> None:
    """Привязывает нового игрока к пригласившему и выдаёт награду на достигнутой ступени."""
    if inviter_tg_id == newcomer.tg_id:
        return

    inviter = await session.scalar(
        select(User).where(User.tg_id == inviter_tg_id).with_for_update()
    )
    if inviter is None:
        return

    newcomer.invited_by = inviter.id
    inviter.invites += 1

    for step in LADDER:
        if step["need"] != inviter.invites:
            continue
        if step["coins"]:
            await apply_delta(session, inviter, step["coins"], "referral", ref=str(step["need"]))
        if step["gems"]:
            await apply_delta(
                session, inviter, step["gems"], "referral", currency="gems", ref=str(step["need"])
            )
        add_energy(inviter, step["energy"])


async def invited_list(session: AsyncSession, user_id: int) -> list[dict]:
    rows = await session.scalars(
        select(User).where(User.invited_by == user_id).order_by(User.id.desc()).limit(50)
    )
    return [
        {
            "name": user.username or user.first_name or "Игрок",
            "level": user.level,
            "joined": user.created_at.date().isoformat(),
        }
        for user in rows
    ]


async def contest(session: AsyncSession, user: User, limit: int = 20) -> dict:
    rows = await session.execute(
        select(User.id, User.username, User.first_name, User.invites)
        .where(User.invites > 0)
        .order_by(User.invites.desc(), User.id)
        .limit(limit)
    )
    items = [
        {"user_id": user_id, "name": username or first_name or "Игрок", "invites": invites}
        for user_id, username, first_name, invites in rows
    ]
    ahead = await session.scalar(
        select(func.count()).select_from(User).where(User.invites > user.invites)
    )
    return {"items": items, "me": {"place": int(ahead or 0) + 1, "invites": user.invites}}


async def pay_share(session: AsyncSession, user: User, plate: Plate) -> int:
    """1% от эпического и выше уходит пригласившему, не больше 30k в сутки с друга."""
    if plate.rarity not in SHARE_RARITIES or not user.invited_by:
        return 0

    share = int(plate.price * SHARE_RATE)
    if share <= 0:
        return 0

    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    earned = await session.scalar(
        select(func.coalesce(func.sum(Transaction.delta), 0)).where(
            Transaction.user_id == user.invited_by,
            Transaction.reason == "friend_share",
            Transaction.ref == str(user.id),
            Transaction.created_at >= start,
        )
    )
    allowed = min(share, SHARE_DAILY_CAP - int(earned or 0))
    if allowed <= 0:
        return 0

    inviter = await lock_user(session, user.invited_by)
    await apply_delta(session, inviter, allowed, "friend_share", ref=str(user.id))
    return allowed
