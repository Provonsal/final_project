from fastapi import APIRouter

from app.dependencies import EvaluationDep, EvaluationServiceDep, ManagerDep, MemberOrManagerDep, TaskDep, TeamDep
from app.schemas.create_evaluation import CreateEvaluation
from app.schemas.response_evaluation import ResponseEvaluationSchema
from app.schemas.update_evaluation import UpdateEvaluation


router = APIRouter()


@router.post("")
async def write_evaluation(
    evaluation_data: CreateEvaluation,
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: ManagerDep,
    team: TeamDep
):
    
    evaluation =  await evaluation_service_dep.create_evaluation(evaluation_data, user, team, task)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )

@router.get("")
async def read_evaluation(
    evaluation_service_dep: EvaluationServiceDep,
    task: TaskDep,
    user: MemberOrManagerDep,
    team: TeamDep,
    evaluation: EvaluationDep
): 
    
    evaluation = await evaluation_service_dep.get_evaluation(user, team, task, evaluation)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )

@router.patch("/{evaluation_id}")
async def edit_evaluation(
    evaluation: EvaluationDep,
    evaluation_data: UpdateEvaluation,
    evaluation_service_dep: EvaluationServiceDep,
    user: ManagerDep,
    task: TaskDep,
    team: TeamDep
): 
    
    evaluation = await evaluation_service_dep.update(evaluation_data, user, team, task, evaluation)
    return ResponseEvaluationSchema(
        id=evaluation.id,
        rate=evaluation.rate,
        author=evaluation.rater
    )