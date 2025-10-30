from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv
import json

# 1️⃣ JSON 파일 경로 설정
SAMPLE_JSON = "NLQ-Rec/test.sample.json"
json_file = SAMPLE_JSON #test용

# 2️⃣ .env 파일 로드
load_dotenv()

# 3️⃣ 환경변수에서 API 키 불러오기
MY_API_KEY = os.getenv("OPENAI_API_KEY")

# 4️⃣ ChatAnthropic 모델 초기화
chat_model = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,
    anthropic_api_key=MY_API_KEY
)

# 5️⃣ JSON 파일 읽기
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 6️⃣ 한글화 항목 창의적 변환
for item in data:
    original_text = item.get("한글화", "")
    if not original_text:
        continue  # 한글화 내용 없으면 스킵

    # System prompt (AI 역할 정의)
    system_prompt = """
    당신은 문장을 자연스럽고 창의적으로 바꾸는 AI입니다.
    - 한 문장으로 자연스럽게 변환해 주세요.
    - 불필요하게 여러 옵션을 만들지 마세요.
    - 문장 길이와 톤은 자연스럽게 조절하세요.
    """

    # Human prompt (실제 변환 요청, 여러 줄)
    prompt_template = f"""
    다음 문장을 창의적이고 자연스럽게 바꿔주세요:
    원문: {original_text}
    """

    # ChatPromptTemplate 생성
    template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", prompt_template)
    ])

    # Chain 실행
    chain = template | chat_model
    response = chain.invoke({})

    # 한글화 업데이트
    item["한글화"] = response.content

# 7️⃣ 결과 저장 (복사본 생성)
output_file = "NLQ-Rec/data_creative.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 내 모든 '한글화' 값이 창의적으로 변환되어 '{output_file}'에 저장되었습니다.")
