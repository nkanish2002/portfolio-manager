"""Basket CRUD route tests — user-scoping, color/target validation.

Segment 7.1: also covers the 3-basket preset seed (on register) and the
target-allocation summary / warning endpoint.
"""

from __future__ import annotations

from sqlalchemy import select

from portfolio_manager.models import Basket
from portfolio_manager.models.user import User


class TestBasketCrud:
    async def test_create_and_list(self, auth_client):
        r = await auth_client.post(
            "/api/v1/baskets/",
            json={"name": "Super Stable", "color": "#58a6ff", "target_allocation": 40.0},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Super Stable"
        assert body["color"] == "#58a6ff"
        assert float(body["target_allocation"]) == 40.0
        assert body["is_preset"] is False

        listing = await auth_client.get("/api/v1/baskets/")
        assert listing.status_code == 200
        assert len(listing.json()) >= 1

    async def test_list_only_own_baskets(self, auth_client, client, make_user):
        # second user
        other = await make_user()
        h = {"Authorization": f"Bearer {other['token']}"}
        await auth_client.post("/api/v1/baskets/", json={"name": "Mine", "color": "#abc"})
        await client.post(
            "/api/v1/baskets/", json={"name": "Theirs"}, headers=h
        )
        mine = (await auth_client.get("/api/v1/baskets/")).json()
        names = {b["name"] for b in mine}
        assert "Mine" in names
        assert "Theirs" not in names

    async def test_update_color_and_target(self, auth_client):
        created = (await auth_client.post(
            "/api/v1/baskets/", json={"name": "HB", "color": "#000000", "target_allocation": 30.0}
        )).json()
        r = await auth_client.put(
            f"/api/v1/baskets/{created['id']}",
            json={"color": "#ff7b00", "target_allocation": 50.0},
        )
        assert r.status_code == 200
        assert r.json()["color"] == "#ff7b00"
        assert float(r.json()["target_allocation"]) == 50.0

    async def test_delete_basket(self, auth_client):
        created = (await auth_client.post(
            "/api/v1/baskets/", json={"name": "Temp", "color": "#abc"}
        )).json()
        d = await auth_client.delete(f"/api/v1/baskets/{created['id']}")
        assert d.status_code == 204
        assert (await auth_client.get(f"/api/v1/baskets/{created['id']}")).status_code == 404

    async def test_target_allocation_out_of_range_rejected(self, auth_client):
        r = await auth_client.post(
            "/api/v1/baskets/", json={"name": "Bad", "color": "#abc", "target_allocation": 150.0}
        )
        assert r.status_code == 422

    async def test_requires_auth(self, client):
        assert (await client.get("/api/v1/baskets/")).status_code == 401

    async def test_other_users_basket_404(self, auth_client, client, make_user):
        created = (await auth_client.post(
            "/api/v1/baskets/", json={"name": "Secret", "color": "#abc"}
        )).json()
        other = await make_user()
        r = await client.get(
            f"/api/v1/baskets/{created['id']}",
            headers={"Authorization": f"Bearer {other['token']}"},
        )
        assert r.status_code == 404


class TestBasketSeed:
    """Segment 7.1: 3-basket preset seeded on register + target summary endpoint."""

    async def test_seed_creates_three_preset_baskets(self, auth_client):
        # auth_client registration triggers on_after_register → seed_default_baskets
        r = await auth_client.get("/api/v1/baskets/")
        assert r.status_code == 200
        baskets = r.json()
        assert len(baskets) == 3
        names = {b["name"] for b in baskets}
        assert names == {"Super Stable", "Stable Alpha", "High Beta"}
        for b in baskets:
            assert b["is_preset"] is True
        total = sum(float(b["target_allocation"]) for b in baskets)
        assert abs(total - 100.0) < 0.01

    async def test_seed_colors_and_targets(self, auth_client):
        baskets = {b["name"]: b for b in (await auth_client.get("/api/v1/baskets/")).json()}
        assert baskets["Super Stable"]["color"] == "#58a6ff"
        assert float(baskets["Super Stable"]["target_allocation"]) == 40.0
        assert baskets["Stable Alpha"]["color"] == "#bc8cff"
        assert float(baskets["Stable Alpha"]["target_allocation"]) == 40.0
        assert baskets["High Beta"]["color"] == "#f0883e"
        assert float(baskets["High Beta"]["target_allocation"]) == 20.0

    async def test_target_summary_complete_after_seed(self, auth_client):
        r = await auth_client.get("/api/v1/baskets/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["targets_complete"] is True
        assert body["basket_count"] == 3
        assert abs(body["total_target_allocation"] - 100.0) < 0.01
        assert body["warning"] is None

    async def test_target_summary_warns_when_under_allocated(self, auth_client):
        baskets = (await auth_client.get("/api/v1/baskets/")).json()
        # lower one target so the total drops below 100%
        bid = baskets[0]["id"]
        await auth_client.put(f"/api/v1/baskets/{bid}", json={"target_allocation": 20.0})
        body = (await auth_client.get("/api/v1/baskets/summary")).json()
        assert body["targets_complete"] is False
        assert body["warning"] is not None
        assert "unallocated" in body["warning"].lower()

    async def test_target_summary_warns_when_over_allocated(self, auth_client):
        baskets = (await auth_client.get("/api/v1/baskets/")).json()
        bid = baskets[0]["id"]
        await auth_client.put(f"/api/v1/baskets/{bid}", json={"target_allocation": 60.0})
        body = (await auth_client.get("/api/v1/baskets/summary")).json()
        assert body["targets_complete"] is False
        assert body["warning"] is not None
        assert "over-allocated" in body["warning"].lower()

    async def test_seed_is_idempotent(self, auth_client, db_session):
        from portfolio_manager.services.basket_seed import seed_default_baskets

        users = (await db_session.execute(select(User))).scalars().all()
        assert len(users) == 1
        uid = users[0].id

        before = (await db_session.execute(select(Basket).where(Basket.user_id == uid))).scalars().all()
        assert len(before) == 3

        # seeding again must be a no-op (user already has baskets)
        await seed_default_baskets(db_session, uid)
        after = (await db_session.execute(select(Basket).where(Basket.user_id == uid))).scalars().all()
        assert len(after) == 3

    async def test_delete_preset_basket_unassigns_positions(self, auth_client, make_account, make_portfolio, make_asset):
        baskets = {b["name"]: b for b in (await auth_client.get("/api/v1/baskets/")).json()}
        portfolio = await make_portfolio(basket_id=baskets["High Beta"]["id"])
        asset = await make_asset()
        # add a position in the High Beta portfolio
        r = await auth_client.post(
            f"/api/v1/portfolios/{portfolio['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": 10, "avg_cost_basis": 100, "current_price": 110},
        )
        assert r.status_code == 201
        # delete the basket → portfolio.basket_id becomes NULL (SET NULL FK)
        d = await auth_client.delete(f"/api/v1/baskets/{baskets['High Beta']['id']}")
        assert d.status_code == 204
        refreshed = (await auth_client.get(f"/api/v1/portfolios/{portfolio['id']}")).json()
        assert refreshed["basket_id"] is None
