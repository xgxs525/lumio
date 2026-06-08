from fastapi import APIRouter

from app.api.routes import ai, files, health, tasks, templates

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(files.router)
api_router.include_router(tasks.router)
api_router.include_router(templates.router)
api_router.include_router(ai.router)
