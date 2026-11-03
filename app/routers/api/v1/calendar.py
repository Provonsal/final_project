from datetime import UTC, datetime, timezone
import uuid

from fastapi import APIRouter

from app.dependencies import CalendarServiceDep, CurrentUserDep, MemberDep, MemberOrManagerDep, TeamDep


router = APIRouter(
    prefix="/calendar",  # Все пути будут начинаться с /users
    tags=["calendar"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

@router.get("/{team_id}")
async def root(
    team: TeamDep,
    calendar_service_dep: CalendarServiceDep,
    user: MemberOrManagerDep,
    date_from: datetime = datetime.now(tz=UTC), 
    date_until: datetime | None = None
):
    return await calendar_service_dep.get_meetings(team, user, date_from, date_until)
