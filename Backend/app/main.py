"""
FastAPI 서버 기본 환경 설정 코드
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers import search

settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="자연어 기반 패널 검색 및 추출 시스템 API"
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search.router, prefix="/api/v1")


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Panel Search System API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": settings.app_name
    }