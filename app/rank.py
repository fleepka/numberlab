from __future__ import annotations

RANKS: list[tuple[int, str]] = [
    (0, "Новичок"),
    (150_000, "Коллекционер"),
    (750_000, "Эксперт"),
    (3_000_000, "Мастер"),
    (12_000_000, "Легенда"),
    (50_000_000, "Магнат"),
]


def rank_for(total: int) -> dict:
    index = 0
    for position, (need, _) in enumerate(RANKS):
        if total >= need:
            index = position

    need, title = RANKS[index]
    following = RANKS[index + 1] if index + 1 < len(RANKS) else None
    span = following[0] - need if following else 0
    progress = 100 if following is None else int(100 * (total - need) / span)

    return {
        "title": title,
        "index": index,
        "total": total,
        "next": following[0] if following else None,
        "next_title": following[1] if following else None,
        "progress": max(0, min(100, progress)),
    }
