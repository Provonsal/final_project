from fastapi import APIRouter
from app.dependencies import TaskDep, TeamDep, TaskServiceDep, ManagerDep, MemberOrManagerDep
from app.schemas.create_task import CreateTask
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.response_task import ResponseTaskSchema
from app.schemas.update_task import UpdateTask

router = APIRouter()
"""
API роутер для управления задачами.

Этот роутер предоставляет эндпоинты для создания, управления и взаимодействия с задачами команды.
"""

@router.post("")
async def create_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep,
    user: ManagerDep,
    data: CreateTask
):
    """
    Создает новую задачу в команде.

    Только менеджер может создавать задачи.

    Аргументы:
        task_service_dep (TaskService): Сервис для работы с задачами
        team (Team): Команда, в которой создается задача
        user (User): Модели менеджер, создающий задачу
        data (CreateTask): Данные для создания задачи

    Возвращает:
        ResponseTaskSchema: Информация о созданной задаче

    Пример:
        POST /api/v1/teams/tasks/
        Body: {"title": "New Task", "description": "Task description", "assignee_id": user_uuid}
    """
    task = await task_service_dep.create_task(data, team, user)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
    )


@router.get("")
async def read_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep,
    user: MemberOrManagerDep,
):
    """
    Получает все задачи команды.

    Аргументы:
        task_service_dep (TaskService): Сервис для работы с задачами
        team (Team): Команда, для которой получаем задачи
        user (User): Текущий пользователь (для проверки прав доступа)

    Возвращает:
        list[ResponseTaskSchema]: Список задач команды

    Пример:
        GET /api/v1/teams/tasks/
    """
    tasks = await task_service_dep.get_all_tasks(team, user)
    return [
        ResponseTaskSchema(
            id=task.id,
            title=task.title,
            description=task.description,
            assignee_id=task.assignee,
            due_date=task.due_date.isoformat(),
            status=task.status,
            team_id=task.team_id
        ) for task in tasks
    ]


@router.get("/{task_id}")
async def read_task(
    team: TeamDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
):
    """
    Получает информацию о задаче.

    Аргументы:
        team (Team): Команда, к которой относится задача
        user (User): Текущий пользователь (для проверки прав доступа)
        task (Task): Запрашиваемая задача
        task_service_dep (TaskService): Сервис для работы с задачами

    Возвращает:
        ResponseTaskSchema: Информация о задаче

    Пример:
        GET /api/v1/teams/tasks/{task_id}
    """
    task = await task_service_dep.get_task(task, team, user)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
    )

@router.patch("/{task_id}")
async def update_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
    data: UpdateTask
):
    """
    Обновляет задачу.

    Аргументы:
        team (Team): Команда, к которой относится задача
        user (User): Модели менеджер, обновляющий задачу
        task (Task): Обновляемая задача
        task_service_dep (TaskService): Сервис для работы с задачами
        data (UpdateTask): Новые данные для задачи

    Возвращает:
        ResponseTaskSchema: Обновленная информация о задаче

    Пример:
        PATCH /api/v1/teams/tasks/{task_id}
        Body: {"title": "Updated Task", "status": "done"}
    """
    task = await task_service_dep.update_task(data, task, user, team)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
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

    Аргументы:
        team (Team): Команда, к которой относится задача
        user (User): Модели менеджер, удаляющий задачу
        task (Task): Удаляемая задача
        task_service_dep (TaskService): Сервис для работы с задачами

    Возвращает:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Пример:
        DELETE /api/v1/teams/tasks/{task_id}
    """
    result = await task_service_dep.delete_task(task, user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()