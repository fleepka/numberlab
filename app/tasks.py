from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import GameError, apply_delta, lock_user, now
from app.energy import add as add_energy
from app.models import Task, TaskProgress, User
from app.passes import POINTS_TASK
from app.progress import award_xp
from app.tickets import grant as grant_ticket

DEFAULT_TASKS: list[dict] = [
    {
        "code": "daily_spin_5",
        "title": "Крутани 5 номеров",
        "description": "Любые крутки на главной",
        "kind": "daily",
        "metric": "spin",
        "target": 5,
        "reward_coins": 100,
        "reward_energy": 5,
        "reward_gems": 0,
        "sort": 10,
    },
    {
        "code": "daily_sell_3",
        "title": "Продай 3 номера",
        "description": "Из гаража за игровые монеты",
        "kind": "daily",
        "metric": "sell",
        "target": 3,
        "reward_coins": 120,
        "reward_energy": 0,
        "reward_gems": 0,
        "sort": 20,
    },
    {
        "code": "daily_duel_1",
        "title": "Сыграй дуэль",
        "description": "Создай вызов или прими чужой",
        "kind": "daily",
        "metric": "duel",
        "target": 1,
        "reward_coins": 80,
        "reward_energy": 3,
        "reward_gems": 0,
        "sort": 30,
    },
    {
        "code": "daily_bonus_1",
        "title": "Забери ежедневную награду",
        "description": "Серия растёт каждый день",
        "kind": "daily",
        "metric": "daily",
        "target": 1,
        "reward_coins": 50,
        "reward_energy": 0,
        "reward_gems": 0,
        "sort": 40,
    },
    {
        "code": "daily_rare_1",
        "title": "Получи редкий номер",
        "description": "Редкость rare и выше",
        "kind": "daily",
        "metric": "rare",
        "target": 1,
        "reward_coins": 150,
        "reward_energy": 0,
        "reward_gems": 1,
        "reward_ticket": "rare",
        "sort": 50,
    },
    {
        "code": "weekly_spin_25",
        "title": "25 круток за неделю",
        "description": "Держи темп до конца недели",
        "kind": "weekly",
        "metric": "spin",
        "target": 25,
        "reward_coins": 500,
        "reward_energy": 10,
        "reward_gems": 0,
        "sort": 110,
    },
    {
        "code": "weekly_duel_5",
        "title": "5 дуэлей за неделю",
        "description": "Победы не обязательны",
        "kind": "weekly",
        "metric": "duel",
        "target": 5,
        "reward_coins": 400,
        "reward_energy": 0,
        "reward_gems": 0,
        "sort": 120,
    },
    {
        "code": "weekly_collection_1",
        "title": "Заверши коллекцию",
        "description": "Собери и забери награду",
        "kind": "weekly",
        "metric": "collection",
        "target": 1,
        "reward_coins": 600,
        "reward_energy": 0,
        "reward_gems": 2,
        "reward_ticket": "legendary",
        "sort": 130,
    },
    {
        "code": "first_plate",
        "title": "Первый номер",
        "description": "Крутани колесо впервые",
        "kind": "once",
        "metric": "spin",
        "target": 1,
        "reward_coins": 200,
        "reward_energy": 0,
        "reward_gems": 0,
        "sort": 210,
    },
    {
        "code": "ten_plates",
        "title": "Десять номеров",
        "description": "Коллекция начинается",
        "kind": "once",
        "metric": "spin",
        "target": 10,
        "reward_coins": 500,
        "reward_energy": 0,
        "reward_gems": 1,
        "sort": 220,
    },
]


def period_key(kind: str, today: date | None = None) -> str:
    today = today or date.today()
    if kind == "daily":
        return today.isoformat()
    if kind == "weekly":
        year, week, _ = today.isocalendar()
        return f"{year}-W{week:02d}"
    return "once"


async def bump(session: AsyncSession, user: User, metric: str, amount: int = 1) -> None:
    tasks = list(await session.scalars(select(Task).where(Task.is_active, Task.metric == metric)))
    for task in tasks:
        period = period_key(task.kind)
        row = await session.scalar(
            select(TaskProgress).where(
                TaskProgress.user_id == user.id,
                TaskProgress.task_id == task.id,
                TaskProgress.period == period,
            )
        )
        if row is None:
            row = TaskProgress(user_id=user.id, task_id=task.id, period=period, progress=0)
            session.add(row)
        if row.claimed_at is not None:
            continue
        row.progress = min(task.target, row.progress + amount)


async def catalog(session: AsyncSession, user_id: int) -> list[dict]:
    tasks = await session.scalars(select(Task).where(Task.is_active).order_by(Task.sort, Task.id))
    result = []
    for task in tasks:
        period = period_key(task.kind)
        row = await session.scalar(
            select(TaskProgress).where(
                TaskProgress.user_id == user_id,
                TaskProgress.task_id == task.id,
                TaskProgress.period == period,
            )
        )
        progress = min(task.target, row.progress if row else 0)
        result.append(
            {
                "code": task.code,
                "title": task.title,
                "description": task.description,
                "kind": task.kind,
                "target": task.target,
                "progress": progress,
                "done": progress >= task.target,
                "claimed": bool(row and row.claimed_at),
                "reward_coins": task.reward_coins,
                "reward_energy": task.reward_energy,
                "reward_gems": task.reward_gems,
            }
        )
    return result


async def claim(session: AsyncSession, user_id: int, code: str) -> dict:
    task = await session.scalar(select(Task).where(Task.code == code, Task.is_active))
    if task is None:
        raise GameError("задание не найдено")

    period = period_key(task.kind)
    row = await session.scalar(
        select(TaskProgress)
        .where(
            TaskProgress.user_id == user_id,
            TaskProgress.task_id == task.id,
            TaskProgress.period == period,
        )
        .with_for_update()
    )
    if row is None or row.progress < task.target:
        raise GameError("задание ещё не выполнено")
    if row.claimed_at is not None:
        raise GameError("награда уже получена")

    user = await lock_user(session, user_id)
    row.claimed_at = now()

    if task.reward_coins:
        await apply_delta(session, user, task.reward_coins, "task", ref=task.code)
    if task.reward_gems:
        await apply_delta(session, user, task.reward_gems, "task", currency="gems", ref=task.code)
    add_energy(user, task.reward_energy)
    if task.reward_ticket:
        await grant_ticket(session, user.id, task.reward_ticket)
    user.season_points += POINTS_TASK
    award_xp(user, 20)

    return {
        "code": task.code,
        "coins": user.coins,
        "gems": user.gems,
        "energy": user.energy,
        "rewards": {
            "coins": task.reward_coins,
            "energy": task.reward_energy,
            "gems": task.reward_gems,
            "ticket": task.reward_ticket or None,
        },
    }


async def seed(session: AsyncSession) -> int:
    existing = set(await session.scalars(select(Task.code)))
    added = 0
    for item in DEFAULT_TASKS:
        if item["code"] in existing:
            continue
        session.add(Task(**item))
        added += 1
    return added
