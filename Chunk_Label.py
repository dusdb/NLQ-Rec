import re
import json
import uuid
from pathlib import Path

CHUNK_SIZE = 900
CHUNK_OVERLAP = 0.15
INPUT_PATH = Path("data/cleaned_data/vector_data_haiku_processed_resume.jsonl")
OUTPUT_PATH = Path("data/cleaned_data/chunked_label.jsonl")

# ✅ 중복된 종결어미 자동 정제 함수
def clean_redundant_endings(text: str) -> str:
    """
    '있습니다입니다', '합니다합니다', '선호합니다합니다' 등
    종결 어미 중복 패턴을 제거하고 문장 부드럽게 정제.
    """
    text = re.sub(r'([가-힣]+습니다)\s*\1', r'\1', text)
    text = re.sub(r'([가-힣]+습니다)\s*입니다', r'\1', text)
    text = re.sub(r'([가-힣]+했습니다)\s*입니다', r'\1', text)
    text = re.sub(r'([가-힣]+했습니다)\s*\1', r'\1', text)
    text = re.sub(r'([가-힣]+했다)\s*\1', r'\1', text)
    text = re.sub(r'([가-힣]+다)\s*\1', r'\1', text)

    # 2️⃣ '다다.' 같은 짧은 중복 제거
    text = re.sub(r'(다)\1(\.|$)', r'\1\2', text)

    # 3️⃣ 불필요한 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def sentence_split(text: str):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def recursive_chunk(sentences, chunk_size=900, overlap=0.15):
    chunks = []
    current_chunk = []
    for sent in sentences:
        joined = " ".join(current_chunk + [sent])
        if len(joined) <= chunk_size:
            current_chunk.append(sent)
        else:
            chunks.append(" ".join(current_chunk))
            overlap_count = max(1, int(len(current_chunk) * overlap))
            current_chunk = current_chunk[-overlap_count:]
            current_chunk.append(sent)
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def chunk_and_label(record):
    # 원문 불러오기
    raw_text = str(record.get("answer_text", "")).strip()

    # ✅ 중복된 어미 정제 (1차)
    raw_text = clean_redundant_endings(raw_text)

    sentences = sentence_split(raw_text)
    chunks = recursive_chunk(sentences, CHUNK_SIZE, CHUNK_OVERLAP)

    for text in chunks:
        # ✅ 청크별로도 중복 어미 재정제 (2차 보정)
        cleaned_text = clean_redundant_endings(text)

        yield {
            "vector_uuid": str(uuid.uuid4()),
            "panel_uuid": record.get("panel_uuid"),
            "response_uuid": record.get("response_uuid"),
            "answer_text": cleaned_text,
            "embedding": None
        }


if __name__ == "__main__":
    print("🔹 청킹 + 라벨링 + 문장 정제 시작")
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {INPUT_PATH}")

    records = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄은 무시
                records.append(json.loads(line))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out_f:
        for record in records:
            for chunk in chunk_and_label(record):
                out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                total_chunks += 1

    print(f"✅ 총 {len(records)}개 record 처리 완료")
    print(f"✅ 생성된 청크 수: {total_chunks}개")
    print(f"💾 저장 완료: {OUTPUT_PATH.resolve()}")
