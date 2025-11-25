# app/utils/database.py

import asyncpg
import ssl
from typing import List, Dict, Any
from app.config.settings import get_settings

settings = get_settings()

_pool: asyncpg.Pool = None

async def create_db_pool():
    """
    서버 시작 시 DB 연결 풀(Pool)을 생성합니다.
    """
    global _pool
    if _pool is None:
        try:
            # ✅ Neon용 SSL Context
            ssl_context = None
            if settings.POSTGRES_HOST != "localhost":
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            _pool = await asyncpg.create_pool(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                min_size=1,
                max_size=10,
                ssl=ssl_context,
                timeout=30,
                command_timeout=30
            )
            print("✅ Database connection pool created successfully.")
        except Exception as e:
            print(f"❌ Database connection pool creation failed: {e}")
            raise ConnectionError(f"DB 풀 생성 실패: {e}")

async def close_db_pool():
    """
    서버 종료 시 DB 연결 풀(Pool)을 닫습니다.
    """
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("✅ Database connection pool closed.")


async def execute_fetch_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    SQL 쿼리를 실행하고 결과를 딕셔너리 리스트 형태로 반환합니다.
    """
    global _pool
    
    if _pool is None:
        print("❌ DB Pool is not initialized. Check server startup.")
        raise ConnectionError("DB 연결 풀이 초기화되지 않았습니다.")

    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch(sql_query)
            results = [dict(row) for row in rows]
            return results
    except Exception as e:
        print(f"❌ SQL Execution Error: {e}")
        raise ConnectionError(f"쿼리 실행 중 오류: {e}")