# app/utils/search_helpers.py
"""
검색 관련 유틸리티 함수들
"""
from typing import Dict, List, Optional
import re


def should_use_vector_search(query: str, search_conditions: Dict) -> bool:
    """
    벡터 검색이 필요한지 판단
    
    Returns:
        True: 하이브리드 필요 (의미 기반 검색 필요)
        False: SQL만 사용 (조건만 있음)
    """
    # 1. 의미 기반 키워드 감지
    semantic_keywords = [
        '관심', '좋아', '선호', '즐기', '자주',
        '관련', '열정', '취미', '행동', '패턴',
        'AI', '운동', '음악', '여행', '독서',
        '환경', '건강', '투자', '게임', '콘텐츠',
        '브랜드', '제품', '서비스'
    ]
    
    has_semantic = any(keyword in query for keyword in semantic_keywords)
    
    if has_semantic:
        print(f"   ✅ 의미 키워드 감지: {[k for k in semantic_keywords if k in query]}")
        return True
    
    # 2. 구조화된 조건만 있는지 확인
    if not search_conditions:
        # 조건이 없으면 벡터 검색 필요
        return True
    
    structured_fields = {
        'age_range', 'gender', 'location', 'district', 
        'job', 'income_keyword', 'phone_brand', 'car_brand', 'smoking'
    }
    
    active_conditions = {
        key for key, value in search_conditions.items() 
        if value is not None
    }
    
    all_structured = active_conditions.issubset(structured_fields)
    
    if all_structured and active_conditions:
        print(f"   ⚠️ 구조화된 조건만 존재: {active_conditions}")
        return False
    
    # 3. 애매하면 하이브리드
    return True


def generate_concise_strategy_name(
    original_query: str,
    core_demo: str,
    key_chars: List[str]
) -> str:
    """
    간결한 전략 제목 생성
    
    예: "서울 경기 OTT 이용하는 젊은층" 
        → "OTT 이용층 타겟 전략"
    """
    # 1. 핵심 키워드 추출
    keywords = []
    
    # OTT, AI, IT 같은 고유명사
    tech_keywords = ['OTT', 'AI', 'IT', 'IoT', 'VR', 'AR']
    for kw in tech_keywords:
        if kw in original_query:
            keywords.append(kw)
    
    # 관심사 키워드
    interest_keywords = ['운동', '건강', '여행', '음악', '게임', '독서', '투자', '환경']
    for kw in interest_keywords:
        if kw in original_query:
            keywords.append(kw)
    
    # 2. 타겟 요약
    target_summary = ""
    if '젊은' in original_query or '청년' in original_query:
        target_summary = "젊은층"
    elif any(age in original_query for age in ['10대', '20대', '30대', '40대', '50대']):
        for age in ['10대', '20대', '30대', '40대', '50대']:
            if age in original_query:
                target_summary = age
                break
    
    # 3. 제목 조합
    if keywords and target_summary:
        return f"{keywords[0]} {target_summary} 타겟 전략"
    elif keywords:
        return f"{keywords[0]} 이용층 전략"
    elif target_summary:
        return f"{target_summary} 타겟 전략"
    else:
        # Fallback: core_demo 사용 (하지만 짧게)
        demo_short = core_demo.split()[0] if core_demo else "타겟 그룹"
        return f"{demo_short} 전략"


def get_user_friendly_query_part(feature: str, value: str) -> str:
    """
    feature와 value를 사용자 친화적인 검색 조건으로 변환
    
    예시:
    - feature="location", value="수도권 집중 (서울/인천/경기)" → "서울"
    - feature="job", value="IT/전문직" → "전문직"
    - feature="income", value="고소득층 (700만원+)" → "고소득"
    """
    feature_lower = feature.lower()
    value_lower = value.lower()
    
    # 1. location 처리
    if any(word in feature_lower for word in ['location', '지역', '거주', '수도권']):
        # 구체적 지역명 추출
        cities = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', 
                 '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
        
        for city in cities:
            if city in value:
                return city
        
        # 괄호 안 내용 추출 (서울/인천/경기)
        match = re.search(r'\(([^)]+)\)', value)
        if match:
            locations = match.group(1).split('/')
            return locations[0].strip()
        
        # "수도권"이라는 단어가 있으면
        if '수도권' in value_lower:
            return '서울'
        
        return value.split()[0] if value else 'location'
    
    # 2. job 처리
    if any(word in feature_lower for word in ['job', '직업', '전문직', '사무직']):
        # "IT/전문직" → "전문직"
        if '/' in value:
            jobs = [j.strip() for j in value.split('/')]
            # 우선순위: 전문직 > 사무직 > 기타
            if any('전문직' in j for j in jobs):
                return '전문직'
            elif any('사무직' in j for j in jobs):
                return '사무직'
            return jobs[-1]
        
        # 괄호 제거
        cleaned = re.sub(r'\([^)]*\)', '', value).strip()
        return cleaned if cleaned else value
    
    # 3. income 처리
    if any(word in feature_lower for word in ['income', '소득', '연봉']):
        if any(word in value_lower for word in ['고소득', '상위', '700', '800', '1000']):
            return '고소득'
        elif any(word in value_lower for word in ['중산층', '중위', '평균']):
            return '중산층'
        return '고소득'
    
    # 4. car 처리
    if any(word in feature_lower for word in ['car', '자동차', '차량']):
        if any(word in value_lower for word in ['독일', 'bmw', '벤츠', '아우디', '수입']):
            return '독일차'
        elif any(word in value_lower for word in ['국산', '현대', '기아']):
            return '국산차'
        return '자동차'
    
    # 5. phone 처리
    if any(word in feature_lower for word in ['phone', '스마트폰', '휴대폰']):
        if any(word in value_lower for word in ['iphone', '아이폰', '애플']):
            return '아이폰'
        elif any(word in value_lower for word in ['갤럭시', 'galaxy', '삼성']):
            return '갤럭시'
        return '스마트폰'
    
    # 6. education 처리
    if any(word in feature_lower for word in ['education', '학력', '대학']):
        if any(word in value_lower for word in ['대학원', '석사', '박사']):
            return '대학원생'
        elif '대학' in value_lower:
            return '대학생'
        return value
    
    # 7. lifestyle/interest 처리
    if any(word in feature_lower for word in ['lifestyle', 'interest', '라이프', '취미', '관심']):
        # 괄호 제거
        cleaned = re.sub(r'\([^)]*\)', '', value).strip()
        # 슬래시로 구분된 경우 첫 번째
        if '/' in cleaned:
            return cleaned.split('/')[0].strip()
        return cleaned if cleaned else value
    
    # 8. 기본 처리
    # 괄호 제거
    cleaned = re.sub(r'\([^)]*\)', '', value).strip()
    
    # 슬래시가 있으면 마지막 항목 (보통 가장 구체적)
    if '/' in cleaned:
        parts = [p.strip() for p in cleaned.split('/')]
        return parts[-1]
    
    # 공백으로 구분된 경우 첫 2단어
    words = cleaned.split()
    if len(words) > 2:
        return ' '.join(words[:2])
    
    return cleaned if cleaned else value


def clean_insight_text(insight: str) -> Optional[str]:
    """
    Claude가 생성한 인사이트 텍스트 정제
    """
    if not insight or len(insight) < 20:
        return None
    
    # 1. 기본 정제
    insight = insight.strip()
    
    # 2. 불완전한 문장 감지
    if not any(insight.endswith(end) for end in ['.', '다', '음', '니다', '습니다']):
        insight += "."
    
    # 3. 너무 긴 문장 자르기 (200자 제한)
    if len(insight) > 200:
        insight = insight[:197] + "..."
    
    return insight