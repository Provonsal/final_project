from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


async def test_create_comment_success(client, as_user, service, obj, member, team_obj, task_obj):
    as_user(member)
    service("comment").create_comment.return_value = SimpleNamespace(
        id="c1", text="Hi", author=member.id, task_id=task_obj.id,
    )
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.post(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/comments",
        json={"text": "Hi"},
    )
    assert resp.status_code == 200


async def test_read_comments_success(client, as_user, service, obj, member, team_obj, task_obj):
    as_user(member)
    service("comment").get_comments.return_value = [
        SimpleNamespace(id="c1", text="Hi", author=member.id, task_id=task_obj.id)
    ]
    obj("team", team_obj)
    obj("task", task_obj)
    resp = await client.get(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/comments"
    )
    assert resp.status_code == 200


async def test_update_comment_success(
    client, as_user, service, obj, member, team_obj, task_obj, comment_obj
):
    as_user(member)
    service("comment").update.return_value = SimpleNamespace(
        id=comment_obj.id, text="Edited", author=member.id, task_id=task_obj.id,
    )
    obj("team", team_obj)
    obj("task", task_obj)
    obj("comment", comment_obj)
    resp = await client.patch(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/comments/{comment_obj.id}",
        json={"text": "Edited"},
    )
    assert resp.status_code == 200


async def test_delete_comment_success(
    client, as_user, service, obj, member, team_obj, task_obj, comment_obj
):
    as_user(member)
    service("comment").delete.return_value = {"status": "ok"}
    obj("team", team_obj)
    obj("task", task_obj)
    obj("comment", comment_obj)
    resp = await client.delete(
        f"/api/v1/teams/{team_obj.id}/tasks/{task_obj.id}/comments/{comment_obj.id}"
    )
    assert resp.status_code == 200