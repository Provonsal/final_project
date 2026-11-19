



from fastapi import APIRouter

from app.dependencies import ManagerDep, MeetingDep, MeetingServiceDep, MemberOrManagerDep, TeamDep
from app.schemas.create_meeting import MeetingCreate
from app.schemas.return_meeting import ReturnMeetingSchema
from app.schemas.update_meeting import MeetingUpdate


router = APIRouter()

@router.post("")
async def create_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingCreate
): 
    new_meeting = await meeting_service_dep.create_meeting(data, team, user)
    invite_code_body = await meeting_service_dep.get_invite_code(team, new_meeting, user)
    await meeting_service_dep.join_meeting(team, invite_code_body, user)
    return ReturnMeetingSchema(
        id=new_meeting.id,
        start_time=new_meeting.starts_at.isoformat(),
        end_time=new_meeting.ends_at.isoformat(),
        team_id=new_meeting.related_team
    )
        

@router.get("")
async def read_meetings(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.get_meetings(team, user)

@router.post("/join")
async def join_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    code: str,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.join_meeting(team, code, user)

@router.get("/{meeting_id}/invite_code")
async def get_invite_code(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.get_invite_code(team, meeting, user)

@router.post("/{meeting_id}/leave")
async def leave_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.leave_meeting(team, meeting, user)

@router.get("/{meeting_id}")
async def read_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
): 
    return await meeting_service_dep.get_meeting(meeting, team, user)

@router.patch("/{meeting_id}")
async def update_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingUpdate
): 
    return await meeting_service_dep.update(meeting, team, data, user)
    

@router.delete("/{meeting_id}")
async def delete_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.delete(meeting, team, user)