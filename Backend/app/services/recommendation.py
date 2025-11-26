# app/services/recommendation.py
"""
동적 추천 시스템
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
        
        for pattern in patterns:
            feature = pattern.get('feature', '').lower()
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            # percentage는 이후 Top2 정렬에만 사용 (여기선 사용 X)
            percentage = pattern.get('percentage', 0)

            # 1) 사소한 키워드가 포함된 패턴은 제거
            if any(kw in feature or kw in value or kw in insight for kw in self.TRIVIAL_KEYWORDS):
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

            if should_exclude:
                print(f"   ⚠️ 필터링(중복 조건): {feature} - {value}")
                continue

            # 🔹 더 이상 lift / percentage 기준 필터링은 하지 않고,
            #     위 조건만 통과하면 모두 남김.
            filtered.append(pattern)

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
