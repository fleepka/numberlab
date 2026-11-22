from __future__ import annotations

from datetime import date, timedelta

from app.garage import GARAGE_MAX
from app.models import User

PRICE_STARS = 99
DAYS = 30
INCOME_BONUS = 1.5


def is_active(user: User) -> bool:
    return user.vip_until is not None and user.vip_until >= date.today()


def apply_vip(user: User) -> None:
    """Продлевает VIP на 30 дней и даёт +2 места в гараже (однократно за покупку)."""
    today = date.today()
    base = user.vip_until if user.vip_until and user.vip_until > today else today
    user.vip_until = base + timedelta(days=DAYS)
    user.garage_slots = min(GARAGE_MAX, user.garage_slots + 2)
