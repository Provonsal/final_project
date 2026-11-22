from datetime import UTC, datetime, timezone
import uuid

from fastapi import APIRouter

from app.dependencies import CalendarServiceDep, CurrentUserDep, MemberDep, MemberOrManagerDep, TeamDep
from app.schemas.response_meeting import ResponseMeetingSchema


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
    user: MemberOrManagerDep,
    date_from: datetime = datetime.now(tz=UTC),
    date_until: datetime | None = None
):
    """
    Получает список совещаний для команды.

    Args:
        team: Команда, для которой запрашиваются совещания
        calendar_service_dep: Сервис для работы с календарём
        user: Текущий пользователь (должен быть членом или менеджером команды)
        date_from: Начальная дата диапазона (по умолчанию сегодня)
        date_until: Конечная дата диапазона (опционально)

    Returns:
        List[ResponseMeetingSchema]: Список совещаний

    Example:
        GET /api/v1/calendar/{team_id}?date_from=2023-12-01&date_until=2023-12-31
    """
    meetings = await calendar_service_dep.get_meetings(team, user, date_from, date_until)
    return [
        ResponseMeetingSchema(
            id=meeting.id,
            start_time=meeting.starts_at.isoformat(),
            end_time=meeting.ends_at.isoformat(),
            team_id=meeting.related_team,
            creator=meeting.creator
        ) for meeting in meetings
    ]
