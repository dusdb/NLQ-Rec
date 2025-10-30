#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overlap chunking for survey JSONL files (no normalization/correction).
- Input: one or more .jsonl files with records that include "answer_text"
- Output: for each input X.jsonl -> X_overlap.jsonl written alongside
- Sentence split: ., !, ?, and Korean ending "다." (look-behind free)
- Chunking: sliding window by char length with overlap
"""
import sys, json, re, uuid, argparse
from pathlib import Path
from typing import List, Dict, Any

# -------- Parameters (defaults; can be overridden by CLI) --------
DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 160
MIN_SENTENCE = 10  # min chars; shorter fragments will be merged forward

# Safe sentence split regex (no look-behind)
_SENT_SPLIT = re.compile(r"([.!?]|다\.)\s+")

def sentence_split(text: str) -> List[str]:
    """Split text into sentences using a safe regex and merge tiny fragments."""
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    merged = []
    buf = ""
    for i in range(0, len(parts), 2):
        seg = parts[i]
        tail = parts[i+1] if i+1 < len(parts) else ""
        endp = tail if tail and tail.strip() in [".","!","?","다."] else ""
        sent = (seg + endp).strip()
        if not sent:
            continue
        if len(sent) < MIN_SENTENCE:
            buf = (buf + " " + sent).strip() if buf else sent
        else:
            if buf:
                merged.append(buf)
                buf = ""
            merged.append(sent)
    if buf:
        merged.append(buf)
    return merged

def overlap_chunks(text: str, max_chars: int, overlap: int) -> List[Dict[str, Any]]:
    """Create overlapping chunks from text by sentence groups."""
    if not text:
        return []
    sents = sentence_split(text)
    if not sents:
        sents = [text]
    chunks = []
    i = 0
    cursor = 0
    while i < len(sents):
        start_idx = text.find(sents[i], cursor)
        if start_idx == -1:
            start_idx = cursor
        cur = sents[i]
        j = i + 1
        while j < len(sents) and len(cur) + 1 + len(sents[j]) <= max_chars:
            cur += " " + sents[j]
            j += 1
        end_idx = start_idx + len(cur)
        chunks.append({"start": start_idx, "end": end_idx, "text": cur})
        # advance with overlap window
        i = j
        cursor = max(0, end_idx - overlap)
        # move i to the first sentence whose start is at/after cursor
        while i < len(sents):
            pos = text.find(sents[i], cursor)
            if pos != -1:
                break
            i += 1
    return chunks

def new_vec() -> str:
    return "V_" + uuid.uuid4().hex[:12]

def process_file(in_path: Path, max_chars: int, overlap: int) -> Dict[str, Any]:
    """Process a single .jsonl file and write an _overlap.jsonl file alongside."""
    out_path = in_path.with_name(in_path.stem + "_overlap.jsonl")
    n_records = 0
    n_chunks = 0
    with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_records += 1
            panel_uuid = rec.get("panel_uuid")
            response_uuid = rec.get("response_uuid")
            raw = rec.get("answer_text", "") or ""
            chunks = overlap_chunks(raw, max_chars, overlap)
            for idx, c in enumerate(chunks, start=1):
                ov_chunk = {
                    "panel_uuid": panel_uuid,
                    "response_uuid": response_uuid,
                    "chunk_type": "overlap",
                    "chunk_id": f"{response_uuid}#OV#{idx:04d}" if response_uuid else f"NORESP#OV#{idx:04d}",
                    "vector_uuid": new_vec(),
                    "chunk_text": c["text"],
                    "section": "answer_text_full",
                    "span": {"start_char": c["start"], "end_char": c["end"]},
                    "labels": [],
                    "confidence": 0.85,
                    "meta": {"window": {"max_chars": max_chars, "overlap": overlap},
                             "source_file": in_path.name}
                }
                fout.write(json.dumps(ov_chunk, ensure_ascii=False) + "\n")
                n_chunks += 1
    return {"file": in_path.name, "records": n_records, "chunks": n_chunks, "out": str(out_path)}

def main():
    ap = argparse.ArgumentParser(description="Overlap chunking for JSONL survey files.")
    ap.add_argument("inputs", nargs="+",
                    help="Input .jsonl file paths (supports shell globs in most shells).")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help=f"Max characters per chunk (default: {DEFAULT_MAX_CHARS})")
    ap.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP_CHARS,
                    help=f"Overlap characters between chunks (default: {DEFAULT_OVERLAP_CHARS})")
    args = ap.parse_args()

    results = []
    for p in args.inputs:
        path = Path(p)
        if not path.exists():
            print(f"[WARN] Missing: {p}")
            continue
        if path.suffix.lower() != ".jsonl":
            print(f"[WARN] Not a .jsonl file, skipping: {p}")
            continue
        res = process_file(path, args.max_chars, args.overlap)
        results.append(res)
        print(f"[OK] {res['file']}: records={res['records']:,}, chunks={res['chunks']:,} -> {res['out']}")
    if not results:
        print("[INFO] No files processed.")

if __name__ == "__main__":
    main()
