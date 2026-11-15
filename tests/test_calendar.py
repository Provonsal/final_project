from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_get_calendar_success(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("calendar").get_meetings.return_value = [
        SimpleNamespace(id="m1", starts_at="2026-01-01T10:00:00Z",
                        ends_at="2026-01-01T11:00:00Z", max_members=5),
    ]
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/calendar/{team_obj.id}")
    assert resp.status_code == 200


async def test_get_calendar_forbidden_for_guest(client, as_user, service, obj, guest, team_obj):
    as_user(guest)
    service("calendar")
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/calendar/{team_obj.id}")
    assert resp.status_code == 403


async def test_get_calendar_with_date_range(client, as_user, service, obj, member, team_obj):
    as_user(member)
    calendar_service = service("calendar")
    calendar_service.get_meetings.return_value = []
    obj("team", team_obj)
    resp = await client.get(
        f"/api/v1/calendar/{team_obj.id}",
        params={
            "date_from": "2026-01-01T00:00:00Z",
            "date_until": "2026-01-31T23:59:59Z",
        },
    )
    assert resp.status_code == 200
    calendar_service.get_meetings.assert_awaited_once()