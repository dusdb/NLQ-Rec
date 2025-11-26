# app/services/claude/opus.py
"""
Opus 모델
쿼리 분석
"""
from anthropic import Anthropic
from typing import Dict, Any
import json

from app.config.settings import get_settings
from app.services.prompts import PromptTemplates
from app.services.parsers import QueryParser
from .base import ClaudeBase

settings = get_settings()


class OpusService(ClaudeBase):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
        self.query_parser = QueryParser()
    
    def analyze_query(self, user_query: str, use_parser: bool = True) -> Dict[str, Any]:
        try:
            pre_analysis = None

            # ===== 1) 로컬 파서로 1차 분석 =====
            if use_parser:
                parsed_data = self.query_parser.full_parse_and_augment(user_query)
                target_count = self.query_parser.extract_target_count(user_query)

                pre_analysis = {
                    "parsed_conditions": parsed_data['search_conditions'],
                    "suggestions": parsed_data['suggestions'],
                    "keywords": parsed_data['keywords'],
                    "complexity": parsed_data['complexity'],
                    "target_count": target_count
                }
                print(f"Pre-analysis: {json.dumps(pre_analysis, ensure_ascii=False, indent=2)}")
            
            # ===== 2) LLM에게 정식 분석 요청 =====
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.query_analysis_prompt(user_query, schema)
            system_message = self.prompt_templates.get_system_message('analyzer')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_QUERY_ANALYSIS_MODEL,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\nRaw Analysis Response:\n{response_text}\n")
            
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:

                # 🔹 3) 로컬 파서 조건을 LLM 결과에 병합 (여기가 중요)
                if pre_analysis:
                    parsed_conditions = pre_analysis.get("parsed_conditions") or {}
                    if parsed_conditions:
                        llm_conditions = parsed_result.get("search_conditions") or {}
                        
                        # 파서가 뽑은 조건이 있고, LLM이 비워둔 필드만 덮어쓰기
                        for key, value in parsed_conditions.items():
                            if value is None:
                                continue
                            if key not in llm_conditions or llm_conditions[key] in (None, "", [], {}):
                                llm_conditions[key] = value
                        
                        parsed_result["search_conditions"] = llm_conditions
                        print(
                            "Merged search_conditions: "
                            f"{json.dumps(llm_conditions, ensure_ascii=False, indent=2)}"
                        )

                    # 기존 target_count 반영 로직 유지
                    if pre_analysis.get('target_count'):
                        parsed_result['target_count'] = pre_analysis['target_count']
                
                return {
                    "success": True,
                    "data": parsed_result,
                    "pre_analysis": pre_analysis,
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "pre_analysis": pre_analysis,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Query Analysis Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }