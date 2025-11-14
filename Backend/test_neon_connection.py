# test_neon_connection.py 

import asyncio
import asyncpg
import ssl

async def test_connection():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        conn = await asyncpg.connect(
            user="neondb_owner",
            password="npg_l4gBNpmK1XWM",
            database="neondb",
            host="ep-steep-cloud-a1wwzegi-pooler.ap-southeast-1.aws.neon.tech",
            port=5432,
            ssl=ssl_context
        )
        
        print("✅ 연결 성공!")
        
        # 테이블 확인
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print("\n📊 테이블 목록:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ 연결 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())