from types import SimpleNamespace

import pytest

from app.exc.exceptions import BusinessRuleError, NotFoundError


pytestmark = pytest.mark.asyncio


# ---------- create ----------

async def test_create_team_success(client, as_user, service, manager):
    as_user(manager)
    team_service = service("team")
    team_service.create_team.return_value = SimpleNamespace(
        id="team-1", name="Alpha", max_per_team=5, owner=manager.id
    )
    team_service.get_invite_code.return_value = SimpleNamespace(body="INVITE")
    team_service.join_team.return_value = None

    resp = await client.post("/api/v1/teams/", json={"name": "Alpha", "max_per_team": 5})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alpha"
    team_service.create_team.assert_awaited_once()
    team_service.get_invite_code.assert_awaited_once()
    team_service.join_team.assert_awaited_once()


async def test_create_team_business_error(client, as_user, service, manager):
    as_user(manager)
    service("team").create_team.side_effect = BusinessRuleError(
        message="Team name already taken."
    )
    resp = await client.post("/api/v1/teams/", json={"name": "Alpha", "max_per_team": 5})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


async def test_create_team_forbidden_for_member(client, as_user, service, member):
    as_user(member)
    service("team")
    resp = await client.post("/api/v1/teams/", json={"name": "X", "max_per_team": 3})
    assert resp.status_code == 403


async def test_create_team_forbidden_for_guest(client, as_user, service, guest):
    as_user(guest)
    service("team")
    resp = await client.post("/api/v1/teams/", json={"name": "X", "max_per_team": 3})
    assert resp.status_code == 403


async def test_create_team_unauthorized(client, service):
    service("team")
    resp = await client.post("/api/v1/teams/", json={"name": "X", "max_per_team": 3})
    assert resp.status_code == 401


async def test_create_team_validation_error(client, as_user, service, manager):
    as_user(manager)
    service("team")
    resp = await client.post("/api/v1/teams/", json={"max_per_team": 5})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------- read ----------

async def test_read_teams_success(client, as_user, service, member):
    as_user(member)
    service("team").get_teams.return_value = [
        SimpleNamespace(id="t1", name="A", max_per_team=5, owner=member.id)
    ]
    resp = await client.get("/api/v1/teams/")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "A"


async def test_read_teams_forbidden_for_guest(client, as_user, service, guest):
    as_user(guest)
    service("team")
    resp = await client.get("/api/v1/teams/")
    assert resp.status_code == 403


async def test_read_team_success(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("team").get_team.return_value = team_obj   
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(team_obj.id)


async def test_read_team_not_found(client, as_user, service, obj, member):
    as_user(member)
    service("team")
    obj("team", error=NotFoundError(resource="Team", resource_id="x"))
    import uuid
    resp = await client.get(f"/api/v1/teams/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


# ---------- update / delete ----------

async def test_update_team_success(client, as_user, service, obj, manager, team_obj):
    as_user(manager)
    service("team").update.return_value = SimpleNamespace(
        id=team_obj.id, name="Renamed", max_per_team=5, owner=manager.id
    )
    obj("team", team_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}", json={"name": "Renamed"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


async def test_update_team_forbidden_for_member(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("team")
    obj("team", team_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}", json={"name": "Hijack"}
    )
    assert resp.status_code == 403


async def test_delete_team_success(client, as_user, service, obj, manager, team_obj):
    as_user(manager)
    service("team").delete.return_value = {"status": "ok"}
    obj("team", team_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}")
    assert resp.status_code == 200


async def test_delete_team_forbidden_for_member(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("team")
    obj("team", team_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}")
    assert resp.status_code == 403


# ---------- members / join / code ----------

async def test_members_success(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("team").get_team_users.return_value = [
        SimpleNamespace(id=str(team_obj.owner), email="o@e.com")
    ]
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/members")
    assert resp.status_code == 200


async def test_join_success(client, as_user, service, auth_user):
    as_user(auth_user)
    service("team").join_team.return_value = None
    resp = await client.post("/api/v1/teams/join", params={"invite_code": "INVITE"})
    assert resp.status_code == 200


async def test_join_invalid_code(client, as_user, service, auth_user):
    as_user(auth_user)
    service("team").join_team.side_effect = BusinessRuleError(message="Invite code not active")
    resp = await client.post("/api/v1/teams/join", params={"invite_code": "BAD"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


async def test_get_invite_code_success(client, as_user, service, obj, manager, team_obj):
    as_user(manager)
    service("team").get_invite_code.return_value = SimpleNamespace(body="CODE")
    obj("team", team_obj)
    resp = await client.post("/api/v1/teams/code", params={"team_id": str(team_obj.id)})
    assert resp.status_code == 200
    assert resp.json()["body"] == "CODE"


async def test_get_invite_code_forbidden_for_member(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("team")
    obj("team", team_obj)
    resp = await client.post("/api/v1/teams/code", params={"team_id": str(team_obj.id)})
    assert resp.status_code == 403