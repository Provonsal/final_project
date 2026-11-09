



from fastapi import APIRouter

from app.dependencies import ManagerDep, MeetingDep, MeetingServiceDep, TeamDep
from app.schemas.create_meeting import MeetingCreate
from app.schemas.update_meeting import MeetingUpdate


router = APIRouter()

@router.post("")
async def create_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingCreate
): 
    return await meeting_service_dep.create_meeting(data, team, user)
        

@router.get("")
async def read_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.get_meetings(team, user)

@router.get("/{meeting_id}")
async def read_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
): 
    return await meeting_service_dep.get_meeting(meeting, team, user)

@router.patch("/{meeting_id}")
async def update_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingUpdate
): 
    return await meeting_service_dep.update(meeting, team, data, user)
    

@router.delete("/{meeting_id}")
async def delete_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.delete(meeting, team, user)