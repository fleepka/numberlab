from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import tickets as ticket_service
from app.api.deps import current_user
from app.api.serializers import plate_json, tx_json, user_json
from app.db import get_session
from app.craft import craft
from app.collections import catalog as collections_catalog
from app.collections import claim as claim_collection
from app.economy import history
from app.energy import next_in, regenerate
from app.friends import invite_link, ladder_view
from app.rating import leaderboard, position
from app.tasks import catalog as tasks_catalog
from app.tasks import claim as claim_task
from app.game import GameError, claim_daily, sell_plate, spin
from app.garage import claim_income, income_state, sell_many
from app.models import Plate, User
from app.plates import STAKES

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/me")
async def me(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)) -> dict:
    regenerate(user)
    await session.commit()
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
        "stakes": STAKES,
    }


@router.post("/spin")
async def do_spin(
    tier: str | None = None,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        plate, cost, used_tier = await spin(session, user.id, tier)
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
        "tier": used_tier,
        "coins": user.coins,
        "energy": user.energy,
        "energy_in": next_in(user),
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
    return {"plates": [plate_json(p) for p in plates], "income": await income_state(session, user)}


@router.post("/garage/sell")
async def sell_batch(
    payload: dict,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not all(isinstance(item, int) for item in ids):
        raise HTTPException(status_code=400, detail="ожидается список id")
    try:
        result = await sell_many(session, user.id, ids)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/garage/income")
async def collect_income(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        result = await claim_income(session, user.id)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/garage/craft")
async def craft_plates(
    payload: dict,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not all(isinstance(item, int) for item in ids):
        raise HTTPException(status_code=400, detail="ожидается список id")
    try:
        result = await craft(session, user.id, ids)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return {
        "plate": plate_json(result["plate"]),
        "spent": result["spent"],
        "value": result["value"],
        "target": result["target"],
        "target_label": result["target_label"],
    }


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


@router.get("/tasks")
async def tasks_view(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await tasks_catalog(session, user.id)}


@router.post("/tasks/{code}/claim")
async def claim_task_view(
    code: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        result = await claim_task(session, user.id, code)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None

    return result


@router.get("/friends")
async def friends_view(user: User = Depends(current_user)) -> dict:
    return {
        "invites": user.invites,
        "link": invite_link(user.tg_id),
        "ladder": ladder_view(user.invites),
    }


@router.get("/rating")
async def rating_view(
    period: str = "season",
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    period = "week" if period == "week" else "season"
    return {
        "period": period,
        "items": await leaderboard(session, period=period),
        "me": await position(session, user.id, period),
    }


@router.get("/tickets")
async def tickets_view(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await ticket_service.list_for(session, user.id)}


@router.post("/tickets/use")
async def use_ticket(
    payload: dict,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rarity = str(payload.get("rarity", ""))
    try:
        result = await ticket_service.use(session, user.id, rarity)
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return {
        "plate": plate_json(result["plate"]),
        "left": result["left"],
        "coins": result["coins"],
    }


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
