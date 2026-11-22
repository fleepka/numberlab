from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, now
from app.models import Message, User

MAX_LEN = 200
MIN_GAP = timedelta(seconds=2)
HISTORY = 60

_LINK = re.compile(r"(https?://|t\.me/|www\.)", re.IGNORECASE)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def send(session: AsyncSession, user: User, text: str) -> Message:
    clean = " ".join((text or "").split())
    if not clean:
        raise GameError("сообщение пустое")
    if len(clean) > MAX_LEN:
        raise GameError(f"не больше {MAX_LEN} символов")
    if _LINK.search(clean):
        raise GameError("ссылки в чате запрещены")

    last = await session.scalar(
        select(Message.created_at)
        .where(Message.user_id == user.id)
        .order_by(Message.id.desc())
        .limit(1)
    )
    if last is not None and (now() - _aware(last)) < MIN_GAP:
        raise GameError("слишком часто, подожди пару секунд")

    message = Message(user_id=user.id, text=clean)
    session.add(message)
    await session.flush()
    return message


async def history(session: AsyncSession, after_id: int = 0) -> list[dict]:
    query = (
        select(Message, User.username, User.first_name)
        .join(User, User.id == Message.user_id)
        .order_by(Message.id.desc())
        .limit(HISTORY)
    )
    if after_id:
        query = query.where(Message.id > after_id)

    rows = list(await session.execute(query))
    rows.reverse()
    return [
        {
            "id": message.id,
            "user_id": message.user_id,
            "username": username,
            "first_name": first_name,
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        }
        for message, username, first_name in rows
    ]
