import os
import json
import psycopg2
from dotenv import load_dotenv

# === .env 불러오기 ===
load_dotenv(dotenv_path="C:/Hansung_Project/NLQ-Rec/data/.env")

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
    password=DB_PASSWORD
)
cur = conn.cursor()
print("✅ PostgreSQL 연결 성공")

# === JSON 파일 불러오기 ===
with open("data/cleaned_data/rdb_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

panel_master = data["panel_master"]
response_meta = data["response_meta"]

# === panel_master 삽입 ===
for panel in panel_master:
    cur.execute("""
        INSERT INTO panel_master (
            panel_uuid, panel_id, gender, birth_year, region_main, region_sub,
            marital_status, child_num, family_num, education, job_category,
            job_detail, personal_income, household_income, owned_products,
            owned_phone_brand, owned_phone_model, has_car, car_brand, car_model,
            smoking_exp, smoking_brands, smoking_brands_other,
            heated_tobacco_exp, heated_tobacco_other,
            alcohol_exp, alcohol_exp_other
        )
        VALUES (
            %(panel_uuid)s, %(panel_id)s, %(gender)s, %(birth_year)s, %(region_main)s, %(region_sub)s,
            %(marital_status)s, %(child_num)s, %(family_num)s, %(education)s, %(job_category)s,
            %(job_detail)s, %(personal_income)s, %(household_income)s, %(owned_products)s,
            %(owned_phone_brand)s, %(owned_phone_model)s, %(has_car)s, %(car_brand)s, %(car_model)s,
            %(smoking_exp)s, %(smoking_brands)s, %(smoking_brands_other)s,
            %(heated_tobacco_exp)s, %(heated_tobacco_other)s,
            %(alcohol_exp)s, %(alcohol_exp_other)s
        )
        ON CONFLICT (panel_uuid) DO NOTHING
    """, panel)

# === response_meta 삽입 ===
for resp in response_meta:
    cur.execute("""
        INSERT INTO response_meta (
            response_uuid, survey_id, panel_uuid, question_text, answer_text, answer_at
        )
        VALUES (
            %(response_uuid)s, %(survey_id)s, %(panel_uuid)s, %(question_text)s,
            %(answer_text)s, %(answer_at)s
        )
        ON CONFLICT (response_uuid) DO NOTHING
    """, resp)

# === 커밋 & 종료 ===
conn.commit()
print("✅ 데이터 삽입 완료")

cur.close()
conn.close()
print("✅ 연결 종료")
