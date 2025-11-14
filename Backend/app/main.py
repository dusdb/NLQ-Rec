# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v1.search import router as search_router
from app.utils.database import create_db_pool, close_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 서버 시작/종료 시 실행되는 lifespan 이벤트
    """
    # 시작 시: DB 연결 풀 생성
    print("🚀 서버 시작 중...")
    await create_db_pool()
    
    yield  # 서버 실행 중
    
    # 종료 시: DB 연결 풀 닫기
    print("🛑 서버 종료 중...")
    await close_db_pool()


# FastAPI 앱 생성
app = FastAPI(
    title="Panel Search System",
    description="자연어 기반 패널 검색 및 추출 시스템",
    version="1.0.0",
    lifespan=lifespan  # ⭐ 중요: lifespan 연결
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경: 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search_router, prefix="/api/v1", tags=["Search"])


# 헬스체크 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "Panel Search System API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}