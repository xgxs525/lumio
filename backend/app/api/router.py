from fastapi import APIRouter

from app.api.routes import (
    admin,
    ai,
    auth,
    billing,
    chat,
    documents,
    drive,
    file_ai,
    files,
    folders,
    health,
    integrations,
    jobs,
    knowledge,
    models,
    share,
    tags,
    tasks,
    team,
    templates,
    usage,
    users,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(files.router)
api_router.include_router(folders.router)
api_router.include_router(tasks.router)
api_router.include_router(templates.router)
api_router.include_router(ai.router)
api_router.include_router(chat.router)
api_router.include_router(workspaces.router)
api_router.include_router(usage.router)
api_router.include_router(admin.router)
api_router.include_router(integrations.router)
api_router.include_router(billing.router)
api_router.include_router(drive.router)
api_router.include_router(file_ai.router)
api_router.include_router(documents.router)
api_router.include_router(knowledge.router)
api_router.include_router(jobs.router)
api_router.include_router(team.router)
api_router.include_router(share.router)
api_router.include_router(tags.router)
api_router.include_router(models.router)
