"""
API 테스트 스크립트

사용법:
1. 서버 실행: uvicorn app.main:app --reload
2. 다른 터미널에서: python test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_root():
    """루트 엔드포인트 테스트"""
    print("\n=== 루트 엔드포인트 테스트 ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_health():
    """헬스 체크 테스트"""
    print("\n=== 헬스 체크 테스트 ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_analyze_query():
    """질의 분석 테스트"""
    print("\n=== 질의 분석 테스트 ===")
    
    test_queries = [
        "서울에 사는 20대 남성 중 IT 직종 종사자를 찾아줘",
        "30대 여성이면서 대졸 이상, 월 소득 500만원 이상인 사람들",
        "아이폰 사용자 중에서 강남에 사는 사람"
    ]
    
    for query in test_queries:
        print(f"\n쿼리: {query}")
        response = requests.post(
            f"{BASE_URL}/api/v1/search/analyze",
            json={"query": query}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print(f"Error: {response.text}")


def test_full_search():
    """전체 검색 파이프라인 테스트"""
    print("\n=== 전체 검색 테스트 ===")
    
    query = "서울에 사는 20대 남성 중 IT 직종 종사자를 찾아줘"
    
    print(f"쿼리: {query}")
    response = requests.post(
        f"{BASE_URL}/api/v1/search/full",
        json={"query": query}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ 검색 성공!")
        print(f"분석된 조건: {json.dumps(result.get('query_analysis'), indent=2, ensure_ascii=False)}")
        print(f"\nSQL 쿼리:\n{result.get('sql_query')}")
        print(f"\n결과 수: {result.get('results_count')}")
        print(f"결과: {json.dumps(result.get('results'), indent=2, ensure_ascii=False)}")
        print(f"\n인사이트: {json.dumps(result.get('insights'), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    try:
        print("🚀 API 테스트 시작")
        print("=" * 50)
        
        test_root()
        test_health()
        
        # Claude API 키가 설정되어 있어야 아래 테스트 가능
        print("\n\n⚠️  다음 테스트는 .env 파일에 ANTHROPIC_API_KEY가 설정되어 있어야 합니다.")
        input("계속하려면 Enter를 누르세요...")
        
        test_analyze_query()
        test_full_search()
        
        print("\n" + "=" * 50)
        print("✅ 모든 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 서버에 연결할 수 없습니다.")
        print("서버를 실행했는지 확인하세요: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")