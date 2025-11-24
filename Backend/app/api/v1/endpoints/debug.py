# app/api/v1/endpoints/debug.py
"""
디버그 전용 엔드포인트
테스트 환경에서 DB 상태 확인
"""
from fastapi import APIRouter, HTTPException
import traceback

from app.utils.database import execute_fetch_query
from app.services.search import vector_service
router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/gender")
async def debug_gender_endpoint():
    try:
        print("\n" + "="*60)
        print("DATABASE DEBUG INFO")
        print("="*60)
        
        query1 = "SELECT DISTINCT gender, COUNT(*) as count FROM panel_master GROUP BY gender"
        result1 = await execute_fetch_query(query1)
        print("\nGender Values Distribution:")
        print("-" * 40)
        for row in result1:
            print(f"  gender: '{row.get('gender')}' -> {row.get('count')}명")
        
        query2 = "SELECT COUNT(*) as total FROM panel_master"
        result2 = await execute_fetch_query(query2)
        total = result2[0].get('total') if result2 else 0
        print(f"\nTotal Panels: {total}명")
        
        query3 = "SELECT COUNT(*) as vector_count FROM vector_index"
        result3 = await execute_fetch_query(query3)
        vector_count = result3[0].get('vector_count') if result3 else 0
        print(f"Vector Index Records: {vector_count}개")
        
        print("\n" + "="*60 + "\n")
        
        return {
            "status": "success",
            "message": "디버깅 정보가 터미널에 출력되었습니다",
            "summary": {
                "total_panels": total,
                "vector_index_count": vector_count,
                "gender_distribution": result1
            }
        }
    
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n❌ Debug Error:\n{error_detail}\n")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_detail
            }
        )


@router.get("/age-distribution")
async def debug_age_distribution():
    try:
        query1 = """
        SELECT 
            (2025 - birth_year) as age,
            COUNT(*) as count
        FROM panel_master
        WHERE birth_year IS NOT NULL
        GROUP BY birth_year
        ORDER BY age
        """
        all_ages = await execute_fetch_query(query1)
        
        query2 = """
        SELECT 
            (2025 - birth_year) as age,
            COUNT(*) as count
        FROM panel_master
        WHERE birth_year IS NOT NULL
            AND gender = '남'
            AND (2025 - birth_year) BETWEEN 10 AND 19
        GROUP BY birth_year
        ORDER BY age
        """
        teen_males = await execute_fetch_query(query2)
        
        query3 = """
        SELECT COUNT(*) as total
        FROM panel_master
        WHERE (2025 - birth_year) BETWEEN 10 AND 19
        """
        total_teens = await execute_fetch_query(query3)
        
        return {
            "status": "success",
            "all_ages_sample": all_ages[:20],
            "teen_males": teen_males,
            "total_teens": total_teens[0]['total'] if total_teens else 0,
            "summary": {
                "has_10_19_year_olds": len(teen_males) > 0,
                "teen_male_count": sum(r['count'] for r in teen_males) if teen_males else 0,
                "age_range": f"{teen_males[0]['age']}~{teen_males[-1]['age']}세" if teen_males else "없음"
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/vector-test")
async def test_vector_search():
    try:
        test_query = "서울에 사는 30대 직장인"
        
        results = vector_service.semantic_search(
            query_text=test_query,
            top_k=5
        )
        
        return {
            "status": "success",
            "test_query": test_query,
            "results_count": len(results),
            "top_results": results[:3] if results else []
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@router.get("/db-status")
async def check_database_status():
    try:
        from app.database.connection import DatabaseConnection
        
        db_ok = DatabaseConnection.test_connection()
        
        pgvector_ok = DatabaseConnection.check_pgvector_extension()

        tables_query = """
        SELECT 
            'panel_master' as table_name,
            COUNT(*) as count
        FROM panel_master
        UNION ALL
        SELECT 
            'vector_index' as table_name,
            COUNT(*) as count
        FROM vector_index
        """
        table_counts = await execute_fetch_query(tables_query)
        
        vector_dim_query = """
        SELECT 
            array_length(embedding, 1) as dimension,
            COUNT(*) as count
        FROM vector_index
        GROUP BY dimension
        LIMIT 1
        """
        vector_dim = await execute_fetch_query(vector_dim_query)
        
        return {
            "status": "healthy" if db_ok and pgvector_ok else "degraded",
            "database": {
                "postgres_connected": db_ok,
                "pgvector_enabled": pgvector_ok
            },
            "tables": {
                row['table_name']: row['count'] 
                for row in table_counts
            },
            "vector_config": {
                "dimension": vector_dim[0]['dimension'] if vector_dim else None,
                "total_vectors": vector_dim[0]['count'] if vector_dim else 0
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )