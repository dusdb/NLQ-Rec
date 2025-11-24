# app/main.py

import time
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config.settings import get_settings

from app.core.startup import startup_database, startup_ai_model, shutdown_resources

from app.middlewares import setup_cors

from app.api.v1.search import router as search_router
from app.api.v1.endpoints import debug_router, health_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_time = time.time()
    print("🚀 서버 시작 중...")
    
    await startup_database()
    
    await startup_ai_model()
    
    elapsed = round(time.time() - start_time, 2)
    print(f"✅ 서버 준비 완료 (총 소요시간: {elapsed}초)")
    
    yield
    
    await shutdown_resources()


app = FastAPI(
    title=settings.app_name,
    description="자연어 기반 패널 검색 및 추출 시스템",
    version=settings.app_version,
    lifespan=lifespan
)

setup_cors(app)

app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(debug_router, prefix="/api/v1/debug", tags=["Debug"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "simple_health": "/api/v1/health/simple",
            "search": "/api/v1/search",
            "report": "/api/v1/generate-report",
            "vector": "/api/v1/vector"
        },
        "features": {
            "search_modes": ["rdb", "vector", "hybrid"],
            "vector_search": True,
            "hybrid_search": True,
            "ai_insights": True,
            "prompt_caching": settings.enable_prompt_caching
        },
        "database": {
            "type": "PostgreSQL",
            "extensions": ["pgvector"]
        }
    }