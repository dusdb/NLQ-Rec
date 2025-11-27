# Backend/app/services/vector_service.py

"""
pgvector 기반 유사도 검색 서비스 (Refactored: JOIN Optimization + Deduplication)
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # TensorFlow 로그 숨기기
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # oneDNN 메시지 제거

from typing import List, Dict, Any, Optional
import logging
from uuid import UUID  # UUID 타입 체크용

from app.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class VectorSearchService:
    """벡터 검색 서비스"""
    
    def __init__(self, model_name: str = "nlpai-lab/KURE-v1"):
        """
        Args:
            model_name: 임베딩 모델 이름
        """
        self.model_name = model_name
        self._model = None  # Lazy loading용
        self.embedding_dim = 1024  # KURE-v1의 고정 차원
        
    @property
    def model(self):
        """모델을 필요할 때만 로드 (Lazy Loading)"""
        if self._model is None:
            logger.info(f"⏳ 임베딩 모델 로딩 중: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"✅ 모델 로딩 완료 (차원: {self.embedding_dim})")
        return self._model
    
    def get_embedding(self, text: str) -> List[float]:
        """
        텍스트를 벡터로 변환
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def _validate_embedding_dimension(self, vector: List[float]) -> bool:
        """임베딩 차원 검증"""
        expected_dim = 1024
        if len(vector) != expected_dim:
            logger.error(f"❌ 차원 불일치: {len(vector)} != {expected_dim}")
            return False
        return True

    def _convert_uuids_to_str(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        결과 리스트 내의 UUID 객체를 문자열로 변환 (JSON 직렬화 에러 방지)
        """
        for row in results:
            for key, value in row.items():
                if isinstance(value, UUID):
                    row[key] = str(value)
        return results

    def semantic_search(
        self,
        query_text: str,
        top_k: int = 10,
        distance_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        의미 기반 유사도 검색 (SQL 필터 없음)
        ✅ panel_uuid 기준 중복 제거: 동일 패널의 여러 응답 중 최고 similarity만 반환
        """
        # 1. 질의 텍스트를 벡터로 변환
        query_vector = self.get_embedding(query_text)

        if not self._validate_embedding_dimension(query_vector):
            logger.error("❌ 임베딩 차원 오류로 검색 실패")
            return []
        
        # 2. pgvector cosine distance 검색 (중복 허용, 더 많이 가져옴)
        fetch_limit = top_k * 3  # 중복 제거 후에도 충분한 결과 확보
        
        sql = """
        SELECT 
            vi.vector_uuid,
            vi.panel_uuid,
            vi.response_uuid,
            vi.answer_text,
            (vi.embedding <=> %s::vector) as distance,
            (1 - (vi.embedding <=> %s::vector)) as similarity
        FROM vector_index vi
        WHERE vi.embedding IS NOT NULL 
            AND vi.panel_uuid IS NOT NULL
        """
        
        if distance_threshold is not None:
            sql += f" AND (vi.embedding <=> %s::vector) <= {distance_threshold}"
        
        sql += " ORDER BY distance ASC LIMIT %s;"
        
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        
        try:
            params = (vector_str, vector_str, fetch_limit) if distance_threshold is None else (vector_str, vector_str, vector_str, fetch_limit)
            
            results = DatabaseConnection.execute_query(sql, params)
            
            # ✅ UUID -> String 변환
            results = self._convert_uuids_to_str(results)
            
            # ✅ 중복 제거: panel_uuid 기준으로 최고 similarity만 유지
            seen_panels = {}
            for result in results:
                panel_uuid = result['panel_uuid']
                similarity = result['similarity']
                
                if panel_uuid not in seen_panels or similarity > seen_panels[panel_uuid]['similarity']:
                    seen_panels[panel_uuid] = result
            
            # 중복 제거 후 similarity 순 정렬 + top_k개만 반환
            deduplicated = sorted(seen_panels.values(), key=lambda x: x['similarity'], reverse=True)[:top_k]
            
            logger.info(f"✅ 벡터 검색 완료: {len(results)}개 → 중복 제거 후 {len(deduplicated)}개")
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {e}")
            return []

    def get_panel_info_by_uuids(
        self,
        panel_uuids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        panel_uuid 리스트로 패널 정보 조회 (보조용)
        """
        if not panel_uuids:
            return []
        
        placeholders = ','.join(['%s'] * len(panel_uuids))
        sql = f"""
        SELECT 
            panel_uuid, panel_id, birth_year, gender,
            region_main, region_sub, job_category, job_detail,
            education, marital_status
        FROM panel_master
        WHERE panel_uuid IN ({placeholders});
        """
        
        try:
            results = DatabaseConnection.execute_query(sql, tuple(panel_uuids))
            
            # ✅ UUID -> String 변환
            results = self._convert_uuids_to_str(results)
            
            return results
        except Exception as e:
            logger.error(f"❌ 패널 정보 조회 실패: {e}")
            return []

    def hybrid_search(
        self,
        query_text: str,
        sql_conditions: Optional[Dict[str, Any]] = None,
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색: SQL JOIN을 통한 필터링 + 벡터 검색
        ✅ panel_uuid 기준 중복 제거 포함
        
        [Refactoring Note]
        기존: SQL 필터링 -> Python List(UUID) -> SQL IN절 (메모리 비효율)
        변경: INNER JOIN panel_master -> 단일 쿼리로 필터링 및 검색 수행
        """
        # 1. 조건이 없으면 일반 시맨틱 검색 수행 후 정보 결합
        if not sql_conditions:
            results = self.semantic_search(query_text, top_k)
            if results:
                panel_uuids = list(set([r['panel_uuid'] for r in results]))
                panel_info = self.get_panel_info_by_uuids(panel_uuids)
                panel_map = {p['panel_uuid']: p for p in panel_info}
                
                combined = []
                for r in results:
                    uid = r['panel_uuid']
                    if uid in panel_map:
                        combined.append({**r, **panel_map[uid]})
                return combined
            return []

        # 2. 하이브리드 검색 (JOIN 방식 + 중복 제거)
        query_vector = self.get_embedding(query_text)
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        
        # 중복 제거를 위해 더 많이 가져옴
        fetch_limit = top_k * 3
        
        # 기본 쿼리: vector_index와 panel_master를 조인
        sql = """
        SELECT 
            vi.vector_uuid,
            vi.panel_uuid,
            vi.response_uuid,
            vi.answer_text,
            (vi.embedding <=> %s::vector) as distance,
            (1 - (vi.embedding <=> %s::vector)) as similarity,
            pm.panel_id, pm.birth_year, pm.gender,
            pm.region_main, pm.region_sub, pm.job_category, pm.job_detail,
            pm.education, pm.marital_status
        FROM vector_index vi
        INNER JOIN panel_master pm ON vi.panel_uuid = pm.panel_uuid
        WHERE vi.embedding IS NOT NULL 
        """
        
        params = [vector_str, vector_str]
        
        # 3. 동적 필터링 조건 추가 (JOIN된 pm 테이블 기준)
        if sql_conditions.get('age_range'):
            age_range = sql_conditions['age_range']
            if isinstance(age_range, dict):
                current_year = 2025
                min_age = age_range.get('min', 0)
                max_age = age_range.get('max', 100)
                start_year = current_year - max_age
                end_year = current_year - min_age
                sql += " AND pm.birth_year BETWEEN %s AND %s"
                params.extend([start_year, end_year])
        
        if sql_conditions.get('gender'):
            sql += " AND pm.gender = %s"
            params.append(sql_conditions['gender'])
        
        # 지역 조건
        if sql_conditions.get('location'):
            loc = sql_conditions['location']
            if loc == '지방':
                sql += " AND pm.region_main NOT IN ('서울', '경기', '인천')"
            else:
                sql += " AND pm.region_main LIKE %s"
                params.append(f"%{loc}%")
        
        if sql_conditions.get('district'):
            sql += " AND pm.region_sub LIKE %s"
            params.append(f"%{sql_conditions['district']}%")
        
        # 직업 조건
        if sql_conditions.get('job'):
            sql += " AND (pm.job_category LIKE %s OR pm.job_detail LIKE %s)"
            params.extend([f"%{sql_conditions['job']}%", f"%{sql_conditions['job']}%"])
            
        # 소득, 자산 등 추가 조건이 있다면 여기에 계속 추가 가능
        
        # 4. 정렬 및 제한
        sql += " ORDER BY distance ASC LIMIT %s;"
        params.append(fetch_limit)
        
        try:
            # 단일 쿼리로 실행
            results = DatabaseConnection.execute_query(sql, tuple(params))
            
            # ✅ UUID -> String 변환
            results = self._convert_uuids_to_str(results)
            
            # ✅ 중복 제거: panel_uuid 기준으로 최고 similarity만 유지
            seen_panels = {}
            for result in results:
                panel_uuid = result['panel_uuid']
                similarity = result['similarity']
                
                if panel_uuid not in seen_panels or similarity > seen_panels[panel_uuid]['similarity']:
                    seen_panels[panel_uuid] = result
            
            # 중복 제거 후 similarity 순 정렬 + top_k개만 반환
            deduplicated = sorted(seen_panels.values(), key=lambda x: x['similarity'], reverse=True)[:top_k]
            
            logger.info(f"✅ 하이브리드 검색(JOIN) 완료: {len(results)}개 → 중복 제거 후 {len(deduplicated)}개")
            return deduplicated
            
        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 실패: {e}")
            return []

# Lazy 싱글톤 인스턴스
_vector_service_instance = None

def get_vector_service() -> VectorSearchService:
    """벡터 서비스 싱글톤 인스턴스 반환"""
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorSearchService()
    return _vector_service_instance

# 싱글톤 인스턴스 (즉시 생성)
vector_service = get_vector_service()