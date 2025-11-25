# app/services/response_formatter.py
"""
응답 데이터 포맷팅 서비스
DB 원본 데이터를 프론트엔드 형식으로 변환
"""
from typing import Dict, Any, List
from datetime import datetime
import json


def convert_panel_to_frontend_format(panel: Dict[str, Any]) -> Dict[str, Any]:

    current_year = datetime.now().year

    birth_year = panel.get('birth_year')
    if birth_year is None or birth_year == 0:
        age = None
        age_display = "미기재"
    else:
        age = current_year - birth_year
        age_display = f"{age}세"

    region_main = (panel.get('region_main') or '').strip()
    region_sub = (panel.get('region_sub') or '').strip()
    location = f"{region_main} {region_sub}".strip() if region_main else '미기재'
    
    job = panel.get('job_category') or '미기재'

    gender_str = panel.get('gender') or '미기재'

    interests = panel.get('interests')
    if interests is None:
        interests = ['기타']
    elif isinstance(interests, str):
        try:
            interests = json.loads(interests) if interests.startswith('[') else [interests]
        except:
            interests = [interests]
 
    bio_sentence = ""

    if region_main:
        location_text = f"{region_main} {region_sub}".strip()
        if panel.get('education'):
            bio_sentence += f"{location_text} 거주, {panel.get('education')} 학력의 "
        else:
            bio_sentence += f"{location_text} 거주하는 "

    if age is not None and gender_str != '미기재':
        bio_sentence += f"{age}세 {gender_str}입니다. "

    job_category_clean = panel.get('job_category') or '미기재'
    if '(' in job_category_clean:
        job_category_clean = job_category_clean.split('(')[0].strip()
    
    if panel.get('job_category') and panel.get('job_category') != '미기재':
        bio_sentence += f"{job_category_clean}"
        
        if panel.get('job_detail'):
            bio_sentence += f" 분야에서 근무하고 있으며"
        else:
            bio_sentence += "이며"

    if panel.get('car_brand'):
        if bio_sentence and not bio_sentence.endswith('며'):
            bio_sentence += ", "
        bio_sentence += f" {panel.get('car_brand')} 차량을 보유하고 있습니다."
    elif bio_sentence:
        if not bio_sentence.endswith('.'):
            bio_sentence += "."

    bio_summary = bio_sentence.strip() if bio_sentence else "정보 없음"

    grouped_details = {
        "기본 정보": [],
        "경제 활동": [],
        "라이프스타일": []
    }

    if panel.get('birth_year'):
        grouped_details["기본 정보"].append({
            "label": "출생년도", 
            "value": str(panel.get('birth_year'))
        })
    
    if panel.get('marital_status'):
        grouped_details["기본 정보"].append({
            "label": "결혼 상태", 
            "value": panel.get('marital_status')
        })
    
    if panel.get('child_num'):
        grouped_details["기본 정보"].append({
            "label": "자녀 수", 
            "value": f"{panel.get('child_num')}명"
        })
    
    if panel.get('family_num'):
        grouped_details["기본 정보"].append({
            "label": "가족 구성", 
            "value": panel.get('family_num')
        })
    
    if panel.get('education'):
        grouped_details["기본 정보"].append({
            "label": "학력", 
            "value": panel.get('education')
        })

    if panel.get('job_category'):
        grouped_details["경제 활동"].append({
            "label": "직업", 
            "value": panel.get('job_category')
        })
    
    if panel.get('job_detail'):
        grouped_details["경제 활동"].append({
            "label": "직무", 
            "value": panel.get('job_detail')
        })
    
    if panel.get('personal_income'):
        grouped_details["경제 활동"].append({
            "label": "개인 소득", 
            "value": panel.get('personal_income')
        })
    
    if panel.get('household_income'):
        grouped_details["경제 활동"].append({
            "label": "가구 소득", 
            "value": panel.get('household_income')
        })

    if panel.get('car_brand'):
        car_info = panel.get('car_brand')
        if panel.get('car_model'):
            car_info += f" {panel.get('car_model')}"
        grouped_details["라이프스타일"].append({
            "label": "차량", 
            "value": car_info + " 보유"
        })
    elif panel.get('has_car') == '없다':
        grouped_details["라이프스타일"].append({
            "label": "차량", 
            "value": "미보유"
        })
    
    if panel.get('owned_phone_model'):
        grouped_details["라이프스타일"].append({
            "label": "휴대폰", 
            "value": panel.get('owned_phone_model')
        })
    elif panel.get('owned_phone_brand'):
        grouped_details["라이프스타일"].append({
            "label": "휴대폰", 
            "value": panel.get('owned_phone_brand')
        })
    
    if panel.get('smoking_exp'):
        smoking_value = "비흡연" if panel.get('smoking_exp') == "담배를 피워본 적이 없다" else panel.get('smoking_exp')
        grouped_details["라이프스타일"].append({
            "label": "흡연", 
            "value": smoking_value
        })
    
    grouped_details = {k: v for k, v in grouped_details.items() if v}

    result = {
        "id": panel.get('panel_id', 'P-Unknown'),
        "panel_id": panel.get('panel_id'),
        "panel_uuid": panel.get('panel_uuid'),
        "birth_year": panel.get('birth_year'),
        "gender": panel.get('gender'),
        "region_main": panel.get('region_main'),
        "region_sub": panel.get('region_sub'),
        "job_category": job_category_clean,
        "job_detail": panel.get('job_detail'),
        "education": panel.get('education'),
        "marital_status": panel.get('marital_status'),
        "car_brand": panel.get('car_brand'),
        "car_model": panel.get('car_model'),
        "personal_income": panel.get('personal_income'),
        "household_income": panel.get('household_income'),
        "owned_phone_brand": panel.get('owned_phone_brand'),
        "owned_phone_model": panel.get('owned_phone_model'),
        "child_num": panel.get('child_num'),
        "family_num": panel.get('family_num'),
        "has_car": panel.get('has_car'),
        "smoking_exp": panel.get('smoking_exp'),
        "age": age_display,
        "location": location,
        "job": job,
        "interests": interests,
        "bio": bio_summary,  
        "grouped_details": grouped_details
    }

    similarity = panel.get('similarity')
    answer_text = panel.get('answer_text')
    
    if similarity is not None:
        result['similarity_score'] = round(float(similarity), 4)
    if answer_text:
        result['matched_content'] = answer_text[:150]
    
    return result


def convert_panels_bulk(panels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [convert_panel_to_frontend_format(panel) for panel in panels]