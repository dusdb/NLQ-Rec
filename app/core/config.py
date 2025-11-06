"""
환경 변수(.env 파일)로부터 
Claude API 키와 모델 설정을 
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
    
    # 모델 설정 
    claude_opus_model: str = "claude-opus-4-1"
    claude_sonnet_model: str = "claude-sonnet-4-5"
    claude_haiku_model: str = "claude-haiku-4-5"
    
    # API 제한 설정
    max_tokens: int = 4096
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    """설정 싱글톤 인스턴스 반환"""
    return Settings()