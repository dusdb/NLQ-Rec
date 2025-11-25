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
import re

logger = logging.getLogger(__name__)

class RecommendationEngine:
    
    def __init__(self):
        self.HIERARCHY_MAP = {
            'location': ['district', 'region_sub', '구', '군', '동'],
            'job': ['detail', 'job_detail', '세부', '직무'],
        }
        
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
        if not search_conditions:
            return False
            
        if feature_group == 'age':
            return search_conditions.get('age_range') is not None
            
        elif feature_group == 'gender':
            return search_conditions.get('gender') is not None
            
        elif feature_group == 'location':
            if '수도권' in value and (search_conditions.get('location') or search_conditions.get('district')):
                return True
            return (search_conditions.get('location') is not None or 
                    search_conditions.get('district') is not None)
            
        elif feature_group == 'job':
            return search_conditions.get('job') is not None
            
        elif feature_group == 'income':
            return search_conditions.get('income_keyword') is not None
            
        elif feature_group in search_conditions:
            return search_conditions.get(feature_group) is not None
            
        return False

    def calculate_lift(
        self,
        pattern_percentage: float,
        feature_key: str,
        value_key: str,
        full_statistics: Dict
    ) -> Optional[float]:
        if not full_statistics:
            return None
            
        stat_key_map = {
            'job': 'job_distribution', '직업': 'job_distribution',
            'location': 'location_distribution', '지역': 'location_distribution',
            'age': 'age_distribution', '나이': 'age_distribution',
            'gender': 'gender_distribution', '성별': 'gender_distribution',
            'income': 'income_distribution', '소득': 'income_distribution'
        }
        
        target_stat_key = None
        for key, stat_name in stat_key_map.items():
            if key in feature_key.lower():
                target_stat_key = stat_name
                break
        
        if not target_stat_key or target_stat_key not in full_statistics:
            return None
            
        stats = full_statistics[target_stat_key]
        total_count = full_statistics.get('total_count', 1)
        
        baseline_count = 0
        for k, v in stats.items():
            if str(value_key) in str(k) or str(k) in str(value_key):
                baseline_count += v
                
        if baseline_count == 0:
            return None
            
        baseline_percentage = (baseline_count / total_count) * 100
        if baseline_percentage == 0:
            return None
            
        return pattern_percentage / baseline_percentage

    def filter_patterns(
        self,
        patterns: List[Dict],
        search_conditions: Dict,
        full_statistics: Optional[Dict] = None
    ) -> List[Dict]:
        """
        패턴 필터링 (v3.0)
        
        개선사항:
        - 정확한 그룹 감지
        - Drilldown 예외 추가
        - 원래 로직(percentage 30%) 유지
        """
        filtered = []
        
        logger.info(f"🔍 필터링 시작: {len(patterns)}개 패턴")
        logger.info(f"   검색 조건: {search_conditions}")
        
        for pattern in patterns:
            feature_raw = pattern.get('feature', '')
            feature = feature_raw.lower()
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            percentage = pattern.get('percentage', 0)
            
            # 1) 사소한 패턴 제거
            if any(kw in feature or kw in value or kw in insight for kw in self.TRIVIAL_KEYWORDS):
                logger.debug(f"   ❌ Trivial 제거: {feature_raw}")
                continue

            # 2) 그룹 감지
            group = self.detect_feature_group(feature_raw, value)
            logger.debug(f"   🔎 '{feature_raw}' = '{value}' → group: {group}")
            
            # 3) 중복 조건 체크 (Drilldown 예외 포함)
            should_exclude = False
            
            if group and self.is_condition_applied(search_conditions, group, value):
                # Drilldown인지 확인
                if self.is_drilldown(search_conditions, feature_raw, value, group):
                    # Drilldown이면 제외하지 않음
                    should_exclude = False
                else:
                    # 일반 중복이면 제외
                    should_exclude = True
                    logger.info(f"   ⚠️ 중복 조건 제거: {feature_raw} = {value} (group: {group})")

            if should_exclude:
                continue

            # 4) 통계적 유의성 (원래 로직)
            is_boring_region = any(r in value for r in ['수도권', '서울', '경기'])
            min_lift_threshold = 2.0 if is_boring_region else 1.3
            
            is_significant = False
            lift = self.calculate_lift(percentage, feature_raw, value, full_statistics)
            
            if lift is not None:
                if lift >= min_lift_threshold:
                    is_significant = True
                    logger.info(f"   ✅ 발견 (Lift): {feature_raw}={value} (Lift: {lift:.2f})")
                else:
                    logger.debug(f"   ❌ Lift 부족: {feature_raw}={value} (Lift: {lift:.2f} < {min_lift_threshold})")
            elif percentage >= 30:
                is_significant = True
                logger.info(f"   ✅ 발견 (비율): {feature_raw}={value} ({percentage}%)")
            
            if is_significant:
                filtered.append(pattern)

        logger.info(f"📊 필터링 완료: {len(patterns)}개 → {len(filtered)}개")
        return filtered

    def generate_recommendations(
        self,
        filtered_patterns: List[Dict],
        max_count: int = 2
    ) -> List[Dict]:
        recommendations = []
        
        for pattern in filtered_patterns[:max_count]:
            feature = pattern.get('feature', '')
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            
            cleaned_insight = insight.strip()
            cleaned_insight = re.sub(r'(입니다|합니다|습니다)+$', r'\1', cleaned_insight)
            if not cleaned_insight.endswith('.'):
                cleaned_insight += "."

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