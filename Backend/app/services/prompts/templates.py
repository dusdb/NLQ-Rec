"""
Claude 프롬프트 템플릿 모음
"""

import json
from typing import Dict, List, Any, Optional


class PromptTemplates:
    # =====================================================
    # 1. DB 스키마 로드 (panel_master 기준)
    # =====================================================

    @staticmethod
    def load_schema() -> Dict:
        """DB 스키마 정보 반환 (실제 DB 데이터 분석 기반 매핑 규칙 적용)"""
        return {
            "table_name": "panel_master",
            "columns": {
                # =========================================================
                # 1. 기본 인적 사항 & 가족
                # =========================================================
                "gender": {
                    "type": "VARCHAR(2)",
                    "desc": "성별 (표준값: '남', '여')",
                    "mapping": {
                        "남성": "남", "남자": "남", "man": "남", 
                        "여성": "여", "여자": "여", "woman": "여",
                    }
                },

                "birth_year": {
                    "type": "INTEGER",
                    "desc": "출생년도 (예: 1997, 1985)"
                },

                "region_main": {
                    "type": "VARCHAR(50)",
                    "desc": "거주 시/도 (표준값: 서울, 경기, 인천, 강원, 충남, 충북, 전남, 전북, 경남, 경북, 부산, 대구, 대전, 광주, 울산, 세종, 제주)",
                    "mapping": {
                        "경기도": "경기", "서울시": "서울", "충청남도": "충남",
                        "충청북도": "충북", "전라도": None,
                        "지방": "NOT IN ('서울', '경기', '인천')",
                    }
                },

                "region_sub": {
                    "type": "VARCHAR(50)",
                    "desc": "거주 구/군 (예: 강남구, 분당구, 증평군, 다정동)"
                },

                "marital_status": {
                    "type": "VARCHAR(30)",
                    "desc": "결혼 여부(표준값: '기혼', '미혼', '기타(사별/이혼 등)",
                    "mapping": {
                        "미혼": "미혼",
                        "기혼": "기혼",
                        "이혼": "기타(사별/이혼 등)",
                        "사별": "기타(사별/이혼 등)",
                        "싱글": "미혼"
                    }
                },

                "education": {
                    "type": "VARCHAR(50)",
                    "desc": "최종 학력 (고등학교 졸업 이하 / 대학교 재학(휴학 포함) / 대학교 졸업 / 대학원 재학/졸업 이상)",
                    "mapping": {
                        "고등학교": "고등학교 졸업 이하",
                        "고졸": "고등학교 졸업 이하",
                        "중졸": "고등학교 졸업 이하",
                        "대학교 재학": "대학교 재학(휴학 포함)",
                        "대학생": "대학교 재학(휴학 포함)",
                        "휴학생": "대학교 재학(휴학 포함)",
                        "대학교 졸업": "대학교 졸업",
                        "대졸": "대학교 졸업",
                        "대학원": "대학원 재학/졸업 이상",
                        "석사": "대학원 재학/졸업 이상",
                        "박사": "대학원 재학/졸업 이상",
                    }
                },

                "family_num": {
                    "type": "VARCHAR(10)",
                    "desc": "가구원 수 (표준값: '1명', '2명', '3명', '4명', '5명 이상')",
                    "mapping": {
                        "혼자": "1명",
                        "1인가구": "1명",
                    }
                },

                "child_num": {
                    "type": "VARCHAR(10)",
                    "desc": "자녀 수 (표준값: '0명', '1명', '2명', '3명 이상')",
                },

                "job_category": {
                    "type": "VARCHAR(100)",
                    "desc": "직업군 (전문직 / 교직 / 경영/관리직 / 사무직 / 자영업 / 판매직 / 서비스직 / 생산/노무직 / 기능직 / 농업/임업/축산업/광업/수산업 / 중/고등학생 / 대학생/대학원생, 전업주부, 퇴직/연금생활자)",
                    "mapping": {
                        "의사": "전문직", "간호사": "전문직", "변호사": "전문직",
                        "엔지니어": "전문직", "프로그래머": "전문직", "기술사": "전문직",
                        "교수": "교직", "교사": "교직", "강사": "교직",
                        "사장": "경영/관리직", "임원": "경영/관리직", "대기업 간부": "경영/관리직", "고위 공무원": "경영/관리직", 
                        "사무직": "사무직", "총무": "사무직", "공무원": "사무직",
                        "제조업": "자영업", "건설업": "자영업", "도소매업": "자영업", "운수업": "자영업",
                        "무역업": "자영업", "서비스업 경영": "자영업",
                        "보험판매": "판매직", "세일즈": "판매직", "판매직": "판매직",
                        "도/소매업": "판매직", "부동산 판매": "판매직", "행상": "판매직", "노점상": "판매직",
                        "요식업": "서비스직", "미용": "서비스직", "통신": "서비스직", "안내": "서비스직",
                        "현장직": "생산/노무직", "생산직": "생산/노무직", "차량운전자": "생산/노무직",
                        "정비사": "기능직", "전기공": "기능직", "기술직": "기능직", "제빵업": "기능직",
                        "목수": "기능직", "배관공": "기능직",
                        "대학생": "대학생/대학원생",
                        "주부": "전업주부",
                        "은퇴": "퇴직/연금생활자",
                    }
                },

                "personal_income": {
                    "type": "VARCHAR(50)",
                    "desc": "개인 소득 구간 (텍스트)\n"
                            "- 형식: '월 200~299만원', '월 700~799만원' 등\n"
                            "- 고소득 검색: LIKE '%7%' OR LIKE '%8%' OR LIKE '%9%' OR LIKE '%1000%' 추천\n"
                            "  (700만원 이상을 고소득으로 간주)"
                },

                "household_income": {
                    "type": "VARCHAR(50)",
                    "desc": "월평균 가구소득 (형식: '월 300~399만원' 등 텍스트 구간)"
                },

                "owned_products": {
                    "type": "TEXT",
                    "desc": "보유 전자제품 (콤마 구분)",
                    "mapping": {
                        "티비": "TV",
                        "애플워치": "스마트 워치",
                        "갤럭시 워치": "스마트 워치",
                        "갤럭시 버즈": "무선 이어폰",
                        "에어팟": "무선 이어폰",
                        "다이슨": "무선청소기",
                        "코드제로": "무선청소기",
                        "제트": "무선청소기",
                        "스타일러": "의류 관리기",
                        "에스프레소 머신": "커피머신",
                        "캡슐커피 머신": "커피 머신",
                    }
                },

                "owned_phone_brand": {
                    "type": "VARCHAR(50)",
                    "desc": "사용 중인 스마트폰 기종 (LIKE 검색 필수)\n"
                            "- 애플/아이폰 -> LIKE '%아이폰%' (예: 아이폰 15 Pro 시리즈)\n"
                            "- 삼성/갤럭시 -> LIKE '%갤럭시%' (예: 갤럭시 S23 시리즈)\n"
                            "- LG -> LIKE '%LG%' (예: LG V 시리즈)\n"
                            "- 샤오미/홍미 -> LIKE '%Redmi%' OR LIKE '%Mi%' OR LIKE '%POCO%'"
                },

                "has_car": {"type": "VARCHAR", "desc": "자차 보유 여부 (보유/미보유)"},

                "car_brand": {
                    "type": "VARCHAR",
                    "desc": "자동차 브랜드 (표준값: 현대, 기아, 제네시스, 쌍용, 르노삼성, 메르세데스-벤츠, BMW, 아우디, 테슬라 등)"
                },

                "car_model": {
                    "type": "VARCHAR(50)",
                    "desc": "자동차 모델 (모델명이 매우 다양 → vectorDB 필요 가능)",
                },

                "smoking_exp": {
                    "type": "TEXT",
                    "desc": "흡연 여부 (주의: 비흡연자를 찾을 땐 부정 조건 사용)\n"
                            "- 비흡연자: '담배를 피워본 적이 없다'\n"
                            "- 흡연자: '일반 담배', '궐련형 전자 담배', '액상형 전자담배' 등\n"
                            "- 흡연자 검색 시: column != '담배를 피워본 적이 없다' 또는 column LIKE '%담배%'"
                },

                "smoking_brands": {
                    "type": "TEXT",
                    "desc": "흡연 브랜드(값이 ','로 구분됨. LIKE 연산자 필수)",
                    "mapping": {
                        "구 마일드세븐": "메비우스",
                        "구 라크": "하모니",
                        "구 로스만": "켄트",
                    }
                },

                "alcohol_exp": {
                    "type": "TEXT",
                    "desc": "음용 경험 술 (값이 '; '로 구분됨. LIKE 연산자 필수)",
                    "mapping": {
                        "소주": "소주",
                        "맥주": "맥주",
                        "막걸리": "막걸리/탁주",
                        "청주": "저도주",
                        "매실주": "저도주",
                        "복분자주": "저도주",
                        "위스키": "양주",
                        "보드카": "양주",
                        "데킬라": "양주",
                        "진": "양주",
                        "KGB": "과일칵테일주",
                        "후치": "과일칵테일주",
                        "크루저": "과일칵테일주",
                        "사케": "일본청주/사케",
                    }
                }
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
- gender (성별: 남/여)
- region_main (시/도), region_sub (구/군)
- job_category (직업군), personal_income (소득 구간)
- owned_phone_brand, car_brand (기기 정보)
- smoking_exp, alcohol_exp (기호 식품)

## 나이 표현 해석 규칙 (반드시 적용)
아래와 같은 표현이 사용자 질의에 등장하면, 반드시 age_range를 채우세요.

- "10대"       → {{ "min": 10, "max": 19 }}
- "20대"       → {{ "min": 20, "max": 29 }}
- "30대"       → {{ "min": 30, "max": 39 }}
- "40대"       → {{ "min": 40, "max": 49 }}
- "50대"       → {{ "min": 50, "max": 59 }}
- "60대"       → {{ "min": 60, "max": 69 }}
- "청년"       → {{ "min": 20, "max": 34 }}
- "중장년"     → {{ "min": 40, "max": 64 }}
- "노년"       → {{ "min": 65, "max": 100 }}

예)
- "30대 여성" 이라고 하면 age_range는 {{ "min": 30, "max": 39 }} 입니다.
- "20~30대" 처럼 범위 표현이 있으면 직접 범위를 해석하여 age_range에 넣으세요.

## 사용자 질의
"{user_query}"

## 절대 규칙 (Strict Rules)
1. 추론 금지: 사용자가 언급하지 않은 조건은 무조건 null로 두세요.
2. 데이터 매핑: 사용자의 표현을 DB 스키마 설명(desc)에 있는 표준값과 가장 가까운 형태로 변환하세요.
    - 예: "경기도" -> location="경기"
    - 예: "아이폰 유저" -> phone_brand="아이폰"
    - 예: "지방" -> location="지방" (SQL에서 NOT IN 처리)
    - 예: "고소득" -> income_keyword="고소득" (SQL에서 700만원 이상 처리)
3. JSON 형식 엄수: 아래 형식을 필드를 빠뜨리지 말고 정확히 지키세요.

## 필수 응답 형식 (JSON Schema)
{{
  "search_conditions": {{
    "age_range": {{ "min": 20, "max": 29 }} 또는 null,
    "gender": "남" 또는 "여" 또는 null,
    "location": "서울" 또는 "지방" 또는 null,
    "district": "강남구" (구/군) 또는 null,
    "job": "검색어" (직업 관련 키워드) 또는 null,
    "income_keyword": "고소득" 또는 "검색어" 또는 null,
    "phone_brand": "검색어" (예: '아이폰', '갤럭시') 또는 null,
    "car_brand": "검색어" (예: '벤츠') 또는 null,
    "smoking": "흡연" 또는 "비흡연" 또는 null,
    "alcohol": "검색어" (예: '와인') 또는 null
  }},
  "search_intent": "타겟 그룹 찾기" 또는 "통계 조회",
  "keywords": ["추출된", "핵심", "단어들"],
  "complexity": "simple" 또는 "medium" 또는 "complex",
  "estimated_result_size": "unknown"
}}

주의: 주석이나 설명 없이 오직 JSON 코드만 반환하세요."""
        return prompt
    
    # =====================================================
    # 3. SQL 쿼리 생성 (HAIKU)
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
        
        sql_hints = []
        current_year = 2025

        if conditions.get('age_range') is not None:
            age_range = conditions['age_range']
            if isinstance(age_range, dict):
                min_age = age_range.get('min') or 0
                max_age = age_range.get('max') or 100
                start_year = current_year - max_age
                end_year = current_year - min_age
                sql_hints.append(f"birth_year BETWEEN {start_year} AND {end_year}")

        if conditions.get('gender') is not None:
            sql_hints.append(f"gender = '{conditions['gender']}'")

        location = conditions.get('location')
        if location == '지방':
            sql_hints.append("region_main NOT IN ('서울', '경기', '인천')")
        elif location:
            sql_hints.append(f"region_main = '{location}'")
        
        if conditions.get('district') is not None:
            sql_hints.append(f"region_sub LIKE '%{conditions['district']}%'")

        if conditions.get('job'):
            job_keyword = conditions['job']
            keywords = [k.strip() for k in job_keyword.replace('/', ' ').split() if k.strip()]
            
            conditions_list = []
            for kw in keywords:
                conditions_list.append(f"job_category LIKE '%{kw}%'")
                conditions_list.append(f"job_detail LIKE '%{kw}%'")
            
            sql_hints.append(f"({' OR '.join(conditions_list)})")
        
        income_keyword = conditions.get('income_keyword')
        if income_keyword:
            if '고소득' in income_keyword or '고' in income_keyword:
                sql_hints.append(
                    "(personal_income LIKE '%700%' OR "
                    "personal_income LIKE '%800%' OR "
                    "personal_income LIKE '%900%' OR "
                    "personal_income LIKE '%1000%')"
                )
            else:
                sql_hints.append(f"personal_income LIKE '%{income_keyword}%'")
        
        if conditions.get('phone_brand') is not None:
            sql_hints.append(f"owned_phone_brand LIKE '%{conditions['phone_brand']}%'")
        
        if conditions.get('car_brand') is not None:
            sql_hints.append(f"car_brand LIKE '%{conditions['car_brand']}%'")

        if conditions.get('smoking') == '흡연':
            sql_hints.append("smoking_exp != '담배를 피워본 적이 없다'")
        elif conditions.get('smoking') == '비흡연':
            sql_hints.append("smoking_exp = '담배를 피워본 적이 없다'")

        hints_text = " AND ".join(sql_hints) if sql_hints else "1=1"
        
        prompt = f"""당신은 PostgreSQL 전문가입니다.
주어진 검색 조건을 SQL 쿼리로 변환하세요.

## 타겟 테이블: {schema['table_name']}

## 컬럼 정보 (Schema Description 참고 필수)
{json.dumps(schema['columns'], ensure_ascii=False, indent=2)}

## 검색 조건
{json.dumps(conditions, ensure_ascii=False, indent=2)}

## WHERE 조건 힌트
{hints_text}

## 중요 규칙
1. panel_uuid 필수 포함
2. SELECT 형식: 
SELECT panel_id, panel_uuid, birth_year, gender, region_main, region_sub, job_category, job_detail, personal_income
FROM {schema['table_name']} 
WHERE ...
3. 오직 SQL 문장만 출력 (설명 금지, JSON 금지, 마크다운 금지)
4. LIMIT {target_count} 필수
5. LIKE 연산자 활용: 텍스트 매칭이 필요한 컬럼(브랜드, 소득구간 등)은 반드시 LIKE를 사용
6. "지방" 검색: region_main NOT IN ('서울', '경기', '인천')
7. "고소득" 검색: personal_income LIKE '%700%' OR LIKE '%800%' OR LIKE '%900%' OR LIKE '%1000%'

SQL:"""
        return prompt
    
    # =====================================================
    # 4. 인사이트 추출
    # =====================================================
        
    @staticmethod
    def insight_extraction_prompt(
        panel_data: List[Dict[str, Any]],
        original_query: str,
        full_statistics: Optional[Dict[str, Any]] = None
    ) -> str:

        sample_size = min(50, len(panel_data))
        sampled_data = panel_data[:sample_size]
        
        data_summary = "\n".join([
            f"- 패널{i+1}: {p.get('age', 'N/A')}, {p.get('gender', 'N/A')}, {p.get('location', 'N/A')}, "
            f"직업:{p.get('job_category', 'N/A')}({p.get('job_detail', '')}), "
            f"소득:{p.get('personal_income', 'N/A')}, 차량:{p.get('car_brand', 'N/A')}, "
            f"폰:{p.get('owned_phone_brand', 'N/A')}, 흡연:{p.get('smoking_exp', 'N/A')}"
            for i, p in enumerate(sampled_data)
        ])
        
        stats_section = ""
        if full_statistics:
            stats_section = f"""
## 전체 그룹 통계 (우선 참고)
{json.dumps(full_statistics, ensure_ascii=False, indent=2)}

통계 해석 규칙:
- 위 통계는 샘플이 아닌 **전체 검색 결과({full_statistics.get('total_count', 0)}명)**의 분포입니다.
- 샘플 데이터보다 이 통계 수치를 우선하여 인사이트를 도출하세요.
"""
        
        prompt = f"""당신은 데이터 마이닝 전문가이자 마케팅 전략가입니다.
검색된 패널 그룹을 **다양한 관점**에서 입체적으로 분석하여, 겉으로 드러나지 않는 **실행 가능한 인사이트(Actionable Insights)**를 도출하세요.

## 검색 맥락
- 사용자 질의: "{original_query}"
{stats_section}

## 데이터 샘플 ({len(sampled_data)}명) - 정성적 패턴 분석용
{data_summary}

## **심층 분석 5단계 파이프라인**
다음 순서대로 데이터를 스캔하여 가장 강력한 특징을 찾아내세요.

1. **경제/직업 DNA 분석** (Priority 1)
    - 단순 직업 분포를 넘어, 소득 수준과 직업의 상관관계를 보세요.
    - 예: "전문직이 많음" (X) -> "고소득 전문직 집중도 높음" (O)

2. **라이프스타일 & 소비 패턴** (Priority 2)
    - 차량, 스마트폰, 보유 기기 등을 통해 소비 성향을 추론하세요.
    - 브랜드 선호도(예: 벤츠, 아이폰)에서 "프리미엄 지향" 여부를 판단하세요.

3. **기호 및 습관** (Priority 3)
    - 흡연, 음주 패턴을 통해 건강/유흥 성향을 분석하세요.

4. **숨겨진 연관성 발견** (Advanced)
    - **[직업 + 지역]** 또는 **[나이 + 차]** 등 두 가지 이상의 속성이 결합된 패턴을 찾으세요.
    - 예: "강남 거주 30대 전문직", "수입차를 보유한 20대"

5. **인구통계 필터링** (Lowest Priority)
    - 나이, 성별, 지역은 **검색 조건에 없을 때만** 언급하세요.
    - 뻔한 사실(예: "한국인임", "응답자임")은 절대 배제하세요.

## **품질 관리 규칙 (Critical Rules)**
1. **"미기재/정보없음" 절대 금지**
    - 데이터가 없다는 사실은 인사이트가 아닙니다. 
    - "차량 정보 미기재가 많습니다" -> 무조건 탈락.
    - 입력된 값 중에서만 패턴을 찾으세요.

2. **다양성 확보 (Category Diversity)**
    - 한 카테고리(예: 직업)에서만 4개를 뽑지 마세요.
    - **최소 3개 이상의 서로 다른 카테고리**에서 인사이트를 조합하세요.

3. **구체적이고 완결된 문장**
    - 수치를 반드시 포함하세요 (예: "약 40%", "과반수 이상").
    - 문장은 "~함"이나 "~음"으로 끝내지 말고, **"~합니다."** 또는 **"~입니다."**로 정중하게 끝맺으세요.

## 필수 응답 형식 (JSON)
{{
  "hidden_patterns": [
    {{
      "feature": "job_category", 
      "value": "전문직/IT", 
      "percentage": 65, 
      "insight": "IT 및 전문직 종사자 비율이 65%로 매우 높습니다.", 
      "confidence": "high"
    }},
    {{
      "feature": "lifestyle_composite", 
      "value": "프리미엄 소비", 
      "percentage": 40, 
      "insight": "벤츠 등 수입차와 아이폰 사용 비율이 높아 프리미엄 소비 성향을 보입니다.", 
      "confidence": "medium"
    }},
    {{
      "feature": "smoking_exp", 
      "value": "비흡연", 
      "percentage": 85, 
      "insight": "85%가 비흡연자로 건강 관리에 신경 쓰는 그룹입니다.", 
      "confidence": "high"
    }}
  ],
  "statistics": {{
    "top_jobs": {{"전문직": 40, "경영관리": 15}},
    "brand_preference": {{"벤츠": 20, "아이폰": 60}}
  }},
  "target_profile": {{
    "core_demographic": "30-40대 고소득층",
    "key_traits": ["전문직 종사", "수입차 선호", "건강 지향"]
  }}
}}

**Self-Check**: 
- hidden_patterns가 4~5개인가? 
- "미기재" 관련 내용이 0개인가? 
- 직업, 소비, 습관 등 카테고리가 섞여 있는가?
- 문장이 자연스러운가?

위 규칙을 준수하여 JSON을 생성하세요."""
        return prompt

    # =====================================================
    # 5. 전략 보고서 생성 (OPUS)
    # =====================================================
    
    @staticmethod
    def strategy_report_prompt(
        insights: Dict[str, Any],
        original_query: str,
        panel_count: int
    ) -> str:
        prompt = f"""당신은 비즈니스 전략 기획자입니다.
아래 인사이트를 바탕으로 **실행 가능한 사업 기획서**를 작성하세요.

## 검색 질의
"{original_query}"

## 타겟 그룹 규모
{panel_count}명

## 도출된 인사이트
{json.dumps(insights, ensure_ascii=False, indent=2)}

## 필수 응답 형식 (JSON)
{{
  "projectName": "서비스명",
  "projectSubtitle": "한 줄 설명 (30자 이내)",
  "summaryTable": [
    {{"th": "프로젝트명", "td": "구체적인 서비스명"}},
    {{"th": "타겟 고객", "td": "실제 데이터 기반 타겟 정의"}},
    {{"th": "목표", "td": "핵심 목표 1줄"}}
  ],
  "problemDefinition": "타겟이 겪는 문제 정의 (2문장 이내)",
  "coreValueHighlight": "핵심 가치 한 문장 (20자 이내)",
  "coreValueText": "핵심 가치 설명 (3문장)",
  "insightTable": {{
    "headers": ["지표", "수치", "의미"],
    "rows": [
      ["직업 분포", "전문직 40%", "고학력 타겟"],
      ["지역 집중도", "서울 65%", "수도권 중심"]
    ]
  }},
  "serviceTable": {{
    "rows": [
      {{"th": "서비스 형태", "td": "설명"}},
      {{"th": "핵심 기능", "td": "설명"}}
    ]
  }},
  "strategyProposal": ["초기 런칭 전략 (100자)", "성장 확대 전략 (100자)", "장기 안정화 전략 (100자)"],
  "effectTable": {{
    "headers": ["구분", "정량적 효과", "정성적 효과"],
    "rows": [
      ["단기", "가입자 20% 증가", "브랜드 인지도 향상"],
      ["장기", "MAU 50% 증가", "충성도 고객 확보"]
    ]
  }}
}}

중요: 
1. 모든 텍스트는 간결하게 (지정된 길이 준수)
2. insightTable, effectTable은 반드시 headers + rows 구조로
3. 주석 없이 순수 JSON만 반환

주석 없이 순수 JSON만 반환하세요."""
        return prompt

    # =====================================================
    # 6. 결과 검증 (SONNET)
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
    # 7. 시스템 메시지
    # =====================================================

    @staticmethod
    def get_system_message(role: str) -> str:
        messages = {
            'analyzer': "당신은 자연어 처리 전문가입니다. 반드시 유효한 JSON만 반환하세요.",
            'sql_generator': "당신은 SQL 전문가입니다. 설명 없이 SQL 쿼리문만 한 줄로 반환하세요.",
            'insight_extractor': "당신은 데이터 과학자입니다. 구체적인 수치와 비교 기준을 포함한 JSON만 반환하세요.",
            'strategy_planner': "당신은 비즈니스 전략 기획자입니다. 실행 가능한 전략이 담긴 JSON만 반환하세요.",
            'validator': "당신은 품질 관리 전문가입니다. JSON 형식으로만 응답하세요."
        }
        return messages.get(role, "도움이 되는 AI 어시스턴트입니다.")