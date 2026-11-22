from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.economy import GameError, apply_delta, lock_user, lock_users, now
from app.energy import regenerate
from app.friends import pay_share
from app.garage import ensure_space
from app.hunts import register as register_hunt
from app.passes import POINTS_SPIN
from app.models import DailyClaim, Duel, Plate, Spin, User
from app.plates import (
    ENERGY_COST,
    STAKES,
    PlateValue,
    plate_for_tier,
    pretty_plate,
    spin_plate,
    tier_index,
)
from app.plate_store import insert_plate
from app.progress import award_xp
from app.tasks import bump


MIN_BET = 100
MAX_BET = 100_000


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
    factory=pretty_plate,
) -> Plate:
    return await insert_plate(session, factory, owner_id=owner_id, source=source)


async def spin(
    session: AsyncSession, user_id: int, stake: str | None = None
) -> tuple[Plate, int, str]:
    user = await lock_user(session, user_id)
    if user.is_banned:
        raise GameError("аккаунт заблокирован")

    regenerate(user)
    await ensure_space(session, user.id, user.garage_slots)
    tier = stake if stake in STAKES else "common"
    need = ENERGY_COST[tier]
    if user.energy >= need:
        user.energy -= need
        cost = 0
        factory = lambda: plate_for_tier(tier)  # noqa: E731
    else:
        cost = STAKES[tier]
        if user.coins < cost:
            raise GameError(f"нужно {need} ⚡ или {cost} ₽ на такую прокрутку")
        await apply_delta(session, user, -cost, "spin", ref=tier)
        factory = lambda: spin_plate(tier)  # noqa: E731
    plate = await create_unique_plate(session, user.id, source="spin", factory=factory)

    user.spins += 1
    user.best_score = max(user.best_score, plate.score)
    user.season_points += POINTS_SPIN
    award_xp(user, 5)
    session.add(Spin(user_id=user.id, plate_id=plate.id, cost=cost))
    await bump(session, user, "spin")
    if tier_index(plate.rarity) >= tier_index("rare"):
        await bump(session, user, "rare")
    await register_hunt(session, user, plate)
    await pay_share(session, user, plate)
    return plate, cost, tier


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
    await bump(session, user, "sell")
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

    try:
        async with session.begin_nested():
            session.add(DailyClaim(user_id=user.id, day=today, amount=amount))
            await session.flush()
    except IntegrityError:
        raise GameError("награда за сегодня уже получена") from None

    await apply_delta(session, user, amount, "daily", ref=str(today))
    award_xp(user, 10)
    await bump(session, user, "daily")
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

    await bump(session, creator, "duel")
    await bump(session, opponent, "duel")
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
