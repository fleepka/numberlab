from __future__ import annotations

from app.models import User

XP_PER_LEVEL = 400
MAX_LEVEL = 100


def level_for(xp: int) -> int:
    return min(MAX_LEVEL, 1 + max(0, xp) // XP_PER_LEVEL)


def xp_to_next(xp: int) -> int:
    level = level_for(xp)
    if level >= MAX_LEVEL:
        return 0
    return level * XP_PER_LEVEL - xp


def award_xp(user: User, amount: int) -> None:
    if amount <= 0:
        return
    user.xp += amount
    user.level = level_for(user.xp)
