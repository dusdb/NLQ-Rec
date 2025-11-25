import os
import json
import requests
from dotenv import load_dotenv

# Load API KEY from .env
load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")

assert API_KEY and API_KEY.startswith("sk-ant-"), "Please set ANTHROPIC_API_KEY in .env"

API_URL = "https://api.anthropic.com/v1/messages"
MODEL_ID = "claude-3-5-haiku-latest"

# ---------------------------
# ✅ SYSTEM PROMPT 정의
# ---------------------------
SYSTEM_PROMPT = """
당신은 데이터 패널 응답을 표준화된 문장으로 교정하는 전문가입니다.

🎯 목표:
- 모든 문장은 1인칭 서술체로, 완전한 서술문으로 통일합니다.
- 불확실하거나 알 수 없는 정보(‘특정 연도’, ‘특정 지역’, ‘미상’)는 삭제합니다.
- 의미를 바꾸거나 추측하지 않습니다.
- 숫자, 단위, 브랜드명, 지역명, 빈도 등은 그대로 유지합니다.
- ‘질문 + 답변’은 하나의 자연스러운 문단으로 재작성합니다.
- 문단 구조: [출생/거주] → [가족] → [학력/직업] → [소득] → [전자제품 보유] → [차량] → [흡연/음주] → [기타]
- 문장은 '저는 ...입니다/합니다.' 로 끝냅니다.
- 출력은 수정된 문장만 포함합니다.
"""

# ---------------------------
# ✅ 단일 문장 교정 함수
# ---------------------------
def rewrite_answer(text: str) -> str:
    payload = {
        "model": MODEL_ID,
        "max_tokens": 500,
        "temperature": 0.15,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": text}]
            }
        ]
    }

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    res = requests.post(API_URL, headers=headers, json=payload)
    res.raise_for_status()
    out = res.json()

    # 결과 텍스트 추출
    blocks = out["content"]
    result_text = "".join(b.get("text", "") for b in blocks if b["type"] == "text").strip()
    return result_text


# ---------------------------
# ✅ JSONL 일괄 변환 함수
# ---------------------------
def process_jsonl(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    out_lines = []

    for obj in lines:
        old = (obj.get("answer_text") or "").strip()
        if old:
            obj["answer_text"] = rewrite_answer(old)
        out_lines.append(obj)

    with open(output_path, "w", encoding="utf-8") as fw:
        for o in out_lines:
            fw.write(json.dumps(o, ensure_ascii=False) + "\n")

    print("✅ 완료:", output_path)


# ---------------------------
# ✅ CLI 실행
# ---------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="입력 JSONL 파일")
    parser.add_argument("--output", default="processed.jsonl", help="출력 JSONL")
    args = parser.parse_args()

    process_jsonl(args.input, args.output)
