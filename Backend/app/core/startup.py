# app/core/startup.py

"""
서버 시작/종료 시 초기화 및 정리 로직
"""

import time
import logging
from app.utils.database import create_db_pool, close_db_pool
from app.services.search import vector_service

logger = logging.getLogger(__name__)


async def startup_database():
    logger.info("데이터베이스 연결 풀 생성 중...")
    start = time.time()
    
    await create_db_pool()
    
    elapsed = round(time.time() - start, 2)
    logger.info(f"DB 연결 완료 ({elapsed}초)")


async def startup_ai_model():
    logger.info("AI 모델 프리로딩 시작...")
    start = time.time()

    _ = vector_service.model
    
    elapsed = round(time.time() - start, 2)
    logger.info(f"AI 모델 로드 완료 ({elapsed}초)")


async def shutdown_resources():

    logger.info("서버 종료 중... 리소스 정리 시작")
    
    await close_db_pool()
    
    logger.info("모든 리소스 정리 완료")