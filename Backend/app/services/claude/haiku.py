# app/services/claude/haiku.py
"""
Haiku 모델
SQL 생성
"""
from anthropic import Anthropic
from typing import Dict, Any

from app.config.settings import get_settings
from app.services.prompts import PromptTemplates
from .base import ClaudeBase

settings = get_settings()


class HaikuService(ClaudeBase):
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.prompt_templates = PromptTemplates()
    
    def generate_sql(
        self, 
        analyzed_query: Dict[str, Any], 
        target_count: int = 100
    ) -> Dict[str, Any]:
        try:
            conditions = analyzed_query.get('search_conditions', {}).copy()
            if 'gender' in conditions and conditions['gender']:
                gender_map = {
                    '남성': '남', 
                    '여성': '여', 
                    '남': '남', 
                    '여': '여',
                    'M': '남',
                    'F': '여'
                }
                original_gender = conditions['gender']
                if original_gender in gender_map:
                    conditions['gender'] = gender_map[original_gender]
                    print(f"Gender converted: '{original_gender}' -> '{conditions['gender']}'")
            
            modified_query = analyzed_query.copy()
            modified_query['search_conditions'] = conditions
            
            schema = self.prompt_templates.load_schema()
            prompt = self.prompt_templates.sql_generation_prompt(
                modified_query,
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
            print(f"\nRaw SQL Response:\n{response_text}\n")
            
            sql_query = self.extract_sql(response_text)
            print(f"Extracted SQL:\n{sql_query}\n")
            
            if not sql_query or not sql_query.upper().strip().startswith('SELECT'):
                raise ValueError("유효하지 않은 SQL 쿼리")
            
            return {
                "success": True,
                "sql_query": sql_query,
                "metadata": {
                    "target_count": target_count,
                    "conditions": conditions
                },
                "raw_response": response_text
            }
                
        except Exception as e:
            print(f"SQL Generation Error: {e}")
            return {
                "success": False,
                "sql_query": None,
                "error": str(e)
            }