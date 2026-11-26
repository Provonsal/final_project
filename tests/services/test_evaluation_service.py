from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import AuthorizationError, BusinessRuleError, WrongInputError
from app.models import RoleEnum

from app.services.evaluation_service import EvaluationService
SERVICE_MODULE = "app.services.evaluation_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), role=role, is_active=True)


def make_team(team_id=None):
    return SimpleNamespace(id=team_id or uuid4())


def make_task(team_id=None, task_id=None):
    return SimpleNamespace(id=task_id or uuid4(), team_id=team_id or uuid4())


def make_evaluation(task_id=None, evaluation_id=None, rate=3, rater_id=None):
    return SimpleNamespace(
        id=evaluation_id or uuid4(),
        task_id=task_id or uuid4(),
        rate=rate,
        rater=rater_id or uuid4(),
    )


def make_create_evaluation_schema(task_id=None, rate=3):
    """Заглушка CreateEvaluation с методом model_dump."""
    tid = task_id or uuid4()
    schema = SimpleNamespace(task_id=tid, rate=rate)
    schema.model_dump = lambda: {"task_id": tid, "rate": rate}
    return schema


def make_update_evaluation_schema(rate=None):
    """Заглушка UpdateEvaluation с методом model_dump(exclude_unset=True)."""
    schema = SimpleNamespace(rate=rate)
    def model_dump(exclude_unset=False):
        if exclude_unset:
            return {"rate": rate} if rate is not None else {}
        return {"rate": rate}
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
    """Подменяем классы репозиториев ВНУТРИ модуля сервиса."""
    with patch(f"{SERVICE_MODULE}.EvaluationRepo") as eval_cls, \
         patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls:

        eval_repo = eval_cls.return_value
        eval_repo.get_evaluation_for_task = AsyncMock()
        eval_repo.create = AsyncMock()
        eval_repo.update = AsyncMock()
        eval_repo.delete = AsyncMock()

        team_repo = team_cls.return_value
        team_repo.belongs_to_team = AsyncMock(return_value=True)

        yield SimpleNamespace(evaluation=eval_repo, team=team_repo)


@pytest.fixture
def service(session, repos):
    return EvaluationService(session)


# ==================== TestGetEvaluation ====================

class TestGetEvaluation:
    """Тестируем get_evaluation."""

    @pytest.mark.asyncio
    async def test_get_evaluation_success(self, service, repos):
        """Все проверки пройдены → возвращается переданная evaluation."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)

        result = await service.get_evaluation(user, team, task, evaluation)

        assert result is evaluation
        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)

    @pytest.mark.asyncio
    async def test_get_evaluation_manager_also_allowed(self, service, repos):
        """MANAGER тоже может получать оценки."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)

        result = await service.get_evaluation(user, team, task, evaluation)
        assert result is evaluation

    @pytest.mark.asyncio
    async def test_get_evaluation_guest_raises_authorization_error(self, service, repos):
        """GUEST не может получать оценки → AuthorizationError."""
        user = make_user(role=RoleEnum.GUEST)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)

        with pytest.raises(AuthorizationError) as exc:
            await service.get_evaluation(user, team, task, evaluation)

        assert exc.value.status_code == 403
        assert exc.value.error_code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_get_evaluation_user_not_in_team_raises_authorization_error(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_evaluation(user, team, task, evaluation)

    @pytest.mark.asyncio
    async def test_get_evaluation_task_not_in_team_raises_authorization_error(self, service, repos):
        """Задача не принадлежит команде → AuthorizationError (даже если пользователь в команде)."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=uuid4())  # другой team_id
        evaluation = make_evaluation(task_id=task.id)

        with pytest.raises(WrongInputError):
            await service.get_evaluation(user, team, task, evaluation)

    @pytest.mark.asyncio
    async def test_get_evaluation_not_in_task_raises_authorization_error(self, service, repos):
        """Оценка не принадлежит задаче → AuthorizationError."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=uuid4())  # другой task_id

        with pytest.raises(WrongInputError):
            await service.get_evaluation(user, team, task, evaluation)


# ==================== TestGetEvaluationsForTasks ====================

class TestGetEvaluationsForTasks:
    """Тестируем get_evaluations_for_tasks."""

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_success(self, service, repos):
        """Успех: возвращается словарь {task_id: evaluation}."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task1 = make_task(team_id=team.id)
        task2 = make_task(team_id=team.id)
        eval1 = make_evaluation(task_id=task1.id)
        eval2 = make_evaluation(task_id=task2.id)

        repos.evaluation.get_evaluation_for_task.side_effect = [eval1, eval2]

        result = await service.get_evaluations_for_tasks(user, team, [task1, task2])

        assert result == {task1.id: eval1, task2.id: eval2}
        assert repos.evaluation.get_evaluation_for_task.await_count == 2

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_member_role_required(self, service, repos):
        """Только MANAGER или MEMBER могут получать оценки."""
        user = make_user(role=RoleEnum.GUEST)
        team = make_team()

        with pytest.raises(AuthorizationError):
            await service.get_evaluations_for_tasks(user, team, [])

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_user_not_in_team(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_evaluations_for_tasks(user, team, [])

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_task_not_in_team(self, service, repos):
        """Задача не принадлежит команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=uuid4())

        with pytest.raises(AuthorizationError):
            await service.get_evaluations_for_tasks(user, team, [task])

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_missing_evaluation_returns_empty_dict(
        self, service, repos
    ):
        """Если у задачи нет оценки — она просто не попадает в словарь (роут поставит None)."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task_with_eval = make_task(team_id=team.id)
        task_without_eval = make_task(team_id=team.id)
        eval1 = make_evaluation(task_id=task_with_eval.id)

        # Первая задача имеет оценку, вторая — нет
        async def get_eval_side_effect(task_id):
            if task_id == task_with_eval.id:
                return eval1
            raise NoResultFound()

        repos.evaluation.get_evaluation_for_task.side_effect = get_eval_side_effect

        result = await service.get_evaluations_for_tasks(user, team, [task_with_eval, task_without_eval])

        # В словаре только задача с оценкой
        assert result == {task_with_eval.id: eval1}
        assert task_without_eval.id not in result

    @pytest.mark.asyncio
    async def test_get_evaluations_for_tasks_empty_list(self, service, repos):
        """Пустой список задач → пустой словарь."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()

        result = await service.get_evaluations_for_tasks(user, team, [])

        assert result == {}
        repos.evaluation.get_evaluation_for_task.assert_not_awaited()


# ==================== TestCreateEvaluation ====================

class TestCreateEvaluation:
    """Тестируем create_evaluation."""

    @pytest.mark.asyncio
    async def test_create_evaluation_success(self, service, repos, session):
        """Успешное создание оценки MANAGER'ом."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_evaluation_schema(task_id=task.id, rate=4)

        # Мокаем репо: оценка ещё не существует
        repos.evaluation.get_evaluation_for_task.side_effect = NoResultFound()

        # Мокаем TaskRate
        with patch(f"{SERVICE_MODULE}.TaskRate") as task_rate_cls:
            new_eval = make_evaluation(task_id=task.id, rate=4, rater_id=user.id)
            task_rate_cls.return_value = new_eval

            result = await service.create_evaluation(data, user, team, task)

        assert result is new_eval
        repos.evaluation.create.assert_awaited_once_with(new_eval)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_evaluation_already_exists_raises_business_rule_error(self, service, repos, session):
        """Попытка создать вторую оценку → BusinessRuleError (422)."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_evaluation_schema(task_id=task.id, rate=4)

        # Оценка уже существует
        existing_eval = make_evaluation(task_id=task.id)
        repos.evaluation.get_evaluation_for_task.return_value = existing_eval

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_evaluation(data, user, team, task)

        assert exc.value.status_code == 422
        assert "already exists" in exc.value.message
        repos.evaluation.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_evaluation_only_manager_allowed(self, service, repos, session):
        """Только MANAGER может создавать оценки, MEMBER не может."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_evaluation_schema(task_id=task.id, rate=4)

        with pytest.raises(AuthorizationError):
            await service.create_evaluation(data, user, team, task)

        repos.evaluation.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_evaluation_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_evaluation_schema(task_id=task.id, rate=4)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.create_evaluation(data, user, team, task)

        repos.evaluation.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_evaluation_task_not_in_team(self, service, repos, session):
        """Задача не принадлежит команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=uuid4())  # другой team_id
        data = make_create_evaluation_schema(task_id=task.id, rate=4)

        with pytest.raises(AuthorizationError):
            await service.create_evaluation(data, user, team, task)

        repos.evaluation.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_evaluation_passes_user_and_task_as_objects(self, service, repos):
        """TaskRate создаётся с user и task как объектами, а не ID."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_evaluation_schema(task_id=task.id, rate=4)
        repos.evaluation.get_evaluation_for_task.side_effect = NoResultFound()

        with patch(f"{SERVICE_MODULE}.TaskRate") as task_rate_cls:
            task_rate_cls.return_value = make_evaluation()
            await service.create_evaluation(data, user, team, task)

        call_kwargs = task_rate_cls.call_args.kwargs
        assert call_kwargs["user"] is user
        assert call_kwargs["task"] is task


# ==================== TestUpdate ====================

class TestUpdate:
    """Тестируем update."""

    @pytest.mark.asyncio
    async def test_update_success(self, service, repos, session):
        """Успешное обновление оценки MANAGER'ом."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id, rate=3)
        data = make_update_evaluation_schema(rate=5)

        updated_eval = make_evaluation(task_id=task.id, rate=5)
        repos.evaluation.update.return_value = updated_eval

        result = await service.update(data, user, team, task, evaluation)

        assert result is updated_eval
        repos.evaluation.update.assert_awaited_once_with(evaluation.id, {"rate": 5})
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_no_changes_skips_repo_call(self, service, repos, session):
        """Если изменений нет — репо не вызывается, коммита нет."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)
        data = make_update_evaluation_schema(rate=None)  # ничего не меняем

        result = await service.update(data, user, team, task, evaluation)

        assert result is evaluation
        repos.evaluation.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_only_manager_allowed(self, service, repos, session):
        """Только MANAGER может обновлять оценки."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)
        data = make_update_evaluation_schema(rate=5)

        with pytest.raises(AuthorizationError):
            await service.update(data, user, team, task, evaluation)

        repos.evaluation.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)
        data = make_update_evaluation_schema(rate=5)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.update(data, user, team, task, evaluation)

        repos.evaluation.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_task_not_in_team(self, service, repos, session):
        """Задача не принадлежит команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=uuid4())
        evaluation = make_evaluation(task_id=task.id)
        data = make_update_evaluation_schema(rate=5)

        with pytest.raises(AuthorizationError):
            await service.update(data, user, team, task, evaluation)

        repos.evaluation.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_evaluation_not_in_task(self, service, repos, session):
        """Оценка не принадлежит задаче → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=uuid4())  # другой task_id
        data = make_update_evaluation_schema(rate=5)

        with pytest.raises(AuthorizationError):
            await service.update(data, user, team, task, evaluation)

        repos.evaluation.update.assert_not_awaited()


# ==================== TestDelete ====================

class TestDelete:
    """Тестируем delete."""

    @pytest.mark.asyncio
    async def test_delete_success(self, service, repos, session):
        """Успешное удаление оценки MANAGER'ом."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)

        result = await service.delete(user, team, task, evaluation)

        assert result is True
        repos.evaluation.delete.assert_awaited_once_with(evaluation)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_only_manager_allowed(self, service, repos, session):
        """Только MANAGER может удалять оценки."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)

        with pytest.raises(AuthorizationError):
            await service.delete(user, team, task, evaluation)

        repos.evaluation.delete.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_user_not_in_team(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=task.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.delete(user, team, task, evaluation)

        repos.evaluation.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_task_not_in_team(self, service, repos, session):
        """Задача не принадлежит команде → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=uuid4())
        evaluation = make_evaluation(task_id=task.id)

        with pytest.raises(AuthorizationError):
            await service.delete(user, team, task, evaluation)

        repos.evaluation.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_evaluation_not_in_task(self, service, repos, session):
        """Оценка не принадлежит задаче → AuthorizationError."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        task = make_task(team_id=team.id)
        evaluation = make_evaluation(task_id=uuid4())

        with pytest.raises(AuthorizationError):
            await service.delete(user, team, task, evaluation)

        repos.evaluation.delete.assert_not_awaited()