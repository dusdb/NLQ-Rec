# app/api/v1/endpoints/health.py

"""
헬스체크 엔드포인트
DB 연결, AI 모델 상태 확인
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.config.settings import get_settings
from app.database.connection import DatabaseConnection
from app.utils.database import _pool
from app.services.search import vector_service

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
async def health_check():
    overall_status = "healthy"

    db_status = "unknown"
    pgvector_status = "unknown"
    pool_info = {}
    
    try:
        db_ok = DatabaseConnection.test_connection()
        db_status = "healthy" if db_ok else "unhealthy"
        
        if not db_ok:
            overall_status = "unhealthy"
        
        pgvector_ok = DatabaseConnection.check_pgvector_extension()
        pgvector_status = "enabled" if pgvector_ok else "disabled"

        if _pool is not None:
            pool_info = {
                "pool_size": _pool.get_size(),
                "free_connections": _pool.get_idle_size()
            }
    
    except Exception as e:
        db_status = f"error: {str(e)}"
        overall_status = "unhealthy"
    
    ai_model_status = {
        "loaded": False,
        "model_name": vector_service.model_name,
        "embedding_dim": vector_service.embedding_dim
    }
    
    try:
        if vector_service._model is not None:
            ai_model_status["loaded"] = True
            ai_model_status["status"] = "ready"
        else:
            ai_model_status["status"] = "not_loaded"
            ai_model_status["message"] = "Model will load on first use"
    
    except Exception as e:
        ai_model_status["status"] = "error"
        ai_model_status["error"] = str(e)
        overall_status = "degraded"
    
    vector_service_status = {"ready": False}
    
    try:
        test_embedding = vector_service.get_embedding("테스트")
        
        if len(test_embedding) == vector_service.embedding_dim:
            vector_service_status = {
                "ready": True,
                "status": "operational",
                "test_passed": True
            }
        else:
            vector_service_status = {
                "ready": False,
                "status": "error",
                "error": f"Dimension mismatch: {len(test_embedding)} != {vector_service.embedding_dim}"
            }
            overall_status = "degraded"
    
    except Exception as e:
        vector_service_status = {
            "ready": False,
            "status": "error",
            "error": str(e)
        }
        overall_status = "degraded"

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version,
        "database": {
            "postgres": db_status,
            "pgvector": pgvector_status,
            **pool_info
        },
        "ai_services": {
            "model": ai_model_status,
            "vector_search": vector_service_status
        },
        "features": {
            "search_modes": ["rdb", "vector", "hybrid"],
            "models": {
                "query_analysis": settings.CLAUDE_QUERY_ANALYSIS_MODEL,
                "sql_generation": settings.CLAUDE_SQL_GENERATION_MODEL,
                "insight_extraction": settings.CLAUDE_INSIGHT_EXTRACTION_MODEL
            },
            "prompt_caching": settings.enable_prompt_caching
        },
        "endpoints": {
            "search": "POST /api/v1/search",
            "report": "POST /api/v1/generate-report",
            "vector": "POST /api/v1/vector",
            "debug": "GET /api/v1/debug/*",
            "health": "GET /api/v1/health"
        }
    }

    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response)
    
    return response


@router.get("/health/simple")
async def simple_health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }