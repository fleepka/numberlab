from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthError, get_or_create_user, verify_init_data
from app.config import settings
from app.db import get_session
from app.models import User


async def current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    init_data = request.headers.get("x-init-data", "")
    dev_id = request.headers.get("x-dev-user", "")
    start_param = request.headers.get("x-start-param", "") or None

    try:
        if settings.dev_mode and dev_id and not init_data:
            payload = {
                "id": int(dev_id),
                "first_name": f"Dev {dev_id}",
                "username": f"dev{dev_id}",
            }
        else:
            payload = verify_init_data(init_data, settings.bot_token)
    except (AuthError, ValueError):
        raise HTTPException(status_code=401, detail="unauthorized") from None

    user = await get_or_create_user(session, payload, start_param)
    await session.commit()

    if user.is_banned:
        raise HTTPException(status_code=403, detail="account is banned")
    return user
