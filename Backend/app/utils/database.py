# app/utils/database.py

import asyncpg
from typing import List, Dict, Any
from app.config.settings import get_settings

settings = get_settings()

_pool = None

async def get_db_connection_pool():
    """DB ?곌껐 ?(Pool)??媛?몄샃?덈떎. ?놁쑝硫??덈줈 ?앹꽦?⑸땲??"""
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
            print("??Database connection pool created successfully.")
        except Exception as e:
            print(f"??Database connection failed: {e}")
            # ?ш린??ConnectionError瑜?raise?댁빞 search.py?먯꽌 503?쇰줈 媛먯???
            raise ConnectionError(f"DB ?곌껐 ?ㅽ뙣: {e}")
    return _pool


async def execute_fetch_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    SQL 荑쇰━瑜??ㅽ뻾?섍퀬 寃곌낵瑜??뺤뀛?덈━ 由ъ뒪???뺥깭濡?諛섑솚?⑸땲??
    """
    try:
        pool = await get_db_connection_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_query)
            results = [dict(row) for row in rows]
            print(f"??Query executed successfully. Rows fetched: {len(results)}")
            return results
    except ConnectionError as ce:
        # DB ?곌껐 ?ㅻ쪟 (search.py?먯꽌 503?쇰줈 蹂??
        print(f"?좑툘 ConnectionError: {ce}")
        raise
    except Exception as e:
        # SQL ?ㅻ쪟??湲고? ?ㅽ뻾 以??ㅻ쪟
        print(f"??SQL Execution Error: {e}")
        raise ConnectionError(f"荑쇰━ ?ㅽ뻾 以??ㅻ쪟: {e}")
