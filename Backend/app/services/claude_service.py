"""
Claude API ?쒕퉬??- 紐⑤뜽???ㅼ젙 ?뚯씪?먯꽌 ?숈쟻?쇰줈 媛?몄삤?꾨줉 ?붿빱?뚮쭅
?ㅻ쪟 ?섏젙: system_message 蹂?섍? try 釉붾줉 ?댁뿉??紐낇솗?섍쾶 ?뺤쓽?섎룄濡??섏젙
"""
from anthropic import Anthropic
from typing import Dict, Any, List
import json

from app.config.settings import get_settings
from app.services.prompt_templates import PromptTemplates
from app.services.query_parser import QueryParser

settings = get_settings()


class ClaudeService:
    """Claude API瑜??ъ슜???먯뿰??泥섎━ ?쒕퉬??""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
        self.query_parser = QueryParser()
    
    # [1李??몄텧] 荑쇰━ 遺꾩꽍
    def analyze_query(
        self, 
        user_query: str,
        use_parser: bool = True
    ) -> Dict[str, Any]:
        """
        ?ъ슜???먯뿰??吏덉쓽瑜?遺꾩꽍?섎ŉ ?ㅼ젙??紐⑤뜽???ъ슜?⑸땲??
        """
        
        # ?좑툘 ?ㅻ쪟 諛⑹?: try 釉붾줉 ?댁뿉??紐⑤뱺 ?꾩닔 蹂???뺤쓽
        try:
            # 1?④퀎: Query Parser濡??ъ쟾 泥섎━
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
            
            # 2?④퀎: LLM ?몄텧???꾪븳 ?꾨＼?꾪듃? ?쒖뒪??硫붿떆吏 ?뺤쓽
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.query_analysis_prompt(user_query, schema)
            system_message = self.prompt_templates.get_system_message('analyzer') # <-- ?ш린???뺤쓽!

            
            message = self.client.messages.create(
                model=settings.CLAUDE_QUERY_ANALYSIS_MODEL,  # <-- ?ㅼ젙 ?뚯씪?먯꽌 紐⑤뜽 媛?몄샂
                max_tokens=settings.max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # ?묐떟 泥섎━ 濡쒖쭅
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
                    "error": f"JSON ?뚯떛 ?ㅽ뙣: {str(e)}"
                }
                
        except Exception as e:
            # ?ㅻ쪟 諛쒖깮 ??pre_analysis媛 ?뺤쓽?섏? ?딆븯?????덉쑝誘濡?湲곕낯媛??ъ슜
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # [2李??몄텧] SQL ?앹꽦
    def generate_sql(
        self, 
        analyzed_query: Dict[str, Any],
        target_count: int = 100
    ) -> Dict[str, Any]:
        """
        JSON 遺꾩꽍 寃곌낵瑜?SQL濡?蹂?섑븯硫??ㅼ젙??紐⑤뜽???ъ슜?⑸땲??
        """
        
        try:
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.sql_generation_prompt(
                analyzed_query,
                schema,
                target_count
            )
            system_message = self.prompt_templates.get_system_message('sql_generator') # <-- ?ш린???뺤쓽!
            
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
    
    # [3李??몄텧] ?몄궗?댄듃 異붿텧
    def extract_insights(
        self, 
        panel_data: List[Dict[str, Any]],
        original_query: str = None
    ) -> Dict[str, Any]:
        """
        ?⑤꼸 洹몃９???④꺼吏?怨듯넻 ?뱀꽦??異붿텧?섎ŉ ?ㅼ젙??紐⑤뜽???ъ슜?⑸땲??
        """
        
        try:
            sample_size = min(50, len(panel_data))
            sampled_data = panel_data[:sample_size]
            
            prompt = self.prompt_templates.insight_extraction_prompt(
                sampled_data,
                original_query or "?ъ슜??吏덉쓽 ?놁쓬"
            )
            system_message = self.prompt_templates.get_system_message('insight_extractor') # <-- ?ш린???뺤쓽!
            
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
                    "error": "JSON ?뚯떛 ?ㅽ뙣"
                }
                
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # =====================================================
    # ?좏떥由ы떚 硫붿꽌??
    # =====================================================
    
    @staticmethod
    def _clean_json_response(text: str) -> str:
        """JSON ?묐떟?먯꽌 留덊겕?ㅼ슫 肄붾뱶 釉붾줉 ?쒓굅"""
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        return text
    
    @staticmethod
    def _clean_sql_response(text: str) -> str:
        """SQL ?묐떟?먯꽌 留덊겕?ㅼ슫 肄붾뱶 釉붾줉 ?쒓굅"""
        if text.startswith("```sql"):
            text = text.replace("```sql", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        return text


# ?깃????몄뒪?댁뒪
claude_service = ClaudeService()
