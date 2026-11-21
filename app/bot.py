from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)

from app.config import settings
from app.db import SessionLocal
from app.shop import fulfil_purchase

dp = Dispatcher()


def app_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть NUMBERLAB",
                    web_app=WebAppInfo(url=settings.public_url),
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "<b>NUMBERLAB</b>\n"
        "Лаборатория номерных знаков: крути, собирай коллекции и вызывай других на дуэль.\n\n"
        "Внутри — спин, инвентарь, коллекции, дуэли и витрина номеров за звёзды.",
        reply_markup=app_button(),
    )


@dp.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    payment = message.successful_payment
    async with SessionLocal() as session:
        plate = await fulfil_purchase(session, payment.invoice_payload)
        await session.commit()

    if plate is not None:
        await message.answer(f"Оплата прошла. Номер <b>{plate.code}</b> уже в гараже.")
    else:
        await message.answer("Платёж получен. Номер уже выдан ранее — напишите в поддержку.")
