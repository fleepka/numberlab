from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.serializers import plate_json, spin_ready_in, tx_json, user_json
from app.db import get_session
from app.collections import catalog as collections_catalog
from app.collections import claim as claim_collection
from app.economy import history
from app.game import GameError, claim_daily, sell_plate, spin
from app.models import Plate, User

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/me")
async def me(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)) -> dict:
    garage_count = await session.scalar(
        select(func.count(Plate.id)).where(Plate.owner_id == user.id)
    )
    top = await session.scalars(
        select(Plate).where(Plate.owner_id == user.id).order_by(Plate.price.desc()).limit(5)
    )
    return {
        "user": user_json(user),
        "garage_count": garage_count or 0,
        "top": [plate_json(p) for p in top],
    }


@router.post("/spin")
async def do_spin(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        plate, cost = await spin(session, user.id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    except Exception:
        await session.rollback()
        raise

    return {
        "plate": plate_json(plate),
        "cost": cost,
        "coins": user.coins,
        "spin_ready_in": spin_ready_in(user),
    }


@router.post("/daily")
async def daily(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        amount = await claim_daily(session, user.id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"amount": amount, "coins": user.coins, "streak": user.streak}


@router.get("/garage")
async def garage(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    plates = await session.scalars(
        select(Plate)
        .where(Plate.owner_id == user.id)
        .order_by(Plate.price.desc(), Plate.id.desc())
        .limit(300)
    )
    return {"plates": [plate_json(p) for p in plates]}


@router.post("/garage/{plate_id}/sell")
async def sell(
    plate_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        amount = await sell_plate(session, user.id, plate_id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"amount": amount, "coins": user.coins}


@router.get("/history")
async def history_view(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = await history(session, user.id)
    return {"items": [tx_json(tx) for tx in rows]}


@router.get("/collections")
async def collections_view(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await collections_catalog(session, user.id)}


@router.post("/collections/{collection_id}/claim")
async def claim_collection_view(
    collection_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        result = await claim_collection(session, user.id, collection_id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return result


@router.get("/feed")
async def feed(session: AsyncSession = Depends(get_session)) -> dict:
    rows = await session.execute(
        select(Plate, User.username, User.first_name)
        .join(User, User.id == Plate.owner_id)
        .where(Plate.owner_id.is_not(None), Plate.score >= 9)
        .order_by(Plate.id.desc())
        .limit(15)
    )
    return {
        "items": [
            {
                "code": plate.code,
                "rarity": plate.rarity,
                "score": plate.score,
                "owner": username or first_name or "игрок",
            }
            for plate, username, first_name in rows
        ]
    }
