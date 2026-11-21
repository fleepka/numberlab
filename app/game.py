from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.economy import GameError, apply_delta, lock_user, lock_users, now
from app.models import DailyClaim, Duel, Plate, Spin, User
from app.plates import PlateValue, random_plate
from app.progress import award_xp


MIN_BET = 100
MAX_BET = 100_000


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _plate_from(value: PlateValue, owner_id: int, source: str) -> Plate:
    return Plate(
        code=value.code,
        digits=value.digits,
        letters=value.letters,
        region=value.region,
        score=value.score,
        price=value.price,
        rarity=value.rarity,
        stars=value.stars,
        owner_id=owner_id,
        source=source,
    )


async def create_unique_plate(
    session: AsyncSession,
    owner_id: int,
    *,
    source: str,
    factory=random_plate,
) -> Plate:
    for _ in range(8):
        value = factory()
        if await session.scalar(select(Plate.id).where(Plate.code == value.code)):
            continue
        plate = _plate_from(value, owner_id, source)
        session.add(plate)
        await session.flush()
        return plate
    raise GameError("не удалось подобрать свободный номер")


def next_spin_at(user: User) -> datetime | None:
    last = _aware(user.last_spin_at)
    if last is None:
        return None
    return last + timedelta(hours=settings.free_spin_hours)


def spin_is_free(user: User) -> bool:
    ready = next_spin_at(user)
    return ready is None or now() >= ready


async def spin(session: AsyncSession, user_id: int) -> tuple[Plate, int]:
    user = await lock_user(session, user_id)
    if user.is_banned:
        raise GameError("аккаунт заблокирован")

    free = spin_is_free(user)
    cost = 0 if free else settings.spin_cost
    if cost:
        await apply_delta(session, user, -cost, "spin")

    plate = await create_unique_plate(session, user.id, source="spin")

    user.spins += 1
    user.last_spin_at = now()
    user.best_score = max(user.best_score, plate.score)
    award_xp(user, 5)
    session.add(Spin(user_id=user.id, plate_id=plate.id, cost=cost))
    return plate, cost


async def sell_plate(session: AsyncSession, user_id: int, plate_id: int) -> int:
    plate = await session.scalar(
        select(Plate).where(Plate.id == plate_id, Plate.owner_id == user_id).with_for_update()
    )
    if plate is None:
        raise GameError("номер не найден")
    if plate.is_paid:
        raise GameError("купленные за звёзды номера не продаются")

    user = await lock_user(session, user_id)
    amount = plate.price
    await apply_delta(session, user, amount, "sell", ref=plate.code)
    award_xp(user, 3)
    plate.owner_id = None
    return amount


async def claim_daily(session: AsyncSession, user_id: int) -> int:
    user = await lock_user(session, user_id)
    today = date.today()

    claimed = await session.scalar(
        select(DailyClaim.id).where(DailyClaim.user_id == user.id, DailyClaim.day == today)
    )
    if claimed:
        raise GameError("награда за сегодня уже получена")

    yesterday = today - timedelta(days=1)
    previous = await session.scalar(
        select(DailyClaim.id).where(DailyClaim.user_id == user.id, DailyClaim.day == yesterday)
    )
    user.streak = user.streak + 1 if previous else 1
    amount = settings.daily_base * min(user.streak, 7)

    await apply_delta(session, user, amount, "daily", ref=str(today))
    session.add(DailyClaim(user_id=user.id, day=today, amount=amount))
    award_xp(user, 10)
    return amount


async def create_duel(session: AsyncSession, user_id: int, bet: int) -> Duel:
    if not MIN_BET <= bet <= MAX_BET:
        raise GameError(f"ставка должна быть от {MIN_BET} до {MAX_BET}")

    user = await lock_user(session, user_id)
    if user.is_banned:
        raise GameError("аккаунт заблокирован")

    await apply_delta(session, user, -bet, "duel_bet", ref="open")
    duel = Duel(bet=bet, creator_id=user.id, status="open")
    session.add(duel)
    await session.flush()
    return duel


async def cancel_duel(session: AsyncSession, user_id: int, duel_id: int) -> None:
    duel = await session.scalar(select(Duel).where(Duel.id == duel_id).with_for_update())
    if duel is None or duel.status != "open":
        raise GameError("матч уже не открыт")
    if duel.creator_id != user_id:
        raise GameError("это не ваш матч")

    creator = await lock_user(session, duel.creator_id)
    await apply_delta(session, creator, duel.bet, "duel_refund", ref=str(duel.id))
    duel.status = "cancelled"
    duel.finished_at = now()


async def join_duel(session: AsyncSession, user_id: int, duel_id: int) -> tuple[Duel, Plate, Plate, int]:
    duel = await session.scalar(select(Duel).where(Duel.id == duel_id).with_for_update())
    if duel is None or duel.status != "open":
        raise GameError("матч уже занят или закрыт")
    if duel.creator_id == user_id:
        raise GameError("нельзя играть против себя")

    users = await lock_users(session, {duel.creator_id, user_id})
    creator, opponent = users[duel.creator_id], users[user_id]
    if opponent.is_banned:
        raise GameError("аккаунт заблокирован")

    await apply_delta(session, opponent, -duel.bet, "duel_bet", ref=str(duel.id))

    creator_plate = await create_unique_plate(session, creator.id, source="duel")
    opponent_plate = await create_unique_plate(session, opponent.id, source="duel")

    duel.creator_plate_id = creator_plate.id
    duel.opponent_plate_id = opponent_plate.id
    duel.opponent_id = opponent.id
    duel.finished_at = now()

    payout = 0
    if creator_plate.price == opponent_plate.price:
        duel.status = "tie"
        await apply_delta(session, creator, duel.bet, "duel_refund", ref=str(duel.id))
        await apply_delta(session, opponent, duel.bet, "duel_refund", ref=str(duel.id))
        award_xp(creator, 5)
        award_xp(opponent, 5)
    else:
        if creator_plate.price > opponent_plate.price:
            winner, loser = creator, opponent
        else:
            winner, loser = opponent, creator
        payout = duel.bet * 2
        await apply_delta(session, winner, payout, "duel_win", ref=str(duel.id))
        winner.duels_won += 1
        loser.duels_lost += 1
        award_xp(winner, 20)
        award_xp(loser, 5)
        duel.winner_id = winner.id
        duel.status = "finished"

    return duel, creator_plate, opponent_plate, payout


async def open_duels(session: AsyncSession, limit: int = 30) -> list[Duel]:
    rows = await session.scalars(
        select(Duel).where(Duel.status == "open").order_by(Duel.id.desc()).limit(limit)
    )
    return list(rows)


async def user_duels(session: AsyncSession, user_id: int, limit: int = 30) -> list[Duel]:
    rows = await session.scalars(
        select(Duel)
        .where(
            (Duel.creator_id == user_id) | (Duel.opponent_id == user_id)
        )
        .order_by(Duel.id.desc())
        .limit(limit)
    )
    return list(rows)
