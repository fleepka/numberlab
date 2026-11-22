from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user
from app.energy import add as add_energy
from app.models import Promo, PromoUse, User
from app.tickets import grant as grant_ticket

DEFAULT_PROMOS = [
    {
        "code": "NUMBERLAB",
        "kind": "coins",
        "value": 5000,
        "ticket": "",
        "uses_left": 1000,
        "per_user": 1,
    },
    {
        "code": "START",
        "kind": "coins",
        "value": 2500,
        "ticket": "",
        "uses_left": 5000,
        "per_user": 1,
    },
    {
        "code": "GOLD",
        "kind": "gems",
        "value": 25,
        "ticket": "",
        "uses_left": 500,
        "per_user": 1,
    },
    {
        "code": "ENERGY",
        "kind": "energy",
        "value": 100,
        "ticket": "",
        "uses_left": 500,
        "per_user": 1,
    },
    {
        "code": "MYTHIC",
        "kind": "ticket",
        "value": 0,
        "ticket": "mythic",
        "uses_left": 50,
        "per_user": 1,
    },
]


async def seed(session: AsyncSession) -> int:
    existing = set(await session.scalars(select(Promo.code)))
    added = 0
    for item in DEFAULT_PROMOS:
        if item["code"] in existing:
            continue
        session.add(Promo(**item))
        added += 1
    return added


def normalize(code: str) -> str:
    return code.strip().upper()


async def redeem(session: AsyncSession, user: User, code: str) -> dict:
    key = normalize(code)
    if not key:
        raise GameError("введи код")

    promo = await session.scalar(
        select(Promo).where(Promo.code == key, Promo.active).with_for_update()
    )
    if promo is None:
        raise GameError("такого промокода нет")
    if promo.uses_left <= 0:
        raise GameError("промокод закончился")

    used = await session.scalar(
        select(PromoUse.id).where(PromoUse.user_id == user.id, PromoUse.promo_id == promo.id)
    )
    if used is not None:
        raise GameError("ты уже активировал этот код")

    session.add(PromoUse(user_id=user.id, promo_id=promo.id))
    promo.uses_left -= 1

    locked = await lock_user(session, user.id)
    given = {"kind": promo.kind, "value": promo.value, "ticket": promo.ticket}

    if promo.kind == "coins":
        await apply_delta(session, locked, promo.value, "promo", ref=promo.code)
    elif promo.kind == "gems":
        await apply_delta(session, locked, promo.value, "promo", currency="gems", ref=promo.code)
    elif promo.kind == "energy":
        add_energy(locked, promo.value)
    elif promo.kind == "ticket":
        await grant_ticket(session, locked.id, promo.ticket or "rare")

    return {
        "code": promo.code,
        "given": given,
        "coins": locked.coins,
        "gems": locked.gems,
        "energy": locked.energy,
    }
