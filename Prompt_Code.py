import os
import json
import uuid

INPUT_FILE = "./data/cleaned_data/rdb_data.json"
OUTPUT_FILE = "./data/cleaned_data/vector_data.json"


def clean(val):
    if val in [None, "", "null", "None"]:
        return None
    return str(val).strip()


def make_prompt(panel, responses):
    """panel_master + response_meta 기반 전체 문장 생성"""
    gender = clean(panel.get("gender"))
    birth = clean(panel.get("birth_year"))
    region_main = clean(panel.get("region_main"))
    region_sub = clean(panel.get("region_sub"))
    marital = clean(panel.get("marital_status"))
    child_num = clean(panel.get("child_num"))
    family_num = clean(panel.get("family_num"))
    education = clean(panel.get("education"))
    job_cat = clean(panel.get("job_category"))
    job_det = clean(panel.get("job_detail"))
    personal_income = clean(panel.get("personal_income"))
    household_income = clean(panel.get("household_income"))
    owned_products = clean(panel.get("owned_products"))
    owned_phone_brand = clean(panel.get("owned_phone_brand"))
    owned_phone_model = clean(panel.get("owned_phone_model"))
    has_car = clean(panel.get("has_car"))
    car_brand = clean(panel.get("car_brand"))
    car_model = clean(panel.get("car_model"))
    smoking_exp = clean(panel.get("smoking_exp"))
    smoking_brands = clean(panel.get("smoking_brands"))
    smoking_brands_other = clean(panel.get("smoking_brands_other"))
    heated_tobacco_exp = clean(panel.get("heated_tobacco_exp"))
    heated_tobacco_other = clean(panel.get("heated_tobacco_other"))
    alcohol_exp = clean(panel.get("alcohol_exp"))
    alcohol_exp_other = clean(panel.get("alcohol_exp_other"))

    # --- 기본 문장 ---
    base_sentence = f"{birth}년생 {gender or ''}으로, {region_main or ''} {region_sub or ''}에 거주합니다.".strip()

    if marital:
        base_sentence += f" 결혼 상태는 {marital}입니다."
    if family_num or child_num:
        base_sentence += f" 가족은 총 {family_num or '미상'}이며, 자녀는 {child_num or '미상'}명 있습니다."
    if education:
        base_sentence += f" 최종 학력은 {education}입니다."
    if job_cat:
        base_sentence += f" 직업은 {job_cat}이며, 세부 직무는 {job_det or '미상'}입니다."
    if personal_income or household_income:
        base_sentence += f" 월평균 개인소득은 {personal_income or '미상'}이며, 가구소득은 {household_income or '미상'}입니다."
    if owned_products:
        base_sentence += f" 보유 전자제품은 {owned_products}입니다."
    if owned_phone_brand or owned_phone_model:
        base_sentence += f" 휴대폰은 {owned_phone_brand or ''} {owned_phone_model or ''}를 사용합니다."
    if has_car == "있다":
        if car_brand or car_model:
            base_sentence += f" 차량을 보유하고 있으며, {car_brand or '미상'} {car_model or ''}를 운전합니다."
        else:
            base_sentence += " 차량을 보유하고 있습니다."
    elif has_car == "없다":
        base_sentence += " 차량을 보유하고 있지 않습니다."
    if smoking_exp:
        base_sentence += f" 흡연 경험은 {smoking_exp}이며,"
        if smoking_brands or smoking_brands_other:
            base_sentence += f" 주로 {smoking_brands or smoking_brands_other} 브랜드를 이용했습니다."
    if heated_tobacco_exp:
        base_sentence += f" 전자담배 이용 경험은 {heated_tobacco_exp}입니다."
        if heated_tobacco_other:
            base_sentence += f" 추가 내용으로는 {heated_tobacco_other}가 있습니다."
    if alcohol_exp:
        base_sentence += f" 주로 {alcohol_exp}을(를) 마십니다."
        if alcohol_exp_other:
            base_sentence += f" 기타로는 {alcohol_exp_other}이(가) 있습니다."

    # --- 설문 응답 문장 ---
    response_sentences = []
    for r in responses:
        q = clean(r.get("question_text"))
        a = clean(r.get("answer_text"))
        if q and a:
            response_sentences.append(f"‘{q}’ 질문에 ‘{a}’라고 답했습니다.")

    full_text = base_sentence + " " + " ".join(response_sentences)
    return full_text.strip() if full_text else None


def generate_vector_json():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    panels = data.get("panel_master", [])
    responses = data.get("response_meta", [])

    # panel_uuid 기준으로 응답 묶기
    response_map = {}
    for r in responses:
        pid = r.get("panel_uuid")
        if not pid:
            continue
        if pid not in response_map:
            response_map[pid] = []
        response_map[pid].append(r)

    vector_records = []

    # panel + response 매칭
    for panel in panels:
        pid = panel.get("panel_uuid")
        res_list = response_map.get(pid, [])

        for res in res_list:
            text = make_prompt(panel, [res])
            if text:
                vector_records.append({
                    "vector_uuid": None,
                    "panel_uuid": pid,
                    "response_uuid": res.get("response_uuid"),
                    "answer_text": text,
                    "embedding": None
                })

    # response만 존재하는 경우도 저장
    known_ids = {p.get("panel_uuid") for p in panels}
    for r in responses:
        pid = r.get("panel_uuid")
        if pid not in known_ids:
            text = f"익명 응답자가 ‘{clean(r.get('question_text'))}’ 질문에 ‘{clean(r.get('answer_text'))}’라고 답했습니다."
            vector_records.append({
                "vector_uuid": None,
                "panel_uuid": pid,
                "response_uuid": r.get("response_uuid"),
                "answer_text": text,
                "embedding": None
            })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(vector_records, f, ensure_ascii=False, indent=2)

    print(f"✅ 벡터DB용 JSON 생성 완료 ({len(vector_records)}개 레코드)")
    print(f"📁 저장 경로: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_vector_json()
