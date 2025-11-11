import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path="data/.env")

print("DB_HOST =", repr(os.getenv("DB_HOST")))
print("DB_USER =", repr(os.getenv("DB_USER")))
print("DB_PASSWORD =", repr(os.getenv("DB_PASSWORD")))
print("DB_PASSWORD_LENGTH =", len(os.getenv("DB_PASSWORD") or ""))

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require",
    )
    print("✅ Neon PostgreSQL 연결 성공")
    conn.close()
except Exception as e:
    print("❌ 연결 실패:", e)
