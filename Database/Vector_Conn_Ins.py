import os
import json
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import time

# === .env 불러오기 ===
#load_dotenv(dotenv_path="C:/Hansung_Project/NLQ-Rec/data/.env")
load_dotenv(dotenv_path="/content/drive/MyDrive/.env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# === PostgreSQL 연결 ===
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    sslmode="require"
)
cur = conn.cursor()
print("✅ PostgreSQL 연결 성공")

# === JSONL 파일 읽기 ===
#VECTOR_FILE = Path("data/cleaned_data/embedded.jsonl")
VECTOR_FILE = Path("/content/drive/MyDrive/embedded.jsonl")

records = []

with open(VECTOR_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

total = len(records)
print(f"📄 불러온 데이터 개수: {total}개")

# === DB에 이미 저장된 개수 확인 ===
cur.execute("SELECT COUNT(*) FROM vector_index;")
inserted_count = cur.fetchone()[0]
print(f"⚙️ 이미 DB에 저장된 데이터: {inserted_count}건 → {inserted_count + 1}번째부터 재개")

# === 진행률 변수 ===
start_time = time.time()
success_count = 0
fail_count = 0
batch_size = 1000

# === 데이터 삽입 시작 ===
for i, vec in enumerate(records[inserted_count:], start=inserted_count + 1):
    try:
        embedding = vec.get("embedding")
        embedding_str = "[" + ", ".join(map(str, embedding)) + "]" if isinstance(embedding, list) else None

        cur.execute("""
            INSERT INTO vector_index (
                vector_uuid, panel_uuid, response_uuid, embedding, answer_text
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (vector_uuid) DO NOTHING
        """, (
            vec["vector_uuid"],
            vec["panel_uuid"],
            vec["response_uuid"],
            embedding_str,
            vec["answer_text"]
        ))

        success_count += 1

        # 1000건마다 커밋 및 진행률 출력
        if i % batch_size == 0:
            conn.commit()
            elapsed = time.time() - start_time
            progress = (i / total) * 100
            est_total_time = (elapsed / i) * total
            eta = est_total_time - elapsed
            print(f"📊 진행률: {progress:.2f}% ({i}/{total}) | ✅ 성공: {success_count} | ❌ 실패: {fail_count} | ⏱ 경과: {elapsed:.1f}s | 남은 예상: {eta/60:.1f}분")

    except Exception as e:
        fail_count += 1
        print(f"⚠️ {i}번째 데이터 삽입 실패: {e}")
        conn.rollback()

# === 마지막 커밋 ===
conn.commit()
elapsed = time.time() - start_time
print(f"\n✅ vector_index 데이터 삽입 완료!")
print(f"📦 총 데이터: {total} | ✅ 성공: {success_count} | ❌ 실패: {fail_count} | ⏱ 총 경과시간: {elapsed:.1f}초")

cur.close()
conn.close()
print("✅ 연결 종료")
