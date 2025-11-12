"""
Claude API 서비스 - 모델을 설정 파일에서 동적으로 가져오도록 디커플링
오류 수정: system_message 변수가 try 블록 내에서 명확하게 정의되도록 수정
"""
from anthropic import Anthropic
from typing import Dict, Any, List
import json

from app.config.settings import get_settings
from app.services.prompt_templates import PromptTemplates
from app.services.query_parser import QueryParser

settings = get_settings()


class ClaudeService:
    """Claude API를 사용한 자연어 처리 서비스"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
        self.query_parser = QueryParser()
    
    # [1차 호출] 쿼리 분석
    def analyze_query(
        self, 
        user_query: str,
        use_parser: bool = True
    ) -> Dict[str, Any]:
        """
        사용자 자연어 질의를 분석하며 설정된 모델을 사용합니다.
        """
        
        # ⚠️ 오류 방지: try 블록 내에서 모든 필수 변수 정의
        try:
            # 1단계: Query Parser로 사전 처리
            if use_parser:
                parsed_data = self.query_parser.full_parse_and_augment(user_query)
                pre_analysis = {
                    "parsed_conditions": parsed_data['search_conditions'],
                    "suggestions": parsed_data['suggestions'],
                    "keywords": parsed_data['keywords'],
                    "complexity": parsed_data['complexity']
                }
            else:
                pre_analysis = None
            
            # 2단계: LLM 호출을 위한 프롬프트와 시스템 메시지 정의
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.query_analysis_prompt(user_query, schema)
            system_message = self.prompt_templates.get_system_message('analyzer') # <-- 여기서 정의!

            
            message = self.client.messages.create(
                model=settings.CLAUDE_QUERY_ANALYSIS_MODEL,  # <-- 설정 파일에서 모델 가져옴
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 응답 처리 로직
            response_text = message.content[0].text.strip()
            response_text = self._clean_json_response(response_text)
            
            try:
                parsed_result = json.loads(response_text)
                
                return {
                    "success": True,
                    "data": parsed_result,
                    "pre_analysis": pre_analysis,
                    "raw_response": response_text
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "data": None,
                    "pre_analysis": pre_analysis,
                    "raw_response": response_text,
                    "error": f"JSON 파싱 실패: {str(e)}"
                }
                
        except Exception as e:
            # 오류 발생 시 pre_analysis가 정의되지 않았을 수 있으므로 기본값 사용
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # [2차 호출] SQL 생성
    def generate_sql(
        self, 
        analyzed_query: Dict[str, Any],
        target_count: int = 100
    ) -> Dict[str, Any]:
        """
        JSON 분석 결과를 SQL로 변환하며 설정된 모델을 사용합니다.
        """
        
        try:
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.sql_generation_prompt(
                analyzed_query,
                schema,
                target_count
            )
            system_message = self.prompt_templates.get_system_message('sql_generator') # <-- 여기서 정의!
            
            message = self.client.messages.create(
                model=settings.CLAUDE_SQL_GENERATION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text.strip()
            response_text = self._clean_json_response(response_text)
            
            try:
                parsed_result = json.loads(response_text)
                sql_query = parsed_result.get('sql_query', response_text)
                
                return {
                    "success": True,
                    "sql_query": sql_query,
                    "metadata": {
                        "estimated_rows": parsed_result.get('estimated_rows'),
                        "execution_plan": parsed_result.get('execution_plan')
                    },
                    "raw_response": response_text
                }
            except json.JSONDecodeError:
                sql_query = self._clean_sql_response(response_text)
                
                return {
                    "success": True,
                    "sql_query": sql_query,
                    "metadata": None,
                    "raw_response": response_text
                }
                
        except Exception as e:
            return {
                "success": False,
                "sql_query": None,
                "error": str(e)
            }
    
    # [3차 호출] 인사이트 추출
    def extract_insights(
        self, 
        panel_data: List[Dict[str, Any]],
        original_query: str = None
    ) -> Dict[str, Any]:
        """
        패널 그룹의 숨겨진 공통 특성을 추출하며 설정된 모델을 사용합니다.
        """
        
        try:
            sample_size = min(50, len(panel_data))
            sampled_data = panel_data[:sample_size]
            
            prompt = self.prompt_templates.insight_extraction_prompt(
                sampled_data,
                original_query or "사용자 질의 없음"
            )
            system_message = self.prompt_templates.get_system_message('insight_extractor') # <-- 여기서 정의!
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text.strip()
            response_text = self._clean_json_response(response_text)
            
            try:
                parsed_result = json.loads(response_text)
                return {
                    "success": True,
                    "data": parsed_result,
                    "raw_response": response_text
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "data": None,
                    "raw_response": response_text,
                    "error": "JSON 파싱 실패"
                }
                
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # =====================================================
    # 유틸리티 메서드
    # =====================================================
    
    @staticmethod
    def _clean_json_response(text: str) -> str:
        """JSON 응답에서 마크다운 코드 블록 제거"""
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        return text
    
    @staticmethod
    def _clean_sql_response(text: str) -> str:
        """SQL 응답에서 마크다운 코드 블록 제거"""
        if text.startswith("```sql"):
            text = text.replace("```sql", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        return text


# 싱글톤 인스턴스
claude_service = ClaudeService()