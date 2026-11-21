from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import User

ENERGY_MAX = 30
REGEN_MINUTES = 10


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def now() -> datetime:
    return datetime.now(timezone.utc)


def regenerate(user: User, moment: datetime | None = None) -> int:
    """Догоняет энергию до текущего момента. Возвращает, сколько добавилось."""
    moment = moment or now()
    before = user.energy

    if user.energy >= ENERGY_MAX:
        user.energy = ENERGY_MAX
        user.energy_at = moment
        return 0

    if user.energy_at is None:
        user.energy_at = moment
        return 0

    start = _aware(user.energy_at)
    gained = int((moment - start).total_seconds() // (REGEN_MINUTES * 60))
    if gained <= 0:
        return 0

    user.energy = min(ENERGY_MAX, user.energy + gained)
    if user.energy >= ENERGY_MAX:
        user.energy_at = moment
    else:
        user.energy_at = start + timedelta(minutes=gained * REGEN_MINUTES)
    return user.energy - before


def next_in(user: User, moment: datetime | None = None) -> int:
    """Секунд до следующей единицы энергии."""
    if user.energy >= ENERGY_MAX or user.energy_at is None:
        return 0
    moment = moment or now()
    block = REGEN_MINUTES * 60
    passed = (moment - _aware(user.energy_at)).total_seconds()
    return max(0, int(block - passed % block))


def add(user: User, amount: int) -> int:
    if amount <= 0:
        return 0
    before = user.energy
    user.energy = min(ENERGY_MAX, user.energy + amount)
    return user.energy - before
