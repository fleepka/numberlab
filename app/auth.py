from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.energy import ENERGY_MAX
from app.models import User


class AuthError(Exception):
    pass


def verify_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """Проверка подписи Telegram WebApp initData.

    Схема из документации Telegram: secret = HMAC(b"WebAppData", bot_token),
    затем HMAC-SHA256 от отсортированной строки data_check_string.
    """
    if not init_data:
        raise AuthError("empty init data")
    if not bot_token:
        raise AuthError("BOT_TOKEN is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise AuthError("no hash in init data")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise AuthError("bad signature")

    if max_age:
        try:
            issued = int(pairs.get("auth_date", "0"))
        except ValueError:
            raise AuthError("bad auth_date") from None
        if time.time() - issued > max_age:
            raise AuthError("init data expired")

    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError:
        raise AuthError("bad user payload") from None
    if "id" not in user:
        raise AuthError("no user in init data")
    return user


async def get_or_create_user(session: AsyncSession, data: dict) -> User:
    tg_id = int(data["id"])
    user = await session.scalar(select(User).where(User.tg_id == tg_id))

    if user is None:
        user = User(
            tg_id=tg_id,
            coins=settings.start_balance,
            energy=ENERGY_MAX,
            is_admin=bool(settings.admin_id) and tg_id == settings.admin_id,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError:
            # Параллельный первый вход того же пользователя — забираем существующую запись.
            await session.rollback()
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if user is None:
                raise

    user.username = data.get("username")
    user.first_name = data.get("first_name") or user.first_name or ""
    if data.get("photo_url"):
        user.photo_url = data["photo_url"]
    return user
