from fastapi import APIRouter
from . import teams, tasks, meetings, comments, evaluations

router = APIRouter(prefix="/teams", tags=["teams"], responses={404: {"description": "Not found"}})

router.include_router(teams.router)                                                      # /teams
router.include_router(tasks.router,       prefix="/{team_id}/tasks",       tags=["tasks"])
router.include_router(meetings.router,    prefix="/{team_id}/meetings",    tags=["meetings"])
router.include_router(comments.router,    prefix="/{team_id}/tasks/{task_id}/comments", tags=["comments"])
router.include_router(evaluations.router, prefix="/{team_id}/tasks/{task_id}/evaluation", tags=["evaluations"])