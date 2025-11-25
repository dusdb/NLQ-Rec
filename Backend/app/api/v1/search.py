# app/api/v1/search.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
import json
import traceback

from app.utils.database import execute_fetch_query
from app.services.claude import claude_service
from app.services.search import search_agent

from app.database.connection import DatabaseConnection
from app.services.search import vector_service

from app.utils import (
    should_use_vector_search,
    generate_concise_strategy_name,
    get_user_friendly_query_part,
    clean_insight_text
)

from app.services.formatters import convert_panel_to_frontend_format

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    search_mode: str = "hybrid" 
    top_k: int = 100

class ReportRequest(BaseModel):
    strategyId: str
    strategyName: Optional[str] = None
    coreTarget: Optional[str] = None
    originalQuery: Optional[str] = None

@router.post("/search")
async def search_panels(request: SearchRequest):

    start_time = time.time()
    time_logs = {}
    
    converted_panels = []
    analysis_result = {}
    sql_generation_result = {}
    insight_result = {}
    search_metadata = {}
    
    try:
        print(f"\n{'='*60}")
        print(f"검색 모드: {request.search_mode.upper()}")
        print(f"검색 질의: {request.query}")
        print(f"{'='*60}\n")
        
        # ========================================
        # Step 1: 쿼리 분석 (Opus)
        # ========================================

        print("Step 1: Query analysis starting...")
        step1_start = time.time()
        
        analysis_result = claude_service.analyze_query(request.query)
        
        step1_time = round(time.time() - step1_start, 3)
        time_logs['step1_analysis'] = step1_time
        print(f"Step 1 소요시간: {step1_time}초")
        print(f"Step 1 완료: {analysis_result.get('success')}")
        
        if not analysis_result.get('success'):
            raise ValueError(f"Query analysis failed: {analysis_result.get('error', 'Unknown')}")
        
        conditions_json = analysis_result.get('data', {})
        search_conditions = conditions_json.get('search_conditions', {})
        
        extracted_count = conditions_json.get('target_count')
        target_count = extracted_count if extracted_count else request.top_k

        print(f"🎯 타겟 인원수: {target_count}명 (추출: {extracted_count}, 기본: {request.top_k})")


        # ========================================
        # Step 2: SQL 생성 (Haiku)
        # ========================================

        print("Step 2: SQL generation starting...")
        step2_start = time.time()

        sql_generation_result = claude_service.generate_sql(
            analyzed_query=conditions_json,
            target_count=target_count
        )
        
        step2_time = round(time.time() - step2_start, 3)
        time_logs['step2_sql_gen'] = step2_time
        print(f"Step 2 소요시간: {step2_time}초")
        print(f"Step 2 완료: {sql_generation_result.get('success')}")
        
        sql_query = sql_generation_result.get('sql_query')
        
        # ========================================
        # Step 3: 검색 실행 (자동 모드 결정)
        # ========================================

        print(f"Step 3: Determining optimal search strategy...")
        step3_start = time.time()

        actual_mode = request.search_mode

        if request.search_mode == "hybrid":
            needs_vector = should_use_vector_search(request.query, search_conditions)
            
            if not needs_vector:
                print(" → SQL 전용 모드로 자동 전환")
                actual_mode = "rdb"
            else:
                print("→ 하이브리드 모드 유지")
                actual_mode = "hybrid"

        print(f"Step 3: Executing {actual_mode.upper()} search...")

        if actual_mode == "rdb":
            if not sql_query: 
                raise ValueError("SQL generation failed")
            filtered_panels = await execute_fetch_query(sql_query)
            search_metadata = {
                "search_type": "rdb_only",
                "sql_executed": True,
                "reason": "structured_conditions_only" if request.search_mode == "hybrid" else "user_specified"
            }
            
        elif actual_mode == "vector":
            filtered_panels = search_agent.semantic_search(request.query, target_count)  # 🆕 변경
            search_metadata = {"search_type": "vector_only", "vector_used": True}
            
        elif actual_mode == "hybrid":
            filtered_panels = search_agent.hybrid_search(request.query, search_conditions, target_count)  # 🆕 변경
            search_metadata = {
                "search_type": "hybrid",
                "sql_executed": True, 
                "vector_used": True,
                "conditions_applied": list(search_conditions.keys())
            }

        else:
            raise ValueError(f"Invalid search_mode: {actual_mode}")

        is_fallback = False
        if not filtered_panels and actual_mode in ["rdb", "hybrid"]:
            print(f"정확한 매칭 결과 없음. 유사도 기반 검색(Vector Only)으로 전환합니다...")
            
            filtered_panels = search_agent.semantic_search(request.query, top_k=target_count)  # 🆕 변경
            is_fallback = True
            
            search_metadata = {
                "search_type": "fallback_vector",
                "original_mode": actual_mode,
                "message": "조건에 완벽히 부합하는 대상이 없어, 가장 유사한 대상을 찾았습니다."
            }

        step3_time = round(time.time() - step3_start, 3)
        time_logs['step3_search_exec'] = step3_time
        print(f"Step 3 완료: {len(filtered_panels)}명 검색됨 (Fallback: {is_fallback})")
        print(f"Step 3 소요시간: {step3_time}초")

        # ========================================
        # Step 4: 데이터 변환
        # ========================================

        print("Step 4: Converting panel data...")
        step4_start = time.time()

        converted_panels = [
            convert_panel_to_frontend_format(panel) 
            for panel in filtered_panels
        ]

        step4_time = round(time.time() - step4_start, 3)
        time_logs['step4_conversion'] = step4_time
        print(f"Step 4 소요시간: {step4_time}초")
        print(f"Step 4 완료: {len(converted_panels)}명 변환됨")
        
        # ========================================
        # Step 5, 6, 7: 인사이트 및 추천 생성
        # ========================================

        recommendations = []
        strategy_cards = []
        insights = {}
        
        try:
            print("Step 5: Extracting insights (Claude)...")
            step5_start = time.time()
            
            if converted_panels:
                print(f"{len(converted_panels)}명의 패널 분석 중...")
                
                job_stats = {}
                location_stats = {}
                age_stats = {}
                gender_stats = {}
                income_stats = {}
                car_stats = {}
                
                for p in converted_panels:
                    job = p.get('job_category', '미상')
                    job_stats[job] = job_stats.get(job, 0) + 1

                    location = p.get('region_main', '미상')
                    location_stats[location] = location_stats.get(location, 0) + 1

                    birth_year = p.get('birth_year')
                    if birth_year:
                        age = 2025 - birth_year
                        age_group = f"{(age // 10) * 10}대"
                        age_stats[age_group] = age_stats.get(age_group, 0) + 1

                    gender = p.get('gender', '미상')
                    gender_stats[gender] = gender_stats.get(gender, 0) + 1

                    income = p.get('personal_income', '미상')
                    if income and income != '미상':
                        income_stats[income] = income_stats.get(income, 0) + 1

                    car = p.get('car_brand', '미상')
                    if car and car != '미상':
                        car_stats[car] = car_stats.get(car, 0) + 1

                print(f"직업 분포: {job_stats}")
                print(f"지역 분포: {location_stats}")
                print(f"연령대 분포: {age_stats}")
                print(f"성별 분포: {gender_stats}")

                top_results_for_insight = []
                vector_results = [p for p in converted_panels if 'similarity_score' in p]

                if vector_results:
                    top_results_for_insight = sorted(
                        vector_results,
                        key=lambda x: x['similarity_score'],
                        reverse=True
                    )[:10]
                else:
                    top_results_for_insight = converted_panels[:10]

                insight_result = claude_service.extract_insights(
                    panel_data=top_results_for_insight,
                    original_query=request.query,
                    full_statistics={
                        "job_distribution": job_stats,
                        "location_distribution": location_stats,
                        "age_distribution": age_stats,
                        "gender_distribution": gender_stats,
                        "income_distribution": income_stats,
                        "car_distribution": car_stats,
                        "total_count": len(converted_panels)
                    }
                )
            else:
                print("검색 결과 0명 → 조건 완화 피드백 생성 중...")
                
                active_conditions = [k for k, v in search_conditions.items() if v is not None]
                
                insight_result = {
                    "success": True,
                    "data": {
                        "hidden_patterns": [],
                        "target_profile": {
                            "core_demographic": "검색 결과 없음",
                            "key_characteristics": [
                                f"검색 조건: {', '.join(active_conditions)}",
                                "조건 완화 필요"
                            ]
                        },
                        "statistics": {},
                        "summary": f"'{request.query}' 조건과 일치하는 패널이 없습니다. 조건을 완화하거나 다른 검색어를 시도해보세요."
                    }
                }
            
            step5_time = round(time.time() - step5_start, 3)
            time_logs['step5_insights'] = step5_time
            print(f"Step 5 소요시간: {step5_time}초")
            
            is_insight_success = insight_result.get('success', False)
            print(f"Step 5 완료: {is_insight_success}")
            
            if is_insight_success:
                insights = insight_result.get('data', {})
                
                # ========================================
                # Step 6: 임베딩 평균 기반 추천 생성 (NEW)
                # ========================================

                print("Step 6: Creating recommendations (embedding-based)...")
                step6_start = time.time()

                if converted_panels:
                    # 임베딩 기반 엔진 import
                    from app.services.embedding_insight import embedding_insight_engine
                    
                    # 패널 UUID 리스트 추출
                    panel_uuids = [p['panel_uuid'] for p in converted_panels if p.get('panel_uuid')]
                    
                    print(f"📊 임베딩 분석 대상: {len(panel_uuids)}명")
                    
                    # 임베딩 평균 기반 인사이트 추출
                    embedding_insights = await embedding_insight_engine.extract_insights_by_embedding(
                        panel_uuids=panel_uuids,
                        search_conditions=search_conditions,
                        top_k=2  # 상위 2개만 선정
                    )
                    
                    print(f"✅ 임베딩 기반 인사이트: {len(embedding_insights)}개 발견")
                    
                    # 추천 버튼 생성
                    recommendations = []
                    for i, insight in enumerate(embedding_insights):
                        keyword = insight['value']
                        similarity = insight['similarity']
                        
                        recommendations.append({
                            "id": f"rec-embedding-{i+1}",
                            "text": insight['insight'],
                            "action": {
                                "buttonText": f"+ '{keyword}' 추가",
                                "data": {
                                    "type": "embedding_insight",
                                    "value": keyword,
                                    "queryPart": keyword,
                                    "similarity": similarity
                                }
                            }
                        })
                    
                    print(f"최종 {len(recommendations)}개 추천 생성 (임베딩 기반)")

                else:
                    # 검색 결과 없을 때 대체 추천
                    suggestions = []
                    
                    if search_conditions.get('location') == '지방':
                        suggestions.append({
                            "id": "rec-location-busan",
                            "text": "지방 전체가 아닌 특정 지역(예: 부산, 대구)을 지정해보세요.",
                            "action": {
                                "buttonText": "지역 구체화하기",
                                "data": { "type": "suggestion", "value": "부산", "queryPart": "부산" }
                            }
                        })
                    
                    if search_conditions.get('income_keyword'):
                        suggestions.append({
                            "id": "rec-income-remove",
                            "text": "소득 조건이 너무 엄격할 수 있습니다. 조건을 완화해보세요.",
                            "action": {
                                "buttonText": "소득 조건 제거",
                                "data": { "type": "suggestion", "value": "소득 무관", "queryPart": "" }
                            }
                        })
                    
                    recommendations = suggestions[:2]

                step6_time = round(time.time() - step6_start, 3)
                time_logs['step6_recommendations'] = step6_time
                print(f"Step 6 소요시간: {step6_time}초")

                # ========================================
                # Step 7: strategyCards 생성
                # ========================================

                print("Step 7: Creating strategy card metadata...")
                step7_start = time.time()
                
                # strategy_type_map = {
                #     # "rdb": "RDB 분석",
                #     # "vector": "벡터 유사도 분석",
                #     # "hybrid": "하이브리드 분석 (RDB + Vector)"
                # }
                
                target_profile = insights.get('target_profile', {})
                core_demo = target_profile.get('core_demographic', '타겟 그룹')
                key_chars = target_profile.get('key_characteristics', [])
                
                if converted_panels:
                    strategy_name = generate_concise_strategy_name(
                        original_query=request.query,
                        core_demo=core_demo,
                        key_chars=key_chars
                    )
                    
                    strategy_cards.append({
                        "id": "strategy-001",
                        "strategyName": strategy_name,
                        "coreTarget": ", ".join(key_chars[:3]) if key_chars else core_demo,
                        "strategyType": "",

                        "keywords": ", ".join([
                            p.get('feature', '') 
                            for p in insights.get('hidden_patterns', [])[:3]
                        ]),
                        "preloadHint": True
                    })

                    print(f"   전략 카드 생성 완료")
                else:
                    strategy_cards.append({
                        "id": "strategy-no-result",
                        "strategyName": "검색 결과 없음",
                        "coreTarget": f"검색 조건: {request.query}",
                        "strategyType": "조건 재설정 필요",
                        "keywords": "결과 없음, 조건 완화 권장",
                    })
                    print(f"   피드백 카드 생성 완료")
                
                step7_time = round(time.time() - step7_start, 3)
                time_logs['step7_card_metadata'] = step7_time
                print(f"Step 7 완료: {len(strategy_cards)}개 전략 카드 생성")
            else:
                print("Step 5 실패: 인사이트 데이터 없음")
        
        except Exception as e:
            print(f"AI Insight generation error: {e}")
            traceback.print_exc()
            
            strategy_cards.append({
                "id": "strategy-error",
                "strategyName": "AI 분석 불가",
                "coreTarget": f"{actual_mode.upper()} 검색 결과 제공",
                "strategyType": "System Error",
                "keywords": "오류 발생",
            })
        
        # ========================================
        # Step 8: filterTags 생성
        # ========================================
        step8_start = time.time()
        filter_tags = []
        
        age_range = search_conditions.get('age_range')
        if age_range and age_range.get('min'):
            decade = (age_range['min'] // 10) * 10
            filter_tags.append({
                "label": "나이",
                "value": f"{age_range.get('min')}-{age_range.get('max', age_range['min'])}세",
                "queryPart": f"{decade}대"
            })
        
        for key, label in [
            ('gender', '성별'),
            ('location', '지역'),
            ('district', '상세지역'),
            ('job', '직업')
        ]:
            if search_conditions.get(key):
                filter_tags.append({
                    "label": label,
                    "value": search_conditions[key],
                    "queryPart": search_conditions[key]
                })
        
        step8_time = round(time.time() - step8_start, 3)
        time_logs['step8_filters'] = step8_time
        
        sample_panels = converted_panels[:3]
        
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        
        print("모든 단계 완료! 응답 반환 중...")
        print(f"총 소요시간: {total_response_time}초")
        print(f"시간 분석: {json.dumps(time_logs, indent=2, ensure_ascii=False)}\n")
        
        return {
            "totalCount": len(converted_panels),
            "filterTags": filter_tags,
            "samplePanels": sample_panels,
            "currentFullPanelList": converted_panels,
            "recommendations": recommendations,
            "strategyCards": strategy_cards,
            "control": {
                "status": "success" if converted_panels else "no_results",
                "message": f"검색 완료 ({len(converted_panels)}명)" if converted_panels else "검색 결과 없음 - 조건 완화 필요",
                "searchQuery": request.query,
                "searchMode": request.search_mode,
                "actualMode": actual_mode,
                "timestamp": int(time.time()),
                "metadata": search_metadata,
                "time_breakdown": time_logs
            },
            "analysis": analysis_result,
            "generated_sql": sql_generation_result,
            "hidden_insights": insight_result,
            "count": len(converted_panels),
            "total_response_time_seconds": total_response_time
        }
    
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\nSearch Error:\n{error_detail}\n")
        
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail,
                "total_response_time_seconds": total_response_time
            }
        )


@router.get("/panel/{panel_uuid}")
async def get_panel_detail(panel_uuid: str):
    try:
        sql = """
            SELECT * FROM panel_master 
            WHERE panel_uuid = %s
        """
        result = DatabaseConnection.execute_query(sql, (panel_uuid,), fetch_all=False)
        
        if not result:
            raise HTTPException(status_code=404, detail="패널을 찾을 수 없습니다")
        
        formatted = convert_panel_to_frontend_format(result)
        
        return {"success": True, "data": formatted}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-report")
async def generate_strategy_report(request: ReportRequest):

    start_time = time.time()
    
    try:
        print(f"\n{'='*60}")
        print(f"리포트 생성 시작")
        print(f"   Strategy ID: {request.strategyId}")
        print(f"   Strategy Name: {request.strategyName}")
        print(f"{'='*60}\n")

        if request.originalQuery:
            search_result = await search_panels(
                SearchRequest(
                    query=request.originalQuery,
                    search_mode="hybrid",
                    top_k=100
                )
            )
            
            insights = search_result.get('hidden_insights', {}).get('data', {})
            panel_count = search_result.get('totalCount', 0)
        else:
            insights = {
                "hidden_patterns": [],
                "target_profile": {
                    "core_demographic": request.coreTarget or "타겟 그룹",
                    "key_characteristics": []
                }
            }
            panel_count = 0

        print("Generating full strategy report...")
        report_start = time.time()
        
        strategy_report_result = claude_service.generate_strategy_report(
            insights=insights,
            original_query=request.originalQuery or request.strategyName,
            panel_count=panel_count
        )
        
        report_time = round(time.time() - report_start, 2)
        print(f"리포트 생성 시간: {report_time}초")
        
        if not strategy_report_result.get('success'):
            raise ValueError("리포트 생성 실패")
        
        report_data = strategy_report_result.get('data', {})
        
        total_time = round(time.time() - start_time, 2)
        print(f"리포트 생성 완료 (총 {total_time}초)")
        
        return {
            "success": True,
            "report": report_data,
            "metadata": {
                "generation_time_seconds": total_time,
                "strategy_id": request.strategyId,
                "timestamp": int(time.time())
            }
        }
    
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\nReport Generation Error:\n{error_detail}\n")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail,
                "total_time": round(time.time() - start_time, 2)
            }
        )

@router.get("/search")
async def search_panels_get(
    query: str,
    search_mode: str = "hybrid",
    top_k: int = 100
):

    request = SearchRequest(
        query=query,
        search_mode=search_mode,
        top_k=top_k
    )
    return await search_panels(request)

@router.post("/vector")
async def vector_only_search(request: SearchRequest):
    try:
        results = search_agent.semantic_search(
            query_text=request.query,
            top_k=request.top_k
        )
        
        converted = [convert_panel_to_frontend_format(p) for p in results]
        
        return {
            "success": True,
            "data": converted,
            "count": len(converted),
            "search_type": "vector_semantic"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )