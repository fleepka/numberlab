from __future__ import annotations

from app.energy import ENERGY_MAX, next_in
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
        "country": plate.country,
        "score": plate.score,
        "price": plate.price,
        "stars": plate.stars,
        "is_paid": plate.is_paid,
        "source": plate.source,
        "factors": factors,
        "created_at": plate.created_at.isoformat() if plate.created_at else None,
    }


def user_json(user: User) -> dict:
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "photo_url": user.photo_url,
        "coins": user.coins,
        "gems": user.gems,
        "energy": user.energy,
        "energy_max": ENERGY_MAX,
        "energy_in": next_in(user),
        "xp": user.xp,
        "level": user.level,
        "xp_to_next": xp_to_next(user.xp),
        "is_admin": user.is_admin,
        "spins": user.spins,
        "duels_won": user.duels_won,
        "duels_lost": user.duels_lost,
        "best_score": user.best_score,
        "streak": user.streak,
        "garage_slots": user.garage_slots,
        "season_points": user.season_points,
        "pass_premium": user.pass_premium,
        "vip_until": user.vip_until.isoformat() if user.vip_until else None,
        "frame": user.frame,
        "theme": user.theme,
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
