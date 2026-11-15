from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.exc.exceptions import WrongInputError


pytestmark = pytest.mark.asyncio


async def test_register_success(client, service):
    user_service = service("user")
    user_service.register.return_value = SimpleNamespace(
        login="alice@example.com", message="Регистрация успешна", role="guest",
    )
    resp = await client.post(
        "/api/v1/auth/register",
        data={"username": "alice@example.com", "name": "Alice", "password": "pwd"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["login"] == "alice@example.com"
    assert body["role"] == "guest"
    user_service.register.assert_awaited_once()


async def test_register_duplicate_login(client, service):
    service("user").register.side_effect = WrongInputError(
        message="User with this login already exists"
    )
    resp = await client.post(
        "/api/v1/auth/register",
        data={"username": "alice@example.com", "name": "Alice", "password": "pwd"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "BAD_REQUEST"
    assert "already exists" in body["error"]["message"]


async def test_register_validation_error(client, service):
    service("user")
    resp = await client.post(
        "/api/v1/auth/register",
        data={"username": "alice@example.com"},  # нет name, password
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_login_success(client, service):
    service("auth").login.return_value = {
        "access_token": "abc.def.ghi",
        "refresh_token": "refresh",
        "token_type": "bearer",
    }
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "pwd"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "abc.def.ghi"


async def test_login_invalid_credentials(client, service):
    service("auth").login.side_effect = HTTPException(
        status_code=401, detail="Invalid credentials"
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "Invalid credentials"