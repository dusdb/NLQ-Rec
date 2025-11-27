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
        # 카테고리별 대표 키워드 정의 (대폭 확장 및 구체화)
        self.category_keywords = {
            "job": [
                # 전문직
                "의사", "내과의", "외과의", "피부과 전문의", "치과의사",
                "변호사", "검사", "판사", "회계사", "세무사", "건축가",
                "약사", "임상 약사", "한의사", "수의사", "간호사", "물리치료사",
                "작업치료사", "임상심리사", "노무사", "관세사", "변리사",

                # IT/기술직
                "프론트엔드 개발자", "백엔드 개발자", "풀스택 개발자",
                "데이터 사이언티스트", "데이터 엔지니어", "ML 엔지니어",
                "AI 엔지니어", "LLM 엔지니어", "DevOps 엔지니어",
                "클라우드 엔지니어", "보안 전문가", "시스템 엔지니어",
                "네트워크 엔지니어", "SRE 엔지니어",
                "모바일 앱 개발자", "iOS 개발자", "안드로이드 개발자",
                "게임 클라이언트 개발자", "게임 서버 개발자", "블록체인 개발자",
                "임베디드 개발자", "펌웨어 개발자",
                "UI 디자이너", "UX 디자이너", "프로덕트 디자이너",

                # 사무/관리직
                "대기업 사원", "중소기업 직원", "외국계 기업 직원",
                "공무원", "공기업 직원", "공공기관 직원",
                "인사 담당자", "채용 담당자", "교육 담당자",
                "마케팅 매니저", "브랜드 매니저", "퍼포먼스 마케터",
                "영업 관리자", "B2B 영업", "B2C 영업", "해외영업 담당자",
                "재무 담당자", "회계 담당자", "IR 담당자", "총무 담당자",
                "프로젝트 매니저", "프로덕트 매니저", "서비스 기획자",

                # 경영/관리
                "CEO", "CFO", "COO", "CTO", "CMO",
                "임원", "이사", "상무", "전무",
                "본부장", "실장", "팀장", "부장", "차장", "과장", "주임", "사원",
                "스타트업 창업자", "1인 기업가", "프리랜서", "컨설턴트",
                "경영 컨설턴트", "IT 컨설턴트", "전략 컨설턴트",

                # 자영업/소상공인
                "카페 운영", "식당 운영", "분식점 운영", "술집 운영",
                "편의점 운영", "베이커리 운영", "배달 전문점 운영",
                "부동산 중개업", "부동산 컨설턴트",
                "미용실 운영", "네일샵 운영", "피부관리샵 운영",
                "학원 강사", "학원 원장", "과외 강사",
                "운전기사", "대리운전 기사", "택배 기사", "배달 라이더",
                "프랜차이즈 사업자", "온라인 쇼핑몰 운영자",

                # 교육
                "초등교사", "중등교사", "고등학교 교사",
                "대학교수", "시간강사", "전문대 교수",
                "유치원 교사", "보육교사",
                "코딩 학원 강사", "스터디 운영자", "멘토링 강사",

                # 창작/예술
                "작가", "웹소설 작가", "에세이 작가",
                "예술가", "화가", "일러스트레이터",
                "유튜버", "스트리머", "인플루언서", "크리에이터",
                "사진작가", "영상 감독", "편집자",
                "배우", "뮤지션", "보컬리스트", "작곡가", "프로듀서",
                "성우", "라디오 진행자",
                "웹툰 작가", "만화가", "애니메이터",

                # 생산/기술
                "제조업 기술자", "공장 관리자", "라인 관리자",
                "기계 설비 기술자", "전기 기사", "기계 기사",
                "자동차 정비사", "품질 관리 담당자", "생산 관리 담당자",

                # 서비스직
                "호텔 직원", "리셉션 직원", "콘시어지",
                "항공 승무원", "지상직 승무원",
                "미용사", "헤어 스타일리스트", "네일아티스트",
                "요리사", "셰프", "제빵사", "바리스타",
                "헬스 트레이너", "PT 트레이너", "필라테스 강사", "요가 강사"
            ],

            "lifestyle": [
                # 소비 성향
                "명품 애호가", "플렉스 소비 성향", "가성비 추구자",
                "알뜰 소비자", "극단적 절약가", "충동 구매자",
                "계획적 소비자", "구매 전 비교 검색 습관",
                "브랜드 충성도 높음", "브랜드 이미지 중시",
                "신제품 얼리어답터", "테크 얼리어답터",
                "친환경 브랜드 선호", "국산 브랜드 선호",

                # 여가 활동
                "주말 등산", "아침 등산", "야간 등산",
                "캠핑 애호가", "차박 캠핑", "글램핑 선호",
                "해외여행 자주 감", "유럽 여행 선호", "일본 여행 선호",
                "국내여행 선호", "호캉스 선호", "맛집 투어 즐김",
                "집순이", "집돌이", "홈카페 즐김",
                "인스타그래머", "브이로그 촬영", "틱톡 촬영",

                # 건강/운동
                "헬스장 등록", "헬스 3회 이상 운동", "집에서 홈트",
                "요가 수련", "필라테스", "크로스핏", "러닝 크루",
                "마라톤 참가", "사이클링", "로드 자전거", "MTB 자전거",
                "등산 동호회", "수영", "테니스 레슨", "골프 레슨",

                # 문화생활
                "영화관 자주 감", "OTT로 영화 시청", "독립영화 선호",
                "공연 관람", "연극 관람", "뮤지컬 관람",
                "전시회 방문", "아트페어 방문", "콘서트 참여",
                "독서 모임", "북클럽 회원", "팟캐스트 청취",

                # 가족/관계
                "가족 우선주의", "부모님과 동거", "부모님과 자주 만남",
                "자녀 교육 열성", "사교육 중시", "공교육 중시",
                "반려동물과 생활", "반려견 가족", "반려묘 가족",
                "싱글 라이프", "솔로 라이프 만족",
                "연애 중", "결혼 준비 중", "신혼부부", "육아맘", "육아대디",

                # 라이프스타일
                "미니멀리즘", "제로웨이스트", "비건 라이프",
                "친환경 실천", "텀블러 항상 사용",
                "디지털 노마드", "원격 근무 선호",
                "워라밸 중시", "칼퇴 중시", "야근 거부 성향",
                "자기계발 열심", "온라인 강의 수강", "자격증 준비",
                "사이드 프로젝트", "N잡러", "창업 준비 중"
            ],

            "consumption": [
                # 소득 수준
                "연봉 3천만원대", "연봉 4천만원대", "연봉 5천만원대",
                "연봉 6천만원대", "연봉 7천만원대", "연봉 8천만원대",
                "연봉 9천만원대", "연봉 1억 이상",
                "고소득 전문직", "중산층", "서민층", "저소득층",

                # 소비 패턴
                "명품 구매", "한정판 제품 선호", "리셀 시장 참여",
                "해외 직구", "공동구매 참여", "중고거래",
                "구독 서비스 다수", "OTT 구독 3개 이상",
                "할인 쿠폰 적극 활용", "포인트 적립 열심",
                "정기 배송", "정기 구독 커머스 이용",
                "배달앱 자주 이용", "편의점 자주 이용",

                # 투자/재테크
                "주식 투자자", "해외 주식 투자자", "미국 주식 투자자",
                "부동산 투자", "전세 투자", "상가 투자",
                "코인 투자", "NFT 투자 경험",
                "예적금 선호", "적금 위주 재테크",
                "펀드 가입자", "연금저축 가입",
                "보험 다수 가입", "저축 우선", "지출 관리 철저",

                # 쇼핑 채널
                "백화점 쇼핑", "아울렛 쇼핑", "면세점 쇼핑",
                "온라인 쇼핑 선호", "라이브 커머스 시청",
                "쿠팡 로켓배송", "쿠팡 와우 회원",
                "SSG 닷컴", "11번가", "지마켓", "네이버 쇼핑",
                "무신사 이용", "올리브영 단골", "다이소 애용"
            ],

            "hobby": [
                # 실내 취미
                "게임 애호가", "콘솔 게임 즐김", "PC 게임 즐김",
                "넷플릭스 정주행", "OTT 드라마 몰아보기", "애니메이션 시청",
                "유튜브 시청", "ASMR 시청", "브이로그 시청",
                "독서광", "전자책 위주 독서", "오디오북 청취",
                "그림 그리기", "디지털 드로잉", "수채화 그리기",
                "악기 연주", "피아노 연주", "기타 연주",
                "노래방", "보컬 레슨", "작곡 취미",
                "보드게임", "퍼즐", "프라모델 조립", "레고 조립",
                "프로그래밍", "사이드 프로젝트 개발",

                # 실외 취미
                "등산", "트레킹", "산책", "조깅",
                "캠핑", "백패킹", "차박",
                "낚시", "바다낚시", "민물낚시",
                "골프", "스크린골프", "테니스", "배드민턴",
                "자전거 타기", "로드 사이클", "MTB",
                "드라이브", "야경 드라이브",

                # 창작 활동
                "사진 촬영", "필름 카메라 사용", "풍경 사진 촬영",
                "영상 편집", "브이로그 편집", "숏폼 영상 제작",
                "블로그 운영", "글쓰기", "일기 쓰기",
                "DIY 공예", "비즈 공예", "목공", "뜨개질",
                "베이킹", "디저트 만들기", "집밥 요리", "정원 가꾸기",

                # 수집/덕질
                "피규어 수집", "스니커즈 수집", "레고 수집", "앨범 수집",
                "아이돌 팬", "팬클럽 활동", "굿즈 수집",
                "K팝 팬", "콘서트 원정",
                "애니메이션 덕후", "영화 마니아", "마블 팬", "DC 팬",

                # 반려동물
                "강아지 양육", "고양이 집사", "파충류 키움", "물고기 키움",
                "소형견 선호", "대형견 선호"
            ],

            "health": [
                # 음주
                "음주 안 함", "가끔 음주", "주 1-2회 음주",
                "주 3회 이상 음주", "거의 매일 음주",
                "소주 선호", "맥주 선호", "수제 맥주 선호",
                "와인 선호", "위스키 선호", "칵테일 선호",

                # 건강 관리
                "헬스장 다님", "헬스장 3회 이상 방문", "PT 수강",
                "식단 관리", "칼로리 기록", "저탄고지 식단",
                "영양제 복용", "비타민 복용", "단백질 보충제 복용",
                "정기 검진", "건강검진 매년 시행",
                "다이어트 중", "체중 관리", "체지방 관리",
                "근력 운동", "유산소 운동", "스트레칭 습관",

                # 식습관
                "채식주의자", "비건", "페스코 베지테리언",
                "저탄고지", "간헐적 단식", "하루 한 끼",
                "규칙적 식사", "불규칙한 식사",
                "외식 선호", "집밥 선호", "배달 음식 선호",
                "매운 음식 선호", "단 음식 선호", "짠 음식 선호",

                # 수면/스트레스
                "충분한 수면", "수면 부족", "야행성 생활",
                "불면증", "수면제 복용 경험",
                "명상 실천", "요가로 스트레스 해소",
                "취미로 스트레스 해소", "운동으로 스트레스 해소"
            ],

            "tech": [

                # 기술 활용
                "AI 서비스 적극 활용", "챗GPT 사용", "생성형 AI 관심",
                "이미지 생성 AI 사용", "코딩 보조 AI 사용",
                "스마트홈 구축", "IoT 기기 다수",
                "음성 비서 사용", "홈 IoT 조명 사용",
                "구독 OTT 3개 이상", "음악 스트리밍 구독",

                # SNS 활용
                "인스타그램 활발", "피드 업로드 자주 함",
                "페이스북 활발", "카카오스토리 사용",
                "틱톡 시청", "틱톡 업로드",
                "유튜브 크리에이터", "유튜브 댓글 활동",
                "트위터 활동", "스레드 사용",
                "블로그 운영", "브런치 작가",
                "커뮤니티 활동 잦음", "온라인 카페 운영"
            ],

            "value": [
                # 가치관
                "환경 보호 중시", "동물 권리 옹호",
                "페미니즘 지지", "성평등 중시",
                "사회 정의 관심", "인권 이슈 관심",
                "기부 정기 참여", "후원 단체 정기 후원",
                "봉사활동 참여", "지역사회 활동 참여",

                # 정치 성향
                "진보 성향", "보수 성향", "중도 성향",
                "정치 무관심", "정치 이슈 적극 참여",

                # 종교
                "기독교", "천주교", "불교", "원불교",
                "천도교", "이슬람교", "힌두교", "무교",
                "영성 추구", "명상 중심 가치관"
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
        print("\n" + "=" * 60)
        print("🚀 임베딩 기반 인사이트 추출 시작")
        print("=" * 60)
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

        print("\n" + "=" * 60)
        print(f"📊 최종 인사이트: {len(filtered_insights)}개")
        for i, ins in enumerate(filtered_insights, 1):
            print(f"  {i}. {ins['value']} ({ins['feature']}) - {ins['similarity']}")
        print("=" * 60 + "\n")

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
