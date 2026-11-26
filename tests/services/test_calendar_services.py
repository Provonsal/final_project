from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exc.exceptions import AuthorizationError, WrongInputError
from app.models import RoleEnum

from app.services.calendar_service import CalendarService
SERVICE_MODULE = "app.services.calendar_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER):
    return SimpleNamespace(id=uuid4(), role=role, is_active=True)


def make_team():
    return SimpleNamespace(id=uuid4())


def make_task(team_id=None):
    return SimpleNamespace(id=uuid4(), team_id=team_id or uuid4())


def make_meeting(team_id=None):
    return SimpleNamespace(
        id=uuid4(),
        related_team=team_id or uuid4(),
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
        ends_at=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
    )


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    s = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.fixture
def repos():
    """Подменяем классы репозиториев ВНУТРИ модуля сервиса."""
    with patch(f"{SERVICE_MODULE}.MeetingRepo") as meeting_cls, \
         patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls:

        meeting_repo = meeting_cls.return_value
        meeting_repo.get_all_meetings_from_to = AsyncMock(return_value=[])

        team_repo = team_cls.return_value
        team_repo.belongs_to_team = AsyncMock(return_value=True)

        yield SimpleNamespace(meeting=meeting_repo, team=team_repo)


@pytest.fixture
def service(session, repos):
    return CalendarService(session)


# ==================== TestRequiresAccessDecorator ====================

class TestRequiresAccessDecorator:
    """Тестируем декоратор @requires_access."""

    @pytest.mark.asyncio
    async def test_decorator_calls_ensure_access(self, service, repos):
        """Декоратор вызывает _ensure_access с правильными аргументами."""
        user = make_user()
        team = make_team()

        # Мокаем _ensure_access, чтобы проверить вызов
        service._ensure_access = AsyncMock()

        await service.get_meetings(team=team, user=user)

        service._ensure_access.assert_awaited_once_with(user, team, None)

    @pytest.mark.asyncio
    async def test_decorator_passes_task_when_present(self, service, repos):
        """Если метод принимает task, он передаётся в _ensure_access."""
        # Создадим тестовый метод с task в сигнатуре
        from app.services.calendar_service import requires_access

        @requires_access
        async def fake_method(self, team, user, task):
            return "ok"

        # Привяжем к сервису
        service._ensure_access = AsyncMock()
        bound_method = fake_method.__get__(service, type(service))

        user = make_user()
        team = make_team()
        task = make_task()

        result = await bound_method(team=team, user=user, task=task)

        assert result == "ok"
        service._ensure_access.assert_awaited_once_with(user, team, task)

    @pytest.mark.asyncio
    async def test_decorator_raises_type_error_if_no_user(self, service, repos):
        """Если у метода нет параметра user — TypeError при определении."""
        from app.services.calendar_service import requires_access

        with pytest.raises(TypeError) as exc:
            @requires_access
            async def bad_method(self, team):
                pass

        assert "user" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_decorator_raises_type_error_if_no_team(self, service, repos):
        """Если у метода нет параметра team — TypeError при определении."""
        from app.services.calendar_service import requires_access

        with pytest.raises(TypeError) as exc:
            @requires_access
            async def bad_method(self, user):
                pass

        assert "team" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_decorator_passes_optional_kwargs_unchanged(self, service, repos):
        """Опциональные параметры (date_from, date_until) проходят сквозь декоратор."""
        user = make_user()
        team = make_team()
        service._ensure_access = AsyncMock()

        date_from = datetime.now(timezone.utc)
        date_until = date_from + timedelta(days=7)

        await service.get_meetings(
            team=team, user=user,
            date_from=date_from, date_until=date_until
        )

        # _ensure_access вызывается только с user/team/task
        service._ensure_access.assert_awaited_once_with(user, team, None)


# ==================== TestEnsureAccess ====================

class TestEnsureAccess:
    """Тестируем приватный метод _ensure_access."""

    @pytest.mark.asyncio
    async def test_user_in_team_access_granted(self, service, repos):
        """Пользователь в команде → доступ разрешён."""
        user = make_user()
        team = make_team()
        repos.team.belongs_to_team.return_value = True

        # Не должно выбрасывать исключений
        await service._ensure_access(user, team)

        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)

    @pytest.mark.asyncio
    async def test_user_not_in_team_raises_authorization_error(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user()
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError) as exc:
            await service._ensure_access(user, team)

        assert exc.value.status_code == 403
        assert exc.value.error_code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_task_with_matching_team_id_ok(self, service, repos):
        """Task передан и team_id совпадает → доступ разрешён."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        repos.team.belongs_to_team.return_value = True

        await service._ensure_access(user, team, task)

    @pytest.mark.asyncio
    async def test_task_with_wrong_team_id_raises_authorization_error(self, service, repos):
        """Task передан, но team_id не совпадает → AuthorizationError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())  # другой team_id
        repos.team.belongs_to_team.return_value = True

        with pytest.raises(WrongInputError):
            await service._ensure_access(user, team, task)

    @pytest.mark.asyncio
    async def test_task_none_skips_task_check(self, service, repos):
        """Task=None → проверка только команды, без task.team_id."""
        user = make_user()
        team = make_team()
        repos.team.belongs_to_team.return_value = True

        await service._ensure_access(user, team, None)

        repos.team.belongs_to_team.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_role_is_not_checked_current_behavior(self, service, repos):
        """
        ТЕКУЩЕЕ ПОВЕДЕНИЕ (баг/недочёт):
        В докстринге заявлена проверка роли MANAGER/MEMBER, но в коде её нет.
        GUEST тоже пройдёт проверку, если он в команде.
        """
        guest = make_user(role=RoleEnum.GUEST)
        team = make_team()
        repos.team.belongs_to_team.return_value = True

        # Не должно выбрасывать — роли не проверяются
        await service._ensure_access(guest, team)


# ==================== TestGetMeetings ====================

class TestGetMeetings:
    """Тестируем публичный метод get_meetings."""

    @pytest.mark.asyncio
    async def test_get_meetings_delegates_to_repo(self, service, repos):
        """get_meetings делегирует вызов meeting_repo.get_all_meetings_from_to."""
        user = make_user()
        team = make_team()
        date_from = datetime.now(timezone.utc)
        date_until = date_from + timedelta(days=7)

        expected_meetings = [make_meeting(team.id), make_meeting(team.id)]
        repos.meeting.get_all_meetings_from_to.return_value = expected_meetings

        result = await service.get_meetings(team, user, date_from, date_until)

        assert result == expected_meetings
        repos.meeting.get_all_meetings_from_to.assert_awaited_once_with(
            team.id, date_from, date_until
        )

    @pytest.mark.asyncio
    async def test_get_meetings_date_from_none_uses_now(self, service, repos):
        """date_from=None → используется datetime.now(UTC)."""
        user = make_user()
        team = make_team()

        before = datetime.now(timezone.utc)
        await service.get_meetings(team, user, date_from=None, date_until=None)
        after = datetime.now(timezone.utc)

        # Проверяем, что в репо передана дата в разумном диапазоне
        call_args = repos.meeting.get_all_meetings_from_to.await_args.args
        passed_date_from = call_args[1]

        assert before <= passed_date_from <= after
        assert call_args[2] is None  # date_until=None

    @pytest.mark.asyncio
    async def test_get_meetings_date_until_none_passes_none(self, service, repos):
        """date_until=None → передаётся None в репо (без верхней границы)."""
        user = make_user()
        team = make_team()
        date_from = datetime.now(timezone.utc)

        await service.get_meetings(team, user, date_from, None)

        call_args = repos.meeting.get_all_meetings_from_to.await_args.args
        assert call_args[2] is None

    @pytest.mark.asyncio
    async def test_get_meetings_date_from_greater_than_date_until(self, service, repos):
        """date_from > date_until → WrongInputError."""
        user = make_user()
        team = make_team()
        date_from = datetime.now(timezone.utc) + timedelta(days=10)
        date_until = datetime.now(timezone.utc)

        with pytest.raises(WrongInputError) as exc:
            await service.get_meetings(team, user, date_from, date_until)

        assert exc.value.status_code == 400
        repos.meeting.get_all_meetings_from_to.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_meetings_date_from_equals_date_until_bug(self, service, repos):
        """
        БАГ: date_from == date_until тоже не выбрасывает.
        Условие `date_from >= date_until` должно ловить и равенство.
        """
        user = make_user()
        team = make_team()
        same_date = datetime.now(timezone.utc) + timedelta(days=5)

        
        with pytest.raises(WrongInputError) as exc:
            await service.get_meetings(team, user, same_date, same_date)

        assert exc.value.status_code == 400
        repos.meeting.get_all_meetings_from_to.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_meetings_access_denied_propagates(self, service, repos):
        """Если пользователь не в команде → AuthorizationError всплывает."""
        user = make_user()
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_meetings(team, user, datetime.now(timezone.utc), None)

        # Репозиторий встреч НЕ должен вызываться
        repos.meeting.get_all_meetings_from_to.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_meetings_empty_result(self, service, repos):
        """Если встреч нет — возвращается пустой список."""
        user = make_user()
        team = make_team()
        repos.meeting.get_all_meetings_from_to.return_value = []

        result = await service.get_meetings(
            team, user,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=7)
        )

        assert result == []


# ==================== TestServiceInit ====================

class TestServiceInit:
    """Тестируем конструктор."""

    def test_init_creates_repos(self, session, repos):
        """Конструктор создаёт MeetingRepo и TeamRepo."""
        service = CalendarService(session)

        assert hasattr(service, "meeting_repo")
        assert hasattr(service, "team_repo")
        assert service.session is session