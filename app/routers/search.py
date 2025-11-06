# app/routers/search.py
"""
검색 API 엔드포인트 정의
"""

from fastapi import APIRouter, HTTPException
from app.services.claude_service import ClaudeService
from pydantic import BaseModel

router = APIRouter()
claude_service = ClaudeService()

class SearchRequest(BaseModel):
    query: str

@router.post("/search")
async def search_panels(request: SearchRequest):
    try:
        result = claude_service.analyze_query_with_opus(request.query)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))