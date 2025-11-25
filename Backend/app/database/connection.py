# Backend/app/database/connection.py

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

db_pool = None

async def create_db_pool():
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, settings.DB_POOL_SIZE,
            **settings.db_config
        )
        logger.info("DB Connection Pool Created")
    except Exception as e:
        logger.error(f"Pool Creation Failed: {e}")
        raise

async def close_db_pool():
    global db_pool
    if db_pool:
        db_pool.closeall()
        logger.info("DB Connection Pool Closed")

class DatabaseConnection:
    
    @staticmethod
    @contextmanager
    def get_connection():

        global db_pool
        conn = None
        try:
            if not db_pool:
                conn = psycopg2.connect(**settings.db_config)
            else:
                conn = db_pool.getconn()
                
            if conn.closed:
                if db_pool:
                    db_pool.putconn(conn, close=True)
                    conn = db_pool.getconn() 
                else:
                    conn = psycopg2.connect(**settings.db_config)

            yield conn
            conn.commit()
            
        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"❌ DB Transaction Error: {e}")
            raise
        finally:
            if conn and db_pool:
                try:
                    db_pool.putconn(conn) 
                except Exception:
                    pass 
            elif conn:
                conn.close()

    @staticmethod
    def execute_query(sql: str, params: tuple = None, fetch_all: bool = True) -> List[Dict[str, Any]]:
        with DatabaseConnection.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                if fetch_all:
                    return [dict(row) for row in cur.fetchall()]
                else:
                    res = cur.fetchone()
                    return dict(res) if res else {}