from datetime import UTC, datetime, timezone
import uuid

from fastapi import APIRouter

from app.dependencies import CalendarServiceDep, CurrentUserDep, MemberDep, MemberOrManagerDep, TaskServiceDep, TeamDep
from app.schemas.response_meeting import ResponseMeetingSchema
from app.schemas.response_task import ResponseTaskSchema


router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    responses={404: {"description": "Not found"}}
)
"""
API роутер для календаря совещаний.

Этот роутер предоставляет доступ к расписанию совещаний команды.
"""

@router.get("/{team_id}")
async def root(
    team: TeamDep,
    calendar_service_dep: CalendarServiceDep,
    task_service_dep: TaskServiceDep,
    user: MemberOrManagerDep,
    date_from: datetime = datetime.now(tz=UTC),
    date_until: datetime | None = None
):
    """
    Получает список совещаний и задач в диапазоне дат.

    Args:
        team: Команда, для которой запрашиваются задачи и совещания
        calendar_service_dep: Сервис для работы с календарём
        user: Текущий пользователь (должен быть членом или менеджером команды)
        date_from: Начальная дата диапазона (по умолчанию сегодня)
        date_until: Конечная дата диапазона (опционально)

    Returns:
        Dict: Словарь с совещаниями и задачами
    Example:
        GET /api/v1/calendar/{team_id}?date_from=2023-12-01&date_until=2023-12-31
    """
    meetings = await calendar_service_dep.get_meetings(team, user, date_from, date_until)
    tasks = await task_service_dep.get_tasks(user, team, date_from=None, date_until=date_until)
    resp = {
        "meetings": [ResponseMeetingSchema(
                    id=meeting.id,
                    start_time=meeting.starts_at.isoformat(),
                    end_time=meeting.ends_at.isoformat(),
                    team_id=meeting.related_team,
                    creator=meeting.creator,
                    max_members=meeting.max_members
                ) for meeting in meetings],
        "tasks": [
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
    }
    return resp
