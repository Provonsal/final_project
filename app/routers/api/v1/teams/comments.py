from fastapi import APIRouter

from app.dependencies import CommentDep, CommentServiceDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_comment import CommentCreate
from app.schemas.update_comment import CommentUpdate


router = APIRouter()


@router.post("")
async def write_comment(
    comment_data: CommentCreate,
    comment_dep: CommentServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
):

    return await comment_dep.create_comment(comment_data, user, task, team)


@router.get("")
async def read_comments(
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    task: TaskDep,
    team: TeamDep
): 
    
    return await comment_service.get_comments(task, user, team)

@router.patch("/{comment_id}")
async def edit_comment(
    
    comment_data: CommentUpdate,
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    team: TeamDep,
    task: TaskDep,
    comment: CommentDep
): 
    

    return await comment_service.update(comment_data, comment, task, user, team)

@router.delete("/{comment_id}")
async def delete_comment(
    comment_service: CommentServiceDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    team: TeamDep,
    comment: CommentDep
): 
    
    await comment_service.delete(comment, task, user, team)