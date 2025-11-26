# app/services/combined_insight_engine.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter


# ====== 데이터 구조 정의 ======

@dataclass
class PanelSummary:
    """검색 결과에서 사용하는 패널 요약 정보 형태 (필요한 필드만 사용)."""
    panel_uuid: str
    age_group: Optional[str]      # 예: "30대", "40대"
    gender: Optional[str]         # 예: "남", "여"
    region: Optional[str]         # 예: "서울", "경기"
    job: Optional[str]            # 예: "사무직", "전문직", ...


@dataclass
class StructuredStats:
    """정형 데이터 통계."""
    total_count: int
    age_distribution: Dict[str, int]
    gender_distribution: Dict[str, int]
    region_distribution: Dict[str, int]
    job_distribution: Dict[str, int]


@dataclass
class SemanticTopic:
    """
    비정형(임베딩/텍스트) 기반 의미 토픽.

    예시:
      topic: "헬스/운동 관심"
      keywords: ["운동", "헬스", "다이어트"]
      size: 18               ← 이 토픽에 속한 패널 수
      examples: ["운동 PT를 주 2회 받는다", ...]
    """
    topic: str
    keywords: List[str]
    size: int
    examples: List[str]


@dataclass
class CombinedInsight:
    """
    최종으로 프론트에 넘길 통합 인사이트 구조 예시.
    """
    title: str                    # 카드 상단에 들어갈 한 줄 요약
    summary: str                  # 전체 서술 요약
    main_segment: str             # "40대 경기 거주 남성" 처럼 핵심 타깃 요약
    main_reason: str              # 왜 이 세그먼트를 주요 타깃으로 봤는지
    structured_stats: Dict[str, Any]
    semantic_topics: List[Dict[str, Any]]


# ====== 유틸 함수 ======

def _top_item(dist: Dict[str, int]) -> Tuple[Optional[str], float]:
    """
    가장 많이 나온 값과 비율을 계산.
    dist: {"30대": 11, "40대": 39} 형태
    return: ("40대", 0.78)
    """
    if not dist:
        return None, 0.0
    counter = Counter(dist)
    value, cnt = counter.most_common(1)[0]
    total = sum(counter.values())
    ratio = cnt / total if total > 0 else 0.0
    return value, ratio


# ====== 1단계: 패널 리스트 → 정형 통계 계산 ======

def calculate_structured_stats(panels: List[PanelSummary]) -> StructuredStats:
    age_dist: Dict[str, int] = {}
    gender_dist: Dict[str, int] = {}
    region_dist: Dict[str, int] = {}
    job_dist: Dict[str, int] = {}

    for p in panels:
        if p.age_group:
            age_dist[p.age_group] = age_dist.get(p.age_group, 0) + 1
        if p.gender:
            gender_dist[p.gender] = gender_dist.get(p.gender, 0) + 1
        if p.region:
            region_dist[p.region] = region_dist.get(p.region, 0) + 1
        if p.job:
            job_dist[p.job] = job_dist.get(p.job, 0) + 1

    return StructuredStats(
        total_count=len(panels),
        age_distribution=age_dist,
        gender_distribution=gender_dist,
        region_distribution=region_dist,
        job_distribution=job_dist,
    )


# ====== 2단계: 정형 + (선택) 비정형을 합쳐서 인사이트 생성 ======

def build_combined_insight(
    stats: StructuredStats,
    semantic_topics: Optional[List[SemanticTopic]] = None,
) -> CombinedInsight:
    """
    - 정형 통계만 있어도 인사이트 생성 가능
    - semantic_topics가 있으면, 가장 큰 토픽을 정형 인사이트에 엮어서 설명
    """

    # 1) 메인 세그먼트(나이/성별/지역/직업) 뽑기
    main_age,  age_ratio  = _top_item(stats.age_distribution)
    main_gender, gender_ratio = _top_item(stats.gender_distribution)
    main_region, region_ratio = _top_item(stats.region_distribution)
    main_job, job_ratio = _top_item(stats.job_distribution)

    # 자연어로 조합
    segment_parts = []
    if main_region:
        segment_parts.append(main_region)
    if main_age:
        segment_parts.append(main_age)
    if main_gender:
        segment_parts.append(main_gender)
    if main_job:
        segment_parts.append(main_job)

    main_segment = " ".join(segment_parts) if segment_parts else "주요 타깃 집단"

    # 2) 비정형(의미 토픽) 중 가장 큰 토픽 선택 (있을 때만)
    main_topic: Optional[SemanticTopic] = None
    if semantic_topics:
        semantic_topics = [t for t in semantic_topics if t.size > 0]
        if semantic_topics:
            main_topic = sorted(semantic_topics, key=lambda t: t.size, reverse=True)[0]

    # 3) 정형/비정형을 합쳐 한 줄 요약 & 상세 요약 만들기
    # --- 타이틀 ---
    if main_topic:
        title = f"{main_segment} 중심의 '{main_topic.topic}' 공통 인사이트"
    else:
        title = f"{main_segment} 중심 핵심 타깃 인사이트"

    # --- 이유 설명 ---
    reason_parts = []

    if main_age and age_ratio > 0:
        reason_parts.append(f"{main_age}가 전체의 약 {round(age_ratio * 100)}%로 가장 많습니다.")
    if main_gender and gender_ratio > 0:
        reason_parts.append(f"{main_gender} 비중이 약 {round(gender_ratio * 100)}%입니다.")
    if main_region and region_ratio > 0:
        reason_parts.append(f"거주 지역은 '{main_region}'이 약 {round(region_ratio * 100)}%로 대부분입니다.")
    if main_job and job_ratio > 0:
        reason_parts.append(f"직업은 '{main_job}' 비중이 가장 높습니다.")

    if main_topic:
        reason_parts.append(
            f"비정형 응답을 의미 기반으로 묶었을 때, "
            f"'{main_topic.topic}' 관련 토픽이 가장 큰 집단({main_topic.size}명)을 형성합니다."
        )

    main_reason = " ".join(reason_parts) if reason_parts else "주요 세그먼트의 비중이 상대적으로 높게 나타납니다."

    # --- 전체 요약 문장 ---
    if main_topic:
        summary = (
            f"이번 검색 결과에서 가장 두드러지는 집단은 {main_segment}입니다. "
            f"이들은 '{main_topic.topic}'과(와) 관련된 응답이 많이 나타나며, "
            f"통계적으로도 위 세그먼트의 비중이 가장 높게 관측됩니다."
        )
    else:
        summary = (
            f"이번 검색 결과에서 가장 두드러지는 집단은 {main_segment}입니다. "
            f"비정형 응답 임베딩 정보가 충분하지 않아 의미 기반 토픽은 추출되지 않았지만, "
            f"연령·성별·지역·직업 분포를 기준으로 볼 때 이 세그먼트를 핵심 타깃으로 보는 것이 합리적입니다."
        )

    # 4) 정형 통계를 그대로 내려주기 (프론트에서 그래프 등으로 사용 가능)
    structured_stats_dict: Dict[str, Any] = {
        "total_count": stats.total_count,
        "age_distribution": stats.age_distribution,
        "gender_distribution": stats.gender_distribution,
        "region_distribution": stats.region_distribution,
        "job_distribution": stats.job_distribution,
    }

    # 5) semantic_topics도 dict로 변환해서 내려주기 (없으면 빈 리스트)
    semantic_topics_payload: List[Dict[str, Any]] = []
    if semantic_topics:
        for t in semantic_topics:
            semantic_topics_payload.append(
                {
                    "topic": t.topic,
                    "keywords": t.keywords,
                    "size": t.size,
                    "examples": t.examples,
                }
            )

    return CombinedInsight(
        title=title,
        summary=summary,
        main_segment=main_segment,
        main_reason=main_reason,
        structured_stats=structured_stats_dict,
        semantic_topics=semantic_topics_payload,
    )
