from contextlib import asynccontextmanager
import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.schema_compat import run_compat_migrations
import app.models  # noqa: F401

logger = logging.getLogger('序光.api')
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await run_compat_migrations(conn)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description='序光 AI 办公平台 API',
        version='2.0.0',
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @application.middleware('http')
    async def catch_exceptions_middleware(request: Request, call_next):
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                'Unhandled exception %s %s',
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content={'detail': '服务器内部错误，请稍后重试'},
            )
        duration = perf_counter() - started_at
        response.headers['X-Process-Time'] = f'{duration:.4f}'
        if duration >= settings.slow_request_seconds:
            logger.warning(
                'Slow request %.3fs %s %s',
                duration,
                request.method,
                request.url.path,
            )
        return response

    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()

