"""Portfolio + Account CRUD route tests — ownership + basket assignment."""

from __future__ import annotations


class TestAccountCrud:
    async def test_create_and_list(self, auth_client):
        r = await auth_client.post(
            "/api/v1/accounts/",
            json={"name": "Wacky", "institution": "Schwab", "account_number": "1234"},
        )
        assert r.status_code == 201
        listing = await auth_client.get("/api/v1/accounts/")
        assert listing.status_code == 200
        assert any(a["name"] == "Wacky" for a in listing.json())

    async def test_list_only_own_accounts(self, auth_client, client, make_user):
        other = await make_user()
        await auth_client.post("/api/v1/accounts/", json={"name": "Mine"})
        await client.post(
            "/api/v1/accounts/", json={"name": "Theirs"},
            headers={"Authorization": f"Bearer {other['token']}"},
        )
        names = {a["name"] for a in (await auth_client.get("/api/v1/accounts/")).json()}
        assert "Mine" in names and "Theirs" not in names

    async def test_update_and_delete(self, auth_client):
        acc = (await auth_client.post("/api/v1/accounts/", json={"name": "Old"})).json()
        r = await auth_client.put(f"/api/v1/accounts/{acc['id']}", json={"name": "New"})
        assert r.status_code == 200
        assert r.json()["name"] == "New"
        assert (await auth_client.delete(f"/api/v1/accounts/{acc['id']}")).status_code == 204


class TestPortfolioCrud:
    async def test_create_with_account_and_basket(self, auth_client, make_account, make_basket):
        account = await make_account()
        basket = await make_basket()
        r = await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "Main", "account_id": account["id"], "basket_id": basket["id"]},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Main"
        assert body["basket_id"] == basket["id"]

    async def test_create_without_basket(self, auth_client, make_account):
        account = await make_account()
        r = await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "NoBasket", "account_id": account["id"]},
        )
        assert r.status_code == 201
        assert r.json()["basket_id"] is None

    async def test_invalid_account_rejected(self, auth_client):
        # random (non-owned) account id → 400
        from uuid import uuid4

        r = await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "Bad", "account_id": str(uuid4())},
        )
        assert r.status_code == 400

    async def test_list_and_detail(self, auth_client, make_account):
        account = await make_account()
        created = (await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "P1", "account_id": account["id"]},
        )).json()
        listing = await auth_client.get("/api/v1/portfolios/")
        assert any(p["id"] == created["id"] for p in listing.json())
        detail = await auth_client.get(f"/api/v1/portfolios/{created['id']}")
        assert detail.status_code == 200
        assert detail.json()["id"] == created["id"]
        assert detail.json()["positions"] == []

    async def test_update_basket(self, auth_client, make_account, make_basket):
        account = await make_account()
        basket = await make_basket(name="Target")
        pf = (await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "P", "account_id": account["id"]},
        )).json()
        r = await auth_client.put(
            f"/api/v1/portfolios/{pf['id']}", json={"basket_id": basket["id"]}
        )
        assert r.status_code == 200
        assert r.json()["basket_id"] == basket["id"]

    async def test_delete_portfolio(self, auth_client, make_account):
        account = await make_account()
        pf = (await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "Gone", "account_id": account["id"]},
        )).json()
        assert (await auth_client.delete(f"/api/v1/portfolios/{pf['id']}")).status_code == 204
        assert (await auth_client.get(f"/api/v1/portfolios/{pf['id']}")).status_code == 404

    async def test_other_user_portfolio_404(self, auth_client, make_account, make_user):
        account = await make_account()
        pf = (await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "Private", "account_id": account["id"]},
        )).json()
        other = await make_user()
        r = await auth_client.get(
            f"/api/v1/portfolios/{pf['id']}",
            headers={"Authorization": f"Bearer {other['token']}"},
        )
        # note: auth_client headers already set; use a fresh client for other user
        assert r.status_code in (401, 403, 404)
