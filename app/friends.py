from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.economy import apply_delta
from app.energy import add as add_energy
from app.models import User

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
