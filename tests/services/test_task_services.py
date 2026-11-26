from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exc.exceptions import AuthorizationError, BusinessRuleError, WrongInputError
from app.models import RateEnum, RoleEnum, TaskStatusEnum

from app.services.task_service import TaskService
SERVICE_MODULE = "app.services.task_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), role=role, is_active=True)


def make_team(team_id=None, max_per_team=10):
    return SimpleNamespace(id=team_id or uuid4(), max_per_team=max_per_team)


def make_task(team_id=None, task_id=None, assignee_id=None, 
              status=TaskStatusEnum.OPEN, due_date=None, title=None, description=None):
    return SimpleNamespace(
        id=task_id or uuid4(),
        team_id=team_id or uuid4(),
        assignee=assignee_id or uuid4(),
        status=status,
        due_date=due_date or datetime.now(timezone.utc) + timedelta(days=7),
        title=title or "Test Task",
        description=description or "Test Description",
    )


def make_create_task_schema(title="New Task", description="Desc", 
                            assignee_id=None, due_date=None, status=TaskStatusEnum.OPEN):
    schema = SimpleNamespace(
        title=title,
        description=description,
        assignee=assignee_id or uuid4(),
        due_date=due_date or datetime.now(timezone.utc) + timedelta(days=7),
        status=status,
    )
    schema.model_dump = lambda: {
        "title": title,
        "description": description,
        "assignee": assignee_id or uuid4(),
        "due_date": due_date or datetime.now(timezone.utc) + timedelta(days=7),
        "status": status,
    }
    return schema


def make_update_task_schema(title=None, description=None, due_date=None, status=None):
    schema = SimpleNamespace(title=title, description=description, due_date=due_date, status=status)
    def model_dump(exclude_unset=False):
        result = {}
        if exclude_unset:
            if title is not None: result["title"] = title
            if description is not None: result["description"] = description
            if due_date is not None: result["due_date"] = due_date
            if status is not None: result["status"] = status
            return result
        return {"title": title, "description": description, "due_date": due_date, "status": status}
    schema.model_dump = model_dump
    return schema


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    s = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.fixture
def repos():
    with patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls, \
         patch(f"{SERVICE_MODULE}.TaskRepo") as task_cls, \
         patch(f"{SERVICE_MODULE}.UserRepo") as user_cls, \
         patch(f"{SERVICE_MODULE}.EvaluationRepo") as eval_cls:

        team_repo = team_cls.return_value
        team_repo.belongs_to_team = AsyncMock(return_value=True)

        task_repo = task_cls.return_value
        task_repo.create = AsyncMock()
        task_repo.update = AsyncMock()
        task_repo.delete = AsyncMock()
        task_repo.get_all_tasks = AsyncMock(return_value=[])
        task_repo.get_all_tasks_for_user = AsyncMock(return_value=[])
        task_repo.start_task = AsyncMock()
        task_repo.end_task = AsyncMock()
        task_repo.get_all_tasks_from_to = AsyncMock(return_value=[])

        user_repo = user_cls.return_value
        user_repo.get_by_id = AsyncMock()

        eval_repo = eval_cls.return_value
        eval_repo.create = AsyncMock()

        yield SimpleNamespace(
            team=team_repo,
            task=task_repo,
            user=user_repo,
            evaluation=eval_repo,
        )


@pytest.fixture
def service(session, repos):
    return TaskService(session)


# ==================== TestCreateTask ====================

class TestCreateTask:

    @pytest.mark.asyncio
    async def test_create_task_success(self, service, repos, session):
        """Успешное создание задачи MANAGER'ом."""
        manager = make_user(role=RoleEnum.MANAGER)
        assignee = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        data = make_create_task_schema(assignee_id=assignee.id)

        repos.user.get_by_id.return_value = assignee

        with patch(f"{SERVICE_MODULE}.Task") as task_cls, \
             patch(f"{SERVICE_MODULE}.TaskRate") as rate_cls:
            new_task = make_task(team_id=team.id, assignee_id=assignee.id)
            task_cls.return_value = new_task
            rate_cls.return_value = SimpleNamespace()

            result = await service.create_task(data, team, manager)

        assert result is new_task
        repos.task.create.assert_awaited_once_with(new_task)
        repos.evaluation.create.assert_awaited_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_task_creates_unrated_evaluation(self, service, repos):
        """При создании задачи автоматически создаётся оценка UNRATED."""
        manager = make_user(role=RoleEnum.MANAGER)
        assignee = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        data = make_create_task_schema(assignee_id=assignee.id)

        repos.user.get_by_id.return_value = assignee

        with patch(f"{SERVICE_MODULE}.Task") as task_cls, \
             patch(f"{SERVICE_MODULE}.TaskRate") as rate_cls:
            task_cls.return_value = make_task()
            rate_cls.return_value = SimpleNamespace()

            await service.create_task(data, team, manager)

        # Проверяем, что TaskRate создан с rate=UNRATED
        call_kwargs = rate_cls.call_args.kwargs
        assert call_kwargs["rate"] == RateEnum.UNRATED
        assert call_kwargs["user"] is assignee

    @pytest.mark.asyncio
    async def test_create_task_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_task_schema()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.create_task(data, team, manager)

        repos.task.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_task_assignee_not_in_team(self, service, repos, session):
        """Assignee не в команде → AuthorizationError."""
        manager = make_user(role=RoleEnum.MANAGER)
        assignee = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        data = make_create_task_schema(assignee_id=assignee.id)

        # Первый вызов belongs_to_team для manager → True
        # Второй вызов для assignee → False
        repos.team.belongs_to_team.side_effect = [True, False]

        with pytest.raises(AuthorizationError) as exc:
            await service.create_task(data, team, manager)

        assert "Assignee" in exc.value.message
        repos.task.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_task_not_manager(self, service, repos, session):
        """Только MANAGER может создавать задачи."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        data = make_create_task_schema()

        with pytest.raises(AuthorizationError):
            await service.create_task(data, team, member)

        repos.task.create.assert_not_awaited()


# ==================== TestGetAllTasks ====================

class TestGetAllTasks:

    @pytest.mark.asyncio
    async def test_get_all_tasks_manager_sees_all(self, service, repos):
        """MANAGER видит все задачи команды."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        expected_tasks = [make_task(), make_task()]
        repos.task.get_all_tasks.return_value = expected_tasks

        result = await service.get_all_tasks(team, manager)

        assert result == expected_tasks
        repos.task.get_all_tasks.assert_awaited_once_with(team.id)
        repos.task.get_all_tasks_for_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_all_tasks_member_sees_own(self, service, repos):
        """MEMBER видит только свои задачи."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        expected_tasks = [make_task(assignee_id=member.id)]
        repos.task.get_all_tasks_for_user.return_value = expected_tasks

        result = await service.get_all_tasks(team, member)

        assert result == expected_tasks
        repos.task.get_all_tasks_for_user.assert_awaited_once_with(team.id, member.id)
        repos.task.get_all_tasks.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_all_tasks_user_not_in_team(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_all_tasks(team, member)


# ==================== TestGetTask ====================

class TestGetTask:

    @pytest.mark.asyncio
    async def test_get_task_success_as_assignee(self, service, repos):
        """Assignee может получить задачу."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=member.id)

        result = await service.get_task(task, team, member)

        assert result is task

    @pytest.mark.asyncio
    async def test_get_task_success_as_manager(self, service, repos):
        """MANAGER может получить любую задачу."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=uuid4())

        result = await service.get_task(task, team, manager)

        assert result is task

    @pytest.mark.asyncio
    async def test_get_task_user_not_in_team(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_task(task, team, member)

    @pytest.mark.asyncio
    async def test_get_task_not_in_team_raises_wrong_input(self, service, repos):
        """Задача не принадлежит команде → WrongInputError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=uuid4())  # другой team

        with pytest.raises(WrongInputError) as exc:
            await service.get_task(task, team, member)

        assert "does not belong" in exc.value.message

    @pytest.mark.asyncio
    async def test_get_task_not_assignee_and_not_manager(self, service, repos):
        """Пользователь не assignee и не MANAGER → AuthorizationError."""
        other_member = make_user(role=RoleEnum.MEMBER, user_id=uuid4())
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=uuid4())  # другой assignee

        with pytest.raises(AuthorizationError):
            await service.get_task(task, team, other_member)


# ==================== TestUpdateTask ====================

class TestUpdateTask:

    @pytest.mark.asyncio
    async def test_update_task_success(self, service, repos, session):
        """Успешное обновление задачи MANAGER'ом."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_update_task_schema(title="Updated Title")
        updated_task = make_task(task_id=task.id, title="Updated Title")
        repos.task.update.return_value = updated_task

        result = await service.update_task(data, task, manager, team)

        assert result is updated_task
        repos.task.update.assert_awaited_once_with(task.id, {"title": "Updated Title"})
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_task_no_changes_skips_repo(self, service, repos, session):
        """Если изменений нет — репо не вызывается, коммита нет."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_update_task_schema()  # все None

        result = await service.update_task(data, task, manager, team)

        assert result is task
        repos.task.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_task_not_manager(self, service, repos, session):
        """Только MANAGER может обновлять задачи."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=member.id)
        data = make_update_task_schema(title="Updated")

        with pytest.raises(AuthorizationError):
            await service.update_task(data, task, member, team)

        repos.task.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_task_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_update_task_schema(title="Updated")
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.update_task(data, task, manager, team)

    @pytest.mark.asyncio
    async def test_update_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=uuid4())
        data = make_update_task_schema(title="Updated")

        with pytest.raises(WrongInputError):
            await service.update_task(data, task, manager, team)


# ==================== TestDeleteTask ====================

class TestDeleteTask:

    @pytest.mark.asyncio
    async def test_delete_task_success(self, service, repos, session):
        """Успешное удаление задачи MANAGER'ом."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)

        result = await service.delete_task(task, manager, team)

        assert result is True
        repos.task.delete.assert_awaited_once_with(task)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_task_not_manager(self, service, repos, session):
        """Только MANAGER может удалять задачи."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=member.id)

        with pytest.raises(AuthorizationError):
            await service.delete_task(task, member, team)

        repos.task.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_task_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.delete_task(task, manager, team)

    @pytest.mark.asyncio
    async def test_delete_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=uuid4())

        with pytest.raises(WrongInputError):
            await service.delete_task(task, manager, team)


# ==================== TestStartTask ====================

class TestStartTask:

    @pytest.mark.asyncio
    async def test_start_task_success(self, service, repos, session):
        """Успешное начало выполнения задачи MEMBER'ом."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=member.id, status=TaskStatusEnum.OPEN)
        started_task = make_task(task_id=task.id, status=TaskStatusEnum.IN_PROGRESS)
        repos.task.start_task.return_value = started_task

        result = await service.start_task(team, member, task)

        assert result is started_task
        repos.task.start_task.assert_awaited_once_with(task.id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_task_not_member(self, service, repos, session):
        """Только MEMBER может начинать задачу (MANAGER не может!)."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.OPEN)

        with pytest.raises(AuthorizationError):
            await service.start_task(team, manager, task)

        repos.task.start_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_start_task_not_open_raises_business_rule_error(self, service, repos, session):
        """Нельзя начать задачу, если она не OPEN."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.IN_PROGRESS)

        with pytest.raises(BusinessRuleError) as exc:
            await service.start_task(team, member, task)

        assert "not ready" in exc.value.message.lower() or "already started" in exc.value.message.lower()
        repos.task.start_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_start_task_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.OPEN)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.start_task(team, member, task)

    @pytest.mark.asyncio
    async def test_start_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=uuid4(), status=TaskStatusEnum.OPEN)

        with pytest.raises(WrongInputError):
            await service.start_task(team, member, task)


# ==================== TestEndTask ====================

class TestEndTask:

    @pytest.mark.asyncio
    async def test_end_task_success(self, service, repos, session):
        """Успешное завершение задачи MEMBER'ом."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, assignee_id=member.id, status=TaskStatusEnum.IN_PROGRESS)
        ended_task = make_task(task_id=task.id, status=TaskStatusEnum.DONE)
        repos.task.end_task.return_value = ended_task

        result = await service.end_task(team, member, task)

        assert result is ended_task
        repos.task.end_task.assert_awaited_once_with(task.id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_end_task_not_member(self, service, repos, session):
        """Только MEMBER может завершать задачу."""
        manager = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.IN_PROGRESS)

        with pytest.raises(AuthorizationError):
            await service.end_task(team, manager, task)

        repos.task.end_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_end_task_not_in_progress_raises_business_rule_error(self, service, repos, session):
        """Нельзя завершить задачу, если она не IN_PROGRESS."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.OPEN)

        with pytest.raises(BusinessRuleError) as exc:
            await service.end_task(team, member, task)

        assert "not in progress" in exc.value.message.lower()
        repos.task.end_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_end_task_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id, status=TaskStatusEnum.IN_PROGRESS)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.end_task(team, member, task)

    @pytest.mark.asyncio
    async def test_end_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=uuid4(), status=TaskStatusEnum.IN_PROGRESS)

        with pytest.raises(WrongInputError):
            await service.end_task(team, member, task)


# ==================== TestGetTasks ====================

class TestGetTasks:

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, service, repos):
        """Успешное получение задач для календаря."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        date_from = datetime.now(timezone.utc)
        date_until = date_from + timedelta(days=7)
        expected_tasks = [make_task(), make_task()]
        repos.task.get_all_tasks_from_to.return_value = expected_tasks

        result = await service.get_tasks(member, team, date_from, date_until)

        assert result == expected_tasks
        repos.task.get_all_tasks_from_to.assert_awaited_once_with(
            member.id, date_from, date_until
        )

    @pytest.mark.asyncio
    async def test_get_tasks_date_from_none_uses_now(self, service, repos):
        """date_from=None → используется datetime.now(UTC)."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()

        before = datetime.now(timezone.utc)
        await service.get_tasks(member, team, date_from=None, date_until=None)
        after = datetime.now(timezone.utc)

        call_args = repos.task.get_all_tasks_from_to.await_args.args
        passed_date_from = call_args[1]

        assert before <= passed_date_from <= after
        assert call_args[2] is None

    @pytest.mark.asyncio
    async def test_get_tasks_date_from_greater_than_date_until(self, service, repos):
        """date_from > date_until → WrongInputError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        date_from = datetime.now(timezone.utc) + timedelta(days=10)
        date_until = datetime.now(timezone.utc)

        with pytest.raises(WrongInputError) as exc:
            await service.get_tasks(member, team, date_from, date_until)

        assert "date_from" in exc.value.message.lower()
        repos.task.get_all_tasks_from_to.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_tasks_user_not_in_team(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_tasks(member, team, datetime.now(timezone.utc), None)

    @pytest.mark.asyncio
    async def test_get_tasks_guest_role_raises_authorization_error(self, service, repos):
        """GUEST не может получать задачи для календаря."""
        guest = make_user(role=RoleEnum.GUEST)
        team = make_team()

        with pytest.raises(AuthorizationError):
            await service.get_tasks(guest, team, datetime.now(timezone.utc), None)