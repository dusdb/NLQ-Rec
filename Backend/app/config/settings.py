# app/config/settings.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from typing import Optional, List
import logging

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

logger = logging.getLogger(__name__)


class Settings(BaseSettings):

    app_name: str = "Panel Search System"
    app_version: str = "1.0.0"
    debug: bool = False

    anthropic_api_key: str

    CLAUDE_QUERY_ANALYSIS_MODEL: str = "claude-opus-4-20250514"
    CLAUDE_SQL_GENERATION_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_INSIGHT_EXTRACTION_MODEL: str = "claude-sonnet-4-5-20250929"
    CLAUDE_RESULT_VALIDATION_MODEL: str = "claude-sonnet-4-5-20250929"

    max_tokens: int = 4096
    enable_prompt_caching: bool = True

    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600 

    DB_SSL_MODE: str = "require"

    CORS_ORIGINS: List[str] = ["*"] 
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False
        extra = 'ignore'
        populate_by_name = True

        fields = {
            'POSTGRES_HOST': {'env': ['POSTGRES_HOST', 'DB_HOST']},
            'POSTGRES_PORT': {'env': ['POSTGRES_PORT', 'DB_PORT']},
            'POSTGRES_DB': {'env': ['POSTGRES_DB', 'DB_NAME']},
            'POSTGRES_USER': {'env': ['POSTGRES_USER', 'DB_USER']},
            'POSTGRES_PASSWORD': {'env': ['POSTGRES_PASSWORD', 'DB_PASSWORD']},
            'anthropic_api_key': {'env': ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']},
        }
    
    @property
    def database_url(self) -> str:
        """PostgreSQL 연결 URL 생성 (psycopg2용)"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?sslmode={self.DB_SSL_MODE}"
        )
    
    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def db_config(self) -> dict:
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "dbname": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
            "sslmode": self.DB_SSL_MODE,
        }
    
    def validate_db_config(self) -> bool:
        required_fields = [
            self.POSTGRES_HOST,
            self.POSTGRES_DB,
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD
        ]
        
        if not all(required_fields):
            logger.error("데이터베이스 설정이 불완전합니다.")
            return False
        
        if self.POSTGRES_PORT < 1 or self.POSTGRES_PORT > 65535:
            logger.error(f"잘못된 포트 번호: {self.POSTGRES_PORT}")
            return False
        
        return True
    
    def mask_sensitive_data(self) -> dict:
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "debug": self.debug,
            "POSTGRES_HOST": self.POSTGRES_HOST,
            "POSTGRES_PORT": self.POSTGRES_PORT,
            "POSTGRES_DB": self.POSTGRES_DB,
            "POSTGRES_USER": self.POSTGRES_USER,
            "POSTGRES_PASSWORD": "***",
            "anthropic_api_key": f"{self.anthropic_api_key[:8]}...",
            "database_url": f"postgresql://{self.POSTGRES_USER}:***@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}",
        }
    
    def log_config(self):
        config = self.mask_sensitive_data()
        logger.info("=" * 50)
        logger.info("Application Configuration")
        logger.info("=" * 50)
        for key, value in config.items():
            logger.info(f"{key}: {value}")
        logger.info("=" * 50)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    if not settings.validate_db_config():
        raise ValueError("데이터베이스 설정이 올바르지 않습니다. .env 파일을 확인하세요.")
    
    return settings