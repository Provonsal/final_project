
"""
Тесты для роутера /calendar.

Роутер максимально тонкий — вся логика в CalendarService/MeetingRepo.
Тесты покрывают:
- валидацию query-параметров,
- прокидывание team_id / date_from / date_until в сервис,
- сериализацию ответа,
- контракт OpenAPI.

Интеграционный тест репозитория (фильтр starts_at >= date_from AND ends_at <= date_until)
здесь не пишется — нужен реальный AsyncSession и БД.
"""
import uuid
from datetime import datetime, timezone

import pytest


TEAM_ID    = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DATE_FROM  = "2030-01-01T00:00:00Z"
DATE_UNTIL = "2030-02-01T00:00:00Z"


def _expected_dt(s: str) -> datetime:
    """Z → +00:00, чтобы fromisoformat работал и до Python 3.11."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ============================================================
#  GET /calendar/{team_id}
# ============================================================

class TestCalendarRoot:
    def test_success_returns_meetings_as_is(self, client, mock_calendar_service):
        mock_calendar_service.get_meetings.return_value = [
            {"id": "1", "max_members": 5},
            {"id": "2", "max_members": 10},
        ]

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 200, response.json()
        assert response.json() == [
            {"id": "1", "max_members": 5},
            {"id": "2", "max_members": 10},
        ]

    def test_service_called_with_parsed_datetimes(self, client, mock_calendar_service):
        mock_calendar_service.get_meetings.return_value = []

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 200, response.json()

        args, _ = mock_calendar_service.get_meetings.await_args
        team_id_arg, date_from_arg, date_until_arg = args

        assert team_id_arg == TEAM_ID
        assert date_from_arg == _expected_dt(DATE_FROM)
        assert date_until_arg == _expected_dt(DATE_UNTIL)

    def test_empty_list_is_ok(self, client, mock_calendar_service):
        mock_calendar_service.get_meetings.return_value = []

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 200
        assert response.json() == []

    # --------- валидация ---------

    def test_missing_date_from_returns_422(self, client, mock_calendar_service):
        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_until": DATE_UNTIL},
        )

        assert response.status_code == 422
        mock_calendar_service.get_meetings.assert_not_awaited()

    def test_missing_date_until_returns_200_and_passes_none(
    self, client, mock_calendar_service,
    ):
        """
        date_until стал необязательным (`= None` в роутере).
        Без него запрос проходит, а в сервис уходит None — дальше
        MeetingRepo сам подставляет «now + 30 days».
        """
        mock_calendar_service.get_meetings.return_value = []

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM},
        )

        assert response.status_code == 200, response.json()
        assert response.json() == []

        args, _ = mock_calendar_service.get_meetings.await_args
        team_id_arg, date_from_arg, date_until_arg = args

        assert team_id_arg == TEAM_ID
        assert date_from_arg == _expected_dt(DATE_FROM)
        assert date_until_arg is None       # ← ключевая проверка

    @pytest.mark.parametrize(
        "params",
        [
            {"date_from": "not-a-date",  "date_until": DATE_UNTIL},
            {"date_from": DATE_FROM,     "date_until": "not-a-date"},
            {"date_from": "",            "date_until": DATE_UNTIL},
            {"date_from": DATE_FROM,     "date_until": ""},
        ],
    )
    def test_invalid_datetime_format_returns_422(
        self, client, mock_calendar_service, params,
    ):
        response = client.get(f"/calendar/{TEAM_ID}", params=params)

        assert response.status_code == 422
        mock_calendar_service.get_meetings.assert_not_awaited()

    def test_invalid_team_id_returns_422(self, client, mock_calendar_service):
        response = client.get(
            "/calendar/not-a-uuid",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 422
        mock_calendar_service.get_meetings.assert_not_awaited()

    # --------- форматы дат ---------

    def test_naive_datetime_is_accepted_as_naive(self, client, mock_calendar_service):
        """Без Z/+00:00 → naive datetime, сервис получает как есть."""
        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={
                "date_from": "2030-01-01T00:00:00",
                "date_until": "2030-02-01T00:00:00",
            },
        )

        assert response.status_code == 200
        args, _ = mock_calendar_service.get_meetings.await_args
        _, date_from_arg, date_until_arg = args
        assert date_from_arg.tzinfo is None
        assert date_until_arg.tzinfo is None

    def test_date_only_passes_midnight(self, client, mock_calendar_service):
        """`date_from=2030-01-01` (без времени) → полночь UTC/naive."""
        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": "2030-01-01", "date_until": "2030-02-01"},
        )

        assert response.status_code == 200
        args, _ = mock_calendar_service.get_meetings.await_args
        _, date_from_arg, _ = args
        assert date_from_arg.year == 2030
        assert date_from_arg.month == 1
        assert date_from_arg.day == 1
        assert date_from_arg.hour == 0
        assert date_from_arg.minute == 0

    def test_plus_offset_accepted(self, client, mock_calendar_service):
        """`+03:00` — валидный ISO, Pydantic сохранит offset."""
        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={
                "date_from": "2030-01-01T00:00:00+03:00",
                "date_until": DATE_UNTIL,
            },
        )

        assert response.status_code == 200
        args, _ = mock_calendar_service.get_meetings.await_args
        _, date_from_arg, _ = args
        assert date_from_arg.utcoffset().total_seconds() == 3 * 3600

    # --------- проброс ответа сервиса ---------

    def test_service_exception_propagates(self, client, mock_calendar_service):
        """Если сервис/репозиторий бросит HTTPException — роутер не глотает."""
        from fastapi import HTTPException

        mock_calendar_service.get_meetings.side_effect = HTTPException(
            status_code=404, detail="Team not found",
        )

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Team not found"}

    # ⚠️ Роутер не зависит от current_user — авторизации нет. Фиксируем.
    def test_requires_authentication(self, client, app, mock_calendar_service):
        """
        Роутер теперь зависит от CurrentUserDep. Убираем override — и запрос
        без Bearer-токена должен упасть с 401 (OAuth2PasswordBearer).
        """
        from app.dependencies import get_current_user

        app.dependency_overrides.pop(get_current_user, None)

        response = client.get(
            f"/calendar/{TEAM_ID}",
            params={"date_from": DATE_FROM, "date_until": DATE_UNTIL},
        )

        assert response.status_code == 401
        mock_calendar_service.get_meetings.assert_not_awaited()


# ============================================================
#  Контракт роутера (OpenAPI)
# ============================================================

class TestCalendarContract:
    def test_openapi_path_and_tag(self, client):
        spec = client.get("/openapi.json").json()

        assert "/calendar/{team_id}" in spec["paths"]
        op = spec["paths"]["/calendar/{team_id}"]["get"]
        assert op["tags"] == ["calendar"]

    def test_query_params_declared_and_required(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/calendar/{team_id}"]["get"]
        params = {p["name"]: p for p in op.get("parameters", [])}

        assert params["date_from"]["in"] == "query"
        assert params["date_until"]["in"] == "query"

        # ⚠️ фиксируем текущий контракт: обе даты обязательны.
        # Когда добавите `date_until: datetime | None = None` —
        # тест покраснеет, это сигнал обновить контракт.
        assert params["date_from"].get("required") is True
        assert params["date_until"].get("required") is False
        assert params["date_until"].get("schema", {}).get("anyOf") is not None or \
            params["date_until"].get("schema", {}).get("nullable") is True

    def test_team_id_is_path_param(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/calendar/{team_id}"]["get"]
        params = {p["name"]: p for p in op.get("parameters", [])}
        assert params["team_id"]["in"] == "path"

    def test_security_declared_in_openapi(self, client):
        """С CurrentUserDep в OpenAPI появляется security-требование."""
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/calendar/{team_id}"]["get"]

        assert "security" in op
        assert op["security"] != []

    def test_security_scheme_present(self, client):
        spec = client.get("/openapi.json").json()
        op = spec["paths"]["/calendar/{team_id}"]["get"]

        schemes = set(spec["components"]["securitySchemes"].keys())
        used = {name for req in op["security"] for name in req}
        assert used <= schemes