"""Basket CRUD route tests — user-scoping, color/target validation."""

from __future__ import annotations


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
