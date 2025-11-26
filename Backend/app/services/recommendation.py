# app/services/recommendation.py
"""
동적 추천 시스템 (v3.0)

v3.0 변경사항:
- detect_feature_group 정확도 개선 (단어 경계 검사)
- Drilldown 예외 추가 (서울 → 강남구는 허용)
- 필터링 강도 조절
"""
from typing import Dict, Any, List, Optional
import logging
import re  # 🔹 generate_recommendations에서 re 사용

logger = logging.getLogger(__name__)

class RecommendationEngine:
    
    def __init__(self):
        self.HIERARCHY_MAP = {
            'location': ['district', 'region_sub', '구', '군', '동'],
            'job': ['detail', 'job_detail', '세부', '직무'],
        }
        
        # 🔹 공통 특성으로 의미 없는 값(사소한 키워드) 필터링용
        self.TRIVIAL_KEYWORDS = [
            '대한민국', '한국', '응답자', '전체', '설문', 
            '미기재', '정보 없', '데이터 부족', '수집되지 않',
            '100% 미기재', '전원 미기재', '모두 미기재', '알 수 없음'
        ]

    def detect_feature_group(self, feature: str, value: str) -> Optional[str]:
        """
        feature + value를 보고 age / gender / location / job / income 중 어느 그룹인지 추정
        
        v3.0: 단어 경계를 고려한 정확한 감지
        """
        text = (feature + " " + value).lower()

        # 나이 관련 (더 정확하게)
        age_keywords = [
            r'\b나이\b', r'\b연령\b', r'\bage\b',
            r'\d{1,2}대\b',  # 10대, 20대, 30대...
            r'\d{1,2}세\b',  # 25세, 30세...
            r'청소년', r'청년', r'중년', r'노년'
        ]
        if any(re.search(pattern, text) for pattern in age_keywords):
            return 'age'

        # 성별 관련
        gender_keywords = [
            r'\b성별\b', r'\bgender\b',
            r'\b남성\b', r'\b여성\b', r'\b남자\b', r'\b여자\b',
            r'\b남\b', r'\b여\b'  # 단독으로 쓰일 때만
        ]
        if any(re.search(pattern, text) for pattern in gender_keywords):
            return 'gender'

        # 지역/거주 관련 (오탐 방지)
        location_keywords = [
            r'\b지역\b', r'\blocation\b', r'\b거주\b', r'\b살고\b',
            r'\b서울\b', r'\b경기\b', r'\b부산\b', r'\b대구\b',
            r'\b인천\b', r'\b광주\b', r'\b대전\b', r'\b울산\b',
            r'\b수도권\b', r'\b지방\b',
            r'\b구\s', r'\s동\b', r'\s군\b'  # 앞뒤 공백 확인 (구매, 동의 회피)
        ]
        if any(re.search(pattern, text) for pattern in location_keywords):
            return 'location'

        # 직업 관련 (키워드 확장)
        job_keywords = [
            r'\b직업\b', r'\bjob\b', r'\b직종\b', r'\b직군\b', r'\b직무\b',
            r'\b직장인\b', r'\b회사원\b', r'\b프리랜서\b',
            r'\bIT\b', r'\b개발자\b', r'\b엔지니어\b',
            r'\b사무직\b', r'\b전문직\b', r'\b서비스직\b'
        ]
        if any(re.search(pattern, text) for pattern in job_keywords):
            return 'job'

        # 소득 관련
        income_keywords = [
            r'\b소득\b', r'\bincome\b', r'\b연봉\b', r'\b월급\b', r'\b수입\b',
            r'\b고소득\b', r'\b중산층\b', r'\b저소득\b'
        ]
        if any(re.search(pattern, text) for pattern in income_keywords):
            return 'income'

        return None

    def is_drilldown(self, search_conditions: Dict, feature: str, value: str, group: str) -> bool:
        """
        Drilldown인지 판단 (서울 → 강남구 같은 경우)
        
        Returns:
            True: Drilldown이므로 허용 (제외하지 않음)
            False: Drilldown 아님
        """
        if group == 'location':
            has_location = search_conditions.get('location') is not None
            has_district = search_conditions.get('district') is not None
            
            # "서울" 조건만 있고, 패턴이 "강남구" 같은 세부 지역이면 Drilldown
            if has_location and not has_district:
                feature_lower = feature.lower()
                if any(kw in feature_lower for kw in ['구', '군', '동', 'district', '세부']):
                    logger.info(f"   ✅ Drilldown 허용 (지역): {feature} = {value}")
                    return True
        
        elif group == 'job':
            has_job = search_conditions.get('job') is not None
            
            # "IT" 조건 있고, 패턴이 "소프트웨어 개발" 같은 세부 직무면 Drilldown
            if has_job:
                feature_lower = feature.lower()
                if any(kw in feature_lower for kw in ['세부', '직무', 'detail', '분야']):
                    logger.info(f"   ✅ Drilldown 허용 (직업): {feature} = {value}")
                    return True
        
        return False

    def is_condition_applied(self, search_conditions: Dict, feature_group: str, value: str = "") -> bool:
        """
        자연어 질의(검색 조건)에 이미 포함된 그룹인지 확인하는 함수.
        예: 20대 서울 사는 남성 → age, location, gender는 True가 되도록.
        """
        if not search_conditions:
            return False
            
        if feature_group == 'age':
            return search_conditions.get('age_range') is not None
            
        elif feature_group == 'gender':
            return search_conditions.get('gender') is not None
            
        elif feature_group == 'location':
            # 수도권 등 상위 개념도 고려
            if '수도권' in value and (search_conditions.get('location') or search_conditions.get('district')):
                return True
            return (
                search_conditions.get('location') is not None or 
                search_conditions.get('district') is not None
            )
            
        elif feature_group == 'job':
            return search_conditions.get('job') is not None
            
        elif feature_group == 'income':
            return search_conditions.get('income_keyword') is not None
            
        elif feature_group in search_conditions:
            return search_conditions.get(feature_group) is not None
            
        return False

    def is_drilldown_allowed(self, search_conditions: Dict, feature: str) -> bool:
        """
        더 세부적인 드릴다운이 허용되는지 판단.
        예: location은 광역 → 기초로 내려갈 때만 허용 등.
        """
        feature_lower = feature.lower()
        
        # 위치 계층
        if any(keyword in feature_lower for keyword in self.HIERARCHY_MAP['location']):
            has_location = search_conditions.get('location') is not None
            has_district = search_conditions.get('district') is not None
            # location은 있는데 district는 없으면 → 드릴다운 허용
            return has_location and not has_district
        
        # 직업 계층
        if any(keyword in feature_lower for keyword in self.HIERARCHY_MAP['job']):
            return search_conditions.get('job') is not None
            
        return False

    # 🔻 기존 lift 계산 함수는 더 이상 사용하지 않으므로 제거(혹은 남겨도 되지만 여기선 삭제)
    # def calculate_lift(...):  # 제거됨
    #     ...

    def filter_patterns(
        self,
        patterns: List[Dict],
        search_conditions: Dict,
        full_statistics: Optional[Dict] = None  # 🔹 시그니처는 유지하지만 내부에서 사용 안 함
    ) -> List[Dict]:
        """
        1) 사소한 키워드(TRIVIAL_KEYWORDS) 제거
        2) 자연어 질의에 이미 포함된 조건(나이/성별/지역/직업/소득 등) 제거
        3) 나머지는 전부 남김 (lift/percentage 기준으로 걸러내지 않음)
        """
        filtered = []
        
        logger.info(f"🔍 필터링 시작: {len(patterns)}개 패턴")
        logger.info(f"   검색 조건: {search_conditions}")
        
        for pattern in patterns:
            feature_raw = pattern.get('feature', '')
            feature = feature_raw.lower()
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            # percentage는 이후 Top2 정렬에만 사용 (여기선 사용 X)
            percentage = pattern.get('percentage', 0)

            # 1) 사소한 키워드가 포함된 패턴은 제거
            if any(kw in feature or kw in value or kw in insight for kw in self.TRIVIAL_KEYWORDS):
                logger.debug(f"   ❌ Trivial 제거: {feature_raw}")
                continue

            # 2) 검색 조건과 중복되는지 확인
            should_exclude = False
            
            # 드릴다운 허용이 아닌 경우, 질의에 이미 포함된 그룹은 제외
            if not self.is_drilldown_allowed(search_conditions, feature):
                if any(w in feature for w in ['age', '나이', '연령']) and self.is_condition_applied(search_conditions, 'age', value):
                    should_exclude = True
                elif any(w in feature for w in ['gender', '성별']) and self.is_condition_applied(search_conditions, 'gender', value):
                    should_exclude = True
                elif any(w in feature for w in ['location', '지역', '거주']) and self.is_condition_applied(search_conditions, 'location', value):
                    should_exclude = True
                elif any(w in feature for w in ['job', '직업']) and self.is_condition_applied(search_conditions, 'job', value):
                    should_exclude = True
                elif any(w in feature for w in ['income', '소득']) and self.is_condition_applied(search_conditions, 'income', value):
                    should_exclude = True
                    logger.info(f"   ⚠️ 중복 조건 제거: {feature_raw} = {value} (group: {group})")

            if should_exclude:
                continue

            # 🔹 더 이상 lift / percentage 기준 필터링은 하지 않고,
            #     위 조건만 통과하면 모두 남김.
            filtered.append(pattern)

        logger.info(f"📊 필터링 완료: {len(patterns)}개 → {len(filtered)}개")
        return filtered

    def generate_recommendations(
        self,
        filtered_patterns: List[Dict],
        max_count: int = 2
    ) -> List[Dict]:
        """
        🔹 남아있는 패턴 중에서
            - percentage(비율)가 높은 순으로 정렬
            - Top N(max_count)만 추천으로 사용
        🔹 lift나 추가적인 점수 계산 없음
        """
        recommendations = []
        
        # 🔸 percentage 기준으로 내림차순 정렬 후 Top N만 사용
        sorted_patterns = sorted(
            filtered_patterns,
            key=lambda p: p.get('percentage', 0),
            reverse=True
        )

        for pattern in sorted_patterns[:max_count]:
            feature = pattern.get('feature', '')
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            
            # 🔹 끝 문장 정리: '입니다입니다' 같은 중복 제거
            cleaned_insight = insight.strip()
            cleaned_insight = re.sub(r'(입니다|합니다|습니다)+$', r'\1', cleaned_insight)
            if not cleaned_insight.endswith('.'):
                cleaned_insight += "."
            
            # 버튼에 들어갈 queryPart 정리
            query_part = value
            if '(' in query_part:
                query_part = query_part.split('(')[0].strip()
            
            if len(query_part) < 1 or len(query_part) > 15:
                query_part = feature
            
            button_text = f"+ '{query_part}' 추가"
            
            recommendations.append({
                "id": f"rec-{feature.replace(' ', '-')}-{value[:5]}",
                "text": cleaned_insight,
                "action": {
                    "buttonText": button_text,
                    "data": {
                        "type": "insight",
                        "value": value,
                        "queryPart": query_part
                    }
                }
            })
            
        return recommendations

recommendation_engine = RecommendationEngine()
