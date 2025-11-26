# app/services/recommendation.py
"""
동적 추천 시스템
"""
from typing import Dict, Any, List, Optional
import logging

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

    def is_drilldown_allowed(self, search_conditions: Dict, feature: str) -> bool:
        feature_lower = feature.lower()
        
        if any(keyword in feature_lower for keyword in self.HIERARCHY_MAP['location']):
            has_location = search_conditions.get('location') is not None
            has_district = search_conditions.get('district') is not None
            return has_location and not has_district
        
        if any(keyword in feature_lower for keyword in self.HIERARCHY_MAP['job']):
            return search_conditions.get('job') is not None
            
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
        filtered = []
        
        for pattern in patterns:
            feature = pattern.get('feature', '').lower()
            value = pattern.get('value', '')
            insight = pattern.get('insight', '')
            percentage = pattern.get('percentage', 0)
            
            if any(kw in feature or kw in value or kw in insight for kw in self.TRIVIAL_KEYWORDS):
                continue

            should_exclude = False
            
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

            is_boring_region = any(r in value for r in ['수도권', '서울', '경기'])
            min_lift_threshold = 2.0 if is_boring_region else 1.3  # 수도권은 2배 이상이어야 추천
            
            is_significant = False
            
            lift = self.calculate_lift(percentage, feature, value, full_statistics)
            
            if lift is not None:
                if lift >= min_lift_threshold:
                    is_significant = True
                    print(f"발견: {feature}={value} (Lift: {lift:.2f})")
                else:
                    print(f"제외: {feature}={value} (Lift: {lift:.2f} < {min_lift_threshold})")
            
            elif percentage >= 30:
                is_significant = True
            
            if is_significant:
                filtered.append(pattern)
            else:
                pass 

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
            for suffix in ['입니다.', '습니다.', '합니다.', '입니다', '습니다', '합니다']:
                if cleaned_insight.endswith(suffix):
                    cleaned_insight = cleaned_insight[:-len(suffix)]
                    if not cleaned_insight.endswith('.'):
                        cleaned_insight += "."
                    break
            
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