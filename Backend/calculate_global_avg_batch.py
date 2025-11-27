"""
배치 처리로 전체 평균 임베딩 계산 (메모리 효율적)
실행: python calculate_global_avg_batch.py
"""
import asyncio
import asyncpg
import numpy as np
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

async def calculate_global_average_batch():
    print("="*60)
    print("🚀 배치 처리로 전체 평균 계산 (메모리 효율적)")
    print("="*60)
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        print(f"📡 DB 연결 중: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        
        print("✅ DB 연결 성공!")
        
        # 전체 개수
        count = await conn.fetchval("SELECT COUNT(*) FROM vector_index")
        print(f"📊 전체 임베딩 개수: {count:,}개")
        
        # 배치 크기
        BATCH_SIZE = 10000
        total_batches = (count + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"📦 배치 크기: {BATCH_SIZE:,}개 → 총 {total_batches}개 배치")
        
        # 누적 합계
        sum_embedding = None
        total_count = 0
        
        for batch_num in range(total_batches):
            offset = batch_num * BATCH_SIZE
            print(f"\n🔄 배치 {batch_num + 1}/{total_batches} 처리 중... (offset: {offset:,})")
            
            rows = await conn.fetch(f"""
                SELECT embedding 
                FROM vector_index 
                ORDER BY vector_uuid
                LIMIT {BATCH_SIZE} OFFSET {offset}
            """)
            
            print(f"  ✅ {len(rows):,}개 조회 완료")
            
            for i, row in enumerate(rows):
                emb_data = row['embedding']
                
                # TEXT 형태인 경우
                if isinstance(emb_data, str):
                    # "[0.1, 0.2, ...]" → numpy
                    emb = np.array(json.loads(emb_data), dtype=np.float32)
                else:
                    # BYTEA 형태
                    emb = np.frombuffer(emb_data, dtype=np.float32)
                
                if sum_embedding is None:
                    sum_embedding = emb
                else:
                    sum_embedding += emb
                
                total_count += 1
                
                if (i + 1) % 1000 == 0:
                    print(f"    처리: {i + 1:,}/{len(rows):,}")
            
            print(f"  📊 누적: {total_count:,}개")
        
        # 평균 계산
        global_avg = sum_embedding / total_count
        
        print(f"\n✅ 전체 평균 계산 완료!")
        print(f"   - 총 임베딩: {total_count:,}개")
        print(f"   - 차원: {len(global_avg)}")
        print(f"   - Norm: {np.linalg.norm(global_avg):.4f}")
        
        # JSON 저장
        output = {
            "global_average": global_avg.tolist(),
            "total_embeddings": total_count,
            "dimensions": len(global_avg),
            "norm": float(np.linalg.norm(global_avg))
        }
        
        output_path = Path(__file__).parent / "global_avg.json"
        with open(output_path, "w") as f:
            json.dump(output, f)
        
        print(f"✅ 저장 완료: {output_path}")
        print("="*60)
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(calculate_global_average_batch())