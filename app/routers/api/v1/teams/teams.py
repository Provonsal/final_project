from fastapi import APIRouter
from app.dependencies import ManagerDep, MemberDep, MemberOrManagerDep, TeamDep, TeamServiceDep, AnyAuthDep
from app.schemas.create_team import CreateTeam
from app.schemas.response_invite_code import ResponseInviteCodeSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.response_team import ResponseTeamSchema
from app.schemas.response_user import ResponseUserSchema
from app.schemas.update_team import UpdateTeam

router = APIRouter()
"""
API роутер для управления командами.

Этот роутер предоставляет эндпоинты для создания, управления и взаимодействия с командами.
"""



@router.post("/")
async def create_team(
    user: ManagerDep,
    team_service_dep: TeamServiceDep,
    data: CreateTeam
):
    """
    Создает новую команду.

    Только менеджер может создать команду. После создания создает invite-код для приглашения участников.

    Args:
        user (User): Модели менеджер, создающий команду
        team_service_dep (TeamService): Сервис для работы с командами
        data (CreateTeam): Данные для создания команды

    Returns:
        ResponseTeamSchema: Информация о созданной команде

    Example:
        POST /api/v1/teams/
        Body: {"name": "My Team"}
    """

    new_team = await team_service_dep.create_team(user, data)
    invite_code = await team_service_dep.get_invite_code(new_team, user)
    await team_service_dep.join_team(user, invite_code.body)
    return ResponseTeamSchema(
        id=new_team.id,
        name=new_team.name,
        max_members=new_team.max_per_team,
        owner_id=new_team.owner
    )

@router.post("/join")
async def join(
    invite_code: str,
    current_user: AnyAuthDep,
    team_dep: TeamServiceDep
):
    """
    Присоединяет пользователя к команде по invite-коду.

    Args:
        invite_code (str): Invite-код для участия в команде
        current_user (User): Текущий авторизованный пользователь
        team_dep (TeamService): Сервис для работы с командами

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        POST /api/v1/teams/join
        Body: {"invite_code": "ABC123"}
    """
    
    result = await team_dep.join_team(current_user, invite_code)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()

@router.post("/code")
async def get_invite_code(
    team: TeamDep,
    user: ManagerDep,
    team_service_dep: TeamServiceDep
):
    """
    Генерирует invite-код для команды.

    Только менеджер может создавать invite-коды.

    Args:
        team (Team): Команда для создания invite-кода
        user (User): Модели менеджер команды
        team_service_dep (TeamService): Сервис для работы с командами

    Returns:
        ResponseInviteCodeSchema: Invite-код с деталями

    Example:
        POST /api/v1/teams/code
    """

    invite_code = await team_service_dep.get_invite_code(team, user)
    return ResponseInviteCodeSchema(
        id=invite_code.id,
        code=invite_code.body,
        team_id=invite_code.connected_to,
        is_active=invite_code.active,
        creator=invite_code.creator
    )

@router.post("/{team_id}/leave")
async def leave(
    current_user: MemberDep,
    team: TeamDep,
    team_dep: TeamServiceDep
):
    """
    Удаляет пользователя из команды.

    Args:
        current_user (User): Текущий пользователь
        team (Team): Команда, из которой выходит пользователь
        team_dep (TeamService): Сервис для работы с командами

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        POST /api/v1/teams/{team_id}/leave
    """

    result = await team_dep.leave_team(current_user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()

@router.get("/")
async def read_teams(
    user: MemberOrManagerDep,
    team_service_dep: TeamServiceDep,
):
    """
    Получает список команд пользователя.

    Args:
        user (User): Текущий пользователь
        team_service_dep (TeamService): Сервис для работы с командами

    Returns:
        list[ResponseTeamSchema]: Список команд пользователя

    Example:
        GET /api/v1/teams/
    """

    teams = await team_service_dep.get_teams(user)
    return [
        ResponseTeamSchema(
            id=team.id,
            name=team.name,
            max_members=team.max_per_team,
            owner_id=team.owner
        ) for team in teams
    ]

@router.get("/{team_id}")
async def read_team(
    user: MemberOrManagerDep,
    team_service_dep: TeamServiceDep,
    team: TeamDep,
):
    """
    Получает информацию о команде.

    Args:
        user (User): Текущий пользователь (для проверки прав доступа)
        team_service_dep (TeamService): Сервис для работы с командами
        team (Team): Запрашиваемая команда

    Returns:
        ResponseTeamSchema: Информация о команде

    Example:
        GET /api/v1/teams/{team_id}
    """

    team = await team_service_dep.get_team(team, user)
    return ResponseTeamSchema(
        id=team.id,
        name=team.name,
        max_members=team.max_per_team,
        owner_id=team.owner
    )

@router.patch("/{team_id}")
async def update_team(
    user: ManagerDep,
    team_service_dep: TeamServiceDep,
    team: TeamDep,
    data: UpdateTeam
):
    """
    Обновляет информацию о команде.

    Только менеджер может обновлять информацию о команде.

    Args:
        user (User): Модели менеджер команды
        team_service_dep (TeamService): Сервис для работы с командами
        team (Team): Обновляемая команда
        data (UpdateTeam): Новые данные команды

    Returns:
        ResponseTeamSchema: Обновленная информация о команде

    Example:
        PATCH /api/v1/teams/{team_id}
        Body: {"name": "Updated Team Name"}
    """

    team = await team_service_dep.update(team, user, data)
    return ResponseTeamSchema(
        id=team.id,
        name=team.name,
        max_members=team.max_per_team,
        owner_id=team.owner
    )

@router.delete("/{team_id}")
async def delete_team(
    user: ManagerDep,
    team_service_dep: TeamServiceDep,
    team: TeamDep
):
    """
    Удаляет команду.

    Только менеджер может удалить свою команду.

    Args:
        user (User): Модели менеджер команды
        team_service_dep (TeamService): Сервис для работы с командами
        team (Team): Удаляемая команда

    Returns:
        ResponseOperationSuccess | ResponseOperationFailure: Результат операции

    Example:
        DELETE /api/v1/teams/{team_id}
    """

    result = await team_service_dep.delete(team, user)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()


@router.get("/{team_id}/members")
async def members(
    team_service_dep: TeamServiceDep,
    team: TeamDep,
    user: MemberOrManagerDep,
):
    """
    Получает список участников команды.

    Args:
        team_service_dep (TeamService): Сервис для работы с командами
        team (Team): Команда
        user (User): Текущий пользователь (для проверки прав доступа)

    Returns:
        list[ResponseUserSchema]: Список участников команды

    Example:
        GET /api/v1/teams/{team_id}/members
    """
    
    members_list = await team_service_dep.get_team_users(team, user)
    return [
        ResponseUserSchema(
            id=user.id,
            username=user.name,
            email=user.email,
            active=user.is_active,
            role=user.role
        ) for user in members_list
    ]