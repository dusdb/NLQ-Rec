import os
import json
import uuid
import pandas as pd
from glob import glob

BASE_DIR = "./data/raw_data"
QPOLLS_DIR = os.path.join(BASE_DIR, "qpoll")
OUTPUT_FILE = "./data/cleaned_data/rdb_data.json"


# === UUID 생성 ===
def generate_uuid():
    return str(uuid.uuid4())


# === 값 정리 ===
def clean_value(val):
    """공백, null, NaN 처리 및 문자열 정리"""
    if pd.isna(val) or val in ["", "null", "None", None]:
        return None
    return str(val).strip()


def normalize_number(val, limit=None):
    """'4명', '20가구' 등 문자열에서 숫자만 추출, limit 있으면 최대값 검증"""
    if pd.isna(val) or val in ["", "null", "None", None]:
        return None
    val = str(val)
    digits = "".join([ch for ch in val if ch.isdigit()])
    if digits == "":
        return None
    num = int(digits)
    if limit and num > limit:
        return None
    return num


def normalize_family_text(val):
    """가족수는 '1명(혼자거주)' 같은 형태로 문자열 변환"""
    num = normalize_number(val)
    if num is None:
        return None
    if num == 1:
        return f"{num}명(혼자거주)"
    return f"{num}명"


# === 병합 ===
def merge_panel_data():
    """welcome_1과 welcome_2를 panel_id 기준으로 병합하되, 매칭 안 되면 별도 패널로 구분"""

    # 1️⃣ 파일 로드
    with open(os.path.join(BASE_DIR, "welcome_1.json"), "r", encoding="utf-8") as f1:
        welcome1 = json.load(f1)
    with open(os.path.join(BASE_DIR, "welcome_2.json"), "r", encoding="utf-8") as f2:
        welcome2 = json.load(f2)

    # 2️⃣ 인덱싱 (각 파일에서 panel_id 후보 생성)
    w1_index = {}
    for r in welcome1:
        panel_id = clean_value(r.get("mb_sn"))
        panel_id_2 = clean_value(r.get("고유번호"))
        # 두 컬럼 모두 있는 경우 mb_sn 우선 / 둘 다 없으면 anon
        pid = panel_id or panel_id_2 or f"_anon_w1_{uuid.uuid4()}"
        w1_index[pid] = r

    w2_index = {}
    for r in welcome2:
        panel_id = clean_value(r.get("mb_sn"))
        panel_id_2 = clean_value(r.get("고유번호"))
        pid = panel_id or panel_id_2 or f"_anon_w2_{uuid.uuid4()}"
        w2_index[pid] = r

    all_ids = set(w1_index.keys()) | set(w2_index.keys())
    uuid_map = {}
    merged_panels = []

    # 3️⃣ 전체 ID 기준 병합
    for pid in all_ids:
        w1 = w1_index.get(pid)
        w2 = w2_index.get(pid)

        panel_uuid = generate_uuid()
        uuid_map[pid] = panel_uuid

        # --- 기본정보 (welcome_1) ---
        base = {
            "panel_uuid": panel_uuid,
            "panel_id": pid if not pid.startswith("_anon_") else None,
            "gender": clean_value(w1.get("gender") if w1 else None),
            "birth_year": normalize_number(w1.get("birth_year") if w1 else None),
            "region_main": clean_value(w1.get("region_main") if w1 else None),
            "region_sub": clean_value(w1.get("region_sub") if w1 else None),
        }

        # --- 추가정보 (welcome_2) ---
        extra = {
            "marital_status": clean_value(w2.get("결혼여부") if w2 else None),
            "child_num": normalize_number(w2.get("자녀수") if w2 else None, limit=10),
            "family_num": normalize_family_text(w2.get("가족수") if w2 else None),
            "education": clean_value(w2.get("최종학력") if w2 else None),
            "job_category": clean_value(w2.get("직업") if w2 else None),
            "job_detail": clean_value(w2.get("직무") if w2 else None),
            "personal_income": clean_value(w2.get("월평균 개인소득") if w2 else None),
            "household_income": clean_value(w2.get("월평균 가구소득") if w2 else None),
            "owned_products": clean_value(w2.get("보유 전제품") if w2 else None),
            "owned_phone_brand": clean_value(w2.get("보유 휴대폰 단말기 브랜드") if w2 else None),
            "owned_phone_model": clean_value(w2.get("보유 휴대폰 모델명") if w2 else None),
            "has_car": clean_value(w2.get("보유 차량 여부") if w2 else None),
            "car_brand": clean_value(w2.get("자동차 제조사") if w2 else None),
            "car_model": clean_value(w2.get("자동차 모델") if w2 else None),
            "smoking_exp": clean_value(w2.get("흡연 경험") if w2 else None),
            "smoking_brands": clean_value(w2.get("흡연경험 담배브랜드") if w2 else None),
            "smoking_brands_other": clean_value(w2.get("흡연 경험 기타 담배 브랜드") if w2 else None),
            "heated_tobacco_exp": normalize_number(w2.get("궐련형/가열식 전자담배 이용 경험") if w2 else None),
            "heated_tobacco_other": clean_value(w2.get("전자담배 이용경험(기타내용)") if w2 else None),
            "alcohol_exp": clean_value(w2.get("음용경험 술") if w2 else None),
            "alcohol_exp_other": clean_value(w2.get("음용경험 술(기타내용)") if w2 else None),
        }

        merged_panels.append({**base, **extra})

    return merged_panels, uuid_map


# === 설문 응답 로드 ===
def load_response_meta(uuid_map):
    response_meta = []
    qpoll_files = glob(os.path.join(QPOLLS_DIR, "qpoll_join_*.json"))

    for file_path in qpoll_files:
        survey_id = os.path.basename(file_path).replace(".json", "")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for row in data:
            pid = clean_value(row.get("고유번호") or row.get("mb_sn"))
            panel_uuid = uuid_map.get(pid, generate_uuid())
            response_meta.append({
                "response_uuid": generate_uuid(),
                "survey_id": survey_id,
                "panel_uuid": panel_uuid,
                "question_text": clean_value(row.get("질문")),
                "answer_text": clean_value(row.get("답변")),
                "answer_at": clean_value(row.get("설문일시"))
            })

    return response_meta


# === 실행 ===
def run():
    print("📂 패널 데이터 병합 중...")
    panel_master, uuid_map = merge_panel_data()
    print(f"✅ 패널 {len(panel_master)}개 생성")

    print("🧩 설문 응답 로드 중...")
    response_meta = load_response_meta(uuid_map)
    print(f"✅ 응답 {len(response_meta)}개 로드")

    final = {
        "panel_master": panel_master,
        "response_meta": response_meta
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"🎉 완료! {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
