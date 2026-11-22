from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user, now
from app.models import Auction, Plate, User
from app.plates import plate_for_tier, tier_index

DURATION_HOURS = 24
START_BID = 50_000
MIN_STEP = 5_000
LOT_RARITY = "mythic"


def _aware(value):
    from datetime import timezone

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def _create_lot(session: AsyncSession) -> Auction:
    for _ in range(40):
        value = plate_for_tier(LOT_RARITY)
        taken = await session.scalar(
            select(Plate.id).where(Plate.code == value.code)
        ) or await session.scalar(
            select(Auction.id).where(Auction.plate_code == value.code, Auction.closed.is_(False))
        )
        if taken:
            continue
        auction = Auction(
            plate_code=value.code,
            ends_at=now() + timedelta(hours=DURATION_HOURS),
            top_bid=0,
        )
        session.add(auction)
        await session.flush()
        return auction
    raise GameError("не удалось открыть лот")


async def _close(session: AsyncSession, auction: Auction) -> None:
    if auction.closed:
        return
    if not auction.top_user_id:
        auction.closed = True
        return

    from app.plates import parse_code

    value = parse_code(auction.plate_code)
    plate = Plate(
        code=value.code,
        digits=value.digits,
        letters=value.letters,
        region=value.region,
        score=value.score,
        price=value.price,
        rarity=value.rarity,
        stars=value.stars,
        owner_id=auction.top_user_id,
        source="auction",
    )
    try:
        async with session.begin_nested():
            session.add(plate)
            await session.flush()
    except IntegrityError:
        # Номер уже занят: не отдаём лот, возвращаем ставку лидеру.
        leader = await lock_user(session, auction.top_user_id)
        await apply_delta(session, leader, auction.top_bid, "auction_refund", ref=str(auction.id))
        auction.closed = True
        return

    auction.closed = True


async def current(session: AsyncSession) -> Auction:
    auction = await session.scalar(
        select(Auction).where(Auction.closed.is_(False)).order_by(Auction.id.desc())
    )
    if auction is not None and _aware(auction.ends_at) > now():
        return auction
    if auction is not None:
        await _close(session, auction)
    return await _create_lot(session)


async def view(session: AsyncSession, user: User) -> dict:
    auction = await current(session)
    leader = None
    if auction.top_user_id:
        leader = await session.scalar(select(User).where(User.id == auction.top_user_id))

    return {
        "code": auction.plate_code,
        "rarity": LOT_RARITY,
        "ends_at": auction.ends_at.isoformat(),
        "top_bid": auction.top_bid,
        "min_bid": auction.top_bid + MIN_STEP if auction.top_bid else START_BID,
        "step": MIN_STEP,
        "leader": (leader.username or leader.first_name) if leader else None,
        "mine": auction.top_user_id == user.id,
    }


async def bid(session: AsyncSession, user_id: int, amount: int) -> dict:
    auction = await current(session)
    minimum = auction.top_bid + MIN_STEP if auction.top_bid else START_BID
    if amount < minimum:
        raise GameError(f"минимальная ставка {minimum}")

    bidder = await lock_user(session, user_id)
    if bidder.coins < amount:
        raise GameError("не хватает рублей на ставку")

    previous = auction.top_user_id
    if previous:
        prev_user = await lock_user(session, previous)
        await apply_delta(session, prev_user, auction.top_bid, "auction_refund", ref=str(auction.id))

    await apply_delta(session, bidder, -amount, "auction_bid", ref=str(auction.id))
    auction.top_bid = amount
    auction.top_user_id = bidder.id

    return {"top_bid": amount, "coins": bidder.coins, "ends_at": auction.ends_at.isoformat()}


async def active_for(session: AsyncSession, user_id: int) -> Auction | None:
    return await session.scalar(
        select(Auction)
        .where(Auction.closed.is_(False), Auction.top_user_id == user_id)
        .order_by(Auction.id.desc())
    )


__all__ = ["bid", "current", "view", "active_for", "MIN_STEP", "START_BID"]
