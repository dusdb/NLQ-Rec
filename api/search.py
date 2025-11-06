from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.models.schemas import (
    SearchRequest, 
    QueryAnalysisResponse,
    SQLGenerationResponse,
    InsightsResponse,
    SearchResponse
)
from app.services.claude_service import claude_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/analyze", response_model=QueryAnalysisResponse)
async def analyze_query(request: SearchRequest):
    """
    자연어 질의 분석 엔드포인트
    
    - Opus 모델을 사용하여 사용자 질의를 구조화된 데이터로 변환
    - 검색 조건, 의도, 복잡도, 키워드 추출
    """
    try:
        result = claude_service.analyze_query_with_opus(request.query)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "질의 분석 실패")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"질의 분석 중 오류 발생: {str(e)}"
        )


@router.post("/generate-sql", response_model=SQLGenerationResponse)
async def generate_sql(analyzed_query: Dict[str, Any]):
    """
    SQL 쿼리 생성 엔드포인트
    
    - Haiku 모델을 사용하여 분석된 질의를 SQL로 변환
    """
    try:
        result = claude_service.generate_sql_with_haiku(analyzed_query)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "SQL 생성 실패")
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SQL 생성 중 오류 발생: {str(e)}"
        )


@router.post("/extract-insights", response_model=InsightsResponse)
async def extract_insights(panel_data: list):
    """
    인사이트 추출 엔드포인트
    
    - Opus 모델을 사용하여 패널 데이터에서 숨겨진 공통 특성 추출
    """
    try:
        if not panel_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="패널 데이터가 비어있습니다"
            )
        
        result = claude_service.extract_insights_with_opus(panel_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "인사이트 추출 실패")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인사이트 추출 중 오류 발생: {str(e)}"
        )


@router.post("/full", response_model=SearchResponse)
async def full_search(request: SearchRequest):
    """
    전체 검색 파이프라인 엔드포인트 (통합 API)
    
    1. 자연어 질의 분석 (Opus)
    2. SQL 쿼리 생성 (Haiku)
    3. [DB 연동 후] SQL 실행
    4. [DB 연동 후] 결과 검증 (Sonnet)
    5. 인사이트 추출 (Opus)
    
    현재는 DB 연동 전이므로 1, 2번만 실행하고 목업 데이터로 테스트
    """
    try:
        # Step 1: 질의 분석
        analysis_result = claude_service.analyze_query_with_opus(request.query)
        
        if not analysis_result["success"]:
            return SearchResponse(
                success=False,
                error=f"질의 분석 실패: {analysis_result.get('error')}"
            )
        
        # Step 2: SQL 생성
        sql_result = claude_service.generate_sql_with_haiku(
            analysis_result["data"]
        )
        
        if not sql_result["success"]:
            return SearchResponse(
                success=False,
                query_analysis=analysis_result["data"],
                error=f"SQL 생성 실패: {sql_result.get('error')}"
            )
        
        # Step 3: [TODO] DB 연동 후 SQL 실행
        # 현재는 목업 데이터로 대체
        mock_results = [
            {
                "panel_id": "P001",
                "gender": "남성",
                "age": 25,
                "location": "서울",
                "job": "IT"
            },
            {
                "panel_id": "P002",
                "gender": "남성",
                "age": 28,
                "location": "서울",
                "job": "IT"
            }
        ]
        
        # Step 4: [TODO] 결과 검증 (Sonnet)
        
        # Step 5: 인사이트 추출
        insights_result = claude_service.extract_insights_with_opus(mock_results)
        
        return SearchResponse(
            success=True,
            query_analysis=analysis_result["data"],
            sql_query=sql_result["sql_query"],
            results_count=len(mock_results),
            results=mock_results,
            insights=insights_result.get("data") if insights_result["success"] else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류 발생: {str(e)}"
        )