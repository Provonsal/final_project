from unittest import result

from fastapi import APIRouter

from app.dependencies import CommentDep, CommentServiceDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_comment import CreateComment
from app.schemas.response_comment import ResponseCommentSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.update_comment import UpdateComment


router = APIRouter()
"""
API роутер для комментариев.

Этот роутер предоставляет эндпоинты для создания, чтения, редактирования и удаления комментариев к задачам.
"""


@router.post("")
async def write_comment(
    comment_data: CreateComment,
    comment_dep: CommentServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
):
    """
    Создаёт новый комментарий для задачи.

    Args:
        comment_data (CreateComment): Текст комментария
        comment_dep (CommentDep): Зависимость для работы с комментариями
        task (Task): Задача, к которой относится комментарий
        user (User): Текущий пользователь
        team (Team): Команда, к которой относится задача

    Returns:
        ResponseCommentSchema: Созданный комментарий

    Example:
        POST /api/v1/teams/tasks/{task_id}/comments
        Body: {"text": "New comment"}
    """
    new_comment = await comment_dep.create_comment(comment_data, user, task, team)
    return ResponseCommentSchema(
        id=new_comment.id,
        created_at=new_comment.created_at.isoformat(),
        text=new_comment.text,
        author=new_comment.author
    )


@router.get("")
async def read_comments(
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    task: TaskDep,
    team: TeamDep
):
    """
    Получает все комментарии для задачи.

    Args:
        user (User): Текущий пользователь (для проверки прав доступа)
        comment_service (CommentService): Сервис для работы с комментариями
        task (Task): Задача, к которой относятся комментарии
        team (Team): Команда, к которой относится задача

    Returns:
        list[ResponseCommentSchema]: Список комментариев

    Example:
        GET /api/v1/teams/tasks/{task_id}/comments
    """
    comments = await comment_service.get_comments(task, user, team)
    return [
        ResponseCommentSchema(
            id=comment.id,
            created_at=comment.created_at.isoformat(),
            text=comment.text,
            author=comment.author
        ) for comment in comments
    ]


@router.patch("/{comment_id}")
async def edit_comment(
    comment_data: UpdateComment,
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    team: TeamDep,
    task: TaskDep,
    comment: CommentDep
):
    """
    Редактирует существующий комментарий.

    Args:
        comment_data (UpdateComment): Новые данные комментария
        user (User): Текущий пользователь (должен быть автором комментария)
        comment_service (CommentService): Сервис для работы с комментариями
        team (Team): Команда, к которой относится задача
        task (Task): Задача, к которой относится комментарий
        comment (Comment): Редактируемый комментарий

    Returns:
        ResponseCommentSchema: Обновленный комментарий

    Example:
        PATCH /api/v1/teams/tasks/{task_id}/comments/{comment_id}
        Body: {"text": "Updated comment text"}
    """
    comment = await comment_service.update(comment_data, comment, task, user, team)
    return ResponseCommentSchema(
        id=comment.id,
        created_at=comment.created_at.isoformat(),
        text=comment.text,
        author=comment.author
    )


@router.delete("/{comment_id}")
async def delete_comment(
    comment_service: CommentServiceDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    team: TeamDep,
    comment: CommentDep
):
    """
    Удаляет комментарий.

    Args:
        comment_service (CommentService): Сервис для работы с комментариями
        user (User): Текущий пользователь (должен быть автором комментария)
        task (Task): Задача, к которой относится комментарий
        team (Team): Команда, к которой относится задача
        comment (Comment): Удаляемый комментарий

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        DELETE /api/v1/teams/tasks/{task_id}/comments/{comment_id}
    """
    result = await comment_service.delete(comment, task, user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()