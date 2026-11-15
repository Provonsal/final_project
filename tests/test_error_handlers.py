import uuid

import pytest
from fastapi import HTTPException

from app.exc.exceptions import BusinessRuleError, NotFoundError, WrongInputError


pytestmark = pytest.mark.asyncio


async def test_not_found_format(client, as_user, service, obj, member):
    as_user(member)
    service("team")
    obj("team", error=NotFoundError(resource="Team", resource_id="abc"))
    resp = await client.get(f"/api/v1/teams/{uuid.uuid4()}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["details"]["resource"] == "Team"
    assert body["error"]["details"]["resource_id"] == "abc"


async def test_business_rule_format(client, as_user, service, manager):
    as_user(manager)
    service("team").create_team.side_effect = BusinessRuleError(message="oops")
    resp = await client.post("/api/v1/teams/", json={"name": "X", "max_per_team": 1})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert body["error"]["message"] == "oops"


async def test_wrong_input_format(client, service):
    service("user").register.side_effect = WrongInputError(message="bad")
    resp = await client.post(
        "/api/v1/auth/register",
        data={"username": "x@y.z", "name": "X", "password": "p"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


async def test_http_exception_format(client, service):
    async def _raise(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Nope")

    service("auth").login.side_effect = _raise

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "x", "password": "y"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "Nope"


async def test_unauthorized_format(client):
    """OAuth2PasswordBearer бросает HTTPException без токена."""
    resp = await client.get("/api/v1/teams/")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "HTTP_ERROR"


async def test_unhandled_exception_format(client, as_user, service, manager):
    as_user(manager)
    service("team").create_team.side_effect = RuntimeError("boom")
    resp = await client.post("/api/v1/teams/", json={"name": "X", "max_per_team": 1})
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Внутренняя ошибка сервера"