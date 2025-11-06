"""
Claude AI 프롬프트 템플릿 모음
각 AI 모델(Opus, Haiku, Sonnet)의 역할에 맞는 프롬프트를 정의
"""

import json
from typing import Dict, List, Any


class PromptTemplates:
    """프롬프트 템플릿 관리 클래스"""
    
    # DB 스키마 로드 (나중에 실제 DB에서 가져오도록 변경 가능)
    @staticmethod
    def load_schema() -> Dict:
        """sample_schema.json 파일에서 스키마 로드"""
        try:
            with open('data/sample_schema.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 스키마 파일이 없으면 기본값 반환
            return {
                "table_name": "panels",
                "columns": {
                    "age": {"type": "INTEGER"},
                    "gender": {"type": "VARCHAR"},
                    "location": {"type": "VARCHAR"},
                    "job": {"type": "VARCHAR"}
                }
            }
    
    # =====================================================
    # OPUS: 자연어 질의 분석
    # =====================================================
    
    @staticmethod
    def query_analysis_prompt(user_query: str, schema: Dict = None) -> str:
        """
        사용자의 자연어 질의를 구조화된 데이터로 변환
        
        Args:
            user_query: 사용자가 입력한 자연어 질의
            schema: DB 스키마 정보
            
        Returns:
            Opus 모델에 전달할 프롬프트
        """
        if schema is None:
            schema = PromptTemplates.load_schema()
        
        # 허용된 값들을 프롬프트에 포함
        allowed_values_info = "\n".join([
            f"- {col}: {info.get('allowed_values', '제한 없음')}"
            for col, info in schema['columns'].items()
            if 'allowed_values' in info
        ])
        
        prompt = f"""당신은 마케팅 리서치 전문가입니다. 
사용자가 입력한 자연어 질의를 분석하여 패널(설문 응답자) 검색 조건으로 변환해야 합니다.

## 데이터베이스 스키마 정보
테이블명: {schema['table_name']}

사용 가능한 컬럼과 허용값:
{allowed_values_info}

## 사용자 질의
"{user_query}"

## 요구사항
1. 질의에서 추출 가능한 모든 검색 조건을 파악하세요
2. 나이 표현을 정확한 범위로 변환하세요 (예: "20대" → 20-29세)
3. 지역 표현을 정규화하세요 (예: "강남" → "서울", "부산 해운대" → "부산")
4. 직업/직군 표현을 스키마의 카테고리와 매칭하세요
5. 질의의 복잡도를 평가하세요 (simple/medium/complex)
   - simple: 단일 조건 또는 2-3개 기본 조건
   - medium: 4-5개 조건 또는 범위 조건 포함
   - complex: 6개 이상 조건 또는 복잡한 논리 관계

## 응답 형식 (JSON)
반드시 아래 형식의 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요.

{{
  "search_conditions": {{
    "age_range": {{"min": 20, "max": 29}},  // 나이 범위 (없으면 null)
    "gender": "남성",  // 성별 (없으면 null)
    "location": "서울",  // 지역 (없으면 null)
    "district": "강남구",  // 상세 지역 (없으면 null)
    "education": "대졸",  // 학력 (없으면 null)
    "job": "IT/기술",  // 직업 (없으면 null)
    "income_level": "중",  // 소득 (없으면 null)
    "marital_status": "미혼"  // 결혼 여부 (없으면 null)
  }},
  "search_intent": "타겟 그룹 찾기",  // 질의의 의도
  "complexity": "simple",  // 질의 복잡도
  "keywords": ["서울", "20대", "남성", "IT"],  // 핵심 키워드
  "estimated_result_size": "중간"  // 예상 결과 규모 (많음/중간/적음)
}}

주의: JSON 외의 다른 설명이나 마크다운은 포함하지 마세요."""

        return prompt
    
    # =====================================================
    # HAIKU: SQL 쿼리 생성 (대량 처리)
    # =====================================================
    
    @staticmethod
    def sql_generation_prompt(
        analyzed_query: Dict[str, Any],
        schema: Dict = None,
        target_count: int = 100
    ) -> str:
        """
        분석된 질의를 SQL 쿼리로 변환
        
        Args:
            analyzed_query: Opus가 분석한 검색 조건
            schema: DB 스키마 정보
            target_count: 목표 추출 인원 수
            
        Returns:
            Haiku 모델에 전달할 프롬프트
        """
        if schema is None:
            schema = PromptTemplates.load_schema()
        
        conditions = analyzed_query.get('search_conditions', {})
        
        prompt = f"""당신은 SQL 전문가입니다.
주어진 검색 조건을 PostgreSQL 쿼리로 변환해야 합니다.

## 데이터베이스 스키마
테이블명: {schema['table_name']}
컬럼: {', '.join(schema['columns'].keys())}

## 검색 조건
{json.dumps(conditions, ensure_ascii=False, indent=2)}

## 요구사항
1. WHERE 절을 사용하여 모든 조건을 정확히 반영하세요
2. 나이 범위는 BETWEEN을 사용하세요
3. NULL 값은 적절히 처리하세요
4. 목표 인원: {target_count}명 (LIMIT 사용)
5. 결과에는 id, age, gender, location, job을 포함하세요

## 응답 형식 (JSON)
반드시 아래 형식의 JSON만 반환하세요.

{{
  "sql_query": "SELECT id, age, gender, location, job FROM panels WHERE ...",
  "parameters": {{}},  // 파라미터화된 쿼리인 경우 사용
  "estimated_rows": 150,  // 예상 결과 행 수
  "execution_plan": "인덱스 활용: age, gender"  // 간단한 실행 계획
}}

주의: SQL 쿼리는 반드시 안전하고 최적화되어야 합니다."""

        return prompt
    
    # =====================================================
    # OPUS: 인사이트 추출 (고정밀)
    # =====================================================
    
    @staticmethod
    def insight_extraction_prompt(
        panel_data: List[Dict[str, Any]],
        original_query: str
    ) -> str:
        """
        검색된 패널 그룹에서 숨겨진 공통 특성 추출
        
        Args:
            panel_data: 검색된 패널 데이터 목록
            original_query: 원래 사용자 질의
            
        Returns:
            Opus 모델에 전달할 프롬프트
        """
        
        # 데이터를 텍스트로 변환 (샘플링)
        sample_size = min(50, len(panel_data))  # 최대 50개만 샘플링
        sampled_data = panel_data[:sample_size]
        
        data_summary = "\n".join([
            f"- ID {p.get('id', 'N/A')}: {p.get('age', 'N/A')}세, {p.get('gender', 'N/A')}, "
            f"{p.get('location', 'N/A')}, {p.get('job', 'N/A')}, "
            f"학력: {p.get('education', 'N/A')}, 소득: {p.get('income_level', 'N/A')}"
            for p in sampled_data
        ])
        
        prompt = f"""당신은 데이터 분석 전문가입니다.
검색된 패널 그룹을 분석하여 사용자가 명시하지 않은 숨겨진 공통 특성과 패턴을 찾아야 합니다.

## 원래 검색 질의
"{original_query}"

## 검색된 패널 데이터 (총 {len(panel_data)}명 중 {sample_size}명 샘플)
{data_summary}

## 분석 요구사항
1. **명시되지 않은 공통 특성** 찾기
   - 사용자가 검색 조건으로 제시하지 않았지만, 결과 그룹에서 두드러지는 특성
   - 예: "20대 서울 거주자"를 찾았는데 → 80%가 대졸, 70%가 미혼

2. **행동 패턴 추론**
   - 이 그룹이 가질 가능성이 높은 소비 성향, 라이프스타일
   
3. **추가 세분화 제안**
   - 이 그룹을 더 정교하게 타겟팅하기 위한 추가 조건 제안

4. **통계적 특징**
   - 나이 분포, 성비, 지역 분포 등의 실제 통계

## 응답 형식 (JSON)
{{
  "hidden_patterns": [
    {{
      "feature": "학력",
      "value": "대졸 이상",
      "percentage": 85,
      "insight": "이 그룹의 대부분이 고학력자입니다"
    }}
  ],
  "behavioral_insights": [
    "기술 친화적인 얼리어답터 성향이 강할 것으로 예상됩니다",
    "온라인 쇼핑 및 디지털 서비스 이용률이 높을 것입니다"
  ],
  "segmentation_suggestions": [
    "소득 수준으로 추가 세분화 (중상 이상 / 중 이하)",
    "거주 지역을 구 단위로 세분화 (강남권 / 비강남권)"
  ],
  "statistics": {{
    "age_distribution": {{"20-25세": 40, "26-29세": 60}},
    "gender_ratio": {{"남성": 55, "여성": 45}},
    "top_locations": {{"서울": 70, "경기": 20, "기타": 10}}
  }},
  "summary": "20대 서울 거주 IT 종사자 그룹은 고학력 미혼자가 많으며..."
}}"""

        return prompt
    
    # =====================================================
    # SONNET: 결과 검증 및 포맷팅 (DB 연동 후 사용)
    # =====================================================
    
    @staticmethod
    def result_validation_prompt(
        sql_result: List[Dict],
        original_conditions: Dict,
        target_count: int
    ) -> str:
        """
        SQL 실행 결과가 원래 검색 조건과 일치하는지 검증
        
        Args:
            sql_result: SQL 실행 결과
            original_conditions: 원래 검색 조건
            target_count: 목표 추출 수
            
        Returns:
            Sonnet 모델에 전달할 프롬프트
        """
        
        prompt = f"""당신은 데이터 품질 검증 전문가입니다.
SQL 실행 결과가 원래 검색 조건을 정확히 만족하는지 검증해야 합니다.

## 원래 검색 조건
{json.dumps(original_conditions, ensure_ascii=False, indent=2)}

## SQL 실행 결과
- 총 {len(sql_result)}개 레코드
- 목표: {target_count}개

샘플 데이터 (처음 5개):
{json.dumps(sql_result[:5], ensure_ascii=False, indent=2)}

## 검증 항목
1. 모든 레코드가 검색 조건을 만족하는가?
2. 목표 개수에 도달했는가? (부족/초과 여부)
3. 데이터 품질에 이상이 없는가? (NULL, 이상치 등)
4. 추가 필터링이 필요한가?

## 응답 형식 (JSON)
{{
  "is_valid": true,
  "validation_details": {{
    "condition_match": "모든 조건 만족",
    "count_status": "목표 달성" / "부족" / "초과",
    "data_quality": "정상" / "경고" / "오류"
  }},
  "issues": [],  // 발견된 문제점
  "recommendations": [],  // 개선 제안
  "filtered_result": []  // 추가 필터링된 결과 (필요시)
}}"""

        return prompt
    
    # =====================================================
    # 유틸리티: 프롬프트 조합
    # =====================================================
    
    @staticmethod
    def get_system_message(role: str) -> str:
        """
        각 모델의 역할에 맞는 시스템 메시지
        
        Args:
            role: 'analyzer', 'sql_generator', 'insight_extractor', 'validator'
        """
        messages = {
            'analyzer': "당신은 자연어 처리 전문가입니다. 사용자의 질의를 정확히 이해하고 구조화된 검색 조건으로 변환합니다.",
            'sql_generator': "당신은 데이터베이스 전문가입니다. 안전하고 최적화된 SQL 쿼리를 생성합니다.",
            'insight_extractor': "당신은 데이터 과학자입니다. 패널 데이터에서 의미 있는 인사이트와 패턴을 발견합니다.",
            'validator': "당신은 품질 관리 전문가입니다. 검색 결과의 정확성과 품질을 보증합니다."
        }
        return messages.get(role, "당신은 도움이 되는 AI 어시스턴트입니다.")