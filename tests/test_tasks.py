
import uuid
from unittest.mock import ANY

import pytest
from fastapi import HTTPException

from app.models import RateEnum
from app.models.RoleEnum import RoleEnum
from tests.conftest import make_user


TASK_ID       = uuid.UUID("11111111-1111-1111-1111-111111111111")
COMMENT_ID    = uuid.UUID("22222222-2222-2222-2222-222222222222")
EVALUATION_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
AUTHOR_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def comment_payload(**overrides):
    return {
        "task_id": str(TASK_ID),
        "text": "hi",
        "author": str(AUTHOR_ID),
        **overrides,
    }


def evaluation_payload(rate=RateEnum.FAIL.value, **overrides):
    """
    rate по умолчанию — FAIL (== 1), а не UNRATED (== 0):
    UNRATED семантически «ещё не оценивали», и его обычно не шлют при создании.
    """
    return {
        "task_id": str(TASK_ID),
        "rate": rate,          # int (FAIL.value == 1)
        **overrides,
    }


# ============================================================
#  Общие проверки check_user_identity
# ============================================================

class TestIdentityGuard:
    def test_guest_role_forbidden(self, client, current_user_box):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 403
        assert "must be a member" in response.json()["detail"]

    def test_member_not_in_team_forbidden(
        self, client, current_user_box, mock_team_service,
    ):
        current_user_box["user"] = make_user(RoleEnum.MEMBER)
        mock_team_service.belong_to_team.return_value = False

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 403
        assert "part of the task's team" in response.json()["detail"]

    def test_task_not_found_propagates(
        self, client, current_user_box, mock_task_service,
    ):
        current_user_box["user"] = make_user(RoleEnum.MEMBER)
        mock_task_service.get_task.side_effect = HTTPException(
            status_code=404, detail="Task not found",
        )

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 404
        assert response.json() == {"detail": "Task not found"}


# ============================================================
#  POST /tasks/{task_id}/comments
# ============================================================

class TestWriteComment:
    def test_success(
        self, client, current_user_box,
        mock_comment_service,
    ):
        current_user_box["user"] = make_user(RoleEnum.MEMBER)
        mock_comment_service.create_comment.return_value = {"id": 1, "text": "hi"}

        response = client.post(
            f"/tasks/{TASK_ID}/comments",
            json=comment_payload(text="hi"),
        )

        assert response.status_code == 200, response.json()

        # сервис получил ровно CommentCreate с нашими полями
        mock_comment_service.create_comment.assert_awaited_once()
        arg = mock_comment_service.create_comment.await_args.args[0]
        assert arg.task_id == TASK_ID
        assert arg.text == "hi"
        assert arg.author == AUTHOR_ID

    @pytest.mark.parametrize("role", [RoleEnum.MANAGER, RoleEnum.MEMBER])
    def test_allowed_roles_pass_guard(self, client, current_user_box, role,
                                      mock_comment_service):
        current_user_box["user"] = make_user(role)
        mock_comment_service.create_comment.return_value = {"id": 1}

        response = client.post(
            f"/tasks/{TASK_ID}/comments",
            json=comment_payload(),
        )

        assert response.status_code == 200, response.json()

    def test_forbidden_for_guest(self, client, current_user_box, mock_comment_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.post(
            f"/tasks/{TASK_ID}/comments",
            json=comment_payload(),
        )

        assert response.status_code == 403
        mock_comment_service.create_comment.assert_not_awaited()

    @pytest.mark.parametrize(
        "payload",
        [
            {},                                            # пусто
            {"text": "x"},                                 # нет task_id и author
            {"task_id": str(TASK_ID), "text": "x"},        # нет author
            {"task_id": str(TASK_ID), "author": str(AUTHOR_ID)},  # нет text
        ],
    )
    def test_missing_fields_returns_422(self, client, mock_comment_service, payload):
        response = client.post(f"/tasks/{TASK_ID}/comments", json=payload)

        assert response.status_code == 422
        mock_comment_service.create_comment.assert_not_awaited()

    def test_invalid_task_id_returns_422(self, client):
        response = client.post(
            "/tasks/not-a-uuid/comments",
            json=comment_payload(),
        )
        assert response.status_code == 422


# ============================================================
#  GET /tasks/{task_id}/comments
# ============================================================

class TestReadComments:
    def test_success(self, client, mock_comment_service):
        mock_comment_service.get_comments.return_value = [
            {"id": 1, "text": "a"},
            {"id": 2, "text": "b"},
        ]

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 200
        assert response.json() == [
            {"id": 1, "text": "a"},
            {"id": 2, "text": "b"},
        ]
        mock_comment_service.get_comments.assert_awaited_once_with(TASK_ID)

    def test_forbidden_for_guest(self, client, current_user_box, mock_comment_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 403
        mock_comment_service.get_comments.assert_not_awaited()

    def test_empty_list_is_ok(self, client, mock_comment_service):
        mock_comment_service.get_comments.return_value = []

        response = client.get(f"/tasks/{TASK_ID}/comments")

        assert response.status_code == 200
        assert response.json() == []


# ============================================================
#  PATCH /tasks/{task_id}/comments/{comment_id}
# ============================================================

class TestEditComment:
    def test_success(self, client, mock_comment_service):
        mock_comment_service.update.return_value = {"id": 1, "text": "new"}

        response = client.patch(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
            json={"text": "new"},
        )

        assert response.status_code == 200
        assert response.json() == {"id": 1, "text": "new"}

        # ✅ в сервис уходит comment_id, а не task_id
        mock_comment_service.update.assert_awaited_once_with(COMMENT_ID, ANY)

    def test_forbidden_for_guest(self, client, current_user_box, mock_comment_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.patch(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
            json={"text": "x"},
        )

        assert response.status_code == 403
        mock_comment_service.update.assert_not_awaited()

    def test_forbidden_not_in_team(
        self, client, mock_team_service, mock_comment_service,
    ):
        mock_team_service.belong_to_team.return_value = False

        response = client.patch(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
            json={"text": "x"},
        )

        assert response.status_code == 403
        mock_comment_service.update.assert_not_awaited()

    def test_empty_body_still_calls_service(self, client, mock_comment_service):
        mock_comment_service.update.return_value = {"id": 1}

        response = client.patch(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
            json={},
        )

        assert response.status_code == 200
        mock_comment_service.update.assert_awaited_once_with(COMMENT_ID, ANY)

    def test_invalid_comment_id_returns_422(self, client):
        response = client.patch(
            f"/tasks/{TASK_ID}/comments/not-a-uuid",
            json={"text": "x"},
        )
        assert response.status_code == 422


# ============================================================
#  DELETE /tasks/{task_id}/comments/{comment_id}
# ============================================================

class TestDeleteComment:
    def test_success(self, client, mock_comment_service):
        mock_comment_service.delete.return_value = None

        response = client.delete(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
        )

        assert response.status_code == 200
        assert response.json() is None

        # ✅ в сервис уходит comment_id
        mock_comment_service.delete.assert_awaited_once_with(COMMENT_ID)

    def test_forbidden_for_guest(self, client, current_user_box, mock_comment_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.delete(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
        )

        assert response.status_code == 403
        mock_comment_service.delete.assert_not_awaited()

    def test_forbidden_not_in_team(
        self, client, mock_team_service, mock_comment_service,
    ):
        mock_team_service.belong_to_team.return_value = False

        response = client.delete(
            f"/tasks/{TASK_ID}/comments/{COMMENT_ID}",
        )

        assert response.status_code == 403
        mock_comment_service.delete.assert_not_awaited()

    def test_invalid_comment_id_returns_422(self, client):
        response = client.delete(
            f"/tasks/{TASK_ID}/comments/not-a-uuid",
        )
        assert response.status_code == 422


# ============================================================
#  POST /tasks/{task_id}/evaluation
# ============================================================

class TestWriteEvaluation:
    def test_success(self, client, mock_evaluation_service):
        mock_evaluation_service.create_evaluation.return_value = {"id": 1, "rate": 1}

        response = client.post(
            f"/tasks/{TASK_ID}/evaluation",
            json=evaluation_payload(),          # rate = RateEnum.FAIL.value == 1
        )

        assert response.status_code == 200, response.json()

        arg = mock_evaluation_service.create_evaluation.await_args.args[0]
        assert arg.task_id == TASK_ID
        assert arg.rate is RateEnum.FAIL     # ← уже член enum, не int

    @pytest.mark.parametrize("member", list(RateEnum), ids=lambda m: m.name)
    def test_all_rate_values_accepted(self, client, mock_evaluation_service, member):
        mock_evaluation_service.create_evaluation.return_value = {"id": 1}

        response = client.post(
            f"/tasks/{TASK_ID}/evaluation",
            json=evaluation_payload(rate=member.value),
        )

        assert response.status_code == 200, response.json()
        assert mock_evaluation_service.create_evaluation.await_args.args[0].rate is member

    @pytest.mark.parametrize("bad_rate", [6, -1, "perfect", None, {}])
    def test_invalid_rate_returns_422(self, client, mock_evaluation_service, bad_rate):
        response = client.post(
            f"/tasks/{TASK_ID}/evaluation",
            json={"task_id": str(TASK_ID), "rate": bad_rate},
        )
        assert response.status_code == 422
        mock_evaluation_service.create_evaluation.assert_not_awaited()

    def test_forbidden_for_guest(self, client, current_user_box, mock_evaluation_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)
        response = client.post(f"/tasks/{TASK_ID}/evaluation", json=evaluation_payload())
        assert response.status_code == 403
        mock_evaluation_service.create_evaluation.assert_not_awaited()

    def test_forbidden_not_in_team(
        self, client, mock_team_service, mock_evaluation_service,
    ):
        mock_team_service.belong_to_team.return_value = False
        response = client.post(f"/tasks/{TASK_ID}/evaluation", json=evaluation_payload())
        assert response.status_code == 403
        mock_evaluation_service.create_evaluation.assert_not_awaited()

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"task_id": str(TASK_ID)},            # нет rate
            {"rate": RateEnum.FAIL.value},        # нет task_id
        ],
    )
    def test_missing_fields_returns_422(self, client, mock_evaluation_service, payload):
        response = client.post(f"/tasks/{TASK_ID}/evaluation", json=payload)
        assert response.status_code == 422
        mock_evaluation_service.create_evaluation.assert_not_awaited()


# ============================================================
#  GET /tasks/{task_id}/evaluation
# ============================================================

class TestReadEvaluation:
    def test_success(self, client, mock_evaluation_service):
        mock_evaluation_service.get_evaluation.return_value = {"id": 1, "score": 5}

        response = client.get(f"/tasks/{TASK_ID}/evaluation")

        assert response.status_code == 200
        assert response.json() == {"id": 1, "score": 5}
        # здесь по-прежнему task_id — эндпоинт без evaluation_id
        mock_evaluation_service.get_evaluation.assert_awaited_once_with(TASK_ID)

    def test_forbidden_for_guest(self, client, current_user_box, mock_evaluation_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.get(f"/tasks/{TASK_ID}/evaluation")

        assert response.status_code == 403
        mock_evaluation_service.get_evaluation.assert_not_awaited()


# ============================================================
#  PATCH /tasks/{task_id}/evaluation/{evaluation_id}
# ============================================================

class TestEditEvaluation:
    def test_success(self, client, mock_evaluation_service):
        mock_evaluation_service.update.return_value = {"id": 1, "score": 4}

        response = client.patch(
            f"/tasks/{TASK_ID}/evaluation/{EVALUATION_ID}",
            json={"score": 4},
        )

        assert response.status_code == 200
        assert response.json() == {"id": 1, "score": 4}

        # ✅ в сервис уходит evaluation_id
        mock_evaluation_service.update.assert_awaited_once_with(EVALUATION_ID, ANY)

    def test_forbidden_for_guest(self, client, current_user_box, mock_evaluation_service):
        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.patch(
            f"/tasks/{TASK_ID}/evaluation/{EVALUATION_ID}",
            json={"score": 4},
        )

        assert response.status_code == 403
        mock_evaluation_service.update.assert_not_awaited()

    def test_invalid_evaluation_id_returns_422(self, client):
        response = client.patch(
            f"/tasks/{TASK_ID}/evaluation/not-a-uuid",
            json={"score": 4},
        )
        assert response.status_code == 422


# ============================================================
#  Контракт роутера
# ============================================================

class TestTasksRouterContract:
    def test_openapi_paths_and_tags(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]

        expected = [
            "/tasks/{task_id}/comments",
            "/tasks/{task_id}/comments/{comment_id}",
            "/tasks/{task_id}/evaluation",
            "/tasks/{task_id}/evaluation/{evaluation_id}",
        ]
        for p in expected:
            assert p in paths, f"missing path {p}"
            for method, op in paths[p].items():
                assert op["tags"] == ["tasks"]

    def test_all_declared_methods_present(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]

        assert set(paths["/tasks/{task_id}/comments"]) == {"post", "get"}
        assert set(paths["/tasks/{task_id}/comments/{comment_id}"]) == {"patch", "delete"}
        assert set(paths["/tasks/{task_id}/evaluation"]) == {"post", "get"}
        # у evaluation по-прежнему нет DELETE в роутере
        assert set(paths["/tasks/{task_id}/evaluation/{evaluation_id}"]) == {"patch"}

    def test_comment_id_is_path_param(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/tasks/{task_id}/comments/{comment_id}"]["patch"]
        param_names = {p["name"] for p in op["parameters"]}
        assert {"task_id", "comment_id"} <= param_names

    def test_evaluation_id_is_path_param(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/tasks/{task_id}/evaluation/{evaluation_id}"]["patch"]
        param_names = {p["name"] for p in op["parameters"]}
        assert {"task_id", "evaluation_id"} <= param_names