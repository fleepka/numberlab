# NUMBERLAB

Telegram Mini App: лаборатория виртуальных номерных знаков. Крути номера, собирай коллекции, копи редкости, играй дуэли «у кого номер дороже» и покупай конкретные комбинации за Telegram Stars.

Игровые номера — вымышленные объекты. Денег внутри нет: COINS и GEMS нельзя купить за рубли и нельзя вывести. Stars тратятся только на конкретный номер из витрины, без случайных наборов.

## Что есть

- Авторизация через Telegram `initData` с серверной проверкой подписи
- Спин: тратит энергию (30 максимум, +1 каждые 10 минут), при нуле — за COINS
- Семь категорий редкости: common → uncommon → rare → epic → legendary → mythic → unique
- Объяснение цены: сервер возвращает факторы, из которых сложилась стоимость
- Инвентарь: сортировка по цене, продажа, пометка купленных за звёзды
- Коллекции: 12 правил с прогрессом и наградами, выдача ровно один раз
- Дуэли 1×1 с серверным результатом, возвратом ставки и защитой от встречных блокировок
- Витрина на день: 9 номеров, покупка через Telegram Invoice (XTR)
- Уровни и XP за спины, продажи, дуэли и коллекции
- GEMS как премиальная валюта за коллекции, с отдельным журналом
- Лента редких выпадений
- Задания: ежедневные, еженедельные и разовые, с прогрессом от спинов, продаж, дуэлей и коллекций
- Рейтинг: топ игроков по стоимости гаража и личное место

## Стек

- Backend: Python 3.11, FastAPI, aiogram 3, SQLAlchemy 2 (async), PostgreSQL
- Frontend: React 18 + TypeScript + Vite, Telegram WebApp SDK
- Тесты: pytest + pytest-asyncio + httpx
- Деплой: Docker, Railway

## Экономика

| валюта | как получить | куда тратить |
|---|---|---|
| COINS | спины, продажи, дуэли, ежедневная награда | спины, ставки |
| GEMS | награды за коллекции | косметика (следующие этапы) |
| Stars | покупаются в Telegram | конкретный номер в витрине |

Стартовый баланс — 1500 COINS. Ставка в дуэли — от 100 до 100 000. Купленный за звёзды номер помечается `is_paid`, не продаётся и не обменивается, поэтому реальные деньги не превращаются обратно в игровую валюту.

Формула цены и таблица факторов — в [ARCHITECTURE.md](ARCHITECTURE.md).

## Запуск

### Docker

```bash
docker compose up --build
```

Приложение: http://localhost:8000 (API и собранный Mini App на одном порту).

### Вручную

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Нужен PostgreSQL и `DATABASE_URL` вида `postgresql+asyncpg://postgres:postgres@localhost:5432/nomerok`.
Строка `postgresql://…` из Railway приводится к asyncpg автоматически.

### Mini App в разработке

```bash
cd web
npm install
npm run dev      # http://localhost:5173, /api проксируется на :8000
```

Продакшен-сборка кладётся в `web/dist` и раздаётся FastAPI:

```bash
cd web && npm run build
```

## Переменные окружения

| переменная | назначение |
|---|---|
| `DATABASE_URL` | подключение к PostgreSQL |
| `BOT_TOKEN` / `TELEGRAM_BOT_TOKEN` | токен бота |
| `ADMIN_ID` / `TELEGRAM_ADMIN_ID` | Telegram ID администратора |
| `WEBHOOK_SECRET` / `TELEGRAM_WEBHOOK_SECRET` | секрет заголовка вебхука |
| `PUBLIC_URL` | публичный HTTPS-адрес |
| `DEV_MODE` | вход по `X-Dev-User` без Telegram |

## Режим DEV

При `DEV_MODE=true` и пустом `initData` API принимает `X-Dev-User: <id>`. Mini App хранит такой id в `localStorage` — это только идентификатор отладки.

Без `BOT_TOKEN` кнопка «Забрать» выдаёт номер сразу и возвращает `dev: true`. В продакшене (`DEV_MODE=false`) путь отключён.

## Telegram

1. Бот у @BotFather → токен в `BOT_TOKEN`.
2. `PUBLIC_URL` — HTTPS-домен, Mini App подключается кнопкой меню.
3. Вебхук ставится при старте: `POST {PUBLIC_URL}/api/telegram/webhook` с секретным заголовком.
4. Оплата — `createInvoiceLink`, `currency=XTR`; зачисление только по `successful_payment`, повторное уведомление ничего не дублирует.

## Тесты

```bash
pip install -r requirements.txt pytest pytest-asyncio
pytest -q
```

21 тест: редкость и цена, факторы, авторизация, спин, продажа, ежедневная награда, дуэли с сохранением суммы балансов, коллекции (прогресс, повторная выдача, неготовность), XP, идемпотентность покупки, витрина.

Быстрая проверка статики и здоровья:

```bash
python scripts/smoke.py
```

## Railway

1. Репозиторий на GitHub → Railway → **Deploy from GitHub repo**.
2. Добавить **PostgreSQL**.
3. Переменные: `BOT_TOKEN`, `ADMIN_ID`, `WEBHOOK_SECRET`, `PUBLIC_URL`, `DEV_MODE=false`.
4. Networking → **Generate Domain**, домен должен совпасть с `PUBLIC_URL`.
5. Healthcheck `/healthz` уже в `railway.json`.

Схема создаётся при старте. Перед первым изменением таблиц в проде добавьте Alembic — отметка стоит в `app/db.py`.

## Безопасность

- `initData` проверяется HMAC-подписью с ограничением по `auth_date`
- баланс меняется только через `apply_delta` с блокировкой строки и записью в `transactions`
- отрицательный баланс невозможен
- покупки идемпотентны по `payload`, дуэль закрывается под `SELECT … FOR UPDATE`
- покупка номера выдаётся только после подтверждения платежа Telegram
- rate limit на `/api/*`

## Ограничения текущей версии

- Реализованы этапы 1–2 частично: ядро, инвентарь, коллекции, дуэли, витрина, опыт. Маркетплейс, обмены, сезоны, Premium/Pass и админ-панель — следующие этапы.
- Rate limit в памяти процесса: для нескольких реплик нужен Redis.
- `create_all` вместо миграций.
- Проверено тестами и сборкой; живой платёж Stars и вебхук требуют токена бота и HTTPS-домена.
