# app/api/v1/search.py (프론트 연동 버전 - 패널 데이터 변환 추가)

from fastapi import APIRouter, HTTPException
from app.services.claude_service import ClaudeService
from pydantic import BaseModel
from typing import List, Dict, Any
import time
from datetime import datetime
from app.utils.database import execute_fetch_query 

router = APIRouter()
claude_service = ClaudeService()

class SearchRequest(BaseModel):
    query: str


def convert_panel_to_frontend_format(panel: Dict[str, Any]) -> Dict[str, Any]:
    """
    DB 원본 패널 데이터를 프론트엔드 기대 형식으로 변환
    
    DB 형식 → 프론트엔드 형식
    - panel_id → id
    - birth_year → age (계산)
    - region_main, region_sub → location (결합)
    - job_category → job
    - interests (있으면 사용, 없으면 기본값)
    - bio (있으면 사용, 없으면 생성)
    """
    current_year = datetime.now().year
    
    # 나이 계산 (birth_year가 없으면 기본값 1990 사용)
    birth_year = panel.get('birth_year', 1990)
    age = current_year - birth_year
    
    # 지역 정보 결합 (region_main + region_sub)
    region_main = panel.get('region_main', '').strip()
    region_sub = panel.get('region_sub', '').strip()
    location = f"{region_main} {region_sub}".strip() if region_main else '정보없음'
    
    # 직업
    job = panel.get('job_category', '미기재')
    
    # 관심사 (DB에 있으면 사용, 없으면 기본값)
    interests = panel.get('interests', ['기타'])
    if isinstance(interests, str):
        interests = [interests]  # 문자열이면 배열로 변환
    
    # 자기소개 (DB에 있으면 사용, 없으면 자동 생성)
    bio = panel.get('bio')
    if not bio:
        bio = f"{job}입니다."
        if interests and interests != ['기타']:
            bio += f" {', '.join(interests)}에 관심이 많습니다."
    
    return {
        "id": panel.get('panel_id', 'P-Unknown'),
        "age": age,
        "gender": panel.get('gender', '미상'),
        "location": location,
        "job": job,
        "interests": interests,
        "bio": bio
    }


@router.post("/search")
async def search_panels(request: SearchRequest):
    start_time = time.time()
    
    try:
        # 1. 쿼리 분석 (Opus)
        analysis_result = claude_service.analyze_query(request.query)
        
        if not analysis_result.get('success'):
            return {
                "totalCount": 0,
                "filterTags": [],
                "samplePanels": [],
                "currentFullPanelList": [],
                "recommendations": [],
                "strategyCards": [],
                "control": {
                    "status": "error",
                    "message": "쿼리 분석 실패",
                    "searchQuery": request.query
                },
                "analysis": analysis_result,
                "data": []
            }

        conditions_json = analysis_result.get('data', {})
        
        # 2. SQL 생성 (Haiku)
        sql_generation_result = claude_service.generate_sql(
            analyzed_query=conditions_json
        )
        
        sql_query = sql_generation_result.get('sql_query')
        if not sql_query:
            raise ValueError("SQL generation failed.")

        # 3. DB 쿼리 실행
        filtered_panels: List[Dict[str, Any]] = await execute_fetch_query(sql_query)
        
        # ⭐ 3-1. DB 데이터를 프론트엔드 형식으로 변환
        converted_panels = [convert_panel_to_frontend_format(panel) for panel in filtered_panels]
        
        # 4. 인사이트 추출 (Opus) - 원본 DB 데이터 사용
        insight_result = None
        if filtered_panels: 
            insight_result = claude_service.extract_insights(
                panel_data=filtered_panels,  # 원본 데이터로 인사이트 추출
                original_query=request.query
            )

        # 5. 프론트 기대 형식으로 변환
        # filterTags 생성
        filter_tags = []
        search_cond = conditions_json.get('search_conditions', {})
        
        if search_cond.get('age_range'):
            age_min = search_cond['age_range'].get('min')
            age_max = search_cond['age_range'].get('max')
            if age_min and age_max:
                # age_min을 10으로 나눈 몫에 10을 곱해서 '30대', '40대' 형식으로
                decade = (age_min // 10) * 10
                filter_tags.append({
                    "label": "나이",
                    "value": f"{age_min}-{age_max}세",
                    "queryPart": f"{decade}대"
                })
        
        if search_cond.get('gender'):
            filter_tags.append({
                "label": "성별",
                "value": search_cond['gender'],
                "queryPart": search_cond['gender']
            })
        
        if search_cond.get('location'):
            filter_tags.append({
                "label": "지역",
                "value": search_cond['location'],
                "queryPart": search_cond['location']
            })
        
        if search_cond.get('district'):
            filter_tags.append({
                "label": "상세지역",
                "value": search_cond['district'],
                "queryPart": search_cond['district']
            })
        
        if search_cond.get('job'):
            filter_tags.append({
                "label": "직업",
                "value": search_cond['job'],
                "queryPart": search_cond['job']
            })

        # recommendations 생성 (인사이트에서)
        recommendations = []
        if insight_result and insight_result.get('success'):
            insights = insight_result.get('data', {})
            # 숨겨진 패턴을 추천으로 변환
            for pattern in insights.get('hidden_patterns', [])[:2]:
                recommendations.append({
                    "id": f"rec-{pattern.get('feature', '').replace(' ', '-')}",
                    "text": pattern.get('insight', ''),
                    "action": {
                        "buttonText": f"+ '{pattern.get('feature')}' 조건 추가",
                        "data": {
                            "type": "insight",
                            "value": pattern.get('value', ''),
                            "queryPart": pattern.get('feature', '')
                        }
                    }
                })

        # strategyCards 생성 (인사이트에서)
        strategy_cards = []
        if insight_result and insight_result.get('success'):
            insights = insight_result.get('data', {})
            summary = insights.get('summary', '')
            if summary:
                strategy_cards.append({
                    "id": "strategy-001",
                    "strategyName": "AI 기반 타겟 분석 전략",
                    "coreTarget": summary[:100],
                    "strategyType": "데이터 분석",
                    "keywords": ", ".join(insights.get('statistics', {}).keys()) if insights.get('statistics') else "분석",
                    "effect": "정확한 타겟팅",
                    "report": insights
                })

        # ⭐ samplePanels (처음 3개) - 변환된 데이터 사용
        sample_panels = converted_panels[:3]

        # 최종 응답
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        
        return {
            "totalCount": len(converted_panels),
            "filterTags": filter_tags,
            "samplePanels": sample_panels,  # ⭐ 변환된 데이터
            "currentFullPanelList": converted_panels,  # ⭐ 변환된 데이터
            "recommendations": recommendations,
            "strategyCards": strategy_cards,
            "control": {
                "status": "success",
                "message": "검색 완료",
                "searchQuery": request.query,
                "timestamp": int(time.time())
            },
            "analysis": analysis_result,
            "generated_sql": sql_generation_result,
            "hidden_insights": insight_result,
            "data": filtered_panels,  # 원본 DB 데이터 (디버깅용)
            "count": len(converted_panels),
            "total_response_time_seconds": total_response_time
        }

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"데이터베이스 연결 오류: {e}")
    except Exception as e:
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred: {str(e)}", 
            headers={"X-Response-Time-Seconds": str(total_response_time)}
        )