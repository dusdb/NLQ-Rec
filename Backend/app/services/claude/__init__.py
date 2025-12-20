# app/services/claude/__init__.py
"""
Claude API 서비스 모듈
- Opus: 쿼리 분석
- Haiku: SQL 생성
- Sonnet: 인사이트 추출, 전략 보고서, 결과 검증
"""
from .opus import OpusService
from .haiku import HaikuService
from .sonnet import SonnetService

__all__ = ['OpusService', 'HaikuService', 'SonnetService']

class ClaudeService:
    
    def __init__(self):
        self.opus = OpusService()
        self.haiku = HaikuService()
        self.sonnet = SonnetService()
    
    def analyze_query(self, user_query: str, use_parser: bool = True):
        return self.opus.analyze_query(user_query, use_parser)
    
    def generate_sql(self, analyzed_query, target_count: int = 100):
        return self.haiku.generate_sql(analyzed_query, target_count)
    
    def extract_insights(self, panel_data, original_query=None, full_statistics=None):
        return self.sonnet.extract_insights(panel_data, original_query, full_statistics)
    
    def generate_strategy_report(self, insights, original_query, panel_count):
        return self.sonnet.generate_strategy_report(insights, original_query, panel_count)
    
    def validate_results(self, sql_result, original_conditions, target_count):
        return self.sonnet.validate_results(sql_result, original_conditions, target_count)

claude_service = ClaudeService()