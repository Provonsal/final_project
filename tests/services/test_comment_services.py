from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exc.exceptions import AuthorizationError, WrongInputError
from app.models import RoleEnum

from app.services.comment_service import CommentService
SERVICE_MODULE = "app.services.comment_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), role=role, is_active=True)


def make_team(team_id=None):
    return SimpleNamespace(id=team_id or uuid4())


def make_task(team_id=None, task_id=None):
    return SimpleNamespace(id=task_id or uuid4(), team_id=team_id or uuid4())


def make_comment(task_id=None, author_id=None, comment_id=None, text="Original text"):
    return SimpleNamespace(
        id=comment_id or uuid4(),
        task_id=task_id or uuid4(),
        author=author_id or uuid4(),
        text=text,
    )


def make_create_comment_schema(text="New comment"):
    """Заглушка CreateComment с методом model_dump."""
    schema = SimpleNamespace(text=text)
    schema.model_dump = lambda: {"text": text}
    return schema


def make_update_comment_schema(text=None):
    """Заглушка UpdateComment с методом model_dump(exclude_unset=True)."""
    schema = SimpleNamespace(text=text)
    def model_dump(exclude_unset=False):
        if exclude_unset:
            return {"text": text} if text is not None else {}
        return {"text": text}
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
    with patch(f"{SERVICE_MODULE}.CommentRepo") as comment_cls, \
         patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls:

        comment_repo = comment_cls.return_value
        comment_repo.get_comments_by_task = AsyncMock(return_value=[])
        comment_repo.create = AsyncMock()
        comment_repo.update = AsyncMock()
        comment_repo.delete = AsyncMock()

        team_repo = team_cls.return_value
        team_repo.belongs_to_team = AsyncMock(return_value=True)

        yield SimpleNamespace(comment=comment_repo, team=team_repo)


@pytest.fixture
def service(session, repos):
    return CommentService(session)


# ==================== TestGetComments ====================

class TestGetComments:
    """Тестируем get_comments."""

    @pytest.mark.asyncio
    async def test_get_comments_success(self, service, repos):
        """Пользователь в команде и задача принадлежит команде → успех."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        expected_comments = [make_comment(task.id), make_comment(task.id)]
        repos.comment.get_comments_by_task.return_value = expected_comments

        result = await service.get_comments(task, user, team)

        assert result == expected_comments
        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)
        repos.comment.get_comments_by_task.assert_awaited_once_with(task.id)

    @pytest.mark.asyncio
    async def test_get_comments_user_not_in_team_raises_authorization_error(self, service, repos):
        """Пользователь не в команде → AuthorizationError (403)."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError) as exc:
            await service.get_comments(task, user, team)

        assert exc.value.status_code == 403
        assert exc.value.error_code == "FORBIDDEN"
        repos.comment.get_comments_by_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_comments_task_not_in_team_raises_wrong_input(self, service, repos):
        """Задача не принадлежит команде → WrongInputError (400)."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())  # другой team_id
        repos.team.belongs_to_team.return_value = True

        with pytest.raises(WrongInputError) as exc:
            await service.get_comments(task, user, team)

        assert exc.value.status_code == 400
        assert "does not belong" in exc.value.message
        repos.comment.get_comments_by_task.assert_not_awaited()


# ==================== TestGetComment ====================

class TestGetComment:
    """Тестируем get_comment."""

    @pytest.mark.asyncio
    async def test_get_comment_success(self, service, repos):
        """Все проверки пройдены → возвращается переданный comment."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id)

        result = await service.get_comment(comment, task, user, team)

        assert result is comment

    @pytest.mark.asyncio
    async def test_get_comment_user_not_in_team_raises_authorization_error(self, service, repos):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_comment(comment, task, user, team)

    @pytest.mark.asyncio
    async def test_get_comment_task_not_in_team_raises_wrong_input(self, service, repos):
        """Задача не принадлежит команде → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())
        comment = make_comment(task_id=task.id)

        with pytest.raises(WrongInputError):
            await service.get_comment(comment, task, user, team)

    @pytest.mark.asyncio
    async def test_get_comment_not_in_task_raises_wrong_input(self, service, repos):
        """Комментарий не принадлежит задаче → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=uuid4())  # другой task_id

        with pytest.raises(WrongInputError) as exc:
            await service.get_comment(comment, task, user, team)

        assert "does not belong to the specified task" in exc.value.message


# ==================== TestCreateComment ====================

class TestCreateComment:
    """Тестируем create_comment."""

    @pytest.mark.asyncio
    async def test_create_comment_success(self, service, repos, session):
        """Успешное создание комментария."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_comment_schema("New comment")

        # Мокаем Comment, чтобы он возвращал объект с нужными атрибутами
        with patch(f"{SERVICE_MODULE}.Comment") as comment_cls:
            new_comment = make_comment(task_id=task.id, author_id=user.id, text="New comment")
            comment_cls.return_value = new_comment

            result = await service.create_comment(data, user, task, team)

        assert result is new_comment
        repos.comment.create.assert_awaited_once_with(new_comment)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_comment_user_not_in_team_raises_authorization_error(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError, коммита нет."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_comment_schema("New comment")
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.create_comment(data, user, task, team)

        repos.comment.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_comment_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError, коммита нет."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())
        data = make_create_comment_schema("New comment")

        with pytest.raises(WrongInputError):
            await service.create_comment(data, user, task, team)

        repos.comment.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_comment_passes_user_and_task_as_objects(self, service, repos):
        """Comment создаётся с user и task как объектами, а не ID."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        data = make_create_comment_schema("New comment")

        with patch(f"{SERVICE_MODULE}.Comment") as comment_cls:
            comment_cls.return_value = make_comment()
            await service.create_comment(data, user, task, team)

        # Проверяем, что Comment вызван с user=user и task=task (объекты)
        call_kwargs = comment_cls.call_args.kwargs
        assert call_kwargs["user"] is user
        assert call_kwargs["task"] is task
        assert call_kwargs["text"] == "New comment"


# ==================== TestUpdate ====================

class TestUpdate:
    """Тестируем update."""

    @pytest.mark.asyncio
    async def test_update_success(self, service, repos, session):
        """Автор обновляет свой комментарий → успех."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=user.id, text="Old text")
        data = make_update_comment_schema(text="New text")

        updated_comment = make_comment(task_id=task.id, author_id=user.id, text="New text")
        repos.comment.update.return_value = updated_comment

        result = await service.update(data, comment, task, user, team)

        assert result is updated_comment
        repos.comment.update.assert_awaited_once_with(comment.id, {"text": "New text"})
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_no_changes_skips_repo_call(self, service, repos, session):
        """Если изменений нет — репо не вызывается, коммита нет."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=user.id)
        data = make_update_comment_schema(text=None)  # ничего не меняем

        result = await service.update(data, comment, task, user, team)

        assert result is comment
        repos.comment.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_user_not_in_team_raises_authorization_error(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=user.id)
        data = make_update_comment_schema(text="New text")
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.update(data, comment, task, user, team)

        repos.comment.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())
        comment = make_comment(task_id=task.id, author_id=user.id)
        data = make_update_comment_schema(text="New text")

        with pytest.raises(WrongInputError):
            await service.update(data, comment, task, user, team)

        repos.comment.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_comment_not_in_task_raises_wrong_input(self, service, repos, session):
        """Комментарий не принадлежит задаче → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=uuid4(), author_id=user.id)
        data = make_update_comment_schema(text="New text")

        with pytest.raises(WrongInputError):
            await service.update(data, comment, task, user, team)

        repos.comment.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_not_author_raises_wrong_input(self, service, repos, session):
        """Не автор пытается редактировать → WrongInputError (даже MANAGER!)."""
        author = make_user(user_id=uuid4())
        manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=author.id)
        data = make_update_comment_schema(text="Hacked text")

        with pytest.raises(WrongInputError) as exc:
            await service.update(data, comment, task, manager, team)

        assert "not allowed" in exc.value.message.lower()
        repos.comment.update.assert_not_awaited()
        session.commit.assert_not_awaited()


# ==================== TestDelete ====================

class TestDelete:
    """Тестируем delete."""

    @pytest.mark.asyncio
    async def test_delete_by_author_success(self, service, repos, session):
        """Автор удаляет свой комментарий → успех."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=user.id)

        result = await service.delete(comment, task, user, team)

        assert result is True
        repos.comment.delete.assert_awaited_once_with(comment)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_manager_success(self, service, repos, session):
        """MANAGER удаляет чужой комментарий → успех (модерация)."""
        author = make_user(user_id=uuid4())
        manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=author.id)

        result = await service.delete(comment, task, manager, team)

        assert result is True
        repos.comment.delete.assert_awaited_once_with(comment)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_author_and_not_manager_raises_wrong_input(self, service, repos, session):
        """Обычный участник пытается удалить чужой комментарий → WrongInputError."""
        author = make_user(user_id=uuid4())
        another_member = make_user(role=RoleEnum.MEMBER, user_id=uuid4())
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=author.id)

        with pytest.raises(WrongInputError) as exc:
            await service.delete(comment, task, another_member, team)

        assert "not allowed" in exc.value.message.lower()
        repos.comment.delete.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_user_not_in_team_raises_authorization_error(self, service, repos, session):
        """Пользователь не в команде → AuthorizationError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=task.id, author_id=user.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.delete(comment, task, user, team)

        repos.comment.delete.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_task_not_in_team_raises_wrong_input(self, service, repos, session):
        """Задача не принадлежит команде → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=uuid4())
        comment = make_comment(task_id=task.id, author_id=user.id)

        with pytest.raises(WrongInputError):
            await service.delete(comment, task, user, team)

        repos.comment.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_comment_not_in_task_raises_wrong_input(self, service, repos, session):
        """Комментарий не принадлежит задаче → WrongInputError."""
        user = make_user()
        team = make_team()
        task = make_task(team_id=team.id)
        comment = make_comment(task_id=uuid4(), author_id=user.id)

        with pytest.raises(WrongInputError):
            await service.delete(comment, task, user, team)

        repos.comment.delete.assert_not_awaited()