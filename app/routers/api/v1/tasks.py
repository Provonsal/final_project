import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CommentServiceDep, EvaluationServiceDep, MemberOrManagerDep, TaskServiceDep, TeamServiceDep, CurrentUserDep
from app.models.RoleEnum import RoleEnum
from app.models.models import User
from app.schemas.create_comment import CommentCreate
from app.schemas.create_evaluation import EvaluationCreate
from app.schemas.update_comment import CommentUpdate
from app.schemas.update_evaluation import EvaluationUpdate
from app.services.task_service import TaskService
from app.services.team_service import TeamService


router = APIRouter(
    prefix="/tasks",  # Все пути будут начинаться с /users
    tags=["tasks"],    # Тег для документации
    responses={404: {"description": "Not found"}}  # Общие ответы
)

# async def check_user_identity(task_id: uuid.UUID, current_user: User, task_dep: TaskService, team_dep: TeamService):
#     # Check if the user is a member of the task's team
#     task = await task_dep.get_task(task_id)
#     if current_user.role not in (RoleEnum.MEMBER, RoleEnum.MANAGER):
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a member to comment on this task.")
    
#     # Assuming task has a 'connected_to_team' attribute
#     if not await team_dep.belongs_to_team(current_user.id, task.team_id):
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be part of the task's team to comment.")


# @router.post("/{task_id}/comments")
# async def write_comment(
#     task_id: uuid.UUID,
#     comment_data: CommentCreate,
#     current_user: MemberOrManagerDep,
#     comment_dep: CommentServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ):

#     await check_user_identity(task_id, current_user, task_dep, team_dep)

#     await comment_dep.create_comment(comment_data)


# @router.get("/{task_id}/comments")
# async def read_comments(
#     task_id: uuid.UUID,
#     current_user: MemberOrManagerDep,
#     comment_dep: CommentServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ): 

#     await check_user_identity(task_id, current_user, task_dep, team_dep)
    
#     return await comment_dep.get_comments(task_id)

# @router.patch("/{task_id}/comments/{comment_id}")
# async def edit_comment(
#     task_id: uuid.UUID,
#     comment_id: uuid.UUID,
#     comment_data: CommentUpdate,
#     current_user: MemberOrManagerDep,
#     comment_dep: CommentServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ): 
#     await check_user_identity(task_id, current_user, task_dep, team_dep)

#     return await comment_dep.update(comment_id, comment_data)

# @router.delete("/{task_id}/comments/{comment_id}")
# async def delete_comment(
#     task_id: uuid.UUID,
#     comment_id: uuid.UUID,
#     current_user: MemberOrManagerDep,
#     comment_dep: CommentServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ): 
#     await check_user_identity(task_id, current_user, task_dep, team_dep)
#     await comment_dep.delete(comment_id)



# @router.post("/{task_id}/evaluation")
# async def write_evaluation(
#     task_id: uuid.UUID,
#     evaluation_data: EvaluationCreate,
#     current_user: CurrentUserDep,
#     evaluation_dep: EvaluationServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ):
#     await check_user_identity(task_id, current_user, task_dep, team_dep)
#     await evaluation_dep.create_evaluation(evaluation_data)

# @router.get("/{task_id}/evaluation")
# async def read_evaluation(
#     task_id: uuid.UUID,
#     current_user: CurrentUserDep,
#     evaluation_dep: EvaluationServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ): 
#     await check_user_identity(task_id, current_user, task_dep, team_dep)
#     return await evaluation_dep.get_evaluation(task_id)

# @router.patch("/{task_id}/evaluation/{evaluation_id}")
# async def edit_evaluation(
#     task_id: uuid.UUID,
#     evaluation_id: uuid.UUID,
#     evaluation_data: EvaluationUpdate,
#     current_user: CurrentUserDep,
#     evaluation_dep: EvaluationServiceDep,
#     task_dep: TaskServiceDep,
#     team_dep: TeamServiceDep
# ): 
#     await check_user_identity(task_id, current_user, task_dep, team_dep)
#     return await evaluation_dep.update(evaluation_id, evaluation_data)



