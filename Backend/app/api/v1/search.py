# app/routers/search.py (DB 연동 버전)

from fastapi import APIRouter, HTTPException
from app.services.claude_service import ClaudeService
from pydantic import BaseModel
from typing import List, Dict, Any # 타입 힌트 추가
import time
# ⚠️ DB 연동을 위해 database 유틸리티 임포트
from app.utils.database import execute_fetch_query 

router = APIRouter()
claude_service = ClaudeService()

class SearchRequest(BaseModel):
    query: str

# (⚠️ 경고: load_mock_data 함수 및 목 데이터 필터링 로직은 삭제되었습니다.)

@router.post("/search")
async def search_panels(request: SearchRequest):
    start_time = time.time()
    
    try:
        # 1. 쿼리 분석 (Haiku)
        analysis_result = claude_service.analyze_query(request.query)
        
        if not analysis_result.get('success'):
            return {"analysis": analysis_result, "data": []}

        conditions_json = analysis_result.get('data', {})
        
        # 2. SQL 생성 (Haiku)
        sql_generation_result = claude_service.generate_sql(
            analyzed_query=conditions_json
        )
        
        sql_query = sql_generation_result.get('sql_query')
        if not sql_query:
             raise ValueError("SQL generation failed.")

        # 3. (★★★★★ 핵심 변경 ★★★★★)
        # 생성된 SQL 쿼리를 실제 PostgreSQL DB에 실행하여 결과를 가져옵니다.
        filtered_panels: List[Dict[str, Any]] = await execute_fetch_query(sql_query)
        
        # 4. 인사이트 추출 (Haiku)
        insight_result = None
        if filtered_panels: 
            insight_result = claude_service.extract_insights(
                panel_data=filtered_panels,
                original_query=request.query
            )

        # 5. 최종 결과 반환 및 시간 계산
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        
        return {
            "analysis": analysis_result, 
            "generated_sql": sql_generation_result,
            "hidden_insights": insight_result,
            "data": filtered_panels, # 키 이름도 data로 복원
            "count": len(filtered_panels),
            "total_response_time_seconds": total_response_time
        }

    except ConnectionError as e:
        # DB 연결 실패 시 503 Service Unavailable 반환
        raise HTTPException(status_code=503, detail=f"데이터베이스 연결 오류: {e}")
    except Exception as e:
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred: {str(e)}", 
            headers={"X-Response-Time-Seconds": str(total_response_time)}
        )