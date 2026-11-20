from unittest import result

from fastapi import APIRouter

from app.dependencies import CommentDep, CommentServiceDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_comment import CreateComment
from app.schemas.response_comment import ResponseCommentSchema
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.update_comment import UpdateComment


router = APIRouter()


@router.post("")
async def write_comment(
    comment_data: CreateComment,
    comment_dep: CommentServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
):
    new_comment = await comment_dep.create_comment(comment_data, user, task, team)
    return ResponseCommentSchema(
        id=new_comment.id,
        created_at=new_comment.created_at.isoformat(),
        text=new_comment.text,
        author=new_comment.author
    )


@router.get("")
async def read_comments(
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    task: TaskDep,
    team: TeamDep
): 
    
    comments = await comment_service.get_comments(task, user, team)
    return [ResponseCommentSchema(
        id=comment.id,
        created_at=comment.created_at.isoformat(),
        text=comment.text,
        author=comment.author
    ) for comment in comments]

@router.patch("/{comment_id}")
async def edit_comment(
    
    comment_data: UpdateComment,
    user: MemberOrManagerDep,
    comment_service: CommentServiceDep,
    team: TeamDep,
    task: TaskDep,
    comment: CommentDep
): 
    

    comment = await comment_service.update(comment_data, comment, task, user, team)
    return ResponseCommentSchema(
        id=comment.id,
        created_at=comment.created_at.isoformat(),
        text=comment.text,
        author=comment.author
    )

@router.delete("/{comment_id}")
async def delete_comment(
    comment_service: CommentServiceDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    team: TeamDep,
    comment: CommentDep
): 
    
    result = await comment_service.delete(comment, task, user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()