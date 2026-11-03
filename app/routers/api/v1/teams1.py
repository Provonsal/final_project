from calendar import c
import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import AnyAuthDep, CommentDep, CommentServiceDep, EvaluationDep, EvaluationServiceDep, ManagerDep, MeetingDep, MeetingServiceDep, MemberOrManagerDep, TaskDep, TaskServiceDep, TeamDep, TeamServiceDep, CurrentUserDep
from fastapi import status

from app.schemas.create_comment import CommentCreate
from app.schemas.create_evaluation import EvaluationCreate
from app.schemas.create_meeting import MeetingCreate
from app.schemas.create_team import TeamCreate
from app.schemas.task_create import TaskCreate
from app.schemas.task_update import TaskUpdate
from app.schemas.update_comment import CommentUpdate
from app.schemas.update_evaluation import EvaluationUpdate
from app.schemas.update_meeting import MeetingUpdate
from app.schemas.update_team import TeamUpdate


router = APIRouter(
    prefix="/teams",  # Все пути будут начинаться с /users
    tags=["teams"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

@router.post("/")
async def create_team(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
    data: TeamCreate
):
    await team_service_dep.create_team(user, data)

@router.get("/")
async def read_teams(
    user: ManagerDep, 
    team_service_dep: TeamServiceDep,
):
    return await team_service_dep.get_teams(user)

@router.get("/{team_id}")
async def read_team(
    user: ManagerDep, 
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

@router.post("/join")
async def join(
    invite_code: str, 
    current_user: AnyAuthDep, 
    team_dep: TeamServiceDep
):
    
    await team_dep.join_team(current_user, invite_code)
    


@router.get("/{team_id}/members")
async def members(
    team_service_dep: TeamServiceDep,
    team: TeamDep, 
    user: MemberOrManagerDep,
):
    
    members_list = await team_service_dep.get_team_users(team, user)
    return members_list
    

# tasks crud

@router.post("/{team_id}/tasks")
async def create_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: ManagerDep,
    data: TaskCreate
):
    return await task_service_dep.create_task(data, team, user)
    

@router.get("/{team_id}/tasks")
async def read_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: MemberOrManagerDep,
):
    return await task_service_dep.get_all_tasks(team, user)


@router.get("/{team_id}/tasks/{task_id}")
async def read_task(
    team: TeamDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
):
    return await task_service_dep.get_task(task, team, user)

@router.patch("/{team_id}/tasks/{task_id}")
async def update_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
    data: TaskUpdate
):
    await task_service_dep.update_task(data, task, user, team)

@router.delete("/{team_id}/tasks/{task_id}")
async def delete_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep
):
    await task_service_dep.delete_task(task, user, team)

# meetings crud

@router.post("/{team_id}/meetings")
async def create_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingCreate
): 
    await meeting_service_dep.create_meeting(data, team, user)
        

@router.get("/{team_id}/meetings")
async def read_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting_service_dep: MeetingServiceDep,
):
    return await meeting_service_dep.get_meetings(team, user)

@router.get("/{team_id}/meetings/{meeting_id}")
async def read_meeting(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
): 
    return await meeting_service_dep.get_meeting(meeting, team, user)

@router.patch("/{team_id}/meetings/{meeting_id}")
async def update_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
    data: MeetingUpdate
): 
    return await meeting_service_dep.update(meeting, team, data, user)
    

@router.delete("/{team_id}/meetings/{meeting_id}")
async def delete_meetings(
    team: TeamDep,
    user: ManagerDep,
    meeting: MeetingDep,
    meeting_service_dep: MeetingServiceDep,
):
    await meeting_service_dep.delete(meeting, team, user)

@router.post("/{team_id}/tasks/{task_id}/comments")
async def write_comment(
    comment_data: CommentCreate,
    comment_dep: CommentServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
):

    return await comment_dep.create_comment(comment_data, user, task, team)


@router.get("/{team_id}/tasks/{task_id}/comments")
async def read_comments(
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    task: TaskDep,
    team: TeamDep
): 
    
    return await comment_service.get_comments(task, user, team)

@router.patch("/{team_id}/tasks/{task_id}/comments/{comment_id}")
async def edit_comment(
    
    comment_data: CommentUpdate,
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    team: TeamDep,
    task: TaskDep,
    comment: CommentDep
): 
    

    return await comment_service.update(comment_data, comment, task, user, team)

@router.delete("/{team_id}/tasks/{task_id}/comments/{comment_id}")
async def delete_comment(
    comment_service: CommentServiceDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    team: TeamDep,
    comment: CommentDep
): 
    
    await comment_service.delete(comment, task, user, team)



@router.post("/{team_id}/tasks/{task_id}/evaluation")
async def write_evaluation(
    evaluation_data: EvaluationCreate,
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep
):
    
    await evaluation_service_dep.create_evaluation(evaluation_data, user, team, task)

@router.get("/{team_id}/tasks/{task_id}/evaluation")
async def read_evaluation(
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep
): 
    
    return await evaluation_service_dep.get_evaluation(user, team, task)

@router.patch("/{team_id}/tasks/{task_id}/evaluation/{evaluation_id}")
async def edit_evaluation(
    evaluation: EvaluationDep,
    evaluation_data: EvaluationUpdate,
    evaluation_service_dep: EvaluationServiceDep,
    user: CurrentUserDep,
    task: TaskDep,
    team: TeamDep
): 
    
    return await evaluation_service_dep.update(evaluation_data, user, team, task, evaluation)