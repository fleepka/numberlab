from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.duels import router as duels_router
from app.api.routes import router as routes_router
from app.api.shop import router as shop_router
from app.bot import dp
from app.collections import seed as seed_collections
from app.config import settings
from app.promo import seed as seed_promos
from app.tasks import seed as seed_tasks
from app.db import SessionLocal, init_db
from app.ratelimit import Limiter
from app.tg import bot

limiter = Limiter(limit=120, window=60)
DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        await seed_collections(session)
        await seed_tasks(session)
        await seed_promos(session)
        await session.commit()
    if bot is not None and settings.public_url.startswith("https://"):
        webhook = settings.public_url.rstrip("/") + "/api/telegram/webhook"
        await bot.set_webhook(
            webhook,
            secret_token=settings.webhook_secret or None,
            drop_pending_updates=False,
        )
    yield
    if bot is not None:
        await bot.session.close()


app = FastAPI(title="NUMBERLAB", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_url] if settings.public_url else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_router)
app.include_router(duels_router)
app.include_router(shop_router)
app.include_router(admin_router)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/telegram/"):
        key = request.headers.get("x-dev-user") or (
            request.client.host if request.client else "anon"
        )
        if not limiter.allow(key):
            return JSONResponse({"detail": "too many requests"}, status_code=429)
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "app": "nomerok"}


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    if bot is None:
        raise HTTPException(status_code=503, detail="bot is not configured")

    if settings.webhook_secret:
        token = request.headers.get("x-telegram-bot-api-secret-token", "")
        if token != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="forbidden")

    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:

    @app.get("/")
    async def index() -> dict:
        return {
            "app": "nomerok",
            "hint": "Соберите Mini App: cd web && npm install && npm run build",
        }
