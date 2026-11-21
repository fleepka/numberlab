from __future__ import annotations

from app.economy import now
from app.game import next_spin_at
from app.models import Plate, Transaction, User
from app.plates import RARITY_LABELS, parse_code
from app.progress import xp_to_next


def plate_json(plate: Plate) -> dict:
    try:
        value = parse_code(plate.code)
        factors = [{"title": factor.title, "points": factor.points} for factor in value.factors]
    except ValueError:
        factors = []

    return {
        "id": plate.id,
        "code": plate.code,
        "rarity": plate.rarity,
        "rarity_label": RARITY_LABELS.get(plate.rarity, plate.rarity),
        "score": plate.score,
        "price": plate.price,
        "stars": plate.stars,
        "is_paid": plate.is_paid,
        "source": plate.source,
        "factors": factors,
        "created_at": plate.created_at.isoformat() if plate.created_at else None,
    }


def spin_ready_in(user: User) -> int:
    ready = next_spin_at(user)
    if ready is None:
        return 0
    return max(0, int((ready - now()).total_seconds()))


def user_json(user: User) -> dict:
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "photo_url": user.photo_url,
        "coins": user.coins,
        "gems": user.gems,
        "xp": user.xp,
        "level": user.level,
        "xp_to_next": xp_to_next(user.xp),
        "is_admin": user.is_admin,
        "spins": user.spins,
        "duels_won": user.duels_won,
        "duels_lost": user.duels_lost,
        "best_score": user.best_score,
        "streak": user.streak,
        "spin_ready_in": spin_ready_in(user),
    }


def tx_json(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "currency": tx.currency,
        "delta": tx.delta,
        "reason": tx.reason,
        "ref": tx.ref,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }
