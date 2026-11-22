from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import admin as admin_service
from app.api.deps import current_user
from app.api.serializers import plate_json
from app.db import get_session
from app.economy import GameError
from app.models import User
from app.plates import COUNTRIES

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="доступ только для админа")
    return user


@router.get("/meta")
async def meta(_: User = Depends(admin_user)) -> dict:
    return {
        "rarities": admin_service.rarities(),
        "countries": [
            {"code": code, "title": data["title"], "flag": data["flag"]}
            for code, data in COUNTRIES.items()
        ],
    }


@router.get("/users")
async def users(
    q: str = "",
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"items": await admin_service.list_users(session, q)}


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await admin_service.detail(session, user_id)
    except GameError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.post("/grant")
async def grant(
    payload: dict,
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        user_id = int(payload.get("user_id"))
        amount = int(payload.get("amount"))
        result = await admin_service.grant(session, user_id, str(payload.get("currency")), amount)
        await session.commit()
    except (TypeError, ValueError):
        await session.rollback()
        raise HTTPException(status_code=400, detail="некорректные данные") from None
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/plate")
async def give_plate(
    payload: dict,
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        user_id = int(payload.get("user_id"))
        plate = await admin_service.give_plate(
            session, user_id, str(payload.get("rarity")), str(payload.get("country", "RU"))
        )
        await session.commit()
    except (TypeError, ValueError):
        await session.rollback()
        raise HTTPException(status_code=400, detail="некорректные данные") from None
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return {"plate": plate_json(plate)}


@router.post("/ban")
async def ban(
    payload: dict,
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        user_id = int(payload.get("user_id"))
        result = await admin_service.set_ban(session, user_id, bool(payload.get("banned")))
        await session.commit()
    except (TypeError, ValueError):
        await session.rollback()
        raise HTTPException(status_code=400, detail="некорректные данные") from None
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/cleanup")
async def cleanup(
    _: User = Depends(admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    removed = await admin_service.cleanup_legacy(session)
    await session.commit()
    return {"removed": removed}
