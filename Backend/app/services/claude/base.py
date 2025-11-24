# app/services/claude/base.py
"""
Claude API 공통 기능
JSON 파싱, SQL 추출 등
"""
from typing import Optional, Dict
import json
import re


class ClaudeBase:

    @staticmethod
    def parse_json_response(text: str) -> Optional[Dict]:
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1 and start < end:
                json_text = text[start:end+1]
                return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 실패: {e}")
        
        return None
    
    @staticmethod
    def extract_sql(text: str) -> Optional[str]:
        text = text.replace("```sql", "").replace("```json", "").replace("```", "").strip()
        
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'sql_query' in parsed:
                sql = parsed['sql_query']
                sql = ' '.join(sql.split())
                print(f"SQL extracted from JSON format")
                return sql.rstrip(';')
        except json.JSONDecodeError:
            pass
        
        lines = text.split('\n')
        sql_lines = []
        collecting = False
        
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith('SELECT'):
                collecting = True
                sql_lines.append(line)
            elif collecting:
                if not any('\uac00' <= c <= '\ud7a3' for c in line):
                    sql_lines.append(line)
                    if ';' in line or 'LIMIT' in line.upper():
                        break
                else:
                    break
        
        if sql_lines:
            sql = ' '.join(sql_lines)
            sql = re.sub(r'\s+', ' ', sql)
            sql = sql.rstrip(';').strip()
            print(f"SQL extracted by SELECT pattern")
            return sql
        
        text = text.strip()
        if text.upper().startswith('SELECT'):
            sql = ' '.join(text.split())
            return sql.rstrip(';')
        
        print(f"SQL extraction failed")
        return None