from fastapi import APIRouter

from app.dependencies import EvaluationDep, EvaluationServiceDep, ManagerDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_evaluation import CreateEvaluation
from app.schemas.response_evaluation import ResponseEvaluationSchema
from app.schemas.update_evaluation import UpdateEvaluation


router = APIRouter()
"""
API роутер для оценок задач.

Этот роутер предоставляет эндпоинты для создания, чтения, редактирования и удаления оценок задач.
"""


@router.post("")
async def write_evaluation(
    evaluation_data: CreateEvaluation,
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: ManagerDep,
    team: TeamDep
):
    """
    Создаёт новую оценку для задачи.

    Только менеджер может создавать оценки.

    Аргументы:
        evaluation_data (CreateEvaluation): Данные оценки (идентификатор задачи)
        evaluation_service_dep (EvaluationService): Сервис для работы с оценками
        task (Task): Задача, для которой создаётся оценка
        user (User): Модели менеджер, создающий оценку
        team (Team): Команда, к которой относится задача

    Возвращает:
        ResponseEvaluationSchema: Созданная оценка

    Пример:
        POST /api/v1/teams/tasks/{task_id}/evaluations
        Body: {"task_id": "uuid"}
    """
    evaluation = await evaluation_service_dep.create_evaluation(evaluation_data, user, team, task)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )


@router.get("")
async def read_evaluation(
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
    evaluation: EvaluationDep
):
    """
    Получает информацию об оценке задачи.

    Аргументы:
        evaluation_service_dep (EvaluationService): Сервис для работы с оценками
        task (Task): Задача, для которой получаем оценку
        user (User): Текущий пользователь (для проверки прав доступа)
        team (Team): Команда, к которой относится задача
        evaluation (Evaluation): Запрашиваемая оценка

    Возвращает:
        ResponseEvaluationSchema: Информация об оценке

    Пример:
        GET /api/v1/teams/tasks/{task_id}/evaluations/{evaluation_id}
    """
    evaluation = await evaluation_service_dep.get_evaluation(user, team, task, evaluation)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )


@router.patch("/{evaluation_id}")
async def edit_evaluation(
    evaluation: EvaluationDep,
    evaluation_data: UpdateEvaluation,
    evaluation_service_dep: EvaluationServiceDep,
    user: ManagerDep,
    task: TaskDep,
    team: TeamDep
):
    """
    Редактирует существующую оценку.

    Только менеджер может редактировать оценки.

    Аргументы:
        evaluation (Evaluation): Редактируемая оценка
        evaluation_data (UpdateEvaluation): Новые данные оценки
        evaluation_service_dep (EvaluationService): Сервис для работы с оценками
        user (User): Модели менеджер, редактирующий оценку
        task (Task): Задача, к которой относится оценка
        team (Team): Команда, к которой относится задача

    Возвращает:
        ResponseEvaluationSchema: Обновлённая оценка

    Пример:
        PATCH /api/v1/teams/tasks/{task_id}/evaluations/{evaluation_id}
        Body: {"rate": 5}
    """
    evaluation = await evaluation_service_dep.update(evaluation_data, user, team, task, evaluation)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )