"""
Sales AI Automation API Gateway
FastAPI 應用程式主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from config import settings
from routers import conversations, leads, analytics, health

app = FastAPI(
    title="Sales AI Automation API",
    description="銷售 AI 自動化系統 API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(leads.router, prefix="/api/v1", tags=["Leads"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Sales AI Automation API",
        version="2.0.0",
        description="銷售 AI 自動化系統 API",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
