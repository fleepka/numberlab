from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, User


class GameError(Exception):
    pass


class InsufficientFunds(GameError):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


async def lock_user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise LookupError("user not found")
    return user


async def lock_users(session: AsyncSession, ids: set[int]) -> dict[int, User]:
    # Единый порядок блокировок, чтобы два встречных матча не поймали дедлок.
    locked: dict[int, User] = {}
    for uid in sorted(ids):
        locked[uid] = await lock_user(session, uid)
    return locked


async def apply_delta(
    session: AsyncSession,
    user: User,
    delta: int,
    reason: str,
    *,
    currency: str = "coins",
    ref: str | None = None,
    idem: str | None = None,
) -> bool:
    """Меняет баланс валюты и пишет запись в журнал.

    Возвращает False, если операция с таким idem_key уже была выполнена.
    """
    if currency not in ("coins", "gems"):
        raise ValueError(f"unknown currency: {currency}")
    if idem:
        exists = await session.scalar(select(Transaction.id).where(Transaction.idem_key == idem))
        if exists:
            return False

    field = "coins" if currency == "coins" else "gems"
    balance = getattr(user, field) + delta
    if balance < 0:
        raise InsufficientFunds("not enough funds")

    setattr(user, field, balance)
    session.add(
        Transaction(
            user_id=user.id,
            currency=currency,
            delta=delta,
            reason=reason,
            ref=ref,
            idem_key=idem,
        )
    )
    return True


async def history(session: AsyncSession, user_id: int, limit: int = 30) -> list[Transaction]:
    rows = await session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.id.desc())
        .limit(limit)
    )
    return list(rows)
