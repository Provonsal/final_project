from fastapi import APIRouter
from app.dependencies import ManagerDep, MemberOrManagerDep, TeamDep, TeamServiceDep, AnyAuthDep
from app.schemas.create_team import TeamCreate
from app.schemas.update_team import TeamUpdate

router = APIRouter()

@router.post("/")
async def create_team(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
    data: TeamCreate
):
    new_team = await team_service_dep.create_team(user, data)
    invite_code = await team_service_dep.get_invite_code(new_team, user)
    await team_service_dep.join_team(user, invite_code.body)
    return new_team

@router.post("/join")
async def join(
    invite_code: str, 
    current_user: AnyAuthDep, 
    team_dep: TeamServiceDep
):
    
    await team_dep.join_team(current_user, invite_code)

@router.post("/code")
async def get_invite_code(
    team: TeamDep, 
    user: ManagerDep, 
    team_service_dep: TeamServiceDep
):
    return await team_service_dep.get_invite_code(team, user)

@router.get("/")
async def read_teams(
    user: MemberOrManagerDep, 
    team_service_dep: TeamServiceDep,
):
    return await team_service_dep.get_teams(user)

@router.get("/{team_id}")
async def read_team(
    user: MemberOrManagerDep, 
    team_service_dep: TeamServiceDep,
    team: TeamDep,
):
    return await team_service_dep.get_team(team, user)

@router.patch("/{team_id}")
async def update_team(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
    team: TeamDep,
    data: TeamUpdate
):
    return await team_service_dep.update(team, user, data)

@router.delete("/{team_id}")
async def delete_team(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
    team: TeamDep
):
    return await team_service_dep.delete(team, user)


@router.get("/{team_id}/members")
async def members(
    team_service_dep: TeamServiceDep,
    team: TeamDep, 
    user: MemberOrManagerDep,
):
    
    members_list = await team_service_dep.get_team_users(team, user)
    return members_list