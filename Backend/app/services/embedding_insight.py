# app/services/embedding_insight.py
"""
임베딩 평균 기반 공통 특성 추출 모듈
Lift 지수 대신 코사인 유사도를 사용
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging

from app.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class EmbeddingInsightEngine:
    """임베딩 평균 기반 인사이트 추출 엔진"""
    
    def __init__(self):
        # 카테고리별 대표 키워드 정의
        self.category_keywords = {
            "job": [
                "전문직", "IT", "개발자", "경영관리직", "사무직", 
                "자영업", "서비스직", "생산직", "교직", "의료"
            ],
            "lifestyle": [
                "프리미엄 소비", "건강 지향", "친환경", "문화생활", 
                "스포츠 활동", "여가 중시", "가족 중심"
            ],
            "consumption": [
                "고소득", "중산층", "명품 선호", "실용적 소비", 
                "가성비 중시", "브랜드 충성"
            ],
            "hobby": [
                "운동", "여행", "독서", "게임", "음악", 
                "영화", "요리", "반려동물"
            ],
            "health": [
                "비흡연", "음주", "건강관리", "운동", "다이어트"
            ]
        }
    
    async def calculate_embedding_center(
        self, 
        panel_uuids: List[str]
    ) -> Optional[np.ndarray]:
        """
        패널들의 임베딩 평균 벡터 계산
        
        Args:
            panel_uuids: 패널 UUID 리스트
            
        Returns:
            평균 임베딩 벡터 (numpy array)
        """
        if not panel_uuids:
            print("⚠️ 패널 UUID 리스트가 비어있습니다")
            logger.warning("패널 UUID 리스트가 비어있습니다")
            return None
        
        try:
            print(f"🔍 임베딩 조회 시작: {len(panel_uuids)}개 패널")
            
            # 패널들의 모든 임베딩 조회 (asyncpg 사용)
            from app.utils.database import execute_fetch_query
            
            placeholders = ','.join([f'${i+1}' for i in range(len(panel_uuids))])
            sql = f"""
            SELECT embedding 
            FROM vector_index 
            WHERE panel_uuid IN ({placeholders})
                AND embedding IS NOT NULL
            LIMIT 1000
            """
            
            print(f"📝 SQL 실행: {sql[:200]}...")
            results = await execute_fetch_query(sql, tuple(panel_uuids))
            print(f"✅ DB 조회 완료: {len(results)}개 임베딩")
            
            if not results:
                print("⚠️ 임베딩 데이터를 찾을 수 없습니다")
                logger.warning("임베딩 데이터를 찾을 수 없습니다")
                return None
            
            # 임베딩 벡터 추출 및 평균 계산
            embeddings = []
            for i, row in enumerate(results):
                emb = row.get('embedding')
                if emb:
                    # pgvector는 리스트 또는 배열 형태로 반환
                    if isinstance(emb, str):
                        import json
                        emb = json.loads(emb)  # JSON 파싱
                    elif hasattr(emb, '__iter__'):
                        emb = list(emb)
                    
                    embeddings.append(emb)
                    
                    if i == 0:
                        print(f"📊 첫 번째 임베딩 차원: {len(emb)}")
            
            if not embeddings:
                print("⚠️ 유효한 임베딩이 없습니다")
                logger.warning("유효한 임베딩이 없습니다")
                return None
            
            # NumPy 배열로 변환 후 평균 계산
            embeddings_array = np.array(embeddings, dtype=np.float32)
            avg_embedding = np.mean(embeddings_array, axis=0)
            
            print(f"✅ 임베딩 평균 계산 완료: {len(embeddings)}개 벡터 → 평균 벡터 차원: {len(avg_embedding)}")
            logger.info(f"✅ 임베딩 평균 계산 완료: {len(embeddings)}개 벡터")
            return avg_embedding
            
        except Exception as e:
            print(f"❌ 임베딩 평균 계산 실패: {e}")
            import traceback
            print(traceback.format_exc())
            logger.error(f"❌ 임베딩 평균 계산 실패: {e}")
            return None
    
    async def get_category_embeddings(self) -> Dict[str, Dict[str, np.ndarray]]:
        """
        카테고리별 대표 키워드의 임베딩 조회
        
        Returns:
            {"job": {"전문직": [0.1, 0.2, ...], ...}, ...}
        """
        print("🔍 카테고리 키워드 임베딩 생성 시작...")
        from app.services.search import vector_service
        
        category_embeddings = {}
        total_keywords = sum(len(keywords) for keywords in self.category_keywords.values())
        processed = 0
        
        for category, keywords in self.category_keywords.items():
            category_embeddings[category] = {}
            
            for keyword in keywords:
                try:
                    # 키워드를 임베딩으로 변환
                    embedding = vector_service.get_embedding(keyword)
                    category_embeddings[category][keyword] = np.array(embedding, dtype=np.float32)
                    processed += 1
                    
                    if processed == 1:
                        print(f"  ✅ 첫 키워드 '{keyword}' 임베딩 성공 (차원: {len(embedding)})")
                    
                except Exception as e:
                    print(f"  ❌ 키워드 '{keyword}' 임베딩 실패: {e}")
                    logger.error(f"키워드 '{keyword}' 임베딩 실패: {e}")
        
        print(f"✅ 카테고리 임베딩 생성 완료: {len(category_embeddings)}개 카테고리, {processed}/{total_keywords}개 키워드")
        logger.info(f"✅ 카테고리 임베딩 생성 완료: {len(category_embeddings)}개 카테고리")
        return category_embeddings
    
    def cosine_similarity(
        self, 
        vec1: np.ndarray, 
        vec2: np.ndarray
    ) -> float:
        """
        두 벡터 간 코사인 유사도 계산
        
        Args:
            vec1: 첫 번째 벡터
            vec2: 두 번째 벡터
            
        Returns:
            코사인 유사도 (0~1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def find_top_similar_patterns(
        self,
        avg_embedding: np.ndarray,
        top_k: int = 2
    ) -> List[Dict[str, Any]]:
        """
        평균 임베딩과 가장 유사한 패턴 찾기
        
        Args:
            avg_embedding: 패널들의 평균 임베딩
            top_k: 반환할 상위 패턴 개수
            
        Returns:
            유사도 상위 패턴 리스트
        """
        print(f"🔍 유사 패턴 찾기 시작 (top_k={top_k})...")
        
        # 카테고리별 키워드 임베딩 조회
        category_embeddings = await self.get_category_embeddings()
        
        # 모든 키워드와 유사도 계산
        similarities = []
        
        for category, keywords_dict in category_embeddings.items():
            for keyword, keyword_embedding in keywords_dict.items():
                similarity = self.cosine_similarity(avg_embedding, keyword_embedding)
                
                similarities.append({
                    "category": category,
                    "keyword": keyword,
                    "similarity": similarity
                })
        
        print(f"📊 총 {len(similarities)}개 키워드 유사도 계산 완료")
        
        # 유사도 내림차순 정렬
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 상위 10개 출력
        print("📈 유사도 상위 10개:")
        for i, item in enumerate(similarities[:10], 1):
            print(f"  {i}위: {item['keyword']} ({item['category']}) - {item['similarity']:.4f}")
        
        # 상위 top_k개 선택 (카테고리 중복 방지)
        selected_patterns = []
        used_categories = set()
        
        for item in similarities:
            if len(selected_patterns) >= top_k:
                break
            
            # 같은 카테고리에서 2개 이상 선택 방지
            if item['category'] not in used_categories:
                selected_patterns.append(item)
                used_categories.add(item['category'])
                print(f"  ✅ 선정: {item['keyword']} (유사도: {item['similarity']:.4f})")
        
        # top_k개가 안 채워지면 중복 허용
        if len(selected_patterns) < top_k:
            print(f"⚠️ {top_k}개 미달 ({len(selected_patterns)}개), 카테고리 중복 허용")
            for item in similarities:
                if len(selected_patterns) >= top_k:
                    break
                if item not in selected_patterns:
                    selected_patterns.append(item)
                    print(f"  ✅ 추가: {item['keyword']} (유사도: {item['similarity']:.4f})")
        
        print(f"✅ 최종 {len(selected_patterns)}개 패턴 선정 완료")
        logger.info(f"✅ 상위 {len(selected_patterns)}개 패턴 선정 완료")
        
        return selected_patterns
    
    async def extract_insights_by_embedding(
        self,
        panel_uuids: List[str],
        search_conditions: Dict[str, Any],
        top_k: int = 2
    ) -> List[Dict[str, Any]]:
        """
        임베딩 평균 기반 인사이트 추출 (메인 함수)
        
        Args:
            panel_uuids: 검색된 패널 UUID 리스트
            search_conditions: 검색 조건
            top_k: 추출할 인사이트 개수
            
        Returns:
            인사이트 리스트
        """
        print("\n" + "="*60)
        print("🚀 임베딩 기반 인사이트 추출 시작")
        print("="*60)
        print(f"입력: {len(panel_uuids)}개 패널, top_k={top_k}")
        print(f"검색 조건: {search_conditions}")
        
        # 1. 평균 임베딩 계산
        print("\n[Step 1/3] 평균 임베딩 계산...")
        avg_embedding = await self.calculate_embedding_center(panel_uuids)
        
        if avg_embedding is None:
            print("❌ 평균 임베딩 계산 실패 → 빈 리스트 반환")
            logger.error("❌ 평균 임베딩 계산 실패")
            return []
        
        # 2. 유사 패턴 찾기
        print("\n[Step 2/3] 유사 패턴 찾기...")
        similar_patterns = await self.find_top_similar_patterns(avg_embedding, top_k * 2)  # 여유분 확보
        
        # 3. 검색 조건과 중복 제거
        print("\n[Step 3/3] 중복 제거 및 인사이트 생성...")
        filtered_insights = []
        
        for pattern in similar_patterns:
            keyword = pattern['keyword']
            category = pattern['category']
            similarity = pattern['similarity']
            
            # 검색 조건에 이미 포함된 키워드 제외
            if self._is_duplicate_condition(keyword, search_conditions):
                print(f"  ⚠️ 중복 제거: {keyword} (검색 조건에 포함)")
                logger.info(f"   ⚠️ 중복 제거: {keyword} (검색 조건에 포함)")
                continue
            
            # 인사이트 포맷 생성
            insight = {
                "feature": category,
                "value": keyword,
                "similarity": round(similarity, 4),
                "insight": f"이 그룹은 '{keyword}' 특성과 높은 연관성을 보입니다 (유사도: {similarity:.2%}).",
                "confidence": "high" if similarity > 0.7 else "medium"
            }
            
            filtered_insights.append(insight)
            print(f"  ✅ 인사이트 생성: {keyword} (유사도: {similarity:.4f})")
            
            # top_k개 채우면 중단
            if len(filtered_insights) >= top_k:
                break
        
        print("\n" + "="*60)
        print(f"📊 최종 인사이트: {len(filtered_insights)}개")
        for i, ins in enumerate(filtered_insights, 1):
            print(f"  {i}. {ins['value']} ({ins['feature']}) - {ins['similarity']}")
        print("="*60 + "\n")
        
        logger.info(f"📊 최종 인사이트: {len(filtered_insights)}개")
        return filtered_insights
    
    def _is_duplicate_condition(
        self, 
        keyword: str, 
        search_conditions: Dict[str, Any]
    ) -> bool:
        """검색 조건과 중복 체크"""
        keyword_lower = keyword.lower()
        
        # 직업 조건 체크
        if search_conditions.get('job'):
            if keyword_lower in search_conditions['job'].lower():
                return True
        
        # 지역 조건 체크
        if search_conditions.get('location'):
            if keyword_lower in search_conditions['location'].lower():
                return True
        
        # 소득 조건 체크
        if search_conditions.get('income_keyword'):
            if keyword_lower in search_conditions['income_keyword'].lower():
                return True
        
        return False


# 싱글톤 인스턴스
embedding_insight_engine = EmbeddingInsightEngine()