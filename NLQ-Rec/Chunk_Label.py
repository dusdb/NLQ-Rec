import re
import json
import uuid
from pathlib import Path

CHUNK_SIZE = 900
CHUNK_OVERLAP = 0.15
INPUT_PATH = Path("data/cleaned_data/vector_data.json")
OUTPUT_PATH = Path("data/cleaned_data/chunked_labeled.jsonl")

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

    # ✅ 결측 필드 문맥 치환
    raw_text = re.sub(r'None년생', '출생년도 정보 없음', raw_text)
    raw_text = re.sub(r' 에 거주합니다', '거주지 정보 없음', raw_text)
    raw_text = re.sub(r'성별은\s?\(으\)로[,\s]?', '성별 정보 없음 ', raw_text)

    sentences = sentence_split(raw_text)
    chunks = recursive_chunk(sentences, CHUNK_SIZE, CHUNK_OVERLAP)
    for text in chunks:
        yield {
            "vector_uuid": str(uuid.uuid4()),
            "panel_uuid": record.get("panel_uuid"),
            "response_uuid": record.get("response_uuid"),
            "answer_text": text,
            "embedding": None
        }

if __name__ == "__main__":
    print("🔹 청킹 + 라벨링 시작")
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {INPUT_PATH}")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

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
