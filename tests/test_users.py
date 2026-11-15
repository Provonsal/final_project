from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_me_success(client, as_user, service, member):
    as_user(member)
    user_service = service("user")
    user_service.me.return_value = SimpleNamespace(
        id=str(member.id), username=member.email, role=member.role.value,
    )
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == member.email
    user_service.me.assert_awaited_once_with(member)


async def test_me_unauthorized(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_guest_forbidden(client, as_user, service, guest):
    as_user(guest)
    service("user")
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 403