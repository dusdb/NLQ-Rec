# app/api/v1/search.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import json
import traceback
import asyncio
import re

from fastapi.encoders import jsonable_encoder

from app.utils.database import execute_fetch_query
from app.services.claude import claude_service
from app.services.search import search_agent

from app.database.connection import DatabaseConnection
from app.services.search import vector_service  # (현재 사용 X지만, 기존 코드 유지)

from app.utils import (
    should_use_vector_search,
    generate_concise_strategy_name,
    get_user_friendly_query_part,
    clean_insight_text
)

from app.services.formatters import convert_panel_to_frontend_format

router = APIRouter()


# =========================
# Request Models
# =========================

class SearchRequest(BaseModel):
    query: str
    search_mode: str = "hybrid"
    top_k: int = 100


class ReportRequest(BaseModel):
    strategyId: str
    strategyName: Optional[str] = None
    coreTarget: Optional[str] = None
    originalQuery: Optional[str] = None


class RefineInsightsRequest(BaseModel):
    panelUuids: List[str]  # 기존 검색 결과 패널 UUID 리스트
    additionalCondition: str
    originalQuery: str


# =========================
# SSE Helper
# =========================

def emit_progress(step: int, progress: int, message: str, data: dict = None):
    """SSE 이벤트 생성 헬퍼"""
    event_data = {
        "step": step,
        "progress": progress,
        "message": message,
    }
    if data:
        event_data.update(data)
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


# =========================
# 1. SSE Search (GET /search-stream)
# =========================

@router.get("/search-stream")
async def search_panels_stream(query: str, search_mode: str = "hybrid", top_k: int = 100):
    """
    SSE 스트리밍 방식 검색
    - 검색 단계 진행 상황을 실시간으로 전송
    - 최종 결과는 마지막 이벤트에서 'result' 필드로 전달
    """

    async def event_generator():
        try:
            start_time = time.time()
            print("\n" + "=" * 60)
            print(f"🔎 [SSE] 검색 시작")
            print(f"   모드: {search_mode}")
            print(f"   질의: {query}")
            print("=" * 60 + "\n")

            # -----------------------
            # Step 1: 쿼리 분석
            # -----------------------
            yield emit_progress(1, 10, "검색 조건을 분석하고 있어요...")
            await asyncio.sleep(0.05)

            analysis_result = claude_service.analyze_query(query)
            if not analysis_result.get("success"):
                err = analysis_result.get("error", "쿼리 분석 실패")
                print(f"❌ [SSE] 쿼리 분석 실패: {err}")
                yield emit_progress(0, 0, "검색 조건 분석 실패", {"error": err})
                return

            conditions_json = analysis_result.get("data", {})
            search_conditions = conditions_json.get("search_conditions", {})

            extracted_count = conditions_json.get("target_count")
            target_count = extracted_count if extracted_count else top_k
            print(f"🎯 [SSE] 타겟 인원수: {target_count}명 (추출: {extracted_count}, 기본: {top_k})")

            # -----------------------
            # Step 2: SQL 생성
            # -----------------------
            yield emit_progress(2, 20, "데이터베이스 검색을 준비하고 있어요...")
            await asyncio.sleep(0.05)

            sql_generation_result = claude_service.generate_sql(
                analyzed_query=conditions_json,
                target_count=target_count,
            )
            sql_query = sql_generation_result.get("sql_query")

            # -----------------------
            # Step 3: 검색 모드 결정 & 실행
            # -----------------------
            yield emit_progress(3, 30, "조건에 맞는 패널을 찾고 있어요...")
            await asyncio.sleep(0.05)

            actual_mode = search_mode
            if search_mode == "hybrid":
                needs_vector = should_use_vector_search(query, search_conditions)
                if not needs_vector:
                    print("→ [SSE] SQL 전용 모드로 자동 전환")
                    actual_mode = "rdb"
                else:
                    print("→ [SSE] 하이브리드 모드 유지")
                    actual_mode = "hybrid"

            print(f"▶ [SSE] 실제 검색 모드: {actual_mode.upper()}")

            if actual_mode == "rdb":
                if not sql_query:
                    raise ValueError("SQL 생성 실패 (sql_query 없음)")
                filtered_panels = await execute_fetch_query(sql_query)
            elif actual_mode == "vector":
                filtered_panels = search_agent.semantic_search(query, target_count)
            elif actual_mode == "hybrid":
                filtered_panels = search_agent.hybrid_search(query, search_conditions, target_count)
            else:
                raise ValueError(f"유효하지 않은 search_mode: {actual_mode}")

            # Fallback (hybrid 검색으로 완화)
            if not filtered_panels and actual_mode in ["rdb", "hybrid"]:
                print("⚠ [SSE] RDB/하이브리드 결과 없음 → 조건 유지한 채 하이브리드 fallback 검색 실행")
                filtered_panels = search_agent.hybrid_search(
                    query_text=query,
                    sql_conditions=search_conditions,
                    top_k=target_count,
                )

            # -----------------------
            # Step 4: 데이터 변환
            # -----------------------
            yield emit_progress(4, 45, "패널 정보를 정리하고 있어요...")
            await asyncio.sleep(0.05)

            converted_panels = [
                convert_panel_to_frontend_format(p) for p in filtered_panels
            ]

            print(f"✅ [SSE] 변환된 패널 수: {len(converted_panels)}명")

            # -----------------------
            # Step 5: 통계 계산
            # -----------------------
            yield emit_progress(5, 55, "패널 특성을 집계하고 있어요...")

            job_stats = {}
            location_stats = {}
            age_stats = {}
            gender_stats = {}
            income_stats = {}
            car_stats = {}

            current_year = 2025

            for p in converted_panels:
                job = p.get("job_category", "미상")
                job_stats[job] = job_stats.get(job, 0) + 1

                location = p.get("region_main", "미상")
                location_stats[location] = location_stats.get(location, 0) + 1

                birth_year = p.get("birth_year")
                if birth_year:
                    age = current_year - birth_year
                    age_group = f"{(age // 10) * 10}대"
                    age_stats[age_group] = age_stats.get(age_group, 0) + 1

                gender = p.get("gender", "미상")
                gender_stats[gender] = gender_stats.get(gender, 0) + 1

                income = p.get("personal_income", "미상")
                if income and income != "미상":
                    income_stats[income] = income_stats.get(income, 0) + 1

                car = p.get("car_brand", "미상")
                if car and car != "미상":
                    car_stats[car] = car_stats.get(car, 0) + 1

            full_statistics = {
                "job_distribution": job_stats,
                "location_distribution": location_stats,
                "age_distribution": age_stats,
                "gender_distribution": gender_stats,
                "income_distribution": income_stats,
                "car_distribution": car_stats,
                "total_count": len(converted_panels),
            }

            # -----------------------
            # Step 6: Claude 인사이트
            # -----------------------
            yield emit_progress(6, 65, "AI가 패턴을 분석하고 있어요...")

            if converted_panels:
                vector_results = [p for p in converted_panels if "similarity_score" in p]
                if vector_results:
                    top_results_for_insight = sorted(
                        vector_results,
                        key=lambda x: x["similarity_score"],
                        reverse=True,
                    )[:50]
                else:
                    top_results_for_insight = converted_panels[:50]

                insight_result = claude_service.extract_insights(
                    panel_data=top_results_for_insight,
                    original_query=query,
                    full_statistics=full_statistics,
                )
            else:
                # 검색 결과 0명일 때 기본 피드백
                insight_result = {
                    "success": True,
                    "data": {
                        "hidden_patterns": [],
                        "target_profile": {
                            "core_demographic": "검색 결과 없음",
                            "key_characteristics": [
                                "조건 완화 필요",
                            ],
                        },
                        "statistics": {},
                        "summary": f"'{query}' 조건과 일치하는 패널이 없습니다. 조건을 완화해보세요.",
                    },
                }

            insights = insight_result.get("data", {})

            # -----------------------
            # Step 7: 기존 추천 엔진 기반 추천
            # -----------------------
            yield emit_progress(7, 80, "추가로 좁힐 만한 조건을 추천하고 있어요...")

            recommendations: List[Dict[str, Any]] = []

            if converted_panels:
                from app.services.recommendation import recommendation_engine

                current_statistics = {
                    "job_distribution": job_stats,
                    "location_distribution": location_stats,
                    "age_distribution": age_stats,
                    "gender_distribution": gender_stats,
                    "income_distribution": income_stats,
                    "total_count": len(converted_panels),
                }

                raw_patterns = insights.get("hidden_patterns", [])
                filtered_patterns = recommendation_engine.filter_patterns(
                    patterns=raw_patterns,
                    search_conditions=search_conditions,
                    full_statistics=current_statistics,
                )

                recommendations = recommendation_engine.generate_recommendations(
                    filtered_patterns=filtered_patterns,
                    max_count=2,
                )
            else:
                # 결과가 없을 때는 조건 완화용 추천
                suggestions = []
                if search_conditions.get("location") == "지방":
                    suggestions.append({
                        "id": "rec-location-busan",
                        "text": "지방 전체가 아닌 특정 지역(예: 부산, 대구)을 지정해보세요.",
                        "action": {
                            "buttonText": "지역 구체화하기",
                            "data": {"type": "suggestion", "value": "부산", "queryPart": "부산"},
                        },
                    })
                if search_conditions.get("income_keyword"):
                    suggestions.append({
                        "id": "rec-income-remove",
                        "text": "소득 조건이 너무 엄격할 수 있습니다. 조건을 완화해보세요.",
                        "action": {
                            "buttonText": "소득 조건 제거",
                            "data": {"type": "suggestion", "value": "소득 무관", "queryPart": ""},
                        },
                    })
                if not suggestions:
                    suggestions.append({
                        "id": "rec-general",
                        "text": f"'{query}' 조건이 너무 구체적입니다. 조건을 하나씩 줄여보세요.",
                        "action": {
                            "buttonText": "조건 단순화하기",
                            "data": {"type": "suggestion", "value": "조건 완화", "queryPart": ""},
                        },
                    })
                recommendations = suggestions

            # -----------------------
            # Step 8: 전략 리포트 기반 strategyCards 생성
            # -----------------------
            yield emit_progress(8, 90, "AI가 전략 제안서를 작성하고 있어요...")

            strategy_cards: List[Dict[str, Any]] = []

            if converted_panels:
                strategy_report_result = claude_service.generate_strategy_report(
                    insights=insights,
                    original_query=query,
                    panel_count=len(converted_panels),
                )

                if strategy_report_result.get("success"):
                    strategy_report = strategy_report_result.get("data", {})

                    project_name = strategy_report.get("projectName", "타겟 전략")
                    project_subtitle = strategy_report.get("projectSubtitle", "")

                    core_target = ""
                    summary_table = strategy_report.get("summaryTable", [])
                    for row in summary_table:
                        if row.get("th") == "타겟 고객":
                            core_target = row.get("td", "")
                            break

                    if not core_target:
                        target_profile = insights.get("target_profile", {})
                        key_chars = target_profile.get("key_characteristics", [])
                        core_target = ", ".join(key_chars[:3]) if key_chars else "타겟 그룹"

                    keywords_list = []
                    insight_table = strategy_report.get("insightTable", {})
                    if insight_table and insight_table.get("rows"):
                        for row in insight_table["rows"][:3]:
                            if len(row) > 0:
                                keywords_list.append(row[0])

                    if not keywords_list:
                        keywords_list = [
                            p.get("feature", "")
                            for p in insights.get("hidden_patterns", [])[:3]
                        ]

                    keywords = ", ".join(keywords_list) if keywords_list else "분석 진행 중"

                    strategy_cards.append({
                        "id": "strategy-001",
                        "strategyName": project_name,
                        "projectSubtitle": project_subtitle,
                        "coreTarget": core_target,
                        "keywords": keywords,
                        "strategyType": "",
                        "preloadHint": True,
                        "report": strategy_report,
                    })
                else:
                    # 리포트 실패 시 예전 방식 fallback
                    target_profile = insights.get("target_profile", {})
                    core_demo = target_profile.get("core_demographic", "타겟 그룹")
                    key_chars = target_profile.get("key_characteristics", [])

                    strategy_name = generate_concise_strategy_name(
                        original_query=query,
                        core_demo=core_demo,
                        key_chars=key_chars,
                    )
                    strategy_cards.append({
                        "id": "strategy-001",
                        "strategyName": strategy_name,
                        "coreTarget": ", ".join(key_chars[:3]) if key_chars else core_demo,
                        "keywords": ", ".join([
                            p.get("feature", "")
                            for p in insights.get("hidden_patterns", [])[:3]
                        ]),
                        "strategyType": "",
                        "preloadHint": True,
                    })
            else:
                strategy_cards.append({
                    "id": "strategy-no-result",
                    "strategyName": "검색 결과 없음",
                    "coreTarget": f"검색 조건: {query}",
                    "strategyType": "조건 재설정 필요",
                    "keywords": "결과 없음, 조건 완화 권장",
                })

            # -----------------------
            # filterTags 생성 (확장 버전)
            # -----------------------
            filter_tags: List[Dict[str, Any]] = []

            age_range = search_conditions.get("age_range")
            if age_range and age_range.get("min"):
                decade = (age_range["min"] // 10) * 10
                filter_tags.append({
                    "label": "나이",
                    "value": f"{age_range.get('min')}-{age_range.get('max', age_range['min'])}세",
                    "queryPart": f"{decade}대",
                })

            for key, label in [
                ("gender", "성별"),
                ("location", "지역"),
                ("district", "상세지역"),
                ("job", "직업"),
                ("education", "학력"),
                ("income_level", "소득"),
                ("marital_status", "결혼상태"),
                ("car_brand", "차량"),
                ("phone_brand", "휴대폰"),
                ("smoking", "흡연"),
                ("alcohol", "음주"),
                ("product", "전자제품"),
                ("child", "자녀"),
                ("family", "가족구성"),
            ]:
                if search_conditions.get(key):
                    filter_tags.append({
                        "label": label,
                        "value": search_conditions[key],
                        "queryPart": search_conditions[key],
                    })

            total_time = round(time.time() - start_time, 2)

            result_data = {
                "totalCount": len(converted_panels),
                "filterTags": filter_tags,
                "samplePanels": converted_panels[:3],
                "currentFullPanelList": converted_panels,
                "recommendations": recommendations,
                "strategyCards": strategy_cards,
                "control": {
                    "status": "success" if converted_panels else "no_results",
                    "searchQuery": query,
                    "searchMode": search_mode,
                    "actualMode": actual_mode,
                    "total_response_time_seconds": total_time,
                },
            }
            
            clean_data = jsonable_encoder(result_data)
            yield emit_progress(9, 100, "검색 및 분석이 완료되었어요.", {"result": clean_data})

        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"\n[SSE Search Error]\n{error_detail}\n")
            yield emit_progress(0, 0, f"오류 발생: {str(e)}", {"error": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =========================
# 2. 메인 검색 (POST /search)
# =========================

@router.post("/search")
async def search_panels(request: SearchRequest):

    start_time = time.time()
    time_logs: Dict[str, Any] = {}

    converted_panels: List[Dict[str, Any]] = []
    analysis_result: Dict[str, Any] = {}
    sql_generation_result: Dict[str, Any] = {}
    insight_result: Dict[str, Any] = {}
    search_metadata: Dict[str, Any] = {}

    try:
        print("\n" + "=" * 60)
        print(f"🔎 검색 모드: {request.search_mode.upper()}")
        print(f"🔤 검색 질의: {request.query}")
        print("=" * 60 + "\n")

        # -----------------------
        # Step 1: 쿼리 분석 (Opus)
        # -----------------------
        print("Step 1: Query analysis starting...")
        step1_start = time.time()

        analysis_result = claude_service.analyze_query(request.query)

        step1_time = round(time.time() - step1_start, 3)
        time_logs["step1_analysis"] = step1_time
        print(f"✅ Step 1 완료 ({step1_time}초) / success={analysis_result.get('success')}")

        if not analysis_result.get("success"):
            raise ValueError(
                f"Query analysis failed: {analysis_result.get('error', 'Unknown')}"
            )

        conditions_json = analysis_result.get("data", {})
        search_conditions = conditions_json.get("search_conditions", {})

        extracted_count = conditions_json.get("target_count")
        target_count = extracted_count if extracted_count else request.top_k
        print(
            f"🎯 타겟 인원수: {target_count}명 (추출: {extracted_count}, 기본: {request.top_k})"
        )

        # -----------------------
        # Step 2: SQL 생성 (Haiku)
        # -----------------------
        print("Step 2: SQL generation starting...")
        step2_start = time.time()

        sql_generation_result = claude_service.generate_sql(
            analyzed_query=conditions_json,
            target_count=target_count,
        )

        step2_time = round(time.time() - step2_start, 3)
        time_logs["step2_sql_gen"] = step2_time
        print(
            f"✅ Step 2 완료 ({step2_time}초) / success={sql_generation_result.get('success')}"
        )

        sql_query = sql_generation_result.get("sql_query")

        # -----------------------
        # Step 3: 검색 실행 (자동 모드 결정)
        # -----------------------
        print("Step 3: Determining optimal search strategy...")
        step3_start = time.time()

        actual_mode = request.search_mode

        if request.search_mode == "hybrid":
            needs_vector = should_use_vector_search(request.query, search_conditions)

            if not needs_vector:
                print("→ SQL 전용 모드로 자동 전환")
                actual_mode = "rdb"
            else:
                print("→ 하이브리드 모드 유지")
                actual_mode = "hybrid"

        print(f"▶ Step 3: Executing {actual_mode.upper()} search...")

        if actual_mode == "rdb":
            if not sql_query:
                raise ValueError("SQL generation failed")
            filtered_panels = await execute_fetch_query(sql_query)
            search_metadata = {
                "search_type": "rdb_only",
                "sql_executed": True,
                "reason": "structured_conditions_only"
                if request.search_mode == "hybrid"
                else "user_specified",
            }

        elif actual_mode == "vector":
            filtered_panels = search_agent.semantic_search(
                request.query,
                target_count,  # target_count 사용
            )
            search_metadata = {"search_type": "vector_only", "vector_used": True}

        elif actual_mode == "hybrid":
            filtered_panels = search_agent.hybrid_search(
                request.query,
                search_conditions,
                target_count,  # target_count 사용
            )
            search_metadata = {
                "search_type": "hybrid",
                "sql_executed": True,
                "vector_used": True,
                "conditions_applied": list(search_conditions.keys()),
            }
        else:
            raise ValueError(f"Invalid search_mode: {actual_mode}")

        is_fallback = False
        if not filtered_panels and actual_mode in ["rdb", "hybrid"]:
            print(
                "⚠ 정확한 매칭 결과 없음. 유사도 기반 검색(Vector + 조건 필터)로 전환합니다..."
            )
            filtered_panels = search_agent.hybrid_search(
                query_text=request.query,
                sql_conditions=search_conditions,
                top_k=target_count,
            )
            is_fallback = True

            search_metadata = {
                "search_type": "fallback_hybrid",
                "original_mode": actual_mode,
                "message": "조건에 완벽히 부합하는 대상이 없어, 가장 유사한 대상을 (조건을 유지한 채) 찾았습니다.",
            }

        step3_time = round(time.time() - step3_start, 3)
        time_logs["step3_search_exec"] = step3_time
        print(
            f"✅ Step 3 완료: {len(filtered_panels)}명 검색됨 (Fallback: {is_fallback}) / {step3_time}초"
        )

        # -----------------------
        # Step 4: 데이터 변환
        # -----------------------
        print("Step 4: Converting panel data...")
        step4_start = time.time()

        converted_panels = [
            convert_panel_to_frontend_format(panel) for panel in filtered_panels
        ]

        step4_time = round(time.time() - step4_start, 3)
        time_logs["step4_conversion"] = step4_time
        print(f"✅ Step 4 완료: {len(converted_panels)}명 변환됨 ({step4_time}초)")

        # -----------------------
        # Step 5: 통계 계산
        # -----------------------
        recommendations: List[Dict[str, Any]] = []
        strategy_cards: List[Dict[str, Any]] = []
        insights: Dict[str, Any] = {}

        try:
            print("Step 5: Calculating statistics...")
            step5_start = time.time()

            if converted_panels:
                print(f"   {len(converted_panels)}명의 패널 통계 계산 중...")

                job_stats = {}
                location_stats = {}
                age_stats = {}
                gender_stats = {}
                income_stats = {}
                car_stats = {}

                current_year = 2025

                for p in converted_panels:
                    job = p.get("job_category", "미상")
                    job_stats[job] = job_stats.get(job, 0) + 1

                    location = p.get("region_main", "미상")
                    location_stats[location] = location_stats.get(location, 0) + 1

                    birth_year = p.get("birth_year")
                    if birth_year:
                        age = current_year - birth_year
                        age_group = f"{(age // 10) * 10}대"
                        age_stats[age_group] = age_stats.get(age_group, 0) + 1

                    gender = p.get("gender", "미상")
                    gender_stats[gender] = gender_stats.get(gender, 0) + 1

                    income = p.get("personal_income", "미상")
                    if income and income != "미상":
                        income_stats[income] = income_stats.get(income, 0) + 1

                    car = p.get("car_brand", "미상")
                    if car and car != "미상":
                        car_stats[car] = car_stats.get(car, 0) + 1

                print(f"   직업 분포: {job_stats}")
                print(f"   지역 분포: {location_stats}")
                print(f"   연령대 분포: {age_stats}")
                print(f"   성별 분포: {gender_stats}")

                full_statistics = {
                    "job_distribution": job_stats,
                    "location_distribution": location_stats,
                    "age_distribution": age_stats,
                    "gender_distribution": gender_stats,
                    "income_distribution": income_stats,
                    "car_distribution": car_stats,
                    "total_count": len(converted_panels),
                }

                step5_time = round(time.time() - step5_start, 3)
                time_logs["step5_statistics"] = step5_time
                print(f"✅ Step 5 완료 ({step5_time}초)")

                # -----------------------
                # Step 6: Claude 상세 패턴 분석
                # -----------------------
                print("Step 6: Extracting detailed patterns (Claude)...")
                step6_start = time.time()

                vector_results = [
                    p for p in converted_panels if "similarity_score" in p
                ]

                if vector_results:
                    top_results_for_insight = sorted(
                        vector_results,
                        key=lambda x: x["similarity_score"],
                        reverse=True,
                    )[:50]
                else:
                    top_results_for_insight = converted_panels[:50]

                insight_result = claude_service.extract_insights(
                    panel_data=top_results_for_insight,
                    original_query=request.query,
                    full_statistics=full_statistics,
                )

                step6_time = round(time.time() - step6_start, 3)
                time_logs["step6_claude_insights"] = step6_time
                print(
                    f"✅ Step 6 완료 ({step6_time}초) / success={insight_result.get('success')}"
                )
            else:
                print("   검색 결과 0명 → 조건 완화 피드백 생성")
                active_conditions = [
                    k for k, v in search_conditions.items() if v is not None
                ]
                insight_result = {
                    "success": True,
                    "data": {
                        "hidden_patterns": [],
                        "target_profile": {
                            "core_demographic": "검색 결과 없음",
                            "key_characteristics": [
                                f"검색 조건: {', '.join(active_conditions)}",
                                "조건 완화 필요",
                            ],
                        },
                        "statistics": {},
                        "summary": f"'{request.query}' 조건과 일치하는 패널이 없습니다. 조건을 완화하거나 다른 검색어를 시도해보세요.",
                    },
                }

            is_insight_success = insight_result.get("success", False)
            print(f"   인사이트 성공 여부: {is_insight_success}")

            if is_insight_success:
                insights = insight_result.get("data", {})

                # -----------------------
                # Step 7: 기존 추천 엔진 기반 추천
                # -----------------------
                print(
                    "Step 7: Creating recommendations (기존 recommendation_engine 기반)..."
                )
                step7_start = time.time()

                if converted_panels:
                    from app.services.recommendation import recommendation_engine

                    current_statistics = {
                        "job_distribution": job_stats,
                        "location_distribution": location_stats,
                        "age_distribution": age_stats,
                        "gender_distribution": gender_stats,
                        "income_distribution": income_stats,
                        "total_count": len(converted_panels),
                    }

                    raw_patterns = insights.get("hidden_patterns", [])

                    filtered_patterns = recommendation_engine.filter_patterns(
                        patterns=raw_patterns,
                        search_conditions=search_conditions,
                        full_statistics=current_statistics,
                    )

                    print(
                        f"   필터링 결과: {len(raw_patterns)}개 -> {len(filtered_patterns)}개 유효 패턴"
                    )

                    recommendations = recommendation_engine.generate_recommendations(
                        filtered_patterns=filtered_patterns,
                        max_count=2,
                    )

                    print(f"   최종 {len(recommendations)}개 추천 생성")
                else:
                    suggestions = []

                    if search_conditions.get("location") == "지방":
                        suggestions.append({
                            "id": "rec-location-busan",
                            "text": "지방 전체가 아닌 특정 지역(예: 부산, 대구)을 지정해보세요.",
                            "action": {
                                "buttonText": "지역 구체화하기",
                                "data": {
                                    "type": "suggestion",
                                    "value": "부산",
                                    "queryPart": "부산",
                                },
                            },
                        })

                    if search_conditions.get("income_keyword"):
                        suggestions.append({
                            "id": "rec-income-remove",
                            "text": "소득 조건이 너무 엄격할 수 있습니다. 조건을 완화해보세요.",
                            "action": {
                                "buttonText": "소득 조건 제거",
                                "data": {
                                    "type": "suggestion",
                                    "value": "소득 무관",
                                    "queryPart": "",
                                },
                            },
                        })

                    if not suggestions:
                        suggestions.append({
                            "id": "rec-general",
                            "text": f"'{request.query}' 조건이 너무 구체적입니다. 조건을 하나씩 줄여보세요.",
                            "action": {
                                "buttonText": "조건 단순화하기",
                                "data": {
                                    "type": "suggestion",
                                    "value": "조건 완화",
                                    "queryPart": "",
                                },
                            },
                        })

                    recommendations = suggestions
                    print(f"   {len(recommendations)}개 조건 완화 추천 생성")

                step7_time = round(time.time() - step7_start, 3)
                time_logs["step7_recommendations"] = step7_time
                print(f"✅ Step 7 완료 ({step7_time}초)")

                # -----------------------
                # Step 8: 전략 리포트 기반 strategyCards
                # -----------------------
                print(
                    "Step 8: Generating strategy report & strategyCards (리포트 기반)..."
                )
                step8_start = time.time()

                if converted_panels:
                    print(
                        f"   {len(converted_panels)}명 기반으로 전략 리포트 생성 중..."
                    )

                    strategy_report_result = claude_service.generate_strategy_report(
                        insights=insights,
                        original_query=request.query,
                        panel_count=len(converted_panels),
                    )

                    if strategy_report_result.get("success"):
                        strategy_report = strategy_report_result.get("data", {})

                        project_name = strategy_report.get("projectName", "타겟 전략")
                        project_subtitle = strategy_report.get(
                            "projectSubtitle", ""
                        )

                        core_target = ""
                        summary_table = strategy_report.get("summaryTable", [])
                        for row in summary_table:
                            if row.get("th") == "타겟 고객":
                                core_target = row.get("td", "")
                                break

                        if not core_target:
                            target_profile = insights.get("target_profile", {})
                            key_chars = target_profile.get("key_characteristics", [])
                            core_target = (
                                ", ".join(key_chars[:3])
                                if key_chars
                                else "타겟 그룹"
                            )

                        keywords_list = []
                        insight_table = strategy_report.get("insightTable", {})
                        if insight_table and insight_table.get("rows"):
                            for row in insight_table["rows"][:3]:
                                if len(row) > 0:
                                    keywords_list.append(row[0])

                        if not keywords_list:
                            keywords_list = [
                                p.get("feature", "")
                                for p in insights.get("hidden_patterns", [])[:3]
                            ]

                        keywords = (
                            ", ".join(keywords_list)
                            if keywords_list
                            else "분석 진행 중"
                        )

                        strategy_cards.append({
                            "id": "strategy-001",
                            "strategyName": project_name,
                            "projectSubtitle": project_subtitle,
                            "coreTarget": core_target,
                            "keywords": keywords,
                            "strategyType": "",
                            "preloadHint": True,
                            "report": strategy_report,
                        })

                        print(f"   전략 카드 생성 완료: {project_name}")
                    else:
                        print("   ⚠ 전략 리포트 생성 실패 → 간략 전략명으로 대체")

                        target_profile = insights.get("target_profile", {})
                        core_demo = target_profile.get(
                            "core_demographic", "타겟 그룹"
                        )
                        key_chars = target_profile.get("key_characteristics", [])

                        strategy_name = generate_concise_strategy_name(
                            original_query=request.query,
                            core_demo=core_demo,
                            key_chars=key_chars,
                        )

                        strategy_cards.append({
                            "id": "strategy-001",
                            "strategyName": strategy_name,
                            "coreTarget": ", ".join(key_chars[:3])
                            if key_chars
                            else core_demo,
                            "keywords": ", ".join(
                                [
                                    p.get("feature", "")
                                    for p in insights.get(
                                        "hidden_patterns", []
                                    )[:3]
                                ]
                            ),
                            "strategyType": "",
                            "preloadHint": True,
                        })
                else:
                    strategy_cards.append({
                        "id": "strategy-no-result",
                        "strategyName": "검색 결과 없음",
                        "coreTarget": f"검색 조건: {request.query}",
                        "strategyType": "조건 재설정 필요",
                        "keywords": "결과 없음, 조건 완화 권장",
                    })
                    print("   피드백용 전략 카드 생성 완료")

                step8_time = round(time.time() - step8_start, 3)
                time_logs["step8_report_generation"] = step8_time
                print(f"✅ Step 8 완료 ({step8_time}초) / 카드 수: {len(strategy_cards)}")
            else:
                print("⚠ Step 6 실패: 인사이트 데이터 없음 → 추천/전략카드 생략 또는 최소화")

        except Exception as e:
            print(f"AI Insight / Recommendation error: {e}")
            traceback.print_exc()

            strategy_cards.append({
                "id": "strategy-error",
                "strategyName": "AI 분석 불가",
                "coreTarget": f"{actual_mode.upper()} 검색 결과 제공",
                "strategyType": "System Error",
                "keywords": "오류 발생",
            })

        # -----------------------
        # Step 9: filterTags 생성 (확장 버전)
        # -----------------------
        print("Step 9: filterTags 생성...")
        step9_start = time.time()

        filter_tags: List[Dict[str, Any]] = []

        age_range = search_conditions.get("age_range")
        if age_range and age_range.get("min"):
            decade = (age_range["min"] // 10) * 10
            filter_tags.append({
                "label": "나이",
                "value": f"{age_range.get('min')}-{age_range.get('max', age_range['min'])}세",
                "queryPart": f"{decade}대",
            })

        for key, label in [
            ("gender", "성별"),
            ("location", "지역"),
            ("district", "상세지역"),
            ("job", "직업"),
            ("education", "학력"),
            ("income_level", "소득"),
            ("marital_status", "결혼상태"),
            ("car_brand", "차량"),
            ("phone_brand", "휴대폰"),
            ("smoking", "흡연"),
            ("alcohol", "음주"),
            ("product", "전자제품"),
            ("child", "자녀"),
            ("family", "가족구성"),
        ]:
            if search_conditions.get(key):
                filter_tags.append({
                    "label": label,
                    "value": search_conditions[key],
                    "queryPart": search_conditions[key],
                })

        step9_time = round(time.time() - step9_start, 3)
        time_logs["step9_filters"] = step9_time
        print(f"✅ Step 9 완료 ({step9_time}초) / filterTags={len(filter_tags)}개")

        # -----------------------
        # 최종 응답
        # -----------------------
        sample_panels = converted_panels[:3]
        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)

        print("🎉 모든 단계 완료! 응답 반환 중...")
        print(f"⏱ 총 소요시간: {total_response_time}초")
        print(
            f"⏱ 시간 분석: {json.dumps(time_logs, indent=2, ensure_ascii=False)}\n"
        )

        return {
            "totalCount": len(converted_panels),
            "filterTags": filter_tags,
            "samplePanels": sample_panels,
            "currentFullPanelList": converted_panels,
            "recommendations": recommendations,
            "strategyCards": strategy_cards,
            "control": {
                "status": "success" if converted_panels else "no_results",
                "message": f"검색 완료 ({len(converted_panels)}명)"
                if converted_panels
                else "검색 결과 없음 - 조건 완화 필요",
                "searchQuery": request.query,
                "searchMode": request.search_mode,
                "actualMode": actual_mode,
                "timestamp": int(time.time()),
                "metadata": search_metadata,
                "time_breakdown": time_logs,
            },
            "analysis": analysis_result,
            "generated_sql": sql_generation_result,
            "hidden_insights": insight_result,
            "count": len(converted_panels),
            "total_response_time_seconds": total_response_time,
        }

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n[Search Error]\n{error_detail}\n")

        end_time = time.time()
        total_response_time = round(end_time - start_time, 2)

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail,
                "total_response_time_seconds": total_response_time,
            },
        )


# =========================
# 3. 패널 상세 조회
# =========================

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


# =========================
# 4. 전략 리포트 생성
# =========================

@router.post("/generate-report")
async def generate_strategy_report(request: ReportRequest):

    start_time = time.time()

    try:
        print("\n" + "=" * 60)
        print("📝 리포트 생성 시작")
        print(f"   Strategy ID: {request.strategyId}")
        print(f"   Strategy Name: {request.strategyName}")
        print("=" * 60 + "\n")

        if request.originalQuery:
            search_result = await search_panels(
                SearchRequest(
                    query=request.originalQuery,
                    search_mode="hybrid",
                    top_k=100,
                )
            )

            insights = search_result.get("hidden_insights", {}).get("data", {})
            panel_count = search_result.get("totalCount", 0)
        else:
            insights = {
                "hidden_patterns": [],
                "target_profile": {
                    "core_demographic": request.coreTarget or "타겟 그룹",
                    "key_characteristics": [],
                },
            }
            panel_count = 0

        print("   Claude로 풀 전략 리포트 생성 중...")
        report_start = time.time()

        strategy_report_result = claude_service.generate_strategy_report(
            insights=insights,
            original_query=request.originalQuery or request.strategyName,
            panel_count=panel_count,
        )

        report_time = round(time.time() - report_start, 2)
        print(f"   리포트 생성 시간: {report_time}초")

        if not strategy_report_result.get("success"):
            raise ValueError("리포트 생성 실패")

        report_data = strategy_report_result.get("data", {})

        total_time = round(time.time() - start_time, 2)
        print(f"✅ 리포트 생성 완료 (총 {total_time}초)")

        return {
            "success": True,
            "report": report_data,
            "metadata": {
                "generation_time_seconds": total_time,
                "strategy_id": request.strategyId,
                "timestamp": int(time.time()),
            },
        }

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n[Report Generation Error]\n{error_detail}\n")

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail,
                "total_time": round(time.time() - start_time, 2),
            },
        )


# =========================
# 5. (GET) /search → POST /search 래핑
# =========================

@router.get("/search")
async def search_panels_get(
    query: str,
    search_mode: str = "hybrid",
    top_k: int = 100,
):

    request = SearchRequest(
        query=query,
        search_mode=search_mode,
        top_k=top_k,
    )
    return await search_panels(request)


# =========================
# 6. 벡터 전용 검색
# =========================

@router.post("/vector")
async def vector_only_search(request: SearchRequest):
    try:
        results = search_agent.semantic_search(
            query_text=request.query,
            top_k=request.top_k,
        )

        converted = [convert_panel_to_frontend_format(p) for p in results]

        return {
            "success": True,
            "data": converted,
            "count": len(converted),
            "search_type": "vector_semantic",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


# =========================
# 7. Refine Insights (추가 조건으로 재필터 + 인사이트 재생성)
# =========================

@router.post("/refine-insights")
async def refine_insights(request: RefineInsightsRequest):
    """
    기존 검색 결과에 조건 추가하여 DB에서 필터링 후 인사이트/추천만 재생성
    - 기존 검색: /search → 패널 UUID 수집
    - 이 API: UUID + 추가조건으로 범위를 좁혀서 인사이트/추천 재계산
    """
    start_time = time.time()

    try:
        print("\n" + "=" * 60)
        print("🔁 인사이트 재생성 시작 (refine-insights)")
        print(f"   기존 패널: {len(request.panelUuids)}개 UUID")
        print(f"   추가 조건: {request.additionalCondition}")
        print("=" * 60 + "\n")

        # Step 1: 추가 조건만 분석
        print("Step 1: 추가 조건 분석...")
        step1_start = time.time()

        analysis_result = claude_service.analyze_query(request.additionalCondition)

        if not analysis_result.get("success"):
            raise ValueError(f"조건 분석 실패: {analysis_result.get('error')}")

        additional_conditions = analysis_result.get("data", {}).get(
            "search_conditions", {}
        )
        step1_time = round(time.time() - step1_start, 3)
        print(f"✅ Step 1 완료 ({step1_time}초)")
        print(f"   추가된 조건: {additional_conditions}")

        # Step 2: DB 필터링 (UUID + 추가 조건)
        print("Step 2: DB에서 필터링...")
        step2_start = time.time()

        filtered_panels = await filter_panels_by_uuids_and_conditions(
            request.panelUuids,
            additional_conditions,
        )

        step2_time = round(time.time() - step2_start, 3)
        print(
            f"✅ Step 2 완료: {len(request.panelUuids)}명 → {len(filtered_panels)}명 ({step2_time}초)"
        )

        if not filtered_panels:
            total_time = round(time.time() - start_time, 2)
            print(f"⚠ 필터링 결과 없음 (총 {total_time}초)")

            return {
                "success": True,
                "totalCount": 0,
                "filteredPanels": [],
                "recommendations": [],
                "message": f"'{request.additionalCondition}' 조건을 만족하는 패널이 없습니다.",
                "control": {
                    "status": "no_results",
                    "original_count": len(request.panelUuids),
                    "filtered_count": 0,
                    "condition_added": request.additionalCondition,
                    "total_response_time_seconds": total_time,
                },
            }

        # Step 3: 데이터 변환
        print("Step 3: 데이터 변환...")
        step3_start = time.time()

        converted_panels = [
            convert_panel_to_frontend_format(panel) for panel in filtered_panels
        ]

        step3_time = round(time.time() - step3_start, 3)
        print(f"✅ Step 3 완료 ({step3_time}초) / {len(converted_panels)}명")

        # Step 4: 인사이트 재생성
        print("Step 4: 인사이트 재생성...")
        step4_start = time.time()

        current_year = 2025
        job_stats = {}
        location_stats = {}
        age_stats = {}
        gender_stats = {}

        for p in converted_panels:
            job = p.get("job_category", "미상")
            job_stats[job] = job_stats.get(job, 0) + 1

            location = p.get("region_main", "미상")
            location_stats[location] = location_stats.get(location, 0) + 1

            birth_year = p.get("birth_year")
            if birth_year:
                age = current_year - birth_year
                age_group = f"{(age // 10) * 10}대"
                age_stats[age_group] = age_stats.get(age_group, 0) + 1

            gender = p.get("gender", "미상")
            gender_stats[gender] = gender_stats.get(gender, 0) + 1

        combined_query = f"{request.originalQuery}, {request.additionalCondition}"

        insight_result = claude_service.extract_insights(
            panel_data=converted_panels[:10],
            original_query=combined_query,
            full_statistics={
                "job_distribution": job_stats,
                "location_distribution": location_stats,
                "age_distribution": age_stats,
                "gender_distribution": gender_stats,
                "total_count": len(converted_panels),
            },
        )

        step4_time = round(time.time() - step4_start, 3)
        print(f"✅ Step 4 완료 ({step4_time}초)")

        # Step 5: 기존 추천 엔진 기반 추천
        print("Step 5: 추천 재생성 (recommendation_engine)...")
        step5_start = time.time()

        recommendations: List[Dict[str, Any]] = []

        if len(converted_panels) > 0:
            from app.services.recommendation import recommendation_engine

            # 전체 조건(기존 질의 + 추가 조건)을 다시 분석해서 중복/무의미한 조건 제거용으로 사용
            full_analysis = claude_service.analyze_query(combined_query)
            full_conditions = full_analysis.get("data", {}).get(
                "search_conditions", {}
            )

            current_statistics = {
                "job_distribution": job_stats,
                "location_distribution": location_stats,
                "age_distribution": age_stats,
                "gender_distribution": gender_stats,
                "total_count": len(converted_panels),
            }

            raw_patterns = insight_result.get("data", {}).get("hidden_patterns", [])

            filtered_patterns = recommendation_engine.filter_patterns(
                patterns=raw_patterns,
                search_conditions=full_conditions,
                full_statistics=current_statistics,
            )

            recommendations = recommendation_engine.generate_recommendations(
                filtered_patterns=filtered_patterns,
                max_count=2,
            )

        step5_time = round(time.time() - step5_start, 3)
        print(
            f"✅ Step 5 완료: 추천 {len(recommendations)}개 ({step5_time}초)"
        )

        total_time = round(time.time() - start_time, 2)
        print(f"\n🎉 refine-insights 총 소요시간: {total_time}초\n")

        return {
            "success": True,
            "totalCount": len(converted_panels),
            "filteredPanels": converted_panels,
            "samplePanels": converted_panels[:3],
            "recommendations": recommendations,
            "insights": insight_result.get("data", {}),
            "control": {
                "status": "success",
                "message": f"필터링 완료 ({len(converted_panels)}명)",
                "original_count": len(request.panelUuids),
                "filtered_count": len(converted_panels),
                "condition_added": request.additionalCondition,
                "time_breakdown": {
                    "step1_analysis": step1_time,
                    "step2_db_filtering": step2_time,
                    "step3_conversion": step3_time,
                    "step4_insights": step4_time,
                    "step5_recommendations": step5_time,
                },
                "total_response_time_seconds": total_time,
            },
        }

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n[Refine Insights Error]\n{error_detail}\n")

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail,
            },
        )


# =========================
# 8. SQL 기반 패널 필터링 (UUID + 조건)
# =========================

async def filter_panels_by_uuids_and_conditions(
    panel_uuids: List[str],
    conditions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    UUID 리스트 + 조건으로 DB에서 필터링 (SQL)
    - 기존 검색 결과 범위(패널 UUID) 안에서만 추가 조건으로 좁힘
    """
    if not panel_uuids:
        return []

    current_year = 2025
    where_clauses: List[str] = []
    params: List[Any] = []

    # 1. UUID 조건
    placeholders = ",".join([f"${i + 1}" for i in range(len(panel_uuids))])
    where_clauses.append(f"panel_uuid IN ({placeholders})")
    params.extend(panel_uuids)

    # 2. 나이 조건
    if conditions.get("age_range"):
        age_range = conditions["age_range"]
        min_age = age_range.get("min", 0)
        max_age = age_range.get("max", 100)
        start_year = current_year - max_age
        end_year = current_year - min_age
        where_clauses.append(
            f"birth_year BETWEEN ${len(params) + 1} AND ${len(params) + 2}"
        )
        params.extend([start_year, end_year])

    # 3. 성별
    if conditions.get("gender"):
        where_clauses.append(f"gender = ${len(params) + 1}")
        params.append(conditions["gender"])

    # 4. 지역
    location = conditions.get("location")
    if location:
        if location == "지방":
            where_clauses.append("region_main NOT IN ('서울', '경기', '인천')")
        else:
            where_clauses.append(f"region_main LIKE ${len(params) + 1}")
            params.append(f"%{location}%")

    # 5. 상세 지역
    if conditions.get("district"):
        where_clauses.append(f"region_sub LIKE ${len(params) + 1}")
        params.append(f"%{conditions['district']}%")

    # 6. 직업
    # 6. 직업
    job_value = conditions.get("job")
    if job_value:
        # 공백, /, +, ·, 콤마, 점, -, | 모두 분리
        keywords = re.split(r'[ +/·.,&|-]', job_value)
        keywords = [k.strip() for k in keywords if k.strip()]

        if len(keywords) == 1:
            where_clauses.append(f"job_category LIKE ${len(params) + 1}")
            params.append(f"%{keywords[0]}%")
        else:
            or_clauses = []
            for kw in keywords:
                or_clauses.append(f"job_category LIKE ${len(params) + 1}")
                params.append(f"%{kw}%")

            where_clauses.append("(" + " OR ".join(or_clauses) + ")")


    # 7. 소득
    if conditions.get("income_keyword"):
        where_clauses.append(f"personal_income LIKE ${len(params) + 1}")
        params.append(f"%{conditions['income_keyword']}%")

    # 8. 휴대폰
    if conditions.get("phone_brand"):
        where_clauses.append(f"owned_phone_brand LIKE ${len(params) + 1}")
        params.append(f"%{conditions['phone_brand']}%")

    # 9. 차량
    if conditions.get("car_brand"):
        where_clauses.append(f"car_brand LIKE ${len(params) + 1}")
        params.append(f"%{conditions['car_brand']}%")

    # 10. 흡연
    smoking = conditions.get("smoking")
    if smoking == "흡연":
        where_clauses.append("smoking_exp != '담배를 피워본 적이 없다'")
    elif smoking == "비흡연":
        where_clauses.append("smoking_exp = '담배를 피워본 적이 없다'")

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT 
            panel_id, panel_uuid, birth_year, gender,
            region_main, region_sub, job_category, job_detail,
            education, marital_status, personal_income, household_income,
            owned_phone_brand, owned_phone_model,
            car_brand, car_model, has_car,
            smoking_exp, alcohol_exp, child_num, family_num
        FROM panel_master
        WHERE {where_sql}
    """

    print(f"🔍 실행할 SQL (refine-insights):\n{sql}\n")
    print(f"📊 파라미터 개수: {len(params)}")

    try:
        results = await execute_fetch_query(sql, tuple(params))
        print(f"✅ DB 필터링 완료: {len(results)}명")
        return results
    except Exception as e:
        print(f"❌ DB 필터링 실패: {e}")
        traceback.print_exc()
        return []


# =========================
# 9. 레거시: 메모리 기반 필터 (현재 사용 안 함)
# =========================

def filter_panels_by_condition(
    panels: List[Dict[str, Any]],
    conditions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    패널 리스트를 조건으로 필터링 (레거시, 사용 안 함 - 참고용)
    """
    filtered: List[Dict[str, Any]] = []
    current_year = 2025

    for panel in panels:
        match = True

        # 나이 조건
        if conditions.get("age_range"):
            age_range = conditions["age_range"]
            birth_year = panel.get("birth_year")
            if birth_year:
                age = current_year - birth_year
                min_age = age_range.get("min", 0)
                max_age = age_range.get("max", 100)
                if not (min_age <= age <= max_age):
                    match = False

        # 성별
        if conditions.get("gender") and panel.get("gender") != conditions["gender"]:
            match = False

        # 지역
        location = conditions.get("location")
        if location:
            if location == "지방":
                if panel.get("region_main") in ["서울", "경기", "인천"]:
                    match = False
            else:
                if location not in (panel.get("region_main") or ""):
                    match = False

        # 상세지역
        if conditions.get("district"):
            if conditions["district"] not in (panel.get("region_sub") or ""):
                match = False

        # 직업
        if conditions.get("job"):
            job_category = panel.get("job_category") or ""
            if conditions["job"] not in job_category:
                match = False

        # 소득
        if conditions.get("income_keyword"):
            income = panel.get("personal_income") or ""
            if conditions["income_keyword"] not in income:
                match = False

        # 휴대폰
        if conditions.get("phone_brand"):
            phone = panel.get("owned_phone_brand") or ""
            if conditions["phone_brand"] not in phone:
                match = False

        # 차량
        if conditions.get("car_brand"):
            car = panel.get("car_brand") or ""
            if conditions["car_brand"] not in car:
                match = False

        if match:
            filtered.append(panel)

    return filtered
