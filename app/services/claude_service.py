# app/services/claude_services.py
"""
Claude API 서비스 - 프롬프트 템플릿 통합 버전
자연어 처리, SQL 생성, 인사이트 추출을 담당
"""

from anthropic import Anthropic
from typing import Dict, Any, List
import json

from app.core.config import get_settings
from app.services.prompt_templates import PromptTemplates
from app.services.query_parser import QueryParser

settings = get_settings()


class ClaudeService:
    """Claude API를 사용한 자연어 처리 서비스"""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
        self.query_parser = QueryParser()
    
    def analyze_query_with_opus(
        self, 
        user_query: str,
        use_parser: bool = True
    ) -> Dict[str, Any]:
        """
        Opus 모델을 사용하여 사용자 자연어 질의 분석
        
        Args:
            user_query: 사용자 입력 자연어 질의
            use_parser: 정규화 파서 사용 여부 (기본값: True)
        
        Returns:
            분석 결과 딕셔너리
        """
        
        try:
            # 1단계: Query Parser로 사전 처리 (선택적)
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
            
            # 2단계: Opus로 정밀 분석
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.query_analysis_prompt(user_query, schema)
            system_message = self.prompt_templates.get_system_message('analyzer')
            
            message = self.client.messages.create(
                model=settings.claude_opus_model,
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 응답에서 텍스트 추출
            response_text = message.content[0].text.strip()
            
            # 마크다운 코드 블록 제거
            response_text = self._clean_json_response(response_text)
            
            # JSON 파싱 시도
            try:
                parsed_result = json.loads(response_text)
                
                return {
                    "success": True,
                    "data": parsed_result,
                    "pre_analysis": pre_analysis,  # 파서 결과 포함
                    "raw_response": response_text
                }
            except json.JSONDecodeError as e:
                # JSON 파싱 실패 시 원본 텍스트 반환
                return {
                    "success": False,
                    "data": None,
                    "pre_analysis": pre_analysis,
                    "raw_response": response_text,
                    "error": f"JSON 파싱 실패: {str(e)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def generate_sql_with_haiku(
        self, 
        analyzed_query: Dict[str, Any],
        target_count: int = 100
    ) -> Dict[str, Any]:
        """
        Haiku 모델을 사용하여 SQL 쿼리 생성
        
        Args:
            analyzed_query: Opus가 분석한 질의 결과
            target_count: 목표 추출 인원 수
        
        Returns:
            SQL 쿼리 딕셔너리
        """
        
        try:
            # 프롬프트 템플릿 사용
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.sql_generation_prompt(
                analyzed_query,
                schema,
                target_count
            )
            system_message = self.prompt_templates.get_system_message('sql_generator')
            
            message = self.client.messages.create(
                model=settings.claude_haiku_model,
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
            
            # 응답 정리
            response_text = self._clean_json_response(response_text)
            
            # JSON 응답 파싱 시도
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
                # JSON이 아니면 SQL 쿼리로 간주
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
    
    def verify_and_format_with_sonnet(
        self, 
        sql_query: str, 
        query_results: List[Dict[str, Any]],
        original_conditions: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Sonnet 모델을 사용하여 결과 검증 및 포맷팅
        
        Args:
            sql_query: 실행된 SQL 쿼리
            query_results: SQL 실행 결과
            original_conditions: 원래 검색 조건
        
        Returns:
            검증 및 포맷팅된 결과
        """
        
        try:
            # 프롬프트 템플릿 사용
            prompt = self.prompt_templates.result_validation_prompt(
                query_results,
                original_conditions or {},
                target_count=100
            )
            system_message = self.prompt_templates.get_system_message('validator')
            
            message = self.client.messages.create(
                model=settings.claude_sonnet_model,
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
    
    def extract_insights_with_opus(
        self, 
        panel_data: List[Dict[str, Any]],
        original_query: str = None
    ) -> Dict[str, Any]:
        """
        Opus 모델을 사용하여 패널 그룹의 숨겨진 공통 특성 추출
        
        Args:
            panel_data: 패널 데이터 리스트
            original_query: 원래 사용자 질의 (선택)
        
        Returns:
            인사이트 추출 결과
        """
        
        try:
            # 프롬프트 템플릿 사용
            prompt = self.prompt_templates.insight_extraction_prompt(
                panel_data,
                original_query or "사용자 질의 없음"
            )
            system_message = self.prompt_templates.get_system_message('insight_extractor')
            
            message = self.client.messages.create(
                model=settings.claude_opus_model,
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