# app/services/embedding_insight.py
"""
임베딩 평균 기반 공통 특성 추출 모듈
Lift 지수 대신 코사인 유사도를 사용
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
import json
from pathlib import Path

from app.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class EmbeddingInsightEngine:
    """임베딩 평균 기반 인사이트 추출 엔진"""
    
    def __init__(self):
        # 전체 평균 로드
        self.global_avg = self._load_global_average()
        
        # 카테고리별 대표 키워드 정의 (대폭 확장!)
        self.category_keywords = {
            # === 직업 관련 ===
            "job": [
                "의사", "변호사", "회계사", "세무사", "변리사", "건축사", "약사",
                "개발자", "프로그래머", "데이터 과학자", "AI 엔지니어", "풀스택",
                "디자이너", "UX 디자이너", "그래픽 디자이너", "웹 디자이너",
                "마케터", "디지털 마케터", "브랜드 매니저", "광고 기획자",
                "사무직", "공무원", "공기업", "대기업", "중소기업",
                "교사", "교수", "강사", "학원강사", "과외",
                "간호사", "물리치료사", "방사선사", "임상병리사",
                "자영업", "프리랜서", "1인 기업가", "스타트업", "창업자",
                "서비스직", "판매직", "영업직", "요식업", "요리사",
                "생산직", "기술직", "엔지니어", "연구원", "R&D",
                "금융", "은행원", "증권", "보험", "재무설계사",
                "언론", "기자", "PD", "작가", "방송인",
                "예술가", "음악가", "배우", "모델", "인플루언서",
                "건설", "부동산", "중개인", "인테리어", "시공",
                "운전", "택배", "배달", "물류", "운송",
                "농업", "어업", "축산", "임업", "1차 산업",
                "군인", "경찰", "소방관", "보안", "경비",
                "은퇴", "퇴직", "백수", "주부", "학생", "취준생"
            ],
            
            # === 소비 성향 ===
            "consumption": [
                "연봉 1천만원대", "연봉 2천만원대", "연봉 3천만원대", "연봉 4천만원대",
                "연봉 5천만원대", "연봉 6천만원대", "연봉 7천만원대", "연봉 8천만원대",
                "연봉 9천만원대", "연봉 1억 이상", "고소득", "저소득", "중산층",
                "명품 선호", "럭셔리", "하이엔드", "프리미엄",
                "실용적 소비", "가성비 중시", "알뜰", "절약형",
                "브랜드 충성", "특정 브랜드 선호", "무브랜드",
                "온라인 쇼핑", "오프라인 선호", "백화점", "마트",
                "편의점 자주 이용", "배달앱 자주 이용", "구독 서비스",
                "충동구매", "계획구매", "세일 사냥꾼",
                "해외직구", "면세점", "아울렛",
                "중고거래", "당근마켓", "재테크", "투자"
            ],
            
            # === 라이프스타일 ===
            "lifestyle": [
                "싱글 라이프", "솔로 라이프 만족", "1인 가구", "독신",
                "신혼", "결혼 준비 중", "약혼", "동거",
                "육아", "맘카페", "워킹맘", "전업주부",
                "다자녀", "외동", "무자녀", "DINK",
                "반려동물", "반려견", "반려묘", "펫 용품",
                "문화생활", "공연 관람", "전시회", "뮤지컬",
                "프리미엄 소비", "고급 레스토랑", "파인 다이닝",
                "건강 지향", "웰빙", "유기농", "친환경",
                "미니멀리즘", "정리 정돈", "단순한 삶",
                "워라밸", "여유", "휴식 중시", "힐링",
                "자기계발", "독서", "강의 수강", "자격증",
                "SNS 활동", "인스타그램", "블로그", "유튜브",
                "게임", "e-스포츠", "스트리밍", "넷플릭스",
                "야외활동", "등산", "캠핑 애호가", "낚시",
                "실내활동", "홈트레이닝", "요가", "필라테스",
                "여행", "해외여행", "국내여행", "캠핑카",
                "맛집 탐방", "카페 투어", "와인 선호", "칵테일 선호",
                "패션", "뷰티", "화장품", "스킨케어"
            ],
            
            # === 건강 ===
            "health": [
                "비흡연자", "흡연자", "금연 중", "가끔 흡연", "헤비 스모커",
                "전자담배", "아이코스", "릴", "궐련형",
                "음주 안 함", "소량 음주", "사교적 음주", "주말 음주", "과음",
                "맥주 선호", "소주 선호", "와인 선호", "위스키", "칵테일 선호",
                "건강검진", "병원 정기 방문", "건강 관리", "영양제 복용",
                "운동 안 함", "가끔 운동", "주 3회 이상", "헬스장", "PT",
                "러닝", "조깅", "마라톤", "사이클", "수영",
                "다이어트 중", "체중 관리", "근력 운동", "유산소 운동",
                "채식", "비건", "저염식", "저탄수", "키토",
                "외식 선호", "배달음식", "집밥 선호", "도시락",
                "알레르기", "만성질환", "고혈압", "당뇨", "고지혈증"
            ],
            
            # === 기술/디지털 ===
            "tech": [
                "아이폰 사용자", "갤럭시 사용자", "애플 생태계", "안드로이드",
                "아이패드", "갤럭시탭 사용자", "태블릿", "노트북",
                "맥북", "윈도우", "크롬북", "게이밍 노트북",
                "애플워치 착용", "갤럭시워치 착용", "스마트워치", "웨어러블",
                "에어팟", "갤럭시 버즈", "무선이어폰", "고급 이어폰",
                "스마트홈", "IoT 기기 다수", "AI 스피커", "로봇청소기",
                "게임 콘솔", "플스", "닌텐도", "Xbox",
                "카메라", "미러리스", "DSLR", "드론",
                "IT 얼리어답터", "최신 기기", "기술 매니아",
                "클라우드", "구독형 SW", "OTT", "스트리밍"
            ],
            
            # === 이동/차량 ===
            "mobility": [
                "무차", "차량 없음", "대중교통", "지하철", "버스",
                "현대", "기아", "제네시스", "쉐보레", "르노삼성", "쌍용",
                "벤츠", "BMW", "아우디", "렉서스", "포르쉐", "테슬라",
                "경차", "소형차", "준중형", "중형", "대형",
                "SUV", "세단", "쿠페", "해치백", "왜건",
                "전기차", "하이브리드", "디젤", "가솔린", "LPG",
                "신차", "중고차", "리스", "렌트", "장기렌트",
                "주차", "차고지", "아파트 주차", "노상 주차",
                "자전거", "전동킥보드", "오토바이", "스쿠터",
                "카셰어링", "타다", "우버", "택시"
            ],
            
            # === 주거 ===
            "housing": [
                "자가", "전세", "월세", "반전세", "사글세",
                "아파트", "빌라", "오피스텔", "주택", "다가구",
                "원룸", "투룸", "쓰리룸", "복층", "펜트하우스",
                "신축", "구축", "재건축", "리모델링",
                "역세권", "학군", "숲세권", "강남", "판교",
                "지방", "광역시", "수도권", "서울",
                "부동산 투자", "다주택", "건물주", "임대업",
                "인테리어", "가구", "가전", "홈데코"
            ],
            
            # === 교육 ===
            "education": [
                "고졸", "전문대졸", "대졸", "대학원", "석사", "박사",
                "명문대", "SKY", "서성한", "인서울", "지방대",
                "해외 유학", "MBA", "외국 대학", "교환학생",
                "어학 공부", "영어", "중국어", "일본어", "제2외국어",
                "자격증", "공인중개사", "주택관리사", "기사", "산업기사",
                "코딩 교육", "부트캠프", "온라인 강의", "유데미",
                "학원", "과외", "공부방", "교습소",
                "육아 교육", "영어 유치원", "사교육", "학습지"
            ],
            
            # === 지역 특성 ===
            "location": [
                "서울", "강남", "강북", "강서", "송파", "관악",
                "경기", "인천", "수원", "성남", "고양", "용인",
                "부산", "대구", "광주", "대전", "울산",
                "세종", "제주", "강원", "충청", "전라", "경상",
                "수도권", "지방", "광역시", "중소도시", "농촌",
                "신도시", "구도심", "재개발", "뉴타운",
                "역세권", "대학가", "산업단지", "공단"
            ],
            
            # === 취미 ===
            "hobby": [
                "운동", "헬스", "요가", "필라테스", "크로스핏",
                "러닝", "마라톤", "등산", "트레킹", "클라이밍",
                "수영", "서핑", "스키", "스노보드", "골프",
                "자전거", "사이클", "MTB", "라이딩",
                "여행", "백패킹", "해외여행", "국내여행", "원정",
                "캠핑", "차박", "글램핑", "오토캠핑",
                "독서", "도서관", "서점", "책 수집", "전자책",
                "게임", "PC방", "콘솔", "모바일 게임", "RPG",
                "영화", "넷플릭스", "디즈니플러스", "웨이브", "티빙",
                "음악", "공연", "페스티벌", "콘서트", "악기 연주",
                "요리", "베이킹", "제빵", "바리스타", "홈카페",
                "사진", "카메라", "촬영", "편집", "유튜브",
                "그림", "미술", "캘리그라피", "공예", "DIY",
                "낚시", "바다낚시", "민물낚시", "루어",
                "반려동물", "강아지", "고양이", "햄스터", "파충류"
            ]
        }
    
    
    def _load_global_average(self) -> Optional[np.ndarray]:
        """
        전체 평균 임베딩 로드
        
        Returns:
            전체 평균 벡터 또는 None (파일 없으면)
        """
        try:
            global_avg_path = Path(__file__).parent.parent.parent / "global_avg.json"
            
            if not global_avg_path.exists():
                logger.warning(f"⚠️ 전체 평균 파일 없음: {global_avg_path}")
                return None
            
            with open(global_avg_path, "r") as f:
                data = json.load(f)
            
            global_avg = np.array(data["global_average"], dtype=np.float32)
            logger.info(f"✅ 전체 평균 로드 완료 ({data['total_embeddings']:,}개 기반)")
            
            return global_avg
            
        except Exception as e:
            logger.error(f"❌ 전체 평균 로드 실패: {e}")
            return None

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
        print("🚀 임베딩 기반 인사이트 추출 (Δ embedding)")
        print("="*60)
        print(f"입력: {len(panel_uuids)}개 패널, top_k={top_k}")
        print(f"검색 조건: {search_conditions}")
        
        # 1. 세그먼트 평균 임베딩 계산
        print("\n[Step 1/4] 세그먼트 평균 임베딩 계산...")
        segment_avg = await self.calculate_embedding_center(panel_uuids)
        
        if segment_avg is None:
            print("❌ 평균 임베딩 계산 실패 → 빈 리스트 반환")
            logger.error("❌ 평균 임베딩 계산 실패")
            return []
        
        # 2. ✅ 전체 평균 로드
        print("\n[Step 2/4] 전체 평균 로드...")
        if self.global_avg is None:
            print("⚠️ 전체 평균 파일 없음 → 0벡터 사용 (임시)")
            global_avg = np.zeros_like(segment_avg)
        else:
            global_avg = self.global_avg
            print(f"✅ 전체 평균 로드 완료 (norm: {np.linalg.norm(global_avg):.4f})")
        
        # 3. ✅ Δ embedding 계산
        print("\n[Step 3/4] Δ embedding 계산...")
        delta_embedding = segment_avg - global_avg
        delta_norm = np.linalg.norm(delta_embedding)
        print(f"✅ Δ 계산 완료 (norm: {delta_norm:.4f})")
        
        # 4. 차이 벡터로 유사 패턴 찾기
        print("\n[Step 4/4] 차별적 특징 찾기...")
        similar_patterns = await self.find_top_similar_patterns(delta_embedding, top_k * 2)
        
        # 5. 검색 조건과 중복 제거
        print("\n[Step 5/5] 중복 제거 및 인사이트 생성...")
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