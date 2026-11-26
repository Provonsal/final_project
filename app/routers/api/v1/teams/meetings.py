



from fastapi import APIRouter

from app.dependencies import ManagerDep, MeetingDep, MeetingServiceDep, MemberOrManagerDep, TeamDep
from app.schemas.create_meeting import CreateMeeting
from app.schemas.response_invite_code import ResponseInviteCodeSchema
from app.schemas.response_meeting import ResponseMeetingSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.update_meeting import UpdateMeeting


router = APIRouter()
"""
API роутер для управления совещаниями.

Этот роутер предоставляет эндпоинты для создания, управления и взаимодействия с совещаниями команды.
"""

@router.post("")
async def create_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
    data: CreateMeeting
):
    """
    Создает новое совещание в команде.

    Только менеджер может создавать совещания. После создания автоматически создает invite-код.

    Args:
        team (Team): Команда, для которой создается совещание
        user (User): Модели менеджер, создающий совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями
        data (CreateMeeting): Данные для создания совещания

    Returns:
        ResponseMeetingSchema: Информация о созданном совещании

    Example:
        POST /api/v1/teams/meetings/
        Body: {"title": "Meeting", "starts_at": "2023-01-01T10:00:00", "ends_at": "2023-01-01T11:00:00"}
    """
    new_meeting = await meeting_service_dep.create_meeting(data, team, user)
    invite_code = await meeting_service_dep.get_invite_code(team, new_meeting, user)
    await meeting_service_dep.join_meeting(team, invite_code.body, user)
    return ResponseMeetingSchema(
        id=new_meeting.id,
        start_time=new_meeting.starts_at.isoformat(),
        end_time=new_meeting.ends_at.isoformat(),
        team_id=new_meeting.related_team,
        creator=new_meeting.creator,
        max_members=new_meeting.max_members
    )


@router.get("")
async def read_meetings(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Получает все совещания команды.

    Args:
        team (Team): Команда, для которой получаем совещания
        user (User): Текущий пользователь (для проверки прав доступа)
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        list[ResponseMeetingSchema]: Список совещаний команды

    Example:
        GET /api/v1/teams/meetings/
    """
    meetings = await meeting_service_dep.get_meetings(team, user)
    return [
        ResponseMeetingSchema(
            id=meeting.id,
            start_time=meeting.starts_at.isoformat(),
            end_time=meeting.ends_at.isoformat(),
            team_id=meeting.related_team,
            creator=meeting.creator,
            max_members=meeting.max_members
        ) for meeting in meetings
    ]

@router.post("/join")
async def join_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    code: str,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Присоединяет пользователя к совещанию по invite-коду.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Текущий пользователь
        code (str): Invite-код для участия в совещании
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        POST /api/v1/teams/meetings/join
        Body: {"code": "ABC123"}
    """
    result = await meeting_service_dep.join_meeting(team, code, user)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()

@router.get("/{meeting_id}/invite_code")
async def get_invite_code(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Получает invite-код для совещания.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Текущий пользователь (для проверки прав доступа)
        meeting (Meeting): Запрашиваемое совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        ResponseInviteCodeSchema: Invite-код с деталями

    Example:
        GET /api/v1/teams/meetings/{meeting_id}/invite_code
    """
    code = await meeting_service_dep.get_invite_code(team, meeting, user)
    return ResponseInviteCodeSchema(
        id=code.id,
        code=code.body,
        team_id=code.connected_to,
        is_active=code.active,
        creator=code.creator
    )

@router.post("/{meeting_id}/invite_code")
async def create_invite_code(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    uses: int | None = None
):
    """
    Создает новый invite-код для совещания.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Модели менеджер, создающий invite-код
        meeting (Meeting): Совещание для invite-кода
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями
        uses (int | None): Количество использований invite-кода (-1 для неограниченного)

    Returns:
        ResponseInviteCodeSchema: Созданный invite-код

    Example:
        POST /api/v1/teams/meetings/{meeting_id}/invite_code
    """
    if uses is None:
        uses = -1  # -1 означает неограниченное количество использований
    code = await meeting_service_dep.create_invite_code(team, meeting, user, uses)
    return ResponseInviteCodeSchema(
        id=code.id,
        code=code.body,
        team_id=code.connected_to,
        is_active=code.active,
        creator=code.creator
    )

@router.post("/{meeting_id}/leave")
async def leave_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Удаляет пользователя из совещания.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Текущий пользователь
        meeting (Meeting): Совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        POST /api/v1/teams/meetings/{meeting_id}/leave
    """
    result = await meeting_service_dep.leave_meeting(team, meeting, user)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()

@router.get("/{meeting_id}")
async def read_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Получает информацию о совещании.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Текущий пользователь (для проверки прав доступа)
        meeting (Meeting): Запрашиваемое совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        ResponseMeetingSchema: Информация о совещании

    Example:
        GET /api/v1/teams/meetings/{meeting_id}
    """
    meeting = await meeting_service_dep.get_meeting(meeting, team, user)
    return ResponseMeetingSchema(
        id=meeting.id,
        start_time=meeting.starts_at.isoformat(),
        end_time=meeting.ends_at.isoformat(),
        team_id=meeting.related_team,
        creator=meeting.creator,
        max_members=meeting.max_members
    )

@router.patch("/{meeting_id}")
async def update_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    data: UpdateMeeting
):
    """
    Обновляет информацию о совещании.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Модели менеджер, обновляющий совещание
        meeting (Meeting): Обновляемое совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями
        data (UpdateMeeting): Новые данные для совещания

    Returns:
        ResponseMeetingSchema: Обновленная информация о совещании

    Example:
        PATCH /api/v1/teams/meetings/{meeting_id}
        Body: {"title": "Updated Meeting"}
    """
    
    meeting = await meeting_service_dep.update(meeting, team, data, user)
    return ResponseMeetingSchema(
        id=meeting.id,
        start_time=meeting.starts_at.isoformat(),
        end_time=meeting.ends_at.isoformat(),
        team_id=meeting.related_team,
        creator=meeting.creator,
        max_members=meeting.max_members
    )


@router.delete("/{meeting_id}")
async def delete_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    """
    Удаляет совещание.

    Args:
        team (Team): Команда, к которой относится совещание
        user (User): Модели менеджер, удаляющий совещание
        meeting (Meeting): Удаляемое совещание
        meeting_service_dep (MeetingService): Сервис для работы с совещаниями

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        DELETE /api/v1/teams/meetings/{meeting_id}
    """
    result = await meeting_service_dep.delete(meeting, team, user)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()