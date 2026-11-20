from fastapi import APIRouter
from app.dependencies import TaskDep, TeamDep, TaskServiceDep, ManagerDep, MemberOrManagerDep
from app.schemas.create_task import CreateTask
from app.schemas.response_success import ResponseOperationFailure, ResponseOperationSuccess
from app.schemas.response_task import ResponseTaskSchema
from app.schemas.update_task import UpdateTask

router = APIRouter()

@router.post("")
async def create_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: ManagerDep,
    data: CreateTask
):
    task = await task_service_dep.create_task(data, team, user)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
    )
    

@router.get("")
async def read_tasks(
    task_service_dep: TaskServiceDep,
    team: TeamDep, 
    user: MemberOrManagerDep,
):
    tasks = await task_service_dep.get_all_tasks(team, user)
    return [
        ResponseTaskSchema(
            id=task.id,
            title=task.title,
            description=task.description,
            assignee_id=task.assignee,
            due_date=task.due_date.isoformat(),
            status=task.status,
            team_id=task.team_id
        ) for task in tasks
    ]


@router.get("/{task_id}")
async def read_task(
    team: TeamDep,
    user: MemberOrManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
):
    task = await task_service_dep.get_task(task, team, user)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
    )

@router.patch("/{task_id}")
async def update_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep,
    data: UpdateTask
):
    task = await task_service_dep.update_task(data, task, user, team)
    return ResponseTaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee,
        due_date=task.due_date.isoformat(),
        status=task.status,
        team_id=task.team_id
    )

@router.delete("/{task_id}")
async def delete_tasks(
    team: TeamDep,
    user: ManagerDep,
    task: TaskDep,
    task_service_dep: TaskServiceDep
):
    result = await task_service_dep.delete_task(task, user, team)
    if result:
        return ResponseOperationSuccess()
    else:
        return ResponseOperationFailure()