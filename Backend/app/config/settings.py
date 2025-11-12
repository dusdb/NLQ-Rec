"""
환경 변수(.env 파일)로부터 
LLM 및 PostgreSQL 설정을 
자동으로 로드하고 관리
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    app_name: str = "Panel Search System"
    app_version: str = "1.0.0"
    
    # Claude API 설정
    anthropic_api_key: str
    
    # =======================================================
    # 모델 역할별 설정 (Haiku로 최종 최적화)
    # =======================================================
    CLAUDE_QUERY_ANALYSIS_MODEL: str = "claude-3-haiku-20240307"
    CLAUDE_SQL_GENERATION_MODEL: str = "claude-3-haiku-20240307"
    CLAUDE_INSIGHT_EXTRACTION_MODEL: str = "claude-3-haiku-20240307"
    
    # API 제한 설정
    max_tokens: int = 4096
    
    # =======================================================
    # PostgreSQL 설정 (새로 추가)
    # =======================================================
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = 'ignore'  
        populate_by_name = True


@lru_cache()
def get_settings():
    """설정 싱글톤 인스턴스 반환"""
    return Settings()