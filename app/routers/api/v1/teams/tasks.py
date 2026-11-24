from fastapi import APIRouter
from typing import Optional, cast

from app.dependencies import EvaluationDep, TaskDep, TeamDep, TaskServiceDep, ManagerDep, MemberOrManagerDep, CommentServiceDep, EvaluationServiceDep, get_evaluation
from app.models import RateEnum
from app.models.models import Task
from app.schemas.create_task import CreateTask
from app.schemas.response_evaluation import ResponseEvaluationSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.response_task import ResponseTaskSchema
from app.schemas.update_task import UpdateTask

router = APIRouter()
"""
API роутер для управления задачами.

Этот роутер предоставляет эндпоинты для создания, управления и взаимодействия с задачами команды.
"""

@router.post("")
async def create_task(
    task_service_dep: TaskServiceDep,
    team: TeamDep,
    user: ManagerDep,
    data: CreateTask
):
    """
    Создает новую задачу в команде.

    Только менеджер может создавать задачи.

    Args:
        task_service_dep (TaskService): Сервис для работы с задачами
        team (Team): Команда, в которой создается задача
        user (User): Модели менеджер, создающий задачу
        data (CreateTask): Данные для создания задачи

    Returns:
        ResponseTaskSchema: Информация о созданной задаче

    Example:
        POST /api/v1/teams/tasks/
        Body: {"title": "New Task", "description": "Task description", "assignee_id": user_uuid}
    """
    
    task = await task_service_dep.create_task(data, team, user)
    evaluation_schema = ResponseEvaluationSchema(
        id=task.rate.id,
        rate=task.rate.rate,
        author=task.rate.rater,
        display_text=task.rate.rate.name
    )
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id,
        evaluation=evaluation_schema
    )


@router.get("")
async def read_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep,
    user: MemberOrManagerDep,
    evaluation_service_dep: EvaluationServiceDep
):
    """
    Получает все задачи команды.

    Args:
        task_service_dep (TaskService): Сервис для работы с задачами
        team (Team): Команда, для которой получаем задачи
        user (User): Текущий пользователь (для проверки прав доступа)

    Returns:
        list[ResponseTaskSchema]: Список задач команды

    Example:
        GET /api/v1/teams/tasks/
    """

    tasks: list[Task] = cast(list, await task_service_dep.get_all_tasks(team, user))

    evaluations = await evaluation_service_dep.get_evaluations_for_tasks(user, team, tasks)

    response = [
        ResponseTaskSchema(
            id=task.id,
            title=task.title,
            description=task.description,
            assignee_id=task.assignee,
            due_date=task.due_date.isoformat(),
            status=task.status,
            team_id=task.team_id,
            evaluation=None,

        ) for task in tasks
    ]

    for response_schema in response:
        evaluation = evaluations.get(response_schema.id)
        
        if evaluation is None: continue
        
        evaluation_schema = ResponseEvaluationSchema(
            id=evaluation.id,
            rate=evaluation.rate,
            author=evaluation.rater,
            display_text=evaluation.rate.name
        )
        response_schema.evaluation = evaluation_schema

    return response


@router.get("/{task_id}")
async def read_task(
    team: TeamDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    comment_service: CommentServiceDep,
):
    """
    Получает информацию о задаче.

    Args:
        team (Team): Команда, к которой относится задача
        user (User): Текущий пользователь (для проверки прав доступа)
        task (Task): Запрашиваемая задача
        task_service_dep (TaskService): Сервис для работы с задачами
        evaluation_service (EvaluationService): Сервис для работы с оценками
        comment_service (CommentService): Сервис для работы с комментариями

    Returns:
        ResponseTaskSchema: Информация о задаче с комментариями и оценкой

    Example:
        GET /api/v1/teams/tasks/{task_id}
    """    

    comments = cast(list, await comment_service.get_comments(task, user, team))

    await task.awaitable_attrs.rate
    
    evaluation_schema = ResponseEvaluationSchema(
        id=task.rate.id,
        rate=task.rate.rate,
        author=task.rate.rater,
        display_text=task.rate.rate.name
    )

    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id,
        evaluation=evaluation_schema,
        comments=comments
    )

@router.patch("/{task_id}")
async def update_tasks(
    data: UpdateTask,
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    evaluation: EvaluationDep,
    task_service_dep: TaskServiceDep,
    comment_service: CommentServiceDep,
):
    """
    Обновляет задачу.

    Args:
        team (Team): Команда, к которой относится задача
        user (User): Модели менеджер, обновляющий задачу
        task (Task): Обновляемая задача
        task_service_dep (TaskService): Сервис для работы с задачами
        data (UpdateTask): Новые данные для задачи

    Returns:
        ResponseTaskSchema: Обновленная информация о задаче

    Example:
        PATCH /api/v1/teams/tasks/{task_id}
        Body: {"title": "Updated Task", "status": "done"}
    """
    task = await task_service_dep.update_task(data, task, user, team)
    comments = cast(list, await comment_service.get_comments(task, user, team))
    
    evaluation_schema = ResponseEvaluationSchema(
        id=task.rate.id,
        rate=task.rate.rate,
        author=task.rate.rater,
        display_text=task.rate.rate.name
    )
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id,
        evaluation=evaluation_schema,
        comments=comments
    )

@router.delete("/{task_id}")
async def delete_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep
):
    """
    Удаляет задачу.

    Args:
        team (Team): Команда, к которой относится задача
        user (User): Модели менеджер, удаляющий задачу
        task (Task): Удаляемая задача
        task_service_dep (TaskService): Сервис для работы с задачами

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        DELETE /api/v1/teams/tasks/{task_id}
    """
    result = await task_service_dep.delete_task(task, user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()