"""
Claude AI 프롬프트 템플릿 모음
Updated for: panel_master table schema (Neon DB)
"""

import json
from typing import Dict, List, Any

class PromptTemplates:
    """프롬프트 템플릿 관리 클래스"""
    
    # =====================================================
    # 1. DB 스키마 로드 (panel_master 기준)
    # =====================================================
    
    @staticmethod
    def load_schema() -> Dict:
        """DB 스키마 정보 반환 (실제 DB 구조 반영)"""
        return {
            "table_name": "panel_master",
            "columns": {
                "panel_id": {"type": "VARCHAR", "desc": "패널 ID (PK)"},
                "birth_year": {"type": "INTEGER", "desc": "출생년도 (예: 1990)"},
                "gender": {"type": "VARCHAR", "desc": "성별 (남성/여성)"},
                "region_main": {"type": "VARCHAR", "desc": "시/도 (예: 서울, 경기)"},
                "region_sub": {"type": "VARCHAR", "desc": "구/군 (예: 강남구)"},
                "job_category": {"type": "VARCHAR", "desc": "직업군 (예: IT/기술)"},
                "job_detail": {"type": "VARCHAR", "desc": "상세 직업"},
                "education": {"type": "VARCHAR", "desc": "학력"},
                "marital_status": {"type": "VARCHAR", "desc": "결혼 여부"}
            }
        }
    
    # =====================================================
    # 2. 자연어 질의 분석 (OPUS)
    # =====================================================
    
    @staticmethod
    def query_analysis_prompt(user_query: str, schema: Dict = None) -> str:
        if schema is None:
            schema = PromptTemplates.load_schema()
        
        prompt = f"""당신은 팩트 기반의 검색 조건 생성기입니다.
사용자의 질의를 분석하여 완벽한 JSON 형식의 검색 조건을 반환하세요.

## 데이터베이스 정보
테이블명: {schema['table_name']}
컬럼: 
- birth_year (나이 계산용)
- gender (성별)
- region_main (시/도), region_sub (구/군)
- job_category (직업군), job_detail (상세 직업)

## 사용자 질의
"{user_query}"

## 🚨 절대 규칙 (Strict Rules) - 위반 시 에러 처리됨
1. **추론 절대 금지:** 사용자가 언급하지 않은 조건은 무조건 null로 두세요.
   - 예: "야근" -> job="야근" (O), job="IT" (X)
   - 예: "직장인" -> job="직장인" (O), age_range="20-30" (X)
2. **있는 그대로 매핑:** 사용자의 단어를 변형하지 말고 그대로 검색어에 넣으세요.
3. **JSON 형식 엄수:** 아래 형식을 필드를 빠뜨리지 말고 정확히 지키세요.

## 필수 응답 형식 (JSON Schema)
{{
  "search_conditions": {{
    "age_range": {{ "min": 20, "max": 29 }} 또는 null,
    "gender": "남성" 또는 "여성" 또는 null,
    "location": "서울" (시/도) 또는 null,
    "district": "강남구" (구/군) 또는 null,
    "job": "검색어" (직업 관련 키워드) 또는 null
  }},
  "search_intent": "타겟 그룹 찾기" 또는 "통계 조회",
  "keywords": ["추출된", "핵심", "단어들"],
  "complexity": "simple" 또는 "medium" 또는 "complex",
  "estimated_result_size": "unknown"
}}

주의: 주석이나 설명 없이 오직 JSON 코드만 반환하세요."""
        return prompt
    
    # =====================================================
    # 3. SQL 쿼리 생성 (HAIKU) - 핵심 수정됨!
    # =====================================================
    
    @staticmethod
    def sql_generation_prompt(
        analyzed_query: Dict[str, Any],
        schema: Dict = None,
        target_count: int = 100
    ) -> str:
        if schema is None:
            schema = PromptTemplates.load_schema()
        
        conditions = analyzed_query.get('search_conditions', {})
        
        # SQL 힌트 생성 로직
        sql_hints = []
        current_year = 2025  # 기준 연도

        # (1) 나이 -> 출생년도 변환
        if 'age_range' in conditions:
            age_range = conditions['age_range']
            min_age = age_range.get('min', 0)
            max_age = age_range.get('max', 100)
            # 2025년 기준: 20세 = 2005년생, 29세 = 1996년생
            # SQL: birth_year BETWEEN 1996 AND 2005
            start_year = current_year - max_age
            end_year = current_year - min_age
            sql_hints.append(f"birth_year BETWEEN {start_year} AND {end_year}")

        # (2) 성별
        if 'gender' in conditions:
            sql_hints.append(f"gender = '{conditions['gender']}'")

        # (3) 지역 (시/도)
        if 'location' in conditions:
            sql_hints.append(f"region_main LIKE '%{conditions['location']}%'")
        
        # (4) 상세 지역 (구/군)
        if 'district' in conditions:
            sql_hints.append(f"region_sub LIKE '%{conditions['district']}%'")

        # (5) 직업 (카테고리 또는 상세)
        if 'job' in conditions:
            sql_hints.append(f"(job_category LIKE '%{conditions['job']}%' OR job_detail LIKE '%{conditions['job']}%')")
        
        hints_text = " AND ".join(sql_hints) if sql_hints else "1=1"
        
        prompt = f"""당신은 PostgreSQL 전문가입니다.
주어진 검색 조건을 SQL 쿼리로 변환하세요.

## 타겟 테이블: {schema['table_name']}
## 주요 컬럼
- panel_id (PK)
- birth_year (출생년도) -> 나이 계산: {current_year} - birth_year
- region_main (예: 서울), region_sub (예: 강남구)
- job_category (예: IT/기술), job_detail (예: 개발자)

## 검색 조건
{json.dumps(conditions, ensure_ascii=False, indent=2)}

## SQL 작성 힌트
WHERE {hints_text}

## 규칙
1. SELECT panel_id, birth_year, gender, region_main, job_category FROM {schema['table_name']} ... 형식 사용
2. 오직 SQL 문장 하나만 출력 (JSON 금지, 마크다운 금지, 설명 금지)
3. LIMIT {target_count} 필수 포함

SQL 생성:"""
        return prompt
    
    # =====================================================
    # 4. 인사이트 추출 (OPUS) - 컬럼명 수정됨
    # =====================================================
    
    @staticmethod
    def insight_extraction_prompt(
        panel_data: List[Dict[str, Any]],
        original_query: str
    ) -> str:
        sample_size = min(50, len(panel_data))
        sampled_data = panel_data[:sample_size]
        
        # 데이터 요약 시 실제 컬럼명 사용 (birth_year, region_main 등)
        data_summary = "\n".join([
            f"- ID {p.get('panel_id', 'N/A')}: {p.get('birth_year', 'N/A')}년생, {p.get('gender', 'N/A')}, "
            f"{p.get('region_main', 'N/A')} {p.get('region_sub', '')}, {p.get('job_category', 'N/A')}"
            for p in sampled_data
        ])
        
        prompt = f"""당신은 데이터 분석 전문가입니다.
검색된 패널 그룹을 분석하여 숨겨진 특성을 찾으세요.

## 검색 질의: "{original_query}"
## 데이터 샘플:
{data_summary}

## 응답 형식 (JSON)
{{
  "hidden_patterns": [
    {{ "feature": "특징명", "value": "값", "insight": "설명" }}
  ],
  "statistics": {{
    "age_distribution": {{"20대": 40, "30대": 60}},
    "top_locations": {{"서울": 80, "경기": 20}}
  }},
  "summary": "한줄 요약"
}}

설명 없이 JSON만 반환하세요."""
        return prompt

    # =====================================================
    # 5. 결과 검증 (SONNET)
    # =====================================================
    
    @staticmethod
    def result_validation_prompt(
        sql_result: List[Dict],
        original_conditions: Dict,
        target_count: int
    ) -> str:
        prompt = f"""당신은 데이터 검증 전문가입니다.
SQL 실행 결과가 조건에 맞는지 확인하세요.

조건: {json.dumps(original_conditions, ensure_ascii=False)}
결과 수: {len(sql_result)} / 목표: {target_count}

응답 형식 (JSON):
{{
  "is_valid": true,
  "validation_details": {{
    "condition_match": "양호",
    "count_status": "충족"
  }}
}}"""
        return prompt

    # =====================================================
    # 6. 시스템 메시지
    # =====================================================

    @staticmethod
    def get_system_message(role: str) -> str:
        messages = {
            'analyzer': "당신은 자연어 처리 전문가입니다. 반드시 유효한 JSON만 반환하세요.",
            'sql_generator': "당신은 SQL 전문가입니다. 설명 없이 SQL 쿼리문만 한 줄로 반환하세요.",
            'insight_extractor': "당신은 데이터 과학자입니다. JSON 형식으로만 응답하세요.",
            'validator': "당신은 품질 관리 전문가입니다. JSON 형식으로만 응답하세요."
        }
        return messages.get(role, "도움이 되는 AI 어시스턴트입니다.")