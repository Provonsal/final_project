from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_create_evaluation_success(client, as_user, service, obj, manager, team_obj, task_obj):
    as_user(manager)
    service("evaluation").create_evaluation.return_value = SimpleNamespace(
        id="e1", rate=5, task_id=task_obj.id, rater=manager.id,
    )
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/evaluation",
        json={"task_id": str(task_obj.id), "rate": 5},
    )
    assert resp.status_code == 200


async def test_read_evaluation_success(
    client, as_user, service, obj, member, team_obj, task_obj, evaluation_obj
):
    as_user(member)
    service("evaluation").get_evaluation.return_value = evaluation_obj
    obj("team", team_obj)
    obj("task", task_obj)
    obj("evaluation", evaluation_obj)
    resp = await client.get(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/evaluation"
    )
    assert resp.status_code == 200


async def test_update_evaluation_success(
    client, as_user, service, obj, manager, team_obj, task_obj, evaluation_obj
):
    as_user(manager)
    service("evaluation").update.return_value = SimpleNamespace(
        id=evaluation_obj.id, rate=4, task_id=task_obj.id, rater=manager.id,
    )
    obj("team", team_obj)
    obj("task", task_obj)
    obj("evaluation", evaluation_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/evaluation/{evaluation_obj.id}",
        json={"rate": 4},
    )
    assert resp.status_code == 200