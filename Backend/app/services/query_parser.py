"""
검색어 파싱 및 증강 모듈
사용자 질의를 분석하고 추가 검색 조건을 자동으로 생성
"""

from typing import Dict, List, Optional, Any
from app.utils.text_normalizer import TextNormalizer


class QueryParser:
    """검색어 파싱 및 증강 클래스"""
    
    @staticmethod
    def parse_query(query: str) -> Dict[str, Any]:
        """
        자연어 질의를 파싱하여 구조화된 데이터로 변환
        
        Args:
            query: 사용자 입력 자연어 질의
            
        Returns:
            파싱된 검색 조건 딕셔너리
        """
        # 텍스트 정제
        clean_query = TextNormalizer.clean_text(query)
        
        # 모든 특징 추출
        features = TextNormalizer.extract_all_features(clean_query)
        
        # 추가 메타데이터
        result = {
            'original_query': query,
            'cleaned_query': clean_query,
            'extracted_features': features,
            'keywords': QueryParser._extract_keywords(clean_query),
            'complexity': QueryParser._assess_complexity(features),
        }
        
        return result
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """
        텍스트에서 핵심 키워드 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            키워드 리스트
        """
        # 불용어 리스트
        stopwords = [
            '을', '를', '이', '가', '은', '는', '의', '에', '에서', '으로', '로',
            '과', '와', '하는', '있는', '되는', '하다', '이다', '있다',
            '중', '중에서', '찾아', '찾아줘', '검색', '알려줘', '보여줘',
            '사람', '사람들', '패널', '응답자', '대상'
        ]
        
        # 공백으로 분리
        words = text.split()
        
        # 불용어 제거 및 2글자 이상 단어만 선택
        keywords = [
            word for word in words 
            if len(word) >= 2 and word not in stopwords
        ]
        
        return keywords
    
    @staticmethod
    def _assess_complexity(features: Dict[str, Any]) -> str:
        """
        질의 복잡도 평가
        
        Args:
            features: 추출된 특징들
            
        Returns:
            'simple', 'medium', 'complex'
        """
        feature_count = len(features)
        
        if feature_count <= 2:
            return 'simple'
        elif feature_count <= 4:
            return 'medium'
        else:
            return 'complex'
    
    @staticmethod
    def augment_query(parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        파싱된 질의를 증강 (동의어, 관련 조건 추가)
        
        Args:
            parsed_query: 파싱된 질의
            
        Returns:
            증강된 질의
        """
        features = parsed_query['extracted_features']
        augmented = parsed_query.copy()
        suggestions = []
        
        # 나이대에 따른 추가 조건 제안
        if 'age_range' in features:
            age_min = features['age_range']['min']
            age_max = features['age_range']['max']
            
            if age_min >= 20 and age_max <= 29:
                suggestions.append({
                    'type': 'demographic',
                    'field': 'marital_status',
                    'value': '미혼',
                    'reason': '20대는 대부분 미혼입니다'
                })
            
            if age_min >= 40:
                suggestions.append({
                    'type': 'demographic',
                    'field': 'marital_status',
                    'value': '기혼',
                    'reason': '40대 이상은 기혼일 가능성이 높습니다'
                })
        
        # 직업에 따른 추가 조건 제안
        if 'job' in features:
            job = features['job']
            
            if job == 'IT/기술':
                suggestions.append({
                    'type': 'education',
                    'field': 'education',
                    'value': '대졸',
                    'reason': 'IT 직종은 대졸 이상이 많습니다'
                })
                suggestions.append({
                    'type': 'location',
                    'field': 'location',
                    'value': '서울',
                    'reason': 'IT 기업이 서울에 집중되어 있습니다'
                })
            
            elif job == '학생':
                suggestions.append({
                    'type': 'demographic',
                    'field': 'marital_status',
                    'value': '미혼',
                    'reason': '학생은 대부분 미혼입니다'
                })
        
        # 지역에 따른 추가 조건 제안
        if 'location' in features:
            location = features['location']
            
            if location == '서울':
                suggestions.append({
                    'type': 'income',
                    'field': 'income_level',
                    'value': '중',
                    'reason': '서울 거주자는 평균 이상 소득일 가능성이 높습니다'
                })
        
        augmented['suggestions'] = suggestions
        
        return augmented
    
    @staticmethod
    def build_search_conditions(augmented_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        증강된 질의를 최종 검색 조건으로 변환
        
        Args:
            augmented_query: 증강된 질의
            
        Returns:
            검색 조건 딕셔너리
        """
        features = augmented_query['extracted_features']
        
        # 기본 검색 조건
        search_conditions = {}
        
        # 나이
        if 'age_range' in features:
            search_conditions['age_range'] = features['age_range']
        
        # 성별
        if 'gender' in features:
            search_conditions['gender'] = features['gender']
        
        # 지역
        if 'location' in features:
            search_conditions['location'] = features['location']
        
        # 직업
        if 'job' in features:
            search_conditions['job'] = features['job']
        
        # 학력
        if 'education' in features:
            search_conditions['education'] = features['education']
        
        # 소득
        if 'income_level' in features:
            search_conditions['income_level'] = features['income_level']
        
        # 결혼 여부
        if 'marital_status' in features:
            search_conditions['marital_status'] = features['marital_status']
        
        return search_conditions
    
    @staticmethod
    def generate_search_intent(query: str, features: Dict[str, Any]) -> str:
        """
        검색 의도 파악
        
        Args:
            query: 원본 질의
            features: 추출된 특징
            
        Returns:
            검색 의도 설명
        """
        # 키워드 기반 의도 파악
        if any(keyword in query for keyword in ['찾아', '검색', '추출', '선택']):
            return '타겟 그룹 찾기'
        elif any(keyword in query for keyword in ['분석', '특성', '패턴']):
            return '그룹 특성 분석'
        elif any(keyword in query for keyword in ['몇 명', '규모', '수']):
            return '그룹 규모 파악'
        else:
            return '일반 검색'
    
    @staticmethod
    def estimate_result_size(features: Dict[str, Any]) -> str:
        """
        예상 결과 규모 추정
        
        Args:
            features: 추출된 특징
            
        Returns:
            '많음', '중간', '적음'
        """
        # 조건이 많을수록 결과가 적을 것으로 예상
        feature_count = len(features)
        
        if feature_count <= 2:
            return '많음'
        elif feature_count <= 4:
            return '중간'
        else:
            return '적음'
    
    @staticmethod
    def full_parse_and_augment(query: str) -> Dict[str, Any]:
        """
        전체 파이프라인: 파싱 → 증강 → 검색 조건 생성
        
        Args:
            query: 사용자 입력 자연어 질의
            
        Returns:
            최종 결과 딕셔너리
        """
        # 1. 파싱
        parsed = QueryParser.parse_query(query)
        
        # 2. 증강
        augmented = QueryParser.augment_query(parsed)
        
        # 3. 검색 조건 생성
        search_conditions = QueryParser.build_search_conditions(augmented)
        
        # 4. 검색 의도 파악
        search_intent = QueryParser.generate_search_intent(
            query, 
            parsed['extracted_features']
        )
        
        # 5. 결과 규모 추정
        estimated_size = QueryParser.estimate_result_size(
            parsed['extracted_features']
        )
        
        # 최종 결과 조합
        result = {
            'original_query': query,
            'search_conditions': search_conditions,
            'search_intent': search_intent,
            'complexity': parsed['complexity'],
            'keywords': parsed['keywords'],
            'estimated_result_size': estimated_size,
            'suggestions': augmented.get('suggestions', []),
            'metadata': {
                'feature_count': len(parsed['extracted_features']),
                'has_age_filter': 'age_range' in search_conditions,
                'has_location_filter': 'location' in search_conditions,
                'has_job_filter': 'job' in search_conditions,
            }
        }
        
        return result