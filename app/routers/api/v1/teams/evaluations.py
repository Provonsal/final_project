from fastapi import APIRouter

from app.dependencies import CurrentUserDep, EvaluationDep, EvaluationServiceDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_evaluation import EvaluationCreate
from app.schemas.update_evaluation import EvaluationUpdate


router = APIRouter()


@router.post("")
async def write_evaluation(
    evaluation_data: EvaluationCreate,
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep
):
    
    await evaluation_service_dep.create_evaluation(evaluation_data, user, team, task)

@router.get("")
async def read_evaluation(
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep
): 
    
    return await evaluation_service_dep.get_evaluation(user, team, task)

@router.patch("/{evaluation_id}")
async def edit_evaluation(
    evaluation: EvaluationDep,
    evaluation_data: EvaluationUpdate,
    evaluation_service_dep: EvaluationServiceDep,
    user: CurrentUserDep,
    task: TaskDep,
    team: TeamDep
): 
    
    return await evaluation_service_dep.update(evaluation_data, user, team, task, evaluation)