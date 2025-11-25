"""
검색어 파싱 모듈 (Refactored)
불필요한 추론 로직 제거 및 구조 경량화
"""

import re
from typing import Dict, List, Any, Optional
from app.utils.text_normalizer import TextNormalizer

class QueryParser:
    STOPWORDS = {
        '을', '를', '이', '가', '은', '는', '의', '에', '에서', '으로', '로',
        '과', '와', '하는', '있는', '되는', '하다', '이다', '있다',
        '중', '중에서', '찾아', '찾아줘', '검색', '알려줘', '보여줘',
        '사람', '사람들', '패널', '응답자', '대상', '추출', '선택'
    }

    @classmethod
    def parse_query(cls, query: str) -> Dict[str, Any]:

        clean_query = TextNormalizer.clean_text(query)
        features = TextNormalizer.extract_all_features(clean_query)

        parsed = {
            'original_query': query,
            'search_conditions': features,
            'keywords': cls._extract_keywords(clean_query),
            'suggestions': cls._remove_duplicate_suggestions(features, clean_query),
            'complexity': 'simple',
            'metadata': {
                'intent': cls._analyze_intent(query),
                'feature_count': len(features)
            }
        }
        
        return parsed

    @classmethod
    def _extract_keywords(cls, text: str) -> List[str]:
        return [
            word for word in text.split() 
            if len(word) >= 2 and word not in cls.STOPWORDS
        ]

    @staticmethod
    def _analyze_intent(query: str) -> str:
        query_set = set(query.split())
        if any(w in query_set for w in ['분석', '통계', '비율']): return '분석/통계'
        if any(w in query_set for w in ['몇', '수', '규모']): return '규모 파악'
        return '타겟 그룹 검색'
    
    @classmethod
    def _remove_duplicate_suggestions(cls, applied_features: Dict, query: str) -> List[str]:

        suggestions = []

        if 'location' not in applied_features:
            suggestions.append("지역 조건 추가")
        
        if 'age_range' not in applied_features:
            suggestions.append("나이 조건 추가")
        
        if 'job' not in applied_features:
            suggestions.append("직업 조건 추가")
        
        return suggestions
    
    @staticmethod
    def full_parse_and_augment(query: str) -> Dict[str, Any]:
        return QueryParser.parse_query(query)
    
    @staticmethod
    def extract_target_count(query: str) -> Optional[int]:
        """
        쿼리에서 인원수 추출
        예: "30명", "50명으로", "100명 추출"
        """
        # "30명", "50명으로", "100명 추출" 등
        pattern = r'(\d+)\s*명'
        match = re.search(pattern, query)
        
        if match:
            count = int(match.group(1))
            print(f"✅ 타겟 인원수 추출: {count}명")
            return count
        
        return None