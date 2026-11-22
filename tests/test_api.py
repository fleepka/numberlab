from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db import SessionLocal
from app.energy import ENERGY_MAX
from app.models import Collection, Hunt, Plate, Ticket, User, UserHunt
from app.shop import offers_for


def headers(uid: str) -> dict[str, str]:
    return {"X-Dev-User": uid}


async def get_me(client, uid: str) -> dict:
    response = await client.get("/api/me", headers=headers(uid))
    assert response.status_code == 200, response.text
    return response.json()


async def test_auth_required(client):
    response = await client.get("/api/me")
    assert response.status_code == 401


async def test_user_created_with_start_balance(client):
    data = await get_me(client, "1001")
    assert data["user"]["coins"] == 1500
    assert data["user"]["tg_id"] == 1001


async def test_spin_spends_energy_first(client):
    first = (await client.post("/api/spin", headers=headers("1100"))).json()
    assert first["cost"] == 0
    assert first["coins"] == 1500
    assert first["energy"] == ENERGY_MAX - 1

    second = (await client.post("/api/spin", headers=headers("1100"))).json()
    assert second["cost"] == 0
    assert second["coins"] == 1500
    assert second["energy"] == ENERGY_MAX - 2
    assert second["plate"]["code"] != first["plate"]["code"]


async def test_spin_costs_coins_without_energy(client):
    await get_me(client, "1101")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1101))
        user.energy = 0
        user.coins = 5000
        await session.commit()

    paid = (await client.post("/api/spin?tier=common", headers=headers("1101"))).json()
    assert paid["cost"] == 2000
    assert paid["coins"] == 3000
    assert paid["plate"]["rarity"] == "common"


async def test_paid_spin_needs_enough_money(client):
    await get_me(client, "1102")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1102))
        user.energy = 0
        await session.commit()

    response = await client.post("/api/spin?tier=mythic", headers=headers("1102"))
    assert response.status_code == 400


async def test_sell_plate_credits_exactly_price(client):
    plate = (await client.post("/api/spin", headers=headers("1200"))).json()["plate"]

    response = await client.post(f"/api/garage/{plate['id']}/sell", headers=headers("1200"))
    assert response.status_code == 200
    assert response.json()["coins"] == 1500 + plate["price"]

    again = await client.post(f"/api/garage/{plate['id']}/sell", headers=headers("1200"))
    assert again.status_code == 400


async def test_task_reward_claimed_once(client):
    await client.post("/api/spin", headers=headers("1400"))

    listing = (await client.get("/api/tasks", headers=headers("1400"))).json()["items"]
    task = next(item for item in listing if item["code"] == "first_plate")
    assert task["progress"] == 1
    assert task["done"] is True
    assert task["claimed"] is False

    claim = await client.post("/api/tasks/first_plate/claim", headers=headers("1400"))
    assert claim.status_code == 200
    body = claim.json()
    assert body["rewards"]["coins"] == 200
    assert body["coins"] == 1700

    again = await client.post("/api/tasks/first_plate/claim", headers=headers("1400"))
    assert again.status_code == 400


async def test_task_blocked_until_done(client):
    response = await client.post("/api/tasks/daily_spin_5/claim", headers=headers("1401"))
    assert response.status_code == 400


async def test_rating_shows_garage_value(client):
    plate = (await client.post("/api/spin", headers=headers("1402"))).json()["plate"]

    data = (await client.get("/api/rating", headers=headers("1402"))).json()
    assert data["me"]["rank"] == 1
    assert data["me"]["plates"] == 1
    assert data["me"]["total"] == plate["price"]
    assert data["items"][0]["total"] == plate["price"]


async def test_referral_credits_inviter(client):
    await get_me(client, "1500")

    joined = await client.get(
        "/api/me", headers={**headers("1501"), "X-Start-Param": "1500"}
    )
    assert joined.status_code == 200

    friends = (await client.get("/api/friends", headers=headers("1500"))).json()
    assert friends["invites"] == 1
    assert friends["ladder"][0]["done"] is True

    inviter = await get_me(client, "1500")
    assert inviter["user"]["coins"] == 1800


async def test_referral_ignored_for_existing_user(client):
    await get_me(client, "1510")
    await get_me(client, "1511")

    again = await client.get("/api/me", headers={**headers("1511"), "X-Start-Param": "1510"})
    assert again.status_code == 200

    friends = (await client.get("/api/friends", headers=headers("1510"))).json()
    assert friends["invites"] == 0


async def test_garage_batch_sell(client):
    first = (await client.post("/api/spin", headers=headers("1600"))).json()["plate"]
    second = (await client.post("/api/spin", headers=headers("1600"))).json()["plate"]

    response = await client.post(
        "/api/garage/sell", headers=headers("1600"), json={"ids": [first["id"], second["id"]]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sold"] == 2
    assert body["amount"] == first["price"] + second["price"]
    assert body["coins"] == 1500 + body["amount"]

    garage = (await client.get("/api/garage", headers=headers("1600"))).json()
    assert garage["plates"] == []


async def test_garage_income_grows_with_value(client):
    plate = (await client.post("/api/spin", headers=headers("1610"))).json()["plate"]

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1610))
        user.garage_income_at = user.created_at - timedelta(hours=2)
        await session.commit()

    garage = (await client.get("/api/garage", headers=headers("1610"))).json()
    rate = garage["income"]["rate"]
    assert rate == int(plate["price"] * 0.01)
    assert garage["income"]["available"] == rate * 2

    claim = await client.post("/api/garage/income", headers=headers("1610"))
    assert claim.status_code == 200
    assert claim.json()["amount"] == rate * 2

    again = await client.post("/api/garage/income", headers=headers("1610"))
    assert again.status_code == 400


async def test_garage_refuses_paid_plates(client):
    plate = (await client.post("/api/spin", headers=headers("1620"))).json()["plate"]
    async with SessionLocal() as session:
        row = await session.scalar(select(Plate).where(Plate.id == plate["id"]))
        row.is_paid = True
        await session.commit()

    response = await client.post(
        "/api/garage/sell", headers=headers("1620"), json={"ids": [plate["id"]]}
    )
    assert response.status_code == 400


async def test_craft_merges_same_rarity(client):
    await get_me(client, "1700")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1700))
        ids = []
        for index in range(3):
            plate = Plate(
                code=f"А12{index}ВС50",
                digits=f"12{index}",
                letters="АВС",
                region="50",
                score=0,
                price=1000,
                rarity="common",
                stars=1,
                owner_id=user.id,
            )
            session.add(plate)
            await session.flush()
            ids.append(plate.id)
        await session.commit()

    response = await client.post("/api/garage/craft", headers=headers("1700"), json={"ids": ids})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target"] == "rare"
    assert body["spent"] == 3
    assert 2600 <= body["value"] <= 3400

    garage = (await client.get("/api/garage", headers=headers("1700"))).json()
    assert len(garage["plates"]) == 1
    assert garage["plates"][0]["rarity"] == "rare"


async def test_craft_needs_same_rarity(client):
    await get_me(client, "1710")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1710))
        ids = []
        for index, rarity in enumerate(["common", "common", "rare"]):
            plate = Plate(
                code=f"В12{index}ВС50",
                digits=f"12{index}",
                letters="АВС",
                region="50",
                score=0,
                price=1000,
                rarity=rarity,
                stars=1,
                owner_id=user.id,
            )
            session.add(plate)
            await session.flush()
            ids.append(plate.id)
        await session.commit()

    response = await client.post("/api/garage/craft", headers=headers("1710"), json={"ids": ids})
    assert response.status_code == 400


async def test_ticket_spins_plate_of_rarity(client):
    await get_me(client, "1800")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1800))
        session.add(Ticket(user_id=user.id, rarity="epic", count=1))
        await session.commit()

    response = await client.post(
        "/api/tickets/use", headers=headers("1800"), json={"rarity": "epic"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plate"]["rarity"] == "epic"
    assert body["left"] == 0

    listing = (await client.get("/api/tickets", headers=headers("1800"))).json()
    counts = {item["rarity"]: item["count"] for item in listing["items"]}
    assert counts["epic"] == 0

    again = await client.post(
        "/api/tickets/use", headers=headers("1800"), json={"rarity": "epic"}
    )
    assert again.status_code == 400


async def test_hunt_claim_once(client):
    await get_me(client, "1900")
    state = (await client.get("/api/hunt", headers=headers("1900"))).json()
    assert state["done"] is False

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1900))
        hunt = await session.scalar(select(Hunt).order_by(Hunt.id.desc()))
        session.add(UserHunt(user_id=user.id, hunt_id=hunt.id, done_at=datetime.now(timezone.utc)))
        await session.commit()

    claim = await client.post("/api/hunt/claim", headers=headers("1900"))
    assert claim.status_code == 200, claim.text
    assert claim.json()["rewards"]["coins"] > 0

    again = await client.post("/api/hunt/claim", headers=headers("1900"))
    assert again.status_code == 400


async def test_pass_claim_requires_level(client):
    await get_me(client, "2000")
    response = await client.post(
        "/api/pass/claim", headers=headers("2000"), json={"level": 1, "track": "free"}
    )
    assert response.status_code == 400


async def test_pass_claim_once_per_level(client):
    await get_me(client, "2001")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2001))
        user.season_points = 1000
        await session.commit()

    first = await client.post(
        "/api/pass/claim", headers=headers("2001"), json={"level": 1, "track": "free"}
    )
    assert first.status_code == 200, first.text
    assert first.json()["rewards"]["coins"] > 0

    again = await client.post(
        "/api/pass/claim", headers=headers("2001"), json={"level": 1, "track": "free"}
    )
    assert again.status_code == 400


async def test_pass_premium_branch_locked_until_bought(client):
    await get_me(client, "2010")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2010))
        user.season_points = 1000
        await session.commit()

    locked = await client.post(
        "/api/pass/claim", headers=headers("2010"), json={"level": 1, "track": "premium"}
    )
    assert locked.status_code == 400

    bought = await client.post("/api/pass/buy", headers=headers("2010"))
    assert bought.status_code == 200
    assert bought.json()["premium"] is True

    unlocked = await client.post(
        "/api/pass/claim", headers=headers("2010"), json={"level": 1, "track": "premium"}
    )
    assert unlocked.status_code == 200


async def test_chat_posts_and_lists(client):
    sent = await client.post("/api/chat", headers=headers("2100"), json={"text": "Привет"})
    assert sent.status_code == 200

    items = (await client.get("/api/chat", headers=headers("2100"))).json()["items"]
    assert items[-1]["text"] == "Привет"


async def test_chat_rejects_links_and_flood(client):
    link = await client.post(
        "/api/chat", headers=headers("2110"), json={"text": "https://spam.example"}
    )
    assert link.status_code == 400

    first = await client.post("/api/chat", headers=headers("2111"), json={"text": "раз"})
    assert first.status_code == 200
    second = await client.post("/api/chat", headers=headers("2111"), json={"text": "два"})
    assert second.status_code == 400


async def test_nick_ticket_after_seven_days(client):
    nick_headers = {**headers("2200"), "X-Dev-Name": "Test NumbersLab_off"}
    await get_me(client, "2200")
    await client.get("/api/me", headers=nick_headers)

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2200))
        user.nick_since = date.today() - timedelta(days=8)
        await session.commit()

    first = await client.post("/api/nick/claim", headers=nick_headers, json={"days": 7})
    assert first.status_code == 200, first.text
    assert first.json()["ticket"] == "mythic"

    again = await client.post("/api/nick/claim", headers=nick_headers, json={"days": 7})
    assert again.status_code == 400

    early = await client.post("/api/nick/claim", headers=nick_headers, json={"days": 14})
    assert early.status_code == 400


async def test_shop_sells_energy_for_rubles(client):
    await get_me(client, "2300")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2300))
        user.coins = 6000
        user.energy = 0
        await session.commit()

    response = await client.post(
        "/api/shop/energy", headers=headers("2300"), json={"pack": "small"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["energy"] == 10
    assert response.json()["coins"] == 1000


async def test_shop_sells_ticket_for_rubles(client):
    await get_me(client, "2310")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2310))
        user.coins = 20000
        await session.commit()

    response = await client.post(
        "/api/shop/ticket", headers=headers("2310"), json={"rarity": "rare"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["coins"] == 5000

    listing = (await client.get("/api/tickets", headers=headers("2310"))).json()
    counts = {item["rarity"]: item["count"] for item in listing["items"]}
    assert counts["rare"] == 1


async def test_shop_rejects_expensive_purchase(client):
    await get_me(client, "2320")
    response = await client.post(
        "/api/shop/energy", headers=headers("2320"), json={"pack": "big"}
    )
    assert response.status_code == 400


async def test_friends_lists_invited_and_contest(client):
    await get_me(client, "2400")
    await client.get("/api/me", headers={**headers("2401"), "X-Start-Param": "2400"})

    data = (await client.get("/api/friends", headers=headers("2400"))).json()
    assert data["invites"] == 1
    assert len(data["friends"]) == 1
    assert data["friends"][0]["level"] >= 1
    assert data["contest"]["me"]["place"] >= 1
    assert data["contest"]["items"][0]["invites"] >= 1


async def test_daily_once_per_day(client):
    first = await client.post("/api/daily", headers=headers("1300"))
    assert first.status_code == 200
    assert first.json()["amount"] == 150

    second = await client.post("/api/daily", headers=headers("1300"))
    assert second.status_code == 400


async def test_duel_keeps_total_balance(client):
    a, b = "1400", "1401"
    await get_me(client, a)
    await get_me(client, b)

    created = await client.post("/api/duels", json={"bet": 100}, headers=headers(a))
    assert created.status_code == 200
    duel_id = created.json()["duel"]["id"]

    joined = await client.post(f"/api/duels/{duel_id}/join", headers=headers(b))
    assert joined.status_code == 200
    assert len(joined.json()["plates"]) == 2

    a_coins = (await get_me(client, a))["user"]["coins"]
    b_coins = (await get_me(client, b))["user"]["coins"]
    assert a_coins + b_coins == 3000


async def test_cannot_join_own_duel(client):
    created = await client.post("/api/duels", json={"bet": 100}, headers=headers("1500"))
    duel_id = created.json()["duel"]["id"]
    joined = await client.post(f"/api/duels/{duel_id}/join", headers=headers("1500"))
    assert joined.status_code == 400


async def test_duel_bet_cannot_exceed_balance(client):
    response = await client.post("/api/duels", json={"bet": 99999}, headers=headers("1550"))
    assert response.status_code == 400


async def test_shop_dev_grant_and_no_resale(client):
    offers = (await client.get("/api/shop", headers=headers("1600"))).json()["offers"]
    assert len(offers) == 9

    offer = offers[0]
    bought = await client.post(
        "/api/shop/buy", json={"code": offer["code"]}, headers=headers("1600")
    )
    assert bought.status_code == 200
    assert bought.json()["dev"] is True

    garage = (await client.get("/api/garage", headers=headers("1600"))).json()["plates"]
    plate = next(item for item in garage if item["code"] == offer["code"])
    assert plate["is_paid"] is True

    resale = await client.post(f"/api/garage/{plate['id']}/sell", headers=headers("1600"))
    assert resale.status_code == 400


async def test_purchase_is_idempotent(client):
    await get_me(client, "1700")

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1700))
        code = offers_for(user.id, date.today())[0].code

        from app.shop import prepare_purchase

        purchase = await prepare_purchase(session, user, code)
        await session.commit()
        payload = purchase.payload

        first = await fulfil(session, payload)
        second = await fulfil(session, payload)
        await session.commit()

        total = await session.scalar(select(func.count(Plate.id)).where(Plate.code == code))

    assert first is not None
    assert second is None
    assert total == 1


async def fulfil(session, payload):
    from app.shop import fulfil_purchase

    return await fulfil_purchase(session, payload)


async def test_collections_seeded(client):
    data = (await client.get("/api/collections", headers=headers("1900"))).json()
    assert len(data["items"]) == 12
    assert all(item["progress"] == 0 for item in data["items"])


async def test_collection_claim_grants_once(client):
    await get_me(client, "1910")

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1910))
        for digits in ("777", "111", "999"):
            session.add(
                Plate(
                    code=f"А{digits}ВС77",
                    digits=digits,
                    letters="АВС",
                    region="77",
                    score=9,
                    price=1000,
                    rarity="legendary",
                    stars=25,
                    owner_id=user.id,
                )
            )
        await session.commit()
        collection = await session.scalar(
            select(Collection).where(Collection.code == "triple_three")
        )
        collection_id = collection.id

    items = (await client.get("/api/collections", headers=headers("1910"))).json()["items"]
    target = next(item for item in items if item["id"] == collection_id)
    assert target["done"] is True
    assert target["claimed"] is False

    first = await client.post(
        f"/api/collections/{collection_id}/claim", headers=headers("1910")
    )
    assert first.status_code == 200
    assert first.json()["coins"] == 1500 + 900

    second = await client.post(
        f"/api/collections/{collection_id}/claim", headers=headers("1910")
    )
    assert second.status_code == 400


async def test_collection_not_ready(client):
    items = (await client.get("/api/collections", headers=headers("1920"))).json()["items"]
    locked = next(item for item in items if not item["done"])
    response = await client.post(
        f"/api/collections/{locked['id']}/claim", headers=headers("1920")
    )
    assert response.status_code == 400


async def test_spin_awards_xp(client):
    await get_me(client, "1930")
    response = await client.post("/api/spin", headers=headers("1930"))
    assert response.status_code == 200
    profile = (await get_me(client, "1930"))["user"]
    assert profile["xp"] == 5
    assert profile["level"] == 1
