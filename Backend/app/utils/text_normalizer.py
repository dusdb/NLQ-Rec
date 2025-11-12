"""
텍스트 정규화 및 검색어 증강 유틸리티
사용자 입력을 표준화하고 동의어를 처리합니다.
"""

import re
from typing import Dict, List, Tuple, Optional


class TextNormalizer:
    """텍스트 정규화 및 전처리 클래스"""
    
    # 나이 표현 매핑
    AGE_PATTERNS = {
        r'10대': (10, 19),
        r'20대\s*초반': (20, 24),
        r'20대\s*중반': (25, 27),
        r'20대\s*후반': (28, 29),
        r'20대': (20, 29),
        r'30대\s*초반': (30, 34),
        r'30대\s*중반': (35, 37),
        r'30대\s*후반': (38, 39),
        r'30대': (30, 39),
        r'40대': (40, 49),
        r'50대': (50, 59),
        r'60대\s*이상': (60, 100),
        r'청소년': (13, 19),
        r'청년': (20, 34),
        r'중장년': (40, 64),
        r'노년': (65, 100),
    }
    
    # 성별 표현 정규화
    GENDER_MAPPING = {
        '남자': '남성',
        '남': '남성',
        'male': '남성',
        'm': '남성',
        '여자': '여성',
        '여': '여성',
        'female': '여성',
        'f': '여성',
    }
    
    # 지역 표현 정규화 (시/도 단위)
    LOCATION_MAPPING = {
        # 서울 구 → 서울
        '강남': '서울',
        '강남구': '서울',
        '서초': '서울',
        '서초구': '서울',
        '송파': '서울',
        '송파구': '서울',
        '강동': '서울',
        '강동구': '서울',
        '마포': '서울',
        '마포구': '서울',
        '용산': '서울',
        '용산구': '서울',
        '종로': '서울',
        '종로구': '서울',
        '중구': '서울',  # 서울 중구
        '성동': '서울',
        '성동구': '서울',
        '광진': '서울',
        '광진구': '서울',
        '동대문': '서울',
        '동대문구': '서울',
        '중랑': '서울',
        '중랑구': '서울',
        '성북': '서울',
        '성북구': '서울',
        '강북': '서울',
        '강북구': '서울',
        '도봉': '서울',
        '도봉구': '서울',
        '노원': '서울',
        '노원구': '서울',
        '은평': '서울',
        '은평구': '서울',
        '서대문': '서울',
        '서대문구': '서울',
        '양천': '서울',
        '양천구': '서울',
        '강서': '서울',
        '강서구': '서울',
        '구로': '서울',
        '구로구': '서울',
        '금천': '서울',
        '금천구': '서울',
        '영등포': '서울',
        '영등포구': '서울',
        '동작': '서울',
        '동작구': '서울',
        '관악': '서울',
        '관악구': '서울',
        
        # 부산 구 → 부산
        '해운대': '부산',
        '해운대구': '부산',
        '남구': '부산',  # 부산 남구
        '동래': '부산',
        '동래구': '부산',
        '수영': '부산',
        '수영구': '부산',
        
        # 약어
        '서울시': '서울',
        '부산시': '부산',
        '대구시': '대구',
        '인천시': '인천',
        '광주시': '광주',
        '대전시': '대전',
        '울산시': '울산',
        '세종시': '세종',
        
        # 도
        '경기도': '경기',
        '강원도': '강원',
        '충청북도': '충북',
        '충북도': '충북',
        '충청남도': '충남',
        '충남도': '충남',
        '전라북도': '전북',
        '전북도': '전북',
        '전라남도': '전남',
        '전남도': '전남',
        '경상북도': '경북',
        '경북도': '경북',
        '경상남도': '경남',
        '경남도': '경남',
        '제주도': '제주',
        '제주특별자치도': '제주',
    }
    
    # 직업 카테고리 매핑
    JOB_MAPPING = {
        # IT/기술
        '개발자': 'IT/기술',
        '프로그래머': 'IT/기술',
        '소프트웨어': 'IT/기술',
        '엔지니어': 'IT/기술',
        '데이터': 'IT/기술',
        'it': 'IT/기술',
        '기술직': 'IT/기술',
        
        # 금융/보험
        '은행원': '금융/보험',
        '금융': '금융/보험',
        '보험': '금융/보험',
        '증권': '금융/보험',
        
        # 제조/생산
        '제조': '제조/생산',
        '생산': '제조/생산',
        '공장': '제조/생산',
        
        # 유통/판매
        '판매': '유통/판매',
        '영업': '유통/판매',
        '유통': '유통/판매',
        '마케팅': '유통/판매',
        
        # 교육
        '교사': '교육',
        '강사': '교육',
        '선생님': '교육',
        '교수': '교육',
        
        # 의료/보건
        '의사': '의료/보건',
        '간호사': '의료/보건',
        '약사': '의료/보건',
        '의료': '의료/보건',
        
        # 공무원
        '공무원': '공무원',
        '공직': '공무원',
        
        # 자영업
        '자영업': '자영업',
        '사업': '자영업',
        '가게': '자영업',
        
        # 학생
        '학생': '학생',
        '대학생': '학생',
        
        # 주부
        '주부': '주부',
        '가정주부': '주부',
        
        # 무직
        '무직': '무직',
        '백수': '무직',
        '취준생': '무직',
    }
    
    # 학력 표현 정규화
    EDUCATION_MAPPING = {
        '고졸': '고졸 이하',
        '고등학교': '고졸 이하',
        '중졸': '고졸 이하',
        '재학': '대학 재학',
        '대학생': '대학 재학',
        '대학교': '대졸',
        '대학': '대졸',
        '학사': '대졸',
        '석사': '대학원 이상',
        '박사': '대학원 이상',
        '대학원': '대학원 이상',
    }
    
    # 소득 수준 정규화
    INCOME_MAPPING = {
        '저소득': '하',
        '낮음': '하',
        '중간': '중',
        '보통': '중',
        '평균': '중',
        '높음': '상',
        '고소득': '상',
    }
    
    # 결혼 여부 정규화
    MARITAL_MAPPING = {
        '미혼': '미혼',
        '싱글': '미혼',
        '독신': '미혼',
        '결혼': '기혼',
        '기혼': '기혼',
        '배우자': '기혼',
        '부부': '기혼',
    }
    
    @classmethod
    def extract_age_range(cls, text: str) -> Optional[Tuple[int, int]]:
        """
        텍스트에서 나이 범위 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            (min_age, max_age) 튜플 또는 None
        """
        # 명시적 범위 (예: "25-35세", "30~40살")
        range_pattern = r'(\d{2})\s*[-~]\s*(\d{2})\s*[세살]?'
        match = re.search(range_pattern, text)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        
        # 단일 나이 (예: "25세", "30살")
        single_pattern = r'(\d{2})\s*[세살]'
        match = re.search(single_pattern, text)
        if match:
            age = int(match.group(1))
            return (age, age)
        
        # 패턴 매칭 (예: "20대", "30대 초반")
        for pattern, age_range in cls.AGE_PATTERNS.items():
            if re.search(pattern, text):
                return age_range
        
        return None
    
    @classmethod
    def normalize_gender(cls, text: str) -> Optional[str]:
        """성별 표현 정규화"""
        text_lower = text.lower().strip()
        return cls.GENDER_MAPPING.get(text_lower)
    
    @classmethod
    def normalize_location(cls, text: str) -> Optional[str]:
        """지역 표현 정규화"""
        text = text.strip()
        
        # 직접 매핑
        if text in cls.LOCATION_MAPPING:
            return cls.LOCATION_MAPPING[text]
        
        # 부분 매칭 (예: "강남에 사는" → "서울")
        for key, value in cls.LOCATION_MAPPING.items():
            if key in text:
                return value
        
        # 이미 표준 지역명이면 그대로 반환
        standard_locations = [
            '서울', '부산', '대구', '인천', '광주', 
            '대전', '울산', '세종', '경기', '강원',
            '충북', '충남', '전북', '전남', '경북', '경남', '제주'
        ]
        if text in standard_locations:
            return text
        
        return None
    
    @classmethod
    def normalize_job(cls, text: str) -> Optional[str]:
        """직업 표현 정규화"""
        text_lower = text.lower().strip()
        
        # 직접 매핑
        if text_lower in cls.JOB_MAPPING:
            return cls.JOB_MAPPING[text_lower]
        
        # 부분 매칭
        for key, value in cls.JOB_MAPPING.items():
            if key in text_lower:
                return value
        
        return None
    
    @classmethod
    def normalize_education(cls, text: str) -> Optional[str]:
        """학력 표현 정규화"""
        for key, value in cls.EDUCATION_MAPPING.items():
            if key in text:
                return value
        return None
    
    @classmethod
    def normalize_income(cls, text: str) -> Optional[str]:
        """소득 수준 정규화"""
        for key, value in cls.INCOME_MAPPING.items():
            if key in text:
                return value
        return None
    
    @classmethod
    def normalize_marital_status(cls, text: str) -> Optional[str]:
        """결혼 여부 정규화"""
        for key, value in cls.MARITAL_MAPPING.items():
            if key in text:
                return value
        return None
    
    @classmethod
    def extract_all_features(cls, text: str) -> Dict[str, any]:
        """
        텍스트에서 모든 특징 추출 및 정규화
        
        Args:
            text: 사용자 입력 텍스트
            
        Returns:
            추출된 특징 딕셔너리
        """
        features = {}
        
        # 나이
        age_range = cls.extract_age_range(text)
        if age_range:
            features['age_range'] = {'min': age_range[0], 'max': age_range[1]}
        
        # 성별
        gender = cls.normalize_gender(text)
        if gender:
            features['gender'] = gender
        
        # 지역
        location = cls.normalize_location(text)
        if location:
            features['location'] = location
        
        # 직업
        job = cls.normalize_job(text)
        if job:
            features['job'] = job
        
        # 학력
        education = cls.normalize_education(text)
        if education:
            features['education'] = education
        
        # 소득
        income = cls.normalize_income(text)
        if income:
            features['income_level'] = income
        
        # 결혼 여부
        marital = cls.normalize_marital_status(text)
        if marital:
            features['marital_status'] = marital
        
        return features
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        텍스트 정제 (공백, 특수문자 등)
        
        Args:
            text: 입력 텍스트
            
        Returns:
            정제된 텍스트
        """
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text