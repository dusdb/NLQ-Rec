"""
Claude API 서비스

리팩토링 내용:
- JSON/SQL 파싱 로직 개선
- 에러 핸들링 강화
- 디버깅 로그 개선
- 코드 가독성 향상
"""
from anthropic import Anthropic
from typing import Dict, Any, List, Optional
import json
import re

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
    
    # =====================================================
    # 1. 자연어 질의 분석 (Opus)
    # =====================================================
    
    def analyze_query(self, user_query: str, use_parser: bool = True) -> Dict[str, Any]:
        """
        사용자 자연어 질의를 분석
        
        Args:
            user_query: 사용자 입력 질의
            use_parser: QueryParser 사용 여부
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            # 사전 파싱 (선택적)
            pre_analysis = None
            if use_parser:
                parsed_data = self.query_parser.full_parse_and_augment(user_query)
                pre_analysis = {
                    "parsed_conditions": parsed_data['search_conditions'],
                    "suggestions": parsed_data['suggestions'],
                    "keywords": parsed_data['keywords'],
                    "complexity": parsed_data['complexity']
                }
                print(f"📋 Pre-analysis: {json.dumps(pre_analysis, ensure_ascii=False, indent=2)}")
            
            # Claude API 호출
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
            print(f"\n📝 Raw Analysis Response:\n{response_text}\n")
            
            # JSON 파싱
            parsed_result = self._parse_json_response(response_text)
            
            if parsed_result:
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
            print(f"❌ Query Analysis Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # =====================================================
    # 2. SQL 쿼리 생성 (Haiku)
    # =====================================================
    
    def generate_sql(
        self, 
        analyzed_query: Dict[str, Any], 
        target_count: int = 100
    ) -> Dict[str, Any]:
        """
        JSON 분석 결과를 SQL로 변환
        
        Args:
            analyzed_query: 분석된 검색 조건
            target_count: 목표 추출 인원 수
            
        Returns:
            SQL 쿼리 결과 딕셔너리
        """
        try:
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.sql_generation_prompt(
                analyzed_query, 
                schema, 
                target_count
            )
            system_message = self.prompt_templates.get_system_message('sql_generator')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_SQL_GENERATION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\n📝 Raw SQL Response:\n{response_text}\n")
            
            # SQL 추출
            sql_query = self._extract_sql(response_text)
            print(f"🔍 Extracted SQL:\n{sql_query}\n")
            
            # SQL 유효성 검증
            if not sql_query or not sql_query.upper().strip().startswith('SELECT'):
                raise ValueError("유효하지 않은 SQL 쿼리")
            
            return {
                "success": True,
                "sql_query": sql_query,
                "metadata": {
                    "target_count": target_count,
                    "conditions": analyzed_query.get('search_conditions', {})
                },
                "raw_response": response_text
            }
                
        except Exception as e:
            print(f"❌ SQL Generation Error: {e}")
            return {
                "success": False,
                "sql_query": None,
                "error": str(e)
            }
    
    # =====================================================
    # 3. 인사이트 추출 (Opus)
    # =====================================================
    
    def extract_insights(
        self, 
        panel_data: List[Dict[str, Any]], 
        original_query: str = None
    ) -> Dict[str, Any]:
        """
        패널 그룹의 숨겨진 공통 특성 추출
        
        Args:
            panel_data: 검색된 패널 데이터
            original_query: 원래 사용자 질의
            
        Returns:
            인사이트 분석 결과
        """
        try:
            sample_size = min(50, len(panel_data))
            sampled_data = panel_data[:sample_size]
            
            prompt = self.prompt_templates.insight_extraction_prompt(
                sampled_data, 
                original_query or "사용자 질의 없음"
            )
            system_message = self.prompt_templates.get_system_message('insight_extractor')
            
            message = self.client.messages.create(
                model=settings.CLAUDE_INSIGHT_EXTRACTION_MODEL, 
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            print(f"\n📝 Raw Insight Response:\n{response_text}\n")
            
            # JSON 파싱
            parsed_result = self._parse_json_response(response_text)
            
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
            print(f"❌ Insight Extraction Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # =====================================================
    # 4. 결과 검증 (Sonnet)
    # =====================================================
    
    def validate_results(
        self,
        sql_result: List[Dict],
        original_conditions: Dict,
        target_count: int
    ) -> Dict[str, Any]:
        """
        SQL 실행 결과 검증
        
        Args:
            sql_result: SQL 실행 결과
            original_conditions: 원래 검색 조건
            target_count: 목표 추출 수
            
        Returns:
            검증 결과
        """
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
            parsed_result = self._parse_json_response(response_text)
            
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
            print(f"❌ Validation Error: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # =====================================================
    # 유틸리티: JSON 파싱
    # =====================================================
    
    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict]:
        """
        Claude 응답에서 JSON 추출 및 파싱
        
        Args:
            text: Claude API 응답 텍스트
            
        Returns:
            파싱된 JSON 딕셔너리 또는 None
        """
        # 1. 마크다운 코드 블록 제거
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # 2. 직접 파싱 시도
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 3. 중괄호 찾아서 추출
        try:
            # 가장 바깥쪽 { } 찾기
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1 and start < end:
                json_text = text[start:end+1]
                return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 실패: {e}")
        
        return None
    
    # =====================================================
    # 유틸리티: SQL 추출
    # =====================================================
    
    @staticmethod
    def _extract_sql(text: str) -> Optional[str]:
        """
        Claude 응답에서 SQL 쿼리 추출
        
        Args:
            text: Claude API 응답 텍스트
            
        Returns:
            추출된 SQL 쿼리 또는 None
        """
        # 1. 마크다운 제거
        text = text.replace("```sql", "").replace("```json", "").replace("```", "").strip()
        
        # 2. JSON 형식인 경우 처리
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'sql_query' in parsed:
                sql = parsed['sql_query']
                # 줄바꿈을 공백으로 변환
                sql = ' '.join(sql.split())
                print(f"⚙️ SQL extracted from JSON format")
                return sql.rstrip(';')
        except json.JSONDecodeError:
            pass
        
        # 3. 줄 단위로 SELECT 찾기
        lines = text.split('\n')
        sql_lines = []
        collecting = False
        
        for line in lines:
            line = line.strip()
            
            # SELECT 시작
            if line.upper().startswith('SELECT'):
                collecting = True
                sql_lines.append(line)
            elif collecting:
                # 한글이 포함된 설명은 제외
                if not any('\uac00' <= c <= '\ud7a3' for c in line):
                    sql_lines.append(line)
                    # 세미콜론이나 LIMIT으로 끝나면 종료
                    if ';' in line or 'LIMIT' in line.upper():
                        break
                else:
                    # 한글 설명이 나오면 종료
                    break
        
        if sql_lines:
            # 한 줄로 합치기
            sql = ' '.join(sql_lines)
            # 여러 공백을 하나로
            sql = re.sub(r'\s+', ' ', sql)
            # 세미콜론 제거
            sql = sql.rstrip(';').strip()
            print(f"⚙️ SQL extracted by SELECT pattern")
            return sql
        
        # 4. 실패 시 원본 반환 (SELECT로 시작하는 경우만)
        text = text.strip()
        if text.upper().startswith('SELECT'):
            sql = ' '.join(text.split())
            return sql.rstrip(';')
        
        print(f"⚠️ SQL extraction failed")
        return None


# 싱글톤 인스턴스
claude_service = ClaudeService()