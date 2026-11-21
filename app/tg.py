from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import LabeledPrice

from app.config import settings

bot: Bot | None = None
if settings.bot_token:
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))


async def stars_invoice(title: str, description: str, payload: str, stars: int) -> str:
    if bot is None:
        raise RuntimeError("BOT_TOKEN is not configured")
    return await bot.create_invoice_link(
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=stars)],
    )
