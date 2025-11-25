# Backend/app/services/Search_Agent.py

"""
통합 검색 에이전트
- 벡터 검색 (의미 기반)
- SQL 검색 (조건 기반)
- 하이브리드 검색
v3.4: 단순 필터링 쿼리 자동 감지 → SQL 모드 전환
v3.5: ✅ DB 스키마 불일치 수정 (interests, bio 컬럼 제거)
"""
from typing import List, Dict, Any, Optional
import logging

from .vector_search import get_vector_service
from app.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SearchAgent:
    """통합 검색 에이전트"""
    
    def __init__(self):
        self._vector_service = None  # Lazy loading
        logger.info("✅ SearchAgent 초기화 완료")

    @property
    def vector_service(self):
        """벡터 서비스를 필요할 때만 로드"""
        if self._vector_service is None:
            self._vector_service = get_vector_service()
        return self._vector_service

    def semantic_search(
        self,
        query_text: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        의미 기반 벡터 검색
        
        Args:
            query_text: 검색 질의
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        logger.info(f"🔍 벡터 검색 시작: '{query_text}'")
        
        results = self.vector_service.semantic_search(
            query_text=query_text,
            top_k=top_k
        )
        
        # panel 정보 결합
        if results:
            panel_uuids = list(set([r['panel_uuid'] for r in results]))
            panel_info = self.vector_service.get_panel_info_by_uuids(panel_uuids)
            panel_map = {p['panel_uuid']: p for p in panel_info}
            
            for result in results:
                panel_uuid = result['panel_uuid']
                if panel_uuid in panel_map:
                    result.update(panel_map[panel_uuid])
        
        logger.info(f"✅ 벡터 검색 완료: {len(results)}개 결과")
        return results
    
    def sql_search(
        self,
        sql_query: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        SQL 기반 조건 검색
        
        Args:
            sql_query: SQL 쿼리문
            limit: 최대 반환 개수
            
        Returns:
            검색 결과 리스트
        """
        logger.info(f"🔍 SQL 검색 시작")
        logger.debug(f"SQL: {sql_query}")
        
        try:
            # LIMIT 추가 (없는 경우)
            if 'LIMIT' not in sql_query.upper():
                sql_query = sql_query.rstrip(';') + f" LIMIT {limit};"
            
            results = DatabaseConnection.execute_query(sql_query)
            logger.info(f"✅ SQL 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"❌ SQL 검색 실패: {e}")
            return []
    
    def hybrid_search(
        self,
        query_text: str,
        sql_conditions: Optional[Dict[str, Any]] = None,
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (벡터 + SQL 조건)
        
        ⭐ v3.4 개선:
        - 단순 필터링 쿼리 감지 → SQL 모드로 자동 전환
        - 예: "지방 거주", "서울 사는" 등
        
        Args:
            query_text: 자연어 검색 질의
            sql_conditions: SQL 필터 조건
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        logger.info(f"🔍 하이브리드 검색 시작: '{query_text}'")
        logger.debug(f"SQL 조건: {sql_conditions}")
        
        # ⭐⭐⭐ 추가: 단순 필터링 쿼리 감지 ⭐⭐⭐
        keyword_count = len(query_text.split())
        simple_location_keywords = ['거주', '사는', '지역', '살고', '있는', '위치', '거주자']
        
        is_simple_location_query = (
            keyword_count <= 3 and 
            any(keyword in query_text for keyword in simple_location_keywords)
        )
        
        if is_simple_location_query and sql_conditions:
            logger.warning(f"⚠️ 단순 필터링 쿼리 감지: '{query_text}'")
            logger.warning("   → 벡터 검색 스킵, SQL 필터링만 사용")
            
            # SQL 조건 기반 검색으로 전환
            return self._sql_condition_search(sql_conditions, top_k)
        # ⭐⭐⭐ 추가 끝 ⭐⭐⭐
        
        # 기존 하이브리드 로직
        results = self.vector_service.hybrid_search(
            query_text=query_text,
            sql_conditions=sql_conditions,
            top_k=top_k
        )
        
        logger.info(f"✅ 하이브리드 검색 완료: {len(results)}개 결과")
        return results
    
    def _sql_condition_search(
        self,
        sql_conditions: Dict[str, Any],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        ⭐ 새로 추가: SQL 조건만으로 검색 (벡터 검색 없음)
        
        Args:
            sql_conditions: 검색 조건 딕셔너리
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        logger.info("🔍 SQL 조건 검색 모드 실행")
        
        where_clauses = []
        current_year = 2025
        
        # 1. 나이 조건
        if sql_conditions.get('age_range'):
            age_range = sql_conditions['age_range']
            min_age = age_range.get('min', 0)
            max_age = age_range.get('max', 100)
            start_year = current_year - max_age
            end_year = current_year - min_age
            where_clauses.append(f"birth_year BETWEEN {start_year} AND {end_year}")
        
        # 2. 성별 조건
        if sql_conditions.get('gender'):
            where_clauses.append(f"gender = '{sql_conditions['gender']}'")
        
        # 3. 지역 조건 (⭐ 지방 처리 포함)
        location = sql_conditions.get('location')
        if location == '지방':
            where_clauses.append("region_main NOT IN ('서울', '경기', '인천')")
        elif location:
            where_clauses.append(f"region_main = '{location}'")
        
        # 4. 상세 지역
        if sql_conditions.get('district'):
            where_clauses.append(f"region_sub LIKE '%{sql_conditions['district']}%'")
        
        # 5. 직업
        if sql_conditions.get('job'):
            where_clauses.append(f"job_category LIKE '%{sql_conditions['job']}%'")
        
        # 6. 소득
        income_keyword = sql_conditions.get('income_keyword')
        if income_keyword:
            if '고소득' in income_keyword or '고' in income_keyword:
                where_clauses.append(
                    "(personal_income LIKE '%700%' OR "
                    "personal_income LIKE '%800%' OR "
                    "personal_income LIKE '%900%' OR "
                    "personal_income LIKE '%1000%')"
                )
            else:
                where_clauses.append(f"personal_income LIKE '%{income_keyword}%'")
        
        # 7. 휴대폰 브랜드
        if sql_conditions.get('phone_brand'):
            where_clauses.append(f"owned_phone_brand LIKE '%{sql_conditions['phone_brand']}%'")
        
        # 8. 자동차 브랜드
        if sql_conditions.get('car_brand'):
            where_clauses.append(f"car_brand LIKE '%{sql_conditions['car_brand']}%'")
        
        # 9. 흡연
        smoking = sql_conditions.get('smoking')
        if smoking == '흡연':
            where_clauses.append("smoking_exp != '담배를 피워본 적이 없다'")
        elif smoking == '비흡연':
            where_clauses.append("smoking_exp = '담배를 피워본 적이 없다'")
        
        # WHERE 절 조합
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # ✅ 최종 SQL 쿼리 (interests, bio 제거)
        sql_query = f"""
            SELECT 
                panel_id, panel_uuid, birth_year, gender, 
                region_main, region_sub, job_category, job_detail, 
                personal_income,
                owned_phone_brand, car_brand, smoking_exp
            FROM panel_master
            WHERE {where_sql}
            LIMIT {top_k}
        """
        
        logger.info(f"🔍 실행할 SQL:\n{sql_query}")
        
        try:
            results = DatabaseConnection.execute_query(sql_query)
            logger.info(f"✅ SQL 조건 검색 완료: {len(results)}명")
            return results
        except Exception as e:
            logger.error(f"❌ SQL 조건 검색 실패: {e}")
            return []
    
    def search(
        self,
        query_text: str,
        search_type: str = "hybrid",
        sql_query: Optional[str] = None,
        sql_conditions: Optional[Dict[str, Any]] = None,
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        통합 검색 인터페이스
        
        Args:
            query_text: 검색 질의
            search_type: 'semantic', 'sql', 'hybrid'
            sql_query: SQL 쿼리 (search_type='sql'일 때)
            sql_conditions: SQL 조건 (search_type='hybrid'일 때)
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        if search_type == "semantic":
            return self.semantic_search(query_text, top_k)
        
        elif search_type == "sql":
            if not sql_query:
                logger.error("❌ SQL 검색에는 sql_query가 필요합니다")
                return []
            return self.sql_search(sql_query, top_k)
        
        elif search_type == "hybrid":
            return self.hybrid_search(query_text, sql_conditions, top_k)
        
        else:
            logger.error(f"❌ 알 수 없는 검색 타입: {search_type}")
            return []


# 싱글톤 인스턴스
search_agent = SearchAgent()


# ===== 테스트 코드 =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = SearchAgent()
    
    # 테스트 1: 의미 기반 검색
    print("\n" + "="*50)
    print("🧪 테스트 1: 의미 기반 벡터 검색")
    print("="*50)
    
    query = "서울에 거주하는 30대 남성"
    results = agent.semantic_search(query, top_k=5)
    
    if results:
        for i, res in enumerate(results, 1):
            print(f"\n[{i}위] 유사도: {res.get('similarity', 0):.4f}")
            print(f"  - 패널: {res.get('panel_id', 'N/A')}")
            print(f"  - 성별: {res.get('gender', 'N/A')}, 나이: {2025 - res.get('birth_year', 2000)}세")
            print(f"  - 지역: {res.get('region_main', 'N/A')} {res.get('region_sub', '')}")
            print(f"  - 내용: {res.get('answer_text', '')[:100]}...")
    else:
        print("검색 결과 없음")