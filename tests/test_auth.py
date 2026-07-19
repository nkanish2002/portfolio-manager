"""Auth tests — registration, login, JWT retrieval, protected routes."""

from __future__ import annotations


class TestRegistration:
    async def test_register_success(self, client):
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "new@example.com", "password": "supersecret123"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == "new@example.com"
        assert body["is_active"] is True
        assert body["is_superuser"] is False
        assert "password" not in body
        assert "hashed_password" not in body
        assert "id" in body

    async def test_register_with_display_name(self, client):
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "named@example.com", "password": "supersecret123", "display_name": "Alice"},
        )
        assert r.status_code == 201
        assert r.json()["display_name"] == "Alice"

    async def test_register_duplicate_email_rejected(self, client):
        # first registration ok
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "dup@example.com", "password": "supersecret123"},
        )
        # a second registration with the same email must fail
        r2 = await client.post(
            "/auth/jwt/register",
            json={"email": "dup@example.com", "password": "anothersecret456"},
        )
        assert r.status_code == 201
        assert r2.status_code == 400

    async def test_register_short_password_rejected(self, client):
        # UserManager.validate_password enforces a minimum length of 8 chars.
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "short@example.com", "password": "123"},
        )
        assert r.status_code == 400

    async def test_register_password_equals_email_rejected(self, client):
        # validate_password forbids passwords equal to the email.
        email = "same@example.com"
        r = await client.post(
            "/auth/jwt/register",
            json={"email": email, "password": email},
        )
        assert r.status_code == 400

    async def test_register_valid_long_password_accepted(self, client):
        # A password meeting the policy (>= 8 chars, not the email) succeeds.
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "goodpass@example.com", "password": "securepass123"},
        )
        assert r.status_code == 201

    async def test_register_invalid_email_rejected(self, client):
        r = await client.post(
            "/auth/jwt/register",
            json={"email": "not-an-email", "password": "supersecret123"},
        )
        assert r.status_code == 422


class TestLogin:
    async def test_login_success(self, client, make_user):
        user = await make_user()
        r = await client.post(
            "/auth/jwt/login",
            data={"username": user["email"], "password": user["password"]},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    async def test_login_wrong_password(self, client, make_user):
        user = await make_user()
        r = await client.post(
            "/auth/jwt/login",
            data={"username": user["email"], "password": "totally-wrong"},
        )
        assert r.status_code == 400

    async def test_login_unknown_user(self, client):
        r = await client.post(
            "/auth/jwt/login",
            data={"username": "ghost@example.com", "password": "whatever"},
        )
        assert r.status_code == 400


class TestProtectedRoutes:
    async def test_users_me_requires_auth(self, client):
        r = await client.get("/users/me")
        assert r.status_code == 401

    async def test_users_me_with_token(self, auth_client):
        r = await auth_client.get("/users/me")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "id" in body
        assert body["display_name"] == "Tester"
        assert body["is_active"] is True

    async def test_invalid_token_rejected(self, client):
        client.headers.update({"Authorization": "Bearer not-a-real-token"})
        r = await client.get("/users/me")
        assert r.status_code == 401

    async def test_health_public(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "healthy"}

    async def test_health_db_public(self, client):
        r = await client.get("/health/db")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
