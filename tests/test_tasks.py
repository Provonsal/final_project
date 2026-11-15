from types import SimpleNamespace

import pytest

from app.exc.exceptions import NotFoundError


pytestmark = pytest.mark.asyncio


async def test_create_task_success(client, as_user, service, obj, manager, team_obj):
    as_user(manager)
    service("task").create_task.return_value = SimpleNamespace(
        id="t1", title="Do it", description="", status=1,
        assignee=manager.id, team_id=team_obj.id,
    )
    obj("team", team_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/tasks",
        json={
            "title": "Do it", "description": "D",
            "assignee": str(manager.id), "due_date": "2026-01-01T00:00:00Z", "status": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Do it"


async def test_create_task_forbidden_for_member(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("task")
    obj("team", team_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/tasks",
        json={
            "title": "Do it", "description": "D",
            "assignee": str(member.id), "due_date": "2026-01-01T00:00:00Z", "status": 1,
        },
    )
    assert resp.status_code == 403


async def test_read_tasks_success(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("task").get_all_tasks.return_value = [
        SimpleNamespace(id="t1", title="A", description="", status=1,
                        assignee=member.id, team_id=team_obj.id)
    ]
    obj("team", team_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/tasks")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "A"


async def test_read_task_success(client, as_user, service, obj, member, team_obj, task_obj):
    as_user(member)
    service("task").get_task.return_value = task_obj
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}")
    assert resp.status_code == 200


async def test_read_task_not_found(client, as_user, service, obj, member, team_obj):
    as_user(member)
    service("task")
    obj("team", team_obj)
    obj("task", error=NotFoundError(resource="Task", resource_id="x"))
    import uuid
    resp = await client.get(f"/api/v1/teams/{team_obj.id}/tasks/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_task_success(client, as_user, service, obj, manager, team_obj, task_obj):
    as_user(manager)
    updated = SimpleNamespace(**{**task_obj.__dict__, "title": "New"})
    service("task").update_task.return_value = updated
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}",
        json={"title": "New"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


async def test_update_task_forbidden_for_member(client, as_user, service, obj, member, team_obj, task_obj):
    as_user(member)
    service("task")
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}",
        json={"title": "X"},
    )
    assert resp.status_code == 403


async def test_delete_task_success(client, as_user, service, obj, manager, team_obj, task_obj):
    as_user(manager)
    service("task").delete_task.return_value = {"status": "ok"}
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}")
    assert resp.status_code == 200


async def test_delete_task_forbidden_for_member(client, as_user, service, obj, member, team_obj, task_obj):
    as_user(member)
    service("task")
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.delete(f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}")
    assert resp.status_code == 403