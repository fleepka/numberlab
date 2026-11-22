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
    await get_me(client, "1100")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1100))
        user.energy = ENERGY_MAX
        await session.commit()

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


async def test_rare_spin_costs_energy_and_returns_rare(client):
    await get_me(client, "1103")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1103))
        user.energy = ENERGY_MAX
        await session.commit()

    response = await client.post("/api/spin?tier=rare", headers=headers("1103"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cost"] == 0
    assert body["energy"] == ENERGY_MAX - 8
    assert body["plate"]["rarity"] == "rare"


async def test_spin_returns_selected_country(client):
    response = await client.post("/api/spin?tier=rare&country=KZ", headers=headers("1120"))
    assert response.status_code == 200, response.text
    assert response.json()["plate"]["country"] == "KZ"


async def test_energy_cap_allows_mythic_spin(client):
    await get_me(client, "1130")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 1130))
        user.energy = 300
        await session.commit()

    response = await client.post("/api/spin?tier=mythic", headers=headers("1130"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cost"] == 0
    assert body["energy"] == 300 - 256
    assert body["plate"]["rarity"] == "mythic"


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


async def test_spin_currency_energy_requires_energy(client):
    await get_me(client, "2300")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2300))
        user.energy = 0
        user.coins = 100_000
        await session.commit()

    response = await client.post(
        "/api/spin?tier=common&currency=energy", headers=headers("2300")
    )
    assert response.status_code == 400


async def test_spin_currency_rubles_keeps_energy(client):
    await get_me(client, "2320")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2320))
        user.coins = 5000
        user.energy = ENERGY_MAX
        await session.commit()

    response = await client.post(
        "/api/spin?tier=common&currency=rubles", headers=headers("2320")
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cost"] == 2000
    assert body["energy"] == ENERGY_MAX


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


async def test_friends_lists_invited_and_contest(client):
    await get_me(client, "2400")
    await client.get("/api/me", headers={**headers("2401"), "X-Start-Param": "2400"})

    data = (await client.get("/api/friends", headers=headers("2400"))).json()
    assert data["invites"] == 1
    assert len(data["friends"]) == 1
    assert data["friends"][0]["level"] >= 1
    assert data["contest"]["me"]["place"] >= 1
    assert data["contest"]["items"][0]["invites"] >= 1


async def test_buy_garage_slots(client):
    await get_me(client, "2500")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2500))
        user.gems = 250
        await session.commit()

    response = await client.post("/api/garage/slots", headers=headers("2500"))
    assert response.status_code == 200, response.text
    assert response.json()["slots"] == 27
    assert response.json()["gems"] == 50

    second = await client.post("/api/garage/slots", headers=headers("2500"))
    assert second.status_code == 400


async def test_full_garage_blocks_spin(client):
    await get_me(client, "2510")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2510))
        user.garage_slots = 1
        await session.commit()

    first = await client.post("/api/spin?tier=common", headers=headers("2510"))
    assert first.status_code == 200

    second = await client.post("/api/spin?tier=common", headers=headers("2510"))
    assert second.status_code == 400


async def test_vip_product_gives_slots_and_income_bonus(client):
    await get_me(client, "2600")
    await client.post("/api/spin?tier=common", headers=headers("2600"))

    before = (await client.get("/api/garage", headers=headers("2600"))).json()["income"]["rate"]

    bought = await client.post("/api/products/buy", headers=headers("2600"), json={"code": "vip"})
    assert bought.status_code == 200, bought.text
    assert bought.json()["dev"] is True

    me = await get_me(client, "2600")
    assert me["user"]["vip_until"] is not None
    assert me["user"]["garage_slots"] == 24

    after = (await client.get("/api/garage", headers=headers("2600"))).json()["income"]["rate"]
    assert after == int(before * 1.5)


async def test_cosmetic_product_sets_frame(client):
    await get_me(client, "2610")

    catalog = (await client.get("/api/products", headers=headers("2610"))).json()["items"]
    assert any(item["code"] == "style:neon" for item in catalog)

    bought = await client.post(
        "/api/products/buy", headers=headers("2610"), json={"code": "style:neon"}
    )
    assert bought.status_code == 200, bought.text

    me = await get_me(client, "2610")
    assert me["user"]["frame"] == "neon"


async def test_auction_bid_and_refund(client):
    await get_me(client, "2800")
    await get_me(client, "2801")
    async with SessionLocal() as session:
        for tg_id in (2800, 2801):
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            user.coins = 200_000
        await session.commit()

    lot = (await client.get("/api/auction", headers=headers("2800"))).json()
    first = await client.post(
        "/api/auction/bid", headers=headers("2800"), json={"amount": lot["min_bid"]}
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/api/auction/bid",
        headers=headers("2801"),
        json={"amount": lot["min_bid"] + lot["step"]},
    )
    assert second.status_code == 200, second.text

    first_user = await get_me(client, "2800")
    assert first_user["user"]["coins"] == 200_000

    view = (await client.get("/api/auction", headers=headers("2801"))).json()
    assert view["mine"] is True
    assert view["top_bid"] == lot["min_bid"] + lot["step"]


async def test_buy_frame(client):
    await get_me(client, "2700")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.tg_id == 2700))
        user.gems = 150
        await session.commit()

    bought = await client.post("/api/style/buy", headers=headers("2700"), json={"frame": "neon"})
    assert bought.status_code == 200, bought.text
    assert bought.json()["gems"] == 51

    me = await get_me(client, "2700")
    assert me["user"]["frame"] == "neon"

    again = await client.post("/api/style/buy", headers=headers("2700"), json={"frame": "neon"})
    assert again.status_code == 400


async def test_admin_requires_flag(client):
    await get_me(client, "3000")
    response = await client.get("/api/admin/users", headers=headers("3000"))
    assert response.status_code == 403


async def test_admin_grant_plate_ban_and_cleanup(client):
    await get_me(client, "3010")
    async with SessionLocal() as session:
        admin = await session.scalar(select(User).where(User.tg_id == 3010))
        admin.is_admin = True
        await session.commit()

    target = (await get_me(client, "3011"))["user"]

    granted = await client.post(
        "/api/admin/grant",
        headers=headers("3010"),
        json={"user_id": target["id"], "currency": "coins", "amount": 5000},
    )
    assert granted.status_code == 200, granted.text
    assert (await get_me(client, "3011"))["user"]["coins"] == 6500

    plate = await client.post(
        "/api/admin/plate",
        headers=headers("3010"),
        json={"user_id": target["id"], "rarity": "mythic", "country": "KZ"},
    )
    assert plate.status_code == 200, plate.text
    assert plate.json()["plate"]["rarity"] == "mythic"
    assert plate.json()["plate"]["country"] == "KZ"

    banned = await client.post(
        "/api/admin/ban", headers=headers("3010"), json={"user_id": target["id"], "banned": True}
    )
    assert banned.status_code == 200
    assert (await client.get("/api/me", headers=headers("3011"))).status_code == 403

    async with SessionLocal() as session:
        session.add(
            Plate(
                code="Я999ЯЯ50",
                digits="999",
                letters="ЯВС",
                region="50",
                score=9,
                price=1000,
                rarity="unique",
                stars=1,
            )
        )
        await session.commit()

    cleaned = await client.post("/api/admin/cleanup", headers=headers("3010"))
    assert cleaned.status_code == 200
    assert cleaned.json()["removed"] >= 1


async def test_cosmetics_catalog_has_frames_and_buys(client):
    await get_me(client, "2620")

    items = (await client.get("/api/products", headers=headers("2620"))).json()["items"]
    styles = [item for item in items if item["kind"] == "style"]
    assert len(styles) >= 5
    assert all(item["stars"] > 0 for item in styles)

    bought = await client.post(
        "/api/products/buy", headers=headers("2620"), json={"code": "style:rose"}
    )
    assert bought.status_code == 200, bought.text

    me = await get_me(client, "2620")
    assert me["user"]["frame"] == "rose"


async def test_promo_redeem_once(client):
    await get_me(client, "3100")

    redeemed = await client.post(
        "/api/promo", headers=headers("3100"), json={"code": "numberlab"}
    )
    assert redeemed.status_code == 200, redeemed.text
    assert redeemed.json()["given"]["value"] == 5000
    assert (await get_me(client, "3100"))["user"]["coins"] == 6500

    again = await client.post("/api/promo", headers=headers("3100"), json={"code": "NUMBERLAB"})
    assert again.status_code == 400

    unknown = await client.post("/api/promo", headers=headers("3100"), json={"code": "NOPE"})
    assert unknown.status_code == 400


async def test_themes_catalog_and_choice(client):
    await get_me(client, "3110")

    items = (await client.get("/api/settings/themes", headers=headers("3110"))).json()["items"]
    assert len(items) == 10

    saved = await client.post(
        "/api/settings/theme", headers=headers("3110"), json={"theme": "dracula"}
    )
    assert saved.status_code == 200
    assert (await get_me(client, "3110"))["user"]["theme"] == "dracula"

    bad = await client.post(
        "/api/settings/theme", headers=headers("3110"), json={"theme": "neon"}
    )
    assert bad.status_code == 400


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
    assert len(data["items"]) >= 17
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
