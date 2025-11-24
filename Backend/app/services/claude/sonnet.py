# app/services/claude/sonnet.py
"""
Sonnet 모델
인사이트 추출
전략 보고서 생성
결과 검증
"""
from anthropic import Anthropic
from typing import Dict, Any, List, Optional

from app.config.settings import get_settings
from app.services.prompts import PromptTemplates
from .base import ClaudeBase

settings = get_settings()


class SonnetService(ClaudeBase):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
    
    def extract_insights(
        self, 
        panel_data: List[Dict[str, Any]], 
        original_query: str = None,
        full_statistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            sample_size = min(50, len(panel_data))
            sampled_data = panel_data[:sample_size]
            
            prompt = self.prompt_templates.insight_extraction_prompt(
                sampled_data, 
                original_query or "사용자 질의 없음",
                full_statistics
            )
            
            system_message = self.prompt_templates.get_system_message('insight_extractor')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\nRaw Insight Response:\n{response_text}\n")
            
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:
                filtered_patterns = self._filter_invalid_insights(
                    parsed_result.get('hidden_patterns', [])
                )
                
                parsed_result['hidden_patterns'] = filtered_patterns
                
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text,
                    "filtered_count": {
                        "valid": len(filtered_patterns),
                        "removed": len(parsed_result.get('hidden_patterns', [])) - len(filtered_patterns)
                    }
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Insight Extraction Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def generate_strategy_report(
        self,
        insights: Dict[str, Any],
        original_query: str,
        panel_count: int
    ) -> Dict[str, Any]:
        try:
            prompt = self.prompt_templates.strategy_report_prompt(
                insights,
                original_query,
                panel_count
            )
            
            system_message = self.prompt_templates.get_system_message('strategy_planner')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\nRaw Strategy Report Response:\n{response_text}\n")
            
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Strategy Report Generation Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def validate_results(
        self,
        sql_result: List[Dict],
        original_conditions: Dict,
        target_count: int
    ) -> Dict[str, Any]:
        try:
            prompt = self.prompt_templates.result_validation_prompt(
                sql_result,
                original_conditions,
                target_count
            )
            system_message = self.prompt_templates.get_system_message('validator')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_RESULT_VALIDATION_MODEL,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            parsed_result = self.parse_json_response(response_text)
            
            if parsed_result:
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            print(f"Validation Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    @staticmethod
    def _filter_invalid_insights(patterns: List[Dict]) -> List[Dict]:
        filtered = []
        removed = []
        
        for pattern in patterns:
            feature = pattern.get('feature', '').lower()
            value = pattern.get('value', '').lower()
            insight = pattern.get('insight', '')
            
            is_unrecorded_topic = any(kw in feature for kw in [
                '미기재', '정보 없', '데이터 부족', '수집되지 않',
                '비공개', '기입하지 않', '입력하지 않',
                '알 수 없', '확인 불가', '누락', '부재'
            ])
            
            is_fully_unrecorded = any(phrase in value or phrase in insight for phrase in [
                '100% 미기재', '전원 미기재', '모두 미기재',
                '전체 미기재', '100%가 미기재'
            ])
            
            if is_unrecorded_topic or is_fully_unrecorded:
                removed.append(pattern)
                print(f"미기재 인사이트 제거: {feature} - {insight[:50]}...")
                continue
            
            filtered.append(pattern)
        
        print(f"유효한 인사이트: {len(filtered)}개")
        if removed:
            print(f"제거된 인사이트: {len(removed)}개")
        
        return filtered