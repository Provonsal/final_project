from fastapi import APIRouter
from app.dependencies import TaskDep, TeamDep, TaskServiceDep, ManagerDep, MemberOrManagerDep
from app.schemas.task_create import TaskCreate
from app.schemas.task_update import TaskUpdate

router = APIRouter()

@router.post("")
async def create_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: ManagerDep,
    data: TaskCreate
):
    return await task_service_dep.create_task(data, team, user)
    

@router.get("")
async def read_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: MemberOrManagerDep,
):
    return await task_service_dep.get_all_tasks(team, user)


@router.get("/{task_id}")
async def read_task(
    team: TeamDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
):
    return await task_service_dep.get_task(task, team, user)

@router.patch("/{task_id}")
async def update_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
    data: TaskUpdate
):
    await task_service_dep.update_task(data, task, user, team)

@router.delete("/{task_id}")
async def delete_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep
):
    await task_service_dep.delete_task(task, user, team)