from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_create_meeting_success(client, as_user, service, obj, manager, team_obj):
    as_user(manager)
    service("meeting").create_meeting.return_value = SimpleNamespace(
        id="m1", starts_at="2026-01-01T10:00:00Z",
        ends_at="2026-01-01T11:00:00Z", max_members=5,
    )
    obj("team", team_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/meetings",
        json={"starts_at": "2026-01-01T10:00:00Z",
              "ends_at": "2026-01-01T11:00:00Z", "max_members": 5},
    )
    assert resp.status_code == 200


async def test_create_meeting_forbidden_for_member(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("meeting")
    obj("team", team_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/meetings",
        json={"starts_at": "2026-01-01T10:00:00Z",
              "ends_at": "2026-01-01T11:00:00Z", "max_members": 5},
    )
    assert resp.status_code == 403


async def test_read_meetings_success(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("meeting").get_meetings.return_value = [
        SimpleNamespace(id="m1", starts_at="2026-01-01T10:00:00Z",
                        ends_at="2026-01-01T11:00:00Z", max_members=5)
    ]
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/meetings")
    assert resp.status_code == 200


async def test_read_meeting_success(client, as_user, service, obj, member, team_obj, meeting_obj):
    as_user(member)
    service("meeting").get_meeting.return_value = meeting_obj
    obj("team", team_obj)
    obj("meeting", meeting_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/meetings/{meeting_obj.id}")
    assert resp.status_code == 200


async def test_update_meeting_success(client, as_user, service, obj, manager, team_obj, meeting_obj):
    as_user(manager)
    updated = SimpleNamespace(**{**meeting_obj.__dict__, "max_members": 10})
    service("meeting").update.return_value = updated
    obj("team", team_obj)
    obj("meeting", meeting_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/meetings/{meeting_obj.id}",
        json={"max_members": 10},
    )
    assert resp.status_code == 200


async def test_update_meeting_forbidden_for_member(client, as_user, service, obj, member, team_obj, meeting_obj):
    as_user(member)
    service("meeting")
    obj("team", team_obj)
    obj("meeting", meeting_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/meetings/{meeting_obj.id}",
        json={"max_members": 10},
    )
    assert resp.status_code == 403


async def test_delete_meeting_success(client, as_user, service, obj, manager, team_obj, meeting_obj):
    as_user(manager)
    service("meeting").delete.return_value = {"status": "ok"}
    obj("team", team_obj)
    obj("meeting", meeting_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}/meetings/{meeting_obj.id}")
    assert resp.status_code == 200


async def test_delete_meeting_forbidden_for_member(client, as_user, service, obj, member, team_obj, meeting_obj):
    as_user(member)
    service("meeting")
    obj("team", team_obj)
    obj("meeting", meeting_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}/meetings/{meeting_obj.id}")
    assert resp.status_code == 403