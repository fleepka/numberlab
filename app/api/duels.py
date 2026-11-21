from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.serializers import plate_json
from app.db import get_session
from app.game import GameError, cancel_duel, create_duel, join_duel
from app.models import Duel, User

router = APIRouter(prefix="/api/duels", tags=["duels"])


class DuelCreate(BaseModel):
    bet: int = Field(gt=0)


def duel_json(
    duel: Duel,
    username: str | None = None,
    plates: list | None = None,
) -> dict:
    payload = {
        "id": duel.id,
        "bet": duel.bet,
        "status": duel.status,
        "creator_id": duel.creator_id,
        "creator": username,
        "opponent_id": duel.opponent_id,
        "winner_id": duel.winner_id,
        "created_at": duel.created_at.isoformat() if duel.created_at else None,
    }
    if plates is not None:
        payload["plates"] = [plate_json(p) for p in plates]
    return payload


@router.get("")
async def list_duels(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    open_rows = await session.execute(
        select(Duel, User.username)
        .join(User, User.id == Duel.creator_id)
        .where(Duel.status == "open")
        .order_by(Duel.id.desc())
        .limit(30)
    )
    mine_rows = await session.execute(
        select(Duel, User.username)
        .join(User, User.id == Duel.creator_id)
        .where(
            (Duel.creator_id == user.id) | (Duel.opponent_id == user.id)
        )
        .order_by(Duel.id.desc())
        .limit(30)
    )
    return {
        "open": [duel_json(d, name) for d, name in open_rows],
        "mine": [duel_json(d, name) for d, name in mine_rows],
    }


@router.post("")
async def create(
    body: DuelCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        duel = await create_duel(session, user.id, body.bet)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"duel": duel_json(duel, user.username), "coins": user.coins}


@router.post("/{duel_id}/join")
async def join(
    duel_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        duel, creator_plate, opponent_plate, payout = await join_duel(session, user.id, duel_id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    winner = duel.winner_id
    return {
        "duel": duel_json(duel),
        "plates": [plate_json(creator_plate), plate_json(opponent_plate)],
        "winner_id": winner,
        "you_won": winner == user.id,
        "payout": payout,
        "coins": user.coins,
    }


@router.post("/{duel_id}/cancel")
async def cancel(
    duel_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await cancel_duel(session, user.id, duel_id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"ok": True, "coins": user.coins}
