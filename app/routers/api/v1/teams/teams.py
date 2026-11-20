from fastapi import APIRouter
from app.dependencies import ManagerDep, MemberDep, MemberOrManagerDep, TeamDep, TeamServiceDep, AnyAuthDep
from app.schemas.create_team import CreateTeam
from app.schemas.response_invite_code import ResponseInviteCodeSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.response_team import ResponseTeamSchema
from app.schemas.response_user import ResponseUserSchema
from app.schemas.update_team import UpdateTeam

router = APIRouter()



@router.post("/")
async def create_team(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
    data: CreateTeam
):
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
    
    members_list = await team_service_dep.get_team_users(team, user)
    return [
        ResponseUserSchema(
            id=user.id,
            username=user.name,
            email=user.email,
            active=user.is_active
        ) for user in members_list
    ]