# app/utils/database.py

import asyncpg
from typing import List, Dict, Any
from app.core.config import get_settings

settings = get_settings()

_pool = None

async def get_db_connection_pool():
    """DB 연결 풀(Pool)을 가져옵니다. 없으면 새로 생성합니다."""
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                min_size=1,
                max_size=10
            )
            print("✅ Database connection pool created successfully.")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            # 여기서 ConnectionError를 raise해야 search.py에서 503으로 감지됨
            raise ConnectionError(f"DB 연결 실패: {e}")
    return _pool


async def execute_fetch_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    SQL 쿼리를 실행하고 결과를 딕셔너리 리스트 형태로 반환합니다.
    """
    try:
        pool = await get_db_connection_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_query)
            results = [dict(row) for row in rows]
            print(f"✅ Query executed successfully. Rows fetched: {len(results)}")
            return results
    except ConnectionError as ce:
        # DB 연결 오류 (search.py에서 503으로 변환)
        print(f"⚠️ ConnectionError: {ce}")
        raise
    except Exception as e:
        # SQL 오류나 기타 실행 중 오류
        print(f"❌ SQL Execution Error: {e}")
        raise ConnectionError(f"쿼리 실행 중 오류: {e}")
