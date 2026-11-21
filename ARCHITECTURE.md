# NUMBERLAB — архитектура

## Принципы

1. Сервер — единственный источник правды: номер, редкость, цена, баланс, результат дуэли считаются на бэкенде.
2. Любое движение валюты проходит через `economy.apply_delta` и попадает в `transactions`.
3. Каждая операция, которую можно повторить (покупка, награда, дуэль), защищена блокировкой строки или уникальным ключом.
4. Клиент только отображает состояние и отправляет намерения.

## Структура проекта

```
app/
  main.py         FastAPI, lifespan, вебхук, статика Mini App
  config.py       настройки из окружения
  db.py           движок, сессии, создание схемы
  models.py       все таблицы
  plates.py       генерация, редкость, цена, разбор ценности
  progress.py     опыт и уровни
  collections.py  правила коллекций, прогресс, выдача наград, сид
  economy.py      ledger, блокировки, идемпотентность
  game.py         спин, инвентарь, дуэли, ежедневная награда
  shop.py         витрина и выдача номера после оплаты
  auth.py         проверка Telegram initData
  bot.py          aiogram: /start, оплата, выдача
  tg.py           бот и createInvoiceLink
  api/
    deps.py       текущий пользователь
    routes.py     профиль, спин, инвентарь, коллекции, история
    duels.py      матчи
    shop.py       витрина и счёт
    serializers.py
web/              Mini App: React + TS + Vite
tests/            pytest
scripts/smoke.py
```

## Схема базы данных

### `users`
| поле | тип | примечание |
|---|---|---|
| id | PK | |
| tg_id | bigint, unique, index | Telegram ID |
| username, first_name, photo_url | text | профиль |
| coins | int | игровая валюта, `>= 0` |
| gems | int | премиальная валюта, `>= 0` |
| xp, level | int | прогрессия |
| spins | int | сколько номеров получено |
| duels_won, duels_lost | int | статистика |
| best_score | int | лучший номер |
| streak | int | серия ежедневных наград |
| last_spin_at, last_daily_at | timestamptz | кулдауны |
| is_admin, is_banned | bool | права и блокировка |

### `plates`
Один физический номер = одна строка, `code` уникален глобально.

| поле | тип | примечание |
|---|---|---|
| id | PK | |
| code | varchar(16), unique, index | `А777АА77` |
| digits, letters, region | text | части номера |
| score | int | сумма факторов |
| price | int | цена в COINS |
| rarity | varchar(16) | `common … unique` |
| stars | int | цена в Stars |
| owner_id | FK users, nullable, index | `NULL` — номер свободен |
| is_paid | bool | куплен за звёзды, не продаётся |
| source | varchar(16) | `spin`, `duel`, `shop` |

Индекс `(owner_id, price)` — инвентарь и сортировка.

### `transactions`
Единый журнал: `user_id`, `currency` (`coins`/`gems`), `delta`, `reason`, `ref`, `idem_key` (unique, nullable).

### `spins`
Лог спинов: `user_id`, `plate_id`, `cost`, `created_at`.

### `duels`
`bet`, `status` (`open`/`finished`/`tie`/`cancelled`), `creator_id`, `opponent_id`, `creator_plate_id`, `opponent_plate_id`, `winner_id`.

### `purchases`
Счёт за звёзды: `user_id`, `code`, `stars`, `payload` (unique), `status` (`pending`/`paid`/`failed`), `paid_at`.

### `daily_claims`
`user_id`, `day`, `amount`, unique `(user_id, day)`.

### `collections` / `user_collections`
Правило коллекции: `rule_kind`, `rule_value`, `target`; награды: `reward_coins`, `reward_gems`, `reward_xp`.
Факт получения: unique `(user_id, collection_id)`, `claimed_at`.

## Финансовая модель

- `lock_user` — `SELECT … FOR UPDATE` по строке пользователя.
- `lock_users` — блокировка пары по возрастанию id, чтобы встречные дуэли не дали дедлок.
- `apply_delta` — проверяет отрицательный баланс и пишет `transactions`; при `idem_key` повторная операция не проходит.
- Оплата Stars: `pending` → `createInvoiceLink` → `successful_payment` → `fulfil_purchase` под `FOR UPDATE`. Повторное уведомление не выдаёт номер второй раз.
- Дуэль: обе ставки списываются при создании/входе, победитель получает банк, при равенстве цены ставки возвращаются.

## Редкость и цена

`score` — сумма факторов:

| фактор | баллы |
|---|---|
| три одинаковые цифры | 9 |
| возрастающая последовательность | 5 |
| убывающая последовательность | 4 |
| палиндром | 4 |
| круглое `X00` | 4 |
| ведущие нули `00X` | 3 |
| пара одинаковых цифр | 3 |
| повтор букв | 2 |
| премиальный регион | 3 |
| крупный регион | 2 |

Порог редкости: `0–1 common`, `2–3 uncommon`, `4–5 rare`, `6–8 epic`, `9–11 legendary`, `12–13 mythic`, `14+ unique`.

Цена: `TIER_BASE[rarity] + 50 × score`. Факторы возвращаются в API, поэтому игрок видит, из чего сложилась стоимость.

## Коллекции

Правила: `triple`, `pair`, `palindrome`, `sequence`, `digits_exact`, `contains`, `prefix`, `region`, `rarity_min`.
Прогресс считается по текущему инвентарю, награда выдаётся один раз и фиксируется в `user_collections`.

## Энергия, задания и рейтинг

Спин сначала тратит энергию (`users.energy`, максимум 30, +1 каждые 10 минут), и только когда она кончилась — COINS.
Энергия начисляется лениво в `app/energy.py` (`regenerate` вызывается на `/api/me` и `/api/spin`), отдельного планировщика нет.

Задания живут в таблицах `tasks` и `task_progress`. Период — ключ: дата для `daily`, ISO-неделя для `weekly`, `once` для разовых.
События (`spin`, `sell`, `duel`, `daily`, `rare`, `collection`) вызывают `bump()` из `app/tasks.py`, прогресс обрезается на `target`.
Награда выдаётся один раз на период: `claimed_at` в `task_progress`, повторная выдача — ошибка.

Рейтинг (`app/rating.py`) считается на лету: сумма `price` номеров в гараже, порядок по сумме, затем по количеству. Хранимых снапшотов нет.

## API

| метод | путь | смысл |
|---|---|---|
| GET | `/api/me` | профиль, балансы, уровень |
| POST | `/api/spin` | получить номер |
| GET | `/api/garage` | инвентарь |
| POST | `/api/garage/{id}/sell` | продать номер |
| GET | `/api/collections` | коллекции и прогресс |
| POST | `/api/collections/{id}/claim` | забрать награду |
| GET | `/api/tasks` | задания и прогресс за период |
| POST | `/api/tasks/{code}/claim` | забрать награду задания |
| GET | `/api/rating` | топ по гаражам и личное место |
| GET | `/api/history` | журнал операций |
| GET | `/api/feed` | лента редких номеров |
| GET/POST | `/api/duels` | список и создание |
| POST | `/api/duels/{id}/join` | принять дуэль |
| POST | `/api/duels/{id}/cancel` | вернуть ставку |
| GET | `/api/shop` | витрина |
| POST | `/api/shop/buy` | счёт в Stars |
| POST | `/api/telegram/webhook` | вебхук бота |

## Дальше по этапам

- Этап 2: маркетплейс (`listings`, `sales`), история цен, комиссия.
- Этап 3: обмены, друзья, сезоны и рейтинги.
- Этап 4: задания и достижения.
- Этап 5: Premium, Season Pass, косметика, платежи.
- Этап 6: админ-панель, аналитика, жалобы.

Схема уже совместима с этими шагами: расширяем таблицы, не меняя финансовое ядро.
