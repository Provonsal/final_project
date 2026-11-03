# tests/test_teams.py
"""
Тесты для роутера /teams.

Покрывает:
- POST   /teams/join
- GET    /teams/{team_id}/members
- CRUD   /teams/{team_id}/tasks
- CRUD   /teams/{team_id}/meetings
- контракт OpenAPI

Не покрывает (пока):
- реальную работу guard-ов по ролям/командам — роутер их не вызывает,
  team_id/current_user в сервисы не передаются; поведение зафиксировано
  как «есть на текущий момент» и помечено ⚠️
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import ANY

import pytest

from app.models.TaskStatusEnum import TaskStatusEnum   # ← подправьте путь, если у вас иначе
from app.schemas.task_create import TaskCreate
from app.schemas.task_update import TaskUpdate
from app.schemas.create_meeting import MeetingCreate
from app.schemas.update_meeting import MeetingUpdate


# ============================================================
#  Константы
# ============================================================

TEAM_ID    = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TASK_ID    = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
MEETING_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
USER_ID    = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
ASSIGNEE   = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
INVITE     = "INVITE-123"

DUE_DATE  = "2030-01-01T12:00:00Z"
STARTS_AT = "2030-02-01T10:00:00Z"
ENDS_AT   = "2030-02-01T11:00:00Z"


# ============================================================
#  Фабрики payload-ов
# ============================================================

def task_payload(**overrides):
    """Body для POST /teams/{team_id}/tasks (TaskCreate)."""
    return {
        "title": "Write tests",
        "description": "cover /teams router",
        "assignee": str(ASSIGNEE),
        "due_date": DUE_DATE,
        # status не шлём — проверяем дефолт отдельным тестом
        **overrides,
    }


def task_update_payload(**overrides):
    """Body для PATCH /teams/{team_id}/tasks/{task_id} (TaskUpdate, все optional)."""
    return {"title": "Updated", **overrides}


def meeting_payload(**overrides):
    """Body для POST /teams/{team_id}/meetings (MeetingCreate)."""
    return {
        "starts_at": STARTS_AT,
        "ends_at": ENDS_AT,
        "max_members": 10,
        "related_team": str(TEAM_ID),
        "creator": str(USER_ID),
        **overrides,
    }


def meeting_update_payload(**overrides):
    """Body для PATCH /teams/{team_id}/meetings/{meeting_id} (MeetingUpdate, все optional)."""
    return {"max_members": 20, **overrides}


# ============================================================
#  POST /teams/join   (invite_code — query-параметр)
# ============================================================

class TestJoin:
    def test_success(self, client, current_user_box, mock_team_service):
        response = client.post(f"/teams/join?invite_code={INVITE}")

        assert response.status_code == 200, response.json()
        assert response.json() is None              # роутер ничего не возвращает
        mock_team_service.join_team.assert_awaited_once_with(
            current_user_box["user"].id, INVITE,
        )

    def test_value_error_returns_405(self, client, mock_team_service):
        mock_team_service.join_team.side_effect = ValueError("Invite code not active")

        response = client.post("/teams/join?invite_code=BAD")

        assert response.status_code == 405
        assert response.json() == {"detail": "Invite code not active"}
        mock_team_service.join_team.assert_awaited_once()

    def test_missing_invite_code_returns_422(self, client, mock_team_service):
        response = client.post("/teams/join")

        assert response.status_code == 422
        mock_team_service.join_team.assert_not_awaited()

    def test_empty_invite_code_is_allowed(self, client, mock_team_service):
        """Пустая строка проходит как query-параметр — сервис уже решает, что с ней делать."""
        response = client.post("/teams/join?invite_code=")

        assert response.status_code == 200
        mock_team_service.join_team.assert_awaited_once_with(
            ANY, "",
        )


# ============================================================
#  GET /teams/{team_id}/members
# ============================================================

class TestMembers:
    def test_success(self, client, current_user_box, mock_team_service):
        mock_team_service.get_team_users.return_value = [
            {"id": str(USER_ID), "name": "Alice"},
        ]

        response = client.get(f"/teams/{TEAM_ID}/members")

        assert response.status_code == 200
        assert response.json() == [{"id": str(USER_ID), "name": "Alice"}]
        mock_team_service.get_team_users.assert_awaited_once_with(
            TEAM_ID, current_user_box["user"].id,
        )

    def test_empty_list_is_ok(self, client, mock_team_service):
        mock_team_service.get_team_users.return_value = []

        response = client.get(f"/teams/{TEAM_ID}/members")

        assert response.status_code == 200
        assert response.json() == []

    def test_value_error_returns_405(self, client, mock_team_service):
        mock_team_service.get_team_users.side_effect = ValueError(
            "You are not allowed to do that.",
        )

        response = client.get(f"/teams/{TEAM_ID}/members")

        assert response.status_code == 405
        assert response.json() == {"detail": "You are not allowed to do that."}

    def test_invalid_team_id_returns_422(self, client):
        response = client.get("/teams/not-a-uuid/members")
        assert response.status_code == 422


# ============================================================
#  POST /teams/{team_id}/tasks
# ============================================================

class TestCreateTask:
    def test_success_passes_taskcreate_and_team_id(self, client, mock_task_service):
        response = client.post(
            f"/teams/{TEAM_ID}/tasks",
            json=task_payload(),
        )

        assert response.status_code == 200, response.json()
        assert response.json() is None

        mock_task_service.create_task.assert_awaited_once()
        data, team_id = mock_task_service.create_task.await_args.args

        assert isinstance(data, TaskCreate)
        assert data.title == "Write tests"
        assert data.description == "cover /teams router"
        assert data.assignee == ASSIGNEE
        assert data.due_date.tzinfo is not None      # aware datetime
        assert team_id == TEAM_ID

    def test_status_defaults_to_open(self, client, mock_task_service):
        response = client.post(f"/teams/{TEAM_ID}/tasks", json=task_payload())

        assert response.status_code == 200, response.json()
        data, _ = mock_task_service.create_task.await_args.args
        assert data.status is TaskStatusEnum.OPEN
        assert data.status.value == 1

    @pytest.mark.parametrize(
        "member,raw_value",
        [
            (TaskStatusEnum.OPEN, 1),
            (TaskStatusEnum.IN_PROGRESS, 2),
            (TaskStatusEnum.DONE, 3),
        ],
        ids=lambda x: x.name if hasattr(x, "name") else str(x),
    )
    def test_status_accepts_enum_value_as_int(
        self, client, mock_task_service, member, raw_value,
    ):
        """`enum.Enum` с auto() → в JSON шлём int (raw value), не имя."""
        response = client.post(
            f"/teams/{TEAM_ID}/tasks",
            json=task_payload(status=raw_value),
        )

        assert response.status_code == 200, response.json()
        data, _ = mock_task_service.create_task.await_args.args
        assert data.status is member

    def test_status_string_name_is_rejected(self, client, mock_task_service):
        """Строка 'in_progress' не приводится к enum.Enum → 422."""
        response = client.post(
            f"/teams/{TEAM_ID}/tasks",
            json=task_payload(status="in_progress"),
        )

        assert response.status_code == 422
        mock_task_service.create_task.assert_not_awaited()

    @pytest.mark.parametrize(
        "payload",
        [
            {},                                                  # пусто
            {"title": "t"},                                      # нет description/assignee/due_date
            {"title": "t", "description": "d"},                  # нет assignee/due_date
            task_payload(assignee="not-a-uuid"),                 # невалидный UUID
            task_payload(due_date="not-a-date"),                 # невалидный datetime
            task_payload(status=99),                             # нет такого значения enum
        ],
    )
    def test_invalid_body_returns_422(self, client, mock_task_service, payload):
        response = client.post(f"/teams/{TEAM_ID}/tasks", json=payload)

        assert response.status_code == 422
        mock_task_service.create_task.assert_not_awaited()

    def test_missing_body_returns_422(self, client, mock_task_service):
        response = client.post(f"/teams/{TEAM_ID}/tasks")

        assert response.status_code == 422
        mock_task_service.create_task.assert_not_awaited()

    def test_invalid_team_id_returns_422(self, client):
        response = client.post("/teams/not-a-uuid/tasks", json=task_payload())
        assert response.status_code == 422

    # ⚠️ Проверки роли/членства в команде отсутствуют — фиксируем как есть.
    def test_guest_still_can_create_task_currently(
        self, client, current_user_box, mock_task_service,
    ):
        from tests.conftest import make_user
        from app.models.RoleEnum import RoleEnum

        current_user_box["user"] = make_user(RoleEnum.GUEST)

        response = client.post(f"/teams/{TEAM_ID}/tasks", json=task_payload())

        assert response.status_code == 200, response.json()
        mock_task_service.create_task.assert_awaited_once()


# ============================================================
#  GET /teams/{team_id}/tasks
# ============================================================

class TestReadTasks:
    def test_success(self, client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = [
            {"id": str(TASK_ID), "title": "t"},
            {"id": "22222222-2222-2222-2222-222222222222", "title": "t2"},
        ]

        response = client.get(f"/teams/{TEAM_ID}/tasks")

        assert response.status_code == 200
        assert response.json() == [
            {"id": str(TASK_ID), "title": "t"},
            {"id": "22222222-2222-2222-2222-222222222222", "title": "t2"},
        ]
        mock_task_service.get_all_tasks.assert_awaited_once_with(TEAM_ID)

    def test_empty_list_is_ok(self, client, mock_task_service):
        mock_task_service.get_all_tasks.return_value = []

        response = client.get(f"/teams/{TEAM_ID}/tasks")

        assert response.status_code == 200
        assert response.json() == []

    def test_invalid_team_id_returns_422(self, client):
        response = client.get("/teams/not-a-uuid/tasks")
        assert response.status_code == 422


# ============================================================
#  GET /teams/{team_id}/tasks/{task_id}
# ============================================================

class TestReadSingleTask:
    def test_success(self, client, mock_task_service):
        mock_task_service.get_task.return_value = {"id": str(TASK_ID), "title": "t"}

        response = client.get(f"/teams/{TEAM_ID}/tasks/{TASK_ID}")

        assert response.status_code == 200
        assert response.json() == {"id": str(TASK_ID), "title": "t"}
        # ⚠️ team_id в сервис не передаётся — принадлежность к команде не проверяется
        mock_task_service.get_task.assert_awaited_once_with(TASK_ID)

    def test_invalid_task_id_returns_422(self, client):
        response = client.get(f"/teams/{TEAM_ID}/tasks/not-a-uuid")
        assert response.status_code == 422

    def test_invalid_team_id_returns_422(self, client):
        response = client.get(f"/teams/not-a-uuid/tasks/{TASK_ID}")
        assert response.status_code == 422


# ============================================================
#  PATCH /teams/{team_id}/tasks/{task_id}
# ============================================================

class TestUpdateTask:
    def test_success_with_partial_body(self, client, mock_task_service):
        response = client.patch(
            f"/teams/{TEAM_ID}/tasks/{TASK_ID}",
            json=task_update_payload(title="Only title"),
        )

        assert response.status_code == 200
        assert response.json() is None              # роутер ничего не возвращает

        mock_task_service.update_task.assert_awaited_once()
        task_id_arg, data = mock_task_service.update_task.await_args.args
        assert task_id_arg == TASK_ID
        assert isinstance(data, TaskUpdate)
        assert data.model_dump(exclude_unset=True) == {"title": "Only title"}

    def test_empty_body_is_allowed(self, client, mock_task_service):
        """Все поля optional — {} валиден, решение что менять — в сервисе."""
        response = client.patch(
            f"/teams/{TEAM_ID}/tasks/{TASK_ID}",
            json={},
        )

        assert response.status_code == 200
        mock_task_service.update_task.assert_awaited_once()
        _, data = mock_task_service.update_task.await_args.args
        assert data.model_dump(exclude_unset=True) == {}

    def test_full_body(self, client, mock_task_service):
        payload = {
            "title": "New",
            "description": "New desc",
            "assignee": str(ASSIGNEE),
            "due_date": DUE_DATE,
        }
        response = client.patch(
            f"/teams/{TEAM_ID}/tasks/{TASK_ID}",
            json=payload,
        )

        assert response.status_code == 200
        _, data = mock_task_service.update_task.await_args.args
        assert data.model_dump(mode="json", exclude_unset=True) == payload

    def test_missing_body_returns_422(self, client, mock_task_service):
        response = client.patch(f"/teams/{TEAM_ID}/tasks/{TASK_ID}")

        assert response.status_code == 422
        mock_task_service.update_task.assert_not_awaited()

    @pytest.mark.parametrize(
        "payload",
        [
            {"due_date": "not-a-date"},
            {"assignee": "not-a-uuid"},
            {"title": 123},                          # число → Pydantic v2 не приведёт к str автоматически
        ],
    )
    def test_invalid_field_returns_422(self, client, mock_task_service, payload):
        response = client.patch(
            f"/teams/{TEAM_ID}/tasks/{TASK_ID}",
            json=payload,
        )

        # для title: 123 Pydantic v2 в lax-режиме обычно приводит → если 200,
        # уберите эту параметризацию
        assert response.status_code == 422
        mock_task_service.update_task.assert_not_awaited()


# ============================================================
#  DELETE /teams/{team_id}/tasks/{task_id}
# ============================================================

class TestDeleteTask:
    def test_success(self, client, mock_task_service):
        response = client.delete(f"/teams/{TEAM_ID}/tasks/{TASK_ID}")

        assert response.status_code == 200
        assert response.json() is None
        mock_task_service.delete_task.assert_awaited_once_with(TASK_ID)

    def test_invalid_task_id_returns_422(self, client):
        response = client.delete(f"/teams/{TEAM_ID}/tasks/not-a-uuid")
        assert response.status_code == 422


# ============================================================
#  POST /teams/{team_id}/meetings
# ============================================================

class TestCreateMeeting:
    def test_success_passes_meetingcreate_as_is(self, client, mock_meeting_service):
        response = client.post(
            f"/teams/{TEAM_ID}/meetings",
            json=meeting_payload(),
        )

        assert response.status_code == 200, response.json()
        assert response.json() is None

        mock_meeting_service.create_meeting.assert_awaited_once()
        data = mock_meeting_service.create_meeting.await_args.args[0]

        assert isinstance(data, MeetingCreate)
        assert data.max_members == 10
        assert data.related_team == TEAM_ID
        assert data.creator == USER_ID
        assert data.starts_at.tzinfo is not None
        assert data.ends_at.tzinfo is not None

    def test_max_members_defaults_to_10(self, client, mock_meeting_service):
        payload = meeting_payload()
        payload.pop("max_members")

        response = client.post(f"/teams/{TEAM_ID}/meetings", json=payload)

        assert response.status_code == 200, response.json()
        data = mock_meeting_service.create_meeting.await_args.args[0]
        assert data.max_members == 10

    # ⚠️ Роутер не передаёт team_id/current_user в сервис — всё берётся из body.
    def test_related_team_comes_from_body_not_from_path(
        self, client, mock_meeting_service,
    ):
        other_team = uuid.uuid4()

        response = client.post(
            f"/teams/{TEAM_ID}/meetings",
            json=meeting_payload(related_team=str(other_team)),
        )

        assert response.status_code == 200, response.json()
        data = mock_meeting_service.create_meeting.await_args.args[0]
        assert data.related_team == other_team   # создали встречу в «чужой» команде

    def test_creator_comes_from_body_not_from_current_user(
        self, client, current_user_box, mock_meeting_service,
    ):
        other_user = uuid.uuid4()

        response = client.post(
            f"/teams/{TEAM_ID}/meetings",
            json=meeting_payload(creator=str(other_user)),
        )

        assert response.status_code == 200, response.json()
        data = mock_meeting_service.create_meeting.await_args.args[0]
        assert data.creator == other_user
        assert data.creator != current_user_box["user"].id

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"starts_at": STARTS_AT, "ends_at": ENDS_AT},     # нет related_team/creator
            meeting_payload(related_team="not-a-uuid"),
            meeting_payload(creator="not-a-uuid"),
            meeting_payload(starts_at="not-a-date"),
            meeting_payload(ends_at="not-a-date"),
        ],
    )
    def test_invalid_body_returns_422(self, client, mock_meeting_service, payload):
        response = client.post(f"/teams/{TEAM_ID}/meetings", json=payload)

        assert response.status_code == 422
        mock_meeting_service.create_meeting.assert_not_awaited()

    def test_missing_body_returns_422(self, client, mock_meeting_service):
        response = client.post(f"/teams/{TEAM_ID}/meetings")

        assert response.status_code == 422
        mock_meeting_service.create_meeting.assert_not_awaited()

    def test_invalid_team_id_returns_422(self, client):
        response = client.post("/teams/not-a-uuid/meetings", json=meeting_payload())
        assert response.status_code == 422


# ============================================================
#  GET /teams/{team_id}/meetings
# ============================================================

class TestReadMeetings:
    def test_success(self, client, mock_meeting_service):
        mock_meeting_service.get_meetings.return_value = [
            {"id": str(MEETING_ID), "max_members": 5},
        ]

        response = client.get(f"/teams/{TEAM_ID}/meetings")

        assert response.status_code == 200
        assert response.json() == [{"id": str(MEETING_ID), "max_members": 5}]
        mock_meeting_service.get_meetings.assert_awaited_once_with(TEAM_ID)

    def test_empty_list_is_ok(self, client, mock_meeting_service):
        mock_meeting_service.get_meetings.return_value = []

        response = client.get(f"/teams/{TEAM_ID}/meetings")

        assert response.status_code == 200
        assert response.json() == []


# ============================================================
#  GET /teams/{team_id}/meetings/{meeting_id}
# ============================================================

class TestReadSingleMeeting:
    def test_success(self, client, mock_meeting_service):
        mock_meeting_service.get_meeting.return_value = {
            "id": str(MEETING_ID), "max_members": 5,
        }

        response = client.get(f"/teams/{TEAM_ID}/meetings/{MEETING_ID}")

        assert response.status_code == 200
        assert response.json() == {"id": str(MEETING_ID), "max_members": 5}
        # ⚠️ team_id в сервис не передаётся
        mock_meeting_service.get_meeting.assert_awaited_once_with(MEETING_ID)

    def test_invalid_meeting_id_returns_422(self, client):
        response = client.get(f"/teams/{TEAM_ID}/meetings/not-a-uuid")
        assert response.status_code == 422


# ============================================================
#  PATCH /teams/{team_id}/meetings/{meeting_id}
# ============================================================

class TestUpdateMeeting:
    def test_success(self, client, mock_meeting_service):
        mock_meeting_service.update.return_value = {
            "id": str(MEETING_ID), "max_members": 20,
        }

        response = client.patch(
            f"/teams/{TEAM_ID}/meetings/{MEETING_ID}",
            json=meeting_update_payload(max_members=20),
        )

        assert response.status_code == 200
        assert response.json() == {"id": str(MEETING_ID), "max_members": 20}

        mock_meeting_service.update.assert_awaited_once()
        meeting_id_arg, data = mock_meeting_service.update.await_args.args
        assert meeting_id_arg == MEETING_ID
        assert isinstance(data, MeetingUpdate)
        assert data.model_dump(exclude_unset=True) == {"max_members": 20}

    def test_empty_body_allowed(self, client, mock_meeting_service):
        mock_meeting_service.update.return_value = {"id": str(MEETING_ID)}

        response = client.patch(
            f"/teams/{TEAM_ID}/meetings/{MEETING_ID}",
            json={},
        )

        assert response.status_code == 200
        mock_meeting_service.update.assert_awaited_once()
        _, data = mock_meeting_service.update.await_args.args
        assert data.model_dump(exclude_unset=True) == {}

    def test_full_body(self, client, mock_meeting_service):
        mock_meeting_service.update.return_value = {"id": str(MEETING_ID)}
        payload = {
            "starts_at": STARTS_AT,
            "ends_at": ENDS_AT,
            "max_members": 25,
            "creator": str(USER_ID),
        }

        response = client.patch(
            f"/teams/{TEAM_ID}/meetings/{MEETING_ID}",
            json=payload,
        )

        assert response.status_code == 200
        _, data = mock_meeting_service.update.await_args.args
        assert data.model_dump(mode="json",exclude_unset=True) == payload

    @pytest.mark.parametrize(
        "payload",
        [
            {"starts_at": "not-a-date"},
            {"ends_at": "not-a-date"},
            {"creator": "not-a-uuid"},
        ],
    )
    def test_invalid_field_returns_422(self, client, mock_meeting_service, payload):
        response = client.patch(
            f"/teams/{TEAM_ID}/meetings/{MEETING_ID}",
            json=payload,
        )

        assert response.status_code == 422
        mock_meeting_service.update.assert_not_awaited()


# ============================================================
#  DELETE /teams/{team_id}/meetings/{meeting_id}
# ============================================================

class TestDeleteMeeting:
    def test_success(self, client, mock_meeting_service):
        response = client.delete(f"/teams/{TEAM_ID}/meetings/{MEETING_ID}")

        assert response.status_code == 200
        assert response.json() is None
        mock_meeting_service.delete.assert_awaited_once_with(MEETING_ID)

    def test_invalid_meeting_id_returns_422(self, client):
        response = client.delete(f"/teams/{TEAM_ID}/meetings/not-a-uuid")
        assert response.status_code == 422


# ============================================================
#  Контракт роутера (OpenAPI)
# ============================================================

class TestTeamsRouterContract:
    def test_openapi_paths_and_tags(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]

        expected = [
            "/teams/join",
            "/teams/{team_id}/members",
            "/teams/{team_id}/tasks",
            "/teams/{team_id}/tasks/{task_id}",
            "/teams/{team_id}/meetings",
            "/teams/{team_id}/meetings/{meeting_id}",
        ]
        for p in expected:
            assert p in paths, f"missing path {p}"
            for _, op in paths[p].items():
                assert op["tags"] == ["teams"]

    def test_methods_per_path(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]

        assert set(paths["/teams/join"]) == {"post"}
        assert set(paths["/teams/{team_id}/members"]) == {"get"}
        assert set(paths["/teams/{team_id}/tasks"]) == {"post", "get"}
        assert set(paths["/teams/{team_id}/tasks/{task_id}"]) == {"get", "patch", "delete"}
        assert set(paths["/teams/{team_id}/meetings"]) == {"post", "get"}
        assert set(paths["/teams/{team_id}/meetings/{meeting_id}"]) == {"get", "patch", "delete"}

    def test_join_uses_query_param(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/teams/join"]["post"]
        params = {p["name"]: p["in"] for p in op.get("parameters", [])}
        assert params.get("invite_code") == "query"

    def test_task_schema_required_fields(self, client):
        spec = client.get("/openapi.json").json()
        schema = spec["components"]["schemas"]["TaskCreate"]
        assert set(schema["required"]) >= {"title", "description", "assignee", "due_date"}
        # status имеет дефолт → не в required
        assert "status" not in schema.get("required", [])

    def test_meeting_schema_required_fields(self, client):
        spec = client.get("/openapi.json").json()
        schema = spec["components"]["schemas"]["MeetingCreate"]
        assert set(schema["required"]) >= {"starts_at", "ends_at", "related_team", "creator"}
        assert "max_members" not in schema.get("required", [])