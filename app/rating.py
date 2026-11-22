from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plate, User


def week_start(moment: datetime | None = None) -> datetime:
    moment = moment or datetime.now(timezone.utc)
    start = moment - timedelta(days=moment.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _plate_filter(period: str):
    if period == "week":
        return Plate.created_at >= week_start()
    return None


async def leaderboard(session: AsyncSession, limit: int = 50, period: str = "season") -> list[dict]:
    total = func.coalesce(func.sum(Plate.price), 0).label("total")
    count = func.count(Plate.id).label("plates")
    condition = _plate_filter(period)

    query = (
        select(User.id, User.username, User.first_name, total, count)
        .join(Plate, Plate.owner_id == User.id)
        .group_by(User.id)
        .order_by(total.desc(), count.desc())
        .limit(limit)
    )
    if condition is not None:
        query = query.where(condition)

    rows = await session.execute(query)

    return [
        {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "total": int(player_total or 0),
            "plates": int(plates or 0),
        }
        for user_id, username, first_name, player_total, plates in rows
    ]


async def position(session: AsyncSession, user_id: int, period: str = "season") -> dict:
    condition = _plate_filter(period)

    summary_query = select(
        User.id.label("uid"),
        func.coalesce(func.sum(Plate.price), 0).label("total"),
        func.count(Plate.id).label("plates"),
    ).join(Plate, Plate.owner_id == User.id)
    if condition is not None:
        summary_query = summary_query.where(condition)
    summary = summary_query.group_by(User.id).subquery()

    mine = (
        await session.execute(
            select(summary.c.total, summary.c.plates).where(summary.c.uid == user_id)
        )
    ).first()

    my_total = int(mine[0]) if mine else 0
    my_plates = int(mine[1]) if mine else 0

    ahead = await session.scalar(
        select(func.count()).select_from(summary).where(summary.c.total > my_total)
    )

    return {
        "rank": int(ahead or 0) + 1,
        "total": my_total,
        "plates": my_plates,
    }
