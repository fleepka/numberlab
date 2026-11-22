from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.serializers import plate_json
from app.config import settings
from app.db import get_session
from app.models import Plate, User
from app.shop import (
    ENERGY_PACKS,
    TICKET_PRICES,
    ShopError,
    buy_energy,
    buy_ticket,
    fulfil_purchase,
    offers_for,
    prepare_purchase,
)
from app.tg import bot, stars_invoice

router = APIRouter(prefix="/api/shop", tags=["shop"])


class BuyRequest(BaseModel):
    code: str


@router.get("")
async def shop(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    values = offers_for(user.id, date.today())
    taken = set(
        await session.scalars(
            select(Plate.code).where(Plate.code.in_([v.code for v in values]))
        )
    )
    return {
        "offers": [
            {
                "code": v.code,
                "rarity": v.rarity,
                "score": v.score,
                "price": v.price,
                "stars": v.stars,
            }
            for v in values
            if v.code not in taken
        ],
        "energy_packs": [
            {"code": code, "energy": item["energy"], "price": item["price"]}
            for code, item in ENERGY_PACKS.items()
        ],
        "ticket_prices": TICKET_PRICES,
    }


@router.post("/energy")
async def buy_energy_view(
    body: dict,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.economy import GameError

    try:
        result = await buy_energy(session, user.id, str(body.get("pack", "")))
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/ticket")
async def buy_ticket_view(
    body: dict,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.economy import GameError

    try:
        result = await buy_ticket(session, user.id, str(body.get("rarity", "")))
        await session.commit()
    except GameError as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    return result


@router.post("/buy")
async def buy(
    body: BuyRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        purchase = await prepare_purchase(session, user, body.code)
    except ShopError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    try:
        url = await stars_invoice(
            title=f"Номер {purchase.code}",
            description="Личный номерной знак в коллекцию НОМЕРОК",
            payload=purchase.payload,
            stars=purchase.stars,
        )
    except RuntimeError:
        if not settings.dev_mode:
            await session.rollback()
            raise HTTPException(status_code=503, detail="оплата временно недоступна") from None
        # DEV без токена бота: номер выдаётся сразу, чтобы витрину можно было проверить локально.
        plate = await fulfil_purchase(session, purchase.payload)
        await session.commit()
        return {"dev": True, "invoice_url": None, "plate": plate_json(plate) if plate else None}

    await session.commit()
    return {"dev": False, "invoice_url": url, "payload": purchase.payload}
