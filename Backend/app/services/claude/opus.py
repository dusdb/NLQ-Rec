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

                if pre_analysis and pre_analysis.get('target_count'):
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