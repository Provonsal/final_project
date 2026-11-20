



from fastapi import APIRouter

from app.dependencies import ManagerDep, MeetingDep, MeetingServiceDep, MemberOrManagerDep, TeamDep
from app.schemas.create_meeting import CreateMeeting
from app.schemas.response_invite_code import ResponseInviteCodeSchema
from app.schemas.response_meeting import ResponseMeetingSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.update_meeting import UpdateMeeting


router = APIRouter()

@router.post("")
async def create_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
    data: CreateMeeting
): 
    new_meeting = await meeting_service_dep.create_meeting(data, team, user)
    invite_code = await meeting_service_dep.get_invite_code(team, new_meeting, user)
    await meeting_service_dep.join_meeting(team, invite_code.body, user)
    return ResponseMeetingSchema(
        id=new_meeting.id,
        start_time=new_meeting.starts_at.isoformat(),
        end_time=new_meeting.ends_at.isoformat(),
        team_id=new_meeting.related_team,
        creator=new_meeting.creator
    )
        

@router.get("")
async def read_meetings(
    team: TeamDep,
    user: MemberOrManagerDep,
    meeting_service_dep: MeetingServiceDep,
):
    meetings = await meeting_service_dep.get_meetings(team, user)
    return [ResponseMeetingSchema(
        id=meeting.id,
        start_time=meeting.starts_at.isoformat(),
        end_time=meeting.ends_at.isoformat(),
        team_id=meeting.related_team,
        creator=meeting.creator
    ) for meeting in meetings]

@router.post("/join")
async def join_meeting(
    team: TeamDep,
    user: MemberOrManagerDep,
    code: str,
    meeting_service_dep: MeetingServiceDep,
):
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
    meeting = await meeting_service_dep.get_meeting(meeting, team, user)
    return ResponseMeetingSchema(
        id=meeting.id,
        start_time=meeting.starts_at.isoformat(),
        end_time=meeting.ends_at.isoformat(),
        team_id=meeting.related_team,
        creator=meeting.creator
    )

@router.patch("/{meeting_id}")
async def update_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    data: UpdateMeeting
): 
    meeting = await meeting_service_dep.update(meeting, team, data, user)
    return ResponseMeetingSchema(
        id=meeting.id,
        start_time=meeting.starts_at.isoformat(),
        end_time=meeting.ends_at.isoformat(),
        team_id=meeting.related_team,
        creator=meeting.creator
    )
    

@router.delete("/{meeting_id}")
async def delete_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    result = await meeting_service_dep.delete(meeting, team, user)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()