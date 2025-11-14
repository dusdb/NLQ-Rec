# app/config/settings.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    app_name: str = "Panel Search System"
    app_version: str = "1.0.0"
    
    # Claude API 설정 (여러 변수명 지원)
    anthropic_api_key: str
    
    # 모델 역할별 설정 (API 정확 모델명)
    CLAUDE_QUERY_ANALYSIS_MODEL: str = "claude-opus-4-1"  # 쿼리 해석
    CLAUDE_SQL_GENERATION_MODEL: str = "claude-haiku-4-5"  # SQL 생성 (최신)
    CLAUDE_INSIGHT_EXTRACTION_MODEL: str = "claude-opus-4-1"  # 인사이트 추출
    CLAUDE_RESULT_VALIDATION_MODEL: str = "claude-sonnet-4-5"  # 결과 검증
    
    # API 제한 설정
    max_tokens: int = 4096
    
    # ✅ PostgreSQL 설정 (POSTGRES_* 변수명 사용)
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    
    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False
        extra = 'ignore'
        populate_by_name = True
        # ✅ 환경 변수 별칭 매핑
        fields = {
            'POSTGRES_HOST': {'env': ['POSTGRES_HOST', 'DB_HOST']},
            'POSTGRES_PORT': {'env': ['POSTGRES_PORT', 'DB_PORT']},
            'POSTGRES_DB': {'env': ['POSTGRES_DB', 'DB_NAME']},
            'POSTGRES_USER': {'env': ['POSTGRES_USER', 'DB_USER']},
            'POSTGRES_PASSWORD': {'env': ['POSTGRES_PASSWORD', 'DB_PASSWORD']},
            'anthropic_api_key': {'env': ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']},
        }


@lru_cache()
def get_settings():
    """설정 싱글톤 인스턴스 반환"""
    return Settings()